# -*- coding: utf-8 -*-
"""
Метод 3 — название компании в отчёте.

До миграции 024 колонки не было, и company_name_for попадал во второе звено
цепочки: заголовок отчёта показывал название портфеля вместо названия
компании. Проверяется, что название доезжает от формы до заголовка и что у
портфелей без него запасная цепочка работает по-прежнему.
"""
import pytest

from app.m3_models import M3Portfolio
from app.m3_report_api import company_name_for
from app.models import User
from tests.test_m3_api import M3, m3_on, seeded  # noqa: F401


@pytest.mark.asyncio
async def test_company_name_saved_and_returned(auth_client, m3_on):
    r = await auth_client.post(f"{M3}/portfolios", json={
        "title": "Косметика", "company_name": "ООО «Ромашка»", "industry_id": 2})
    assert r.status_code == 201, r.text
    assert r.json()["company_name"] == "ООО «Ромашка»"

    got = await auth_client.get(f"{M3}/portfolios/{r.json()['id']}")
    assert got.json()["company_name"] == "ООО «Ромашка»"


@pytest.mark.asyncio
async def test_portfolio_without_company_name_is_allowed(auth_client, m3_on):
    """Поле необязательно: портфель можно создать и из раздела /m3 напрямую."""
    r = await auth_client.post(f"{M3}/portfolios", json={"title": "Без компании"})
    assert r.status_code == 201, r.text
    assert r.json()["company_name"] is None


def test_company_name_for_prefers_portfolio_field():
    p = M3Portfolio(title="Портфель 2026", company_name="ООО «Ромашка»")
    u = User(email="a@b.c", company_name="Профиль ООО")
    assert company_name_for(p, u) == "ООО «Ромашка»"


def test_company_name_for_falls_back_for_legacy_portfolios():
    """У портфелей, созданных до миграции 024, названия компании нет —
    заголовок выданного ранее отчёта не должен превратиться в «Компания»."""
    p = M3Portfolio(title="Портфель 2026", company_name=None)
    u = User(email="a@b.c", company_name="Профиль ООО")
    assert company_name_for(p, u) == "Портфель 2026"

    empty = M3Portfolio(title=None, company_name=None)
    assert company_name_for(empty, u) == "Профиль ООО"
    assert company_name_for(empty, User(email="a@b.c")) == "Компания"
