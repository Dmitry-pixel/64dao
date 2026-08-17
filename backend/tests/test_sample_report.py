# -*- coding: utf-8 -*-
"""
Форма перед скачиванием документов лендинга.

Запуск: docker compose exec backend pytest tests/test_sample_report.py -v

Что проверяем и почему именно это:
- обязательность имени, e-mail и телефона — ради них форму и переделывали;
- маршрутизацию method -> файл -> source: одна форма обслуживает три
  документа, и перепутанный слот означает, что человек получил чужой PDF,
  а лид попал не в тот сегмент;
- отсутствие файла: контакт должен сохраниться, даже если PDF ещё не
  загружен в админку. Раньше на этом месте открывалась вкладка с 404.
"""
import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
from sqlalchemy import select

from app.limiter import limiter
from app.routers.sample_report import REQUEST_RATE_LIMIT
from app.models import SampleLead
from app.sample_report_store import file_for

PAYLOAD = {
    "name": "Иван Петров",
    "email": "ivan@company.ru",
    "phone": "+7 900 000-00-00",
    "consent": True,
}


@pytest.fixture(autouse=True)
def _no_smtp(monkeypatch):
    """Письмо не отправляем: тест про запись лида, а не про SMTP."""
    import app.routers.sample_report as r
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(r, "send_sample_report_email", mock)
    return mock


@pytest.fixture(autouse=True)
def _no_rate_limit():
    """Лимитер 5/мин ключуется по IP, а в тестах он у всех один — 127.0.0.1.
    Без этого шестой POST в наборе получал 429, и падение выглядело как
    поломка эндпоинта. Гасим лимитер явно, а не подгоняем число запросов:
    иначе любой новый тест снова упрётся в невидимый потолок.
    Что лимит на месте, проверяет test_rate_limit_applies ниже."""
    limiter.enabled = False
    yield
    limiter.enabled = True


def _write_pdf(method: str | None) -> None:
    path = file_for(method)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 test")


def _drop_pdf(method: str | None) -> None:
    path = file_for(method)
    if path.exists():
        path.unlink()


# ── Валидация ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["name", "email", "phone"])
async def test_required_fields(client: AsyncClient, missing):
    body = {k: v for k, v in PAYLOAD.items() if k != missing}
    res = await client.post("/api/sample-report/request", json=body)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_email_must_be_valid(client: AsyncClient):
    res = await client.post("/api/sample-report/request", json={**PAYLOAD, "email": "ivan"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_consent_required(client: AsyncClient):
    res = await client.post("/api/sample-report/request", json={**PAYLOAD, "consent": False})
    assert res.status_code == 400


# ── Запись лида ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lead_saved_with_all_contacts(client: AsyncClient, db_session):
    _write_pdf("1")
    res = await client.post("/api/sample-report/request", json={
        **PAYLOAD, "max_address": "+79000000001", "telegram_address": "@ivan", "method": "1",
    })
    assert res.status_code == 200

    lead = (await db_session.execute(select(SampleLead))).scalars().first()
    assert lead.name == "Иван Петров"
    assert lead.email == "ivan@company.ru"
    assert lead.phone == "+7 900 000-00-00"
    assert lead.max_addr == "+79000000001"
    assert lead.tg_addr == "@ivan"
    assert lead.source == "sample_m12"
    # channel/address заполняются ради совместимости со строками старой формы
    assert lead.channel == "email"
    assert lead.address == "ivan@company.ru"


@pytest.mark.asyncio
async def test_blank_messengers_stored_as_null(client: AsyncClient, db_session):
    _write_pdf("1")
    res = await client.post("/api/sample-report/request", json={
        **PAYLOAD, "max_address": "   ", "telegram_address": "", "method": "1",
    })
    assert res.status_code == 200

    lead = (await db_session.execute(select(SampleLead))).scalars().first()
    # Пробелы — это отсутствие контакта, а не контакт из пробелов: иначе
    # выгрузка выглядит заполненной, а звонить некуда.
    assert lead.max_addr is None
    assert lead.tg_addr is None


# ── Маршрутизация документов ─────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("method,source,suffix", [
    ("1", "sample_m12", "?method=1"),
    ("3", "sample_m3", "?method=3"),
    ("methodology", "methodology", "?method=methodology"),
])
async def test_method_routes_to_document(client: AsyncClient, db_session, method, source, suffix):
    _write_pdf(method)
    res = await client.post("/api/sample-report/request", json={**PAYLOAD, "method": method})
    assert res.status_code == 200
    assert res.json()["pdf_url"] == f"/api/sample-report/view{suffix}"

    lead = (await db_session.execute(select(SampleLead))).scalars().first()
    assert lead.source == source


@pytest.mark.asyncio
async def test_unknown_method_falls_back_to_m12(client: AsyncClient, db_session):
    _write_pdf("1")
    res = await client.post("/api/sample-report/request", json={**PAYLOAD, "method": "42"})
    assert res.status_code == 200
    lead = (await db_session.execute(select(SampleLead))).scalars().first()
    assert lead.source == "sample_m12"


# ── Файла ещё нет ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lead_saved_when_file_missing(client: AsyncClient, db_session):
    _drop_pdf("methodology")
    res = await client.post("/api/sample-report/request", json={**PAYLOAD, "method": "methodology"})
    assert res.status_code == 200
    body = res.json()
    assert body["file_ready"] is False
    assert body["pdf_url"] is None
    assert body["emailed"] is False

    lead = (await db_session.execute(select(SampleLead))).scalars().first()
    assert lead is not None


@pytest.mark.asyncio
async def test_view_404_when_file_missing(client: AsyncClient):
    _drop_pdf("methodology")
    res = await client.get("/api/sample-report/view?method=methodology")
    assert res.status_code == 404


# ── Админская выдача ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_leads_require_admin(client: AsyncClient, auth_client: AsyncClient):
    assert (await client.get("/api/sample-report/leads")).status_code in (401, 403)
    assert (await auth_client.get("/api/sample-report/leads")).status_code == 403


@pytest.mark.asyncio
async def test_leads_expose_new_columns(client: AsyncClient, admin_client: AsyncClient):
    _write_pdf("1")
    await client.post("/api/sample-report/request", json={
        **PAYLOAD, "telegram_address": "@ivan", "method": "1",
    })
    rows = (await admin_client.get("/api/sample-report/leads")).json()
    assert rows and set(rows[0]) >= {
        "email", "phone", "max_address", "telegram_address", "source",
    }
    assert rows[0]["telegram_address"] == "@ivan"


# ── Лимит запросов ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_applies(client: AsyncClient):
    """Запрос сверх потолка отбивается.

    Число берём из REQUEST_RATE_LIMIT, а не пишем цифрой: потолок уже
    поднимали с 5 до 20, и захардкоженный тест пришлось бы править следом
    — либо он молча проверял бы не то.

    Отдельный IP в заголовке — чтобы тест не зависел от того, сколько
    запросов сделали соседние тесты: _client_ip читает x-real-ip первым.
    """
    limit = int(REQUEST_RATE_LIMIT.split("/")[0])
    _write_pdf("1")
    headers = {"x-real-ip": "203.0.113.77"}
    limiter.enabled = True
    try:
        codes = []
        for _ in range(limit + 1):
            res = await client.post(
                "/api/sample-report/request",
                json={**PAYLOAD, "method": "1"},
                headers=headers,
            )
            codes.append(res.status_code)
    finally:
        limiter.enabled = False

    assert codes[:limit] == [200] * limit
    assert codes[limit] == 429


@pytest.mark.asyncio
async def test_csv_header(admin_client: AsyncClient):
    res = await admin_client.get("/api/sample-report/leads.csv")
    assert res.status_code == 200
    header = res.text.lstrip("﻿").splitlines()[0]
    assert header.split(";")[:6] == ["Имя", "E-mail", "Телефон", "Max", "Telegram", "Документ"]
