# -*- coding: utf-8 -*-
"""
PR6: email-напоминания (app/jobs/reminders.py). Письма замоканы; проверяем
отбор, идемпотентность и гейт подписки на «пора повторить».
"""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from app.models import User, Subscription, Company, Assessment
from app.jobs import reminders


@pytest.fixture
def mock_emails(monkeypatch):
    import app.email as email_mod
    m = {"expiry": AsyncMock(return_value=None), "repeat": AsyncMock(return_value=None)}
    monkeypatch.setattr(email_mod, "send_subscription_expiry_email", m["expiry"])
    monkeypatch.setattr(email_mod, "send_repeat_diagnostic_email", m["repeat"])
    return m


@pytest.fixture(autouse=True)
def isolated_reminder_settings(monkeypatch, tmp_path):
    """Джоб читает порог из volume: тест не должен зависеть от прода.

    Без этого смена периодичности в админке ломала бы тесты, которые
    рассчитаны на порог 90 дней.
    """
    from app import reminders_settings
    monkeypatch.setattr(reminders_settings, "SETTINGS_FILE",
                        tmp_path / "reminders_settings.json")


def _now():
    return datetime.now(timezone.utc)


async def _mk_user(db) -> User:
    u = User(email=f"rem-{uuid.uuid4()}@t.t", full_name="Тест", role="user")
    db.add(u)
    await db.flush()
    return u


async def _grant(db, user_id, days_left: int) -> Subscription:
    now = _now()
    sub = Subscription(
        user_id=user_id,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=days_left),
        status="active",
    )
    db.add(sub)
    await db.flush()
    return sub


async def _company(db, user_id, name="Компания") -> Company:
    c = Company(user_id=user_id, name=name)
    db.add(c)
    await db.flush()
    return c


async def _assessment(db, user_id, company_id, days_ago: int, status="completed") -> Assessment:
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


# ── Expiry: за 14 дней до конца подписки ─────────────────────────────────────

@pytest.mark.asyncio
async def test_expiry_sends_within_window_and_is_idempotent(db_session, mock_emails):
    u = await _mk_user(db_session)
    sub = await _grant(db_session, u.id, days_left=10)  # в окне 14 дней
    n = await reminders.run_expiry_reminders(db_session)
    assert n == 1
    mock_emails["expiry"].assert_awaited_once()
    assert sub.expiry_reminder_sent_at is not None
    # повторный прогон — не дублирует
    n2 = await reminders.run_expiry_reminders(db_session)
    assert n2 == 0
    assert mock_emails["expiry"].await_count == 1


@pytest.mark.asyncio
async def test_expiry_skips_far_subscription(db_session, mock_emails):
    u = await _mk_user(db_session)
    await _grant(db_session, u.id, days_left=30)  # дальше окна
    n = await reminders.run_expiry_reminders(db_session)
    assert n == 0
    mock_emails["expiry"].assert_not_awaited()


@pytest.mark.asyncio
async def test_expiry_ignores_inactive_user(db_session, mock_emails):
    u = await _mk_user(db_session)
    u.is_active = False
    await _grant(db_session, u.id, days_left=10)
    await db_session.flush()
    n = await reminders.run_expiry_reminders(db_session)
    assert n == 0


# ── Repeat: «пора повторить» через N=90 дней ─────────────────────────────────

@pytest.mark.asyncio
async def test_repeat_sends_for_subscriber_and_is_idempotent(db_session, mock_emails):
    u = await _mk_user(db_session)
    await _grant(db_session, u.id, days_left=200)
    c = await _company(db_session, u.id, "A")
    await _assessment(db_session, u.id, c.id, days_ago=100)  # старше 90
    n = await reminders.run_repeat_reminders(db_session)
    assert n == 1
    mock_emails["repeat"].assert_awaited_once()
    assert c.repeat_reminder_sent_at is not None
    n2 = await reminders.run_repeat_reminders(db_session)
    assert n2 == 0


@pytest.mark.asyncio
async def test_repeat_gated_by_subscription(db_session, mock_emails):
    u = await _mk_user(db_session)  # без подписки
    c = await _company(db_session, u.id, "B")
    await _assessment(db_session, u.id, c.id, days_ago=100)
    n = await reminders.run_repeat_reminders(db_session)
    assert n == 0
    mock_emails["repeat"].assert_not_awaited()


@pytest.mark.asyncio
async def test_repeat_skips_recent_diagnostic(db_session, mock_emails):
    u = await _mk_user(db_session)
    await _grant(db_session, u.id, days_left=200)
    c = await _company(db_session, u.id, "C")
    await _assessment(db_session, u.id, c.id, days_ago=30)  # свежее 90
    n = await reminders.run_repeat_reminders(db_session)
    assert n == 0


@pytest.mark.asyncio
async def test_repeat_rearms_after_new_diagnostic(db_session, mock_emails):
    u = await _mk_user(db_session)
    await _grant(db_session, u.id, days_left=200)
    c = await _company(db_session, u.id, "D")
    await _assessment(db_session, u.id, c.id, days_ago=200)
    # уже напоминали 150 дней назад (по старой диагностике)
    c.repeat_reminder_sent_at = _now() - timedelta(days=150)
    await db_session.flush()
    n = await reminders.run_repeat_reminders(db_session)
    assert n == 0  # новее старой диагностики ничего нет
    # новая диагностика 100 дней назад (снова старше порога) → перевзвод
    await _assessment(db_session, u.id, c.id, days_ago=100)
    n2 = await reminders.run_repeat_reminders(db_session)
    assert n2 == 1
