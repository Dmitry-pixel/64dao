import logging
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def send_otp_email(to: str, code: str, name: str | None = None) -> None:
    if settings.debug:
        logger.warning("=== DEBUG OTP === email=%s code=%s ===", to, code)
        return
    greeting = f"Здравствуйте, {name}!" if name else "Здравствуйте!"
    html = f"<html><body><p>{greeting}</p><p>Код: <b>{code}</b></p><p>Действует 10 минут.</p></body></html>"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{code} — код входа в 64DAO"
    msg["From"] = f"64DAO <{settings.smtp_from_address}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))
    await aiosmtplib.send(msg, hostname=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_user, password=settings.smtp_pass, use_tls=settings.smtp_use_tls)


async def send_welcome_email(to: str, name: str) -> None:
    if settings.debug:
        logger.info("=== DEBUG WELCOME === email=%s name=%s ===", to, name)
        return
    html = f"<html><body><p>Добро пожаловать, {name}!</p></body></html>"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Добро пожаловать в 64DAO"
    msg["From"] = f"64DAO <{settings.smtp_from_address}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))
    await aiosmtplib.send(msg, hostname=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_user, password=settings.smtp_pass, use_tls=settings.smtp_use_tls)
