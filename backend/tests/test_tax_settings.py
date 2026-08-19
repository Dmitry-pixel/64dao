# -*- coding: utf-8 -*-
"""
F9: путь tax_settings.json должен резолвиться через UPLOAD_DIR, а не быть жёстко
привязан к боевому тому. Иначе тест, дёрнувший set_vat_enabled, переключил бы
НДС в проде.
"""
import os

from app import tax_settings


def test_path_derived_from_upload_dir():
    # conftest выставляет UPLOAD_DIR на временную папку прогона
    assert os.path.join(
        os.environ["UPLOAD_DIR"], "tax_settings.json"
    ) == tax_settings.TAX_SETTINGS_PATH
    # и это не боевой том
    assert not tax_settings.TAX_SETTINGS_PATH.startswith("/var/www/64dao/uploads")


def test_set_vat_roundtrip_isolated():
    from app.tax_settings import current_vat_type, get_tax_settings, set_vat_enabled
    try:
        set_vat_enabled(True, "vat20")
        assert get_tax_settings()["vat_enabled"] is True
        assert current_vat_type() == "vat20"
    finally:
        set_vat_enabled(False)
    assert current_vat_type() == "none"
