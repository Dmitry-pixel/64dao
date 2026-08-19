# -*- coding: utf-8 -*-
"""
Компании и повторная диагностика (роадмап 3.1, PR2): create привязывает/создаёт
компанию; повтор с тем же именем переиспользует её; company_id наследуется;
GET /api/companies.
"""
import uuid

import pytest
from sqlalchemy import func, select

from app.models import Assessment, Company

_FIN = {f"{b}.{q}": 3 for b in range(1, 7) for q in range(1, 5)}


def _payload(**ov):
    p = {
        "method1_answers": {"goal": "A", "strategy": "B"},
        "method1_combination": "AABBAB",
        "method2_data": None,
        "finance_answers": _FIN,
        "company_name": "Акме",
        "status": "completed",
    }
    p.update(ov)
    return p


@pytest.mark.asyncio
async def test_create_creates_and_links_company(auth_client, test_user, db_session):
    r = await auth_client.post("/api/assessments", json=_payload())
    assert r.status_code == 200, r.text
    aid = r.json()["id"]

    comp = await db_session.scalar(
        select(Company).where(Company.user_id == test_user.id, Company.name == "Акме"))
    assert comp is not None
    a = await db_session.scalar(select(Assessment).where(Assessment.id == aid))
    assert a.company_id == comp.id


@pytest.mark.asyncio
async def test_repeat_same_name_reuses_company(auth_client, test_user, db_session):
    await auth_client.post("/api/assessments", json=_payload(company_name="Реюз"))
    await auth_client.post("/api/assessments", json=_payload(company_name="Реюз"))
    companies = (await db_session.execute(
        select(Company).where(Company.user_id == test_user.id, Company.name == "Реюз"))).scalars().all()
    assert len(companies) == 1
    cnt = await db_session.scalar(
        select(func.count(Assessment.id)).where(Assessment.company_id == companies[0].id))
    assert cnt == 2


@pytest.mark.asyncio
async def test_explicit_company_id_inherited(auth_client, test_user, db_session):
    await auth_client.post("/api/assessments", json=_payload(company_name="Явная"))
    comp = await db_session.scalar(
        select(Company).where(Company.user_id == test_user.id, Company.name == "Явная"))
    r2 = await auth_client.post("/api/assessments", json=_payload(company_name=None, company_id=str(comp.id)))
    assert r2.status_code == 200, r2.text
    a2 = await db_session.scalar(select(Assessment).where(Assessment.id == r2.json()["id"]))
    assert a2.company_id == comp.id


@pytest.mark.asyncio
async def test_foreign_company_id_404(auth_client):
    r = await auth_client.post("/api/assessments", json=_payload(company_id=str(uuid.uuid4())))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_empty_name_goes_to_default_company(auth_client, test_user, db_session):
    await auth_client.post("/api/assessments", json=_payload(company_name="   "))
    comp = await db_session.scalar(
        select(Company).where(Company.user_id == test_user.id, Company.name == "Без названия"))
    assert comp is not None


@pytest.mark.asyncio
async def test_list_companies_endpoint(auth_client):
    await auth_client.post("/api/assessments", json=_payload(company_name="Списочная"))
    r = await auth_client.get("/api/companies")
    assert r.status_code == 200
    names = {c["name"]: c for c in r.json()}
    assert "Списочная" in names
    assert names["Списочная"]["assessment_count"] >= 1
