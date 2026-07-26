# -*- coding: utf-8 -*-
"""
Поиск диагностик по названию компании.

Ищем по company_name самой диагностики, а не по профилю владельца: компаний
у него может быть несколько, и профиль о них не знает.
"""
import pytest

VALID = "AABABA"
FINANCE = {f"{b}.{p}": 3 for b in range(1, 7) for p in range(1, 5)}


def _payload(name: str) -> dict:
    return {
        "method1_answers": {"goal": "A", "strategy": "B"},
        "method1_combination": VALID,
        "method2_data": None,
        "finance_answers": FINANCE,
        "company_name": name,
        "status": "completed",
    }


async def _seed(client):
    for name in ("Ромашка", "Лютик", "Ромашка Плюс"):
        r = await client.post("/api/assessments", json=_payload(name))
        assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_search_returns_matching_only(auth_client):
    await _seed(auth_client)
    r = await auth_client.get("/api/assessments", params={"q": "ромаш"})
    assert r.status_code == 200, r.text
    assert {a["company_name"] for a in r.json()} == {"Ромашка", "Ромашка Плюс"}


@pytest.mark.asyncio
async def test_search_is_case_insensitive(auth_client):
    await _seed(auth_client)
    r = await auth_client.get("/api/assessments", params={"q": "ЛЮТИК"})
    assert [a["company_name"] for a in r.json()] == ["Лютик"]


@pytest.mark.asyncio
async def test_blank_query_returns_everything(auth_client):
    await _seed(auth_client)
    full = (await auth_client.get("/api/assessments")).json()
    blank = (await auth_client.get("/api/assessments", params={"q": "   "})).json()
    assert len(blank) == len(full) >= 3


@pytest.mark.asyncio
async def test_no_match_returns_empty(auth_client):
    await _seed(auth_client)
    r = await auth_client.get("/api/assessments", params={"q": "нет такой компании"})
    assert r.json() == []


@pytest.mark.asyncio
async def test_followup_fields_are_exposed(auth_client):
    """Кабинету нужен счётчик, иначе бейдж «доступна повторная» не нарисовать."""
    await auth_client.post("/api/assessments", json=_payload("Счётчик Ко"))
    r = await auth_client.get("/api/assessments", params={"q": "Счётчик"})
    item = r.json()[0]
    assert item["followup_allowed"] == 1
    assert item["followup_used"] == 0
    assert item["is_followup"] is False
    assert item["parent_assessment_id"] is None
    assert item["company_id"]
