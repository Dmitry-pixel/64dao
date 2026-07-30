import logging
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

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


async def send_forgot_password_email(to: str, name: str | None, reset_link: str) -> None:
    name_part = f", {name}" if name else ""
    subject, body = _render("forgot_password", {"name": name or "", "name_part": name_part, "reset_link": reset_link})
    if settings.debug:
        logger.info("=== DEBUG FORGOT PASSWORD === email=%s link=%s ===", to, reset_link)
        return
    await _send_message(to, subject, _wrap_html(body), _sender("forgot_password"))


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


async def send_support_email(from_email: str, from_name: str | None, message: str) -> None:
    """Отправляет сообщение пользователя на адрес поддержки (smtp_from_address)."""
    admin_email = settings.support_email_address
    if not admin_email:
        logger.warning("send_support_email: smtp_from_address не настроен")
        return
    name_display = from_name or from_email
    subject = f"Поддержка 64DAO — сообщение от {name_display}"
    body_html = (
        f"<p><b>От:</b> {name_display} ({from_email})</p>"
        f"<p><b>Сообщение:</b></p>"
        f"<p style='white-space:pre-wrap;'>{message}</p>"
    )
    if settings.debug:
        logger.info("=== DEBUG SUPPORT === from=%s message=%s ===", from_email, message)
        return
    await _send_message(admin_email, subject, _wrap_html(body_html))


async def send_sample_report_email(to: str, name: str | None = None) -> None:
    """Письмо с примером отчёта (PDF во вложении)."""
    name_part = f", {name}" if name else ""
    body_html = _wrap_html(
        f"<p>Здравствуйте{name_part}!</p>"
        "<p>Во вложении — пример стратегического отчёта <b>64 ДАО</b>. "
        "Он также открылся у вас в браузере.</p>"
        "<p style=\"color:#999;font-size:12px;\">Команда 64DAO</p>"
    )
    if settings.debug:
        logger.info("=== DEBUG SAMPLE REPORT === email=%s ===", to)
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = "Пример отчёта — 64 ДАО"
    msg["From"] = f"64DAO <{settings.smtp_from_address}>"
    msg["To"] = to

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(alt)

    sample_file = Path("/var/www/64dao/uploads/sample_report.pdf")
    if sample_file.exists():
        part = MIMEApplication(sample_file.read_bytes(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename="64dao-sample-report.pdf")
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
