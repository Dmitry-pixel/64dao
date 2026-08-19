"""
Публичная форма обратной связи на лендинге (анонимные посетители).
POST /api/contact/send — отправляет письмо на адрес поддержки (support@64dao.ru).

Отдельно от /api/support/send (тот эндпоинт требует авторизации и
используется в личном кабинете залогиненных пользователей, и шлёт письма
на smtp_from_address — другой ящик, не support@).
"""
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.email import _send_message, _wrap_html, esc, header_safe
from app.limiter import limiter

router = APIRouter(prefix="/api/contact", tags=["contact"])
logger = logging.getLogger(__name__)

SUPPORT_EMAIL = "support@64dao.ru"


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(min_length=1, max_length=1000)


@router.post("/send")
@limiter.limit("3/minute")
async def send_contact_message(request: Request, body: ContactRequest):
    # Эндпоинт публичный и отправляет письмо на каждый вызов. Без лимита это
    # открытый релей: чужой скрипт разгоняет ваш SMTP до блокировки у
    # провайдера и просадки репутации домена.
    body_html = (
        f"<p><b>Сообщение с формы на лендинге 64dao.ru</b></p>"
        f"<p><b>Имя:</b> {esc(body.name)}</p>"
        f"<p><b>Email:</b> {esc(body.email)}</p>"
        f"<p style='white-space:pre-wrap;'>{esc(body.message)}</p>"
    )
    try:
        await _send_message(
            to=SUPPORT_EMAIL,
            subject=header_safe(f"[Лендинг] Сообщение от {body.name}"),
            html=_wrap_html(body_html),
        )
    except Exception as e:
        logger.error("Landing contact email error: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось отправить сообщение. Попробуйте позже.") from e

    return {"status": "ok"}
