"""
Пример отчёта.
GET  /api/sample-report            — скачивание PDF (attachment).
GET  /api/sample-report/view       — просмотр inline (открытие в новой вкладке).
POST /api/sample-report/request    — заявка (Имя+e-mail+телефон, Max/Telegram по желанию).
GET  /api/sample-report/leads      — список заявок (admin).
GET  /api/sample-report/leads.csv  — экспорт CSV (admin).
"""
import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.db import get_db
from app.email import send_sample_report_email
from app.limiter import limiter
from app.models import SampleLead, User

router = APIRouter(prefix="/api/sample-report", tags=["sample-report"])
logger = logging.getLogger(__name__)

from app.sample_report_store import (
    download_name_for as sample_report_name_for,
)
from app.sample_report_store import (
    file_for as sample_report_file_for,
)
from app.sample_report_store import (
    product_for as sample_report_product_for,
)

# Оставлено для совместимости: код вне этого модуля мог импортировать константу.
SAMPLE_REPORT_FILE = sample_report_file_for(None)
CHANNEL_LABEL = {"email": "E-mail", "telegram": "Telegram", "max": "Max"}

# Что человек запрашивал. Ключи те же, что у слотов файлов, плюс префикс
# sample_ у примеров: в выгрузке «m12» без контекста не читается.
SOURCE_BY_PRODUCT = {
    "m12": "sample_m12",
    "m3": "sample_m3",
    "methodology": "methodology",
}
# Потолок на IP, а не на человека: ключ — x-real-ip, и офис за одним NAT
# делит счётчик на всех. При 5/мин шестой коллега, открывший ссылку из
# корпоративного чата, не мог оставить контакт. 20 выбрано как запас на
# такую группу; злоупотребление формой ограничено тем, что адрес указывает
# сам заявитель — разослать письма третьим лицам через неё нельзя.
# Тест читает значение отсюда, менять только здесь.
REQUEST_RATE_LIMIT = "20/minute"

SOURCE_LABEL = {
    "sample_m12": "Пример отчёта · Методы 1-2",
    "sample_m3": "Пример отчёта · Метод 3",
    "methodology": "Методика 64DAO",
}


class SampleLeadRequest(BaseModel):
    """Имя, e-mail и телефон обязательны; мессенджеры — по желанию.

    Валидация телефона намеренно только по длине: строгая маска отсекает
    корпоративные добавочные и зарубежные номера, а лид с кривым номером
    полезнее отсутствующего лида.
    """
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=3, max_length=64)
    max_address: str | None = Field(default=None, max_length=320)
    telegram_address: str | None = Field(default=None, max_length=320)
    # Какой документ запрашивают: '1'/'3'/'methodology'. Неизвестное значение
    # sample_report_store сводит к примеру Методов 1-2 — см. product_for.
    method: str | None = None
    consent: bool


@router.post("/request")
@limiter.limit(REQUEST_RATE_LIMIT)
async def request_sample(
    body: SampleLeadRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not body.consent:
        raise HTTPException(status_code=400, detail="Требуется согласие на обработку данных")

    name = body.name.strip()
    email = body.email.strip()
    product = sample_report_product_for(body.method)

    lead = SampleLead(
        name=name,
        # channel/address заполняем, потому что колонки NOT NULL и на них
        # опираются старые строки: канал теперь всегда e-mail.
        channel="email",
        address=email,
        email=email,
        phone=body.phone.strip(),
        max_addr=(body.max_address or "").strip() or None,
        tg_addr=(body.telegram_address or "").strip() or None,
        source=SOURCE_BY_PRODUCT[product],
        consent=True,
        ip=request.client.host if request.client else None,
    )
    db.add(lead)
    await db.flush()  # commit выполняется в get_db

    # Файл могли ещё не загрузить в админку. Лид в этом случае уже сохранён —
    # терять контакт из-за отсутствующего PDF смысла нет, поэтому отвечаем 200
    # и сообщаем фронту, что открывать нечего.
    file_ready = sample_report_file_for(body.method).exists()

    emailed = False
    if file_ready:
        try:
            await send_sample_report_email(email, name, method=body.method)
            emailed = True
        except Exception as e:
            logger.error("sample-report email error: %s", e)

    suffix = f"?method={body.method}" if body.method else ""
    return {
        "ok": True,
        "pdf_url": f"/api/sample-report/view{suffix}" if file_ready else None,
        "file_ready": file_ready,
        "emailed": emailed,
    }


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
            # У строк старой формы новых полей нет — отдаём null, админка
            # рисует прочерк, а не пустую ячейку неясного происхождения.
            "email": r.email,
            "phone": r.phone,
            "max_address": r.max_addr,
            "telegram_address": r.tg_addr,
            "source": r.source,
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
    w.writerow(["Имя", "E-mail", "Телефон", "Max", "Telegram", "Документ", "Канал (старая форма)", "Адрес", "Дата"])
    for r in rows:
        w.writerow([
            r.name,
            r.email or "",
            r.phone or "",
            r.max_addr or "",
            r.tg_addr or "",
            SOURCE_LABEL.get(r.source or "", r.source or ""),
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
