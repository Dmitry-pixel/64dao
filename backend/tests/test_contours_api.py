# -*- coding: utf-8 -*-
"""
API-тесты контуров (этап 3). Требуют БД dao64_test.
Флаги контуров пишутся в temp-каталог (UPLOAD_DIR подменён в conftest),
боевой том не затрагивается.
"""
import os

import pytest

from app.contour_settings import CONTOUR_SETTINGS_PATH, set_contour_enabled


def flat_answers(value: int = 3) -> dict:
    return {f"{b}.{p}": value for b in range(1, 7) for p in range(1, 5)}


def control_finance() -> dict:
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    return a


@pytest.fixture(autouse=True)
def reset_contour_flags():
    """Флаги — файл в temp-каталоге; чистим между тестами, чтобы включение
    контура в одном тесте не протекало в другие."""
    yield
    if os.path.exists(CONTOUR_SETTINGS_PATH):
        os.remove(CONTOUR_SETTINGS_PATH)


async def _make_method1(auth_client) -> str:
    resp = await auth_client.post("/api/assessments", json={
        "method1_answers": {str(i): "A" for i in range(1, 7)},
        "method1_combination": "AAAABB",
        "status": "completed",
        "finance_answers": control_finance(),
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ── Доступность анкеты ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_disabled_contour_items_404(auth_client):
    resp = await auth_client.get("/api/method1/contour-items/product")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unknown_contour_items_404(auth_client):
    resp = await auth_client.get("/api/method1/contour-items/nope")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_enabled_contour_items_ok(auth_client):
    set_contour_enabled("product", True)
    resp = await auth_client.get("/api/method1/contour-items/product")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contour"] == "product"
    assert data["max_unknowns"] == 3
    assert len(data["blocks"]) == 6
    assert sum(len(b["items"]) for b in data["blocks"]) == 24
    assert data["intro"]


@pytest.mark.asyncio
async def test_finance_items_alias_still_works(auth_client):
    resp = await auth_client.get("/api/method1/finance-items")
    assert resp.status_code == 200, resp.text
    assert sum(len(b["items"]) for b in resp.json()["blocks"]) == 24


# ── Сабмит контура ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_contour_ok(auth_client):
    set_contour_enabled("product", True)
    aid = await _make_method1(auth_client)
    resp = await auth_client.post(f"/api/assessments/{aid}/contours/product",
                                  json={"answers": flat_answers()})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contour"] == "product"
    assert len(data["combination"]) == 6
    assert data["result"]["hexagram_current"]["number"] in range(1, 65)


@pytest.mark.asyncio
async def test_submit_twice_conflict(auth_client):
    set_contour_enabled("product", True)
    aid = await _make_method1(auth_client)
    first = await auth_client.post(f"/api/assessments/{aid}/contours/product",
                                   json={"answers": flat_answers()})
    assert first.status_code == 200
    second = await auth_client.post(f"/api/assessments/{aid}/contours/product",
                                    json={"answers": flat_answers()})
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_submit_disabled_contour_404(auth_client):
    aid = await _make_method1(auth_client)
    resp = await auth_client.post(f"/api/assessments/{aid}/contours/market",
                                  json={"answers": flat_answers()})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_incomplete_answers_400(auth_client):
    set_contour_enabled("product", True)
    aid = await _make_method1(auth_client)
    answers = flat_answers()
    del answers["3.3"]
    resp = await auth_client.post(f"/api/assessments/{aid}/contours/product",
                                  json={"answers": answers})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_two_unknowns_in_block_400(auth_client):
    set_contour_enabled("product", True)
    aid = await _make_method1(auth_client)
    answers = flat_answers()
    answers["2.1"] = None
    answers["2.2"] = None
    resp = await auth_client.post(f"/api/assessments/{aid}/contours/product",
                                  json={"answers": answers})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_to_method2_400(auth_client):
    set_contour_enabled("product", True)
    created = await auth_client.post("/api/assessments", json={
        "status": "completed",
        "method2_data": {"Ценностное предложение": {"score": 3, "text": "x"}},
    })
    assert created.status_code == 200, created.text
    aid = created.json()["id"]
    resp = await auth_client.post(f"/api/assessments/{aid}/contours/product",
                                  json={"answers": flat_answers()})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_unknown_assessment_404(auth_client):
    set_contour_enabled("product", True)
    resp = await auth_client.post(
        "/api/assessments/00000000-0000-0000-0000-000000000000/contours/product",
        json={"answers": flat_answers()})
    assert resp.status_code == 404


# ── Админка ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_lists_and_toggles_contours(admin_client):
    resp = await admin_client.get("/api/admin/contours")
    assert resp.status_code == 200, resp.text
    items = resp.json()["contours"]
    assert [c["contour"] for c in items] == ["finance", "product", "process", "market"]
    assert next(c for c in items if c["contour"] == "finance")["enabled"] is True

    upd = await admin_client.put("/api/admin/contours/market", json={"enabled": True})
    assert upd.status_code == 200, upd.text
    assert upd.json()["contours"]["market"] is True


@pytest.mark.asyncio
async def test_admin_cannot_disable_finance(admin_client):
    resp = await admin_client.put("/api/admin/contours/finance", json={"enabled": False})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_reset_allows_resubmit(admin_client):
    set_contour_enabled("product", True)
    aid = await _make_method1(admin_client)
    first = await admin_client.post(f"/api/assessments/{aid}/contours/product",
                                    json={"answers": flat_answers()})
    assert first.status_code == 200
    dele = await admin_client.delete(f"/api/admin/assessments/{aid}/contours/product")
    assert dele.status_code == 204, dele.text
    again = await admin_client.post(f"/api/assessments/{aid}/contours/product",
                                    json={"answers": flat_answers()})
    assert again.status_code == 200, again.text


@pytest.mark.asyncio
async def test_admin_cannot_reset_finance(admin_client):
    aid = await _make_method1(admin_client)
    resp = await admin_client.delete(f"/api/admin/assessments/{aid}/contours/finance")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_passed_contours_in_list_and_detail(auth_client):
    set_contour_enabled("product", True)
    aid = await _make_method1(auth_client)
    await auth_client.post(f"/api/assessments/{aid}/contours/product",
                           json={"answers": flat_answers()})

    detail = await auth_client.get(f"/api/assessments/{aid}")
    assert detail.status_code == 200, detail.text
    passed = {c["contour"] for c in detail.json()["passed_contours"]}
    assert passed == {"finance", "product"}

    listing = await auth_client.get("/api/assessments")
    assert listing.status_code == 200, listing.text
    row = next(a for a in listing.json() if a["id"] == aid)
    assert {c["contour"] for c in row["passed_contours"]} == {"finance", "product"}
