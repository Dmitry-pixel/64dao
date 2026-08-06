# -*- coding: utf-8 -*-
"""
Фича F: чек-листы шагов маршрута перехода. Маршрут детерминирован и
пересчитывается (contour_route/finance_interpret), в БД — только отметки
(route_progress). Доступ — владелец диагностики или админ. Гейта подписки нет:
чек-лист входит в ценность купленной диагностики (подписка — только «Динамика»).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Assessment, AssessmentContour, RouteProgress, User
from app.contours import CONTOUR_ORDER
from app.finance_interpret import enrich_route, load_content

router = APIRouter(prefix="/api/assessments", tags=["checklist"])

CONTOUR_TITLES = {
    "finance": "Финансы",
    "product": "Продукт",
    "process": "Процессы",
    "market": "Рынок",
}


class ToggleBody(BaseModel):
    done: bool


async def _owned_assessment(assessment_id: str, user: User, db: AsyncSession) -> Assessment:
    a = await db.scalar(select(Assessment).where(
        Assessment.id == assessment_id, Assessment.deleted_at.is_(None)))
    if not a:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    if a.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")
    return a


@router.get("/{assessment_id}/checklist")
async def get_checklist(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    a = await _owned_assessment(assessment_id, user, db)
    done_rows = (await db.execute(
        select(RouteProgress.contour, RouteProgress.line, RouteProgress.done_at)
        .where(RouteProgress.assessment_id == a.id)
    )).all()
    done = {(r.contour, r.line): r.done_at for r in done_rows}
    contours = (await db.execute(
        select(AssessmentContour).where(AssessmentContour.assessment_id == a.id)
    )).scalars().all()
    by_name = {c.contour: c for c in contours}
    out = []
    total = 0
    total_done = 0
    for cname in CONTOUR_ORDER:
        ac = by_name.get(cname)
        if not ac:
            continue
        content = await load_content(db, cname)
        steps = enrich_route(ac.result, content)
        if not steps:
            continue
        items = []
        for s in steps:
            key = (cname, s["line"])
            is_done = key in done
            items.append({
                "line": s["line"],
                "order": s["order"],
                "action_text": s.get("action_text"),
                "after_essence": s.get("after_essence"),
                "hexagram_after": s.get("hexagram_after"),
                "is_last": s.get("is_last"),
                "done": is_done,
                "done_at": done[key].isoformat() if is_done and done[key] else None,
            })
            total += 1
            total_done += 1 if is_done else 0
        out.append({
            "contour": cname,
            "title": CONTOUR_TITLES.get(cname, cname),
            "steps": items,
        })
    progress = round(100 * total_done / total) if total else 0
    return {
        "has_route": total > 0,
        "contours": out,
        "total": total,
        "done": total_done,
        "progress": progress,
    }


@router.put("/{assessment_id}/checklist/{contour}/{line}")
async def toggle_step(
    assessment_id: str,
    contour: str,
    line: int,
    body: ToggleBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    a = await _owned_assessment(assessment_id, user, db)
    if contour not in CONTOUR_ORDER:
        raise HTTPException(status_code=400, detail="Неизвестный контур")
    if not 1 <= line <= 6:
        raise HTTPException(status_code=400, detail="Неверный номер линии")
    existing = await db.scalar(select(RouteProgress).where(
        RouteProgress.assessment_id == a.id,
        RouteProgress.contour == contour,
        RouteProgress.line == line,
    ))
    if body.done and not existing:
        db.add(RouteProgress(assessment_id=a.id, contour=contour, line=line))
        await db.flush()
    elif not body.done and existing:
        await db.execute(delete(RouteProgress).where(
            RouteProgress.assessment_id == a.id,
            RouteProgress.contour == contour,
            RouteProgress.line == line,
        ))
    return {"contour": contour, "line": line, "done": body.done}
