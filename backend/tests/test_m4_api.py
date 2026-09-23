"""Прогоны Метода 4 через API: анкета, ответы, расчёт, оплата пакетом, возврат.

Контент — настоящий, из backend/content/m4 (seed в транзакцию теста):
анкета, условия показа и правила проверяются на том, что увидит клиент.
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select

import app.m4_access as m4_access
import seed_m4_content as seed
from app.m3_models import M3Portfolio
from app.m4_models import M4Run
from app.m4_service import SURVEY_ORDER
from app.models import REVENUE_MODELS, AccessGrant, Company, Order, User
from app.routers import m4 as m4_router
from app.routers.payments import pick_order, revoke_order_access
from tests.test_m3_api import m3_on  # noqa: F401

API = "/api/m4"
PROFILE = {"revenue_model": "repeat"}


@pytest_asyncio.fixture
async def content(db_session, m3_on):  # noqa: F811
    await seed.seed(seed.read_content(), reset=False, session=db_session)
    await db_session.flush()


@pytest.fixture
def enforce_on(monkeypatch):
    monkeypatch.setattr(m4_access, "enforce_credits_enabled", lambda: True)


async def _order(db, user, status="paid") -> Order:
    o = Order(user_id=user.id, product="m3", amount=30000, currency="RUB", status=status,
              paid_at=datetime.now(UTC))
    db.add(o)
    await db.flush()
    return o


async def _grant(db, user) -> AccessGrant:
    g = AccessGrant(user_id=user.id, product="m3", quota=1, reason="тест",
                    starts_at=datetime.now(UTC) - timedelta(days=1),
                    expires_at=datetime.now(UTC) + timedelta(days=7))
    db.add(g)
    await db.flush()
    return g


async def _questionnaire(client, mode):
    r = await client.get(f"{API}/questionnaire", params={"mode": mode})
    assert r.status_code == 200, r.text
    return [q for m in r.json()["modules"] for q in m["questions"]]


def _answer(q, good=False):
    if q["type"] in ("number", "money"):
        return {"code": q["code"], "number": q["min"] if q["min"] is not None else 10}
    opts = q["options"]
    return {"code": q["code"], "value": opts[0 if good else -1]["value"]}


async def _fill(client, run_id, mode, good=False):
    qs = await _questionnaire(client, mode)
    r = await client.put(f"{API}/runs/{run_id}/answers", json={"answers": [_answer(q, good) for q in qs]})
    assert r.status_code == 200, r.text
    return r.json()


async def _run(client, mode="express", **kw):
    body = {"mode": mode, "company_name": kw.pop("company_name", "ООО Колесо"), **kw}
    if mode == "full":
        body.setdefault("profile", PROFILE)
    return await client.post(f"{API}/runs", json=body)


# ── Анкета ────────────────────────────────────────────────────────────────────
async def test_questionnaire_express_is_20_questions_over_10_modules(auth_client, content):
    r = await auth_client.get(f"{API}/questionnaire", params={"mode": "express"})
    body = r.json()
    assert [m["code"] for m in body["modules"]] == SURVEY_ORDER
    assert sum(len(m["questions"]) for m in body["modules"]) == 20
    raw = json.dumps(body, ensure_ascii=False)
    # баллы и ссылки на источник клиенту не уходят
    assert '"score"' not in raw and "source_ref" not in raw and "note_internal" not in raw
    assert {o["value"] for o in body["profile_options"]["revenue_model"]} == set(REVENUE_MODELS)


async def test_survey_order_and_profile_values_match_content():
    m = json.loads((Path(seed.__file__).parent / "content/m4/modules.json").read_text(encoding="utf-8"))
    assert m["survey_order"]["u0"] == SURVEY_ORDER == m["survey_order"]["u1"]
    assert m4_router.PROFILE_VALUES["revenue_model"] == REVENUE_MODELS


async def test_section_hidden_when_flag_off(auth_client, db_session):
    from app.config import get_settings
    s = get_settings()
    old, s.m3_enabled = s.m3_enabled, False
    try:
        assert (await auth_client.get(f"{API}/questionnaire")).status_code == 404
    finally:
        s.m3_enabled = old


# ── Экспресс ──────────────────────────────────────────────────────────────────
async def test_express_flow(auth_client, content, db_session):
    r = await _run(auth_client)
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["progress"]["required"] == 20 and run["status"] == "draft"

    r = await auth_client.post(f"{API}/runs/{run['id']}/calculate")
    assert r.status_code == 400 and len(r.json()["detail"]["missing"]) == 20

    filled = await _fill(auth_client, run["id"], "express")
    assert filled["status"] == "filled" and filled["progress"]["missing"] == []

    r = await auth_client.post(f"{API}/runs/{run['id']}/calculate")
    assert r.status_code == 200, r.text
    res = r.json()
    assert len(res["top_gaps"]) == 3 and res["constraint"] is None and res["priority_queue"] == []
    assert set(res["modules"]) == {str(i) for i in range(1, 11)}

    row = await db_session.get(M4Run, res["run_id"])
    assert row.status == "calculated" and row.order_id is None and row.item_versions["questions"]

    # рассчитанный прогон не правится и второй раз не считается
    q = (await _questionnaire(auth_client, "express"))[0]
    assert (await auth_client.put(f"{API}/runs/{run['id']}/answers",
                                  json={"answers": [_answer(q)]})).status_code == 409
    assert (await auth_client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 409
    assert (await auth_client.get(f"{API}/runs/{run['id']}/result")).status_code == 200


async def test_draft_is_continued_not_duplicated(auth_client, content):
    a = (await _run(auth_client)).json()
    b = (await _run(auth_client)).json()
    assert a["id"] == b["id"]
    assert len((await auth_client.get(f"{API}/runs")).json()) == 1


async def test_answer_validation(auth_client, content):
    run = (await _run(auth_client)).json()
    qs = {q["code"]: q for q in await _questionnaire(auth_client, "express")}
    choice = next(q for q in qs.values() if q["options"])
    number = next(q for q in qs.values() if q["type"] == "number")

    async def put(item):
        return await auth_client.put(f"{API}/runs/{run['id']}/answers", json={"answers": [item]})

    assert (await put({"code": choice["code"], "value": "maybe"})).status_code == 400
    assert (await put({"code": number["code"], "value": "yes"})).status_code == 400
    assert (await put({"code": number["code"], "number": -5})).status_code == 400
    assert (await put({"code": "M04-Q03", "number": 10})).status_code == 400   # u1 в экспрессе
    assert (await put({"code": choice["code"], "value": "unknown"})).status_code == 200
    r = await put({"code": choice["code"]})                                     # снять ответ
    assert r.status_code == 200 and r.json()["progress"]["answered"] == 0


async def test_other_user_cannot_see_run(auth_client, content, db_session, client):
    run = (await _run(auth_client)).json()
    from tests.conftest import _set_auth_cookie
    other = User(email="other@example.com", full_name="Другой", role="user")
    db_session.add(other)
    await db_session.flush()
    _set_auth_cookie(client, other)
    assert (await client.get(f"{API}/runs/{run['id']}")).status_code == 403


async def test_delete_hides_run(auth_client, content):
    run = (await _run(auth_client)).json()
    assert (await auth_client.delete(f"{API}/runs/{run['id']}")).status_code == 204
    assert (await auth_client.get(f"{API}/runs/{run['id']}")).status_code == 404


# ── Полная ────────────────────────────────────────────────────────────────────
async def test_full_requires_profile(auth_client, content):
    r = await auth_client.post(f"{API}/runs", json={"mode": "full", "company_name": "Без профиля"})
    assert r.status_code == 400


async def test_full_takes_express_answers(auth_client, content):
    ex = (await _run(auth_client)).json()
    await _fill(auth_client, ex["id"], "express")
    full = (await _run(auth_client, "full")).json()
    assert full["progress"]["answered"] == 20
    assert full["progress"]["required"] > 100


async def test_conditional_question_leaves_and_returns(auth_client, content):
    """M01-Q12 задаётся только при «да» в M01-Q09."""
    run = (await _run(auth_client, "full")).json()
    put = f"{API}/runs/{run['id']}/answers"
    base = (await auth_client.put(put, json={"answers": [{"code": "M01-Q09", "value": "no"}]})).json()
    assert "M01-Q12" not in base["progress"]["missing"]
    yes = (await auth_client.put(put, json={"answers": [{"code": "M01-Q09", "value": "yes"}]})).json()
    assert "M01-Q12" in yes["progress"]["missing"]
    assert yes["progress"]["required"] == base["progress"]["required"] + 1


async def test_full_flow_with_rules_and_queue(auth_client, content, db_session):
    run = (await _run(auth_client, "full")).json()
    await _fill(auth_client, run["id"], "full")
    r = await auth_client.post(f"{API}/runs/{run['id']}/calculate")
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["constraint"]["module"] in range(1, 10)
    assert res["fired_rules"] and res["priority_queue"][0]["is_constraint"]
    assert res["cause_effect"]["case"] in (
        "both_low", "causes_high_effect_low", "causes_low_effect_high", "consistent")
    assert res["confidence"]["level"] in ("high", "medium", "low")
    row = await db_session.get(M4Run, run["id"])
    assert row.profile_snapshot == {"revenue_model": "repeat", "industry_id": None, "revenue_range": None,
                                    "headcount": None, "active_clients": None}


# ── Оплата пакетом ────────────────────────────────────────────────────────────
async def test_full_blocked_without_package(auth_client, content, enforce_on):
    assert (await _run(auth_client, "full")).status_code == 403
    assert (await _run(auth_client)).status_code == 201          # экспресс бесплатный
    assert (await auth_client.get(f"{API}/credits")).json() == {"full_available": 0}


async def test_package_pays_m4_and_leaves_m3(auth_client, content, db_session, test_user, enforce_on):
    order = await _order(db_session, test_user)
    run = (await _run(auth_client, "full")).json()
    await _fill(auth_client, run["id"], "full")
    assert (await auth_client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 200
    row = await db_session.get(M4Run, run["id"])
    assert row.order_id == order.id and row.grant_id is None

    # Метод 4 из пакета израсходован, Метод 3 — нет
    assert (await auth_client.get(f"{API}/credits")).json() == {"full_available": 0}
    assert (await pick_order(db_session, test_user.id, "m3")).id == order.id
    assert (await _run(auth_client, "full", company_name="Вторая")).status_code == 403


async def test_m3_portfolio_does_not_spend_m4(auth_client, content, db_session, test_user, enforce_on):
    order = await _order(db_session, test_user)
    db_session.add(M3Portfolio(user_id=test_user.id, title="П", company_name="ООО Колесо",
                               status="calculated", order_id=order.id))
    await db_session.flush()
    assert (await auth_client.get(f"{API}/credits")).json() == {"full_available": 1}


async def test_grant_goes_first(auth_client, content, db_session, test_user, enforce_on):
    await _order(db_session, test_user)
    grant = await _grant(db_session, test_user)
    run = (await _run(auth_client, "full")).json()
    await _fill(auth_client, run["id"], "full")
    await auth_client.post(f"{API}/runs/{run['id']}/calculate")
    row = await db_session.get(M4Run, run["id"])
    assert row.grant_id == grant.id and row.order_id is None


async def test_refund_closes_report(auth_client, content, db_session, test_user, enforce_on):
    order = await _order(db_session, test_user)
    run = (await _run(auth_client, "full")).json()
    await _fill(auth_client, run["id"], "full")
    await auth_client.post(f"{API}/runs/{run['id']}/calculate")

    order.status = "refunded"
    revoked = await revoke_order_access(db_session, order)
    await db_session.flush()
    assert revoked["m4_runs"] == 1
    row = await db_session.get(M4Run, run["id"])
    assert row.status == "filled" and row.order_id is None
    assert (await auth_client.get(f"{API}/runs/{run['id']}/result")).status_code == 403
    # без нового пакета пересчитать нельзя
    assert (await auth_client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 403
    await _order(db_session, test_user)
    assert (await auth_client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 200


async def test_admin_is_free(admin_client, content, db_session, enforce_on):
    run = (await _run(admin_client, "full")).json()
    await _fill(admin_client, run["id"], "full")
    assert (await admin_client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 200
    row = await db_session.get(M4Run, run["id"])
    assert row.order_id is None and row.grant_id is None
    assert await db_session.scalar(select(Company).where(Company.id == row.company_id))
