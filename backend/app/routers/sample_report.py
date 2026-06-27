"""
Публичная отдача PDF "Пример отчёта".
GET /api/sample-report — скачивание файла (без авторизации).
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/sample-report", tags=["sample-report"])

SAMPLE_REPORT_FILE = Path("/var/www/64dao/uploads/sample_report.pdf")


@router.get("")
async def get_sample_report():
    if not SAMPLE_REPORT_FILE.exists():
        raise HTTPException(status_code=404, detail="Отчёт пока не загружен")
    return FileResponse(
        path=str(SAMPLE_REPORT_FILE),
        media_type="application/pdf",
        filename="Example_report_64DAO.pdf",
    )
