"""Отчёт Метода 4: сборка текстов из карточек и правил поверх снимка.

Контент настоящий (seed в транзакцию теста), ответы — из API-тестов:
проверяется, что каждый раздел находит свои тексты и что клиенту не уходят
служебные поля.
"""
import json

from sqlalchemy import update

from app.m4_models import M4Card
from tests.test_m4_api import API, _fill, _run, content, m3_on  # noqa: F401


async def _calculated(client, mode="full"):
    run = (await _run(client, mode)).json()
    await _fill(client, run["id"], mode)
    assert (await client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 200
    r = await client.get(f"{API}/runs/{run['id']}/report")
    assert r.status_code == 200, r.text
    return r.json()


async def test_full_report_has_all_sections(auth_client, content):
    rep = await _calculated(auth_client)
    assert rep["run"]["company_name"] == "ООО Колесо"
    assert [m["code"] for m in rep["modules"]] == list(range(1, 11))
    assert all(m["card"] and m["card"]["title"] for m in rep["modules"] if m["state"])
    assert rep["constraint"]["card"]["title"] and rep["constraint"]["blocked"]
    assert rep["contradictions"] and all(c["fix_one_of"] for c in rep["contradictions"])
    assert rep["actions"][0]["is_constraint"]
    assert [a["n"] for a in rep["actions"]] == list(range(1, len(rep["actions"]) + 1))
    assert rep["confidence"]["card"]["title"]
    assert rep["cause_effect"]["text"]


async def test_rule_actions_take_options_from_rule(auth_client, content):
    rep = await _calculated(auth_client)
    rule_actions = [a for a in rep["actions"] if a["rule_code"]]
    assert rule_actions
    for a in rule_actions:
        # служебное тело карточки правила клиенту не показывается
        assert a["body"] is None and a["options"]


async def test_no_internal_fields(auth_client, content):
    raw = json.dumps(await _calculated(auth_client), ensure_ascii=False)
    for word in ("source_ref", "note_internal", "fix_one_of\": null", "гл.", "Ли Цзянь"):
        assert word not in raw


async def test_express_report(auth_client, content):
    rep = await _calculated(auth_client, "express")
    assert rep["constraint"] is None and rep["actions"] == [] and rep["contradictions"] == []
    assert len(rep["top_gaps"]) == 3


async def test_disabled_card_does_not_break_report(auth_client, content, db_session):
    await db_session.execute(update(M4Card).where(M4Card.kind == "module_state").values(is_active=False))
    rep = await _calculated(auth_client)
    assert all(m["card"] is None for m in rep["modules"])
    assert rep["actions"]


async def test_report_closed_until_calculated(auth_client, content):
    run = (await _run(auth_client)).json()
    assert (await auth_client.get(f"{API}/runs/{run['id']}/report")).status_code == 403
