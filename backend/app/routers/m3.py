# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — роутер.

Отдельный роутер и отдельный раздел API: /assessment остаётся единственной
точкой входа Метода 1, маршрутизация Методов 1 и 2 не трогается.

Флаг фичи m3_enabled: при false роутер зарегистрирован, но все эндпоинты
отдают 404. Это позволяет катить код на прод, не открывая функциональность,
и снимать флаг отдельным действием — как enforce_credits.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import m3_service as svc
from app.auth import get_current_user, require_admin
from app.config import get_settings
from app.db import get_db
from app.m3_models import (
    M3ChecklistStep, M3Content, M3Hint, M3Item, M3Object, M3Portfolio,
    M3TradeoffDecision, M3Weight,
)
from app.m3_schemas import (
    M3AnswersIn, M3ArbiterOut, M3ChecklistStepOut, M3ChecklistToggle,
    M3ContentUpsert, M3HintUpsert, M3ItemUpsert, M3ObjectsPut, M3OwnerRanks,
    M3PortfolioCreate, M3PortfolioOut, M3QuestionnaireOut, M3ReportOut,
    M3TradeoffIn, M3WeightUpsert,
)
from app.models import User


async def _flag_gate() -> None:
    """
    Гейт флага фичи. Повешен НА РОУТЕР, а не вызывается в теле эндпоинта:
    зависимости роутера резолвятся раньше Depends(get_current_user), поэтому
    анонимный запрос получает 404, а не 401. Пока проверка стояла в теле,
    авторизация отбивала анонима первой, и по коду ответа раздел отличался
    от несуществующего пути — то есть о его существовании можно было узнать
    снаружи до релиза.

    404, а не 403: при выключенном флаге раздела не существует. 403 сообщал бы,
    что функциональность есть и она закрыта, — лишняя информация до релиза.
    """
    if not get_settings().m3_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


router = APIRouter(prefix="/api/m3", tags=["m3"],
                   dependencies=[Depends(_flag_gate)])
admin_router = APIRouter(prefix="/api/admin/m3", tags=["m3-admin"],
                         dependencies=[Depends(_flag_gate)])
reports_router = APIRouter(prefix="/api/reports/m3", tags=["m3"],
                           dependencies=[Depends(_flag_gate)])


async def _owned(portfolio_id: uuid.UUID, user: User, db: AsyncSession) -> M3Portfolio:
    p = await db.scalar(
        select(M3Portfolio)
        .options(selectinload(M3Portfolio.objects))
        .where(M3Portfolio.id == portfolio_id)
    )
    if not p:
        raise HTTPException(status_code=404, detail="Портфель не найден")
    if p.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")
    return p


def _bad(e: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(e))


# ── Справочники ───────────────────────────────────────────────────────────────
@router.get("/industries")
async def list_industries(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    18 областей для селекта отрасли. Отдаются с бэкенда, а не зашиты во фронт:
    названия правятся в админке вместе с весами, и второй список в коде фронта
    разошёлся бы с первым при первой же правке.

    Пустая таблица — рабочее состояние до сида: отдаём дефолты из конфига,
    чтобы форма не оставалась без вариантов.
    """
    rows = (await db.execute(select(M3Weight).order_by(M3Weight.industry_id))).scalars().all()
    if rows:
        return [{"id": w.industry_id, "name": w.name} for w in rows]
    cfg = svc.get_config()
    return [
        {"id": iid, "name": preset["name"]}
        for iid, preset in sorted(cfg["industry_presets"].items(), key=lambda kv: int(kv[0]))
    ]


# ── Портфель ──────────────────────────────────────────────────────────────────
@router.post("/portfolios", response_model=M3PortfolioOut, status_code=201)
async def create_portfolio(
    body: M3PortfolioCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = M3Portfolio(user_id=user.id, title=body.title, industry_id=body.industry_id)
    db.add(p)
    await db.flush()
    await db.refresh(p, ["objects"])
    return p


@router.get("/portfolios", response_model=list[M3PortfolioOut])
async def list_portfolios(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(M3Portfolio)
        .options(selectinload(M3Portfolio.objects))
        .where(M3Portfolio.user_id == user.id)
        .order_by(M3Portfolio.created_at.desc())
    )).scalars().all()
    return list(rows)


@router.get("/portfolios/{portfolio_id}", response_model=M3PortfolioOut)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _owned(portfolio_id, user, db)


@router.put("/portfolios/{portfolio_id}/objects", response_model=M3PortfolioOut)
async def put_objects(
    portfolio_id: uuid.UUID,
    body: M3ObjectsPut,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Полная замена списка направлений. Переписывать список после расчёта нельзя:
    ответы и снимок привязаны к направлениям, и молчаливое удаление сделало бы
    выданный отчёт неповторяемым.
    """
    p = await _owned(portfolio_id, user, db)
    if p.status == "calculated":
        raise HTTPException(
            status_code=409,
            detail="Портфель уже рассчитан. Измените состав направлений "
                   "в новом портфеле, иначе выданный отчёт станет неповторяемым.",
        )

    for o in list(p.objects):
        await db.delete(o)
    await db.flush()

    for item in sorted(body.objects, key=lambda x: x.position):
        db.add(M3Object(portfolio_id=p.id, **item.model_dump()))
    await db.flush()
    await db.refresh(p, ["objects"])
    return p


@router.put("/portfolios/{portfolio_id}/owner-ranks", response_model=M3PortfolioOut)
async def put_owner_ranks(
    portfolio_id: uuid.UUID,
    body: M3OwnerRanks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    if len(body.ranks) != len(p.objects):
        raise HTTPException(
            status_code=400,
            detail=f"Рангов {len(body.ranks)}, направлений {len(p.objects)}",
        )
    p.owner_ranks = body.ranks
    await db.flush()
    return p


# ── Анкета ────────────────────────────────────────────────────────────────────
@router.get("/portfolios/{portfolio_id}/questionnaire", response_model=M3QuestionnaireOut)
async def questionnaire(
    portfolio_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    return await svc.build_questionnaire(db, p)


@router.post("/portfolios/{portfolio_id}/answers")
async def post_answers(
    portfolio_id: uuid.UUID,
    body: M3AnswersIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    try:
        saved = await svc.save_answers(db, p, [a.model_dump() for a in body.answers])
    except svc.M3ServiceError as e:
        raise _bad(e) from e
    return {"saved": saved, "status": p.status}


@router.get("/portfolios/{portfolio_id}/arbiter-required", response_model=list[M3ArbiterOut])
async def get_arbiter_required(
    portfolio_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    return await svc.arbiter_required(db, p)


@router.post("/portfolios/{portfolio_id}/calculate")
async def post_calculate(
    portfolio_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    try:
        calc = await svc.calculate(db, p)
    except svc.M3ServiceError as e:
        raise _bad(e) from e
    return {
        "portfolio_id": p.id,
        "objects": len(calc["objects"]),
        "verdicts_held": calc["portfolio"]["verdicts_held"],
        "flags": calc["portfolio"]["flags"],
    }


# ── Отчёт ─────────────────────────────────────────────────────────────────────
@reports_router.get("/{portfolio_id}", response_model=M3ReportOut)
async def get_report(
    portfolio_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    try:
        return await svc.build_report(db, p)
    except svc.M3ServiceError as e:
        raise _bad(e) from e


@reports_router.post("/{portfolio_id}/tradeoff")
async def post_tradeoff(
    portfolio_id: uuid.UUID,
    body: M3TradeoffIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Фиксация решения по волнам. Меняет чек-лист: плоский список перестраивается,
    часть шагов уходит в отложенный статус. Без записанного решения повторная
    диагностика истолкует неизменившееся направление как невыполнение
    рекомендаций, а не как исполнение принятого плана.
    """
    p = await _owned(portfolio_id, user, db)

    known = {o.id for o in p.objects}
    assigned: set[uuid.UUID] = set()
    for wave, ids in body.waves.items():
        for oid in ids:
            if oid not in known:
                raise HTTPException(
                    status_code=400,
                    detail="В волнах указано направление не из этого портфеля",
                )
            if oid in assigned:
                raise HTTPException(
                    status_code=400,
                    detail="Направление назначено сразу в две волны",
                )
            assigned.add(oid)

    decision = M3TradeoffDecision(
        portfolio_id=p.id,
        accepted_option=body.accepted_option,
        waves={k: [str(i) for i in v] for k, v in body.waves.items()},
        cost_accepted=body.cost_accepted,
        review_triggers=body.review_triggers or None,
    )
    db.add(decision)

    wave_by_object = {oid: int(w) for w, ids in body.waves.items() for oid in ids}
    steps = (await db.execute(
        select(M3ChecklistStep).where(M3ChecklistStep.portfolio_id == p.id)
    )).scalars().all()
    for s in steps:
        # Подготовительный шаг остаётся в первой волне и по отложенным
        # направлениям: он не меняет ни одной линии и не расходует
        # трансформационный ресурс, зато снимает часть цены отсрочки.
        s.wave = 1 if s.step_type == "prep" else wave_by_object.get(s.object_id, 1)
    await db.flush()

    return {"decision_id": decision.id, "steps_rescheduled": len(steps)}


@reports_router.get("/{portfolio_id}/checklist", response_model=list[M3ChecklistStepOut])
async def get_checklist(
    portfolio_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    rows = (await db.execute(
        select(M3ChecklistStep)
        .where(M3ChecklistStep.portfolio_id == p.id)
        .order_by(M3ChecklistStep.wave, M3ChecklistStep.step_type, M3ChecklistStep.line)
    )).scalars().all()
    return list(rows)


@reports_router.patch("/{portfolio_id}/checklist/{step_id}", response_model=M3ChecklistStepOut)
async def patch_checklist(
    portfolio_id: uuid.UUID,
    step_id: uuid.UUID,
    body: M3ChecklistToggle,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _owned(portfolio_id, user, db)
    step = await db.scalar(
        select(M3ChecklistStep).where(
            M3ChecklistStep.id == step_id,
            M3ChecklistStep.portfolio_id == p.id,
        )
    )
    if not step:
        raise HTTPException(status_code=404, detail="Шаг не найден")
    step.done = body.done
    if body.done:
        from sqlalchemy import func as sa_func
        step.done_at = sa_func.now()
    else:
        step.done_at = None
    await db.flush()
    await db.refresh(step)
    return step


# ── Админка ───────────────────────────────────────────────────────────────────
@admin_router.get("/items")
async def admin_list_items(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(M3Item).order_by(M3Item.block, M3Item.number, M3Item.item_version)
    )).scalars().all()
    return [
        {
            "id": i.id, "block": i.block, "number": i.number, "code": i.code,
            "line": i.line, "text": i.text, "is_reverse": i.is_reverse,
            "industry_id": i.industry_id, "item_version": i.item_version,
            "is_active": i.is_active,
        }
        for i in rows
    ]


@admin_router.post("/items", status_code=201)
async def admin_upsert_item(
    body: M3ItemUpsert,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Правка формулировки создаёт НОВУЮ версию, старая не удаляется и не
    правится. Без этого выданные отчёты стали бы несопоставимы с новыми,
    а модуль динамики отнёс бы расхождение баллов к изменениям в бизнесе.
    """
    rows = (await db.execute(
        select(M3Item).where(
            M3Item.code == body.code,
            M3Item.industry_id.is_(None) if body.industry_id is None
            else M3Item.industry_id == body.industry_id,
        )
    )).scalars().all()

    next_version = max((r.item_version for r in rows), default=0) + 1
    for r in rows:
        r.is_active = False

    item = M3Item(
        block=body.block, number=body.number, code=body.code, line=body.line,
        text=body.text, is_reverse=body.is_reverse, industry_id=body.industry_id,
        item_version=next_version, is_active=True,
    )
    db.add(item)
    await db.flush()
    return {"id": item.id, "code": item.code, "item_version": item.item_version}


@admin_router.get("/weights")
async def admin_list_weights(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(M3Weight).order_by(M3Weight.industry_id))).scalars().all()
    return [
        {
            "industry_id": w.industry_id, "name": w.name,
            "w_l1": w.w_l1, "w_l2": w.w_l2, "w_l3": w.w_l3,
            "w_l4": w.w_l4, "w_l5": w.w_l5, "w_l6": w.w_l6,
        }
        for w in rows
    ]


@admin_router.put("/weights/{industry_id}")
async def admin_put_weight(
    industry_id: int,
    body: M3WeightUpsert,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if industry_id != body.industry_id:
        raise HTTPException(status_code=400, detail="industry_id в пути и теле расходятся")
    row = await db.scalar(select(M3Weight).where(M3Weight.industry_id == industry_id))
    if row is None:
        row = M3Weight(industry_id=industry_id)
        db.add(row)
    for f in ("name", "w_l1", "w_l2", "w_l3", "w_l4", "w_l5", "w_l6"):
        setattr(row, f, getattr(body, f))
    await db.flush()
    return {"industry_id": row.industry_id}


@admin_router.get("/content")
async def admin_list_content(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(M3Content).order_by(M3Content.kind, M3Content.key))).scalars().all()
    return [
        {
            "id": c.id, "kind": c.kind, "key": c.key, "title": c.title,
            "body": c.body, "mistake": c.mistake, "industry_id": c.industry_id,
            "is_active": c.is_active,
        }
        for c in rows
    ]


@admin_router.put("/content")
async def admin_put_content(
    body: M3ContentUpsert,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(select(M3Content).where(
        M3Content.kind == body.kind,
        M3Content.key == body.key,
        M3Content.industry_id.is_(None) if body.industry_id is None
        else M3Content.industry_id == body.industry_id,
    ))
    if row is None:
        row = M3Content(kind=body.kind, key=body.key, industry_id=body.industry_id)
        db.add(row)
    row.title, row.body, row.mistake = body.title, body.body, body.mistake
    row.is_active = True
    await db.flush()
    return {"id": row.id, "kind": row.kind, "key": row.key}


@admin_router.get("/hints")
async def admin_list_hints(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(M3Hint).order_by(M3Hint.industry_id, M3Hint.item_code)
    )).scalars().all()
    return [
        {"id": h.id, "industry_id": h.industry_id, "item_code": h.item_code, "text": h.text}
        for h in rows
    ]


@admin_router.put("/hints")
async def admin_put_hint(
    body: M3HintUpsert,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(select(M3Hint).where(
        M3Hint.industry_id == body.industry_id,
        M3Hint.item_code == body.item_code,
    ))
    if row is None:
        row = M3Hint(industry_id=body.industry_id, item_code=body.item_code)
        db.add(row)
    row.text = body.text
    await db.flush()
    return {"id": row.id}


# ── Скачивание PDF ────────────────────────────────────────────────────────────
# Обработчик живёт в отдельном модуле: роутер уже длинный, а правка
# существующего файла дороже нового. Регистрация здесь, чтобы эндпоинт попал
# в reports_router с гейтом флага фичи — при m3_enabled=false он отдаёт 404
# наравне с остальными. Проверка доступа переиспользует _owned: второй её
# копии в проекте быть не должно.
from app.m3_report_api import register_download  # noqa: E402

register_download(reports_router, _owned)
