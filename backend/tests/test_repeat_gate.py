# -*- coding: utf-8 -*-
"""
Право на одну бесплатную повторную диагностику.

Счётчик живёт на первичной диагностике компании. Подписки больше нет:
повтор входит в стоимость основной диагностики и доступен один раз.
"""
import pytest
from sqlalchemy import select

from app.models import Assessment

VALID = "AABABA"
FINANCE = {f"{b}.{p}": 3 for b in range(1, 7) for p in range(1, 5)}


def _payload(**ov) -> dict:
    p = {
        "method1_answers": {"goal": "A", "strategy": "B"},
        "method1_combination": VALID,
        "method2_data": None,
        "finance_answers": FINANCE,
        "company_name": "Гейт Ко",
        "status": "completed",
    }
    p.update(ov)
    return p


async def _post(client, name, status="completed"):
    return await client.post(
        "/api/assessments", json=_payload(company_name=name, status=status))


@pytest.mark.asyncio
async def test_first_diagnostic_allowed(auth_client):
    r = await _post(auth_client, "Первая")
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_one_followup_allowed_second_refused(auth_client):
    name = "Повтор Ко"
    assert (await _post(auth_client, name)).status_code == 200
    assert (await _post(auth_client, name)).status_code == 200
    r3 = await _post(auth_client, name)
    assert r3.status_code == 403, r3.text
    assert "один раз" in r3.json()["detail"]


@pytest.mark.asyncio
async def test_followup_is_linked_and_right_is_spent(auth_client, db_session):
    name = "Связь Ко"
    assert (await _post(auth_client, name)).status_code == 200
    assert (await _post(auth_client, name)).status_code == 200
    db_session.expire_all()
    rows = (await db_session.execute(
        select(Assessment)
        .where(Assessment.company_name == name)
        .order_by(Assessment.created_at)
    )).scalars().all()
    assert len(rows) == 2
    primary, repeat = rows
    assert primary.is_followup is False
    assert primary.followup_allowed == 1
    assert primary.followup_used == 1
    assert repeat.is_followup is True
    assert repeat.parent_assessment_id == primary.id


@pytest.mark.asyncio
async def test_draft_does_not_spend_the_right(auth_client):
    """Брошенный на середине повтор не должен сжигать возможность."""
    name = "Черновик Ко"
    assert (await _post(auth_client, name)).status_code == 200
    d = await _post(auth_client, name, status="draft")
    assert d.status_code == 200, d.text
    r = await _post(auth_client, name)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_admin_is_not_limited(admin_client):
    name = "Админ Ко"
    for _ in range(3):
        r = await _post(admin_client, name)
        assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_companies_are_independent(auth_client):
    for name in ("Альфа", "Бета"):
        assert (await _post(auth_client, name)).status_code == 200
        assert (await _post(auth_client, name)).status_code == 200
