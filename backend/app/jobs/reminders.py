# -*- coding: utf-8 -*-
"""
Email-напоминания (PR6). Запуск из host cron:
    docker compose exec -T backend python -m app.jobs.reminders
Идемпотентность — через колонки *_reminder_sent_at (миграция 014). Send-then-mark
с commit по элементу: at-least-once, дубль маловероятен. Планировщика в проде нет
(правило проекта) — триггерит host crontab, как backup/certbot.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import email as email_mod
from app import reminders_settings
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.m3_models import M3Portfolio
from app.m4_models import M4Run
from app.models import Assessment, Company, User

logger = logging.getLogger("reminders")
settings = get_settings()


async def run_repeat_reminders(session: AsyncSession,
                               days: int | None = None) -> int:
    """«Пора повторить» через N дней после последней диагностики компании.
    Авто-перевзвод: при новой диагностике last_at > sent_at снова сработает.
    диагностике last_at > sent_at → снова сработает."""
    now = datetime.now(UTC)
    # Порог задаётся в админке; аргумент оставлен для тестов.
    if days is None:
        days = reminders_settings.read()["repeat_days"]
    threshold = now - timedelta(days=days)
    latest_sq = (
        select(
            Assessment.company_id.label("cid"),
            func.max(Assessment.created_at).label("last_at"),
        )
        .where(Assessment.status.in_(("completed", "paid")),
               Assessment.company_id.isnot(None),
               # Удалённая диагностика для пользователя не существует —
               # напоминать о ней нельзя.
               Assessment.deleted_at.is_(None))
        .group_by(Assessment.company_id)
        .subquery()
    )
    rows = (await session.execute(
        select(Company, User, latest_sq.c.last_at)
        .join(latest_sq, latest_sq.c.cid == Company.id)
        .join(User, User.id == Company.user_id)
        .where(
            User.is_active.is_(True),
            latest_sq.c.last_at <= threshold,
            or_(
                Company.repeat_reminder_sent_at.is_(None),
                Company.repeat_reminder_sent_at < latest_sq.c.last_at,
            ),
        )
    )).all()
    sent = 0
    for company, user, last_at in rows:
        days_since = max(1, (now - last_at).days)
        try:
            await email_mod.send_repeat_diagnostic_email(
                user.email, user.full_name, company.name, days_since)
        except Exception:
            logger.exception("repeat reminder failed: user=%s company=%s", user.id, company.id)
            continue
        company.repeat_reminder_sent_at = now
        await session.commit()
        sent += 1
    return sent


async def _send_latest(session: AsyncSession, key: str, items, company_of, days: int) -> int:
    """Общий ход для Методов 3 и 4: по каждой компании берётся последняя
    рассчитанная диагностика; письмо уходит, если с неё прошло не меньше
    days дней и по ней письма ещё не было. Отметка ставится на эту
    диагностику, поэтому новая диагностика компании взводит напоминание
    заново — как у Метода 1.

    followup — у компании есть неиспользованный повтор: тогда в письме
    фраза «повтор входит в стоимость»."""
    now = datetime.now(UTC)
    threshold = now - timedelta(days=days)
    latest: dict = {}
    followup: dict = {}
    for item, user in items:
        k = (item.user_id, company_of(item))
        if not k[1]:
            continue
        at = item.calculated_at or item.created_at
        if k not in latest or at > (latest[k][0].calculated_at or latest[k][0].created_at):
            latest[k] = (item, user)
        if not item.is_followup and item.followup_used < item.followup_allowed:
            followup[k] = True
    sent = 0
    for k, (item, user) in latest.items():
        at = item.calculated_at or item.created_at
        if at > threshold or item.repeat_reminder_sent_at is not None:
            continue
        name = getattr(item, "company_name", None) or getattr(item, "_company_name", None)
        try:
            await email_mod.send_repeat_method_email(
                key, user.email, user.full_name, name, max(1, (now - at).days), followup.get(k, False))
        except Exception:
            logger.exception("%s reminder failed: user=%s item=%s", key, user.id, item.id)
            continue
        item.repeat_reminder_sent_at = now
        await session.commit()
        sent += 1
    return sent


async def run_m3_repeat_reminders(session: AsyncSession, days: int | None = None) -> int:
    """Метод 3: компания — это название портфеля (к companies портфель не
    привязан), поэтому группировка по названию без учёта регистра."""
    if days is None:
        days = reminders_settings.read()["repeat_days"]
    rows = (await session.execute(
        select(M3Portfolio, User)
        .join(User, User.id == M3Portfolio.user_id)
        .where(User.is_active.is_(True), M3Portfolio.status == "calculated",
               M3Portfolio.deleted_at.is_(None))
    )).all()
    return await _send_latest(session, "repeat_m3", rows,
                              lambda p: (p.company_name or "").strip().lower(), days)


async def run_m4_repeat_reminders(session: AsyncSession, days: int | None = None) -> int:
    """Метод 4: только полная диагностика — экспресс бесплатный и один на
    аккаунт, повторять его нечем."""
    if days is None:
        days = reminders_settings.read()["repeat_days"]
    rows = (await session.execute(
        select(M4Run, User, Company.name)
        .join(User, User.id == M4Run.user_id)
        .join(Company, Company.id == M4Run.company_id)
        .where(User.is_active.is_(True), M4Run.status == "calculated", M4Run.mode == "full",
               M4Run.deleted_at.is_(None))
    )).all()
    items = []
    for run, user, cname in rows:
        run._company_name = cname
        items.append((run, user))
    return await _send_latest(session, "repeat_m4", items, lambda r: r.company_id, days)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if not settings.reminders_enabled:
        logger.info("reminders disabled (REMINDERS_ENABLED=false) — skip")
        return
    cfg = reminders_settings.read()
    if not cfg["enabled"]:
        logger.info("reminders disabled in admin — skip")
        return
    rep = rep_m3 = rep_m4 = 0
    async with AsyncSessionLocal() as session:
        if cfg["repeat_enabled"]:
            rep = await run_repeat_reminders(session, cfg["repeat_days"])
            rep_m3 = await run_m3_repeat_reminders(session, cfg["repeat_days"])
            rep_m4 = await run_m4_repeat_reminders(session, cfg["repeat_days"])
    logger.info("reminders done: repeat=%d m3=%d m4=%d", rep, rep_m3, rep_m4)


if __name__ == "__main__":
    asyncio.run(main())
