from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import Assessment, Report, Strategy, User
from app.pdf import generate_pdf, build_report_html
from app.schemas import AssessmentCreate, AssessmentOut, ReportOut

settings = get_settings()
router = APIRouter(prefix="/api/assessments", tags=["assessments"])


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

    # Перезагружаем с reports для корректного response_model
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
    return result.scalars().all()


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

    # Только владелец или администратор
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

    # Удаляем PDF-файлы с диска
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
    """Генерирует PDF отчёт по запросу и возвращает его запись."""
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

    # Если отчёт уже есть — возвращаем существующий
    if assessment.reports:
        return assessment.reports[0]

    # Подготавливаем данные
    combination = assessment.method1_combination
    company_name = assessment.company_name or user.company_name or "Компания"
    user_name = user.full_name or ""
    method2_data = assessment.method2_data or {}

    strategy = None
    if combination:
        strategy = await db.scalar(
            select(Strategy).where(Strategy.combination == combination, Strategy.is_published == True)
        )

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d %B %Y, %H:%M").replace(
        "January", "января").replace("February", "февраля").replace(
        "March", "марта").replace("April", "апреля").replace(
        "May", "мая").replace("June", "июня").replace(
        "July", "июля").replace("August", "августа").replace(
        "September", "сентября").replace("October", "октября").replace(
        "November", "ноября").replace("December", "декабря")

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

