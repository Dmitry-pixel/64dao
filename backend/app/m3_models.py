# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — модели данных.

Отдельный модуль, а не дописывание в models.py: Метод 3 — изолированный
раздел с собственным роутером и собственными таблицами, и держать его схему
рядом с общими моделями значит расширять файл, который импортируют все
остальные методы. Регистрация в общей Base.metadata — импортом в models.py,
поэтому create_all в тестах и autogenerate в alembic видят эти таблицы.

Все таблицы с префиксом m3_. Модели, роутеры и маршрутизацию Методов 1 и 2
этот модуль не трогает.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ── Портфель и направления ────────────────────────────────────────────────────
class M3Portfolio(Base):
    """Портфель направлений. Единица анализа Метода 3 — направление бизнеса,
    но диагностика всегда идёт по портфелю целиком: метод отвечает на вопрос
    «между чем и чем распределять ресурс»."""

    __tablename__ = "m3_portfolios"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Название компании вводится ПЕРЕД диагностикой, как в Методах 1 и 2,
    # и не берётся из профиля: профиль может измениться после выдачи отчёта,
    # а отчёт обязан остаться воспроизводимым. Отдельно от title: портфель
    # может называться «Продуктовые направления 2026», компания — иначе.
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status:      Mapped[str]       = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    # Блок Р: шесть рыночных пунктов, заполняются один раз на портфель.
    # Хранятся в m3_answers с object_id IS NULL — здесь только порядок,
    # названный собственником, для критерия 3 пилота.
    owner_ranks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # См. Assessment.deleted_at: удаление скрывает запись, но факт расчёта
    # остаётся — иначе удаление возвращало бы оплаченную диагностику.
    deleted_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Чем оплачен расчёт. Симметрично assessments.order_id / grant_id:
    # расход считается по факту привязки, а не счётчиком, поэтому возврат
    # заказа возвращает квоту сам и счётчик не может разойтись с фактом.
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    grant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("access_grants.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint("status IN ('draft','filled','calculated')", name="chk_m3_portfolio_status"),
    )

    objects: Mapped[list["M3Object"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan",
        order_by="M3Object.position",
    )


class M3Object(Base):
    """Направление бизнеса: продукт, СБЕ, сегмент или канал.

    Ограничение 3–8 направлений проверяется в сервисе, а не в БД: направления
    добавляются по одному, и БД-констрейнт запрещал бы промежуточное состояние
    формы, где их пока два."""

    __tablename__ = "m3_objects"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    position:     Mapped[int]       = mapped_column(SmallInteger, nullable=False)
    name:         Mapped[str]       = mapped_column(String(255), nullable=False)

    # Числовые якоря (§6 спецификации): данные, которые респондент знает точно.
    revenue:          Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    revenue_dynamics: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    revenue_share:    Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    profitability:    Mapped[str]  = mapped_column(String(20), nullable=False, default="unknown", server_default="unknown")

    # Переопределяет отраслевой пресет портфеля: портфель из производства,
    # e-commerce и обучения охватывает три разные отрасли, и единый пресет
    # на весь портфель исказил бы оценку (§7).
    industry_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Скрининги (§3). На расчёт не влияют — управляют показом блока Р*
    # на фронте. Источником значения линии является наличие ответа.
    screening_price:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    screening_market: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_new_venture:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "position", name="uq_m3_object_position"),
        CheckConstraint(
            "profitability IN ('profitable','marginal','unprofitable','unknown')",
            name="chk_m3_object_profitability",
        ),
        CheckConstraint("position >= 1 AND position <= 8", name="chk_m3_object_position_range"),
        CheckConstraint(
            "revenue_share IS NULL OR (revenue_share >= 0 AND revenue_share <= 100)",
            name="chk_m3_object_share",
        ),
    )

    portfolio: Mapped["M3Portfolio"] = relationship(back_populates="objects")


# ── Анкета ────────────────────────────────────────────────────────────────────
class M3Item(Base):
    """Пункт анкеты. Слоистая сборка: industry_id IS NULL — общий слой,
    отраслевая версия его замещает (§13). item_version обязателен: правка
    формулировки делает старые отчёты несопоставимыми с новыми, и без версии
    модуль динамики отнесёт расхождение баллов к изменениям в бизнесе."""

    __tablename__ = "m3_items"

    id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    block:   Mapped[str] = mapped_column(String(1), nullable=False)     # Р | Н | А (кириллица)
    number:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    code:    Mapped[str] = mapped_column(String(4), nullable=False)     # 'Р1', 'Р1*', 'Н5', 'А2'
    line:    Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text:    Mapped[str] = mapped_column(Text, nullable=False)
    is_reverse:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    industry_id:  Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    item_version: Mapped[int]  = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active:    Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("code", "industry_id", "item_version", name="uq_m3_item_version"),
        CheckConstraint("block IN ('Р','Н','А')", name="chk_m3_item_block"),
        CheckConstraint("line >= 1 AND line <= 6", name="chk_m3_item_line"),
    )


class M3Hint(Base):
    """Отраслевая подсказка уровня 2: пример под пунктом, текст пункта
    не трогается, сопоставимость баллов не страдает (§13)."""

    __tablename__ = "m3_hints"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    industry_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    item_code:   Mapped[str] = mapped_column(String(4), nullable=False)
    text:        Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("industry_id", "item_code", name="uq_m3_hint"),
    )


class M3Answer(Base):
    """Ответ. object_id IS NULL — блок Р, уровень портфеля.
    value IS NULL — «не знаю»."""

    __tablename__ = "m3_answers"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_objects.id", ondelete="CASCADE"), nullable=True, index=True)
    item_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_items.id", ondelete="CASCADE"), nullable=False)
    item_code:    Mapped[str] = mapped_column(String(4), nullable=False)
    value:        Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("portfolio_id", "object_id", "item_id", name="uq_m3_answer"),
        CheckConstraint("value IS NULL OR (value >= 1 AND value <= 4)", name="chk_m3_answer_value"),
    )


# ── Справочники ───────────────────────────────────────────────────────────────
class M3Weight(Base):
    """Отраслевой пресет весов. Дублирует DEFAULT_M3_CONFIG намеренно:
    админка правит строки в БД, конфиг в коде остаётся дефолтом на случай
    пустой таблицы. Внутри каждой оси веса суммируются в 100."""

    __tablename__ = "m3_weights"

    industry_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name:  Mapped[str] = mapped_column(String(120), nullable=False)
    w_l1:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    w_l2:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    w_l3:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    w_l4:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    w_l5:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    w_l6:  Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("w_l1 + w_l2 + w_l3 = 100", name="chk_m3_weights_strength"),
        CheckConstraint("w_l4 + w_l5 + w_l6 = 100", name="chk_m3_weights_attract"),
    )


class M3Hexagram(Base):
    """Код -> номер Вэнь-вана и название 64DAO. Номер — идентификатор
    конфигурации шести линий, не отсылка к традиции: название выводится
    после номера и зоны и в трактовке не участвует (§15)."""

    __tablename__ = "m3_hexagrams"

    code:       Mapped[str] = mapped_column(String(6), primary_key=True)
    kw_number:  Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True)
    name_64dao: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (
        CheckConstraint(r"code ~ '^[AB]{6}$'", name="chk_m3_hexagram_code"),
        CheckConstraint("kw_number >= 1 AND kw_number <= 64", name="chk_m3_hexagram_number"),
    )


class M3Content(Base):
    """31 блок вместо 64 уникальных разборов: 9 зон + 6 слабых линий +
    6 сильных + 10 напряжений. Каждый блок выбирается детерминированно,
    одинаковая конфигурация даёт одинаковый разбор (§15)."""

    __tablename__ = "m3_content"

    id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    kind:  Mapped[str] = mapped_column(String(20), nullable=False)
    key:   Mapped[str] = mapped_column(String(20), nullable=False)   # 'high_low', 'weak_L3', 'P4'
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body:  Mapped[str] = mapped_column(Text, nullable=False)
    # Типичная ошибка — только у блоков зоны, замыкает разбор.
    mistake:     Mapped[str | None] = mapped_column(Text, nullable=True)
    industry_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_active:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        UniqueConstraint("kind", "key", "industry_id", name="uq_m3_content"),
        CheckConstraint(
            "kind IN ('zone','zone_reduced','weak_line','strong_line','tension')",
            name="chk_m3_content_kind",
        ),
    )


# ── Результаты ────────────────────────────────────────────────────────────────
class M3Result(Base):
    """Снимок расчёта по направлению. item_versions обязателен: без него
    правка формулировки пункта сделает старые отчёты несопоставимыми
    с новыми, и модуль динамики начнёт врать."""

    __tablename__ = "m3_results"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_objects.id", ondelete="CASCADE"), nullable=False, index=True)

    l1: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    l2: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    l3: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    l4: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    l5: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    l6: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)

    symbols:  Mapped[str]  = mapped_column(String(6), nullable=False)
    mobility: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Отраслевые веса, по которым считались ячейка и координата. Хранятся,
    # а не пересчитываются по industry_id: пресеты правятся в админке, и
    # пересчёт менял бы старые отчёты задним числом. Nullable — у снимков
    # до ревизии 030 весов нет, такие отчёты не печатают вывод ячейки.
    weights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    cell_strength: Mapped[str] = mapped_column(String(4), nullable=False)
    cell_attract:  Mapped[str] = mapped_column(String(4), nullable=False)
    coord_strength: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    coord_attract:  Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)

    current_hex:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_hex:   Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    target_lines: Mapped[list | None] = mapped_column(ARRAY(SmallInteger), nullable=True)
    risk_hex:     Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    risk_lines:   Mapped[list | None] = mapped_column(ARRAY(SmallInteger), nullable=True)

    v_index: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    z_index: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    v_rank:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    z_rank:  Mapped[int] = mapped_column(SmallInteger, nullable=False)

    weak_line:   Mapped[int] = mapped_column(SmallInteger, nullable=False)
    strong_line: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tensions:    Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    flags:       Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    item_versions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("portfolio_id", "object_id", name="uq_m3_result"),
        CheckConstraint(r"symbols ~ '^[AB]{6}$'", name="chk_m3_result_symbols"),
        CheckConstraint("cell_strength IN ('low','mid','high')", name="chk_m3_result_cell_s"),
        CheckConstraint("cell_attract IN ('low','mid','high')", name="chk_m3_result_cell_a"),
    )


class M3PortfolioResult(Base):
    """Портфельный слой. verdicts_held: при любом портфельном флаге отчёт
    отдаёт диагноз и маршруты, но не отдаёт вердикты аллокации."""

    __tablename__ = "m3_portfolio_results"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_portfolios.id", ondelete="CASCADE"), primary_key=True)
    sum_positions:  Mapped[int] = mapped_column(SmallInteger, nullable=False)
    turbulence:     Mapped[int] = mapped_column(SmallInteger, nullable=False)
    delta:          Mapped[int] = mapped_column(SmallInteger, nullable=False)
    distinct_cells: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    spearman:       Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    flags:          Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    verdicts_held:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Портфельный слой не считался: направлений меньше portfolio_min.
    # Хранится в снимке, а не выводится из числа объектов при сборке
    # отчёта: порог правится в конфиге, и старые отчёты поехали бы.
    reduced: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                          default=False, server_default="false")
    created_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class M3TradeoffDecision(Base):
    """Решение по волнам. Объект системы, а не строка в переписке: без него
    модуль динамики через полгода истолкует неизменившееся направление
    как невыполнение рекомендаций, а не как исполнение принятого плана (§17)."""

    __tablename__ = "m3_tradeoff_decisions"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    decided_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_option: Mapped[str] = mapped_column(String(10), nullable=False)
    waves:           Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cost_accepted:   Mapped[str | None] = mapped_column(Text, nullable=True)
    review_triggers: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)

    __table_args__ = (
        CheckConstraint("accepted_option IN ('method','custom')", name="chk_m3_tradeoff_option"),
    )


class M3ChecklistStep(Base):
    """Шаг чек-листа. Подготовительный шаг не учитывается в правиле такта
    (не более двух направлений в активной трансформации): его результат —
    знание или решение, а не изменение конфигурации линий (§17)."""

    __tablename__ = "m3_checklist"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("m3_objects.id", ondelete="CASCADE"), nullable=True, index=True)
    step_text: Mapped[str] = mapped_column(Text, nullable=False)
    line:      Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    step_type: Mapped[str] = mapped_column(String(10), nullable=False)
    wave:      Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    needs_budget: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    done:      Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    done_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "step_type IN ('route','hold','prep','decision')",
            name="chk_m3_checklist_type",
        ),
    )
