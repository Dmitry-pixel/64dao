# -*- coding: utf-8 -*-
"""
PR5: гейт подписки на повтор диагностики (create_assessment).
Первая диагностика компании — всегда; повтор (≥1 завершённой) — только
активному подписчику или админу.
"""
import pytest
from app import subscription_service as subs

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


@pytest.mark.asyncio
async def test_first_diagnostic_allowed(auth_client):
    r = await auth_client.post("/api/assessments", json=_payload(company_name="Первая"))
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_repeat_blocked_without_subscription(auth_client):
    r1 = await auth_client.post("/api/assessments", json=_payload(company_name="Повтор Ко"))
    assert r1.status_code == 200, r1.text
    r2 = await auth_client.post("/api/assessments", json=_payload(company_name="Повтор Ко"))
    assert r2.status_code == 403, r2.text
    assert "подписк" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_repeat_allowed_with_subscription(auth_client, test_user, db_session):
    await subs.grant(db_session, test_user.id, days=30)
    r1 = await auth_client.post("/api/assessments", json=_payload(company_name="Подписка Ко"))
    assert r1.status_code == 200, r1.text
    r2 = await auth_client.post("/api/assessments", json=_payload(company_name="Подписка Ко"))
    assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
async def test_admin_bypasses_gate(admin_client):
    r1 = await admin_client.post("/api/assessments", json=_payload(company_name="Админ Ко"))
    assert r1.status_code == 200, r1.text
    r2 = await admin_client.post("/api/assessments", json=_payload(company_name="Админ Ко"))
    assert r2.status_code == 200, r2.text
