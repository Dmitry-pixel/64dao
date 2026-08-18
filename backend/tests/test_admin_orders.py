"""GET /api/payments/admin/orders — список заказов для кнопки возврата в админке.

Ключевое поле — can_refund: фронт рисует кнопку по нему, и его условия
обязаны совпадать с проверками refund_order. Разъедутся — админка начнёт
предлагать возврат, который бэкенд отклонит с 400.
"""
import uuid

import pytest

from app.models import Order


async def _order(db_session, user, **overrides) -> Order:
    data = {
        "user_id": user.id,
        "product": "m12",
        "amount": 14900,
        "currency": "RUB",
        "status": "paid",
        "tochka_operation_id": str(uuid.uuid4()),
    }
    data.update(overrides)
    order = Order(**data)
    db_session.add(order)
    await db_session.commit()
    return order


@pytest.mark.asyncio
async def test_requires_admin(auth_client, db_session, test_user):
    await _order(db_session, test_user)
    resp = await auth_client.get("/api/payments/admin/orders")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_returns_orders_with_buyer_email(admin_client, db_session, test_user):
    await _order(db_session, test_user)
    resp = await admin_client.get("/api/payments/admin/orders")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    item = body["items"][0]
    # Email покупателя — единственное, по чему админ опознаёт заказ:
    # id заказа он в глаза не видел.
    assert item["user_email"] == test_user.email
    assert item["can_refund"] is True


@pytest.mark.asyncio
async def test_can_refund_false_without_operation_id(admin_client, db_session, test_user):
    """Оплачен, но операции в Точке нет — возврату не подлежит.

    Так выглядят заказы, проставленные вручную или пришедшие до подключения
    эквайринга. refund_order на них отвечает 400.
    """
    await _order(db_session, test_user, tochka_operation_id=None)
    resp = await admin_client.get("/api/payments/admin/orders")
    item = next(i for i in resp.json()["items"] if i["tochka_operation_id"] is None)
    assert item["can_refund"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "failed", "refunded"])
async def test_can_refund_false_for_non_paid(admin_client, db_session, test_user, status):
    await _order(db_session, test_user, status=status)
    resp = await admin_client.get("/api/payments/admin/orders")
    item = next(i for i in resp.json()["items"] if i["status"] == status)
    assert item["can_refund"] is False


@pytest.mark.asyncio
async def test_status_filter(admin_client, db_session, test_user):
    await _order(db_session, test_user, status="paid")
    await _order(db_session, test_user, status="refunded")
    resp = await admin_client.get("/api/payments/admin/orders?status=refunded")
    items = resp.json()["items"]
    assert items
    assert all(i["status"] == "refunded" for i in items)


@pytest.mark.asyncio
async def test_search_by_email(admin_client, db_session, test_user):
    await _order(db_session, test_user)
    fragment = test_user.email.split("@")[0]
    resp = await admin_client.get(f"/api/payments/admin/orders?q={fragment}")
    assert resp.json()["total"] >= 1

    resp = await admin_client.get("/api/payments/admin/orders?q=нет-такого-адреса")
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_pagination_reports_full_total(admin_client, db_session, test_user):
    """total считается по всей выборке, а не по странице.

    Иначе «Показано N из M» врёт и админ решит, что заказов больше нет.
    """
    for _ in range(3):
        await _order(db_session, test_user)
    resp = await admin_client.get("/api/payments/admin/orders?limit=1&offset=0")
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["total"] >= 3
