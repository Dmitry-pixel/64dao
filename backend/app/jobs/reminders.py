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
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models import Company, Assessment, User
from app.config import get_settings
from app import email as email_mod
from app import reminders_settings

logger = logging.getLogger("reminders")
settings = get_settings()


async def run_repeat_reminders(session: AsyncSession,
                               days: int | None = None) -> int:
    """«Пора повторить» через N дней после последней диагностики компании.
    Авто-перевзвод: при новой диагностике last_at > sent_at снова сработает.
    диагностике last_at > sent_at → снова сработает."""
    now = datetime.now(timezone.utc)
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
               Assessment.company_id.isnot(None))
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
    rep = 0
    async with AsyncSessionLocal() as session:
        if cfg["repeat_enabled"]:
            rep = await run_repeat_reminders(session, cfg["repeat_days"])
    logger.info("reminders done: repeat=%d", rep)


if __name__ == "__main__":
    asyncio.run(main())
