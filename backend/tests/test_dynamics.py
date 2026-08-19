# -*- coding: utf-8 -*-
"""
Динамика компании (роадмап 3.1, PR3): чистый модуль сравнения + API с гейтом
подписки.
"""
import pytest

from app.contours import LINE_KEYS
from app.dynamics import (
    build_company_dynamics,
    constraint_change,
    contour_diff,
    summarize_contours,
)


def _cres(combo, moving, maturity):
    """Снимок result контура для тестов."""
    lines = [{"line": n, "block": LINE_KEYS[n - 1], "symbol": combo[n - 1],
              "moving": n in moving} for n in range(1, 7)]
    res = "".join(("B" if combo[i] == "A" else "A") if (i + 1) in moving else combo[i]
                  for i in range(6)) if moving else None
    return {"lines": lines, "combination_current": combo, "combination_resulting": res,
            "moving_lines": sorted(moving), "maturity_index": maturity,
            "hexagram_current": {"number": 1, "name": "x", "code": combo}}


# ── чистый модуль ─────────────────────────────────────────────────────────────

def test_contour_diff_line_changes_and_delta():
    prev = _cres("AAAAAA", set(), 6)
    curr = _cres("BBBBBB", set(), 0)
    d = contour_diff(prev, curr)
    assert d["maturity_delta"] == -6
    assert len(d["line_changes"]) == 6
    assert all(ch["direction"] == "yang_to_yin" for ch in d["line_changes"])


def test_contour_diff_reached_prev_target():
    prev = _cres("AAAABB", {6}, 4)            # resulting = AAAABA
    curr = _cres("AAAABA", set(), 5)
    d = contour_diff(prev, curr)
    assert d["reached_prev_target"] is True
    assert d["maturity_delta"] == 1


def test_moving_closed_and_new():
    prev = _cres("AAAAAA", {1, 2}, 6)
    curr = _cres("AAAAAA", {2, 3}, 6)
    d = contour_diff(prev, curr)
    assert d["moving_closed"] == [1]
    assert d["moving_new"] == [3]


def test_summarize_buckets():
    diffs = {
        "finance": {"maturity_delta": 2},
        "product": {"maturity_delta": -1},
        "process": {"maturity_delta": 0},
    }
    s = summarize_contours(diffs)
    assert s["improved"] == ["finance"]
    assert s["degraded"] == ["product"]
    assert s["unchanged"] == ["process"]


def test_constraint_change_detected():
    prev = {"finance": _cres("AAAAAA", set(), 6), "product": _cres("BBBBBB", set(), 0)}
    curr = {"finance": _cres("BBBBBB", set(), 0), "product": _cres("AAAAAA", set(), 6)}
    ch = constraint_change(prev, curr)
    assert ch["from"] == "product" and ch["to"] == "finance" and ch["changed"] is True


def test_build_needs_two():
    one = [{"id": "1", "created_at": "2026-01-01", "combination": "AAAAAA", "contours": {}}]
    assert build_company_dynamics(one)["available"] is False


def test_build_previous_vs_first():
    snaps = [
        {"id": "a", "created_at": "2026-01-01", "combination": "AAAAAA",
         "contours": {"finance": _cres("AAAAAA", set(), 6)}},
        {"id": "b", "created_at": "2026-02-01", "combination": "AAAAAA",
         "contours": {"finance": _cres("AAAABA", set(), 5)}},
        {"id": "c", "created_at": "2026-03-01", "combination": "AAAAAA",
         "contours": {"finance": _cres("AAAABB", set(), 4)}},
    ]
    prev = build_company_dynamics(snaps, mode="previous")
    assert prev["compare_from"]["id"] == "b" and prev["compare_to"]["id"] == "c"
    assert prev["contours"]["finance"]["maturity_delta"] == -1

    first = build_company_dynamics(snaps, mode="first")
    assert first["compare_from"]["id"] == "a"
    assert first["contours"]["finance"]["maturity_delta"] == -2
    assert first["summary"]["degraded"] == ["finance"]


# ── API ───────────────────────────────────────────────────────────────────────

_FIN = {f"{b}.{q}": 3 for b in range(1, 7) for q in range(1, 5)}


def _payload(**ov):
    p = {"method1_answers": {"goal": "A", "strategy": "B"}, "method1_combination": "AABBAB",
         "method2_data": None, "finance_answers": _FIN, "company_name": "Динамика", "status": "completed"}
    p.update(ov)
    return p


@pytest.mark.asyncio
async def test_dynamics_open_without_subscription(auth_client, db_session):
    """Динамика входит в стоимость диагностики, отдельный доступ не нужен."""
    await auth_client.post("/api/assessments", json=_payload())
    await auth_client.post("/api/assessments", json=_payload())
    companies = (await auth_client.get("/api/companies")).json()
    cid = next(c["id"] for c in companies if c["name"] == "Динамика")
    r = await auth_client.get(f"/api/companies/{cid}/dynamics")
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 2


@pytest.mark.asyncio
async def test_dynamics_returns_comparison(auth_client, test_user, db_session):
    await auth_client.post("/api/assessments", json=_payload(company_name="ДинОК"))
    await auth_client.post("/api/assessments", json=_payload(company_name="ДинОК"))

    companies = (await auth_client.get("/api/companies")).json()
    cid = next(c["id"] for c in companies if c["name"] == "ДинОК")
    r = await auth_client.get(f"/api/companies/{cid}/dynamics")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["available"] is True
    assert body["count"] == 2
    assert "finance" in body["contours"]
    assert "summary" in body
