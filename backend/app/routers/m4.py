# -*- coding: utf-8 -*-
"""
Метод 4 «Алмазное колесо» — прогоны анкеты для клиента.

Порядок работы клиента:
  1. POST /runs                    — начать экспресс или полную диагностику компании;
  2. GET  /questionnaire?mode=…    — вопросы по модулям;
  3. PUT  /runs/{id}/answers       — ответы порциями, сколько угодно раз до расчёта;
  4. POST /runs/{id}/calculate     — расчёт; у полной здесь же списание из пакета;
  5. GET  /runs/{id}/result        — снимок результата (отчёт строится из него).

Раздел живёт под тем же флагом фичи, что Метод 3 (m3_enabled): оба метода
продаются одним пакетом и открываются вместе.

В ответы клиенту не уходят баллы вариантов, source_ref и внутренние заметки:
первое сделало бы анкету «угадываемой», второе — ссылки на источник, которые
видит только администратор.
"""
from __future__ import annotations

import json
import logging
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app import m4_access as access
from app import m4_pdf, m4_report
from app import m4_service as svc
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.m4_models import M4Answer, M4Run, M4Snapshot
from app.models import REVENUE_MODELS, REVENUE_RANGES, Company, CompanyProfile, User

PROFILE_FILE = Path(__file__).resolve().parents[2] / "content" / "m4" / "company-profile.json"


async def _flag_gate() -> None:
    """Тот же гейт, что у Метода 3: при выключенном флаге раздела нет (404)."""
    if not get_settings().m3_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


router = APIRouter(prefix="/api/m4", tags=["m4"], dependencies=[Depends(_flag_gate)])


# ── Схемы ─────────────────────────────────────────────────────────────────────
class ProfileIn(BaseModel):
    revenue_model: Literal["one_off", "repeat", "subscription"]
    industry_id: int | None = None
    revenue_range: Literal["lt_10m", "10_50m", "50_300m", "gt_300m"] | None = None
    headcount: int | None = Field(default=None, ge=0)
    active_clients: int | None = Field(default=None, ge=0)


class RunCreate(BaseModel):
    mode: Literal["express", "full"]
    company_id: uuid.UUID | None = None
    company_name: str | None = Field(default=None, max_length=255)
    profile: ProfileIn | None = None


class AnswerIn(BaseModel):
    code: str = Field(max_length=8)
    value: str | None = Field(default=None, max_length=32)
    number: float | None = None


class AnswersIn(BaseModel):
    answers: list[AnswerIn] = Field(max_length=200)


# ── Помощники ─────────────────────────────────────────────────────────────────
def _profile_options() -> dict:
    """Подписи полей профиля — из контента, чтобы форма не держала копию."""
    data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    fields = {f["code"]: f for f in data.get("required", []) + data.get("optional", [])}
    return {code: f.get("options") for code, f in fields.items() if f.get("options")}


async def _company(db: AsyncSession, user: User, company_id, company_name) -> Company:
    if company_id:
        c = await db.scalar(select(Company).where(Company.id == company_id, Company.user_id == user.id))
        if c is None:
            raise HTTPException(status_code=404, detail="Компания не найдена")
        return c
    name = (company_name or user.company_name or "").strip() or "Без названия"
    c = await db.scalar(select(Company).where(Company.user_id == user.id, Company.name == name))
    if c is None:
        c = Company(user_id=user.id, name=name)
        db.add(c)
        await db.flush()
    return c


async def _save_profile(db: AsyncSession, company: Company, body: ProfileIn) -> CompanyProfile:
    p = await db.get(CompanyProfile, company.id)
    if p is None:
        p = CompanyProfile(company_id=company.id, revenue_model=body.revenue_model)
        db.add(p)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    await db.flush()
    return p


async def _owned(db: AsyncSession, run_id: uuid.UUID, user: User) -> M4Run:
    run = await db.scalar(select(M4Run).where(M4Run.id == run_id, M4Run.deleted_at.is_(None)))
    if run is None:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    if run.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")
    return run


async def _answers(db: AsyncSession, run: M4Run) -> list[M4Answer]:
    return list((await db.execute(select(M4Answer).where(M4Answer.run_id == run.id))).scalars().all())


async def _progress(db: AsyncSession, run: M4Run) -> dict:
    questions = await svc.active_questions(db, run.mode)
    answers = svc.to_engine_answers(await _answers(db, run))
    profile = await svc.profile_of(db, run.company_id)
    asked = svc.applicable(questions, answers, profile)
    return {"answered": sum(c in answers for c in asked), "required": len(asked),
            "missing": [c for c in asked if c not in answers]}


async def _run_out(db: AsyncSession, run: M4Run, *, with_answers: bool = False) -> dict:
    company = await db.get(Company, run.company_id)
    out = {
        "id": run.id, "mode": run.mode, "status": run.status,
        "company_id": run.company_id, "company_name": company.name if company else None,
        "is_followup": run.is_followup, "reduced": run.reduced,
        "created_at": run.created_at, "calculated_at": run.calculated_at,
        "progress": await _progress(db, run),
    }
    if with_answers:
        out["answers"] = [
            {"code": a.question_code, "value": a.value,
             "number": None if a.numeric_value is None else float(a.numeric_value), "source": a.source}
            for a in await _answers(db, run)
        ]
    return out


# ── Анкета ────────────────────────────────────────────────────────────────────
@router.get("/questionnaire")
async def questionnaire(
    mode: Literal["express", "full"] = Query("full"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    questions = await svc.active_questions(db, mode)
    by_module: dict[int, list] = {}
    for q in questions:
        by_module.setdefault(q.module_code, []).append({
            "code": q.code, "text": q.text, "type": q.type, "unit": q.unit, "is_fact": q.is_fact,
            "unknown_allowed": q.unknown_allowed, "min": q.min_value, "max": q.max_value,
            "applies_when": q.applies_when,
            "options": [{"value": o.value, "label": o.label} for o in sorted(q.options, key=lambda o: o.sort)],
        })
    return {
        "mode": mode,
        "modules": [
            {"code": m.code, "name": m.name, "client_question": m.client_question, "intro": m.intro,
             "questions": by_module[m.code]}
            for m in await svc.modules(db) if m.code in by_module
        ],
        "profile_options": _profile_options(),
    }


@router.get("/credits")
async def credits(
    company_name: str | None = Query(None, max_length=255),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Что доступно пользователю; null — без ограничения.

    full_available — полные диагностики из пакета; express_available —
    бесплатные экспрессы; followup_available — есть ли у компании с этим
    названием неиспользованный повтор (тогда полная не требует пакета)."""
    followup = False
    name = (company_name or "").strip()
    if name:
        company = await db.scalar(select(Company).where(Company.user_id == user.id, Company.name == name))
        followup = bool(company and await access.find_primary(db, user, company.id))
    return {
        "full_available": await access.credits(db, user),
        "express_available": await access.express_left(db, user),
        "followup_available": followup,
    }


# ── Профиль компании ──────────────────────────────────────────────────────────
@router.get("/companies/{company_id}/profile")
async def get_profile(company_id: uuid.UUID, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    company = await _company(db, user, company_id, None)
    return await svc.profile_of(db, company.id) or None


@router.put("/companies/{company_id}/profile")
async def put_profile(company_id: uuid.UUID, body: ProfileIn, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    company = await _company(db, user, company_id, None)
    await _save_profile(db, company, body)
    return await svc.profile_of(db, company.id)


# ── Прогоны ───────────────────────────────────────────────────────────────────
@router.post("/runs", status_code=201)
async def create_run(body: RunCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    company = await _company(db, user, body.company_id, body.company_name)
    if body.profile is not None:
        await _save_profile(db, company, body.profile)
    profile = await svc.profile_of(db, company.id)

    # Незаконченная диагностика той же компании и того же вида продолжается,
    # а не заводится вторая: иначе в кабинете копятся пустые черновики.
    # Проверка черновика — до лимитов: продолжить начатое можно всегда.
    draft = await db.scalar(
        select(M4Run).where(M4Run.user_id == user.id, M4Run.company_id == company.id,
                            M4Run.mode == body.mode, M4Run.status != "calculated",
                            M4Run.deleted_at.is_(None))
        .order_by(M4Run.created_at.desc())
    )
    if draft is not None:
        out = await _run_out(db, draft, with_answers=True)
        await db.commit()      # профиль мог измениться — анкета читает его сразу
        return out

    primary = None
    if body.mode == "full":
        # Профиль обязателен: от модели выручки зависят вопросы модуля 4.
        if not profile:
            raise HTTPException(status_code=400, detail="Укажите, как устроена оплата у компании")
        # Повтор входит в стоимость первичной диагностики и пакета не требует.
        primary = await access.find_primary(db, user, company.id)
        if primary is None:
            # Проверка до анкеты, а не только на расчёте: иначе клиент
            # заполнит 120 вопросов и узнает, что пакет не оплачен.
            left = await access.credits(db, user)
            if left is not None and left <= 0:
                raise HTTPException(status_code=403, detail=access.NO_CREDITS)
    else:
        left = await access.express_left(db, user)
        if left is not None and left <= 0:
            raise HTTPException(status_code=403, detail=access.NO_EXPRESS)

    run = M4Run(user_id=user.id, company_id=company.id, mode=body.mode, status="draft",
                is_followup=primary is not None, parent_run_id=primary.id if primary else None)
    db.add(run)
    await db.flush()

    # Повтор отвечает заново, без подстановки прошлых ответов: он нужен,
    # чтобы измерить изменение, а подставленные ответы его бы скрыли.
    if body.mode == "full" and primary is None:
        # Ответы последнего экспресса этой компании переносятся: это те же
        # 20 вопросов, клиент не должен отвечать на них второй раз.
        express = await db.scalar(
            select(M4Run).where(M4Run.company_id == company.id, M4Run.mode == "express",
                                M4Run.user_id == user.id, M4Run.deleted_at.is_(None))
            .order_by(M4Run.created_at.desc())
        )
        if express is not None:
            for a in await _answers(db, express):
                db.add(M4Answer(run_id=run.id, question_code=a.question_code, value=a.value,
                                numeric_value=a.numeric_value, source="direct", item_version=a.item_version))
            await db.flush()
    out = await _run_out(db, run, with_answers=True)
    await db.commit()          # см. calculate_run: клиент сразу открывает анкету
    return out


@router.get("/runs")
async def list_runs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    runs = (await db.execute(
        select(M4Run).where(M4Run.user_id == user.id, M4Run.deleted_at.is_(None))
        .order_by(M4Run.created_at.desc())
    )).scalars().all()
    return [await _run_out(db, r) for r in runs]


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _run_out(db, await _owned(db, run_id, user), with_answers=True)


@router.put("/runs/{run_id}/answers")
async def put_answers(run_id: uuid.UUID, body: AnswersIn, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """Записать ответы порцией. value и number оба пустые — снять ответ
    (клиент передумал в вопросе-условии, и зависимый вопрос исчез)."""
    run = await _owned(db, run_id, user)
    if run.status == "calculated":
        raise HTTPException(status_code=409, detail="Диагностика уже рассчитана, ответы не меняются")
    questions = {q.code: q for q in await svc.active_questions(db, run.mode)}
    existing = {a.question_code: a for a in await _answers(db, run)}
    for item in body.answers:
        q = questions.get(item.code)
        if q is None:
            raise HTTPException(status_code=400, detail=f"{item.code}: вопроса нет в этой анкете")
        if item.value is None and item.number is None:
            if item.code in existing:
                await db.delete(existing.pop(item.code))
            continue
        try:
            value, number = svc.validate_answer(q, item.value, item.number)
        except svc.AnswerError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        row = existing.get(item.code)
        if row is None:
            row = M4Answer(run_id=run.id, question_code=q.code)
            db.add(row)
            existing[q.code] = row
        row.value, row.numeric_value, row.source, row.item_version = value, number, "direct", q.item_version
    await db.flush()
    progress = await _progress(db, run)
    run.status = "filled" if not progress["missing"] else "draft"
    await db.flush()
    out = await _run_out(db, run)
    await db.commit()          # см. calculate_run: за сохранением сразу идёт расчёт
    return out


@router.post("/runs/{run_id}/calculate")
async def calculate_run(run_id: uuid.UUID, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    run = await _owned(db, run_id, user)
    if run.status == "calculated":
        raise HTTPException(status_code=409, detail="Диагностика уже рассчитана")
    progress = await _progress(db, run)
    if progress["missing"]:
        raise HTTPException(status_code=400, detail={
            "message": "Ответьте на все вопросы анкеты — «Не знаю» тоже ответ",
            "missing": progress["missing"],
        })
    if run.mode == "express":
        left = await access.express_left(db, user)
        if left is not None and left <= 0:
            raise HTTPException(status_code=403, detail=access.NO_EXPRESS)
    parent = None
    if run.is_followup:
        # Право могли израсходовать другим прогоном или снять возвратом, пока
        # анкета заполнялась. Тогда это обычная платная диагностика.
        parent = await db.get(M4Run, run.parent_run_id) if run.parent_run_id else None
        if parent is None or (user.role != "admin" and parent.followup_used >= parent.followup_allowed):
            run.is_followup, run.parent_run_id, parent = False, None, None
    grant, order = await access.reserve_payment(db, run, user)
    snap = await svc.calculate(db, run)
    access.attach_payment(run, grant, order)
    if parent is not None:
        access.use_followup(parent)
    elif run.mode == "full" and grant is None:
        # Первичная полная диагностика приносит право на один повтор, как у
        # Метода 1. Грантовая — нет: квота гранта должна совпадать с числом
        # прогонов (решение D1).
        run.followup_allowed = 1
    # Явный commit до ответа: get_db коммитит в завершении зависимости, и
    # следующий запрос клиента (страница отчёта сразу после расчёта) мог
    # успеть раньше и увидеть прогон нерассчитанным — отчёт отвечал 403.
    await db.commit()
    return _snapshot_out(run, snap)


@router.get("/runs/{run_id}/result")
async def get_result(run_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _owned(db, run_id, user)
    access.ensure_result_access(run, user)
    snap = await db.get(M4Snapshot, run.id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Результата нет")
    return _snapshot_out(run, snap)


@router.get("/runs/{run_id}/report")
async def get_report(run_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Отчёт: снимок расчёта с текстами карточек и правил. Один источник
    для веба и PDF."""
    run = await _owned(db, run_id, user)
    access.ensure_result_access(run, user)
    snap = await db.get(M4Snapshot, run.id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Результата нет")
    return await m4_report.build(db, run, snap)


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logging.getLogger(__name__).warning("Не удалось удалить временный PDF Метода 4 %s: %s", path, exc)


@router.get("/runs/{run_id}/pdf")
async def get_pdf(run_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """PDF отчёта. Собирается на каждый запрос из той же структуры, что веб
    (m4_report.build), и не хранится: снимок не меняется, поэтому повторная
    сборка даёт тот же документ, а тексты карточек — текущие, как в вебе."""
    from app.m3_pdf import PDF_MARGIN, footer_template, header_template
    from app.pdf import generate_pdf

    run = await _owned(db, run_id, user)
    access.ensure_result_access(run, user)
    snap = await db.get(M4Snapshot, run.id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Результата нет")
    rep = await m4_report.build(db, run, snap)
    company = rep["run"].get("company_name") or "Компания"

    path = Path(tempfile.gettempdir()) / f"dao64-m4-{run_id}-{uuid.uuid4().hex}.pdf"
    await generate_pdf(m4_pdf.build_report_html(rep), str(path),
                       header_html=header_template(company), footer_html=footer_template(), margin=PDF_MARGIN)
    filename = f"64dao-almaznoe-koleso-{run_id}.pdf"
    return FileResponse(
        path=str(path), media_type="application/pdf", filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        background=BackgroundTask(_unlink_quietly, path),
    )


@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(run_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Скрыть диагностику. Факт расчёта остаётся: удаление не возвращает
    оплаченную диагностику в пакет."""
    run = await _owned(db, run_id, user)
    run.deleted_at = datetime.now(UTC)
    await db.flush()


def _snapshot_out(run: M4Run, s: M4Snapshot) -> dict:
    return {
        "run_id": run.id, "mode": run.mode, "calc_version": s.calc_version,
        "modules": s.module_scores, "top_gaps": s.top_gaps,
        "constraint": s.constraint_detail, "cause_effect": s.cause_effect,
        "fired_rules": s.fired_rules, "unverified_rules": s.unverified_rules,
        "confidence": {"index": s.confidence_index, **s.confidence_components},
        "resistance": float(s.resistance_factor), "priority_queue": s.priority_queue,
        "metrics": s.metrics, "reduced": s.reduced, "calculated_at": run.calculated_at,
    }


# Валидация значений профиля живёт в ProfileIn (Literal); кортежи моделей
# импортируются, чтобы тест сверил их с Literal и они не разошлись.
PROFILE_VALUES = {"revenue_model": REVENUE_MODELS, "revenue_range": REVENUE_RANGES}
