# -*- coding: utf-8 -*-
"""
Email-напоминания (app/jobs/reminders.py). Письма замоканы; проверяем отбор,
порог и идемпотентность. Подписки больше нет: напоминание уходит всем
владельцам компаний, у которых давно не было диагностики.
"""
import uuid
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.jobs import reminders
from app.models import Assessment, Company, User


@pytest.fixture
def mock_emails(monkeypatch):
    import app.email as email_mod
    m = {"repeat": AsyncMock(return_value=None)}
    monkeypatch.setattr(email_mod, "send_repeat_diagnostic_email", m["repeat"])
    return m


@pytest.fixture(autouse=True)
def isolated_reminder_settings(monkeypatch, tmp_path):
    """Джоб читает порог из volume: тест не должен зависеть от прода."""
    from app import reminders_settings
    monkeypatch.setattr(reminders_settings, "SETTINGS_FILE",
                        tmp_path / "reminders_settings.json")


def _now():
    return datetime.now(UTC)


async def _mk_user(db) -> User:
    u = User(email=f"rem-{uuid.uuid4()}@t.t", full_name="Тест", role="user")
    db.add(u)
    await db.flush()
    return u


async def _company(db, user_id, name="Компания") -> Company:
    c = Company(user_id=user_id, name=name)
    db.add(c)
    await db.flush()
    return c


async def _assessment(db, user_id, company_id, days_ago: int,
                      status="completed") -> Assessment:
    a = Assessment(
        user_id=user_id,
        company_id=company_id,
        status=status,
        method="method1",
        created_at=_now() - timedelta(days=days_ago),
    )
    db.add(a)
    await db.flush()
    return a


@pytest.mark.asyncio
async def test_sends_after_threshold_and_is_idempotent(db_session, mock_emails):
    u = await _mk_user(db_session)
    c = await _company(db_session, u.id, "A")
    await _assessment(db_session, u.id, c.id, days_ago=100)
    assert await reminders.run_repeat_reminders(db_session) == 1
    mock_emails["repeat"].assert_awaited_once()
    assert c.repeat_reminder_sent_at is not None
    assert await reminders.run_repeat_reminders(db_session) == 0


@pytest.mark.asyncio
async def test_no_subscription_required(db_session, mock_emails):
    """Раньше письмо уходило только подписчикам, теперь всем."""
    u = await _mk_user(db_session)
    c = await _company(db_session, u.id, "B")
    await _assessment(db_session, u.id, c.id, days_ago=100)
    assert await reminders.run_repeat_reminders(db_session) == 1


@pytest.mark.asyncio
async def test_skips_recent_diagnostic(db_session, mock_emails):
    u = await _mk_user(db_session)
    c = await _company(db_session, u.id, "C")
    await _assessment(db_session, u.id, c.id, days_ago=30)
    assert await reminders.run_repeat_reminders(db_session) == 0


@pytest.mark.asyncio
async def test_ignores_inactive_user(db_session, mock_emails):
    u = await _mk_user(db_session)
    u.is_active = False
    c = await _company(db_session, u.id, "D")
    await _assessment(db_session, u.id, c.id, days_ago=100)
    await db_session.flush()
    assert await reminders.run_repeat_reminders(db_session) == 0


@pytest.mark.asyncio
async def test_threshold_comes_from_argument(db_session, mock_emails):
    """Порог задаётся в админке и передаётся джобом аргументом."""
    u = await _mk_user(db_session)
    c = await _company(db_session, u.id, "E")
    await _assessment(db_session, u.id, c.id, days_ago=40)
    assert await reminders.run_repeat_reminders(db_session, days=90) == 0
    assert await reminders.run_repeat_reminders(db_session, days=30) == 1


@pytest.mark.asyncio
async def test_rearms_after_new_diagnostic(db_session, mock_emails):
    u = await _mk_user(db_session)
    c = await _company(db_session, u.id, "F")
    await _assessment(db_session, u.id, c.id, days_ago=200)
    c.repeat_reminder_sent_at = _now() - timedelta(days=150)
    await db_session.flush()
    assert await reminders.run_repeat_reminders(db_session) == 0
    await _assessment(db_session, u.id, c.id, days_ago=100)
    assert await reminders.run_repeat_reminders(db_session) == 1
