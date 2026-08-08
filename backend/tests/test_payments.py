"""
test_payments.py — smoke-тесты платёжного роутера (routers/payments.py).

Внешний API Точки НЕ вызывается: get_tochka_client подменяется моком
(fixture mock_tochka), поэтому тесты детерминированы и не ходят в сеть.
Так же подменяются pricing-хелперы (is_payment_enabled/current_price),
чтобы не зависеть от pricing.json в volume.
"""
import uuid
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

import app.routers.payments as payments_router
from app.models import Assessment, Order


@pytest.fixture
def mock_tochka(monkeypatch):
    tochka = AsyncMock()
    tochka.create_payment_with_receipt = AsyncMock(return_value={
        "Data": {"operationId": "op-test-123", "paymentLink": "https://pay.tochka.test/abc"}
    })
    # Реальный формат ответа банка — Data.Operation[] (список операций),
    # а не Data напрямую. Старая заглушка скрывала баг разбора.
    tochka.get_payment_status = AsyncMock(return_value={
        "Data": {"Operation": [{"status": "APPROVED", "operationId": "op-test-123"}]}
    })
    tochka.refund_payment = AsyncMock(return_value={"Data": {"status": "REFUNDED"}})
    tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": "op-test-123", "status": "APPROVED"}
    )
    monkeypatch.setattr(payments_router, "get_tochka_client", lambda: tochka)
    return tochka


@pytest.fixture
def payment_enabled(monkeypatch):
    # Хелперы принимают продукт: у Метода 3 своя цена и свой флаг оплаты.
    monkeypatch.setattr(payments_router, "is_payment_enabled", lambda product="m12": True)
    monkeypatch.setattr(payments_router, "current_price", lambda product="m12": 14900.0)


async def _make_assessment(db, user, status="completed", combination="AAABAA"):
    a = Assessment(user_id=user.id, method1_combination=combination, status=status, company_name="Test Co")
    db.add(a)
    await db.flush()
    return a


async def _make_order(db, user, assessment, status="pending", operation_id="op-test-123"):
    o = Order(user_id=user.id, product="m12", assessment_id=assessment.id, amount=14900.00,
              currency="RUB", status=status, tochka_operation_id=operation_id)
    db.add(o)
    await db.flush()
    return o


@pytest.mark.asyncio
async def test_create_payment_disabled_returns_503(auth_client, monkeypatch):
    monkeypatch.setattr(payments_router, "is_payment_enabled", lambda product="m12": False)
    resp = await auth_client.post("/api/payments/create", params={"assessment_id": str(uuid.uuid4())})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_create_payment_requires_auth(client, payment_enabled):
    resp = await client.post("/api/payments/create", params={"assessment_id": str(uuid.uuid4())})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_payment_success(auth_client, db_session, test_user, mock_tochka, payment_enabled):
    assessment = await _make_assessment(db_session, test_user)
    resp = await auth_client.post("/api/payments/create", params={"assessment_id": str(assessment.id)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["payment_link"] == "https://pay.tochka.test/abc"
    assert "order_id" in body
    mock_tochka.create_payment_with_receipt.assert_awaited_once()
    order = await db_session.get(Order, uuid.UUID(body["order_id"]))
    assert order is not None
    assert order.status == "pending"
    assert order.tochka_operation_id == "op-test-123"


@pytest.mark.asyncio
async def test_webhook_invalid_signature_ignored(client, mock_tochka):
    mock_tochka.verify_and_decode_webhook = AsyncMock(side_effect=ValueError("bad sig"))
    resp = await client.post("/api/payments/webhook", content=b"garbage")
    assert resp.status_code == 200
    assert resp.json()["reason"] == "invalid signature"


@pytest.mark.asyncio
async def test_webhook_order_not_found_ignored(client, mock_tochka):
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": "op-nonexistent", "status": "APPROVED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["reason"] == "order not found"


@pytest.mark.asyncio
async def test_webhook_approved_marks_order_paid(client, db_session, test_user, mock_tochka):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="pending")
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": order.tochka_operation_id, "status": "APPROVED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    await db_session.refresh(order)
    assert order.status == "paid"
    assert order.paid_at is not None


@pytest.mark.asyncio
async def test_webhook_idempotent_when_already_paid(client, db_session, test_user, mock_tochka):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="paid")
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": order.tochka_operation_id, "status": "APPROVED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_status_returns_order_status(auth_client, db_session, test_user):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="paid")
    resp = await auth_client.get(f"/api/payments/{order.id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_status_only_owner(auth_client, db_session, test_admin):
    assessment = await _make_assessment(db_session, test_admin)
    order = await _make_order(db_session, test_admin, assessment, status="paid")
    resp = await auth_client.get(f"/api/payments/{order.id}/status")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_refund_requires_admin(auth_client, db_session, test_user):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="paid")
    resp = await auth_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refund_non_paid_returns_400(admin_client, db_session, test_admin, mock_tochka):
    assessment = await _make_assessment(db_session, test_admin)
    order = await _make_order(db_session, test_admin, assessment, status="pending")
    resp = await admin_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_refund_success_resets_assessment(admin_client, db_session, test_admin, mock_tochka):
    assessment = await _make_assessment(db_session, test_admin, status="completed")
    order = await _make_order(db_session, test_admin, assessment, status="paid")
    resp = await admin_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"
    mock_tochka.refund_payment.assert_awaited_once()
    await db_session.refresh(order)
    await db_session.refresh(assessment)
    assert order.status == "refunded"
    assert assessment.status == "draft"


@pytest.mark.asyncio
async def test_credits_reflects_paid_orders(auth_client, db_session, test_user):
    assessment = await _make_assessment(db_session, test_user, status="draft")
    await _make_order(db_session, test_user, assessment, status="paid")
    resp = await auth_client.get("/api/payments/credits")
    assert resp.status_code == 200
    assert resp.json()["credits"] == payments_router.REPORTS_PER_ORDER


@pytest.mark.asyncio
async def test_orders_list_loads_reports_eagerly(auth_client, db_session, test_user):
    """Регресс: /api/payments/orders читал assessment.reports без selectinload
    и падал 500 (greenlet_spawn ... await_only) на первом же заказе с готовым
    отчётом — то есть у любого, кто уже оплатил."""
    from app.models import Report

    a = await _make_assessment(db_session, test_user, status="paid")
    db_session.add(Report(assessment_id=a.id, user_id=test_user.id,
                          pdf_path="/tmp/x.pdf", pdf_filename="x.pdf"))
    await db_session.flush()
    await _make_order(db_session, test_user, a, status="paid")

    resp = await auth_client.get("/api/payments/orders")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["assessment"]["reports"], "отчёты должны приезжать в ответе"


@pytest.mark.asyncio
async def test_refund_passes_order_amount(admin_client, db_session, test_admin, mock_tochka):
    """Регресс: refund_payment вызывался без amount, клиент отправлял пустое
    тело, и Точка отвечала 400 «Field Data : Field required» — возврат не
    работал вообще (воспроизведено на боевом)."""
    a = await _make_assessment(db_session, test_admin, status="completed")
    order = await _make_order(db_session, test_admin, a, status="paid")
    resp = await admin_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 200
    args, kwargs = mock_tochka.refund_payment.await_args
    passed = kwargs.get('amount', args[1] if len(args) > 1 else None)
    assert passed == float(order.amount)


async def _make_company(db, user, name="Test Co"):
    from app.models import Company
    c = Company(user_id=user.id, name=name)
    db.add(c)
    await db.flush()
    return c


@pytest.mark.asyncio
async def test_refund_revokes_whole_purchase(admin_client, db_session, test_admin, mock_tochka):
    """Оплата покупает диагностику целиком: Метод 1, Метод 2 и повторный
    Метод 1. Регресс: возврат закрывал только ту запись, из которой создан
    платёж. Метод 2 и повтор оставались в 'completed'."""
    company = await _make_company(db_session, test_admin)

    m1 = Assessment(user_id=test_admin.id, company_id=company.id, method="method1",
                    method1_combination="AAABAA", company_name=company.name,
                    status="completed", followup_allowed=1, followup_used=1)
    db_session.add(m1)
    await db_session.flush()

    m2 = Assessment(user_id=test_admin.id, company_id=company.id, method="method2",
                    method2_data={"x": 1}, company_name=company.name, status="completed")
    followup = Assessment(user_id=test_admin.id, company_id=company.id, method="method1",
                          method1_combination="AAABAB", company_name=company.name,
                          status="completed", is_followup=True,
                          parent_assessment_id=m1.id)
    db_session.add_all([m2, followup])
    await db_session.flush()

    order = await _make_order(db_session, test_admin, m1, status="paid")
    # Привязка к заказу — то, по чему теперь проходит граница отзыва.
    m1.order_id = order.id
    m2.order_id = order.id
    await db_session.flush()

    resp = await admin_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 200
    assert resp.json()["revoked_assessments"] == 3

    for row in (m1, m2, followup):
        await db_session.refresh(row)
        assert row.status == "draft"
    assert m1.followup_allowed == 0
    assert m1.followup_used == 0


@pytest.mark.asyncio
async def test_refund_ignores_grant_paid_assessment(admin_client, db_session, test_admin, mock_tochka):
    """Диагностику, выданную грантом, возврат денег не касается."""
    from datetime import timedelta
    from app.models import AccessGrant

    company = await _make_company(db_session, test_admin, name="Grant Co")
    grant = AccessGrant(user_id=test_admin.id, quota=1,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=30))
    db_session.add(grant)
    await db_session.flush()

    paid = Assessment(user_id=test_admin.id, company_id=company.id, method="method1",
                      method1_combination="AAABAA", company_name=company.name,
                      status="completed")
    granted = Assessment(user_id=test_admin.id, company_id=company.id, method="method1",
                         method1_combination="BBBABA", company_name=company.name,
                         status="completed", grant_id=grant.id)
    db_session.add_all([paid, granted])
    await db_session.flush()

    order = await _make_order(db_session, test_admin, paid, status="paid")
    resp = await admin_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 200
    assert resp.json()["revoked_assessments"] == 1

    await db_session.refresh(granted)
    assert granted.status == "completed"


@pytest.mark.asyncio
async def test_webhook_refund_revokes_access(client, db_session, test_user, mock_tochka):
    """Возврат вне админки (кабинет Точки, диспут) должен отзывать доступ:
    вебхук знал только APPROVED/REJECTED/DECLINED."""
    a = await _make_assessment(db_session, test_user, status="completed")
    order = await _make_order(db_session, test_user, a, status="paid")
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": order.tochka_operation_id, "status": "REFUNDED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"
    assert resp.json()["revoked_assessments"] == 1
    await db_session.refresh(order)
    await db_session.refresh(a)
    assert order.status == "refunded"
    assert a.status == "draft"


@pytest.mark.asyncio
async def test_webhook_refund_flag_without_status(client, db_session, test_user, mock_tochka):
    """Точка помечает возврат флагом isRefund; имя статуса не зафиксировано."""
    a = await _make_assessment(db_session, test_user, status="completed")
    order = await _make_order(db_session, test_user, a, status="paid")
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": order.tochka_operation_id,
                      "status": "APPROVED", "isRefund": True}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"
    await db_session.refresh(order)
    assert order.status == "refunded"


@pytest.mark.asyncio
async def test_webhook_approved_does_not_resurrect_refunded_order(
    client, db_session, test_user, mock_tochka
):
    """Регресс: ретрай APPROVED по возвращённой операции возвращал 'paid'
    вместе с REPORTS_PER_ORDER кредитов."""
    a = await _make_assessment(db_session, test_user, status="draft")
    order = await _make_order(db_session, test_user, a, status="refunded")
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": order.tochka_operation_id, "status": "APPROVED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["reason"] == "order refunded"
    await db_session.refresh(order)
    assert order.status == "refunded"


@pytest.mark.asyncio
async def test_report_download_blocked_after_refund(
    auth_client, db_session, test_user, monkeypatch
):
    """Регресс: рефанд переводил диагностику в draft, но /api/reports/{id}/
    download отдавал PDF без проверки."""
    import app.routers.assessments as assessments_router
    from app.models import Report

    monkeypatch.setattr(assessments_router, "enforce_credits_enabled", lambda: True)
    a = await _make_assessment(db_session, test_user, status="draft")
    report = Report(assessment_id=a.id, user_id=test_user.id,
                    pdf_path="/tmp/x.pdf", pdf_filename="x.pdf")
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_followup_does_not_consume_paid_credit(auth_client, db_session, test_user):
    """Регресс: повтор входит в стоимость основной диагностики, но
    списывался как отдельный кредит — на заказ приходилось 2 прогона из
    трёх обещанных."""
    primary = await _make_assessment(db_session, test_user, status="completed")
    primary.followup_allowed = 1
    primary.followup_used = 1
    followup = Assessment(user_id=test_user.id, method1_combination="AAABAB",
                          company_name="Test Co", status="completed",
                          is_followup=True, parent_assessment_id=primary.id)
    db_session.add(followup)
    await db_session.flush()
    order = await _make_order(db_session, test_user, primary, status="paid")
    primary.order_id = order.id
    await db_session.flush()

    resp = await auth_client.get("/api/payments/credits")
    assert resp.status_code == 200
    assert resp.json()["paid_credits"] == 1


@pytest.mark.asyncio
async def test_method2_consumes_paid_credit(auth_client, db_session, test_user):
    """Метод 2 кредит тратит: фильтр по is_followup не должен исключить всё."""
    m1 = await _make_assessment(db_session, test_user, status="completed")
    m2 = Assessment(user_id=test_user.id, method="method2", method2_data={"x": 1},
                    company_name="Test Co", status="completed")
    db_session.add(m2)
    await db_session.flush()
    order = await _make_order(db_session, test_user, m1, status="paid")
    m1.order_id = order.id
    m2.order_id = order.id
    await db_session.flush()

    resp = await auth_client.get("/api/payments/credits")
    assert resp.json()["paid_credits"] == 0

@pytest.mark.asyncio
async def test_status_polling_marks_pending_order_paid(auth_client, db_session, test_user, mock_tochka):
    """Регресс: get_order_status читал resp['Data']['status'], а банк отдаёт
    Data.Operation[] — remote_status всегда None. Запасной путь «вебхук не
    дошёл, спросим банк» не работал, заказ навсегда оставался pending."""
    a = await _make_assessment(db_session, test_user, status="draft")
    order = await _make_order(db_session, test_user, a, status="pending")

    resp = await auth_client.get(f"/api/payments/{order.id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"
    await db_session.refresh(order)
    assert order.status == "paid"
    assert order.paid_at is not None


@pytest.mark.asyncio
async def test_status_polling_detects_refund(auth_client, db_session, test_user, mock_tochka):
    """Вебхука о возврате у Точки нет — возврат из кабинета банка виден
    только опросом Get Payment Operation Info."""
    a = await _make_assessment(db_session, test_user, status="completed")
    order = await _make_order(db_session, test_user, a, status="paid")
    mock_tochka.get_payment_status = AsyncMock(
        return_value={"Data": {"Operation": [{"status": "REFUNDED"}]}})

    resp = await auth_client.get(f"/api/payments/{order.id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"
    await db_session.refresh(order)
    await db_session.refresh(a)
    assert order.status == "refunded"
    assert a.status == "draft"


@pytest.mark.asyncio
async def test_admin_reconcile_marks_refunded(admin_client, db_session, test_admin, mock_tochka):
    """Массовая сверка: администратор видит возвраты, о которых банк не
    уведомляет."""
    a = await _make_assessment(db_session, test_admin, status="completed")
    order = await _make_order(db_session, test_admin, a, status="paid")
    mock_tochka.get_payment_status = AsyncMock(
        return_value={"Data": {"Operation": [{"status": "REFUNDED"}]}})

    resp = await admin_client.post("/api/payments/admin/reconcile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["marked_refunded"] == 1
    assert body["errors"] == 0
    await db_session.refresh(order)
    await db_session.refresh(a)
    assert order.status == "refunded"
    assert a.status == "draft"


@pytest.mark.asyncio
async def test_paid_credits_ignores_unlinked_assessments(auth_client, db_session, test_user):
    """Диагностики бесплатного периода (order_id IS NULL) не съедают
    оплаченные кредиты. Раньше расход считался глобально, и покупатель
    получал меньше, чем оплатил."""
    await _make_assessment(db_session, test_user, status="completed")
    a = await _make_assessment(db_session, test_user, status="draft")
    await _make_order(db_session, test_user, a, status="paid")

    resp = await auth_client.get("/api/payments/credits")
    assert resp.status_code == 200
    assert resp.json()["paid_credits"] == payments_router.REPORTS_PER_ORDER


@pytest.mark.asyncio
async def test_refund_revokes_only_its_own_order(admin_client, db_session, test_admin, mock_tochka):
    """Два платных заказа на одну компанию: возврат первого не должен
    закрывать диагностику, оплаченную вторым. Раньше границей отзыва была
    компания, и возврат бил по чужой оплате."""
    company = await _make_company(db_session, test_admin, name="Two Orders Co")
    first = Assessment(user_id=test_admin.id, company_id=company.id, method="method1",
                       method1_combination="AAABAA", company_name=company.name,
                       status="completed")
    second = Assessment(user_id=test_admin.id, company_id=company.id, method="method1",
                        method1_combination="BBBABA", company_name=company.name,
                        status="completed")
    db_session.add_all([first, second])
    await db_session.flush()

    o1 = await _make_order(db_session, test_admin, first, status="paid")
    o2 = await _make_order(db_session, test_admin, second, status="paid",
                           operation_id="op-test-456")
    first.order_id = o1.id
    second.order_id = o2.id
    await db_session.flush()

    resp = await admin_client.post(f"/api/payments/{o1.id}/refund")
    assert resp.status_code == 200
    assert resp.json()["revoked_assessments"] == 1

    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.status == "draft"
    assert second.status == "completed"


# ── Удаление не возвращает кредит ─────────────────────────────────────────────
# Расход считается по факту существования записи. Пока удаление стирало
# строку, оплаченный прогон возвращался в баланс, и при включённой
# обязательной оплате диагностику можно было проходить заново без конца.

@pytest.mark.asyncio
async def test_deleting_assessment_does_not_return_credit(auth_client, db_session, test_user):
    a = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, a, status="paid")
    a.order_id = order.id
    await db_session.flush()

    before = (await auth_client.get("/api/payments/credits")).json()["paid_credits"]

    resp = await auth_client.delete(f"/api/assessments/{a.id}")
    assert resp.status_code == 204, resp.text

    after = (await auth_client.get("/api/payments/credits")).json()["paid_credits"]
    assert after == before, "удаление не должно возвращать оплаченный прогон"


@pytest.mark.asyncio
async def test_deleted_assessment_disappears_from_list(auth_client, db_session, test_user):
    a = await _make_assessment(db_session, test_user)

    await auth_client.delete(f"/api/assessments/{a.id}")

    listed = (await auth_client.get("/api/assessments")).json()
    assert [x["id"] for x in listed] == []
    assert (await auth_client.get(f"/api/assessments/{a.id}")).status_code == 404


@pytest.mark.asyncio
async def test_refund_returns_credit_even_after_deletion(auth_client, db_session, test_user):
    """Возврат денег кредит возвращает: там меняется статус диагностики, а не
    факт её существования. Это обещание пользователю, а не дыра."""
    from app.routers.payments import revoke_order_access

    a = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, a, status="paid")
    a.order_id = order.id
    await db_session.flush()
    await db_session.refresh(order, ["assessment"])

    await auth_client.delete(f"/api/assessments/{a.id}")
    assert (await auth_client.get("/api/payments/credits")).json()["paid_credits"] == 1

    order.status = "refunded"
    await revoke_order_access(db_session, order)
    await db_session.flush()

    assert a.status == "draft"
    assert (await auth_client.get("/api/payments/credits")).json()["paid_credits"] == 0


# ── Тестовый платёж на 1 ₽ ────────────────────────────────────────────────────
# Раньше эндпоинт был захардкожен на product="m12", и платёжный путь Метода 3
# не проверялся живьём ни разу. Тестов на него не было вовсе.
@pytest.mark.asyncio
async def test_test_create_requires_admin(auth_client):
    r = await auth_client.post("/api/payments/test-create?product=m3")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_test_create_rejects_unknown_product(admin_client):
    r = await admin_client.post("/api/payments/test-create?product=m99")
    assert r.status_code == 400
    assert "m99" in r.json()["detail"]


@pytest.mark.asyncio
async def test_test_create_makes_m3_order_without_assessment(
    admin_client, db_session, mock_tochka,
):
    """
    Заказ Метода 3 не привязывается к диагностике: обратной ссылки нет
    по построению, а служебная запись Assessment заводилась только из-за
    NOT NULL, которого больше нет.
    """
    r = await admin_client.post("/api/payments/test-create?product=m3")
    assert r.status_code == 200, r.text

    order = await db_session.get(Order, uuid.UUID(r.json()["order_id"]))
    assert order.product == "m3"
    assert order.assessment_id is None
    assert float(order.amount) == 1.00


@pytest.mark.asyncio
async def test_test_create_works_when_payment_disabled(
    admin_client, db_session, mock_tochka, monkeypatch,
):
    """Проверять шлюз нужно и при выключенном приёме платежей."""
    monkeypatch.setattr(payments_router, "is_payment_enabled",
                        lambda product="m12": False)
    r = await admin_client.post("/api/payments/test-create?product=m3")
    assert r.status_code == 200, r.text
