# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — схемы Pydantic v2.

Отдельный модуль, а не schemas.py: schemas.py импортируют все остальные
методы, и добавление туда полутора сотен строк ради изолированного раздела
расширяет поверхность регресса без выигрыша. Прецедент в проекте есть —
routers/checklist.py объявляет свои тела запросов локально.
Стиль соблюдён: model_config = {"from_attributes": True} на всех выходных
схемах, Field-валидации на входных.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Profitability = Literal["profitable", "marginal", "unprofitable", "unknown"]
CellLevel = Literal["low", "mid", "high"]

# Ограничение методологическое, а не тарифное: цена от числа направлений
# не зависит.
OBJECTS_MIN = 3
OBJECTS_MAX = 8
MIN_SHARE = 3.0            # доля ниже 3% не различима на карте портфеля
MIN_COVERAGE = 80.0        # покрытие выручки портфелем


def _bounds() -> tuple[int, int]:
    """
    Действующие границы числа направлений: из конфига, иначе дефолты выше.

    Литералы OBJECTS_MIN/MAX остаются потолком позиции и запасным вариантом,
    но проверку количества больше не задают. Копия константы в схеме уже
    стоила режима: расчёт опустил минимум до единицы, а PUT objects
    продолжал отбивать портфель из одного направления, и войти
    в сокращённый режим через интерфейс было нельзя.
    """
    from app.m3_config import DEFAULT_M3_CONFIG, read_m3_config
    try:
        cfg = read_m3_config()
    except Exception:
        cfg = DEFAULT_M3_CONFIG
    return (int(cfg.get("objects_min", OBJECTS_MIN)),
            int(cfg.get("objects_max", OBJECTS_MAX)))


# ── Портфель ──────────────────────────────────────────────────────────────────
class M3PortfolioCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    # Название компании вводится перед диагностикой, как в Методах 1 и 2.
    company_name: str | None = Field(default=None, max_length=255)
    industry_id: int | None = Field(default=None, ge=1, le=18)


class M3ObjectIn(BaseModel):
    position: int = Field(ge=1, le=OBJECTS_MAX)
    name: str = Field(min_length=1, max_length=255)
    revenue: float | None = Field(default=None, ge=0)
    revenue_dynamics: float | None = Field(default=None, ge=-100, le=1000)
    revenue_share: float | None = Field(default=None, ge=0, le=100)
    profitability: Profitability = "unknown"
    industry_id: int | None = Field(default=None, ge=1, le=18)
    screening_price: bool = True
    screening_market: bool = False
    is_new_venture: bool = False


class M3ObjectsPut(BaseModel):
    objects: list[M3ObjectIn]

    @field_validator("objects")
    @classmethod
    def check_count(cls, v: list[M3ObjectIn]) -> list[M3ObjectIn]:
        lo, hi = _bounds()
        if not lo <= len(v) <= hi:
            raise ValueError(
                f"Направлений должно быть от {lo} до {hi}, получено {len(v)}"
            )
        positions = [o.position for o in v]
        if len(set(positions)) != len(positions):
            raise ValueError("Позиции направлений повторяются")
        return v

    @model_validator(mode="after")
    def check_shares(self):
        shares = [o.revenue_share for o in self.objects if o.revenue_share is not None]
        if not shares:
            return self
        if any(s < MIN_SHARE for s in shares):
            raise ValueError(
                f"Минимальная доля направления — {MIN_SHARE:g}%. Направление "
                "меньшего размера не различимо на карте портфеля и искажает "
                "индекс защиты."
            )
        total = sum(shares)
        if total > 100.0 + 1e-6:
            raise ValueError(f"Сумма долей {total:g}% превышает 100%")
        if len(shares) == len(self.objects) and total < MIN_COVERAGE:
            raise ValueError(
                f"Направления покрывают {total:g}% выручки при минимуме "
                f"{MIN_COVERAGE:g}%. Портфель, из которого выпала половина "
                "бизнеса, не отвечает на вопрос о распределении ресурса."
            )
        if sum(1 for o in self.objects if o.is_new_venture) > 1:
            raise ValueError("Новым направлением может быть отмечено только одно")
        return self


class M3OwnerRanks(BaseModel):
    """Порядок направлений, названный собственником ДО диагностики.
    Нужен для критерия 3 пилота: ранговая корреляция расчёта с интуицией."""

    ranks: list[int]

    @model_validator(mode="after")
    def check_permutation(self):
        n = len(self.ranks)
        if sorted(self.ranks) != list(range(1, n + 1)):
            raise ValueError(
                "Ранги собственника должны быть перестановкой 1..n без повторов"
            )
        return self


class M3ObjectOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    position: int
    name: str
    revenue: float | None
    revenue_dynamics: float | None
    revenue_share: float | None
    profitability: str
    industry_id: int | None
    screening_price: bool
    screening_market: bool
    is_new_venture: bool


class M3PortfolioOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str | None
    company_name: str | None = None
    industry_id: int | None
    status: str
    owner_ranks: list[int] | None
    created_at: datetime
    # updated_at сюда НЕ добавлять. Колонка имеет onupdate=func.now(), после
    # flush SQLAlchemy помечает её протухшей, и сериализация ответа лезет за
    # свежим значением уже вне async-контекста: MissingGreenlet -> 500 на
    # PUT owner-ranks. Единому списку отчётов в кабинете хватает
    # calculated_at и created_at.
    calculated_at: datetime | None
    objects: list[M3ObjectOut] = []


# ── Анкета ────────────────────────────────────────────────────────────────────
class M3ItemOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    block: str
    code: str
    line: int
    text: str
    is_reverse: bool
    item_version: int
    hint: str | None = None
    # Арбитры не отдаются в основном списке: показываются только по ответу
    # /arbiter-required, иначе теряется смысл адаптивности.
    is_arbiter: bool = False


class M3QuestionnaireOut(BaseModel):
    portfolio_id: uuid.UUID
    market_items: list[M3ItemOut]
    object_items: list[M3ItemOut]
    override_items: list[M3ItemOut]
    arbiter_items: list[M3ItemOut]
    objects: list[M3ObjectOut]


class M3AnswerIn(BaseModel):
    item_code: str = Field(min_length=2, max_length=4)
    object_id: uuid.UUID | None = None
    value: int | None = Field(default=None, ge=1, le=4)


class M3AnswersIn(BaseModel):
    """Сохранение инкрементальное: фронт шлёт то, что изменилось."""

    answers: list[M3AnswerIn] = Field(min_length=1)


class M3LimitsOut(BaseModel):
    """Границы и предупреждение для экрана направлений — единый источник."""
    objects_min: int
    objects_max: int
    portfolio_min: int
    reduced_warning: str


class M3ArbiterOut(BaseModel):
    object_id: uuid.UUID
    position: int
    name: str
    lines: list[int]
    items: list[M3ItemOut]


# ── Результаты ────────────────────────────────────────────────────────────────
class M3VerdictOut(BaseModel):
    """Вердикт направления: зона GE/McKinsey, уточнённая подвижностью линий."""

    zone_ru: str
    zone_en: str
    stance: str
    mobility: str
    verdict: str
    notes: list[str]


class M3TransitionMove(BaseModel):
    """
    Сдвиг по одной оси матрицы.

    Поля называются from/to, потому что так они приходят из m3_verdict и так
    читаются в JSON. `from` — ключевое слово Python, поэтому имя поля с
    подчёркиванием, а наружу отдаётся алиас: FastAPI сериализует ответы
    by_alias, так что в контракте остаётся «from».
    """

    model_config = {"populate_by_name": True}

    axis: str
    from_: CellLevel = Field(alias="from")
    to: CellLevel
    phrase: str


class M3TransitionOut(BaseModel):
    kind: Literal["target", "risk"]
    from_hex: int
    to_hex: int
    from_cells: tuple[CellLevel, CellLevel]
    to_cells: tuple[CellLevel, CellLevel]
    moves: list[M3TransitionMove]
    phrase: str


class M3TrajectoryOut(BaseModel):
    """
    Куда уводит цель и куда сползает риск.

    Обе ветки необязательны: подвижная линия может остаться внутри своей
    триграммы и ячейку не сдвинуть — тогда печатать нечего.
    """

    target: M3TransitionOut | None = None
    risk: M3TransitionOut | None = None


class M3CellLineOut(BaseModel):
    line: int
    weight: int


class M3CellAxisOut(BaseModel):
    """Вывод уровня по одной оси: какие линии дали Ян и на какую сумму весов."""
    level: CellLevel
    sum: int
    total: int
    lines: list[M3CellLineOut]
    # Готовая строка: веб печатает её, своей копии формулировки не держит.
    text: str = ""


class M3CellBreakdownOut(BaseModel):
    strength: M3CellAxisOut
    attract: M3CellAxisOut


class M3ResultOut(BaseModel):
    model_config = {"from_attributes": True}

    object_id: uuid.UUID
    name: str
    position: int
    scores: dict[str, float]
    symbols: str
    mobility: dict[str, str]
    cell_strength: CellLevel
    cell_attract: CellLevel
    cell_key: str
    cell_label: str
    coord_strength: float
    coord_attract: float
    current_hex: int
    current_name: str
    target_hex: int | None
    target_lines: list[int]
    risk_hex: int | None
    risk_lines: list[int]
    v_index: float
    z_index: float
    v_rank: int
    z_rank: int
    weak_line: int
    strong_line: int
    tensions: list[str]
    flags: list[str]
    # Сколько пунктов рынка направление переопределило своими ответами (0–6).
    # Дефолт нужен старым снимкам: у отчётов, собранных до появления поля,
    # его в словаре нет, и без дефолта отчёт перестал бы отдаваться.
    market_overrides: int = 0
    # Подпись колонки «Рынок». Дефолт нужен старым снимкам отчёта.
    market_label: str = ""
    # Вывод ячейки. None у снимков до ревизии 030: весов в них нет,
    # и достраивать их задним числом значит выдумать данные.
    cell_breakdown: M3CellBreakdownOut | None = None
    verdict: M3VerdictOut
    trajectory: M3TrajectoryOut
    execution_reason: str


class M3PortfolioSummaryOut(BaseModel):
    objects: int
    sum_positions: int
    sum_positions_max: int
    turbulence: int
    delta: int
    distinct_cells: int
    spearman: float | None
    owner_ranks: list[int] | None = None
    flags: list[str]
    verdicts_held: bool
    # Портфельный слой не считался: направлений меньше portfolio_min.
    reduced: bool = False


class M3NarrativeBlock(BaseModel):
    kind: str
    key: str
    title: str
    body: str
    mistake: str | None = None


class M3YinRow(BaseModel):
    """
    Строка профиля линии по портфелю.

    Четыре числа, а не одно: «слабость у трёх из пяти» ещё не вывод, важно —
    есть ли опора среди оставшихся и хватает ли подвижности на исправление.
    delta_line — назревшие минус перегретые ПО ЭТОЙ ЛИНИИ, не путать с
    дельтой портфеля в шапке и с дельтой направления в индексе V.
    """

    line: int
    factor: str
    yin: int
    yin_ripe: int
    yang: int
    yang_hot: int
    delta_line: int
    total: int
    strong_names: list[str]
    reading: str


class M3ConstraintOut(BaseModel):
    line: int
    factor: str
    yin: int
    yang: int
    yang_hot: int
    delta_line: int
    total: int
    kind: Literal["competence", "structural"]
    kind_title: str
    body: str


class M3MetricReading(BaseModel):
    name: str
    value: str
    reading: str


class M3RankRow(BaseModel):
    position: int
    name: str
    owner_rank: int
    v_rank: int
    gap: int


class M3RankComparison(BaseModel):
    """Порядок собственника против расчётного приоритета вложения."""

    rows: list[M3RankRow]
    agreed: int
    total: int
    disputed: list[M3RankRow]
    reading: str


class M3AnalysisOut(BaseModel):
    """Раздел 03: ограничения уровня компании, а не направления."""

    yin_table: list[M3YinRow]
    constraints: list[M3ConstraintOut]
    metrics: list[M3MetricReading]
    tact_note: str
    # None, если порядок не назван: сравнивать нечего.
    rank_comparison: M3RankComparison | None = None


class M3ObjectReport(BaseModel):
    result: M3ResultOut
    narrative: list[M3NarrativeBlock]


class M3ReportOut(BaseModel):
    portfolio: M3PortfolioOut
    summary: M3PortfolioSummaryOut
    objects: list[M3ObjectReport]
    investment_order: list[uuid.UUID]   # ранг V — приоритет вложения
    execution_order: list[uuid.UUID]    # ранг Z — очередь исполнения
    analysis: M3AnalysisOut
    disclaimers: list[str]


# ── Trade-off и чек-лист ──────────────────────────────────────────────────────
class M3TradeoffIn(BaseModel):
    accepted_option: Literal["method", "custom"]
    waves: dict[str, list[uuid.UUID]]
    cost_accepted: str | None = Field(default=None, max_length=5000)
    review_triggers: list[str] = []

    @field_validator("waves")
    @classmethod
    def check_waves(cls, v):
        if not v:
            raise ValueError("Волны не заданы")
        for k in v:
            if not k.isdigit() or int(k) < 1:
                raise ValueError(f"Номер волны '{k}' должен быть целым от 1")
        return v


class M3ChecklistToggle(BaseModel):
    done: bool


class M3ChecklistStepOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    object_id: uuid.UUID | None
    step_text: str
    line: int | None
    step_type: str
    wave: int
    needs_budget: bool
    done: bool
    done_at: datetime | None


# ── Админка ───────────────────────────────────────────────────────────────────
class M3ItemUpsert(BaseModel):
    code: str = Field(min_length=2, max_length=4)
    block: Literal["Р", "Н", "А"]
    number: int = Field(ge=1, le=8)
    line: int = Field(ge=1, le=6)
    text: str = Field(min_length=1)
    is_reverse: bool = False
    industry_id: int | None = Field(default=None, ge=1, le=18)


class M3WeightUpsert(BaseModel):
    industry_id: int = Field(ge=1, le=18)
    name: str = Field(min_length=1, max_length=120)
    w_l1: int = Field(ge=0, le=100)
    w_l2: int = Field(ge=0, le=100)
    w_l3: int = Field(ge=0, le=100)
    w_l4: int = Field(ge=0, le=100)
    w_l5: int = Field(ge=0, le=100)
    w_l6: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def check_axes(self):
        if self.w_l1 + self.w_l2 + self.w_l3 != 100:
            raise ValueError("Веса конкурентной силы (Л1+Л2+Л3) должны давать 100")
        if self.w_l4 + self.w_l5 + self.w_l6 != 100:
            raise ValueError("Веса привлекательности (Л4+Л5+Л6) должны давать 100")
        return self


class M3ContentUpsert(BaseModel):
    # zone_reduced: версия блока зоны для одиночного режима. Без него
    # админка упиралась бы в 422 ровно на тех записях, ради которых
    # экран и делается.
    kind: Literal["zone", "zone_reduced", "weak_line",
                  "strong_line", "tension"]
    key: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    mistake: str | None = None
    industry_id: int | None = Field(default=None, ge=1, le=18)
    # Флажок «Активно» в админке. Раньше PUT всегда ставил True,
    # и выключить блок из интерфейса было нельзя.
    is_active: bool = True


class M3HintUpsert(BaseModel):
    industry_id: int = Field(ge=1, le=18)
    item_code: str = Field(min_length=2, max_length=4)
    text: str = Field(min_length=1)
