# -*- coding: utf-8 -*-
"""Временный бесплатный доступ: активные гранты и остаток по ним.

Расход не хранится счётчиком, а считается по assessments.grant_id — как
платные кредиты в payments.calculate_credits. Следствия:
  * рефанд (completed -> draft) возвращает квоту гранта автоматически;
  * счётчик не может разойтись с фактом;
  * остаётся та же теоретическая гонка, что и в платном контуре (два
    параллельных запроса могут дать один лишний бесплатный отчёт) —
    принято сознательно, распределённая блокировка при текущем масштабе
    дороже риска.

Статус гранта в БД не хранится: он производная от revoked_at, expires_at
и остатка. Крон на протухание не нужен.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccessGrant, Assessment

# Диагностика считается израсходованной в тех же статусах, что и в
# payments.calculate_credits — иначе платный и грантовый контуры разойдутся.
USED_STATUSES = ("completed", "paid")


async def _used_by_grant(db: AsyncSession, grant_ids: list[uuid.UUID]) -> dict:
    """{grant_id: сколько диагностик списано} одним запросом."""
    if not grant_ids:
        return {}
    rows = await db.execute(
        select(Assessment.grant_id, func.count(Assessment.id))
        .where(Assessment.grant_id.in_(grant_ids),
               Assessment.status.in_(USED_STATUSES))
        .group_by(Assessment.grant_id)
    )
    return {gid: cnt for gid, cnt in rows.all()}


async def active_grants(db: AsyncSession, user_id) -> list[tuple[AccessGrant, int]]:
    """[(грант, остаток)] — только действующие и с ненулевым остатком.

    Порядок: ближайший к истечению первым. Сгорающий ресурс тратим раньше
    бессрочного платного кредита.
    """
    now = datetime.now(timezone.utc)
    grants = (await db.execute(
        select(AccessGrant).where(
            AccessGrant.user_id == user_id,
            AccessGrant.revoked_at.is_(None),
            AccessGrant.starts_at <= now,
            AccessGrant.expires_at > now,
        ).order_by(AccessGrant.expires_at.asc())
    )).scalars().all()
    used = await _used_by_grant(db, [g.id for g in grants])
    out = []
    for g in grants:
        remaining = g.quota - used.get(g.id, 0)
        if remaining > 0:
            out.append((g, remaining))
    return out


async def grant_credits(db: AsyncSession, user_id) -> int:
    """Сколько бесплатных диагностик доступно пользователю прямо сейчас."""
    return sum(remaining for _, remaining in await active_grants(db, user_id))


async def nearest_expiry(db: AsyncSession, user_id) -> datetime | None:
    """Дата окончания ближайшего сгорающего гранта — для плашки в кабинете."""
    items = await active_grants(db, user_id)
    return items[0][0].expires_at if items else None


async def pick_grant(db: AsyncSession, user_id) -> AccessGrant | None:
    """Грант, которым будет оплачена следующая диагностика (или None)."""
    items = await active_grants(db, user_id)
    return items[0][0] if items else None


async def states(db: AsyncSession, grants: list[AccessGrant]) -> dict:
    """{grant_id: {used, remaining, status}} одним запросом — для админки.

    status: revoked | expired | used_up | active. Приоритет проверок важен:
    отозванный просроченный грант показываем как revoked (это действие
    администратора, а не естественное истечение).
    """
    now = datetime.now(timezone.utc)
    used = await _used_by_grant(db, [g.id for g in grants])
    result = {}
    for g in grants:
        u = used.get(g.id, 0)
        if g.revoked_at is not None:
            status = "revoked"
        elif g.expires_at <= now:
            status = "expired"
        elif u >= g.quota:
            status = "used_up"
        elif g.starts_at > now:
            status = "pending"
        else:
            status = "active"
        result[g.id] = {"used": u, "remaining": max(0, g.quota - u), "status": status}
    return result


async def grant_state(db: AsyncSession, grant: AccessGrant) -> dict:
    return (await states(db, [grant]))[grant.id]
