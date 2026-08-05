# -*- coding: utf-8 -*-
"""
Тариф на два продукта: m12 (Методы 1 и 2) и m3 (Метод 3).

Проверяется главное следствие второй цены: цены и флаги оплаты у продуктов
раздельные, а старый плоский формат файла (он лежит на проде) читается как
m12 и не теряется.
"""
import json

import pytest

from app import pricing_store as ps


@pytest.fixture
def pricing_file(monkeypatch, tmp_path):
    path = tmp_path / "pricing.json"
    monkeypatch.setattr(ps, "PRICING_FILE", path)
    return path


def test_defaults_when_file_missing(pricing_file):
    data = ps.read_pricing()
    assert set(data) == {"m12", "m3"}
    assert data["m12"]["price"] == 14900
    assert data["m3"]["price"] == 20000
    assert ps.current_price() == 14900.0
    assert ps.current_price("m3") == 20000.0


def test_legacy_flat_file_read_as_m12(pricing_file):
    """На проде в pricing.json лежит плоский формат — он не должен потеряться."""
    pricing_file.write_text(json.dumps({
        "title": "Полный отчёт 64 ДАО", "price": 14900, "currency": "₽",
        "payment_enabled": True,
    }), encoding="utf-8")

    data = ps.read_pricing()
    assert data["m12"]["price"] == 14900
    assert data["m12"]["payment_enabled"] is True
    # Метод 3 берётся из дефолтов кода, а не из плоского блока.
    assert data["m3"]["price"] == 20000
    assert data["m3"]["payment_enabled"] is False


def test_missing_keys_filled_from_defaults(pricing_file):
    """Ключ, добавленный в код, появляется у всех, а не только у тех, кто
    после этого пересохранил тариф в админке."""
    pricing_file.write_text(json.dumps({"m12": {"price": 100}}), encoding="utf-8")
    data = ps.read_pricing()
    assert data["m12"]["price"] == 100
    assert data["m12"]["currency"] == "₽"
    assert data["m12"]["features"]


def test_prices_are_independent(pricing_file):
    ps.write_pricing({
        "m12": {**ps.DEFAULT_M12, "price": 15900, "payment_enabled": True},
        "m3": {**ps.DEFAULT_M3, "price": 25000, "payment_enabled": False},
    })
    assert ps.current_price("m12") == 15900.0
    assert ps.current_price("m3") == 25000.0
    # Флаги оплаты раздельные и могут расходиться — на это опирается
    # карточка Метода 3 в /assessment.
    assert ps.is_payment_enabled("m12") is True
    assert ps.is_payment_enabled("m3") is False


def test_write_normalises_legacy_body(pricing_file):
    """PUT из админки старого деплоя не должен затирать тариф Метода 3."""
    ps.write_pricing({"title": "Старый формат", "price": 12345, "currency": "₽"})
    saved = json.loads(pricing_file.read_text(encoding="utf-8"))
    assert set(saved) == {"m12", "m3"}
    assert saved["m12"]["price"] == 12345
    assert saved["m3"]["price"] == 20000


def test_unknown_product_falls_back_to_m12(pricing_file):
    assert ps.read_product("m99")["price"] == ps.read_product("m12")["price"]


@pytest.mark.asyncio
async def test_public_endpoint_keeps_flat_m12_and_adds_products(client, pricing_file):
    """Лендинг читает price/title с верхнего уровня — ломать его нельзя."""
    resp = await client.get("/api/pricing")
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 14900
    assert body["title"]
    assert set(body["products"]) == {"m12", "m3"}
    assert body["products"]["m3"]["price"] == 20000
