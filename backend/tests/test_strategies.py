"""
test_strategies.py — regression-тесты роутера /api/strategies.

Покрывает: GET /all (admin only), GET /{combination} (любой
авторизованный, без фильтра is_published), PUT /{combination} (upsert,
admin only, partial update через exclude_unset).
"""
import pytest
from sqlalchemy import select

from app.models import Strategy


VALID_COMBINATION = "AABABA"
OTHER_COMBINATION = "BBABAB"


def strategy_payload(**overrides) -> dict:
    payload = {
        "title": "Тестовая стратегия",
        "stratagema_title": "Тестагема",
        "lifecycle_stage": "Рост",
    }
    payload.update(overrides)
    return payload


# ── GET /all ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_all_strategies_admin_succeeds(admin_client, db_session):
    s = Strategy(combination=VALID_COMBINATION, title="Тест")
    db_session.add(s)
    await db_session.flush()

    resp = await admin_client.get("/api/strategies/all")
    assert resp.status_code == 200
    combos = {item["combination"] for item in resp.json()}
    assert VALID_COMBINATION in combos


@pytest.mark.asyncio
async def test_get_all_strategies_regular_user_forbidden(auth_client):
    resp = await auth_client.get("/api/strategies/all")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_all_strategies_without_auth_401(client):
    resp = await client.get("/api/strategies/all")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_all_strategies_ordered_by_combination(admin_client, db_session):
    db_session.add(Strategy(combination=OTHER_COMBINATION, title="B"))
    db_session.add(Strategy(combination=VALID_COMBINATION, title="A"))
    await db_session.flush()

    resp = await admin_client.get("/api/strategies/all")
    combos = [item["combination"] for item in resp.json()]
    assert combos.index(VALID_COMBINATION) < combos.index(OTHER_COMBINATION)


# ── GET /{combination} ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_strategy_by_combination_found(auth_client, db_session):
    s = Strategy(combination=VALID_COMBINATION, title="Найденная", is_published=True)
    db_session.add(s)
    await db_session.flush()

    resp = await auth_client.get(f"/api/strategies/{VALID_COMBINATION}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Найденная"


@pytest.mark.asyncio
async def test_get_strategy_unpublished_still_visible_to_regular_user(auth_client, db_session):
    """
    Известное расхождение с assessments.py::stream_pdf_on_demand (там
    обычный пользователь видит только is_published=True). Здесь —
    фильтра нет вообще, любой авторизованный видит любую стратегию.
    Тест фиксирует ТЕКУЩЕЕ поведение, не предполагает, что оно корректно.
    """
    s = Strategy(combination=VALID_COMBINATION, title="Черновик", is_published=False)
    db_session.add(s)
    await db_session.flush()

    resp = await auth_client.get(f"/api/strategies/{VALID_COMBINATION}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Черновик"


@pytest.mark.asyncio
async def test_get_strategy_not_found_404(auth_client):
    resp = await auth_client.get(f"/api/strategies/{VALID_COMBINATION}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_strategy_invalid_format_400(auth_client):
    resp = await auth_client.get("/api/strategies/SHORT")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_strategy_invalid_chars_400(auth_client):
    resp = await auth_client.get("/api/strategies/XXXXXX")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_strategy_lowercase_normalized(auth_client, db_session):
    s = Strategy(combination=VALID_COMBINATION, title="Регистр")
    db_session.add(s)
    await db_session.flush()

    resp = await auth_client.get(f"/api/strategies/{VALID_COMBINATION.lower()}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Регистр"


@pytest.mark.asyncio
async def test_get_strategy_without_auth_401(client):
    resp = await client.get(f"/api/strategies/{VALID_COMBINATION}")
    assert resp.status_code == 401


# ── PUT /{combination} (upsert) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_strategy_creates_new(admin_client, db_session):
    resp = await admin_client.put(
        f"/api/strategies/{VALID_COMBINATION}",
        json=strategy_payload(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["combination"] == VALID_COMBINATION
    assert body["title"] == "Тестовая стратегия"

    saved = await db_session.scalar(select(Strategy).where(Strategy.combination == VALID_COMBINATION))
    assert saved is not None


@pytest.mark.asyncio
async def test_upsert_strategy_updates_existing(admin_client, db_session):
    existing = Strategy(combination=VALID_COMBINATION, title="Старое название")
    db_session.add(existing)
    await db_session.flush()

    resp = await admin_client.put(
        f"/api/strategies/{VALID_COMBINATION}",
        json=strategy_payload(title="Новое название"),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Новое название"
    assert resp.json()["id"] == str(existing.id)


@pytest.mark.asyncio
async def test_upsert_strategy_partial_update_preserves_other_fields(admin_client, db_session):
    existing = Strategy(
        combination=VALID_COMBINATION,
        title="Заголовок",
        stratagema_title="Стратагема не должна измениться",
    )
    db_session.add(existing)
    await db_session.flush()

    resp = await admin_client.put(
        f"/api/strategies/{VALID_COMBINATION}",
        json={"title": "Новый заголовок"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Новый заголовок"
    assert resp.json()["stratagema_title"] == "Стратагема не должна измениться"


@pytest.mark.asyncio
async def test_upsert_strategy_regular_user_forbidden(auth_client):
    resp = await auth_client.put(
        f"/api/strategies/{VALID_COMBINATION}",
        json=strategy_payload(),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upsert_strategy_without_auth_401(client):
    resp = await client.put(
        f"/api/strategies/{VALID_COMBINATION}",
        json=strategy_payload(),
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upsert_strategy_invalid_combination_format_400(admin_client):
    resp = await admin_client.put(
        "/api/strategies/SHORT",
        json=strategy_payload(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upsert_strategy_lowercase_normalized(admin_client, db_session):
    resp = await admin_client.put(
        f"/api/strategies/{VALID_COMBINATION.lower()}",
        json=strategy_payload(),
    )
    assert resp.status_code == 200
    assert resp.json()["combination"] == VALID_COMBINATION

    saved = await db_session.scalar(select(Strategy).where(Strategy.combination == VALID_COMBINATION))
    assert saved is not None
