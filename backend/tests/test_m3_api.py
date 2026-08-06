# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — контракты API.

Проверяется: поведение при выключенном флаге фичи, права доступа, валидации
состава портфеля, сборка анкеты, правило арбитра через API, сквозной прогон
контрольного кейса (те же числа, что в test_m3_scoring), версионирование
пунктов в админке, trade-off и чек-лист.

Арифметика здесь НЕ дублируется — она покрыта юнит-тестами ядра. Здесь
проверяется, что до ядра доходят правильные данные и обратно доходит
правильный ответ.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.auth import create_token
from app.config import get_settings
from app.m3_models import M3Content, M3Hint, M3Item, M3Weight
from app.m3_config import INDUSTRY_PRESETS
from seed_m3 import CONTENT_BLOCKS, HINTS, ITEMS

M3 = "/api/m3"
REPORTS = "/api/reports/m3"


def as_role(client, user) -> None:
    """
    Переключение роли на одном клиенте. Фикстуры auth_client и admin_client
    возвращают ОДИН объект с общей cookie jar, поэтому запросить обе в тесте
    нельзя: победит та, что разрешилась последней, и проверка прав
    превратится в проверку самой себя.
    """
    client.cookies.clear()
    client.cookies.set("auth-token", create_token(
        user_id=str(user.id), email=user.email, role=user.role))


@pytest.fixture
def m3_on():
    """
    Settings кэшируется через lru_cache, поэтому подменяем атрибут
    на самом объекте: переустановка переменной окружения после первого
    вызова get_settings() не подействовала бы.
    """
    s = get_settings()
    old = s.m3_enabled
    s.m3_enabled = True
    yield
    s.m3_enabled = old


@pytest.fixture
def m3_off():
    s = get_settings()
    old = s.m3_enabled
    s.m3_enabled = False
    yield
    s.m3_enabled = old


@pytest_asyncio.fixture
async def seeded(db_session):
    """Справочники: анкета, веса, контент, подсказки."""
    for it in ITEMS:
        db_session.add(M3Item(
            code=it["code"], block=it["block"], number=it["number"],
            line=it["line"], text=it["text"], is_reverse=it["is_reverse"],
            industry_id=None, item_version=1, is_active=True,
        ))
    for iid, p in INDUSTRY_PRESETS.items():
        db_session.add(M3Weight(
            industry_id=iid, name=p["name"],
            w_l1=p["L1"], w_l2=p["L2"], w_l3=p["L3"],
            w_l4=p["L4"], w_l5=p["L5"], w_l6=p["L6"],
        ))
    for b in CONTENT_BLOCKS:
        db_session.add(M3Content(
            kind=b["kind"], key=b["key"], title=b["title"],
            body=b["body"], mistake=b["mistake"], industry_id=None,
        ))
    for h in HINTS:
        db_session.add(M3Hint(
            industry_id=h["industry_id"], item_code=h["item_code"], text=h["text"]
        ))
    await db_session.flush()


# ── Контрольный кейс ──────────────────────────────────────────────────────────
CONTROL_OBJECTS = [
    {"position": 1, "name": "Салонный канал B2B", "revenue": 180,
     "revenue_dynamics": -5, "revenue_share": 45, "profitability": "profitable",
     "industry_id": 2, "screening_price": True, "screening_market": False},
    {"position": 2, "name": "Маркетплейсы", "revenue": 120,
     "revenue_dynamics": 60, "revenue_share": 30, "profitability": "marginal",
     "industry_id": 7, "screening_price": False, "screening_market": False},
    {"position": 3, "name": "Интернет-магазин", "revenue": 32,
     "revenue_dynamics": 10, "revenue_share": 8, "profitability": "marginal",
     "industry_id": 7, "screening_price": True, "screening_market": False},
    {"position": 4, "name": "Контрактное пр-во", "revenue": 48,
     "revenue_dynamics": 15, "revenue_share": 12, "profitability": "profitable",
     "industry_id": 2, "screening_price": True, "screening_market": False},
    {"position": 5, "name": "Обучение мастеров", "revenue": 20,
     "revenue_dynamics": 40, "revenue_share": 5, "profitability": "marginal",
     "industry_id": 10, "screening_price": True, "screening_market": True},
]

MARKET_ANSWERS = {"Р1": 2, "Р2": 2, "Р3": 3, "Р4": 3, "Р5": 3, "Р6": 2}

OBJECT_ANSWERS = {
    1: {"Н1": 3, "Н2": 2, "Н3": 3, "Н4": 2, "Н5": 4, "Н6": 1, "Н7": 2, "Н8": 3},
    2: {"Н1": 2, "Н2": 3, "Н3": 3, "Н4": 2, "Н5": 1, "Н6": 4, "Н7": 4, "Н8": 1,
        "Р1*": 1, "Р2*": 2, "Р3*": 3},
    3: {"Н1": 3, "Н2": 2, "Н3": 2, "Н4": 3, "Н5": 2, "Н6": 3, "Н7": 3, "Н8": 2},
    4: {"Н1": 3, "Н2": 2, "Н3": 2, "Н4": 3, "Н5": 3, "Н6": 3, "Н7": 3, "Н8": 2},
    5: {"Н1": 1, "Н2": 4, "Н3": 3, "Н4": 2, "Н5": 2, "Н6": 3, "Н7": 3, "Н8": 2,
        "Р1*": 3, "Р2*": 3, "Р3*": 3, "Р4*": 4, "Р5*": 3, "Р6*": 2},
}
ARBITER_ANSWERS = {4: {"А3": 3}}
OWNER_RANKS = [3, 1, 5, 4, 2]


async def _make_portfolio(client: AsyncClient) -> dict:
    r = await client.post(f"{M3}/portfolios", json={"title": "Косметика", "industry_id": 2})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = await client.put(f"{M3}/portfolios/{pid}/objects", json={"objects": CONTROL_OBJECTS})
    assert r.status_code == 200, r.text
    return r.json()


async def _fill(client: AsyncClient, portfolio: dict, with_arbiter: bool = True) -> None:
    pid = portfolio["id"]
    by_pos = {o["position"]: o["id"] for o in portfolio["objects"]}

    payload = [{"item_code": c, "value": v} for c, v in MARKET_ANSWERS.items()]
    r = await client.post(f"{M3}/portfolios/{pid}/answers", json={"answers": payload})
    assert r.status_code == 200, r.text

    for pos, answers in OBJECT_ANSWERS.items():
        payload = [
            {"item_code": c, "value": v, "object_id": by_pos[pos]}
            for c, v in answers.items()
        ]
        r = await client.post(f"{M3}/portfolios/{pid}/answers", json={"answers": payload})
        assert r.status_code == 200, r.text

    if with_arbiter:
        for pos, answers in ARBITER_ANSWERS.items():
            payload = [
                {"item_code": c, "value": v, "object_id": by_pos[pos]}
                for c, v in answers.items()
            ]
            r = await client.post(f"{M3}/portfolios/{pid}/answers", json={"answers": payload})
            assert r.status_code == 200, r.text

    r = await client.put(f"{M3}/portfolios/{pid}/owner-ranks", json={"ranks": OWNER_RANKS})
    assert r.status_code == 200, r.text


@pytest_asyncio.fixture
async def calculated(auth_client: AsyncClient, seeded, m3_on):
    p = await _make_portfolio(auth_client)
    await _fill(auth_client, p)
    r = await auth_client.post(f"{M3}/portfolios/{p['id']}/calculate")
    assert r.status_code == 200, r.text
    return p


# ── Флаг фичи ─────────────────────────────────────────────────────────────────
class TestFeatureFlag:
    """
    404, а не 403: при выключенном флаге раздела не существует. 403 сообщал бы,
    что функциональность есть и она закрыта, — лишняя информация до релиза.
    """

    @pytest.mark.parametrize("method,path", [
        ("post", f"{M3}/portfolios"),
        ("get", f"{M3}/portfolios"),
        ("get", f"{M3}/portfolios/{uuid.uuid4()}"),
        ("get", f"{M3}/portfolios/{uuid.uuid4()}/questionnaire"),
        ("get", f"{M3}/portfolios/{uuid.uuid4()}/arbiter-required"),
        ("post", f"{M3}/portfolios/{uuid.uuid4()}/calculate"),
        ("get", f"{REPORTS}/{uuid.uuid4()}"),
        ("get", f"{REPORTS}/{uuid.uuid4()}/checklist"),
    ])
    async def test_404_when_disabled(self, auth_client, m3_off, method, path):
        kwargs = {"json": {}} if method == "post" else {}
        r = await getattr(auth_client, method)(path, **kwargs)
        assert r.status_code == 404

    async def test_admin_404_when_disabled(self, admin_client, m3_off):
        r = await admin_client.get("/api/admin/m3/items")
        assert r.status_code == 404

    async def test_anonymous_also_gets_404_when_disabled(self, client, m3_off):
        """
        Гейт флага висит на роутере и резолвится раньше Depends(get_current_user).
        Пока проверка стояла в теле эндпоинта, аноним получал 401, и по коду
        ответа раздел отличался от несуществующего пути — то есть о его
        существовании можно было узнать снаружи до релиза.
        """
        r = await client.get(f"{M3}/portfolios")
        assert r.status_code == 404
        r = await client.get("/api/admin/m3/items")
        assert r.status_code == 404
        r = await client.get(f"{REPORTS}/{uuid.uuid4()}")
        assert r.status_code == 404

    async def test_available_when_enabled(self, auth_client, m3_on):
        r = await auth_client.get(f"{M3}/portfolios")
        assert r.status_code == 200

    async def test_router_registered_either_way(self, m3_off):
        """
        Роутер подключён всегда — флаг гасит эндпоинты, а не сборку маршрутов:
        включение не должно требовать пересборки образа.

        Проверяем по openapi(), а не по app.routes: внутреннее представление
        маршрутов у FastAPI менялось между версиями (0.141 заворачивает
        подключённые роутеры в _IncludedRouter без атрибута path), openapi —
        публичный контракт и от версии не зависит.
        """
        from app.main import app
        paths = set(app.openapi()["paths"])
        assert f"{M3}/portfolios" in paths
        assert f"{M3}/portfolios/{{portfolio_id}}/calculate" in paths
        assert f"{REPORTS}/{{portfolio_id}}" in paths
        assert "/api/admin/m3/items" in paths


# ── Права доступа ─────────────────────────────────────────────────────────────
class TestAccess:
    async def test_anonymous_rejected(self, client, m3_on):
        r = await client.post(f"{M3}/portfolios", json={})
        assert r.status_code == 401

    async def test_foreign_portfolio_forbidden(
        self, auth_client, client, db_session, m3_on, seeded
    ):
        r = await auth_client.post(f"{M3}/portfolios", json={"title": "Чужой"})
        pid = r.json()["id"]

        from app.auth import create_token, hash_password
        from app.models import User
        other = User(id=uuid.uuid4(), email=f"o-{uuid.uuid4().hex[:8]}@e.com",
                     password_hash=hash_password("Password123"), role="user")
        db_session.add(other)
        await db_session.flush()
        client.cookies.clear()
        client.cookies.set("auth-token", create_token(
            user_id=str(other.id), email=other.email, role=other.role))

        r = await client.get(f"{M3}/portfolios/{pid}")
        assert r.status_code == 403

    async def test_admin_sees_foreign_portfolio(
        self, client, test_user, test_admin, m3_on, seeded
    ):
        """
        auth_client и admin_client — один и тот же объект клиента с общей
        cookie jar: взять оба фикстурами значит получить роль того, чья
        фикстура разрешилась последней. Роли переключаем явно.
        """
        as_role(client, test_user)
        r = await client.post(f"{M3}/portfolios", json={"title": "X"})
        pid = r.json()["id"]

        as_role(client, test_admin)
        r = await client.get(f"{M3}/portfolios/{pid}")
        assert r.status_code == 200

    async def test_admin_endpoints_require_admin(self, auth_client, m3_on):
        r = await auth_client.get("/api/admin/m3/items")
        assert r.status_code == 403


# ── Состав портфеля ───────────────────────────────────────────────────────────
class TestObjects:
    async def test_too_few_rejected(self, auth_client, m3_on):
        r = await auth_client.post(f"{M3}/portfolios", json={})
        pid = r.json()["id"]
        r = await auth_client.put(
            f"{M3}/portfolios/{pid}/objects",
            json={"objects": CONTROL_OBJECTS[:2]},
        )
        assert r.status_code == 422

    async def test_too_many_rejected(self, auth_client, m3_on):
        r = await auth_client.post(f"{M3}/portfolios", json={})
        pid = r.json()["id"]
        objs = [dict(o, position=i + 1) for i, o in enumerate(CONTROL_OBJECTS * 2)][:9]
        r = await auth_client.put(f"{M3}/portfolios/{pid}/objects", json={"objects": objs})
        assert r.status_code == 422

    async def test_shares_over_100_rejected(self, auth_client, m3_on):
        r = await auth_client.post(f"{M3}/portfolios", json={})
        pid = r.json()["id"]
        objs = [dict(o) for o in CONTROL_OBJECTS]
        objs[0]["revenue_share"] = 90
        r = await auth_client.put(f"{M3}/portfolios/{pid}/objects", json={"objects": objs})
        assert r.status_code == 422

    async def test_tiny_share_rejected(self, auth_client, m3_on):
        r = await auth_client.post(f"{M3}/portfolios", json={})
        pid = r.json()["id"]
        objs = [dict(o) for o in CONTROL_OBJECTS]
        objs[4]["revenue_share"] = 1
        r = await auth_client.put(f"{M3}/portfolios/{pid}/objects", json={"objects": objs})
        assert r.status_code == 422

    async def test_low_coverage_rejected(self, auth_client, m3_on):
        """Портфель, из которого выпала половина бизнеса, не отвечает
        на вопрос о распределении ресурса."""
        r = await auth_client.post(f"{M3}/portfolios", json={})
        pid = r.json()["id"]
        objs = [dict(o, revenue_share=10) for o in CONTROL_OBJECTS]
        r = await auth_client.put(f"{M3}/portfolios/{pid}/objects", json={"objects": objs})
        assert r.status_code == 422

    async def test_two_new_ventures_rejected(self, auth_client, m3_on):
        r = await auth_client.post(f"{M3}/portfolios", json={})
        pid = r.json()["id"]
        objs = [dict(o) for o in CONTROL_OBJECTS]
        objs[0]["is_new_venture"] = True
        objs[1]["is_new_venture"] = True
        r = await auth_client.put(f"{M3}/portfolios/{pid}/objects", json={"objects": objs})
        assert r.status_code == 422

    async def test_replace_after_calculate_conflicts(self, auth_client, calculated):
        r = await auth_client.put(
            f"{M3}/portfolios/{calculated['id']}/objects",
            json={"objects": CONTROL_OBJECTS},
        )
        assert r.status_code == 409

    async def test_owner_ranks_must_be_permutation(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        r = await auth_client.put(
            f"{M3}/portfolios/{p['id']}/owner-ranks", json={"ranks": [1, 1, 2, 3, 4]}
        )
        assert r.status_code == 422


# ── Справочники ───────────────────────────────────────────────────────────────
class TestIndustries:
    async def test_list_from_db(self, auth_client, m3_on, seeded):
        r = await auth_client.get(f"{M3}/industries")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 18
        assert rows[0] == {"id": 1, "name": "IT и разработка"}
        assert rows[-1]["id"] == 18

    async def test_falls_back_to_config_before_seed(self, auth_client, m3_on):
        """До сида таблица пуста — форма не должна остаться без вариантов."""
        r = await auth_client.get(f"{M3}/industries")
        assert r.status_code == 200
        assert len(r.json()) == 18

    async def test_reflects_admin_rename(self, client, test_user, test_admin, m3_on, seeded):
        """Название правится в админке вместе с весами: второй список
        в коде фронта разошёлся бы с первым при первой же правке."""
        as_role(client, test_admin)
        r = await client.put("/api/admin/m3/weights/2", json={
            "industry_id": 2, "name": "Производство и сборка",
            "w_l1": 45, "w_l2": 25, "w_l3": 30,
            "w_l4": 30, "w_l5": 45, "w_l6": 25,
        })
        assert r.status_code == 200

        as_role(client, test_user)
        rows = (await client.get(f"{M3}/industries")).json()
        assert next(x for x in rows if x["id"] == 2)["name"] == "Производство и сборка"

    async def test_404_when_disabled(self, client, m3_off):
        r = await client.get(f"{M3}/industries")
        assert r.status_code == 404


# ── Анкета ────────────────────────────────────────────────────────────────────
class TestQuestionnaire:
    async def test_structure(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        r = await auth_client.get(f"{M3}/portfolios/{p['id']}/questionnaire")
        assert r.status_code == 200
        q = r.json()
        assert len(q["market_items"]) == 6
        assert len(q["object_items"]) == 8
        assert len(q["override_items"]) == 6
        assert len(q["arbiter_items"]) == 4
        assert len(q["objects"]) == 5

    async def test_reverse_items_marked(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        q = (await auth_client.get(f"{M3}/portfolios/{p['id']}/questionnaire")).json()
        reverse = {i["code"] for i in q["market_items"] + q["object_items"] if i["is_reverse"]}
        assert reverse == {"Р3", "Р6", "Н2", "Н4", "Н6", "Н8"}

    async def test_arbiters_not_mixed_into_object_items(self, auth_client, m3_on, seeded):
        """Адаптивность в том и состоит, что арбитр появляется
        при неоднозначности, а не заранее."""
        p = await _make_portfolio(auth_client)
        q = (await auth_client.get(f"{M3}/portfolios/{p['id']}/questionnaire")).json()
        assert all(not i["is_arbiter"] for i in q["object_items"])
        assert all(i["is_arbiter"] for i in q["arbiter_items"])

    async def test_industry_hint_attached(self, auth_client, m3_on, seeded):
        r = await auth_client.post(f"{M3}/portfolios", json={"industry_id": 12})
        pid = r.json()["id"]
        await auth_client.put(f"{M3}/portfolios/{pid}/objects", json={"objects": CONTROL_OBJECTS})
        q = (await auth_client.get(f"{M3}/portfolios/{pid}/questionnaire")).json()
        hints = {i["code"]: i["hint"] for i in q["market_items"]}
        assert hints["Р1"] is not None       # Энергетика и ЖКХ: тарифное регулирование
        assert hints["Р5"] is None

    async def test_no_hint_for_industry_without_one(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)     # отрасль 2, подсказок нет
        q = (await auth_client.get(f"{M3}/portfolios/{p['id']}/questionnaire")).json()
        assert all(i["hint"] is None for i in q["market_items"])


# ── Ответы ────────────────────────────────────────────────────────────────────
class TestAnswers:
    async def test_market_item_rejects_object_id(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        oid = p["objects"][0]["id"]
        r = await auth_client.post(
            f"{M3}/portfolios/{p['id']}/answers",
            json={"answers": [{"item_code": "Р1", "value": 3, "object_id": oid}]},
        )
        assert r.status_code == 400

    async def test_object_item_requires_object_id(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        r = await auth_client.post(
            f"{M3}/portfolios/{p['id']}/answers",
            json={"answers": [{"item_code": "Н1", "value": 3}]},
        )
        assert r.status_code == 400

    async def test_unknown_item_rejected(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        r = await auth_client.post(
            f"{M3}/portfolios/{p['id']}/answers",
            json={"answers": [{"item_code": "Н9", "value": 3,
                               "object_id": p["objects"][0]["id"]}]},
        )
        assert r.status_code == 400

    async def test_value_out_of_range_rejected(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        r = await auth_client.post(
            f"{M3}/portfolios/{p['id']}/answers",
            json={"answers": [{"item_code": "Р1", "value": 5}]},
        )
        assert r.status_code == 422

    async def test_incremental_overwrite(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        pid = p["id"]
        await auth_client.post(f"{M3}/portfolios/{pid}/answers",
                               json={"answers": [{"item_code": "Р1", "value": 1}]})
        r = await auth_client.post(f"{M3}/portfolios/{pid}/answers",
                                   json={"answers": [{"item_code": "Р1", "value": 4}]})
        assert r.status_code == 200
        assert r.json()["status"] == "filled"

    async def test_unknown_value_allowed(self, auth_client, m3_on, seeded):
        """«Не знаю» — законный ответ, он сам по себе диагноз."""
        p = await _make_portfolio(auth_client)
        r = await auth_client.post(
            f"{M3}/portfolios/{p['id']}/answers",
            json={"answers": [{"item_code": "Р1", "value": None}]},
        )
        assert r.status_code == 200


# ── Арбитр ────────────────────────────────────────────────────────────────────
class TestArbiter:
    async def test_only_object_four_line_three(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        await _fill(auth_client, p, with_arbiter=False)
        r = await auth_client.get(f"{M3}/portfolios/{p['id']}/arbiter-required")
        assert r.status_code == 200
        by_pos = {row["position"]: row["lines"] for row in r.json()}
        assert by_pos == {1: [], 2: [], 3: [], 4: [3], 5: []}

    async def test_arbiter_item_text_returned(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        await _fill(auth_client, p, with_arbiter=False)
        rows = (await auth_client.get(f"{M3}/portfolios/{p['id']}/arbiter-required")).json()
        row = next(r for r in rows if r["position"] == 4)
        assert [i["code"] for i in row["items"]] == ["А3"]
        assert row["items"][0]["is_arbiter"] is True


# ── Сквозной расчёт ───────────────────────────────────────────────────────────
class TestCalculate:
    async def test_calculate_returns_summary(self, auth_client, calculated):
        r = await auth_client.post(f"{M3}/portfolios/{calculated['id']}/calculate")
        body = r.json()
        assert body["objects"] == 5
        assert body["verdicts_held"] is False
        assert body["flags"] == []

    async def test_status_becomes_calculated(self, auth_client, calculated):
        r = await auth_client.get(f"{M3}/portfolios/{calculated['id']}")
        assert r.json()["status"] == "calculated"
        assert r.json()["calculated_at"] is not None

    async def test_calculate_without_objects_rejected(self, auth_client, m3_on, seeded):
        r = await auth_client.post(f"{M3}/portfolios", json={})
        pid = r.json()["id"]
        r = await auth_client.post(f"{M3}/portfolios/{pid}/calculate")
        assert r.status_code == 400

    async def test_report_before_calculate_rejected(self, auth_client, m3_on, seeded):
        p = await _make_portfolio(auth_client)
        r = await auth_client.get(f"{REPORTS}/{p['id']}")
        assert r.status_code == 400


# ── Отчёт ─────────────────────────────────────────────────────────────────────
class TestReport:
    @pytest_asyncio.fixture
    async def report(self, auth_client, calculated):
        r = await auth_client.get(f"{REPORTS}/{calculated['id']}")
        assert r.status_code == 200, r.text
        return r.json()

    def test_control_case_numbers(self, report):
        """Те же значения, что в юнит-тестах ядра: путь через БД
        ничего не потерял и не округлил лишний раз."""
        by_name = {o["result"]["name"]: o["result"] for o in report["objects"]}
        expected = {
            "Салонный канал B2B": (26, None, 41, 3.30, 2.25, 5, 1),
            "Маркетплейсы":       (64, 50, 4, 1.80, 2.87, 2, 2),
            "Интернет-магазин":   (21, None, None, 2.30, 2.60, 4, 4),
            "Контрактное пр-во":  (30, None, None, 2.65, 2.55, 3, 3),
            "Обучение мастеров":  (6, 10, None, 2.15, 3.00, 1, 5),
        }
        for name, (cur, tgt, risk, cs, ca, vr, zr) in expected.items():
            r = by_name[name]
            assert (r["current_hex"], r["target_hex"], r["risk_hex"]) == (cur, tgt, risk)
            assert (r["coord_strength"], r["coord_attract"]) == (cs, ca)
            assert (r["v_rank"], r["z_rank"]) == (vr, zr)

    def test_portfolio_summary(self, report):
        s = report["summary"]
        assert (s["sum_positions"], s["turbulence"], s["delta"]) == (18, 4, 0)
        assert s["distinct_cells"] == 4
        assert s["spearman"] == 0.60
        assert s["verdicts_held"] is False

    def test_objects_ordered_by_investment_rank(self, report):
        ranks = [o["result"]["v_rank"] for o in report["objects"]]
        assert ranks == sorted(ranks)

    def test_two_orders_diverge(self, report):
        """Расхождение приоритета вложения и очереди исполнения — результат,
        а не дефект: денежная корова последняя по V и первая по Z."""
        assert report["investment_order"] != report["execution_order"]
        assert report["investment_order"][-1] == report["execution_order"][0]

    def test_narrative_assembled_from_blocks(self, report):
        by_name = {o["result"]["name"]: o for o in report["objects"]}
        mp = by_name["Маркетплейсы"]
        kinds = [b["kind"] for b in mp["narrative"]]
        assert kinds[:3] == ["zone", "weak_line", "strong_line"]
        assert kinds.count("tension") == 3

    def test_same_cell_different_narrative(self, report):
        """Направления 2 и 3 стоят в одной ячейке, но получают разные разборы:
        различаются ведущими линиями и набором напряжений."""
        by_name = {o["result"]["name"]: o for o in report["objects"]}
        a, b = by_name["Маркетплейсы"], by_name["Интернет-магазин"]
        assert a["result"]["cell_key"] == b["result"]["cell_key"] == "low_mid"
        assert [x["key"] for x in a["narrative"]] != [x["key"] for x in b["narrative"]]

    def test_zone_block_carries_mistake(self, report):
        zone = report["objects"][0]["narrative"][0]
        assert zone["kind"] == "zone"
        assert zone["mistake"]

    def test_disclaimers_present(self, report):
        text = " ".join(report["disclaimers"])
        assert "экспертные априорные" in text
        assert "идентификатор конфигурации" in text

    def test_hexagram_name_returned_but_secondary(self, report):
        r = report["objects"][0]["result"]
        assert r["current_name"]
        assert isinstance(r["current_hex"], int)


# ── Чек-лист и trade-off ──────────────────────────────────────────────────────
class TestChecklistAndTradeoff:
    async def test_checklist_built_on_calculate(self, auth_client, calculated):
        r = await auth_client.get(f"{REPORTS}/{calculated['id']}/checklist")
        assert r.status_code == 200
        steps = r.json()
        kinds = {s["step_type"] for s in steps}
        assert "route" in kinds and "hold" in kinds and "prep" in kinds

    async def test_route_step_only_for_old_yin(self, auth_client, calculated):
        """Старый Ян даёт не шаг маршрута, а пакет удержания: цель там
        остаться на месте, а не переместиться."""
        steps = (await auth_client.get(f"{REPORTS}/{calculated['id']}/checklist")).json()
        by_type = {}
        for s in steps:
            by_type.setdefault(s["step_type"], []).append(s)
        assert len(by_type["route"]) == 2      # старых Инь в кейсе два
        assert len(by_type["hold"]) == 2       # старых Ян тоже два

    async def test_toggle_step(self, auth_client, calculated):
        steps = (await auth_client.get(f"{REPORTS}/{calculated['id']}/checklist")).json()
        sid = steps[0]["id"]
        r = await auth_client.patch(
            f"{REPORTS}/{calculated['id']}/checklist/{sid}", json={"done": True}
        )
        assert r.status_code == 200
        assert r.json()["done"] is True and r.json()["done_at"]

    async def test_toggle_foreign_step_404(self, auth_client, calculated):
        r = await auth_client.patch(
            f"{REPORTS}/{calculated['id']}/checklist/{uuid.uuid4()}", json={"done": True}
        )
        assert r.status_code == 404

    async def test_tradeoff_reschedules_waves(self, auth_client, calculated):
        objs = calculated["objects"]
        waves = {"1": [objs[0]["id"], objs[1]["id"]],
                 "2": [objs[2]["id"], objs[3]["id"], objs[4]["id"]]}
        r = await auth_client.post(
            f"{REPORTS}/{calculated['id']}/tradeoff",
            json={"accepted_option": "method", "waves": waves,
                  "cost_accepted": "Обучение ждёт полгода",
                  "review_triggers": ["падение выручки волны 1 на 10%"]},
        )
        assert r.status_code == 200, r.text

        steps = (await auth_client.get(f"{REPORTS}/{calculated['id']}/checklist")).json()
        wave2 = {s["object_id"] for s in steps if s["wave"] == 2}
        assert wave2 <= {objs[2]["id"], objs[3]["id"], objs[4]["id"]}

    async def test_prep_step_stays_in_first_wave(self, auth_client, calculated):
        """Подготовительный шаг не учитывается в правиле такта: его результат —
        знание, а не изменение конфигурации линий."""
        objs = calculated["objects"]
        waves = {"1": [objs[0]["id"]],
                 "2": [o["id"] for o in objs[1:]]}
        await auth_client.post(
            f"{REPORTS}/{calculated['id']}/tradeoff",
            json={"accepted_option": "method", "waves": waves},
        )
        steps = (await auth_client.get(f"{REPORTS}/{calculated['id']}/checklist")).json()
        prep = [s for s in steps if s["step_type"] == "prep"]
        assert prep and all(s["wave"] == 1 for s in prep)

    async def test_object_in_two_waves_rejected(self, auth_client, calculated):
        oid = calculated["objects"][0]["id"]
        r = await auth_client.post(
            f"{REPORTS}/{calculated['id']}/tradeoff",
            json={"accepted_option": "method", "waves": {"1": [oid], "2": [oid]}},
        )
        assert r.status_code == 400

    async def test_foreign_object_in_waves_rejected(self, auth_client, calculated):
        r = await auth_client.post(
            f"{REPORTS}/{calculated['id']}/tradeoff",
            json={"accepted_option": "method", "waves": {"1": [str(uuid.uuid4())]}},
        )
        assert r.status_code == 400


# ── Админка ───────────────────────────────────────────────────────────────────
class TestAdmin:
    async def test_list_items(self, admin_client, m3_on, seeded):
        r = await admin_client.get("/api/admin/m3/items")
        assert r.status_code == 200
        assert len(r.json()) == 24        # 6 Р + 6 Р* + 8 Н + 4 А

    async def test_edit_creates_new_version(self, admin_client, m3_on, seeded):
        """Правка формулировки создаёт новую версию, старая не удаляется:
        иначе выданные отчёты станут несопоставимы с новыми."""
        r = await admin_client.post("/api/admin/m3/items", json={
            "code": "Н2", "block": "Н", "number": 2, "line": 1,
            "text": "Новая редакция пункта про переиспользование наработок.",
            "is_reverse": True,
        })
        assert r.status_code == 201, r.text
        assert r.json()["item_version"] == 2

        rows = (await admin_client.get("/api/admin/m3/items")).json()
        n2 = [i for i in rows if i["code"] == "Н2"]
        assert len(n2) == 2
        assert {i["item_version"]: i["is_active"] for i in n2} == {1: False, 2: True}

    async def test_new_version_used_in_questionnaire(
        self, client, test_user, test_admin, m3_on, seeded
    ):
        as_role(client, test_admin)
        r = await client.post("/api/admin/m3/items", json={
            "code": "Н2", "block": "Н", "number": 2, "line": 1,
            "text": "ВТОРАЯ РЕДАКЦИЯ", "is_reverse": True,
        })
        assert r.status_code == 201, r.text

        as_role(client, test_user)
        p = await _make_portfolio(client)
        q = (await client.get(f"{M3}/portfolios/{p['id']}/questionnaire")).json()
        n2 = next(i for i in q["object_items"] if i["code"] == "Н2")
        assert n2["text"] == "ВТОРАЯ РЕДАКЦИЯ"
        assert n2["item_version"] == 2

    async def test_weights_must_sum_to_100(self, admin_client, m3_on, seeded):
        r = await admin_client.put("/api/admin/m3/weights/2", json={
            "industry_id": 2, "name": "Производство",
            "w_l1": 50, "w_l2": 25, "w_l3": 30,
            "w_l4": 30, "w_l5": 45, "w_l6": 25,
        })
        assert r.status_code == 422

    async def test_weights_updated(self, admin_client, m3_on, seeded):
        r = await admin_client.put("/api/admin/m3/weights/2", json={
            "industry_id": 2, "name": "Производство",
            "w_l1": 40, "w_l2": 30, "w_l3": 30,
            "w_l4": 30, "w_l5": 45, "w_l6": 25,
        })
        assert r.status_code == 200
        rows = (await admin_client.get("/api/admin/m3/weights")).json()
        assert next(w for w in rows if w["industry_id"] == 2)["w_l1"] == 40

    async def test_content_upsert(self, admin_client, m3_on, seeded):
        r = await admin_client.put("/api/admin/m3/content", json={
            "kind": "zone", "key": "high_low", "title": "Сбор урожая",
            "body": "Правленый текст зоны.", "mistake": "Правленая ошибка.",
        })
        assert r.status_code == 200
        rows = (await admin_client.get("/api/admin/m3/content")).json()
        block = next(c for c in rows if c["kind"] == "zone" and c["key"] == "high_low")
        assert block["body"] == "Правленый текст зоны."

    async def test_content_has_31_blocks(self, admin_client, m3_on, seeded):
        rows = (await admin_client.get("/api/admin/m3/content")).json()
        assert len(rows) == 31
        by_kind = {}
        for c in rows:
            by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        assert by_kind == {"zone": 9, "weak_line": 6, "strong_line": 6, "tension": 10}

    async def test_hints_upsert(self, admin_client, m3_on, seeded):
        r = await admin_client.put("/api/admin/m3/hints", json={
            "industry_id": 8, "item_code": "Н5", "text": "Новая подсказка.",
        })
        assert r.status_code == 200
        rows = (await admin_client.get("/api/admin/m3/hints")).json()
        h = next(x for x in rows if x["industry_id"] == 8 and x["item_code"] == "Н5")
        assert h["text"] == "Новая подсказка."


# ── Снимок расчёта ────────────────────────────────────────────────────────────
class TestSnapshot:
    async def test_item_versions_recorded(self, auth_client, db_session, calculated):
        """Без версий пунктов правка формулировки сделает старые отчёты
        несопоставимыми с новыми, и модуль динамики начнёт врать."""
        from sqlalchemy import select
        from app.m3_models import M3Result
        rows = (await db_session.execute(
            select(M3Result).where(M3Result.portfolio_id == uuid.UUID(calculated["id"]))
        )).scalars().all()
        assert len(rows) == 5
        for r in rows:
            assert r.item_versions
            assert all(v == 1 for v in r.item_versions.values())

    async def test_report_survives_weight_edit(
        self, client, test_user, test_admin, calculated
    ):
        """
        Отчёт собирается из снимка, а не пересчитывается: правка весов в админке
        не должна менять уже выданный документ. Иначе клиент, открывший отчёт
        второй раз, увидел бы другие числа.
        """
        before = (await client.get(f"{REPORTS}/{calculated['id']}")).json()

        as_role(client, test_admin)
        r = await client.put("/api/admin/m3/weights/2", json={
            "industry_id": 2, "name": "Производство",
            "w_l1": 34, "w_l2": 33, "w_l3": 33,
            "w_l4": 34, "w_l5": 33, "w_l6": 33,
        })
        assert r.status_code == 200, r.text

        as_role(client, test_user)
        after = (await client.get(f"{REPORTS}/{calculated['id']}")).json()
        assert before["objects"][0]["result"]["coord_strength"] == \
               after["objects"][0]["result"]["coord_strength"]

    async def test_recalculate_is_idempotent(self, auth_client, calculated):
        before = (await auth_client.get(f"{REPORTS}/{calculated['id']}")).json()
        await auth_client.post(f"{M3}/portfolios/{calculated['id']}/calculate")
        after = (await auth_client.get(f"{REPORTS}/{calculated['id']}")).json()
        assert before["summary"] == after["summary"]
        assert len(after["objects"]) == 5


# ── Колонка «Рынок»: число переопределений доезжает до отчёта ─────────────────
@pytest.mark.asyncio
async def test_report_carries_market_overrides_of_control_case(auth_client, calculated):
    """
    Сквозная проверка: в контрольном кейсе второе направление отвечает на три
    пункта Р*, пятое — на все шесть, остальные наследуют рынок портфеля.
    Числа должны доехать от ответов до отчёта без потерь — именно из них
    собирается колонка «Рынок» в разделе 00.
    """
    r = await auth_client.get(f"{REPORTS}/{calculated['id']}")
    assert r.status_code == 200, r.text
    by_position = {
        o["result"]["position"]: o["result"]["market_overrides"]
        for o in r.json()["objects"]
    }
    assert by_position == {1: 0, 2: 3, 3: 0, 4: 0, 5: 6}


# ── Удаление портфеля ─────────────────────────────────────────────────────────
class TestDelete:
    @pytest.mark.asyncio
    async def test_owner_deletes_portfolio(self, auth_client, calculated):
        pid = calculated["id"]
        r = await auth_client.delete(f"{M3}/portfolios/{pid}")
        assert r.status_code == 204, r.text
        assert (await auth_client.get(f"{M3}/portfolios/{pid}")).status_code == 404
        assert (await auth_client.get(f"{REPORTS}/{pid}")).status_code == 404

    @pytest.mark.asyncio
    async def test_calculated_portfolio_disappears_from_list(self, auth_client, calculated):
        await auth_client.delete(f"{M3}/portfolios/{calculated['id']}")
        r = await auth_client.get(f"{M3}/portfolios")
        assert [p["id"] for p in r.json()] == []

    @pytest.mark.asyncio
    async def test_stranger_cannot_delete(self, auth_client, calculated, db_session,
                                          test_user, test_admin):
        """Чужой портфель не удаляется: проверка та же, что на чтении."""
        from app.auth import hash_password
        from app.models import User

        other = User(
            id=uuid.uuid4(), email=f"other-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("Password123"), full_name="Чужой", role="user",
        )
        db_session.add(other)
        await db_session.flush()

        as_role(auth_client, other)
        r = await auth_client.delete(f"{M3}/portfolios/{calculated['id']}")
        assert r.status_code == 403

        as_role(auth_client, test_user)
        assert (await auth_client.get(f"{M3}/portfolios/{calculated['id']}")).status_code == 200

    @pytest.mark.asyncio
    async def test_admin_deletes_any_portfolio(self, auth_client, calculated,
                                               test_admin, test_user):
        as_role(auth_client, test_admin)
        r = await auth_client.delete(f"{M3}/portfolios/{calculated['id']}")
        assert r.status_code == 204, r.text

    @pytest.mark.asyncio
    async def test_missing_portfolio_gives_404(self, auth_client, m3_on):
        r = await auth_client.delete(f"{M3}/portfolios/{uuid.uuid4()}")
        assert r.status_code == 404


# ── PDF Метода 3 не хранится ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_m3_pdf_is_removed_after_download(auth_client, calculated, monkeypatch):
    """
    Файл собирается на каждый запрос и удаляется после отдачи. Настоящий
    Playwright здесь не нужен: проверяется судьба файла, а не его содержимое.
    """
    from pathlib import Path

    import app.m3_report_api as report_api

    written: list[Path] = []

    async def _fake(html, output_path):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4 m3")
        written.append(path)

    monkeypatch.setattr(report_api, "generate_pdf", _fake)

    resp = await auth_client.get(f"{REPORTS}/{calculated['id']}/download")
    assert resp.status_code == 200, resp.text
    assert resp.content == b"%PDF-1.4 m3"

    assert len(written) == 1
    assert not written[0].exists(), "временный PDF должен удаляться после отдачи"
    assert str(get_settings().uploads_dir) not in str(written[0])
