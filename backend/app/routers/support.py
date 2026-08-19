import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import email as email_module
from app.auth import get_current_user
from app.db import get_db
from app.limiter import limiter
from app.models import User

router = APIRouter(prefix="/api/support", tags=["support"])
logger = logging.getLogger(__name__)

class SupportRequest(BaseModel):
    # Границы длины: без них тело письма ограничено только client_max_body_size.
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)

@router.post("/send")
@limiter.limit("5/minute")
async def send_support_message(
    request: Request,
    body: SupportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.subject.strip() or not body.message.strip():
        raise HTTPException(status_code=422, detail="Тема и сообщение обязательны")

    email = email_module.esc(current_user.email)
    html = (
        f"<p><b>От:</b> {email}</p>"
        f"<p><b>Имя:</b> {email_module.esc(current_user.full_name or chr(8212))}</p>"
        f"<p><b>Тема:</b> {email_module.esc(body.subject)}</p>"
        "<hr style=\"border:none;border-top:1px solid #eee;margin:16px 0\"/>"
        f"<p style=\"white-space:pre-wrap;\">{email_module.esc(body.message)}</p>"
        "<hr style=\"border:none;border-top:1px solid #eee;margin:16px 0\"/>"
        f"<p style=\"color:#999;font-size:12px;\">Ответить: "
        f"<a href=\"mailto:{email}\">{email}</a></p>"
    )

    try:
        await email_module._send_message(
            to="support@64dao.ru",
            subject=email_module.header_safe(f"[Поддержка] {body.subject}"),
            html=email_module._wrap_html(html),
        )
    except Exception as e:
        logger.error("Support email error: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось отправить сообщение. Попробуйте позже.") from e

    return {"ok": True}
