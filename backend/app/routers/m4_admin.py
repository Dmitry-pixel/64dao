# -*- coding: utf-8 -*-
"""
Метод 4 «Алмазное колесо» — админка контента.

Правило раздела: контент правится здесь, логика живёт в коде.
  - Тексты модулей, вопросов, вариантов, карточек, правил, конструктов и
    цепочек правятся свободно.
  - Коды (вопроса, варианта, правила, карточки) не правятся никогда: на них
    ссылаются условия правил и сохранённые ответы.
  - Условия правил, граф зависимостей и формула приоритизации — только для
    чтения: это программа, а не текст.
  - Удалять нельзя, выключать можно. Выключить вопрос, на который ссылается
    активное правило, цепочка или контрольная пара, нельзя — ответ 409 с
    перечнем того, что мешает.

Правка формулировки поднимает версию (item_version / rule_version): прошлые
отчёты хранят версии в снимке, и динамика не примет смену формулировки за
изменение в бизнесе.

Доступ — require_admin на роутере. Флаг показа Метода 4 пользователям здесь
не проверяется: тексты правят до релиза.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_admin
from app.db import get_db
from app.m4_models import (
    M4Card,
    M4Construct,
    M4Module,
    M4Question,
    M4Rule,
    M4SymptomChain,
)

router = APIRouter(prefix="/api/admin/m4", tags=["m4-admin"],
                   dependencies=[Depends(require_admin)])


def _apply(row, data: dict, versioned: tuple[str, ...] = (), version_attr: str | None = None) -> list[str]:
    """Переносит в строку только переданные поля. Возвращает изменённые.
    Если среди них есть поле из versioned — поднимает версию."""
    changed = [k for k, v in data.items() if getattr(row, k) != v]
    for k in changed:
        setattr(row, k, data[k])
    if version_attr and any(k in versioned for k in changed):
        setattr(row, version_attr, getattr(row, version_attr) + 1)
    return changed


def _patch(body: BaseModel, nullable: tuple[str, ...] = ()) -> dict:
    """Только переданные поля. null принимается лишь для полей, которые в
    базе могут быть пустыми: пустой заголовок или вес запись бы уронили."""
    return {k: v for k, v in body.model_dump(exclude_unset=True).items()
            if v is not None or k in nullable}


# ── Модули ────────────────────────────────────────────────────────────────────
class ModuleOut(BaseModel):
    model_config = {"from_attributes": True}
    code: int
    slug: str
    name: str
    client_question: str
    why_it_matters: str
    intro: str | None
    is_effect: bool
    sort: int
    is_active: bool


class ModulePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    client_question: str | None = Field(default=None, min_length=1)
    why_it_matters: str | None = Field(default=None, min_length=1)
    intro: str | None = None


@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(M4Module).order_by(M4Module.sort))).scalars().all()


@router.put("/modules/{code}", response_model=ModuleOut)
async def put_module(code: int, body: ModulePatch, db: AsyncSession = Depends(get_db)):
    row = await db.get(M4Module, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Модуль не найден")
    _apply(row, _patch(body, nullable=("intro",)))
    await db.flush()
    return row


# ── Вопросы и варианты ────────────────────────────────────────────────────────
class OptionOut(BaseModel):
    model_config = {"from_attributes": True}
    value: str
    label: str
    score: int | None
    sort: int


class QuestionOut(BaseModel):
    model_config = {"from_attributes": True}
    code: str
    module_code: int
    text: str
    type: str
    unit: str | None
    weight: int
    is_fact: bool
    tier: str
    reverse: bool
    score_neutral: bool
    score_excluded: bool
    affects: str | None
    unknown_allowed: bool
    unknown_score: int | None
    unknown_confidence_penalty: int
    metric_code: str | None
    control_pair: str | None
    applies_when: dict | None
    construct_code: str | None
    source_ref: str | None
    note_internal: str | None
    min_value: int | None
    max_value: int | None
    item_version: int
    sort: int
    is_active: bool
    options: list[OptionOut]


class QuestionPatch(BaseModel):
    """Свободно правится: text, weight, tier, sort, unit, границы, заметка.
    С предупреждением на экране: reverse и поведение «Не знаю» — меняют балл."""
    text: str | None = Field(default=None, min_length=1)
    weight: int | None = Field(default=None, ge=1, le=3)
    tier: str | None = Field(default=None, pattern="^u[01]$")
    sort: int | None = None
    unit: str | None = Field(default=None, max_length=32)
    min_value: int | None = None
    max_value: int | None = None
    note_internal: str | None = None
    reverse: bool | None = None
    unknown_allowed: bool | None = None
    unknown_score: int | None = Field(default=None, ge=0, le=100)
    unknown_confidence_penalty: int | None = Field(default=None, ge=0, le=3)


class ActivePatch(BaseModel):
    is_active: bool


class OptionPatch(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    score: int | None = Field(default=None, ge=0, le=100)
    sort: int | None = None


# Поля, изменение которых делает старые ответы несопоставимыми с новыми.
QUESTION_VERSIONED = ("text", "reverse", "unknown_allowed", "unknown_score")


async def _question(db: AsyncSession, code: str) -> M4Question:
    row = await db.scalar(
        select(M4Question).options(selectinload(M4Question.options)).where(M4Question.code == code))
    if row is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return row


def _rule_questions(node, out: set) -> None:
    if isinstance(node, dict):
        if "q" in node:
            out.add(node["q"])
            if node.get("op") == "gt_question":
                out.add(node.get("value"))
        for v in node.values():
            _rule_questions(v, out)
    elif isinstance(node, list):
        for v in node:
            _rule_questions(v, out)


async def question_dependents(db: AsyncSession, code: str) -> list[str]:
    """Кто опирается на вопрос: активные правила, цепочки, контрольные пары
    и условия показа других вопросов."""
    out = []
    for r in (await db.execute(select(M4Rule).where(M4Rule.is_active.is_(True)))).scalars():
        refs: set = set()
        _rule_questions(r.conditions, refs)
        if code in refs:
            out.append(f"правило {r.code}")
    for c in (await db.execute(select(M4SymptomChain).where(M4SymptomChain.is_active.is_(True)))).scalars():
        if code in (c.detected_by or []) or code in (c.check_questions or []):
            out.append(f"цепочка «{c.label}»")
    for q in (await db.execute(select(M4Question).where(M4Question.is_active.is_(True)))).scalars():
        if q.code == code:
            continue
        if q.control_pair == code:
            out.append(f"контрольная пара {q.code}")
        if code in (q.applies_when or {}):
            out.append(f"условие показа {q.code}")
    return out


@router.get("/questions", response_model=list[QuestionOut])
async def list_questions(module: int | None = None, db: AsyncSession = Depends(get_db)):
    stmt = (select(M4Question).options(selectinload(M4Question.options))
            .order_by(M4Question.module_code, M4Question.sort))
    if module is not None:
        stmt = stmt.where(M4Question.module_code == module)
    return (await db.execute(stmt)).scalars().all()


@router.put("/questions/{code}", response_model=QuestionOut)
async def put_question(code: str, body: QuestionPatch, db: AsyncSession = Depends(get_db)):
    row = await _question(db, code)
    data = _patch(body, nullable=("unit", "min_value", "max_value", "note_internal", "unknown_score"))
    if data.get("unknown_allowed") is False:
        data["unknown_score"] = None
    lo = data.get("min_value", row.min_value)
    hi = data.get("max_value", row.max_value)
    if lo is not None and hi is not None and lo > hi:
        raise HTTPException(status_code=400, detail="Нижняя граница больше верхней")
    if row.affects and data.get("unknown_score") is not None:
        raise HTTPException(status_code=400, detail="Вопрос не идёт в балл: балл для «Не знаю» ему не задаётся")
    _apply(row, data, QUESTION_VERSIONED, "item_version")
    await db.flush()
    return row


@router.put("/questions/{code}/active", response_model=QuestionOut)
async def put_question_active(code: str, body: ActivePatch, db: AsyncSession = Depends(get_db)):
    row = await _question(db, code)
    if not body.is_active and row.is_active:
        deps = await question_dependents(db, code)
        if deps:
            raise HTTPException(status_code=409, detail="Вопрос нельзя выключить: на него опираются "
                                + ", ".join(deps) + ". Сначала выключите их.")
    row.is_active = body.is_active
    await db.flush()
    return row


@router.put("/questions/{code}/options/{value}", response_model=QuestionOut)
async def put_option(code: str, value: str, body: OptionPatch, db: AsyncSession = Depends(get_db)):
    row = await _question(db, code)
    opt = next((o for o in row.options if o.value == value), None)
    if opt is None:
        raise HTTPException(status_code=404, detail="Вариант не найден")
    changed = _apply(opt, _patch(body))
    # Подпись и балл варианта — часть смысла вопроса: старые ответы с новыми
    # сравнивать уже нельзя.
    if {"label", "score"} & set(changed):
        row.item_version += 1
    await db.flush()
    await db.refresh(row, attribute_names=["options"])
    return row


# ── Карточки отчёта ───────────────────────────────────────────────────────────
class CardOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    kind: str
    key: str
    module_code: int | None
    state: str | None
    rule_code: str | None
    title: str
    body: str
    mistake: str | None
    steps: list[str] | None
    first_step: str | None
    how_to_check: str | None
    effect: int | None
    speed_weeks: int | None
    cost: int | None
    item_version: int
    sort: int
    is_active: bool


class CardPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    body: str | None = Field(default=None, min_length=1)
    mistake: str | None = None
    steps: list[str] | None = None
    first_step: str | None = None
    how_to_check: str | None = None
    effect: int | None = Field(default=None, ge=1, le=3)
    speed_weeks: int | None = Field(default=None, ge=1, le=104)
    cost: int | None = Field(default=None, ge=1, le=3)
    sort: int | None = None
    is_active: bool | None = None


CARD_VERSIONED = ("title", "body", "mistake", "steps", "first_step", "how_to_check")


@router.get("/cards", response_model=list[CardOut])
async def list_cards(kind: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(M4Card).order_by(M4Card.kind, M4Card.module_code, M4Card.sort, M4Card.key)
    if kind:
        stmt = stmt.where(M4Card.kind == kind)
    return (await db.execute(stmt)).scalars().all()


@router.put("/cards/{card_id}", response_model=CardOut)
async def put_card(card_id: uuid.UUID, body: CardPatch, db: AsyncSession = Depends(get_db)):
    row = await db.get(M4Card, card_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    data = _patch(body, nullable=("mistake", "steps", "first_step", "how_to_check",
                                  "effect", "speed_weeks", "cost"))
    if "steps" in data and data["steps"] is not None:
        data["steps"] = [s.strip() for s in data["steps"] if s.strip()] or None
    if row.kind == "recommendation":
        for f in ("effect", "speed_weeks", "cost"):
            if f in data and data[f] is None:
                raise HTTPException(status_code=400,
                                    detail="У рекомендации оценки эффекта, срока и затрат обязательны: "
                                           "по ним строится очередь действий")
    _apply(row, data, CARD_VERSIONED, "item_version")
    await db.flush()
    return row


# ── Правила противоречий ──────────────────────────────────────────────────────
class RuleOut(BaseModel):
    model_config = {"from_attributes": True}
    code: str
    title: str
    severity: str
    conditions: dict
    diagnosis: str
    what_happens: str
    fix_one_of: list[str]
    cost_of_inaction: str
    source_ref: str | None
    is_mvp: bool
    rule_version: int
    sort: int
    is_active: bool


class RulePatch(BaseModel):
    """Условие срабатывания (conditions) сюда не входит: это логика."""
    title: str | None = Field(default=None, min_length=1, max_length=160)
    severity: str | None = Field(default=None, pattern="^(high|medium|low)$")
    diagnosis: str | None = Field(default=None, min_length=1)
    what_happens: str | None = Field(default=None, min_length=1)
    fix_one_of: list[str] | None = None
    cost_of_inaction: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


@router.get("/rules", response_model=list[RuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(M4Rule).order_by(M4Rule.sort))).scalars().all()


@router.put("/rules/{code}", response_model=RuleOut)
async def put_rule(code: str, body: RulePatch, db: AsyncSession = Depends(get_db)):
    row = await db.get(M4Rule, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    data = _patch(body)
    if "fix_one_of" in data:
        data["fix_one_of"] = [s.strip() for s in (data["fix_one_of"] or []) if s.strip()]
        if not data["fix_one_of"]:
            raise HTTPException(status_code=400, detail="Нужен хотя бы один вариант решения")
    _apply(row, data)
    await db.flush()
    return row


# ── Реестр конструктов ────────────────────────────────────────────────────────
class LinkOut(BaseModel):
    model_config = {"from_attributes": True}
    method: str
    item_code: str
    reverse: bool
    dynamic: bool
    free_text: bool


class ConstructOut(BaseModel):
    model_config = {"from_attributes": True}
    code: str
    name: str
    unit: str
    reusable: bool
    cross_check: str | None
    cross_check_why: str | None
    note: str | None
    sort: int
    is_active: bool
    links: list[LinkOut]


class ConstructPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = None
    cross_check_why: str | None = None
    reusable: bool | None = None
    cross_check: str | None = Field(default=None, pattern="^(always|single_direction_only|no)$")
    is_active: bool | None = None


@router.get("/constructs", response_model=list[ConstructOut])
async def list_constructs(db: AsyncSession = Depends(get_db)):
    return (await db.execute(
        select(M4Construct).options(selectinload(M4Construct.links)).order_by(M4Construct.sort)
    )).scalars().all()


@router.put("/constructs/{code}", response_model=ConstructOut)
async def put_construct(code: str, body: ConstructPatch, db: AsyncSession = Depends(get_db)):
    row = await db.scalar(
        select(M4Construct).options(selectinload(M4Construct.links)).where(M4Construct.code == code))
    if row is None:
        raise HTTPException(status_code=404, detail="Конструкт не найден")
    _apply(row, _patch(body, nullable=("note", "cross_check_why", "cross_check")))
    await db.flush()
    return row


# ── Цепочки симптомов ─────────────────────────────────────────────────────────
class ChainOut(BaseModel):
    model_config = {"from_attributes": True}
    code: str
    label: str
    detected_by: list[str]
    chain: list[str]
    root_modules: list[int]
    check_questions: list[str]
    first_action: str
    note: str | None
    sort: int
    is_active: bool


class ChainPatch(BaseModel):
    """detected_by, root_modules, check_questions — структура, не текст."""
    label: str | None = Field(default=None, min_length=1, max_length=160)
    chain: list[str] | None = None
    first_action: str | None = Field(default=None, min_length=1)
    note: str | None = None
    is_active: bool | None = None


@router.get("/chains", response_model=list[ChainOut])
async def list_chains(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(M4SymptomChain).order_by(M4SymptomChain.sort))).scalars().all()


@router.put("/chains/{code}", response_model=ChainOut)
async def put_chain(code: str, body: ChainPatch, db: AsyncSession = Depends(get_db)):
    row = await db.get(M4SymptomChain, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Цепочка не найдена")
    data = _patch(body, nullable=("note",))
    if "chain" in data:
        data["chain"] = [s.strip() for s in (data["chain"] or []) if s.strip()]
        if not data["chain"]:
            raise HTTPException(status_code=400, detail="Цепочка не может быть пустой")
    _apply(row, data)
    await db.flush()
    return row

