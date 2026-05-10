from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Report, User

router = APIRouter(prefix="/api/reports", tags=["reports"])


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
    )
