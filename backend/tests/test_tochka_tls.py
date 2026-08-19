"""Проверка выбора CA-бандла для вызовов к Точке.

Молча откатиться на дефолтное хранилище допустимо — приложение не должно
падать при старте. Недопустимо verify=False: JWT банка уходит в заголовке
Authorization, соединение без проверки цепочки = риск утечки токена.
"""
import importlib
import os

import pytest


def _reload_client(monkeypatch, bundle_value: str):
    """Перечитывает модуль с подменённым TOCHKA_CA_BUNDLE.

    TOCHKA_SSL_VERIFY вычисляется на импорте, поэтому монипатчить настройку
    после импорта бесполезно — нужен reload.
    """
    import app.config as config

    config.get_settings.cache_clear()
    monkeypatch.setenv("TOCHKA_CA_BUNDLE", bundle_value)

    import app.tochka_client as tochka_client

    return importlib.reload(tochka_client)


@pytest.fixture(autouse=True)
def _restore_module_state():
    """Возвращает модуль к боевому состоянию: reload протекает на другие тесты."""
    yield
    import app.config as config
    import app.tochka_client as tochka_client

    os.environ.pop("TOCHKA_CA_BUNDLE", None)
    config.get_settings.cache_clear()
    importlib.reload(tochka_client)


def test_missing_bundle_falls_back_to_default_store(monkeypatch):
    assert _reload_client(monkeypatch, "/nonexistent/ca-bundle.pem").TOCHKA_SSL_VERIFY is True


def test_empty_bundle_falls_back_to_default_store(monkeypatch):
    assert _reload_client(monkeypatch, "").TOCHKA_SSL_VERIFY is True


def test_existing_bundle_is_used(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n")
    assert str(bundle) == _reload_client(monkeypatch, str(bundle)).TOCHKA_SSL_VERIFY


@pytest.mark.parametrize("value", ["", "/nonexistent.pem", "/etc/hosts"])
def test_verify_is_never_disabled(monkeypatch, value):
    assert _reload_client(monkeypatch, value).TOCHKA_SSL_VERIFY is not False
