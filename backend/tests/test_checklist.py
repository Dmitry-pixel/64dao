# -*- coding: utf-8 -*-
"""
Фича F: чек-листы шагов маршрута (routers/checklist.py).
Маршрут задаётся синтетическим снимком контура (2 подвижные линии) — build_route
чист, _lookup принимает любой AB-код. Проверяем отдачу, прогресс, персист
отметок, доступ и валидацию.
"""
import uuid

import pytest

from app.models import Assessment, AssessmentContour, User


def _result():
    # combination_current + подвижные линии 2 (old_yin) и 4 (old_yang) → 2 шага.
    return {
        "combination_current": "AAAAAA",
        "lines": [
            {"line": 2, "moving": True, "state": "old_yin", "symbol": "B", "block": "b2", "flags": []},
            {"line": 4, "moving": True, "state": "old_yang", "symbol": "A", "block": "b4", "flags": []},
            {"line": 1, "moving": False, "state": "young_yang", "symbol": "A", "block": "b1", "flags": []},
        ],
    }


async def _assessment(db, user_id, with_contour=True) -> Assessment:
    a = Assessment(user_id=user_id, method="method1",
                   method1_combination="AAAAAA", status="completed",
                   company_name="Ко")
    db.add(a)
    await db.flush()
    if with_contour:
        db.add(AssessmentContour(assessment_id=a.id, contour="finance",
                                 answers={"x": 1}, result=_result(),
                                 combination="AAAAAA"))
        await db.flush()
    return a


@pytest.mark.asyncio
async def test_checklist_lists_route_steps(auth_client, db_session, test_user):
    a = await _assessment(db_session, test_user.id)
    r = await auth_client.get(f"/api/assessments/{a.id}/checklist")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["has_route"] is True
    assert b["total"] == 2 and b["done"] == 0 and b["progress"] == 0
    fin = [c for c in b["contours"] if c["contour"] == "finance"][0]
    assert fin["title"] == "Финансы"
    assert {s["line"] for s in fin["steps"]} == {2, 4}
    assert all(s["done"] is False for s in fin["steps"])


@pytest.mark.asyncio
async def test_toggle_persists_and_updates_progress(auth_client, db_session, test_user):
    a = await _assessment(db_session, test_user.id)
    r = await auth_client.put(f"/api/assessments/{a.id}/checklist/finance/2", json={"done": True})
    assert r.status_code == 200, r.text
    assert r.json()["done"] is True
    b = (await auth_client.get(f"/api/assessments/{a.id}/checklist")).json()
    assert b["done"] == 1 and b["progress"] == 50
    step2 = [s for c in b["contours"] for s in c["steps"] if s["line"] == 2][0]
    assert step2["done"] is True and step2["done_at"]
    # снять отметку
    r2 = await auth_client.put(f"/api/assessments/{a.id}/checklist/finance/2", json={"done": False})
    assert r2.json()["done"] is False
    b2 = (await auth_client.get(f"/api/assessments/{a.id}/checklist")).json()
    assert b2["done"] == 0 and b2["progress"] == 0


@pytest.mark.asyncio
async def test_empty_for_assessment_without_contours(auth_client, db_session, test_user):
    a = await _assessment(db_session, test_user.id, with_contour=False)
    b = (await auth_client.get(f"/api/assessments/{a.id}/checklist")).json()
    assert b["has_route"] is False and b["total"] == 0 and b["contours"] == []


@pytest.mark.asyncio
async def test_unknown_assessment_404(auth_client):
    r = await auth_client.get(f"/api/assessments/{uuid.uuid4()}/checklist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_foreign_assessment_forbidden(auth_client, db_session):
    other = User(email=f"other-{uuid.uuid4()}@t.t", role="user")
    db_session.add(other)
    await db_session.flush()
    a = await _assessment(db_session, other.id)
    r = await auth_client.get(f"/api/assessments/{a.id}/checklist")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_toggle_validation(auth_client, db_session, test_user):
    a = await _assessment(db_session, test_user.id)
    r1 = await auth_client.put(f"/api/assessments/{a.id}/checklist/bogus/2", json={"done": True})
    assert r1.status_code == 400
    r2 = await auth_client.put(f"/api/assessments/{a.id}/checklist/finance/9", json={"done": True})
    assert r2.status_code == 400
