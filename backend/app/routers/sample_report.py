"""
Пример отчёта.
GET  /api/sample-report            — скачивание PDF (attachment).
GET  /api/sample-report/view       — просмотр inline (открытие в новой вкладке).
POST /api/sample-report/request    — заявка (Имя+канал+адрес, e-mail: копия письмом).
GET  /api/sample-report/leads      — список заявок (admin).
GET  /api/sample-report/leads.csv  — экспорт CSV (admin).
"""
import io
import csv
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import SampleLead, User
from app.auth import require_admin
from app.limiter import limiter
from app.email import send_sample_report_email

router = APIRouter(prefix="/api/sample-report", tags=["sample-report"])
logger = logging.getLogger(__name__)

from app.sample_report_store import (
    file_for as sample_report_file_for,
    download_name_for as sample_report_name_for,
)

# Оставлено для совместимости: код вне этого модуля мог импортировать константу.
SAMPLE_REPORT_FILE = sample_report_file_for(None)
CHANNEL_LABEL = {"email": "E-mail", "telegram": "Telegram", "max": "Max"}


class SampleLeadRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    channel: Literal["email", "telegram", "max"]
    address: str = Field(min_length=1, max_length=320)
    consent: bool


@router.post("/request")
@limiter.limit("5/minute")
async def request_sample(
    body: SampleLeadRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not body.consent:
        raise HTTPException(status_code=400, detail="Требуется согласие на обработку данных")

    name = body.name.strip()
    address = body.address.strip()

    lead = SampleLead(
        name=name,
        channel=body.channel,
        address=address,
        consent=True,
        ip=request.client.host if request.client else None,
    )
    db.add(lead)
    await db.flush()  # commit выполняется в get_db

    emailed = False
    if body.channel == "email":
        try:
            await send_sample_report_email(address, name)
            emailed = True
        except Exception as e:
            logger.error("sample-report email error: %s", e)

    return {"ok": True, "pdf_url": "/api/sample-report/view", "emailed": emailed}


@router.get("/view")
async def view_sample_report(method: str | None = None):
    path = sample_report_file_for(method)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Отчёт пока не загружен")
    name = sample_report_name_for(method)
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )


@router.get("")
async def get_sample_report(method: str | None = None):
    path = sample_report_file_for(method)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Отчёт пока не загружен")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=sample_report_name_for(method),
    )


@router.get("/leads")
async def list_leads(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = (await db.execute(
        select(SampleLead).order_by(SampleLead.created_at.desc())
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "channel": r.channel,
            "address": r.address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/leads.csv")
async def export_leads_csv(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = (await db.execute(
        select(SampleLead).order_by(SampleLead.created_at.desc())
    )).scalars().all()

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM для Excel
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Имя", "Канал", "Адрес", "Дата"])
    for r in rows:
        w.writerow([
            r.name,
            CHANNEL_LABEL.get(r.channel, r.channel),
            r.address,
            r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sample-leads.csv"'},
    )
