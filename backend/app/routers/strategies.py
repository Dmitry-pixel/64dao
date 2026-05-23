from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.db import get_db
from app.models import Strategy, User
from app.schemas import StrategyOut, StrategyListItem, StrategyCreate, StrategyUpdate

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/all", response_model=list[StrategyListItem])
async def get_all_strategies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Все 64 стратегии для админки."""
    if user.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    result = await db.execute(select(Strategy).order_by(Strategy.combination))
    return result.scalars().all()


@router.get("/{combination}", response_model=StrategyOut)
async def get_strategy_by_combination(
    combination: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if len(combination) != 6 or not all(c in "AB" for c in combination.upper()):
        raise HTTPException(status_code=400, detail="Комбинация должна быть 6 символов A/B")

    # Админ видит и неопубликованные
    q = select(Strategy).where(Strategy.combination == combination.upper())
    if user.role not in ("admin", "editor"):
        q = q.where(Strategy.is_published == True)

    strategy = await db.scalar(q)
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")
    return strategy


@router.put("/{combination}", response_model=StrategyOut)
async def upsert_strategy(
    combination: str,
    data: StrategyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать или обновить стратегию (только admin/editor)."""
    if user.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    combination = combination.upper()
    if len(combination) != 6 or not all(c in "AB" for c in combination):
        raise HTTPException(status_code=400, detail="Комбинация должна быть 6 символов A/B")

    strategy = await db.scalar(
        select(Strategy).where(Strategy.combination == combination)
    )

    if strategy is None:
        # Создаём новую
        strategy = Strategy(combination=combination)
        db.add(strategy)

    # Обновляем поля
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(strategy, field, value)

    await db.flush()
    await db.refresh(strategy)
    return strategy
