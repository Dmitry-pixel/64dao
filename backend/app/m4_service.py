# -*- coding: utf-8 -*-
"""
Метод 4 — прогон анкеты: состав анкеты, проверка ответов, расчёт и снимок.

Связка между базой и чистым расчётом (m4_engine). Роутер знает про HTTP,
расчёт — про формулы, здесь — про то, какие вопросы в анкете, какой ответ
допустим и что пишется в снимок.

Анкета собирается из активного контента: выключенный в админке вопрос
пропадает из новых прогонов, но старые ответы на него остаются (вопросы
не удаляются). Условия показа (applies_when) проверяет тот же код, что
считает баллы, — иначе анкета и расчёт разошлись бы.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import m4_engine as engine
from app.m4_models import M4Answer, M4Card, M4Module, M4Question, M4Rule, M4Run, M4Snapshot
from app.models import CompanyProfile

# Порядок модулей в анкете (content/m4/modules.json → survey_order):
# от конкретного к абстрактному. Совпадение с контентом проверяет тест.
SURVEY_ORDER = [4, 6, 9, 10, 3, 8, 5, 7, 2, 1]

UNKNOWN = engine.UNKNOWN
NUMERIC = ("number", "money")


class AnswerError(ValueError):
    """Недопустимый ответ — 400 с понятным текстом."""


async def active_questions(db: AsyncSession, mode: str) -> list[M4Question]:
    q = (select(M4Question).options(selectinload(M4Question.options))
         .join(M4Module, M4Module.code == M4Question.module_code)
         .where(M4Question.is_active.is_(True), M4Module.is_active.is_(True)))
    if mode == "express":
        q = q.where(M4Question.tier == "u0")
    rows = (await db.execute(q)).scalars().all()
    pos = {m: i for i, m in enumerate(SURVEY_ORDER)}
    return sorted(rows, key=lambda x: (pos.get(x.module_code, 99), x.sort, x.code))


async def modules(db: AsyncSession) -> list[M4Module]:
    rows = (await db.execute(select(M4Module).where(M4Module.is_active.is_(True)))).scalars().all()
    pos = {m: i for i, m in enumerate(SURVEY_ORDER)}
    return sorted(rows, key=lambda m: pos.get(m.code, 99))


async def profile_of(db: AsyncSession, company_id) -> dict:
    p = await db.get(CompanyProfile, company_id)
    if p is None:
        return {}
    return {"revenue_model": p.revenue_model, "industry_id": p.industry_id, "revenue_range": p.revenue_range,
            "headcount": p.headcount, "active_clients": p.active_clients}


def to_engine_answers(rows: list[M4Answer]) -> dict[str, engine.Answer]:
    return {
        a.question_code: engine.Answer(
            value=a.value, number=None if a.numeric_value is None else float(a.numeric_value),
        )
        for a in rows
    }


def validate_answer(q: M4Question, value: str | None, number: float | None) -> tuple[str | None, float | None]:
    """(value, numeric_value) для записи или AnswerError.

    «Не знаю» — value='unknown' у любого типа, если вопрос его допускает.
    Числовой вопрос — только число в границах min/max; вариантный — только
    значение из списка вариантов."""
    if value == UNKNOWN:
        if not q.unknown_allowed:
            raise AnswerError(f"{q.code}: у этого вопроса нет варианта «Не знаю»")
        return UNKNOWN, None
    if q.type in NUMERIC:
        if number is None:
            raise AnswerError(f"{q.code}: нужно число")
        # Без явной нижней границы число не бывает отрицательным: позиции,
        # дни, доли. Отрицательные допускает только вопрос с min < 0.
        low = 0 if q.min_value is None else q.min_value
        if number < low:
            raise AnswerError(f"{q.code}: число меньше {low}")
        if q.max_value is not None and number > q.max_value:
            raise AnswerError(f"{q.code}: число больше {q.max_value}")
        return None, round(float(number), 2)
    allowed = {o.value for o in q.options}
    if value not in allowed:
        raise AnswerError(f"{q.code}: недопустимый вариант ответа")
    return value, None


def applicable(questions: list[M4Question], answers: dict[str, engine.Answer], profile: dict) -> list[str]:
    """Коды вопросов, которые сейчас задаются. Условие показа проверяется по
    тем же ответам, что пойдут в расчёт."""
    return [q.code for q in map(engine.question_from, questions) if engine.applies(q, answers, profile)]


def missing(questions: list[M4Question], answers: dict[str, engine.Answer], profile: dict) -> list[str]:
    """Вопросы, которые задаются, но без ответа."""
    return [c for c in applicable(questions, answers, profile) if c not in answers]


async def calculate(db: AsyncSession, run: M4Run) -> M4Snapshot:
    """Посчитать прогон и записать снимок. Вызывающий проверяет полноту
    анкеты и оплату; здесь — только расчёт и фиксация версий."""
    questions = await active_questions(db, run.mode)
    rules = (await db.execute(select(M4Rule).where(M4Rule.is_active.is_(True)))).scalars().all()
    cards = (await db.execute(
        select(M4Card).where(M4Card.is_active.is_(True), M4Card.kind == "recommendation")
    )).scalars().all()
    rows = (await db.execute(select(M4Answer).where(M4Answer.run_id == run.id))).scalars().all()
    profile = await profile_of(db, run.company_id)

    result = engine.calculate(
        [engine.question_from(q) for q in questions],
        to_engine_answers(list(rows)),
        mode=run.mode,
        profile=profile,
        rules=[engine.rule_from(r) for r in rules],
        recommendations=[r for r in (engine.recommendation_from(c) for c in cards) if r],
    )

    snap = await db.get(M4Snapshot, run.id)
    if snap is None:
        snap = M4Snapshot(run_id=run.id)
        db.add(snap)
    conf = result["confidence"]
    constraint = result.get("constraint")
    snap.calc_version = result["calc_version"]
    snap.module_scores = {str(m): v for m, v in result["modules"].items()}
    snap.constraint_module = constraint["module"] if constraint else None
    snap.constraint_detail = constraint
    snap.fired_rules = result.get("fired_rules", [])
    snap.unverified_rules = result.get("unverified_rules", [])
    snap.confidence_index = conf["index"]
    snap.confidence_components = {"level": conf["level"], **conf["components"]}
    snap.resistance_factor = result.get("resistance", 1.0)
    snap.priority_queue = result.get("priority_queue", [])
    snap.top_gaps = result["top_gaps"]
    snap.cause_effect = result.get("cause_effect")
    snap.metrics = result["metrics"] or None
    snap.reduced = run.reduced

    run.profile_snapshot = profile or None
    run.item_versions = {
        "questions": {q.code: q.item_version for q in questions},
        "rules": {r.code: r.rule_version for r in rules},
        "cards": {c.key: c.item_version for c in cards},
    }
    run.status = "calculated"
    run.calculated_at = datetime.now(UTC)
    return snap
