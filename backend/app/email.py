import html as _html
import logging
import re as _re

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_CRLF = _re.compile(r"[\r\n]+")


def esc(value: object) -> str:
    """Экранирование значения для вставки в HTML письма.

    Поля форм обратной связи уходят в письмо администратору как есть. Без
    экранирования отправитель вставляет в него произвольную разметку —
    ссылку с подменённым текстом, фальшивую подпись, скрытый блок. Это не
    XSS в браузере пользователя, а фишинг в почтовом ящике поддержки.
    """
    return _html.escape(str(value), quote=True)


def header_safe(value: str, limit: int = 120) -> str:
    """Значение, пригодное для заголовка письма.

    CR/LF в Subject позволяют дописать собственные заголовки, в том числе
    Bcc. Python значения заголовков не валидирует — отсекаем здесь.
    """
    return _CRLF.sub(" ", value).strip()[:limit]

# Дефолты, чтение, запись и подстановка живут в одном модуле: раньше
# DEFAULT_TEMPLATES дублировался здесь и в routers/admin.py, и копии
# успели разойтись по полю description.
from app.email_templates_store import (  # noqa: F401
    DEFAULT_TEMPLATES,
    TEMPLATES_FILE,
    read_templates as _load_templates,
    render as _render,
    sender as _sender,
)


def _wrap_html(body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #1a2540; max-width: 520px;
         margin: 40px auto; padding: 32px; background: #f5f3ef; }}
  p {{ line-height: 1.7; margin: 0 0 14px; }}
</style>
</head>
<body>{body_html}</body>
</html>"""


async def _send_message(to: str, subject: str, html: str,
                        from_address: str | None = None) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"64DAO <{from_address or settings.smtp_from_address}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_pass,
        use_tls=settings.smtp_use_tls,
    )


async def send_otp_email(to: str, code: str, name: str | None = None) -> None:
    name_part = f", {name}" if name else ""
    subject, body = _render("otp", {"code": code, "name": name or "", "name_part": name_part})
    if settings.debug:
        logger.warning("=== DEBUG OTP === email=%s code=%s subject=%s ===", to, code, subject)
        return
    await _send_message(to, subject, _wrap_html(body), _sender("otp"))


async def send_welcome_email(to: str, name: str) -> None:
    name_part = f", {name}" if name else ""
    subject, body = _render("welcome", {"name": name, "name_part": name_part})
    if settings.debug:
        logger.info("=== DEBUG WELCOME === email=%s name=%s ===", to, name)
        return
    await _send_message(to, subject, _wrap_html(body), _sender("welcome"))


async def send_account_status_email(to: str, name: str | None, activated: bool) -> None:
    name_part = f", {name}" if name else ""
    key = "account_activated" if activated else "account_deactivated"
    subject, body = _render(key, {"name": name or "", "name_part": name_part})
    if settings.debug:
        logger.warning("=== DEBUG STATUS EMAIL === email=%s key=%s ===", to, key)
        return
    await _send_message(to, subject, _wrap_html(body), _sender(key))


# Подписи документов, которые уходят этой формой. Держим здесь, а не в
# роутере: письмо — единственное место, где они видны получателю.
_SAMPLE_DOC_TITLE = {
    "m12": ("Пример отчёта — 64 ДАО", "пример стратегического отчёта"),
    "m3": ("Пример отчёта · Метод 3 — 64 ДАО", "пример отчёта по Методу 3 «Матрица силы»"),
    "methodology": ("Методика 64DAO", "описание методологии"),
}


async def send_sample_report_email(
    to: str, name: str | None = None, method: str | None = None
) -> None:
    """Письмо с запрошенным документом (PDF во вложении).

    Раньше вложение было зашито на файл примера Методов 1-2, из-за чего запрос
    Метода 3 или методики приводил к письму с чужим PDF. Файл берём из того же
    хранилища, что и выдача по HTTP.
    """
    from app.sample_report_store import (
        file_for as _file_for,
        product_for as _product_for,
        download_name_for as _download_name_for,
    )

    product = _product_for(method)
    subject, doc_phrase = _SAMPLE_DOC_TITLE[product]

    name_part = f", {name}" if name else ""
    body_html = _wrap_html(
        f"<p>Здравствуйте{name_part}!</p>"
        f"<p>Во вложении — {doc_phrase} <b>64 ДАО</b>. "
        "Он также открылся у вас в браузере.</p>"
        "<p style=\"color:#999;font-size:12px;\">Команда 64DAO</p>"
    )
    if settings.debug:
        logger.info("=== DEBUG SAMPLE REPORT === email=%s product=%s ===", to, product)
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"64DAO <{settings.smtp_from_address}>"
    msg["To"] = to

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(alt)

    sample_file = _file_for(method)
    if sample_file.exists():
        part = MIMEApplication(sample_file.read_bytes(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=_download_name_for(method))
        msg.attach(part)

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_pass,
        use_tls=settings.smtp_use_tls,
    )


async def send_repeat_diagnostic_email(
    to: str, name: str | None, company_name: str | None, days_since: int
) -> None:
    """«Пора повторить диагностику» через N дней. Текст правится в админке."""
    name_part = f", {name}" if name else ""
    company_part = f" компании «{company_name}»" if company_name else ""
    subject, body = _render("repeat_diagnostic", {
        "name": name or "",
        "name_part": name_part,
        "company": company_name or "",
        "company_part": company_part,
        "days_since": days_since,
        "app_url": settings.app_url.rstrip("/"),
    })
    if settings.debug:
        logger.info("=== DEBUG REPEAT DIAGNOSTIC === email=%s days=%s ===",
                    to, days_since)
        return
    await _send_message(to, subject, _wrap_html(body), _sender("repeat_diagnostic"))


async def send_access_grant_email(
    to: str, name: str | None, quota: int, expires_at
) -> None:
    """Письмо партнёру о выданном временном бесплатном доступе.

    Текст правится в админке: «Email-шаблоны» -> «Тестовый доступ».
    Сбой отправки не является причиной откатить грант: доступ уже выдан,
    письмо переотправляется кнопкой в админке (email_sent_at).
    """
    name_part = f", {name}" if name else ""
    subject, body = _render("access_grant", {
        "name": name or "",
        "name_part": name_part,
        "quota": quota,
        "expires_at": expires_at.strftime("%d.%m.%Y"),
        "app_url": settings.app_url.rstrip("/"),
    })
    if settings.debug:
        logger.info("=== DEBUG ACCESS GRANT === email=%s quota=%s until=%s ===",
                    to, quota, expires_at)
        return
    await _send_message(to, subject, _wrap_html(body), _sender("access_grant"))
