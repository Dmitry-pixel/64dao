"""Админка контента Метода 4: что правится, что нет, когда поднимается версия
и почему нельзя выключить вопрос, на который опирается правило."""
import pytest

from app.m4_models import (
    M4Card,
    M4Construct,
    M4ConstructLink,
    M4Module,
    M4Question,
    M4QuestionOption,
    M4Rule,
    M4SymptomChain,
)

API = "/api/admin/m4"


@pytest.fixture
async def content(db_session):
    db_session.add(M4Module(code=1, slug="capital", name="Капитал", client_question="?", why_it_matters="!"))
    await db_session.flush()
    q1 = M4Question(code="M01-Q01", module_code=1, text="Доли оформлены?", type="bool", tier="u0")
    q2 = M4Question(code="M01-Q02", module_code=1, text="Счета разделены?", type="bool", tier="u1")
    db_session.add_all([q1, q2])
    await db_session.flush()
    db_session.add_all([
        M4QuestionOption(question_id=q1.id, value="yes", label="Да", score=100, sort=1),
        M4QuestionOption(question_id=q1.id, value="no", label="Нет", score=0, sort=2),
    ])
    rule = M4Rule(code="CR-01", title="Правило", severity="high",
                  conditions={"all": [{"q": "M01-Q01", "op": "eq", "value": "yes"}]},
                  diagnosis="д", what_happens="в", fix_one_of=["а"], cost_of_inaction="ц")
    db_session.add(rule)
    await db_session.flush()
    card = M4Card(kind="recommendation", key="cr_CR-01", rule_code="CR-01", title="Т", body="Б",
                  effect=2, speed_weeks=4, cost=1)
    db_session.add(card)
    db_session.add(M4SymptomChain(code="s1", label="Симптом", detected_by=["M01-Q02"], chain=["а"],
                                  root_modules=[1], check_questions=["M01-Q02"], first_action="шаг"))
    db_session.add(M4Construct(code="c1", name="Конструкт", unit="company"))
    await db_session.flush()
    db_session.add(M4ConstructLink(construct_code="c1", method="m3", item_code="Р1"))
    await db_session.flush()
    return {"card": card}


async def test_regular_user_has_no_access(auth_client, content):
    assert (await auth_client.get(f"{API}/questions")).status_code == 403


async def test_text_edit_bumps_version_weight_does_not(admin_client, content):
    r = await admin_client.put(f"{API}/questions/M01-Q01", json={"weight": 3})
    assert r.status_code == 200 and r.json()["item_version"] == 1
    r = await admin_client.put(f"{API}/questions/M01-Q01", json={"text": "Доли оформлены документами?"})
    assert r.json()["item_version"] == 2 and r.json()["weight"] == 3


async def test_null_does_not_erase_required_text(admin_client, content):
    r = await admin_client.put(f"{API}/questions/M01-Q01", json={"text": None, "note_internal": None})
    assert r.status_code == 200 and r.json()["text"] == "Доли оформлены?"


async def test_option_score_edit_bumps_version(admin_client, content):
    r = await admin_client.put(f"{API}/questions/M01-Q01/options/no", json={"score": 20})
    assert r.status_code == 200
    body = r.json()
    assert body["item_version"] == 2
    assert {o["value"]: o["score"] for o in body["options"]}["no"] == 20


async def test_question_used_by_rule_cannot_be_disabled(admin_client, content):
    r = await admin_client.put(f"{API}/questions/M01-Q01/active", json={"is_active": False})
    assert r.status_code == 409 and "CR-01" in r.json()["detail"]
    assert (await admin_client.put(f"{API}/rules/CR-01", json={"is_active": False})).status_code == 200
    r = await admin_client.put(f"{API}/questions/M01-Q01/active", json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False


async def test_question_used_by_chain_cannot_be_disabled(admin_client, content):
    r = await admin_client.put(f"{API}/questions/M01-Q02/active", json={"is_active": False})
    assert r.status_code == 409 and "Симптом" in r.json()["detail"]


async def test_rule_conditions_are_read_only(admin_client, content):
    r = await admin_client.put(f"{API}/rules/CR-01", json={
        "title": "Новое", "conditions": {"all": []}, "fix_one_of": ["x", " ", "y"]})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Новое"
    assert body["conditions"]["all"][0]["q"] == "M01-Q01"
    assert body["fix_one_of"] == ["x", "y"]


async def test_recommendation_keeps_priority_scores(admin_client, content):
    cid = content["card"].id
    r = await admin_client.put(f"{API}/cards/{cid}", json={"effect": None})
    assert r.status_code == 400
    r = await admin_client.put(f"{API}/cards/{cid}", json={"body": "Новый текст", "steps": ["a", "", "b"]})
    assert r.status_code == 200
    assert r.json()["item_version"] == 2 and r.json()["steps"] == ["a", "b"]


async def test_lists_for_all_sections(admin_client, content):
    for path in ("modules", "questions", "cards", "rules", "constructs", "chains"):
        r = await admin_client.get(f"{API}/{path}")
        assert r.status_code == 200 and r.json(), path
    c = (await admin_client.get(f"{API}/constructs")).json()[0]
    assert c["links"][0]["item_code"] == "Р1"


async def test_module_intro_can_be_cleared(admin_client, content):
    r = await admin_client.put(f"{API}/modules/1", json={"intro": None, "name": None})
    assert r.status_code == 200 and r.json()["intro"] is None and r.json()["name"] == "Капитал"
