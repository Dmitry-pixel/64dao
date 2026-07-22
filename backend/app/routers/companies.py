# -*- coding: utf-8 -*-
"""
Компании пользователя (роадмап 3.1). Группировка диагностик; вход в «Динамику»
(GET /{id}/dynamics — на этапе PR3). Пока — список компаний с числом диагностик.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Company, Assessment, User
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
