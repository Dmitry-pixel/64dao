# -*- coding: utf-8 -*-
"""Напоминания о повторе Методов 3 и 4: по последней диагностике компании,
один раз, новая диагностика взводит заново. Письма замоканы."""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.jobs import reminders
from app.m3_models import M3Portfolio
from app.m4_models import M4Run
from app.models import Company, User


@pytest.fixture
def mail(monkeypatch):
    import app.email as email_mod
    m = AsyncMock(return_value=None)
    monkeypatch.setattr(email_mod, "send_repeat_method_email", m)
    return m


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    from app import reminders_settings
    monkeypatch.setattr(reminders_settings, "SETTINGS_FILE", tmp_path / "reminders_settings.json")


def ago(days):
    return datetime.now(UTC) - timedelta(days=days)


async def _user(db):
    u = User(email=f"r-{uuid.uuid4()}@t.t", full_name="Тест", role="user")
    db.add(u)
    await db.flush()
    return u


async def _portfolio(db, user, name, days, **kw):
    p = M3Portfolio(user_id=user.id, company_name=name, status="calculated", calculated_at=ago(days), **kw)
    db.add(p)
    await db.flush()
    return p


async def _run(db, user, company, days, mode="full", **kw):
    r = M4Run(user_id=user.id, company_id=company.id, mode=mode, status="calculated",
              calculated_at=ago(days), **kw)
    db.add(r)
    await db.flush()
    return r


@pytest.mark.asyncio
async def test_m3_once_per_latest(db_session, mail):
    u = await _user(db_session)
    await _portfolio(db_session, u, "Альфа", 200)
    latest = await _portfolio(db_session, u, " альфа", 100, followup_allowed=1)
    assert await reminders.run_m3_repeat_reminders(db_session, days=90) == 1
    key, email, _name, company, days, followup = mail.call_args.args
    assert key == "repeat_m3" and email == u.email and company == " альфа" and followup is True
    assert latest.repeat_reminder_sent_at is not None
    assert await reminders.run_m3_repeat_reminders(db_session, days=90) == 0
    # новая диагностика снимает напоминание до своего срока
    await _portfolio(db_session, u, "Альфа", 10)
    assert await reminders.run_m3_repeat_reminders(db_session, days=90) == 0


@pytest.mark.asyncio
async def test_m3_skips_recent_and_deleted(db_session, mail):
    u = await _user(db_session)
    await _portfolio(db_session, u, "Бета", 30)
    await _portfolio(db_session, u, "Гамма", 200, deleted_at=ago(1))
    assert await reminders.run_m3_repeat_reminders(db_session, days=90) == 0


@pytest.mark.asyncio
async def test_m4_full_only(db_session, mail):
    u = await _user(db_session)
    c = Company(user_id=u.id, name="Дельта")
    db_session.add(c)
    await db_session.flush()
    await _run(db_session, u, c, 200, mode="express")
    assert await reminders.run_m4_repeat_reminders(db_session, days=90) == 0
    await _run(db_session, u, c, 120)
    assert await reminders.run_m4_repeat_reminders(db_session, days=90) == 1
    key, _e, _n, company, _d, followup = mail.call_args.args
    assert key == "repeat_m4" and company == "Дельта" and followup is False
    assert await reminders.run_m4_repeat_reminders(db_session, days=90) == 0


def test_templates_exist():
    from app.email_templates_store import DEFAULT_TEMPLATES, render
    for key in ("repeat_m3", "repeat_m4"):
        subject, body = render(key, {"company_part": " компании «А»", "days_since": 95, "name_part": "",
                                     "followup_part": " Повтор входит.", "app_url": "https://x"})
        assert subject and "95" in body and "Повтор входит." in body and "https://x/companies" in body
        assert DEFAULT_TEMPLATES[key]["description"]
