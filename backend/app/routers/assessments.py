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
from app.models import Assessment, AssessmentContour, Company, Report, Strategy, User
from app.pdf import generate_pdf, build_report_html
from app.routers.payments import calculate_credits
from app.finance_service import resolve_submission_finance, FinanceRequiredError
from app.finance_scoring import InvalidAnswersError, BlockUnderfilledError
from app.finance_interpret import load_content, build_interpretation
from app.schemas import (
    AssessmentCreate, AssessmentOut, ContourBrief, ContourSubmit, ReportOut, StrategyOut,
)
from app.contours import CONTOURS, CONTOUR_ORDER, get_spec
from app.contour_summary import build_summary
from app.contour_settings import is_contour_enabled
from app.contour_scoring import compute_contour_result
from app.company_lifecycle import build_company_lifecycle, lifecycle_progress

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
    """Читает контур из assessment_contours — единственное хранилище финансового
    контура после миграции 011."""
    row = await db.scalar(
        select(AssessmentContour).where(
            AssessmentContour.assessment_id == assessment.id,
            AssessmentContour.contour == contour,
        )
    )
    if row:
        return row.result, row.combination
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

    # Компания: явный company_id (свой) либо find-or-create по имени (роадмап 3.1).
    if body.company_id:
        company = await db.scalar(select(Company).where(
            Company.id == body.company_id, Company.user_id == user.id))
        if not company:
            raise HTTPException(status_code=404, detail="Компания не найдена")
    else:
        cname = (body.company_name or user.company_name or "").strip() or "Без названия"
        company = await db.scalar(select(Company).where(
            Company.user_id == user.id, Company.name == cname))
        if not company:
            company = Company(user_id=user.id, name=cname)
            db.add(company)
            await db.flush()

    # Повторная диагностика входит в стоимость основной и доступна один раз.
    # Право живёт на первичной диагностике компании, а не на пользователе:
    # оно куплено вместе с конкретным отчётом. Админ не ограничен.
    primary = None
    # Поиск первичной идёт для всех, включая админа: обход касается только
    # лимита. Иначе повтор админа не помечался бы и не связывался с основным.
    if body.status in ("completed", "paid") and not method2_payload:
        primary = await db.scalar(
            select(Assessment)
            .where(
                Assessment.company_id == company.id,
                Assessment.status.in_(("completed", "paid")),
                Assessment.is_followup.is_(False),
                Assessment.method == "method1",
            )
            .order_by(Assessment.created_at)
            .limit(1)
            .with_for_update()
        )
        if (primary is not None and user.role != "admin"
                and primary.followup_used >= primary.followup_allowed):
            raise HTTPException(
                status_code=403,
                detail="Повторная диагностика для этой компании уже пройдена. "
                       "Она входит в стоимость основной диагностики "
                       "и доступна один раз.",
            )

    assessment = Assessment(
        user_id=user.id,
        method1_answers=body.method1_answers,
        method1_combination=body.method1_combination,
        method2_data=method2_payload,
        method="method2" if method2_payload else "method1",
        company_name=company.name,
        company_id=company.id,
        status=body.status,
    )
    db.add(assessment)
    await db.flush()
    # Отметка повтора и выдача права — в одной транзакции с созданием:
    # двойной клик не должен выдать два прогона.
    if primary is not None:
        assessment.is_followup = True
        assessment.parent_assessment_id = primary.id
        if primary.followup_used >= primary.followup_allowed:
            # Админ лимитом не ограничен, но инвариант
            # followup_used <= followup_allowed обязан сохраниться,
            # иначе запись не пройдёт проверку ограничения в БД.
            primary.followup_allowed = primary.followup_used + 1
        primary.followup_used += 1
        await db.flush()
    elif body.status in ("completed", "paid") and not method2_payload:
        # Первичная диагностика приносит право на один бесплатный повтор.
        # Бэкфил миграции 017 закрыл только записи, существовавшие до неё.
        assessment.followup_allowed = 1
        await db.flush()

    # Финансовый контур хранится только в assessment_contours (после миграции 011).
    if finance_result and finance_combination and body.finance_answers:
        db.add(AssessmentContour(
            assessment_id=assessment.id,
            contour="finance",
            answers=body.finance_answers,
            result=finance_result,
            combination=finance_combination,
        ))
        await db.flush()

    assessment = (await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment.id)
        .options(selectinload(Assessment.reports))
    )).scalar_one()
    item = AssessmentOut.model_validate(assessment)
    if finance_result and finance_combination:
        item.finance_combination = finance_combination
        item.finance_result = finance_result
    return item


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Поиск по названию компании из диагностики, а не из профиля: у одного
    # владельца компаний может быть несколько, и профиль о них не знает.
    # Индекс pg_trgm не заводим: на нынешних объёмах последовательное
    # сканирование дешевле его поддержки.
    stmt = (
        select(Assessment)
        .where(Assessment.user_id == user.id)
        .options(selectinload(Assessment.reports))
        .order_by(Assessment.created_at.desc())
    )
    if q and q.strip():
        stmt = stmt.where(Assessment.company_name.ilike("%" + q.strip() + "%"))
    result = await db.execute(stmt)
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
        _rows_a = contours_map.get(a.id, [])
        item.passed_contours = [ContourBrief.model_validate(r) for r in _rows_a]
        _fin = next((r for r in _rows_a if r.contour == "finance"), None)
        if _fin:
            item.finance_combination = _fin.combination
            item.finance_result = _fin.result
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
    _fin = next((r for r in rows if r.contour == "finance"), None)
    if _fin:
        item.finance_combination = _fin.combination
        item.finance_result = _fin.result
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
    extra, summary = await load_report_contours(db, assessment, fin_result)
    from app.finance_items import BLOCKS as _FIN_BLOCKS
    return {
        "has_finance": True,
        "line_titles": {str(b): _FIN_BLOCKS[b]["title"].split(". ", 1)[-1]
                        for b in _FIN_BLOCKS},
        "finance_result": fin_result,
        "finance_combination": fin_combo,
        "interpretation": interp,
        "contours": extra,
        "summary": summary,
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



async def enrich_with_stages(db, results: dict[str, dict]) -> dict[str, dict]:
    """Обогащение снимков контуров стадиями ЖЦ из strategies (JOIN по
    combination_current и combination_resulting). Сам company_lifecycle —
    чистый модуль и в БД не ходит; стадии подставляются здесь."""
    combos = set()
    for r in results.values():
        for f in ("combination_current", "combination_resulting"):
            if r.get(f):
                combos.add(r[f])
    if not combos:
        return results
    rows = (await db.execute(
        select(Strategy.combination, Strategy.lifecycle_stage)
        .where(Strategy.combination.in_(combos))
    )).all()
    stage_by_combo = {c: st for c, st in rows}
    return {
        key: {
            **r,
            "lifecycle_stage": stage_by_combo.get(r.get("combination_current")),
            "transition_lifecycle_stage": stage_by_combo.get(r.get("combination_resulting")),
        }
        for key, r in results.items()
    }


async def load_report_contours(db, assessment, finance_result):
    """Дополнительные контуры и сводная карта. Общая сборка для PDF и для API
    страницы отчёта — иначе две версии отчёта разъедутся по составу разделов."""
    rows = (await db.execute(
        select(AssessmentContour).where(
            AssessmentContour.assessment_id == assessment.id,
            AssessmentContour.contour != "finance",
        )
    )).scalars().all()
    by_key = {r.contour: r for r in rows}

    extra = []
    no = 5
    for key in CONTOUR_ORDER:
        if key == "finance" or key not in by_key:
            continue
        spec = get_spec(key)
        content = await load_content(db, key)
        extra.append({
            "contour": key,
            "title": spec.title,
            "result": by_key[key].result,
            "combination": by_key[key].combination,
            "interp": build_interpretation(by_key[key].result, content, spec.blocks),
            "section_no": f"{no:02d}",
            # Названия линий — с сервера: во фронте они были бы копией реестра
            "line_titles": {str(b): spec.blocks[b]["title"].split(". ", 1)[-1]
                            for b in spec.blocks},
        })
        no += 1

    all_results = {"finance": finance_result} if finance_result else {}
    for key, row in by_key.items():
        all_results[key] = row.result

    summary = build_summary(all_results)
    if summary is not None:
        from app.contour_route import build_summary_route
        summary["route"] = build_summary_route(all_results)
        # Жизненный цикл компании: по контуру-ограничению, а не по финансам.
        enriched = await enrich_with_stages(db, all_results)
        summary["company_lifecycle"] = build_company_lifecycle(enriched, summary)
        # Прогресс нужен, когда цикл ещё не собран: пользователю важно видеть,
        # сколько контуров осталось, а не просто отсутствие раздела.
        summary["lifecycle_progress"] = lifecycle_progress(all_results)
    return extra, summary


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

    extra_contours, summary = await load_report_contours(db, assessment, finance_result)

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
        extra_contours=extra_contours,
        summary=summary,
    )
