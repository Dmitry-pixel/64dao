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
from app.models import Assessment, AssessmentContour, Report, Strategy, User
from app.pdf import generate_pdf, build_report_html
from app.routers.payments import calculate_credits
from app.finance_service import resolve_submission_finance, FinanceRequiredError
from app.finance_scoring import InvalidAnswersError, BlockUnderfilledError
from app.finance_interpret import load_content, build_interpretation
from app.schemas import (
    AssessmentCreate, AssessmentOut, ContourBrief, ContourSubmit, ReportOut, StrategyOut,
)
from app.contours import CONTOURS, get_spec
from app.contour_settings import is_contour_enabled
from app.contour_scoring import compute_contour_result

settings = get_settings()
router = APIRouter(prefix="/api/assessments", tags=["assessments"])


def _ensure_result_access(assessment, user) -> None:
    """Под enforce_credits результат диагностики (стратегия/PDF) доступен
    только для completed/paid: кредит списывается при создании completed-
    диагностики, draft результата не даёт (иначе — обход кредитов). Админ —
    без ограничений. После рефанда assessment возвращается в draft, и доступ
    к результату корректно закрывается."""
    if settings.enforce_credits and user.role != "admin" and assessment.status == "draft":
        raise HTTPException(
            status_code=403,
            detail="Результат доступен после оформления диагностики.",
        )

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


async def _load_contour(db, assessment, contour: str):
    """Читает контур из assessment_contours. Для finance падает обратно на
    колонки finance_* — они остаются rollback-окном до миграции 010."""
    row = await db.scalar(
        select(AssessmentContour).where(
            AssessmentContour.assessment_id == assessment.id,
            AssessmentContour.contour == contour,
        )
    )
    if row:
        return row.result, row.combination
    if contour == "finance":
        return assessment.finance_result, assessment.finance_combination
    return None, None


@router.post("", response_model=AssessmentOut)
async def create_assessment(
    body: AssessmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if settings.enforce_credits and body.status == "completed" and user.role != "admin":
        credits = await calculate_credits(user.id, db)
        if credits <= 0:
            raise HTTPException(
                status_code=403,
                detail="Нет доступных диагностик. Оплатите новую диагностику, чтобы получить доступ.",
            )

    # Финансовый блок Метода 1: скоринг считает сервер (не доверяем фронту).
    is_method1 = not body.method2_data
    try:
        finance_result, finance_combination = resolve_submission_finance(
            body.finance_answers,
            status=body.status,
            is_method1=is_method1,
            finance_required=settings.finance_block_required,
        )
    except (FinanceRequiredError, InvalidAnswersError, BlockUnderfilledError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    method2_payload = (
        {k: v.model_dump() for k, v in body.method2_data.items()}
        if body.method2_data else None
    )

    assessment = Assessment(
        user_id=user.id,
        method1_answers=body.method1_answers,
        method1_combination=body.method1_combination,
        method2_data=method2_payload,
        method="method2" if method2_payload else "method1",
        company_name=body.company_name or user.company_name,
        status=body.status,
        finance_answers=body.finance_answers,
        finance_result=finance_result,
        finance_combination=finance_combination,
    )
    db.add(assessment)
    await db.flush()

    # Двойная запись финансового контура: assessment_contours — основное хранилище,
    # колонки finance_* остаются rollback-окном до миграции 010.
    if finance_result and finance_combination and body.finance_answers:
        db.add(AssessmentContour(
            assessment_id=assessment.id,
            contour="finance",
            answers=body.finance_answers,
            result=finance_result,
            combination=finance_combination,
        ))
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

    # Пройденные контуры — одним запросом на всю выдачу (как со стратегиями)
    contours_map: dict = {}
    if assessments:
        rows = (await db.execute(
            select(AssessmentContour).where(
                AssessmentContour.assessment_id.in_([a.id for a in assessments])
            )
        )).scalars().all()
        for r in rows:
            contours_map.setdefault(r.assessment_id, []).append(r)

    out = []
    for a in assessments:
        item = AssessmentOut.model_validate(a)
        if a.method1_combination and a.method1_combination in strategies_map:
            item.strategy_image_url = strategies_map[a.method1_combination]
        item.passed_contours = [
            ContourBrief.model_validate(r) for r in contours_map.get(a.id, [])
        ]
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

    item = AssessmentOut.model_validate(assessment)
    rows = (await db.execute(
        select(AssessmentContour).where(
            AssessmentContour.assessment_id == assessment.id
        )
    )).scalars().all()
    item.passed_contours = [ContourBrief.model_validate(r) for r in rows]
    return item


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

    _ensure_result_access(assessment, user)

    if assessment.reports:
        return assessment.reports[0]
    if settings.enforce_credits and assessment.status == "completed" and user.role != "admin":
        credits = await calculate_credits(user.id, db)
        if credits <= 0:
            raise HTTPException(
                status_code=403,
                detail="Нет доступных диагностик. Оплатите новую диагностику, чтобы получить доступ.",
            )

    html = await build_html_for_assessment(db, assessment, user, allow_draft=False)

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

    _ensure_result_access(assessment, user)

    html = await build_html_for_assessment(db, assessment, user, allow_draft=(user.role == "admin"))

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

    _ensure_result_access(assessment, user)

    combination = assessment.method1_combination
    if not combination:
        raise HTTPException(status_code=404, detail="Стратегия для этого типа диагностики не применима")

    strategy = await db.scalar(
        select(Strategy).where(Strategy.combination == combination)
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")

    return strategy


@router.get("/{assessment_id}/finance-interpretation")
async def get_finance_interpretation(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Собранная интерпретация финблока для браузерного HTML-отчёта.
    Возвращает has_finance=False для legacy-диагностик без финансовых данных."""
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    if assessment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")
    _ensure_result_access(assessment, user)

    fin_result, fin_combo = await _load_contour(db, assessment, "finance")
    if not fin_result:
        return {"has_finance": False}
    content = await load_content(db)
    interp = build_interpretation(fin_result, content)
    return {
        "has_finance": True,
        "finance_result": fin_result,
        "finance_combination": fin_combo,
        "interpretation": interp,
    }


@router.post("/{assessment_id}/contours/{contour}")
async def submit_contour(
    assessment_id: str,
    contour: str,
    body: ContourSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Прохождение дополнительного контура из кабинета. Скоринг только на сервере.
    Повторное прохождение запрещено (§0.8): исправление — через админский сброс."""
    if contour not in CONTOURS or not is_contour_enabled(contour):
        raise HTTPException(status_code=404, detail="Контур недоступен")

    assessment = await db.scalar(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    if assessment.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")
    if assessment.method != "method1":
        raise HTTPException(
            status_code=400,
            detail="Контуры применимы только к диагностике Метода 1.",
        )
    if assessment.status not in ("completed", "paid"):
        raise HTTPException(
            status_code=400,
            detail="Контур доступен после завершения диагностики.",
        )

    existing = await db.scalar(
        select(AssessmentContour).where(
            AssessmentContour.assessment_id == assessment.id,
            AssessmentContour.contour == contour,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Этот контур уже пройден.")

    try:
        result = compute_contour_result(body.answers, get_spec(contour))
    except (InvalidAnswersError, BlockUnderfilledError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    row = AssessmentContour(
        assessment_id=assessment.id,
        contour=contour,
        answers=body.answers,
        result=result,
        combination=result["combination_current"],
    )
    db.add(row)
    await db.flush()

    return {
        "contour": contour,
        "title": get_spec(contour).title,
        "combination": row.combination,
        "result": result,
    }


async def build_html_for_assessment(db, assessment, user, allow_draft: bool = False) -> str:
    """Единая сборка HTML отчёта: создание, предпросмотр и скачивание."""
    combination = assessment.method1_combination
    company_name = assessment.company_name or user.company_name or "Компания"
    user_name = user.full_name or ""
    method2_data = assessment.method2_data

    strategy = None
    if combination:
        q = select(Strategy).where(Strategy.combination == combination)
        if not allow_draft:
            q = q.where(Strategy.is_published == True)
        strategy = await db.scalar(q)

    finance_result, finance_combination = await _load_contour(db, assessment, "finance")
    finance_interpretation = None
    finance_strategy = None
    if finance_result:
        finance_content = await load_content(db)
        finance_interpretation = build_interpretation(finance_result, finance_content)
        fin_combo = finance_combination or finance_result.get("combination_current")
        if fin_combo:
            finance_strategy = await db.scalar(
                select(Strategy).where(Strategy.combination == fin_combo)
            )

    from app.models import LifecycleStage
    stages_rows = (await db.execute(
        select(LifecycleStage).order_by(LifecycleStage.sort_order)
    )).scalars().all()
    lifecycle_stages = [
        {"sort_order": s.sort_order, "name": s.name, "description": s.description}
        for s in stages_rows
    ]

    is_method2 = assessment.method == "method2"

    return build_report_html(
        is_method2=is_method2,
        lifecycle_stages=lifecycle_stages,
        company_name=company_name,
        user_name=user_name,
        date_str=_date_ru(datetime.now(timezone.utc)),
        combination=combination or "",
        strategy=strategy,
        method2_data=method2_data,
        finance_result=finance_result,
        finance_interpretation=finance_interpretation,
        finance_strategy=finance_strategy,
    )
