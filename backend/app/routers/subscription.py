# -*- coding: utf-8 -*-
"""
Статус подписки текущего пользователя (роадмап 3.1, PR4b).

Единый источник проверки доступа — subscription_service (правило проекта:
не дублировать проверку по роутерам). Здесь только read-only статус для
отображения в профиле; выдача/отзыв остаются в админском роутере.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import SubscriptionStatus
from app import subscription_service as subs

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


@router.get("/status", response_model=SubscriptionStatus)
async def my_subscription_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await subs.status_for(db, user.id)
