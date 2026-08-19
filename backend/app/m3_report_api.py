# -*- coding: utf-8 -*-
"""
Метод 3 — эндпоинт скачивания PDF.

Отдельный модуль, а не дописывание в routers/m3.py: роутер уже длинный, а
правка существующего файла на сервере дороже нового. Регистрация — двумя
строками в конце routers/m3.py, чтобы эндпоинт попал в тот же reports_router
с гейтом флага фичи: при m3_enabled=false он отдаёт 404 наравне с остальными.

Файл пересобирается на каждый запрос. Это безопасно: отчёт строится из снимка
m3_results, а не пересчитывается, поэтому повторная генерация детерминирована
и разойтись с ранее выданной не может.
"""
from __future__ import annotations

import logging
import tempfile
import uuid
from collections.abc import Callable
from datetime import UTC
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app import m3_service as svc
from app.auth import get_current_user
from app.db import get_db
from app.m3_access import ensure_result_access
from app.m3_models import M3ChecklistStep, M3Portfolio, M3TradeoffDecision, M3Weight
from app.m3_pdf import (
    PDF_MARGIN,
    build_portfolio_report_html,
    footer_template,
    header_template,
)
from app.models import User
from app.pdf import generate_pdf


def _unlink_quietly(path: Path) -> None:
    """Убрать временный файл после отдачи. Ошибку только логируем: ответ уже
    ушёл, а осиротевший файл в /tmp дешевле пятисотки на скачивании."""
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Не удалось удалить временный PDF Метода 3 %s: %s", path, exc)


def company_name_for(portfolio: M3Portfolio, user: User) -> str:
    """
    Название компании для заголовка отчёта.

    По решению владельца оно вводится перед диагностикой, как в Методах 1 и 2,
    и живёт на портфеле (колонка появилась миграцией 024).

    Запасные звенья оставлены для портфелей, созданных до миграции: у них
    названия компании никто не спрашивал, и «Компания» вместо осмысленного
    заголовка была бы регрессом для уже выданных отчётов.
    """
    return (
        portfolio.company_name
        or portfolio.title
        or getattr(user, "company_name", None)
        or "Компания"
    )


async def collect_report_context(
    db: AsyncSession,
    portfolio: M3Portfolio,
    user: User,
) -> dict[str, Any]:
    """Всё, что нужно сборщику HTML, одним словарём — чтобы тест мог его собрать."""
    report = await svc.build_report(db, portfolio)

    steps = (await db.execute(
        select(M3ChecklistStep)
        .where(M3ChecklistStep.portfolio_id == portfolio.id)
        .order_by(M3ChecklistStep.wave, M3ChecklistStep.step_type, M3ChecklistStep.line)
    )).scalars().all()

    decision = await db.scalar(
        select(M3TradeoffDecision)
        .where(M3TradeoffDecision.portfolio_id == portfolio.id)
        .order_by(M3TradeoffDecision.decided_at.desc())
        .limit(1)
    )

    industry_name = None
    if portfolio.industry_id is not None:
        row = await db.scalar(
            select(M3Weight).where(M3Weight.industry_id == portfolio.industry_id)
        )
        industry_name = row.name if row else None

    return {
        "report": report,
        "steps": list(steps),
        "decision": decision,
        "company_name": company_name_for(portfolio, user),
        "industry_name": industry_name,
        "config": svc.get_config(),
    }


def register_download(
    router: Any,
    owned: Callable[..., Any],
) -> None:
    """
    Вешает GET /{portfolio_id}/download на переданный роутер.

    `owned` — уже существующая в routers/m3.py проверка «владелец или админ»:
    второй её копии в проекте быть не должно.
    """

    @router.get("/{portfolio_id}/download")
    async def download_m3_report(
        portfolio_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        from datetime import datetime

        portfolio = await owned(portfolio_id, user, db)
        ensure_result_access(portfolio, user)
        try:
            context = await collect_report_context(db, portfolio, user)
        except svc.M3ServiceError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        html = build_portfolio_report_html(
            report=context["report"],
            steps=context["steps"],
            decision=context["decision"],
            company_name=context["company_name"],
            generated_at=datetime.now(UTC),
            industry_name=context["industry_name"],
            config=context["config"],
        )

        # Файл собирается на каждый запрос и не хранится: копия в uploads
        # только копилась бы. Удаляем фоновой задачей — раньше нельзя,
        # FileResponse отдаёт тело уже после возврата из обработчика.
        path = Path(tempfile.gettempdir()) / f"dao64-m3-{portfolio_id}-{uuid4().hex}.pdf"
        await generate_pdf(
            html, str(path),
            header_html=header_template(context["company_name"]),
            footer_html=footer_template(),
            margin=PDF_MARGIN,
        )

        filename = f"64dao-matrica-sily-{portfolio_id}.pdf"
        return FileResponse(
            path=str(path),
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            background=BackgroundTask(_unlink_quietly, path),
        )

    return download_m3_report
