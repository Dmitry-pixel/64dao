"""Схема прогонов Метода 4: ограничения, которые защищают оплату и повтор.

Ограничения живут в базе, а не только в коде: код прогона ещё не написан,
и база — единственное, что сегодня не даст записать неверные данные.
"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.m4_models import M4Answer, M4Module, M4Question, M4Run, M4Snapshot
from app.models import Company, CompanyProfile


async def _company(db, user):
    c = Company(id=uuid.uuid4(), user_id=user.id, name=f"ООО {uuid.uuid4().hex[:6]}")
    db.add(c)
    await db.flush()
    return c


async def _question(db, code="M01-Q01"):
    db.add(M4Module(code=1, slug="capital", name="Капитал", client_question="?", why_it_matters="!"))
    await db.flush()
    db.add(M4Question(code=code, module_code=1, text="Вопрос", type="bool", tier="u0"))
    await db.flush()


async def _expect_integrity_error(db, obj, constraint):
    """Запись отклонена именно этим ограничением, а не каким-то другим."""
    db.add(obj)
    with pytest.raises(IntegrityError) as exc:
        async with db.begin_nested():
            await db.flush()
    assert constraint in str(exc.value)


async def test_full_run_with_answers_and_snapshot(db_session, test_user):
    company = await _company(db_session, test_user)
    await _question(db_session)
    db_session.add(CompanyProfile(company_id=company.id, revenue_model="repeat"))
    run = M4Run(user_id=test_user.id, company_id=company.id, mode="full", followup_allowed=1)
    db_session.add(run)
    await db_session.flush()
    db_session.add(M4Answer(run_id=run.id, question_code="M01-Q01", value="unknown"))
    db_session.add(M4Snapshot(
        run_id=run.id, calc_version="m4-1", module_scores={"1": 50}, constraint_module=1,
        fired_rules=[], confidence_index=80, confidence_components={}, resistance_factor=1.5,
        priority_queue=[],
    ))
    await db_session.flush()
    assert run.status == "draft"


async def test_express_run_cannot_be_paid(db_session, test_user):
    company = await _company(db_session, test_user)
    await _expect_integrity_error(db_session, M4Run(
        user_id=test_user.id, company_id=company.id, mode="express", grant_id=uuid.uuid4(),
    ), "chk_m4_run_express_unpaid")


async def test_followup_needs_parent(db_session, test_user):
    company = await _company(db_session, test_user)
    await _expect_integrity_error(db_session, M4Run(
        user_id=test_user.id, company_id=company.id, mode="full", is_followup=True,
    ), "chk_m4_run_followup_parent")


async def test_followup_used_cannot_exceed_allowed(db_session, test_user):
    company = await _company(db_session, test_user)
    await _expect_integrity_error(db_session, M4Run(
        user_id=test_user.id, company_id=company.id, mode="full",
        followup_allowed=1, followup_used=2,
    ), "chk_m4_run_followup_used")


async def test_answer_must_reference_existing_question(db_session, test_user):
    company = await _company(db_session, test_user)
    run = M4Run(user_id=test_user.id, company_id=company.id, mode="express")
    db_session.add(run)
    await db_session.flush()
    await _expect_integrity_error(db_session, M4Answer(run_id=run.id, question_code="M99-Q99", value="yes"),
                                  "m4_answers_question_code_fkey")


async def test_finance_module_is_never_the_constraint(db_session, test_user):
    """Модуль 10 — следствие остальных девяти и ограничением быть не может."""
    company = await _company(db_session, test_user)
    run = M4Run(user_id=test_user.id, company_id=company.id, mode="express")
    db_session.add(run)
    await db_session.flush()
    await _expect_integrity_error(db_session, M4Snapshot(
        run_id=run.id, calc_version="m4-1", module_scores={}, constraint_module=10,
        fired_rules=[], confidence_index=50, confidence_components={}, resistance_factor=1.0,
        priority_queue=[],
    ), "chk_m4_snapshot_constraint_module")
