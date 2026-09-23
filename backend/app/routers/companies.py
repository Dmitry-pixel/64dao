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
    пользователь: все диагностики всех — в разделах админки."""
    rows = (await db.execute(
        select(Assessment)
        .join(Company, Company.id == Assessment.company_id)
        .where(Company.user_id == user.id, _visible())
        .order_by(Assessment.created_at)
    )).scalars().all()

    names = dict((await db.execute(
        select(Company.id, Company.name).where(Company.user_id == user.id)
    )).all())
    repeat_days = reminders_settings.read()["repeat_days"]

    by_company: dict = {}
    for a in rows:
        by_company.setdefault(a.company_id, []).append(a)

    out = []
    for cid, items in by_company.items():
        first, last = items[0].created_at, items[-1].created_at
        # Право на бесплатный повтор живёт на первичной диагностике Метода 1 —
        # та же логика, что при создании повтора в routers/assessments.py.
        primary = next((a for a in items if a.method == "method1" and not a.is_followup), None)
        out.append(CompanyOut(
            id=cid,
            name=names.get(cid, ""),
            assessment_count=len(items),
            first_at=first,
            latest_at=last,
            repeat_days=repeat_days,
            next_repeat_at=last + timedelta(days=repeat_days),
            followup_available=bool(primary and primary.followup_used < primary.followup_allowed),
            assessments=[
                CompanyAssessmentOut(id=a.id, method=a.method, created_at=a.created_at,
                                     is_followup=a.is_followup)
                for a in reversed(items)
            ],
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
