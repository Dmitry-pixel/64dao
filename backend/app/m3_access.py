# -*- coding: utf-8 -*-
"""
Метод 3 — доступ и списание кредита.

Отдельный модуль, а не код в routers/m3.py: те же две проверки нужны и
эндпоинту скачивания PDF (m3_report_api), а вторая копия правил доступа
разошлась бы с первой при первой же правке.

Единица расхода Метода 3 — рассчитанный портфель. До расчёта пользователь
не получил ничего, что стоит денег, поэтому списание стоит на calculate,
а не на создании портфеля или заполнении анкеты.

Приоритет списания повторяет платный контур Методов 1 и 2 (routers/
assessments.py): сначала грант — он сгорает по сроку, потом платный
кредит — он не сгорает.

Администратор проходит мимо кассы: полный бесплатный доступ, решение
владельца. Та же ветка, что в assessments.py.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access_grants import pick_grant
from app.credits_settings import enforce_credits_enabled
from app.m3_models import M3Portfolio
from app.models import AccessGrant, Order, User

PRODUCT = "m3"

NO_CREDITS = ("Нет доступных диагностик Метода 3. "
              "Оплатите диагностику, чтобы получить доступ.")
NOT_PAID = ("Отчёт недоступен: диагностика не оплачена или оплата возвращена.")


def _free_pass(user: User) -> bool:
    """Проверка выключена или перед нами администратор."""
    return not enforce_credits_enabled() or user.role == "admin"


def ensure_result_access(portfolio: M3Portfolio, user: User) -> None:
    """Результат доступен только у рассчитанного портфеля.

    Аналог _ensure_result_access в routers/assessments.py, где закрыт
    результат черновика. Возврат заказа переводит портфель обратно в
    'filled' (payments._revoke_m3_order_access) — эта же проверка и
    закрывает доступ после рефанда.

    Снимок расчёта при возврате не удаляется, поэтому без явной проверки
    статуса отчёт продолжал бы собираться из него и после возврата денег.
    """
    if _free_pass(user):
        return
    if portfolio.status != "calculated":
        raise HTTPException(status_code=403, detail=NOT_PAID)


async def reserve_payment(
    db: AsyncSession, portfolio: M3Portfolio, user: User,
) -> tuple[AccessGrant | None, Order | None]:
    """Чем будет оплачен расчёт. Ничего не меняет — только выбирает.

    Выбор отделён от привязки сознательно: привязать нужно ПОСЛЕ успешного
    расчёта, иначе неудачная валидация анкеты (M3ServiceError -> 400)
    съедала бы кредит. Транзакция при исключении откатывается, но полагаться
    на это в вопросе денег не стоит: порядок вызовов виден в коде, поведение
    сессии — нет.

    Уже оплаченный портфель второй раз не списывает: повторный расчёт того
    же портфеля — исправление ответов, а не новая диагностика.
    """
    if _free_pass(user) or portfolio.order_id or portfolio.grant_id or portfolio.is_followup:
        # Повтор входит в стоимость первичного портфеля.
        return None, None

    grant = await pick_grant(db, user.id, PRODUCT)
    if grant is not None:
        return grant, None

    # Импорт внутри функции: routers.payments тянет за собой клиент банка
    # и настройки, а этот модуль импортируется из routers/m3.py на старте.
    from app.routers.payments import pick_order

    order = await pick_order(db, user.id, PRODUCT)
    if order is None:
        raise HTTPException(status_code=403, detail=NO_CREDITS)
    return None, order


def attach_payment(
    portfolio: M3Portfolio,
    grant: AccessGrant | None,
    order: Order | None,
) -> None:
    """Отметить, чем оплачен расчёт. Расход считается по этим полям."""
    if grant is not None:
        portfolio.grant_id = grant.id
    if order is not None:
        portfolio.order_id = order.id


# ── Повтор ────────────────────────────────────────────────────────────────────
def company_key(name: str | None) -> str:
    """Компания Метода 3 — это название (к companies портфель не привязан).
    Сравнение без учёта регистра и пробелов по краям, как в «Моих компаниях»."""
    return (name or "").strip().lower()


async def find_primary(db: AsyncSession, user: User, company_name: str | None) -> M3Portfolio | None:
    """Первичный рассчитанный портфель компании с неиспользованным правом на
    повтор — та же логика, что у Методов 1 и 4: сначала портфель с правом,
    среди равных самый свежий. Админ лимитом не ограничен. Без названия
    компании повтора нет: не с чем связать."""
    key = company_key(company_name)
    if not key:
        return None
    primary = await db.scalar(
        select(M3Portfolio)
        .where(M3Portfolio.user_id == user.id, M3Portfolio.status == "calculated",
               M3Portfolio.is_followup.is_(False), M3Portfolio.deleted_at.is_(None),
               func.lower(func.trim(M3Portfolio.company_name)) == key)
        .order_by((M3Portfolio.followup_used < M3Portfolio.followup_allowed).desc(),
                  M3Portfolio.calculated_at.desc())
        .limit(1)
    )
    if primary is None:
        return None
    if user.role != "admin" and primary.followup_used >= primary.followup_allowed:
        return None
    return primary


def use_followup(primary: M3Portfolio) -> None:
    """Засчитать повтор; у админа право поднимается, чтобы не нарушить
    проверку used <= allowed в базе."""
    if primary.followup_used >= primary.followup_allowed:
        primary.followup_allowed = primary.followup_used + 1
    primary.followup_used += 1
