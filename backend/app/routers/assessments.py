import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import Assessment, Report, Strategy, User
from app.pdf import generate_pdf, build_report_html
from app.schemas import AssessmentCreate, AssessmentOut

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
        status=body.status,
    )
    db.add(assessment)
    await db.flush()

    # Снимаем скалярные данные пока сессия открыта
    assessment_id = str(assessment.id)
    company_name = user.company_name or "Компания"
    user_name    = user.full_name or ""
    user_id      = user.id

    # Запускаем генерацию PDF в фоне — не блокируем ответ
    if body.status == "completed":
        asyncio.create_task(
            _generate_report_background(
                assessment_id=assessment_id,
                user_id=user_id,
                company_name=company_name,
                user_name=user_name,
                combination=body.method1_combination,
                method2_data=assessment.method2_data or {},
            )
        )

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


async def _generate_report_background(
    assessment_id: str,
    user_id,
    company_name: str,
    user_name: str,
    combination: str,
    method2_data: dict,
) -> None:
    """Фоновая генерация PDF — не блокирует API-ответ."""
    try:
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_db:
            # Загружаем стратегию
            strategy = await bg_db.scalar(
                select(Strategy)
                .where(Strategy.combination == combination, Strategy.is_published == True)
            )

            date_str = datetime.now(timezone.utc).strftime("%d %B %Y").replace(
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
                combination=combination,
                strategy=strategy,
                method2_data=method2_data,
            )

            filename = f"{assessment_id}-{int(datetime.now().timestamp())}.pdf"
            output_path = str(Path(settings.uploads_dir) / str(user_id) / filename)

            await generate_pdf(html, output_path)

            # Сохраняем запись отчёта
            report = Report(
                assessment_id=assessment_id,
                user_id=user_id,
                pdf_path=output_path,
                pdf_filename=filename,
                generated_at=datetime.now(timezone.utc),
            )
            bg_db.add(report)

            # Обновляем статус диагностики
            assessment = await bg_db.scalar(
                select(Assessment).where(Assessment.id == assessment_id)
            )
            if assessment:
                assessment.status = "completed"

            await bg_db.commit()

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "Background PDF generation failed for assessment %s: %s",
            assessment_id, exc, exc_info=True,
        )
