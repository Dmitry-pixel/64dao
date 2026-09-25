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


def test_context_is_built_and_verifies(monkeypatch, tmp_path):
    """Рядом с путём живёт готовый SSLContext — его и получает httpx.

    Проверка сильнее прежней «verify не False»: контекст обязан требовать
    сертификат и сверять имя хоста. Отключить одно из двух — значит молча
    снять защиту, оставив verify внешне заполненным.
    """
    import ssl

    bundle = tmp_path / "bundle.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n")
    ctx = _reload_client(monkeypatch, str(bundle)).TOCHKA_SSL_CONTEXT
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode is ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_broken_bundle_does_not_crash_import(monkeypatch, tmp_path):
    """Битый бандл не роняет приложение на старте.

    tests/test_tochka_tls.py уже кладёт неполный PEM в
    test_existing_bundle_is_used: create_default_context на таком файле
    бросает исключение, и без отката импорт модуля упал бы.
    """
    import ssl

    bundle = tmp_path / "broken.pem"
    bundle.write_text("не сертификат вовсе")
    mod = _reload_client(monkeypatch, str(bundle))
    assert isinstance(mod.TOCHKA_SSL_CONTEXT, ssl.SSLContext)
    assert mod.TOCHKA_SSL_VERIFY is not False
