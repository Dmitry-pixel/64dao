# -*- coding: utf-8 -*-
# Сборка снапшотов компании и расчёт динамики.
# Вынесено из routers/companies.py, чтобы отчёт и страница динамики считали
# одно и то же одним кодом. Чистая логика сравнения остаётся в dynamics.py.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dynamics import build_company_dynamics
from app.models import Assessment, AssessmentContour


async def company_snapshots(db: AsyncSession, company_id) -> list[dict]:
    assessments = (await db.execute(
        select(Assessment)
        .where(Assessment.company_id == company_id,
               Assessment.status.in_(('completed', 'paid')))
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

    return [{
        'id': str(a.id),
        'created_at': a.created_at.isoformat() if a.created_at else '',
        'combination': a.method1_combination,
        'method': a.method,
        'contours': contours_by_ass.get(a.id, {}),
    } for a in assessments]


async def company_dynamics(db: AsyncSession, company_id, mode: str = 'previous') -> dict:
    return build_company_dynamics(await company_snapshots(db, company_id), mode=mode)
