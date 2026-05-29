import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import Assessment, Report, Strategy, User
from app.pdf import generate_pdf, build_report_html
from app.schemas import AssessmentCreate, AssessmentOut, ReportOut, StrategyOut

settings = get_settings()
router = APIRouter(prefix="/api/assessments", tags=["assessments"])

_MONTHS_RU = {
    "January": "января", "February": "февраля", "March": "марта",
    "April": "апреля", "May": "мая", "June": "июня",
    "July": "июля", "August": "августа", "September": "сентября",
    "October": "октября", "November": "ноября", "December": "декабря",
}


def _date_ru(dt: datetime) -> str:
    s = dt.strftime("%d %B %Y, %H:%M")
    for en, ru in _MONTHS_RU.items():
        s = s.replace(en, ru)
    return s


@router.post("", response_model=AssessmentOut)
async def create_assessment(
    body: AssessmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assessment = Assessment(
        user_id=user.id,
        method1_answers=body.method1_answers,
        method1_combination=body.method1_combination,
        method2_data={k: v.model_dump() for k, v in (body.method2_data or {}).items()},
        company_name=body.company_name or user.company_name,
        status=body.status,
    )
    db.add(assessment)
    await db.flush()

    result = await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment.id)
        .options(selectinload(Assessment.reports))
    )
    return result.scalar_one()


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.user_id == user.id)
        .options(selectinload(Assessment.reports))
        .order_by(Assessment.created_at.desc())
    )
    assessments = result.scalars().all()

    # Подгружаем image_url стратегий одним запросом (избегаем N+1)
    combinations = {a.method1_combination for a in assessments if a.method1_combination}
    strategies_map: dict[str, str | None] = {}
    if combinations:
        strat_result = await db.execute(
            select(Strategy.combination, Strategy.image_url)
            .where(Strategy.combination.in_(combinations))
        )
        strategies_map = {row.combination: row.image_url for row in strat_result}

    out = []
    for a in assessments:
        item = AssessmentOut.model_validate(a)
        if a.method1_combination and a.method1_combination in strategies_map:
            item.strategy_image_url = strategies_map[a.method1_combination]
        out.append(item)
    return out


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get_assessment(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(selectinload(Assessment.reports))
    )
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")

    if assessment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")

    return assessment


@router.delete("/{assessment_id}", status_code=204)
async def delete_assessment(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(selectinload(Assessment.reports))
    )
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")

    if assessment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")

    for report in assessment.reports:
        if report.pdf_path:
            try:
                Path(report.pdf_path).unlink(missing_ok=True)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Could not delete PDF file %s: %s", report.pdf_path, exc
                )

    await db.delete(assessment)


@router.post("/{assessment_id}/generate-report", response_model=ReportOut)
async def generate_report_on_demand(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas import ReportOut as ReportOutSchema

    result = await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(selectinload(Assessment.reports))
    )
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    if assessment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")

    if assessment.reports:
        return assessment.reports[0]

    combination = assessment.method1_combination
    company_name = assessment.company_name or user.company_name or "Компания"
    user_name = user.full_name or ""
    # Передаём None если поле не задано (None = Метод 1, {} или {...} = Метод 2)
    method2_data = assessment.method2_data

    strategy = None
    if combination:
        strategy = await db.scalar(
            select(Strategy).where(Strategy.combination == combination, Strategy.is_published == True)
        )

    now = datetime.now(timezone.utc)
    date_str = _date_ru(now)

    html = build_report_html(
        company_name=company_name,
        user_name=user_name,
        date_str=date_str,
        combination=combination or "",
        strategy=strategy,
        method2_data=method2_data,
    )

    filename = f"{assessment_id}-{int(datetime.now().timestamp())}.pdf"
    output_path = str(Path(settings.uploads_dir) / str(user.id) / filename)

    await generate_pdf(html, output_path)

    report = Report(
        assessment_id=assessment_id,
        user_id=user.id,
        pdf_path=output_path,
        pdf_filename=filename,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    return report


@router.get("/{assessment_id}/pdf")
async def stream_pdf_on_demand(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    if assessment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")

    combination = assessment.method1_combination
    company_name = assessment.company_name or "Компания"
    user_name = user.full_name or ""
    # Передаём None если поле не задано (None = Метод 1, {} или {...} = Метод 2)
    method2_data = assessment.method2_data

    strategy = None
    if combination:
        q = select(Strategy).where(Strategy.combination == combination)
        if user.role not in ("admin", "editor"):
            q = q.where(Strategy.is_published == True)
        strategy = await db.scalar(q)

    date_str = _date_ru(datetime.now(timezone.utc))

    html = build_report_html(
        company_name=company_name,
        user_name=user_name,
        date_str=date_str,
        combination=combination or "",
        strategy=strategy,
        method2_data=method2_data,
    )

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(tmp_fd)
    try:
        await generate_pdf(html, tmp_path)
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    safe_name = f"64dao-report-{str(assessment_id)[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
        },
    )


@router.get("/{assessment_id}/strategy", response_model=StrategyOut)
async def get_assessment_strategy(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    if assessment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")

    combination = assessment.method1_combination
    if not combination:
        raise HTTPException(status_code=404, detail="Стратегия для этого типа диагностики не применима")

    strategy = await db.scalar(
        select(Strategy).where(Strategy.combination == combination)
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")

    return strategy
