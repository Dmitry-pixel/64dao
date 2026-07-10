from fastapi import APIRouter, Depends
from app.auth import require_admin
from app.models import User
from app.site_mode import SiteMode, get_site_mode, set_site_mode

router = APIRouter()


@router.get("/api/site-mode", response_model=SiteMode)
async def read_site_mode():
    return get_site_mode()


@router.put("/api/admin/site-mode", response_model=SiteMode)
async def update_site_mode(
    payload: SiteMode,
    admin: User = Depends(require_admin),
):
    return set_site_mode(payload)
