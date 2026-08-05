"""
test_admin.py — regression-тесты роутера /api/admin.

КРИТИЧНО: 4 эндпоинта (pricing, email-templates, documents, strategy image)
читают/пишут РЕАЛЬНЫЕ файлы на диске по захардкоженным продовым путям
(/var/www/64dao/uploads/...), а не через настройки, которые можно
переопределить per-environment. Все фикстуры здесь подменяют
module-level переменные путей (PRICING_FILE, TEMPLATES_FILE, DOCS_DIR)
через monkeypatch на время теста — это единственный способ изолировать
тесты от продовых файлов без риска затереть реальную цену, реальные
письма или реальные юридические документы.
"""
import json
import uuid

import pytest
from sqlalchemy import select

from app.models import User, Assessment, Report, Strategy, Order


VALID_COMBINATION = "AABABA"
OTHER_COMBINATION = "BBABAB"


def strategy_payload(**overrides) -> dict:
    payload = {
        "combination": VALID_COMBINATION,
        "title": "Тестовая стратегия",
    }
    payload.update(overrides)
    return payload


# ── Stats ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_stats_admin_succeeds(admin_client, db_session, test_user):
    resp = await admin_client.get("/api/admin/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_users" in body
    assert "orders_by_day" in body
    assert len(body["orders_by_day"]) == 30


@pytest.mark.asyncio
async def test_get_stats_regular_user_forbidden(auth_client):
    resp = await auth_client.get("/api/admin/stats")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_stats_without_auth_401(client):
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 401


# ── Users ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_admin_succeeds(admin_client, test_user, test_admin):
    resp = await admin_client.get("/api/admin/users")
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert test_user.email in emails
    assert test_admin.email in emails


@pytest.mark.asyncio
async def test_list_users_regular_user_forbidden(auth_client):
    resp = await auth_client.get("/api/admin/users")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_set_user_role_succeeds(admin_client, db_session, test_user):
    resp = await admin_client.patch(f"/api/admin/users/{test_user.id}/role", json={"role": "admin"})
    assert resp.status_code == 200

    updated = await db_session.scalar(select(User).where(User.id == test_user.id))
    assert updated.role == "admin"


@pytest.mark.asyncio
async def test_set_user_role_invalid_role_rejected(admin_client, test_user):
    resp = await admin_client.patch(f"/api/admin/users/{test_user.id}/role", json={"role": "superadmin"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_set_user_role_cannot_change_own_role(admin_client, test_admin):
    resp = await admin_client.patch(f"/api/admin/users/{test_admin.id}/role", json={"role": "user"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_set_user_role_not_found_404(admin_client):
    resp = await admin_client.patch(f"/api/admin/users/{uuid.uuid4()}/role", json={"role": "admin"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_succeeds(admin_client, db_session, test_user):
    user_id = test_user.id
    resp = await admin_client.delete(f"/api/admin/users/{user_id}")
    assert resp.status_code == 200

    gone = await db_session.scalar(select(User).where(User.id == user_id))
    assert gone is None


@pytest.mark.asyncio
async def test_delete_user_cannot_delete_self(admin_client, test_admin):
    resp = await admin_client.delete(f"/api/admin/users/{test_admin.id}")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_user_not_found_404(admin_client):
    resp = await admin_client.delete(f"/api/admin/users/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Strategies CRUD (by id) ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_strategy_succeeds(admin_client, db_session):
    resp = await admin_client.post("/api/admin/strategies", json=strategy_payload())
    assert resp.status_code == 201
    assert resp.json()["combination"] == VALID_COMBINATION

    saved = await db_session.scalar(select(Strategy).where(Strategy.combination == VALID_COMBINATION))
    assert saved is not None


@pytest.mark.asyncio
async def test_create_strategy_duplicate_combination_409(admin_client, db_session):
    db_session.add(Strategy(combination=VALID_COMBINATION, title="Существующая"))
    await db_session.flush()

    resp = await admin_client.post("/api/admin/strategies", json=strategy_payload())
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_strategy_regular_user_forbidden(auth_client):
    resp = await auth_client.post("/api/admin/strategies", json=strategy_payload())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_strategies_admin_succeeds(admin_client, db_session):
    db_session.add(Strategy(combination=VALID_COMBINATION, title="Тест"))
    await db_session.flush()

    resp = await admin_client.get("/api/admin/strategies")
    assert resp.status_code == 200
    combos = {s["combination"] for s in resp.json()}
    assert VALID_COMBINATION in combos


@pytest.mark.asyncio
async def test_get_strategy_by_id_succeeds(admin_client, db_session):
    s = Strategy(combination=VALID_COMBINATION, title="Тест")
    db_session.add(s)
    await db_session.flush()

    resp = await admin_client.get(f"/api/admin/strategies/{s.id}")
    assert resp.status_code == 200
    assert resp.json()["combination"] == VALID_COMBINATION


@pytest.mark.asyncio
async def test_get_strategy_by_id_not_found_404(admin_client):
    resp = await admin_client.get(f"/api/admin/strategies/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_strategy_by_id_succeeds(admin_client, db_session):
    s = Strategy(combination=VALID_COMBINATION, title="Старое")
    db_session.add(s)
    await db_session.flush()

    resp = await admin_client.put(f"/api/admin/strategies/{s.id}", json={"title": "Новое"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Новое"


@pytest.mark.asyncio
async def test_update_strategy_by_id_not_found_404(admin_client):
    resp = await admin_client.put(f"/api/admin/strategies/{uuid.uuid4()}", json={"title": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_strategy_succeeds(admin_client, db_session):
    s = Strategy(combination=VALID_COMBINATION, title="К удалению")
    db_session.add(s)
    await db_session.flush()
    strategy_id = s.id

    resp = await admin_client.delete(f"/api/admin/strategies/{strategy_id}")
    assert resp.status_code == 200

    gone = await db_session.scalar(select(Strategy).where(Strategy.id == strategy_id))
    assert gone is None


@pytest.mark.asyncio
async def test_delete_strategy_not_found_404(admin_client):
    resp = await admin_client.delete(f"/api/admin/strategies/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Strategies CRUD (by combo) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_strategy_by_combo_succeeds(admin_client, db_session):
    s = Strategy(combination=VALID_COMBINATION, title="По комбинации")
    db_session.add(s)
    await db_session.flush()

    resp = await admin_client.get(f"/api/admin/strategies/combo/{VALID_COMBINATION}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "По комбинации"


@pytest.mark.asyncio
async def test_get_strategy_by_combo_not_found_404(admin_client):
    resp = await admin_client.get(f"/api/admin/strategies/combo/{VALID_COMBINATION}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upsert_strategy_by_combo_creates_new(admin_client, db_session):
    resp = await admin_client.put(
        f"/api/admin/strategies/combo/{VALID_COMBINATION}",
        json={"title": "Новая через combo"},
    )
    assert resp.status_code == 200
    assert resp.json()["combination"] == VALID_COMBINATION

    saved = await db_session.scalar(select(Strategy).where(Strategy.combination == VALID_COMBINATION))
    assert saved is not None


@pytest.mark.asyncio
async def test_upsert_strategy_by_combo_updates_existing(admin_client, db_session):
    existing = Strategy(combination=VALID_COMBINATION, title="Старое")
    db_session.add(existing)
    await db_session.flush()

    resp = await admin_client.put(
        f"/api/admin/strategies/combo/{VALID_COMBINATION}",
        json={"title": "Обновлённое"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Обновлённое"
    assert resp.json()["id"] == str(existing.id)


@pytest.mark.asyncio
async def test_upsert_strategy_by_combo_lifecycle_description_special_case(admin_client, db_session):
    """
    Особая логика в коде: 'if value is not None or field in (lifecycle_description,)'
    означает, что lifecycle_description записывается даже если value явно None
    (затирает существующее значение пустым), в отличие от других полей, где
    None-значения из exclude_unset просто игнорируются.
    """
    existing = Strategy(
        combination=VALID_COMBINATION,
        title="Заголовок",
        lifecycle_description="Старое описание",
    )
    db_session.add(existing)
    await db_session.flush()

    resp = await admin_client.put(
        f"/api/admin/strategies/combo/{VALID_COMBINATION}",
        json={"title": "Заголовок", "lifecycle_description": None},
    )
    assert resp.status_code == 200
    assert resp.json()["lifecycle_description"] is None

# ── Activity log ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_activity_log_includes_registrations(admin_client, test_user):
    resp = await admin_client.get("/api/admin/logs")
    assert resp.status_code == 200
    emails = {e["user_email"] for e in resp.json()}
    assert test_user.email in emails


@pytest.mark.asyncio
async def test_get_activity_log_regular_user_forbidden(auth_client):
    resp = await auth_client.get("/api/admin/logs")
    assert resp.status_code == 403


# ── Reports list (admin) ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_all_assessments_admin_succeeds(admin_client, db_session, test_user):
    a = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(a)
    await db_session.flush()

    resp = await admin_client.get("/api/admin/reports")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert str(a.id) in ids


@pytest.mark.asyncio
async def test_list_all_assessments_regular_user_forbidden(auth_client):
    resp = await auth_client.get("/api/admin/reports")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_start_impersonation_succeeds(admin_client, test_user):
    """
    Проверяем НОВЫЙ токен через resp.cookies (cookie этого конкретного
    ответа), а не через admin_client.cookies (client-level jar). В jar
    клиента ручная установка auth-token (через cookies.set в conftest.py)
    и Set-Cookie от сервера создают записи с разными атрибутами domain,
    что вызывает httpx.CookieConflict при любом обращении к
    client.cookies - известная проблема httpx с ASGITransport, не баг
    кода приложения.
    """
    resp = await admin_client.post(f"/api/admin/impersonate/{test_user.id}")
    assert resp.status_code == 200
    assert "auth-token" in resp.cookies


@pytest.mark.asyncio
async def test_start_impersonation_cannot_impersonate_admin(admin_client, test_admin):
    resp = await admin_client.post(f"/api/admin/impersonate/{test_admin.id}")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_start_impersonation_not_found_404(admin_client):
    resp = await admin_client.post(f"/api/admin/impersonate/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_impersonation_regular_user_forbidden(auth_client, test_user):
    resp = await auth_client.post(f"/api/admin/impersonate/{test_user.id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stop_impersonation_returns_to_admin(admin_client, test_user, test_admin):
    """
    Новый токен (impersonation) извлекается из resp.cookies первого
    запроса и передаётся ЯВНО через headers= на втором запросе - не
    через client-level cookie jar (который конфликтует, см. комментарий
    в test_start_impersonation_succeeds выше).
    """
    start_resp = await admin_client.post(f"/api/admin/impersonate/{test_user.id}")
    assert start_resp.status_code == 200
    impersonation_token = start_resp.cookies["auth-token"]

    stop_resp = await admin_client.post(
        "/api/admin/impersonate/stop",
        headers={"Cookie": f"auth-token={impersonation_token}"},
    )
    assert stop_resp.status_code == 200


@pytest.mark.asyncio
async def test_stop_impersonation_without_active_session_400(admin_client):
    resp = await admin_client.post("/api/admin/impersonate/stop")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_stop_impersonation_without_cookie_401(client):
    resp = await client.post("/api/admin/impersonate/stop")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_impersonation_status_inactive_without_cookie(client):
    resp = await client.get("/api/admin/impersonate/status")
    assert resp.status_code == 200
    assert resp.json()["active"] is False


@pytest.mark.asyncio
async def test_impersonation_status_active_during_impersonation(admin_client, test_user):
    start_resp = await admin_client.post(f"/api/admin/impersonate/{test_user.id}")
    impersonation_token = start_resp.cookies["auth-token"]

    resp = await admin_client.get(
        "/api/admin/impersonate/status",
        headers={"Cookie": f"auth-token={impersonation_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True


# ── Pricing (файл на диске — путь подменён) ──────────────────────────────────

@pytest.fixture
def isolated_pricing_file(monkeypatch, tmp_path):
    import app.pricing_store as pricing_store

    fake_path = tmp_path / "pricing.json"
    monkeypatch.setattr(pricing_store, "PRICING_FILE", fake_path)
    return fake_path


@pytest.mark.asyncio
async def test_get_pricing_returns_defaults_when_file_missing(admin_client, isolated_pricing_file):
    """Два тарифных блока: m12 — Методы 1 и 2, m3 — Метод 3 по своей цене."""
    resp = await admin_client.get("/api/admin/pricing")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"m12", "m3"}
    assert body["m12"]["price"] == 14900
    assert body["m3"]["price"] == 20000


@pytest.mark.asyncio
async def test_update_pricing_writes_to_isolated_file(admin_client, isolated_pricing_file):
    new_pricing = {
        "m12": {"title": "Тест", "price": 9999, "currency": "₽"},
        "m3": {"title": "Тест 3", "price": 21000, "currency": "₽"},
    }
    resp = await admin_client.put("/api/admin/pricing", json=new_pricing)
    assert resp.status_code == 200

    assert isolated_pricing_file.exists()
    saved = json.loads(isolated_pricing_file.read_text(encoding="utf-8"))
    assert saved["m12"]["price"] == 9999
    assert saved["m3"]["price"] == 21000
    # Поля, которых не было в запросе, добираются из дефолтов кода —
    # иначе один неполный PUT из админки обнулил бы условия оплаты.
    assert saved["m12"]["payment_enabled"] is False
    assert saved["m12"]["features"]


@pytest.mark.asyncio
async def test_update_pricing_accepts_legacy_flat_body(admin_client, isolated_pricing_file):
    """Старый плоский формат читается как m12 и не затирает тариф Метода 3.

    Админка обновляется отдельным деплоем: на время рассинхрона фронт может
    прислать прежнее тело запроса.
    """
    resp = await admin_client.put(
        "/api/admin/pricing", json={"title": "Старый формат", "price": 12345, "currency": "₽"})
    assert resp.status_code == 200

    saved = json.loads(isolated_pricing_file.read_text(encoding="utf-8"))
    assert saved["m12"]["price"] == 12345
    assert saved["m3"]["price"] == 20000


@pytest.mark.asyncio
async def test_pricing_regular_user_forbidden(auth_client, isolated_pricing_file):
    resp = await auth_client.get("/api/admin/pricing")
    assert resp.status_code == 403


# ── Email templates (файл на диске — путь подменён) ──────────────────────────

@pytest.fixture
def isolated_templates_file(monkeypatch, tmp_path):
    import app.email_templates_store as store

    fake_path = tmp_path / "email_templates.json"
    monkeypatch.setattr(store, "TEMPLATES_FILE", fake_path)
    return fake_path


@pytest.mark.asyncio
async def test_get_email_templates_returns_defaults_when_file_missing(admin_client, isolated_templates_file):
    resp = await admin_client.get("/api/admin/email-templates")
    assert resp.status_code == 200
    assert "otp" in resp.json()
    assert "welcome" in resp.json()


@pytest.mark.asyncio
async def test_update_email_templates_writes_to_isolated_file(admin_client, isolated_templates_file):
    new_templates = {"otp": {"subject": "Новый код: {code}", "body_html": "<p>{code}</p>"}}
    resp = await admin_client.put("/api/admin/email-templates", json=new_templates)
    assert resp.status_code == 200

    assert isolated_templates_file.exists()
    saved = json.loads(isolated_templates_file.read_text(encoding="utf-8"))
    assert saved["otp"]["subject"] == "Новый код: {code}"


# ── Documents (файлы на диске — путь подменён) ───────────────────────────────

@pytest.fixture
def isolated_docs_dir(monkeypatch, tmp_path):
    import app.routers.admin as admin_router

    fake_dir = tmp_path / "docs"
    monkeypatch.setattr(admin_router, "DOCS_DIR", fake_dir)
    return fake_dir


@pytest.mark.asyncio
async def test_get_document_returns_default_when_missing(admin_client, isolated_docs_dir):
    resp = await admin_client.get("/api/admin/documents/about")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "about"
    assert body["published"] is False


@pytest.mark.asyncio
async def test_get_document_unknown_slug_404(admin_client, isolated_docs_dir):
    resp = await admin_client.get("/api/admin/documents/nonexistent-slug")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_save_document_writes_to_isolated_dir(admin_client, isolated_docs_dir):
    resp = await admin_client.put(
        "/api/admin/documents/about",
        json={"content": "Тестовый контент", "published": True},
    )
    assert resp.status_code == 200

    saved_file = isolated_docs_dir / "about.json"
    assert saved_file.exists()
    saved = json.loads(saved_file.read_text(encoding="utf-8"))
    assert saved["content"] == "Тестовый контент"
    assert saved["published"] is True
    assert saved["slug"] == "about"


@pytest.mark.asyncio
async def test_save_document_unknown_slug_404(admin_client, isolated_docs_dir):
    resp = await admin_client.put(
        "/api/admin/documents/nonexistent-slug",
        json={"content": "X"},
    )
    assert resp.status_code == 404


# ── Setup (создание первого администратора) ──────────────────────────────────

@pytest.mark.asyncio
async def test_admin_setup_without_key_unauthorized(client, db_session):
    resp = await client.post("/api/admin/setup", json={
        "email": "newadmin@example.com",
        "password": "AdminPass123",
        "full_name": "New Admin",
        "setup_key": "",
    })
    assert resp.status_code == 401


# ── User status (activate/deactivate) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_user_status_cannot_change_own_status(admin_client, test_admin):
    resp = await admin_client.patch(
        f"/api/admin/users/{test_admin.id}/status", json={"is_active": False}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_set_user_status_cannot_block_admin(admin_client, db_session):
    from unittest.mock import AsyncMock, patch
    import uuid as _uuid
    from app.models import User as _User
    from app.auth import hash_password as _hp

    other_admin = _User(
        id=_uuid.uuid4(),
        email=f"admin2-{_uuid.uuid4().hex[:8]}@example.com",
        password_hash=_hp("AdminPassword123"),
        full_name="Second Admin",
        role="admin",
    )
    db_session.add(other_admin)
    await db_session.flush()

    with patch("app.email.send_account_status_email", new=AsyncMock()):
        resp = await admin_client.patch(
            f"/api/admin/users/{other_admin.id}/status", json={"is_active": False}
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_set_user_status_toggle_flow(admin_client, db_session, test_user):
    from unittest.mock import AsyncMock, patch

    with patch("app.email.send_account_status_email", new=AsyncMock()) as mock_send:
        resp = await admin_client.patch(
            f"/api/admin/users/{test_user.id}/status", json={"is_active": False}
        )
        assert resp.status_code == 200
        await db_session.refresh(test_user)
        assert test_user.is_active is False

        resp = await admin_client.patch(
            f"/api/admin/users/{test_user.id}/status", json={"is_active": True}
        )
        assert resp.status_code == 200
        await db_session.refresh(test_user)
        assert test_user.is_active is True

        assert mock_send.await_count == 2
