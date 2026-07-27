# -*- coding: utf-8 -*-
"""
Компании пользователя (роадмап 3.1). Группировка диагностик; вход в «Динамику»
(GET /{id}/dynamics — на этапе PR3). Пока — список компаний с числом диагностик.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Company, Assessment, AssessmentContour, User
from app.schemas import CompanyOut

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[CompanyOut])
async def list_companies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(
            Company.id, Company.name,
            func.count(Assessment.id).label("cnt"),
            func.max(Assessment.created_at).label("latest"),
        )
        .outerjoin(Assessment, Assessment.company_id == Company.id)
        .where(Company.user_id == user.id)
        .group_by(Company.id, Company.name)
        .order_by(func.max(Assessment.created_at).desc().nullslast())
    )).all()
    return [
        CompanyOut(id=r.id, name=r.name, assessment_count=r.cnt, latest_at=r.latest)
        for r in rows
    ]


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
