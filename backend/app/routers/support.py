from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.auth import get_current_user
from app.models import User
from app import email as email_module
import logging

router = APIRouter(prefix="/api/support", tags=["support"])
logger = logging.getLogger(__name__)

class SupportRequest(BaseModel):
    subject: str
    message: str

@router.post("/send")
async def send_support_message(
    body: SupportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.subject.strip() or not body.message.strip():
        raise HTTPException(status_code=422, detail="Тема и сообщение обязательны")

    html = (
        f"<p><b>От:</b> {current_user.email}</p>"
        f"<p><b>Имя:</b> {current_user.full_name or chr(8212)}</p>"
        f"<p><b>Тема:</b> {body.subject}</p>"
        "<hr style=\"border:none;border-top:1px solid #eee;margin:16px 0\"/>"
        f"<p style=\"white-space:pre-wrap;\">{body.message}</p>"
        "<hr style=\"border:none;border-top:1px solid #eee;margin:16px 0\"/>"
        f"<p style=\"color:#999;font-size:12px;\">Ответить: "
        f"<a href=\"mailto:{current_user.email}\">{current_user.email}</a></p>"
    )

    try:
        await email_module._send_message(
            to="support@64dao.ru",
            subject=f"[Поддержка] {body.subject}",
            html=email_module._wrap_html(html),
        )
    except Exception as e:
        logger.error("Support email error: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось отправить сообщение. Попробуйте позже.")

    return {"ok": True}
