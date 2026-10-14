# -*- coding: utf-8 -*-
"""
Журнал решений клиента и сводка переходов Метода 3 для администратора.

GET    /api/decisions?method=m3&source_id=…  — решения по отчёту
POST   /api/decisions                         — записать решение
PATCH  /api/decisions/{id}                    — правка и итог («что произошло»)
DELETE /api/decisions/{id}

GET    /api/admin/m3-transitions              — пары замеров Метода 3 с типом
                                                перехода по каждому направлению
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.db import get_db
from app.decision_models import Decision
from app.m3_models import M3ChecklistStep, M3Object, M3Portfolio, M3Result
from app.m3_transition import classify, scores_of
from app.m4_models import M4Run
from app.models import Assessment, User

router = APIRouter(prefix="/api/decisions", tags=["decisions"])
admin_router = APIRouter(prefix="/api/admin/m3-transitions", tags=["decisions-admin"],
                         dependencies=[Depends(require_admin)])

# Решения пишут к готовому отчёту. Потолок защищает от случайного
# зацикливания формы, а не от осмысленного использования.
MAX_PER_SOURCE = 30
TEXT_MAX = 4000

Method = Literal["m1", "m3", "m4"]
Outcome = Literal["done", "partial", "not_done"]


class DecisionIn(BaseModel):
    method: Method
    source_id: uuid.UUID
    scenario: str = Field(min_length=1, max_length=TEXT_MAX)
    actions: str | None = Field(default=None, max_length=TEXT_MAX)
    expected: str | None = Field(default=None, max_length=TEXT_MAX)


class DecisionPatch(BaseModel):
    scenario: str | None = Field(default=None, min_length=1, max_length=TEXT_MAX)
    actions: str | None = Field(default=None, max_length=TEXT_MAX)
    expected: str | None = Field(default=None, max_length=TEXT_MAX)
    # Пустая строка в outcome снимает отметку: null в JSON неотличим от
    # «поле не передали», а снять отметку клиент должен уметь.
    outcome: Outcome | Literal[""] | None = None
    outcome_note: str | None = Field(default=None, max_length=TEXT_MAX)


def _out(d: Decision) -> dict:
    return {
        "id": str(d.id), "method": d.method, "source_id": str(d.source_id),
        "scenario": d.scenario, "actions": d.actions, "expected": d.expected,
        "outcome": d.outcome, "outcome_note": d.outcome_note,
        "outcome_at": d.outcome_at.isoformat() if d.outcome_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


async def _source_owner(db: AsyncSession, method: str, source_id: uuid.UUID) -> tuple[uuid.UUID, bool] | None:
    """(владелец, готов ли отчёт) или None, если источника нет или он удалён."""
    if method == "m1":
        row = (await db.execute(
            select(Assessment.user_id, Assessment.status)
            .where(Assessment.id == source_id, Assessment.deleted_at.is_(None))
        )).first()
        return (row[0], row[1] in ("completed", "paid")) if row else None
    model = M3Portfolio if method == "m3" else M4Run
    row = (await db.execute(
        select(model.user_id, model.status)
        .where(model.id == source_id, model.deleted_at.is_(None))
    )).first()
    return (row[0], row[1] == "calculated") if row else None


async def _check_source(db: AsyncSession, user: User, method: str, source_id: uuid.UUID,
                        write: bool) -> None:
    src = await _source_owner(db, method, source_id)
    # Чужой отчёт отдаётся как несуществующий: 403 подтвердил бы, что id верный.
    if src is None or (src[0] != user.id and not (user.role == "admin" and not write)):
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    if write and not src[1]:
        raise HTTPException(status_code=400, detail="Решение записывается к готовому отчёту")


async def _own_decision(db: AsyncSession, user: User, decision_id: uuid.UUID) -> Decision:
    d = await db.scalar(select(Decision).where(Decision.id == decision_id))
    if d is None or d.user_id != user.id:
        raise HTTPException(status_code=404, detail="Решение не найдено")
    return d


@router.get("")
async def list_decisions(
    method: Method,
    source_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    src = await _source_owner(db, method, source_id)
    await _check_source(db, user, method, source_id, write=False)
    rows = (await db.execute(
        select(Decision)
        .where(Decision.method == method, Decision.source_id == source_id)
        .order_by(Decision.created_at, Decision.id)
    )).scalars().all()
    # editable: страница не знает, чей отчёт открыт. Администратор видит
    # чужие решения, но писать в чужой журнал не может.
    return {"items": [_out(d) for d in rows],
            "editable": src[0] == user.id and src[1]}


@router.post("", status_code=201)
async def create_decision(
    body: DecisionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_source(db, user, body.method, body.source_id, write=True)
    n = (await db.execute(
        select(func.count()).select_from(Decision)
        .where(Decision.method == body.method, Decision.source_id == body.source_id)
    )).scalar_one()
    if n >= MAX_PER_SOURCE:
        raise HTTPException(status_code=400, detail=f"К одному отчёту — не больше {MAX_PER_SOURCE} решений")
    d = Decision(
        user_id=user.id, method=body.method, source_id=body.source_id,
        scenario=body.scenario.strip(),
        actions=(body.actions or "").strip() or None,
        expected=(body.expected or "").strip() or None,
    )
    db.add(d)
    await db.flush()
    await db.refresh(d)
    return _out(d)


@router.patch("/{decision_id}")
async def update_decision(
    decision_id: uuid.UUID,
    body: DecisionPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    d = await _own_decision(db, user, decision_id)
    sent = body.model_fields_set
    if "scenario" in sent and body.scenario is not None:
        d.scenario = body.scenario.strip()
    if "actions" in sent:
        d.actions = (body.actions or "").strip() or None
    if "expected" in sent:
        d.expected = (body.expected or "").strip() or None
    if "outcome_note" in sent:
        d.outcome_note = (body.outcome_note or "").strip() or None
    if "outcome" in sent:
        new = body.outcome or None
        if new != d.outcome:
            d.outcome = new
            d.outcome_at = datetime.now(UTC) if new else None
    await db.flush()
    await db.refresh(d)
    return _out(d)


@router.delete("/{decision_id}", status_code=204)
async def delete_decision(
    decision_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    d = await _own_decision(db, user, decision_id)
    await db.delete(d)
    await db.flush()


# ── Переходы Метода 3 (только администратор) ─────────────────────────────────

async def m3_transitions(db: AsyncSession) -> list[dict]:
    """Все пары «прошлый замер → следующий» по компаниям Метода 3.

    Пара строится так же, как раздел «Динамика» отчёта (m3_service.dynamics_for):
    тот же пользователь, то же название компании без учёта регистра и
    пробелов, ближайший предыдущий расчёт. Направления сопоставляются по
    названию.
    """
    ports = (await db.execute(
        select(M3Portfolio, User.email)
        .join(User, User.id == M3Portfolio.user_id)
        .where(M3Portfolio.status == "calculated", M3Portfolio.deleted_at.is_(None),
               M3Portfolio.calculated_at.is_not(None))
        .order_by(M3Portfolio.calculated_at)
    )).all()

    chains: dict[tuple, list] = {}
    for p, email in ports:
        key = (p.user_id, (p.company_name or "").strip().lower())
        if not key[1]:
            continue
        chains.setdefault(key, []).append((p, email))
    pairs = [(c[i - 1], c[i]) for c in chains.values() for i in range(1, len(c))]
    if not pairs:
        return []

    ids = {x[0].id for pr in pairs for x in pr}
    results: dict[uuid.UUID, dict[str, tuple]] = {}
    for r, name in (await db.execute(
        select(M3Result, M3Object.name)
        .join(M3Object, M3Object.id == M3Result.object_id)
        .where(M3Result.portfolio_id.in_(ids))
    )).all():
        results.setdefault(r.portfolio_id, {})[name.strip().lower()] = (name, r)

    # Намерение: выполненные шаги чек-листа прошлого замера.
    prev_ids = {pr[0][0].id for pr in pairs}
    intents: dict[tuple, dict[str, list[int]]] = {}
    for s in (await db.execute(
        select(M3ChecklistStep)
        .where(M3ChecklistStep.portfolio_id.in_(prev_ids), M3ChecklistStep.done.is_(True),
               M3ChecklistStep.line.is_not(None), M3ChecklistStep.object_id.is_not(None))
    )).scalars():
        kind = "strengthen" if s.step_type == "route" else "hold" if s.step_type == "hold" else None
        if kind:
            intents.setdefault((s.portfolio_id, s.object_id), {}).setdefault(kind, []).append(s.line)

    decisions: dict[uuid.UUID, list[dict]] = {}
    for d in (await db.execute(
        select(Decision).where(Decision.method == "m3", Decision.source_id.in_(prev_ids))
        .order_by(Decision.created_at)
    )).scalars():
        decisions.setdefault(d.source_id, []).append(_out(d))

    out = []
    for (prev, email), (now, _) in pairs:
        before, after = results.get(prev.id, {}), results.get(now.id, {})
        directions = []
        for key, (name, r_now) in after.items():
            hit = before.get(key)
            if hit is None:
                continue
            r_prev = hit[1]
            directions.append({
                "name": name,
                **classify(
                    {"scores": scores_of(r_prev), "symbols": r_prev.symbols,
                     "target_lines": r_prev.target_lines or [], "risk_lines": r_prev.risk_lines or []},
                    {"scores": scores_of(r_now), "symbols": r_now.symbols},
                    intents.get((prev.id, r_prev.object_id)),
                ),
            })
        directions.sort(key=lambda x: x["name"].lower())
        out.append({
            "user_email": email,
            "company_name": now.company_name,
            "previous": {"id": str(prev.id), "calculated_at": prev.calculated_at.isoformat()},
            "current": {"id": str(now.id), "calculated_at": now.calculated_at.isoformat(),
                        "is_followup": now.is_followup},
            "directions": directions,
            "added": sorted(after[k][0] for k in after.keys() - before.keys()),
            "removed": sorted(before[k][0] for k in before.keys() - after.keys()),
            "decisions": decisions.get(prev.id, []),
        })
    out.sort(key=lambda x: x["current"]["calculated_at"], reverse=True)
    return out


@admin_router.get("")
async def admin_m3_transitions(db: AsyncSession = Depends(get_db)):
    return {"items": await m3_transitions(db)}
