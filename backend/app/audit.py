# -*- coding: utf-8 -*-
"""Журнал действий администратора и истории статусов заказов
(аудит 2026-10-06, R015, R006).

Два источника записей:

1. Middleware AdminAuditMiddleware. Каждый изменяющий запрос (POST, PUT,
   PATCH, DELETE) от администратора или во время имперсонации пишется в
   audit_events: шаблон маршрута, параметры пути и запроса, код ответа.
   Ничего не нужно добавлять в каждый эндпоинт: новые админские маршруты
   попадают в журнал сами. Тело запроса пишется только для маршрутов из
   BODY_ROUTES — там нет секретов (токен банка, тексты писем не пишутся).

2. Слушатель before_flush на смену Order.status. Ловит все пути, которыми
   заказ меняет статус (вебхук, опрос статуса, ежечасная сверка, ручная
   сверка, возврат), без правки каждого. Источник — необязательный атрибут
   order._status_source, который ставят эти пути.
"""
from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.audit_models import AuditEvent

logger = logging.getLogger(__name__)

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

# Маршруты, тело которых сохраняется целиком. Только без секретов.
BODY_ROUTES = {
    "PUT /api/admin/pricing",
    "PATCH /api/admin/users/{user_id}/role",
    "PATCH /api/admin/users/{user_id}/status",
    "PUT /api/admin/site-mode",
    "POST /api/admin/users/{user_id}/access-grants",
    "PUT /api/admin/reminders-settings",
    "PUT /api/admin/social-links",
}
MAX_BODY = 4000

# Параметр пути, который считается идентификатором сущности.
ENTITY_PARAMS = (
    ("order_id", "order"), ("user_id", "user"), ("grant_id", "access_grant"),
    ("assessment_id", "assessment"), ("portfolio_id", "m3_portfolio"),
    ("run_id", "m4_run"), ("strategy_id", "strategy"), ("combination", "strategy"),
    ("slug", "document"), ("code", "content"), ("contour", "contour"),
)


def _actor_from_cookie(request: Request) -> dict | None:
    """Кто действует: админ или админ под имперсонацией. Иначе None."""
    from app.auth import decode_token

    token = request.cookies.get("auth-token")
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None
    imp = payload.get("impersonated_by")
    if payload.get("role") != "admin" and not imp:
        return None
    return {"id": payload.get("sub"), "email": payload.get("email"), "impersonated_by": imp}


def uuid_or_none(value) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class AdminAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in MUTATING or not request.url.path.startswith("/api/"):
            return await call_next(request)
        actor = _actor_from_cookie(request)
        if actor is None:
            return await call_next(request)

        body = await request.body()
        # Обращение к state до call_next создаёт scope["state"]: эндпоинт
        # получает тот же словарь и может положить итог действия в
        # request.state.audit_result (например, сколько записей удалено).
        request.state.audit_result = None
        response = await call_next(request)
        try:
            await self._write(request, response.status_code, actor, body)
        except Exception:
            # Журнал не должен ронять действие, которое уже выполнено.
            logger.exception("audit: не удалось записать событие %s %s",
                             request.method, request.url.path)
        return response

    async def _write(self, request: Request, status_code: int, actor: dict, body: bytes) -> None:
        from app.db import AsyncSessionLocal

        route = request.scope.get("route")
        template = getattr(route, "path", None) or request.url.path
        action = f"{request.method} {template}"
        params = dict(request.scope.get("path_params") or {})

        entity_type = entity_id = None
        for name, etype in ENTITY_PARAMS:
            if name in params:
                entity_type, entity_id = etype, str(params[name])
                break

        after: dict = {}
        if params:
            after["path"] = {k: str(v) for k, v in params.items()}
        if request.query_params:
            after["query"] = dict(request.query_params)
        result = getattr(request.state, "audit_result", None)
        if result:
            after["result"] = result
        if action in BODY_ROUTES and body:
            try:
                after["body"] = json.loads(body[:MAX_BODY])
            except ValueError:
                after["body_raw"] = body[:MAX_BODY].decode("utf-8", "replace")

        async with AsyncSessionLocal() as s:
            s.add(AuditEvent(
                kind="admin",
                action=action[:200],
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=uuid_or_none(actor["id"]),
                actor_email=actor.get("email"),
                impersonated_by=uuid_or_none(actor.get("impersonated_by")),
                status_code=status_code,
                after=after or None,
            ))
            await s.commit()


# ── История статусов заказа ───────────────────────────────────────────────────

@event.listens_for(Session, "before_flush")
def _order_status_history(session: Session, flush_context, instances) -> None:
    from app.models import Order

    for obj in list(session.new):
        if isinstance(obj, Order):
            if obj.id is None:
                # Первичный ключ проставляется при flush; нужен заранее,
                # иначе запись журнала не к чему привязать.
                obj.id = uuid.uuid4()
            session.add(AuditEvent(
                kind="order", action="order.status", entity_type="order",
                entity_id=str(obj.id),
                after={"status": obj.status or "pending", "amount": float(obj.amount or 0),
                       "product": obj.product, "is_test": bool(obj.is_test)},
                note=getattr(obj, "_status_source", None) or "created",
            ))
    for obj in list(session.dirty):
        if not isinstance(obj, Order):
            continue
        hist = inspect(obj).attrs.status.history
        if not hist.has_changes():
            continue
        old = hist.deleted[0] if hist.deleted else None
        new = hist.added[0] if hist.added else obj.status
        if old == new:
            continue
        session.add(AuditEvent(
            kind="order", action="order.status", entity_type="order",
            entity_id=str(obj.id),
            before={"status": old}, after={"status": new},
            note=getattr(obj, "_status_source", None),
        ))
