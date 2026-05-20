import json
import logging
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

TEMPLATES_FILE = Path("/var/www/64dao/uploads/email_templates.json")

DEFAULT_TEMPLATES = {
    "otp": {
        "subject": "{code} — код входа в 64DAO",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Ваш код для входа в систему <b>64DAO</b>:</p>"
            "<p style=\"font-size:28px;font-weight:700;letter-spacing:6px;color:#1a2540;\">{code}</p>"
            "<p>Код действует <b>10 минут</b>. Не передавайте его никому.</p>"
            "<p style=\"color:#999;font-size:12px;\">Если вы не запрашивали код — просто проигнорируйте это письмо.</p>"
        ),
    },
    "welcome": {
        "subject": "Добро пожаловать в 64DAO",
        "body_html": (
            "<p>Добро пожаловать{name_part}!</p>"
            "<p>Вы успешно зарегистрировались в системе стратегической диагностики <b>64DAO</b>.</p>"
            "<p>Вы можете войти в свой кабинет и начать первую диагностику.</p>"
            "<p style=\"color:#999;font-size:12px;\">Команда 64DAO</p>"
        ),
    },
    "forgot_password": {
        "subject": "Сброс пароля 64DAO",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Мы получили запрос на сброс пароля для вашей учётной записи.</p>"
            "<p style=\"margin:24px 0;\">"
            "<a href=\"{reset_link}\" style=\"background:#1a2540;color:#fff;padding:12px 24px;"
            "border-radius:6px;text-decoration:none;font-weight:600;\">Сбросить пароль</a>"
            "</p>"
            "<p>Или скопируйте ссылку в браузер:<br>"
            "<span style=\"color:#1e3a8a;font-size:13px;\">{reset_link}</span></p>"
            "<p>Ссылка действует <b>1 час</b>.</p>"
            "<p style=\"color:#999;font-size:12px;\">Если вы не запрашивали сброс пароля — просто проигнорируйте это письмо.</p>"
        ),
    },
}


def _load_templates() -> dict:
    try:
        return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {k: dict(v) for k, v in DEFAULT_TEMPLATES.items()}


def _render(template_key: str, variables: dict) -> tuple[str, str]:
    """Возвращает (subject, body_html) с подставленными переменными."""
    templates = _load_templates()
    tpl = templates.get(template_key, DEFAULT_TEMPLATES.get(template_key, {}))
    subject = tpl.get("subject", "")
    body = tpl.get("body_html", "")
    for key, val in variables.items():
        subject = subject.replace(f"{{{key}}}", str(val))
        body = body.replace(f"{{{key}}}", str(val))
    return subject, body


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


async def _send(to: str, subject: str, html: str) -> None:
    await aiosmtplib.send(
        MIMEMultipart("alternative"),  # placeholder — заменяется ниже
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_pass,
        use_tls=settings.smtp_use_tls,
    )


async def _send_message(to: str, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"64DAO <{settings.smtp_from_address}>"
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
    await _send_message(to, subject, _wrap_html(body))


async def send_forgot_password_email(to: str, name: str | None, reset_link: str) -> None:
    name_part = f", {name}" if name else ""
    subject, body = _render("forgot_password", {"name": name or "", "name_part": name_part, "reset_link": reset_link})
    if settings.debug:
        logger.info("=== DEBUG FORGOT PASSWORD === email=%s link=%s ===", to, reset_link)
        return
    await _send_message(to, subject, _wrap_html(body))


async def send_welcome_email(to: str, name: str) -> None:
    name_part = f", {name}" if name else ""
    subject, body = _render("welcome", {"name": name, "name_part": name_part})
    if settings.debug:
        logger.info("=== DEBUG WELCOME === email=%s name=%s ===", to, name)
        return
    await _send_message(to, subject, _wrap_html(body))
