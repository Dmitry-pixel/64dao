# -*- coding: utf-8 -*-
# Сборка снапшотов компании и расчёт динамики.
# Вынесено из routers/companies.py, чтобы отчёт и страница динамики считали
# одно и то же одним кодом. Чистая логика сравнения остаётся в dynamics.py.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dynamics import build_company_dynamics
from app.models import Assessment, AssessmentContour


async def company_snapshots(db: AsyncSession, company_id, until: Assessment | None = None) -> list[dict]:
    """Замеры компании для сравнения.

    Только Метод 1: у Метода 2 нет ни гексаграммы, ни контуров, сравнивать в
    нём нечего. Раньше бизнес-модель, пройденная между первичной диагностикой
    и повтором, становилась «предыдущим замером», и раздел «Динамика» в отчёте
    повтора выходил пустым.

    until — замер, на котором история обрывается: отчёт повтора сравнивает
    себя с тем, что было ДО него, и не меняется от более поздних диагностик
    при повторной выгрузке PDF.
    """
    stmt = (
        select(Assessment)
        .where(Assessment.company_id == company_id,
               Assessment.method == 'method1',
               Assessment.status.in_(('completed', 'paid')),
               # Удалённая диагностика не участвует в динамике: для
               # пользователя её нет, а в графике она выглядела бы точкой,
               # которую нельзя открыть.
               Assessment.deleted_at.is_(None))
        .order_by(Assessment.created_at)
    )
    if until is not None:
        stmt = stmt.where(Assessment.created_at <= until.created_at)
    assessments = (await db.execute(stmt)).scalars().all()

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


async def company_dynamics(db: AsyncSession, company_id, mode: str = 'previous',
                           until: Assessment | None = None) -> dict:
    return build_company_dynamics(await company_snapshots(db, company_id, until=until), mode=mode)
