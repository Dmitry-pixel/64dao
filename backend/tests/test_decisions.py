# -*- coding: utf-8 -*-
"""Журнал решений клиента и сводка переходов Метода 3 для администратора."""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.m3_models import M3ChecklistStep, M3Portfolio
from app.m3_transition import TYPE_TITLES
from app.models import Assessment, User
from tests.conftest import _set_auth_cookie
from tests.test_m3_api import CONTROL_OBJECTS, m3_on, seeded  # noqa: F401
from tests.test_m3_repeat import _calculated, _portfolio

API = "/api/decisions"
ADMIN = "/api/admin/m3-transitions"


async def _assessment(db, user, status="completed") -> Assessment:
    a = Assessment(user_id=user.id, status=status, method="method1", method1_combination="AAAAAA")
    db.add(a)
    await db.flush()
    return a


async def _other_user(db) -> User:
    u = User(id=uuid.uuid4(), email=f"other-{uuid.uuid4().hex[:8]}@example.com", role="user")
    db.add(u)
    await db.flush()
    return u


# ── Клиентский журнал ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_list_update_delete(auth_client, db_session, test_user):
    a = await _assessment(db_session, test_user)
    r = await auth_client.post(API, json={
        "method": "m1", "source_id": str(a.id),
        "scenario": "  Сценарий роста через партнёров ", "actions": "", "expected": "+20% выручки",
    })
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["scenario"] == "Сценарий роста через партнёров"
    assert d["actions"] is None and d["outcome"] is None

    data = (await auth_client.get(API, params={"method": "m1", "source_id": str(a.id)})).json()
    assert [x["id"] for x in data["items"]] == [d["id"]] and data["editable"] is True

    r = await auth_client.patch(f"{API}/{d['id']}", json={"outcome": "partial", "outcome_note": "Два партнёра из пяти"})
    assert r.status_code == 200
    assert r.json()["outcome"] == "partial" and r.json()["outcome_at"]

    r = await auth_client.patch(f"{API}/{d['id']}", json={"outcome": ""})
    assert r.json()["outcome"] is None and r.json()["outcome_at"] is None
    assert r.json()["outcome_note"] == "Два партнёра из пяти"   # не переданное поле не трогается

    assert (await auth_client.delete(f"{API}/{d['id']}")).status_code == 204
    assert (await auth_client.get(API, params={"method": "m1", "source_id": str(a.id)})).json()["items"] == []


@pytest.mark.asyncio
async def test_validation(auth_client, db_session, test_user):
    a = await _assessment(db_session, test_user)
    base = {"method": "m1", "source_id": str(a.id)}
    assert (await auth_client.post(API, json={**base, "scenario": ""})).status_code == 422
    assert (await auth_client.post(API, json={**base, "method": "m2", "scenario": "x"})).status_code == 422
    r = await auth_client.patch(f"{API}/{uuid.uuid4()}", json={"outcome": "maybe"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_draft_report_rejected(auth_client, db_session, test_user):
    a = await _assessment(db_session, test_user, status="draft")
    r = await auth_client.post(API, json={"method": "m1", "source_id": str(a.id), "scenario": "x"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_not_found(auth_client):
    r = await auth_client.post(API, json={"method": "m3", "source_id": str(uuid.uuid4()), "scenario": "x"})
    assert r.status_code == 404
    assert (await auth_client.delete(f"{API}/{uuid.uuid4()}")).status_code == 404


@pytest.mark.asyncio
async def test_foreign_report_is_hidden(client, db_session, test_user):
    a = await _assessment(db_session, test_user)
    _set_auth_cookie(client, test_user)
    d = (await client.post(API, json={"method": "m1", "source_id": str(a.id), "scenario": "x"})).json()

    _set_auth_cookie(client, await _other_user(db_session))
    assert (await client.get(API, params={"method": "m1", "source_id": str(a.id)})).status_code == 404
    r = await client.post(API, json={"method": "m1", "source_id": str(a.id), "scenario": "y"})
    assert r.status_code == 404
    assert (await client.patch(f"{API}/{d['id']}", json={"outcome": "done"})).status_code == 404
    assert (await client.delete(f"{API}/{d['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_admin_reads_but_cannot_write(client, db_session, test_user, test_admin):
    a = await _assessment(db_session, test_user)
    _set_auth_cookie(client, test_admin)
    data = (await client.get(API, params={"method": "m1", "source_id": str(a.id)})).json()
    assert data == {"items": [], "editable": False}
    r = await client.post(API, json={"method": "m1", "source_id": str(a.id), "scenario": "x"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_requires_login(client):
    r = await client.get(API, params={"method": "m1", "source_id": str(uuid.uuid4())})
    assert r.status_code == 401


# ── Переходы Метода 3 для администратора ─────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_transitions(client, seeded, m3_on, db_session, test_user, test_admin):
    _set_auth_cookie(client, test_user)
    first = await _calculated(client)
    row = await db_session.scalar(select(M3Portfolio).where(M3Portfolio.id == first["id"]))
    row.calculated_at = datetime(2026, 6, 1, tzinfo=UTC)
    # Клиент отметил шаг чек-листа и записал решение до повтора.
    step = (await db_session.execute(
        select(M3ChecklistStep).where(M3ChecklistStep.portfolio_id == row.id,
                                      M3ChecklistStep.line.is_not(None))
    )).scalars().first()
    assert step is not None
    step.done = True
    await db_session.flush()
    r = await client.post(API, json={"method": "m3", "source_id": first["id"], "scenario": "Фокус на маркетплейсах"})
    assert r.status_code == 201, r.text

    second = await _calculated(client)
    await _portfolio(client, "Другая компания")          # черновик без пары

    assert (await client.get(ADMIN)).status_code == 403

    _set_auth_cookie(client, test_admin)
    items = (await client.get(ADMIN)).json()["items"]
    assert len(items) == 1
    it = items[0]
    assert it["previous"]["id"] == first["id"] and it["current"]["id"] == second["id"]
    assert it["user_email"] == test_user.email
    assert len(it["directions"]) == len(CONTROL_OBJECTS) and it["added"] == [] and it["removed"] == []
    assert all(d["type"] in TYPE_TITLES for d in it["directions"])
    # Ответы те же: значимых смен нет.
    assert all(d["changed"] == [] for d in it["directions"])
    with_intent = [d for d in it["directions"] if d["intent"]["value"] != "нет данных"]
    assert len(with_intent) == 1
    assert [x["scenario"] for x in it["decisions"]] == ["Фокус на маркетплейсах"]


@pytest.mark.asyncio
async def test_admin_transitions_empty(admin_client):
    r = await admin_client.get(ADMIN)
    assert r.status_code == 200 and r.json() == {"items": []}
