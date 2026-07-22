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
    """Динамика компании (роадмап 3.1). Доступ — при активной подписке (§5).
    compare: 'previous' (последняя↔предыдущая) | 'first' (последняя↔первая)."""
    from app import subscription_service as subs
    from app.dynamics import build_company_dynamics

    if not await subs.is_active(db, user.id):
        raise HTTPException(status_code=403, detail="Требуется активная подписка на «Динамику»")

    company = await db.scalar(
        select(Company).where(Company.id == company_id, Company.user_id == user.id))
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")

    assessments = (await db.execute(
        select(Assessment)
        .where(Assessment.company_id == company_id,
               Assessment.status.in_(("completed", "paid")))
        .order_by(Assessment.created_at)
    )).scalars().all()

    ids = [a.id for a in assessments]
    contours_by_ass: dict = {}
    if ids:
        rows = (await db.execute(
            select(AssessmentContour).where(AssessmentContour.assessment_id.in_(ids)))
        ).scalars().all()
        for r in rows:
            contours_by_ass.setdefault(r.assessment_id, {})[r.contour] = r.result

    snapshots = [{
        "id": str(a.id),
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "combination": a.method1_combination,
        "method": a.method,
        "contours": contours_by_ass.get(a.id, {}),
    } for a in assessments]

    mode = "first" if compare == "first" else "previous"
    return build_company_dynamics(snapshots, mode=mode)
