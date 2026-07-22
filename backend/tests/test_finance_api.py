# -*- coding: utf-8 -*-
"""
API-тесты финблока (Этап 4). Требуют БД (dao64_test) — идут в CI/против dao64_test,
НЕ против прод-БД. Используют фикстуры conftest (client/auth_client/admin_client).
"""
import pytest

import app.routers.assessments as assessments_router
from app.finance_items import ITEM_IDS


def control_finance() -> dict:
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    return a


@pytest.mark.asyncio
async def test_create_assessment_with_finance_scores_on_server(auth_client):
    resp = await auth_client.post("/api/assessments", json={
        "method1_combination": "AAAABB",
        "status": "completed",
        "finance_answers": control_finance(),
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["finance_combination"] == "AAAABB"
    assert data["finance_result"]["hexagram_current"]["number"] == 34
    assert data["finance_result"]["hexagram_resulting"]["number"] == 14


@pytest.mark.asyncio
async def test_create_assessment_without_finance_flag_off_ok(auth_client, monkeypatch):
    monkeypatch.setattr(assessments_router.settings, "finance_block_required", False)
    resp = await auth_client.post("/api/assessments", json={
        "method1_combination": "AAAABB", "status": "completed",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["finance_combination"] is None


@pytest.mark.asyncio
async def test_create_assessment_without_finance_flag_on_rejected(auth_client, monkeypatch):
    monkeypatch.setattr(assessments_router.settings, "finance_block_required", True)
    resp = await auth_client.post("/api/assessments", json={
        "method1_combination": "AAAABB", "status": "completed",
    })
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_create_assessment_finance_underfilled_rejected(auth_client):
    a = control_finance(); a["1.1"] = None; a["1.2"] = None
    resp = await auth_client.post("/api/assessments", json={
        "method1_combination": "AAAABB", "status": "completed", "finance_answers": a,
    })
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_create_assessment_finance_bad_value_422(auth_client):
    a = control_finance(); a["1.1"] = 5
    resp = await auth_client.post("/api/assessments", json={
        "method1_combination": "AAAABB", "status": "completed", "finance_answers": a,
    })
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_fin_content_upsert_and_list_admin(admin_client):
    put = await admin_client.put("/api/fin-content/tonality/mature", json={
        "payload": {"title": "Зрелая функция", "text": "Оптимизация."},
        "sort": 0, "is_active": True,
    })
    assert put.status_code == 200, put.text
    assert put.json()["payload"]["text"] == "Оптимизация."

    lst = await admin_client.get("/api/fin-content?kind=tonality")
    assert lst.status_code == 200
    keys = [r["key"] for r in lst.json()]
    assert "mature" in keys


@pytest.mark.asyncio
async def test_fin_content_update_existing(admin_client):
    await admin_client.put("/api/fin-content/quadrant/scale", json={"payload": {"text": "v1"}})
    upd = await admin_client.put("/api/fin-content/quadrant/scale", json={"payload": {"text": "v2"}})
    assert upd.json()["payload"]["text"] == "v2"
    lst = await admin_client.get("/api/fin-content?kind=quadrant")
    scale = [r for r in lst.json() if r["key"] == "scale"]
    assert len(scale) == 1 and scale[0]["payload"]["text"] == "v2"


@pytest.mark.asyncio
async def test_fin_content_invalid_kind_400(admin_client):
    resp = await admin_client.put("/api/fin-content/bogus/x", json={"payload": {"text": "y"}})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_fin_content_forbidden_for_non_admin(auth_client):
    assert (await auth_client.get("/api/fin-content")).status_code == 403
    put = await auth_client.put("/api/fin-content/tonality/mature", json={"payload": {"text": "z"}})
    assert put.status_code == 403


@pytest.mark.asyncio
async def test_fin_content_contour_override(admin_client):
    """Переопределение под контур — отдельная строка, общий слой не затрагивается."""
    await admin_client.put("/api/fin-content/tonality/mature",
                           json={"payload": {"text": "общий"}})
    ov = await admin_client.put("/api/fin-content/tonality/mature?contour=product",
                                json={"payload": {"text": "для продукта"}})
    assert ov.status_code == 200, ov.text
    assert ov.json()["contour"] == "product"

    lst = (await admin_client.get("/api/fin-content?kind=tonality")).json()
    mature = [r for r in lst if r["key"] == "mature"]
    contours = {r["contour"] for r in mature}
    assert {"common", "product"} <= contours

    only = (await admin_client.get("/api/fin-content?kind=tonality&contour=product")).json()
    assert all(r["contour"] == "product" for r in only)
    assert any(r["key"] == "mature" and r["payload"]["text"] == "для продукта" for r in only)
    # общий слой не перезаписан
    common = (await admin_client.get("/api/fin-content?kind=tonality&contour=common")).json()
    assert any(r["key"] == "mature" and r["payload"]["text"] == "общий" for r in common)


@pytest.mark.asyncio
async def test_fin_content_override_delete_reverts(admin_client):
    await admin_client.put("/api/fin-content/tonality/crisis", json={"payload": {"text": "общий"}})
    await admin_client.put("/api/fin-content/tonality/crisis?contour=market",
                           json={"payload": {"text": "рынок"}})
    d = await admin_client.delete("/api/fin-content/tonality/crisis?contour=market")
    assert d.status_code == 204
    only = (await admin_client.get("/api/fin-content?kind=tonality&contour=market")).json()
    assert not any(r["key"] == "crisis" for r in only)


@pytest.mark.asyncio
async def test_fin_content_delete_common_forbidden_400(admin_client):
    await admin_client.put("/api/fin-content/tonality/transitional", json={"payload": {"text": "x"}})
    d = await admin_client.delete("/api/fin-content/tonality/transitional?contour=common")
    assert d.status_code == 400


# ── GET /api/method1/finance-items ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_finance_items_endpoint(auth_client):
    resp = await auth_client.get("/api/method1/finance-items")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data["scale_labels"].keys()) == {"1", "2", "3", "4"}
    assert len(data["blocks"]) == 6
    all_ids = [it["item_id"] for b in data["blocks"] for it in b["items"]]
    assert len(all_ids) == 24
    assert set(all_ids) == set(ITEM_IDS)
    assert data["blocks"][0]["items"][0]["item_id"] == "1.1"


@pytest.mark.asyncio
async def test_finance_items_requires_auth(client):
    assert (await client.get("/api/method1/finance-items")).status_code == 401


# ── fin_pattern_* через редактор стратегии (Этап 7) ───────────────────────────
@pytest.mark.asyncio
async def test_strategy_fin_pattern_roundtrip(admin_client):
    put = await admin_client.put("/api/strategies/AAAABB", json={
        "fin_pattern_essence": "Суть паттерна для теста.",
        "fin_pattern_mistake": "Типичная ошибка для теста.",
    })
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["fin_pattern_essence"] == "Суть паттерна для теста."
    assert body["fin_pattern_mistake"] == "Типичная ошибка для теста."

    got = await admin_client.get("/api/strategies/AAAABB")
    assert got.status_code == 200
    assert got.json()["fin_pattern_essence"] == "Суть паттерна для теста."
