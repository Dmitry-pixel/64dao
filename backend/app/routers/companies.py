# -*- coding: utf-8 -*-
"""
Компании пользователя (роадмап 3.1). Группировка диагностик; вход в «Динамику»
(GET /{id}/dynamics — на этапе PR3). Пока — список компаний с числом диагностик.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import reminders_settings
from app.auth import get_current_user
from app.db import get_db
from app.m3_models import M3Portfolio
from app.models import Assessment, Company, User
from app.schemas import CompanyAssessmentOut, CompanyOut

router = APIRouter(prefix="/api/companies", tags=["companies"])

# Диагностика «считается» только завершённая и не удалённая. Удаление ставит
# отметку, а не стирает запись (факт расхода кредита должен остаться), поэтому
# без этого фильтра список показывал удалённые и черновики, а компании, у
# которых всё удалено, не исчезали.
_DONE = ("completed", "paid")


def _visible(assessment=Assessment):
    return and_(assessment.deleted_at.is_(None), assessment.status.in_(_DONE))


@router.get("", response_model=list[CompanyOut])
async def list_companies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Компании пользователя, у которых есть хотя бы одна действующая
    диагностика. Администратор видит здесь только свои компании, как и любой
    пользователь: все диагностики всех — в разделах админки.

    Метод 3 к компаниям не привязан: у портфеля только текстовое название.
    Поэтому рассчитанный портфель показывается в компании с тем же названием
    (без учёта регистра), а если такой нет — отдельной строкой без id: у неё
    нет ни повтора, ни «Динамики», только ссылки на отчёты.
    """
    rows = (await db.execute(
        select(Assessment)
        .join(Company, Company.id == Assessment.company_id)
        .where(Company.user_id == user.id, _visible())
        .order_by(Assessment.created_at)
    )).scalars().all()
    portfolios = (await db.execute(
        select(M3Portfolio)
        .where(M3Portfolio.user_id == user.id,
               M3Portfolio.deleted_at.is_(None),
               M3Portfolio.status == "calculated")
    )).scalars().all()

    names = dict((await db.execute(
        select(Company.id, Company.name).where(Company.user_id == user.id)
    )).all())
    by_name = {n.strip().casefold(): cid for cid, n in names.items()}
    repeat_days = reminders_settings.read()["repeat_days"]

    groups: dict = {}   # ключ: id компании или ("m3", название)

    def group(key, name):
        return groups.setdefault(key, {"id": key if not isinstance(key, tuple) else None,
                                       "name": name, "a": [], "m3": []})

    for a in rows:
        group(a.company_id, names.get(a.company_id, ""))["a"].append(a)
    for p in portfolios:
        pname = (p.company_name or p.title or "Без названия").strip()
        cid = by_name.get(pname.casefold())
        group(cid if cid else ("m3", pname.casefold()), names.get(cid, pname))["m3"].append(p)

    out = []
    for g in groups.values():
        items = g["a"]
        entries = [
            CompanyAssessmentOut(id=a.id, method=a.method, created_at=a.created_at,
                                 is_followup=a.is_followup)
            for a in items
        ] + [
            CompanyAssessmentOut(id=p.id, method="method3",
                                 created_at=p.calculated_at or p.created_at)
            for p in g["m3"]
        ]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        # Срок и право повтора — только у Методов 1–2: у Метода 3 повтора нет.
        last_m12 = items[-1].created_at if items else None
        # Право на бесплатный повтор живёт на первичной диагностике Метода 1 —
        # та же логика, что при создании повтора в routers/assessments.py.
        primary = next((a for a in items if a.method == "method1" and not a.is_followup), None)
        out.append(CompanyOut(
            id=g["id"],
            name=g["name"],
            assessment_count=len(entries),
            first_at=entries[-1].created_at,
            latest_at=entries[0].created_at,
            repeat_days=repeat_days if last_m12 else None,
            next_repeat_at=last_m12 + timedelta(days=repeat_days) if last_m12 else None,
            followup_available=bool(primary and primary.followup_used < primary.followup_allowed),
            dynamics_available=len(items) >= 2,
            assessments=entries,
        ))
    out.sort(key=lambda c: c.latest_at, reverse=True)
    return out


@router.get("/{company_id}/dynamics")
async def company_dynamics(
    company_id: str,
    compare: str = "previous",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Динамика компании. Входит в стоимость основной диагностики.
    compare: 'previous' (последняя↔предыдущая) | 'first' (последняя↔первая)."""
    from app.dynamics_service import company_dynamics


    company = await db.scalar(
        select(Company).where(Company.id == company_id, Company.user_id == user.id))
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")

    mode = 'first' if compare == 'first' else 'previous'
    return await company_dynamics(db, company_id, mode=mode)
