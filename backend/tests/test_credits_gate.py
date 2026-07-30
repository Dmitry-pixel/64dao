"""Гейт доступа к результату (_ensure_result_access) под enforce_credits."""
import pytest

import app.routers.assessments as assessments_router
from app.models import Assessment, Strategy

COMBO = "AAABAA"


@pytest.fixture
def enforce_credits_on(monkeypatch):
    # Флаг читается из credits_settings.py, а не из Settings: подменяем
    # функцию, иначе тест молча работал бы вхолостую.
    monkeypatch.setattr(assessments_router, "enforce_credits_enabled", lambda: True)


async def _assessment(db, user, status, combo=COMBO):
    a = Assessment(user_id=user.id, method1_combination=combo, status=status, company_name="Co")
    db.add(a)
    await db.flush()
    return a


async def _strategy(db, combo=COMBO):
    s = Strategy(combination=combo, title="T", is_published=True)
    db.add(s)
    await db.flush()
    return s


@pytest.mark.asyncio
async def test_pdf_blocked_for_draft_under_enforce(auth_client, db_session, test_user, enforce_credits_on):
    a = await _assessment(db_session, test_user, "draft")
    resp = await auth_client.get(f"/api/assessments/{a.id}/pdf")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_strategy_blocked_for_draft_under_enforce(auth_client, db_session, test_user, enforce_credits_on):
    a = await _assessment(db_session, test_user, "draft")
    resp = await auth_client.get(f"/api/assessments/{a.id}/strategy")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_strategy_allowed_for_completed_under_enforce(auth_client, db_session, test_user, enforce_credits_on):
    await _strategy(db_session)
    a = await _assessment(db_session, test_user, "completed")
    resp = await auth_client.get(f"/api/assessments/{a.id}/strategy")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_bypasses_gate_for_draft(admin_client, db_session, test_admin, enforce_credits_on):
    await _strategy(db_session)
    a = await _assessment(db_session, test_admin, "draft")
    resp = await admin_client.get(f"/api/assessments/{a.id}/strategy")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_gate_off_by_default_allows_draft_strategy(auth_client, db_session, test_user):
    await _strategy(db_session)
    a = await _assessment(db_session, test_user, "draft")
    resp = await auth_client.get(f"/api/assessments/{a.id}/strategy")
    assert resp.status_code == 200
