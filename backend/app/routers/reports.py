import logging
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.background import BackgroundTask

from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import Report, User
from app.pdf import generate_pdf
from app.routers.assessments import _ensure_result_access, build_html_for_assessment

settings = get_settings()

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _unlink_quietly(path: Path) -> None:
    """Убрать временный файл после отдачи.

    Ошибку только логируем: ответ пользователю уже ушёл, и падать здесь
    незачем — осиротевший файл в /tmp дешевле пятисотки на скачивании.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Не удалось удалить временный PDF %s: %s", path, exc)


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.id == report_id)
        .options(selectinload(Report.assessment))
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    # Только владелец или администратор
    is_owner = report.user_id == user.id
    is_admin = user.role == "admin"
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Нет доступа")

    # Отзыв доступа при возврате. Рефанд переводит диагностику в draft, но
    # ссылка на готовый PDF оставалась рабочей: это единственный эндпоинт
    # выдачи файла, и проверки статуса в нём не было. id отчёта пользователь
    # видит в /api/payments/orders, так что доступ переживал возврат денег.
    _ensure_result_access(report.assessment, user)

    cleanup: BackgroundTask | None = None

    if settings.regenerate_pdf_on_download:
        owner = await db.scalar(select(User).where(User.id == report.user_id))
        if owner is None:
            raise HTTPException(status_code=404, detail="Владелец отчёта не найден")

        filename_new = report.pdf_filename or f"report-{report_id}.pdf"
        # Пересобранный файл не храним: он всё равно строится заново на каждое
        # скачивание, поэтому копия на диске только копится. Пишем во временный
        # файл и удаляем после отдачи — раньше нельзя, FileResponse отдаёт тело
        # уже после возврата из обработчика.
        path = Path(tempfile.gettempdir()) / f"dao64-{report_id}-{uuid4().hex}.pdf"
        cleanup = BackgroundTask(_unlink_quietly, path)

        # Пересобираем из текущих данных: отчёт всегда в актуальной вёрстке
        html = await build_html_for_assessment(db, report.assessment, owner, allow_draft=False)
        await generate_pdf(html, str(path))
        report.pdf_filename = filename_new
        await db.flush()
    else:
        if not report.pdf_path:
            raise HTTPException(status_code=404, detail="Файл отчёта не найден")
        path = Path(report.pdf_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Файл отчёта не найден на диске")

    filename = report.pdf_filename or f"report-{report_id}.pdf"

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
        background=cleanup,
    )
