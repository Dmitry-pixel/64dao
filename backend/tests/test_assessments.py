"""
test_assessments.py — regression-тесты роутера /api/assessments.

generate_pdf мокается везде (AsyncMock) — реальный Playwright/Chromium
рендеринг не тестируется здесь: дорогая операция с общим module-level
browser state (_pw/_browser в app.pdf), не подходит для быстрых
изолированных regression-тестов. Корректность самого HTML уже покрыта
test_sanity.py::TestBuildReportHTML.
"""
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models import Assessment, Report, Strategy


VALID_COMBINATION = "AABABA"  # 6 символов A/B — проходит regex-валидацию схемы


# Финблок обязателен для completed-диагностики Метода 1 (FINANCE_BLOCK_REQUIRED=true).
FINANCE_ANSWERS = {f"{b}.{p}": 3 for b in range(1, 7) for p in range(1, 5)}


def assessment_payload(**overrides) -> dict:
    payload = {
        "method1_answers": {"goal": "A", "strategy": "B"},
        "method1_combination": VALID_COMBINATION,
        "method2_data": None,
        "finance_answers": FINANCE_ANSWERS,
        "company_name": "Тестовая Компания",
        "status": "completed",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def mock_generate_pdf(monkeypatch):
    """Мокает generate_pdf в роутере assessments — не запускает Chromium."""
    import app.routers.assessments as assessments_router

    mock = AsyncMock(return_value="/fake/path/report.pdf")
    monkeypatch.setattr(assessments_router, "generate_pdf", mock)
    return mock


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_assessment_method1(auth_client, db_session, test_user):
    resp = await auth_client.post("/api/assessments", json=assessment_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["method1_combination"] == VALID_COMBINATION
    assert body["company_name"] == "Тестовая Компания"
    assert body["reports"] == []

    saved = await db_session.scalar(select(Assessment).where(Assessment.id == body["id"]))
    assert saved is not None
    assert saved.user_id == test_user.id


@pytest.mark.asyncio
async def test_create_assessment_invalid_combination_rejected(auth_client):
    resp = await auth_client.post("/api/assessments", json=assessment_payload(
        method1_combination="ZZZZZZ",
    ))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_assessment_invalid_answer_rejected(auth_client):
    resp = await auth_client.post("/api/assessments", json=assessment_payload(
        method1_answers={"goal": "C"},  # допустимо только A/B
    ))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_assessment_company_name_falls_back_to_user(auth_client, test_user):
    resp = await auth_client.post("/api/assessments", json=assessment_payload(company_name=None))
    assert resp.status_code == 200
    assert resp.json()["company_name"] == test_user.company_name


@pytest.mark.asyncio
async def test_create_assessment_without_auth_returns_401(client):
    resp = await client.post("/api/assessments", json=assessment_payload())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_assessment_method2(auth_client):
    """method1_* всё None, method2_data заполнен — Метод 2 (BMC)."""
    resp = await auth_client.post("/api/assessments", json=assessment_payload(
        method1_answers=None,
        method1_combination=None,
        method2_data={
            "value_proposition": {"score": 4, "text": "Тестовое значение"},
        },
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert body["method1_combination"] is None
    assert body["method2_data"]["value_proposition"]["score"] == 4


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_assessments_returns_only_own(auth_client, db_session, test_user, test_admin):
    own = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    other = Assessment(user_id=test_admin.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add_all([own, other])
    await db_session.flush()

    resp = await auth_client.get("/api/assessments")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert str(own.id) in ids
    assert str(other.id) not in ids


@pytest.mark.asyncio
async def test_list_assessments_includes_strategy_image_url(auth_client, db_session, test_user):
    strategy = Strategy(combination=VALID_COMBINATION, image_url="/uploads/images/test.webp", is_published=True)
    db_session.add(strategy)
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.get("/api/assessments")
    assert resp.status_code == 200
    item = next(i for i in resp.json() if i["id"] == str(assessment.id))
    assert item["strategy_image_url"] == "/uploads/images/test.webp"


@pytest.mark.asyncio
async def test_list_assessments_empty_without_auth(client):
    resp = await client.get("/api/assessments")
    assert resp.status_code == 401


# ── Get by id ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_assessment_owner_can_access(auth_client, db_session, test_user):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.get(f"/api/assessments/{assessment.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(assessment.id)


@pytest.mark.asyncio
async def test_get_assessment_other_user_forbidden(auth_client, db_session, test_admin):
    """test_admin владеет, auth_client (test_user) не владеет и не админ → 403."""
    assessment = Assessment(user_id=test_admin.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.get(f"/api/assessments/{assessment.id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_assessment_admin_can_access_any(admin_client, db_session, test_user):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await admin_client.get(f"/api/assessments/{assessment.id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_assessment_not_found_returns_404(auth_client):
    resp = await auth_client.get(f"/api/assessments/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_assessment_owner_succeeds(auth_client, db_session, test_user):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()
    assessment_id = assessment.id

    resp = await auth_client.delete(f"/api/assessments/{assessment_id}")
    assert resp.status_code == 204

    gone = await db_session.scalar(select(Assessment).where(Assessment.id == assessment_id))
    assert gone is None


@pytest.mark.asyncio
async def test_delete_assessment_other_user_forbidden(auth_client, db_session, test_admin):
    assessment = Assessment(user_id=test_admin.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.delete(f"/api/assessments/{assessment.id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_assessment_not_found_404(auth_client):
    resp = await auth_client.delete(f"/api/assessments/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Generate report ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_report_creates_report_record(auth_client, db_session, test_user, mock_generate_pdf):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.post(f"/api/assessments/{assessment.id}/generate-report")
    assert resp.status_code == 200
    mock_generate_pdf.assert_called_once()

    saved = await db_session.scalar(select(Report).where(Report.assessment_id == assessment.id))
    assert saved is not None


@pytest.mark.asyncio
async def test_generate_report_idempotent_skips_when_report_exists(auth_client, db_session, test_user, mock_generate_pdf):
    """
    Если report уже существует в БД - эндпоинт возвращает его и НЕ вызывает
    generate_pdf повторно. Тест создаёт report напрямую в БД (не через
    второй HTTP-вызов) - это избегает шаринга AsyncSession между тестовым
    кодом и приложением в рамках одного теста, которое в этой тестовой
    архитектуре (одна сессия на тест, нужна для rollback-изоляции, см.
    conftest.py) приводит к stale identity map и MissingGreenlet ошибкам
    при попытке имитировать два независимых HTTP-запроса. В проде каждый
    request получает новую AsyncSession - там такой проблемы нет.
    """
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    existing_report = Report(
        assessment_id=assessment.id,
        user_id=test_user.id,
        pdf_filename="existing.pdf",
    )
    db_session.add(existing_report)
    await db_session.flush()

    resp = await auth_client.post(f"/api/assessments/{assessment.id}/generate-report")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(existing_report.id)
    mock_generate_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_generate_report_other_user_forbidden(auth_client, db_session, test_admin, mock_generate_pdf):
    assessment = Assessment(user_id=test_admin.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.post(f"/api/assessments/{assessment.id}/generate-report")
    assert resp.status_code == 403
    mock_generate_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_generate_report_not_found_404(auth_client, mock_generate_pdf):
    resp = await auth_client.post(f"/api/assessments/{uuid.uuid4()}/generate-report")
    assert resp.status_code == 404


# ── Strategy lookup ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_assessment_strategy_returns_strategy(auth_client, db_session, test_user):
    strategy = Strategy(combination=VALID_COMBINATION, title="Тестовая стратегия", is_published=True)
    db_session.add(strategy)
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.get(f"/api/assessments/{assessment.id}/strategy")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Тестовая стратегия"


@pytest.mark.asyncio
async def test_get_assessment_strategy_method2_no_combination_404(auth_client, db_session, test_user):
    assessment = Assessment(user_id=test_user.id, method1_combination=None, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.get(f"/api/assessments/{assessment.id}/strategy")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_assessment_strategy_no_matching_strategy_404(auth_client, db_session, test_user):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    resp = await auth_client.get(f"/api/assessments/{assessment.id}/strategy")
    assert resp.status_code == 404


# -- Unknown-answers limit (MAX_UNKNOWNS_TOTAL = 3) ---------------------------

def _finance_with_unknowns(*item_ids: str) -> dict:
    """FINANCE_ANSWERS with given items set to None (max 1 per block)."""
    answers = dict(FINANCE_ANSWERS)
    for iid in item_ids:
        answers[iid] = None
    return answers


@pytest.mark.asyncio
async def test_create_assessment_four_unknowns_rejected(auth_client):
    resp = await auth_client.post("/api/assessments", json=assessment_payload(
        finance_answers=_finance_with_unknowns("1.4", "2.4", "3.4", "4.3"),
    ))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_assessment_three_unknowns_accepted_and_flagged(auth_client, db_session):
    resp = await auth_client.post("/api/assessments", json=assessment_payload(
        finance_answers=_finance_with_unknowns("1.4", "2.4", "3.4"),
    ))
    assert resp.status_code == 200

    saved = await db_session.scalar(
        select(Assessment).where(Assessment.id == resp.json()["id"])
    )
    assert saved.finance_result is not None
    assert "LOW_DATA_COMPLETENESS" in saved.finance_result["quality_flags"]

    partial = [ln for ln in saved.finance_result["lines"] if "PARTIAL_BLOCK" in ln["flags"]]
    assert len(partial) == 3
