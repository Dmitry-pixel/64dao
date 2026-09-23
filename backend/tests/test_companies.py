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


@pytest.fixture
def isolated_reminder_settings(monkeypatch, tmp_path):
    """Срок повтора берётся из volume: тест не должен зависеть от прода."""
    from app import reminders_settings
    monkeypatch.setattr(reminders_settings, "SETTINGS_FILE", tmp_path / "reminders_settings.json")


@pytest.mark.asyncio
async def test_deleted_assessments_are_not_listed(auth_client, isolated_reminder_settings):
    """Удалённая диагностика исчезает из «Моих компаний», а компания, у
    которой удалено всё, не показывается вовсе."""
    r1 = await auth_client.post("/api/assessments", json=_payload(company_name="Удаляемая"))
    r2 = await auth_client.post("/api/assessments", json=_payload(company_name="Остаётся"))
    await auth_client.post("/api/assessments", json=_payload(company_name="Остаётся"))
    assert (await auth_client.delete(f"/api/assessments/{r1.json()['id']}")).status_code in (200, 204)
    assert (await auth_client.delete(f"/api/assessments/{r2.json()['id']}")).status_code in (200, 204)

    names = {c["name"]: c for c in (await auth_client.get("/api/companies")).json()}
    assert "Удаляемая" not in names
    assert names["Остаётся"]["assessment_count"] == 1
    assert len(names["Остаётся"]["assessments"]) == 1


@pytest.mark.asyncio
async def test_drafts_are_not_counted(auth_client, isolated_reminder_settings):
    await auth_client.post("/api/assessments", json=_payload(company_name="Черновик", status="draft"))
    names = {c["name"] for c in (await auth_client.get("/api/companies")).json()}
    assert "Черновик" not in names


@pytest.mark.asyncio
async def test_company_shows_period_and_repeat_date(auth_client, isolated_reminder_settings):
    from datetime import datetime, timedelta

    await auth_client.post("/api/assessments", json=_payload(company_name="Сроки"))
    c = {x["name"]: x for x in (await auth_client.get("/api/companies")).json()}["Сроки"]
    assert c["repeat_days"] == 90
    latest = datetime.fromisoformat(c["latest_at"])
    assert datetime.fromisoformat(c["next_repeat_at"]) == latest + timedelta(days=90)
    assert c["first_at"] == c["latest_at"]
    assert c["followup_available"] is True
    assert c["assessments"][0]["method"] == "method1"


@pytest.mark.asyncio
async def test_method3_portfolios_join_company_by_name(auth_client, test_user, db_session,
                                                       isolated_reminder_settings):
    """Метод 3 к компаниям не привязан: рассчитанный портфель попадает в
    компанию с тем же названием, иначе — в отдельную строку без id.
    Черновик портфеля не показывается."""
    from app.m3_models import M3Portfolio

    await auth_client.post("/api/assessments", json=_payload(company_name="Общая"))
    db_session.add_all([
        M3Portfolio(user_id=test_user.id, company_name="общая", status="calculated"),
        M3Portfolio(user_id=test_user.id, company_name="Только М3", status="calculated"),
        M3Portfolio(user_id=test_user.id, company_name="Черновик М3", status="draft"),
    ])
    await db_session.flush()

    by_name = {c["name"]: c for c in (await auth_client.get("/api/companies")).json()}
    shared = by_name["Общая"]
    assert shared["assessment_count"] == 2
    assert {a["method"] for a in shared["assessments"]} == {"method1", "method3"}
    assert shared["dynamics_available"] is False   # динамика — по Методам 1–2

    only_m3 = by_name["Только М3"]
    assert only_m3["id"] is None
    assert only_m3["next_repeat_at"] is None        # у Метода 3 повтора нет
    assert "Черновик М3" not in by_name


@pytest.mark.asyncio
async def test_free_repeat_flag_follows_latest_primary(auth_client, isolated_reminder_settings):
    """Первичная → повтор: бесплатного повтора больше нет. Новая платная
    диагностика той же компании снова даёт право на повтор."""
    name = "Цикл Ко"
    await auth_client.post("/api/assessments", json=_payload(company_name=name))
    await auth_client.post("/api/assessments", json=_payload(company_name=name))
    c = {x["name"]: x for x in (await auth_client.get("/api/companies")).json()}[name]
    assert c["followup_available"] is False
    await auth_client.post("/api/assessments", json=_payload(company_name=name))
    c = {x["name"]: x for x in (await auth_client.get("/api/companies")).json()}[name]
    assert c["followup_available"] is True
    assert c["assessment_count"] == 3
    assert c["dynamics_available"] is True
