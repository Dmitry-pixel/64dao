# -*- coding: utf-8 -*-
"""Метод 3: один бесплатный повтор, как у Методов 1 и 4.

Первичный портфель компании, оплаченный заказом (не грантом), даёт право на
один повтор без оплаты. Повтор переносит направления, но не ответы; отчёт
повтора сравнивает направления с прошлой диагностикой компании.
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app import m3_pdf
from app.m3_models import M3Portfolio
from app.routers.payments import revoke_order_access
from tests.test_m3_api import CONTROL_OBJECTS, M3, REPORTS, _fill, m3_on, seeded  # noqa: F401
from tests.test_m3_credits import _grant, _paid_order, enforce_on  # noqa: F401

COMPANY = "ООО Косметика"


async def _portfolio(client, company=COMPANY) -> dict:
    r = await client.post(f"{M3}/portfolios", json={"title": "Направления", "company_name": company,
                                                    "industry_id": 2})
    assert r.status_code == 201, r.text
    p = r.json()
    if not p["objects"]:
        r = await client.put(f"{M3}/portfolios/{p['id']}/objects", json={"objects": CONTROL_OBJECTS})
        assert r.status_code == 200, r.text
        p = r.json()
    return p


async def _calculated(client, company=COMPANY) -> dict:
    p = await _portfolio(client, company)
    await _fill(client, p)
    r = await client.post(f"{M3}/portfolios/{p['id']}/calculate")
    assert r.status_code == 200, r.text
    return p


async def _row(db, pid) -> M3Portfolio:
    return await db.scalar(select(M3Portfolio).where(M3Portfolio.id == pid))


@pytest.mark.asyncio
async def test_followup_free_once(auth_client, seeded, m3_on, db_session, test_user, enforce_on):
    order = await _paid_order(db_session, test_user, "m3")
    first = await _calculated(auth_client)
    primary = await _row(db_session, first["id"])
    assert primary.order_id == order.id and primary.followup_allowed == 1

    # регистр и пробелы в названии не мешают узнать компанию
    second = await _portfolio(auth_client, "  ооо косметика ")
    assert second["is_followup"] is True
    assert [o["name"] for o in second["objects"]] == [o["name"] for o in CONTROL_OBJECTS]
    await _fill(auth_client, second)
    assert (await auth_client.post(f"{M3}/portfolios/{second['id']}/calculate")).status_code == 200
    row = await _row(db_session, second["id"])
    assert row.is_followup and row.order_id is None and row.parent_portfolio_id == primary.id
    await db_session.refresh(primary)
    assert primary.followup_used == 1

    # третья — снова платная
    third = await _portfolio(auth_client)
    assert third["is_followup"] is False
    await _fill(auth_client, third)
    assert (await auth_client.post(f"{M3}/portfolios/{third['id']}/calculate")).status_code == 403


@pytest.mark.asyncio
async def test_grant_primary_gives_no_followup(auth_client, seeded, m3_on, db_session, test_user, enforce_on):
    await _grant(db_session, test_user, "m3")
    first = await _calculated(auth_client)
    assert (await _row(db_session, first["id"])).followup_allowed == 0
    assert (await _portfolio(auth_client))["is_followup"] is False


@pytest.mark.asyncio
async def test_followup_report_has_dynamics(auth_client, seeded, m3_on, db_session):
    first = await _calculated(auth_client)
    # В одной транзакции теста now() одинаков у обоих расчётов; в проде это
    # разные запросы. Сдвигаем первый расчёт в прошлое.
    row = await _row(db_session, first["id"])
    row.calculated_at = datetime(2026, 6, 1, tzinfo=UTC)
    await db_session.flush()
    second = await _calculated(auth_client)
    rep = (await auth_client.get(f"{REPORTS}/{second['id']}")).json()
    d = rep["dynamics"]
    assert d and d["previous"]["id"] == first["id"]
    assert len(d["directions"]) == len(CONTROL_OBJECTS) and d["removed"] == []
    assert all(x["before"] for x in d["directions"])
    assert rep["portfolio"]["is_followup"] is True
    first_rep = (await auth_client.get(f"{REPORTS}/{first['id']}")).json()
    assert first_rep["dynamics"] is None


@pytest.mark.asyncio
async def test_refund_closes_followup(auth_client, seeded, m3_on, db_session, test_user, enforce_on):
    order = await _paid_order(db_session, test_user, "m3")
    await _calculated(auth_client)
    second = await _calculated(auth_client)
    order.status = "refunded"
    revoked = await revoke_order_access(db_session, order)
    await db_session.flush()
    assert revoked["portfolios"] == 2
    assert (await _row(db_session, second["id"])).status == "filled"
    assert (await auth_client.get(f"{REPORTS}/{second['id']}")).status_code == 403


@pytest.mark.asyncio
async def test_companies_show_m3_repeat(auth_client, seeded, m3_on):
    await _calculated(auth_client)
    c = (await auth_client.get("/api/companies")).json()[0]
    assert c["m3_followup_available"] is True and c["m3_next_repeat_at"]
    await _calculated(auth_client)
    c = (await auth_client.get("/api/companies")).json()[0]
    assert c["m3_followup_available"] is False
    assert any(a["is_followup"] for a in c["assessments"] if a["method"] == "method3")


def test_pdf_dynamics_section():
    d = {
        "previous": {"id": "x", "calculated_at": datetime(2026, 6, 1, tzinfo=UTC)},
        "directions": [
            {"name": "Кремы", "before": {"cell_label": "сильная · низкая", "v_rank": 2},
             "now": {"cell_label": "сильная · высокая", "v_rank": 1},
             "cell_changed": True, "d_strength": 0.1, "d_attract": 0.35},
            {"name": "Мыло", "before": None, "now": {"cell_label": "слабая · низкая", "v_rank": 2},
             "cell_changed": False, "d_strength": None, "d_attract": None},
        ],
        "removed": ["Шампуни"],
        "sum_positions": {"before": 20, "now": 24},
    }
    html = m3_pdf.dynamics_section(d)
    for text in ("Что изменилось", "01.06.2026", "ячейка сменилась", "новое направление",
                 "Шампуни", "было 20, стало 24", "+0,35"):
        assert text in html, text
