from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.config import get_settings
from app.models import User
from app.site_mode import SiteMode, get_site_mode, set_site_mode

router = APIRouter()


@router.get("/api/site-mode")
async def read_site_mode():
    """Публичный ответ + флаг раздела Метода 3.

    Флаг нужен фронту, чтобы не показывать вход в раздел и не запрашивать
    /api/m3/*, пока он выключен: при m3_enabled=false весь раздел отдаёт 404
    (осознанное решение — до релиза о его существовании нельзя узнать
    снаружи), и кабинет получал бы 404 на каждый заход.

    Сам факт «раздел будет» флаг раскрывает, но это уже раскрыто вёрсткой
    и прайсом на витрине, а 404 остаётся 404: данные раздела по-прежнему
    недоступны.

    response_model снят: SiteMode описывает только режим техобслуживания,
    а расширять его чужим полем — значит смешивать две настройки в одной
    модели ради одного эндпоинта.
    """
    return {**get_site_mode().model_dump(), "m3_enabled": get_settings().m3_enabled}


@router.put("/api/admin/site-mode", response_model=SiteMode)
async def update_site_mode(
    payload: SiteMode,
    admin: User = Depends(require_admin),
):
    return set_site_mode(payload)
