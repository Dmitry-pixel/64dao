"""Переключатель обязательной оплаты: хранилище и админские эндпоинты."""
import pytest

import app.credits_settings as store


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    """Пишем во временный файл: тесты идут в том же контейнере, что и прод,
    и делят volume uploads — настоящий credits_settings.json трогать нельзя."""
    monkeypatch.setattr(store, "CREDITS_SETTINGS_FILE",
                        tmp_path / "credits_settings.json")
    return tmp_path


def test_falls_back_to_env_when_file_absent(tmp_store):
    view = store.read_credits_settings()
    assert view["source"] == "env"
    assert isinstance(view["enforce_credits"], bool)


def test_set_and_read(tmp_store):
    assert store.set_enforce_credits(True)["enforce_credits"] is True
    view = store.read_credits_settings()
    assert view["enforce_credits"] is True
    assert view["source"] == "admin"
    assert store.enforce_credits_enabled() is True

    store.set_enforce_credits(False)
    assert store.enforce_credits_enabled() is False
    assert store.read_credits_settings()["source"] == "admin"


@pytest.mark.asyncio
async def test_endpoint_requires_admin(auth_client, tmp_store):
    resp = await auth_client.get("/api/payments/admin/credits-settings")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_endpoint_toggles(admin_client, tmp_store):
    resp = await admin_client.put("/api/payments/admin/credits-settings",
                                  params={"enforce_credits": "true"})
    assert resp.status_code == 200
    assert resp.json()["enforce_credits"] is True
    assert resp.json()["source"] == "admin"

    resp = await admin_client.get("/api/payments/admin/credits-settings")
    assert resp.json()["enforce_credits"] is True

    resp = await admin_client.put("/api/payments/admin/credits-settings",
                                  params={"enforce_credits": "false"})
    assert resp.json()["enforce_credits"] is False
