# -*- coding: utf-8 -*-
"""
Метод 3 — оплата расчёта.

Главное, что здесь проверяется, — непротекание балансов между продуктами.
Цены разные: кредит Методов 1 и 2 куплен дешевле, и если бы им можно было
оплатить Метод 3, вторая цена не значила бы ничего.

Единица расхода Метода 3 — рассчитанный портфель, поэтому списание стоит
на calculate: до расчёта пользователь не получил ничего, что стоит денег.
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

import app.m3_access as m3_access
from app.m3_models import M3Portfolio
from app.models import AccessGrant, Order

# Фикстуры и хелперы контрольного кейса переиспользуются: второй набор
# анкеты разошёлся бы с первым при правке пунктов.
from tests.test_m3_api import (  # noqa: F401
    M3, REPORTS, _fill, _make_portfolio, as_role, m3_on, seeded,
)


@pytest.fixture
def enforce_on(monkeypatch):
    """Флаг читается из credits_settings, а не из Settings: подменяем
    функцию там, где она импортирована, иначе тест работает вхолостую."""
    monkeypatch.setattr(m3_access, "enforce_credits_enabled", lambda: True)


async def _paid_order(db, user, product: str) -> Order:
    o = Order(user_id=user.id, product=product, amount=20000.00,
              currency="RUB", status="paid",
              paid_at=datetime.now(timezone.utc))
    db.add(o)
    await db.flush()
    return o


async def _grant(db, user, product: str, quota: int = 1) -> AccessGrant:
    g = AccessGrant(
        user_id=user.id, product=product, quota=quota,
        starts_at=datetime.now(timezone.utc) - timedelta(days=1),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="тест",
    )
    db.add(g)
    await db.flush()
    return g


@pytest_asyncio.fixture
async def filled(auth_client, seeded, m3_on):
    """Портфель с заполненной анкетой — остаётся только рассчитать."""
    p = await _make_portfolio(auth_client)
    await _fill(auth_client, p)
    return p


async def _portfolio_row(db, pid) -> M3Portfolio:
    return await db.scalar(select(M3Portfolio).where(M3Portfolio.id == pid))


# ── Списание ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculate_free_when_enforce_off(auth_client, filled, db_session):
    """Выключённый флаг ничего не меняет для живых пользователей."""
    r = await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")
    assert r.status_code == 200, r.text
    row = await _portfolio_row(db_session, filled["id"])
    assert row.status == "calculated"
    assert row.order_id is None and row.grant_id is None


@pytest.mark.asyncio
async def test_calculate_blocked_without_credits(auth_client, filled, db_session, enforce_on):
    r = await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")
    assert r.status_code == 403
    row = await _portfolio_row(db_session, filled["id"])
    assert row.status != "calculated"


@pytest.mark.asyncio
async def test_m12_credit_does_not_pay_for_m3(auth_client, filled, db_session,
                                              test_user, enforce_on):
    """Ключевая проверка второй цены: кошельки продуктов не сообщаются."""
    await _paid_order(db_session, test_user, "m12")
    r = await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_m12_grant_does_not_pay_for_m3(auth_client, filled, db_session,
                                             test_user, enforce_on):
    await _grant(db_session, test_user, "m12", quota=5)
    r = await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_m3_order_pays_and_is_recorded(auth_client, filled, db_session,
                                             test_user, enforce_on):
    order = await _paid_order(db_session, test_user, "m3")
    r = await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")
    assert r.status_code == 200, r.text

    row = await _portfolio_row(db_session, filled["id"])
    assert row.order_id == order.id
    assert row.status == "calculated"

    # Один портфель за заказ: остаток исчерпан.
    credits = (await auth_client.get("/api/payments/credits")).json()
    assert credits["products"]["m3"]["credits"] == 0


@pytest.mark.asyncio
async def test_grant_is_spent_before_paid_order(auth_client, filled, db_session,
                                                test_user, enforce_on):
    """Приоритет тот же, что в контуре Методов 1 и 2: грант сгорает по сроку,
    платный кредит — нет."""
    grant = await _grant(db_session, test_user, "m3")
    order = await _paid_order(db_session, test_user, "m3")

    r = await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")
    assert r.status_code == 200, r.text

    row = await _portfolio_row(db_session, filled["id"])
    assert row.grant_id == grant.id
    assert row.order_id is None
    # Платный кредит не тронут.
    credits = (await auth_client.get("/api/payments/credits")).json()
    assert credits["products"]["m3"]["paid_credits"] == 1
    assert order.status == "paid"


@pytest.mark.asyncio
async def test_recalculate_does_not_consume_second_credit(auth_client, filled,
                                                          db_session, test_user,
                                                          enforce_on):
    """Повторный расчёт того же портфеля — исправление ответов, а не новая
    диагностика."""
    await _paid_order(db_session, test_user, "m3")
    assert (await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")).status_code == 200
    r = await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_admin_calculates_without_credits(admin_client, seeded, m3_on,
                                                db_session, enforce_on):
    """Полный бесплатный доступ администратора — как в Методах 1 и 2."""
    p = await _make_portfolio(admin_client)
    await _fill(admin_client, p)
    r = await admin_client.post(f"{M3}/portfolios/{p['id']}/calculate")
    assert r.status_code == 200, r.text
    row = await _portfolio_row(db_session, p["id"])
    assert row.order_id is None and row.grant_id is None


# ── Доступ к результату ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_blocked_when_portfolio_not_calculated(auth_client, filled, enforce_on):
    r = await auth_client.get(f"{REPORTS}/{filled['id']}")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_refund_closes_report_and_returns_quota(auth_client, filled, db_session,
                                                      test_user, enforce_on):
    """Возврат заказа: портфель обратно в 'filled', отчёт закрыт.

    Снимок расчёта при этом не удаляется — без явной проверки статуса отчёт
    продолжал бы собираться из него и после возврата денег.
    """
    from app.routers.payments import revoke_order_access

    order = await _paid_order(db_session, test_user, "m3")
    assert (await auth_client.post(f"{M3}/portfolios/{filled['id']}/calculate")).status_code == 200
    assert (await auth_client.get(f"{REPORTS}/{filled['id']}")).status_code == 200

    order.status = "refunded"
    revoked = await revoke_order_access(db_session, order)
    await db_session.flush()
    assert revoked["portfolios"] == 1

    row = await _portfolio_row(db_session, filled["id"])
    assert row.status == "filled"
    assert (await auth_client.get(f"{REPORTS}/{filled['id']}")).status_code == 403


# ── Заказ ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_payment_rejects_assessment_for_m3(auth_client, monkeypatch):
    """Заказ Метода 3 не может ссылаться на ассессмент: цены разные,
    перепутанная привязка развела бы два баланса."""
    import app.routers.payments as payments_router
    monkeypatch.setattr(payments_router, "is_payment_enabled", lambda product="m12": True)

    r = await auth_client.post(
        "/api/payments/create?product=m3&assessment_id=00000000-0000-0000-0000-000000000001")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_payment_rejects_unknown_product(auth_client):
    r = await auth_client.post("/api/payments/create?product=m99")
    assert r.status_code == 400
