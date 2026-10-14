# -*- coding: utf-8 -*-
"""Письмо «пора повторить» ведёт к журналу решений под последним отчётом."""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app import email as email_mod
from app.email_templates_store import DEFAULT_TEMPLATES, render
from app.jobs import reminders
from app.m3_models import M3Portfolio
from app.m4_models import M4Run
from app.models import Assessment, Company, User


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    from app import reminders_settings
    monkeypatch.setattr(reminders_settings, "SETTINGS_FILE", tmp_path / "reminders_settings.json")


def ago(days):
    return datetime.now(UTC) - timedelta(days=days)


async def _user_company(db, name="Альфа"):
    u = User(email=f"d-{uuid.uuid4()}@t.t", full_name="Тест", role="user")
    db.add(u)
    await db.flush()
    c = Company(user_id=u.id, name=name)
    db.add(c)
    await db.flush()
    return u, c


# ── Текст абзаца ─────────────────────────────────────────────────────────────

def test_decisions_part_links_to_anchor():
    html = email_mod.decisions_part("/report/abc")
    assert "/report/abc#decision-log\"" in html
    assert "журнал решений" in html
    assert email_mod.decisions_part(None) == ""


def test_default_templates_carry_variable():
    for key in ("repeat_diagnostic", "repeat_m3", "repeat_m4"):
        assert "{decisions_part}" in DEFAULT_TEMPLATES[key]["body_html"]
        _, body = render(key, {"decisions_part": "<p>X</p>"})
        assert "<p>X</p>" in body and "{decisions_part}" not in body


# ── Какая ссылка уходит в письмо ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_m1_links_latest_method1_report(db_session, monkeypatch):
    mail = AsyncMock(return_value=None)
    monkeypatch.setattr(email_mod, "send_repeat_diagnostic_email", mail)
    u, c = await _user_company(db_session)
    old = Assessment(user_id=u.id, company_id=c.id, status="completed", method="method1", created_at=ago(200))
    new = Assessment(user_id=u.id, company_id=c.id, status="completed", method="method1", created_at=ago(120))
    m2 = Assessment(user_id=u.id, company_id=c.id, status="completed", method="method2", created_at=ago(100))
    db_session.add_all([old, new, m2])
    await db_session.flush()
    assert await reminders.run_repeat_reminders(db_session, days=90) == 1
    assert mail.call_args.kwargs["report_path"] == f"/report/{new.id}"


@pytest.mark.asyncio
async def test_m1_without_method1_report_has_no_link(db_session, monkeypatch):
    mail = AsyncMock(return_value=None)
    monkeypatch.setattr(email_mod, "send_repeat_diagnostic_email", mail)
    u, c = await _user_company(db_session)
    db_session.add(Assessment(user_id=u.id, company_id=c.id, status="completed", method="method2", created_at=ago(120)))
    await db_session.flush()
    assert await reminders.run_repeat_reminders(db_session, days=90) == 1
    assert mail.call_args.kwargs["report_path"] is None


@pytest.mark.asyncio
async def test_m3_and_m4_link_their_reports(db_session, monkeypatch):
    mail = AsyncMock(return_value=None)
    monkeypatch.setattr(email_mod, "send_repeat_method_email", mail)
    u, c = await _user_company(db_session)
    p = M3Portfolio(user_id=u.id, company_name="Альфа", status="calculated", calculated_at=ago(120))
    r = M4Run(user_id=u.id, company_id=c.id, mode="full", status="calculated", calculated_at=ago(120))
    db_session.add_all([p, r])
    await db_session.flush()
    assert await reminders.run_m3_repeat_reminders(db_session, days=90) == 1
    assert mail.call_args.kwargs["report_path"] == f"/report/m3/{p.id}"
    assert await reminders.run_m4_repeat_reminders(db_session, days=90) == 1
    assert mail.call_args.kwargs["report_path"] == f"/m4/{r.id}/result"
