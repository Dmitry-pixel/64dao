# -*- coding: utf-8 -*-
"""
CRUD контента интерпретации финансовой функции (fin_content).
Чтение и запись — только admin (это редактор контента для админки, Этап 7).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.db import get_db
from app.models import FinContent, User
from app.schemas import FinContentOut, FinContentUpsert

router = APIRouter(prefix="/api/fin-content", tags=["fin-content"])

ALLOWED_KINDS = {"tonality", "quadrant", "trigram", "tension_rule", "action_package"}


@router.get("", response_model=list[FinContentOut])
async def list_fin_content(
    kind: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(FinContent)
    if kind is not None:
        if kind not in ALLOWED_KINDS:
            raise HTTPException(status_code=400, detail="Недопустимый kind")
        q = q.where(FinContent.kind == kind)
    q = q.order_by(FinContent.kind, FinContent.sort, FinContent.key)
    return (await db.execute(q)).scalars().all()


@router.put("/{kind}/{key}", response_model=FinContentOut)
async def upsert_fin_content(
    kind: str,
    key: str,
    data: FinContentUpsert,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="Недопустимый kind")

    row = await db.scalar(
        select(FinContent).where(FinContent.kind == kind, FinContent.key == key)
    )
    if row is None:
        row = FinContent(kind=kind, key=key, payload=data.payload,
                         sort=data.sort, is_active=data.is_active)
        db.add(row)
    else:
        row.payload = data.payload
        row.sort = data.sort
        row.is_active = data.is_active

    await db.flush()
    await db.refresh(row)
    return row
