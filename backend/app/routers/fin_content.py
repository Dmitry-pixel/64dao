# -*- coding: utf-8 -*-
"""
CRUD контента интерпретации (fin_content). Чтение и запись — только admin.

Контент общий по умолчанию (contour='common') и может переопределяться под
конкретный контур диагностики. Резолюция при рендере — load_content(): строка
контура перекрывает общую (Поправка П1). PUT/DELETE адресуют конкретную
(kind, key, contour); без параметра contour работают с общим слоем 'common'.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.base_questions import BaseQuestionEditError, validate_edit
from app.db import get_db
from app.models import FinContent, User
from app.schemas import FinContentOut, FinContentUpsert

router = APIRouter(prefix="/api/fin-content", tags=["fin-content"])

ALLOWED_KINDS = {"tonality", "quadrant", "trigram", "tension_rule", "action_package",
                 "base_question"}
ALLOWED_CONTOURS = {"common", "finance", "product", "market", "process"}


@router.get("", response_model=list[FinContentOut])
async def list_fin_content(
    kind: str | None = None,
    contour: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(FinContent)
    if kind is not None:
        if kind not in ALLOWED_KINDS:
            raise HTTPException(status_code=400, detail="Недопустимый kind")
        q = q.where(FinContent.kind == kind)
    if contour is not None:
        if contour not in ALLOWED_CONTOURS:
            raise HTTPException(status_code=400, detail="Недопустимый contour")
        q = q.where(FinContent.contour == contour)
    q = q.order_by(FinContent.kind, FinContent.sort, FinContent.key)
    return (await db.execute(q)).scalars().all()


@router.put("/{kind}/{key}", response_model=FinContentOut)
async def upsert_fin_content(
    kind: str,
    key: str,
    data: FinContentUpsert,
    contour: str = "common",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="Недопустимый kind")
    if contour not in ALLOWED_CONTOURS:
        raise HTTPException(status_code=400, detail="Недопустимый contour")
    row = await db.scalar(
        select(FinContent).where(
            FinContent.kind == kind,
            FinContent.key == key,
            FinContent.contour == contour,
        )
    )
    if kind == "base_question":
        try:
            validate_edit(key, contour, data.payload, row.payload if row else None)
        except BaseQuestionEditError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    if row is None:
        row = FinContent(kind=kind, key=key, contour=contour, payload=data.payload,
                         sort=data.sort, is_active=data.is_active)
        db.add(row)
    else:
        row.payload = data.payload
        row.sort = data.sort
        row.is_active = data.is_active

    await db.flush()
    await db.refresh(row)
    return row


@router.delete("/{kind}/{key}", status_code=204)
async def delete_fin_content_override(
    kind: str,
    key: str,
    contour: str = "common",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удаление переопределения контура — возврат ключа к общему слою. Базовую
    строку 'common' удалять нельзя: ключ исчез бы из отчёта."""
    if contour == "common":
        raise HTTPException(status_code=400, detail="Базовую запись (common) удалять нельзя")
    if contour not in ALLOWED_CONTOURS:
        raise HTTPException(status_code=400, detail="Недопустимый contour")
    row = await db.scalar(
        select(FinContent).where(
            FinContent.kind == kind,
            FinContent.key == key,
            FinContent.contour == contour,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Переопределение не найдено")
    await db.delete(row)
