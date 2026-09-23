# -*- coding: utf-8 -*-
"""
Метод 4 «Алмазное колесо» — модели данных.

Отдельный модуль по тем же причинам, что и m3_models: изолированный раздел
со своим роутером и своими таблицами. Регистрация в общей Base.metadata —
импортом в models.py, иначе create_all в тестах и autogenerate в alembic
таблиц m4_* не увидят.

Все таблицы с префиксом m4_.

Главный принцип схемы: контент правится в админке, логика живёт в коде.
Тексты вопросов, варианты ответов, баллы вариантов и тексты карточек —
редактируемые поля. Коды вопросов и значения вариантов — структурные: на них
ссылаются правила противоречий и уже сохранённые ответы, и переименование
кода ломает и то и другое.

item_version обязателен по той же причине, что в m3_items: правка
формулировки делает старые отчёты несопоставимыми с новыми, и без версии
модуль динамики отнесёт расхождение баллов к изменениям в бизнесе.
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ── Модули колеса ─────────────────────────────────────────────────────────────
class M4Module(Base):
    """Десять модулей колеса. Модуль 10 «Финансы» помечен is_effect: он
    следствие решений в остальных девяти и системным ограничением не бывает —
    это проверяется при расчёте, а не только описано в документации."""

    __tablename__ = "m4_modules"

    code:            Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    slug:            Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name:            Mapped[str] = mapped_column(String(128), nullable=False)
    client_question: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters:  Mapped[str] = mapped_column(Text, nullable=False)
    intro:           Mapped[str | None] = mapped_column(Text, nullable=True)       # абзац перед вопросами модуля
    is_effect:       Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    sort:            Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:       Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    questions: Mapped[list["M4Question"]] = relationship(back_populates="module")

    __table_args__ = (
        CheckConstraint("code >= 1 AND code <= 10", name="chk_m4_module_code"),
    )


# ── Банк вопросов ─────────────────────────────────────────────────────────────
class M4Question(Base):
    """Вопрос анкеты.

    Правится в админке: text, weight, tier, sort, is_active.
    Структурное, меняется с предупреждением: type, module_code, reverse,
    поведение «Не знаю».
    Не правится: code — на него ссылаются правила, цепочки и сохранённые ответы.

    score_excluded + affects: вопрос собирается, но в балл модуля не идёт.
    Сейчас так работают два вопроса о сопротивлении изменениям — они дают
    множитель формулы приоритизации, и если их пустить ещё и в балл модуля,
    один ответ учтётся дважды.

    source_ref виден только администратору. В клиентский вывод он не уходит
    никогда — это проверяет валидатор контента и должен проверять тест.
    """

    __tablename__ = "m4_questions"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    code:        Mapped[str] = mapped_column(String(8), nullable=False, unique=True)   # 'M04-Q01'
    module_code: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("m4_modules.code", ondelete="RESTRICT"), nullable=False, index=True,
    )
    text:        Mapped[str] = mapped_column(Text, nullable=False)
    type:        Mapped[str] = mapped_column(String(8), nullable=False)                # bool|scale3|choice|number|money
    unit:        Mapped[str | None] = mapped_column(String(32), nullable=True)
    weight:      Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    is_fact:     Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    tier:        Mapped[str] = mapped_column(String(2), nullable=False)                # u0|u1

    reverse:        Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    score_neutral:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    score_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    affects:        Mapped[str | None] = mapped_column(String(24), nullable=True)      # prioritization

    # Поведение варианта «Не знаю». unknown_allowed=false — вариант не показывается.
    # unknown_score задан — незнание идёт в балл как число, и тогда штраф
    # достоверности обнуляется: иначе один ответ считается дважды.
    unknown_allowed:            Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
    )
    unknown_score:              Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    unknown_confidence_penalty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")

    metric_code:     Mapped[str | None] = mapped_column(String(48), nullable=True)
    threshold_based: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    control_pair:    Mapped[str | None] = mapped_column(String(8), nullable=True)
    applies_when:    Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    construct_code:  Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    source_ref:      Mapped[str | None] = mapped_column(Text, nullable=True)
    min_value:       Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_value:       Mapped[int | None] = mapped_column(Integer, nullable=True)
    note_internal:   Mapped[str | None] = mapped_column(Text, nullable=True)            # только для админки

    item_version: Mapped[int]  = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sort:         Mapped[int]  = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:    Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    module:  Mapped["M4Module"] = relationship(back_populates="questions")
    options: Mapped[list["M4QuestionOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="M4QuestionOption.sort"
    )

    __table_args__ = (
        CheckConstraint("type IN ('bool','scale3','choice','number','money')", name="chk_m4_question_type"),
        CheckConstraint("tier IN ('u0','u1')", name="chk_m4_question_tier"),
        CheckConstraint("weight >= 1 AND weight <= 3", name="chk_m4_question_weight"),
        CheckConstraint("unknown_score IS NULL OR (unknown_score >= 0 AND unknown_score <= 100)",
                        name="chk_m4_question_unknown_score"),
        # «Не знаю» отключён — значит и балла у него быть не может.
        CheckConstraint("unknown_allowed OR unknown_score IS NULL",
                        name="chk_m4_question_unknown_consistency"),
        # Вопрос влияет на что-то вне балла — он обязан быть исключён из балла.
        CheckConstraint("affects IS NULL OR score_excluded", name="chk_m4_question_affects"),
        CheckConstraint("min_value IS NULL OR max_value IS NULL OR min_value <= max_value",
                        name="chk_m4_question_min_max"),
    )


class M4QuestionOption(Base):
    """Вариант ответа для типа choice.

    Правится: label, score, sort. Не правится: value — на него ссылаются
    условия правил и сохранённые ответы.

    Варианта «Не знаю» здесь нет и быть не должно: его подставляет код по
    полям unknown_* вопроса. Если завести его строкой, он разойдётся между
    вопросами — где-то с баллом, где-то без, где-то с другой подписью.
    """

    __tablename__ = "m4_question_options"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("m4_questions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    value:       Mapped[str] = mapped_column(String(32), nullable=False)
    label:       Mapped[str] = mapped_column(Text, nullable=False)
    score:       Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    sort:        Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")

    question: Mapped["M4Question"] = relationship(back_populates="options")

    __table_args__ = (
        UniqueConstraint("question_id", "value", name="uq_m4_option_value"),
        CheckConstraint("value <> 'unknown'", name="chk_m4_option_not_unknown"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="chk_m4_option_score"),
    )


# ── Карточки отчёта ───────────────────────────────────────────────────────────
class M4Card(Base):
    """Текстовая карточка отчёта. Пять видов:

    module_state      — состояние модуля по баллу, ключ m01_low … m10_high;
    module_constraint — что значит, что модуль стал системным ограничением;
    recommendation    — рекомендация: по состоянию модуля (m01_low…) или по
                        правилу противоречия (cr_CR-01…);
    dynamics          — изменение относительно прошлой диагностики;
    confidence        — режим отчёта по индексу достоверности.

    Правится в админке всё, кроме kind и key: по этой паре код выбирает
    карточку. effect, speed_weeks и cost — входы формулы приоритизации,
    поэтому у рекомендации они обязательны на уровне базы.
    """

    __tablename__ = "m4_cards"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    kind:         Mapped[str] = mapped_column(String(24), nullable=False)
    key:          Mapped[str] = mapped_column(String(24), nullable=False)
    module_code:  Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("m4_modules.code", ondelete="RESTRICT"), nullable=True, index=True,
    )
    state:        Mapped[str | None] = mapped_column(String(4), nullable=True)
    rule_code:    Mapped[str | None] = mapped_column(
        String(8), ForeignKey("m4_rules.code", ondelete="RESTRICT"), nullable=True, index=True,
    )
    title:        Mapped[str] = mapped_column(String(160), nullable=False)
    body:         Mapped[str] = mapped_column(Text, nullable=False)
    mistake:      Mapped[str | None] = mapped_column(Text, nullable=True)
    steps:        Mapped[list | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    first_step:   Mapped[str | None] = mapped_column(Text, nullable=True)
    how_to_check: Mapped[str | None] = mapped_column(Text, nullable=True)
    effect:       Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    speed_weeks:  Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    cost:         Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    item_version: Mapped[int]  = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sort:         Mapped[int]  = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:    Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("kind", "key", name="uq_m4_card_kind_key"),
        CheckConstraint(
            "kind IN ('module_state','module_constraint','recommendation','dynamics','confidence')",
            name="chk_m4_card_kind"),
        CheckConstraint("state IS NULL OR state IN ('low','mid','high')", name="chk_m4_card_state"),
        CheckConstraint("effect IS NULL OR (effect >= 1 AND effect <= 3)", name="chk_m4_card_effect"),
        CheckConstraint("cost IS NULL OR (cost >= 1 AND cost <= 3)", name="chk_m4_card_cost"),
        CheckConstraint("speed_weeks IS NULL OR (speed_weeks >= 1 AND speed_weeks <= 104)",
                        name="chk_m4_card_speed"),
        # Без трёх оценок рекомендацию нельзя поставить в очередь действий.
        CheckConstraint(
            "kind <> 'recommendation' OR "
            "(effect IS NOT NULL AND speed_weeks IS NOT NULL AND cost IS NOT NULL)",
            name="chk_m4_card_reco_scores"),
        # Рекомендация привязана ровно к одному: к модулю или к правилу.
        CheckConstraint(
            "kind <> 'recommendation' OR ((module_code IS NULL) <> (rule_code IS NULL))",
            name="chk_m4_card_reco_target"),
        CheckConstraint("steps IS NULL OR jsonb_typeof(steps) = 'array'", name="chk_m4_card_steps"),
    )


# ── Правила противоречий ──────────────────────────────────────────────────────
class M4Rule(Base):
    """Правило противоречия: два управленческих решения, разумных по
    отдельности и мешающих друг другу вместе.

    Правятся в админке: title, severity, diagnosis, what_happens, fix_one_of,
    cost_of_inaction, is_active. conditions — структурное поле: это условие
    срабатывания, в админке оно только для чтения. Правка условия — правка
    логики, она идёт через код и поднимает rule_version.

    source_ref, как у вопросов, виден только администратору.
    """

    __tablename__ = "m4_rules"

    code:             Mapped[str] = mapped_column(String(8), primary_key=True)      # 'CR-01'
    title:            Mapped[str] = mapped_column(String(160), nullable=False)
    severity:         Mapped[str] = mapped_column(String(8), nullable=False)
    conditions:       Mapped[dict] = mapped_column(JSONB, nullable=False)
    diagnosis:        Mapped[str] = mapped_column(Text, nullable=False)
    what_happens:     Mapped[str] = mapped_column(Text, nullable=False)
    fix_one_of:       Mapped[list] = mapped_column(JSONB, nullable=False)
    cost_of_inaction: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref:       Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mvp:           Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    rule_version:     Mapped[int]  = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sort:             Mapped[int]  = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:        Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("severity IN ('high','medium','low')", name="chk_m4_rule_severity"),
        CheckConstraint("jsonb_typeof(conditions) = 'object'", name="chk_m4_rule_conditions"),
        CheckConstraint("jsonb_typeof(fix_one_of) = 'array'", name="chk_m4_rule_fix"),
    )


# ── Цепочки симптомов ─────────────────────────────────────────────────────────
class M4SymptomChain(Base):
    """Обратная трассировка: симптом, который видит собственник, → цепочка
    причин → модули-корни → вопросы для проверки → первое действие.

    Правятся: label, chain, first_action, note, is_active. Структурные:
    detected_by, root_modules, check_questions — на них опирается расчёт.
    """

    __tablename__ = "m4_symptom_chains"

    code:            Mapped[str] = mapped_column(String(40), primary_key=True)
    label:           Mapped[str] = mapped_column(String(160), nullable=False)
    detected_by:     Mapped[list] = mapped_column(JSONB, nullable=False)
    chain:           Mapped[list] = mapped_column(JSONB, nullable=False)
    root_modules:    Mapped[list] = mapped_column(JSONB, nullable=False)
    check_questions: Mapped[list] = mapped_column(JSONB, nullable=False)
    first_action:    Mapped[str] = mapped_column(Text, nullable=False)
    note:            Mapped[str | None] = mapped_column(Text, nullable=True)
    sort:            Mapped[int]  = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:       Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(detected_by) = 'array' AND jsonb_typeof(chain) = 'array' "
            "AND jsonb_typeof(root_modules) = 'array' AND jsonb_typeof(check_questions) = 'array'",
            name="chk_m4_chain_arrays"),
    )


# ── Реестр конструктов ────────────────────────────────────────────────────────
class M4Construct(Base):
    """Конструкт — то, что метод пытается узнать, независимо от формулировки
    и метода: «цену поднимали и проверили реакцию клиентов», «компания
    работает без ручного участия первого лица».

    Зачем: не спрашивать одно и то же дважды (reusable) и сверять ответы
    Метода 3 и Метода 4 на один вопрос (cross_check). Расхождение ответов —
    повод уточнить, а не обвинение в неискренности.

    unit — уровень, на котором конструкт измеряется: компания, направление
    портфеля или функция. Ответ по направлению нельзя подставить в вопрос о
    компании, кроме случая одного направления.

    Правятся: name, note, cross_check_why, reusable, cross_check, is_active.
    Не правится: code — на него ссылаются вопросы и связи.
    """

    __tablename__ = "m4_constructs"

    code:            Mapped[str] = mapped_column(String(48), primary_key=True)
    name:            Mapped[str] = mapped_column(String(200), nullable=False)
    unit:            Mapped[str] = mapped_column(String(12), nullable=False)
    reusable:        Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    cross_check:     Mapped[str | None] = mapped_column(String(24), nullable=True)
    cross_check_why: Mapped[str | None] = mapped_column(Text, nullable=True)
    note:            Mapped[str | None] = mapped_column(Text, nullable=True)
    sort:            Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:       Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    links: Mapped[list["M4ConstructLink"]] = relationship(
        back_populates="construct", cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("unit IN ('company','direction','function')", name="chk_m4_construct_unit"),
        CheckConstraint(
            "cross_check IS NULL OR cross_check IN ('always','single_direction_only','no')",
            name="chk_m4_construct_cross_check"),
    )


class M4ConstructLink(Base):
    """Связь конструкта с пунктом другого метода.

    Отдельная таблица, а не поле construct_code в чужих таблицах: пункты
    Метода 3 хранятся построчно по версиям и отраслям, а пункты контуров
    живут в коде. Связь по коду пункта переживает и новую версию, и
    отраслевой слой, и не требует менять таблицы Метода 3.

    reverse   — пункт реверсивный, значение инвертируется до сравнения;
    dynamic   — пункт меряет динамику, а не уровень (сверять нельзя);
    free_text — свободный текст, только для справки.
    """

    __tablename__ = "m4_construct_links"

    id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    construct_code: Mapped[str] = mapped_column(
        String(48), ForeignKey("m4_constructs.code", ondelete="CASCADE"), nullable=False, index=True,
    )
    method:         Mapped[str] = mapped_column(String(24), nullable=False)
    item_code:      Mapped[str] = mapped_column(String(48), nullable=False)
    reverse:        Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    dynamic:        Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    free_text:      Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    construct: Mapped["M4Construct"] = relationship(back_populates="links")

    __table_args__ = (
        UniqueConstraint("construct_code", "method", "item_code", name="uq_m4_construct_link"),
        CheckConstraint(
            "method IN ('m1_base','m3','contour_finance','contour_product','contour_process',"
            "'contour_market','ui_bmc')",
            name="chk_m4_construct_link_method"),
    )


# ── Прогоны ───────────────────────────────────────────────────────────────────
class M4Run(Base):
    """Один проход анкеты Метода 4 по одной компании.

    mode:
      express — бесплатный экспресс: 20 вопросов уровня u0, колесо и три
                разрыва. Ничего не списывает, поэтому order_id и grant_id
                пусты; ограничение числа экспрессов — в коде, не в схеме.
      full    — полная диагностика из пакета «Метод 3 + Метод 4». Оплата —
                тот же заказ продукта m3, что и у портфеля Метода 3:
                расход считается по привязке order_id / grant_id, как у
                m3_portfolios и assessments, а не счётчиком.

    m3_portfolio_id — портфель Метода 3 из того же пакета. Нужен для сверки
    ответов по общим конструктам; может быть пуст, если Метод 3 не пройден.

    Повтор — как у assessments: у исходного прогона followup_allowed /
    followup_used, у повторного is_followup и parent_run_id. Счётчик свой у
    Метода 4, общего на пакет нет: повтор Метода 3 и повтор Метода 4
    независимы.

    profile_snapshot и item_versions фиксируются при расчёте: отчёт обязан
    воспроизводиться, даже если профиль компании или формулировки вопросов
    потом поменяют в админке.
    """

    __tablename__ = "m4_runs"

    id:              Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:         Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    company_id:      Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    m3_portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("m3_portfolios.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    mode:            Mapped[str] = mapped_column(String(8), nullable=False)
    status:          Mapped[str] = mapped_column(String(12), nullable=False, default="draft", server_default="draft")

    order_id:        Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    grant_id:        Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("access_grants.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    is_followup:      Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    parent_run_id:    Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("m4_runs.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    followup_allowed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    followup_used:    Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reduced:          Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    profile_snapshot: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    item_versions:    Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)

    created_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Удаление скрывает прогон, но факт расчёта остаётся — иначе удаление
    # возвращало бы оплаченную диагностику. Та же схема, что у m3_portfolios.
    deleted_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    answers:  Mapped[list["M4Answer"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    snapshot: Mapped["M4Snapshot | None"] = relationship(back_populates="run", cascade="all, delete-orphan",
                                                         uselist=False)

    __table_args__ = (
        CheckConstraint("mode IN ('express','full')", name="chk_m4_run_mode"),
        CheckConstraint("status IN ('draft','filled','calculated')", name="chk_m4_run_status"),
        CheckConstraint("followup_used >= 0 AND followup_used <= followup_allowed",
                        name="chk_m4_run_followup_used"),
        # Экспресс бесплатный: привязки к оплате у него быть не может.
        CheckConstraint("mode = 'full' OR (order_id IS NULL AND grant_id IS NULL)",
                        name="chk_m4_run_express_unpaid"),
        # Повтор без исходного прогона — ошибка данных.
        CheckConstraint("NOT is_followup OR parent_run_id IS NOT NULL", name="chk_m4_run_followup_parent"),
    )


class M4Answer(Base):
    """Ответ на вопрос в прогоне.

    value — значение варианта ('yes', 'partial', код варианта choice) или
    'unknown'; numeric_value — число для вопросов number/money. «Не знаю» на
    числовой вопрос — value='unknown' и пустое numeric_value.

    source:
      direct       — ответ дан в этом прогоне;
      carried_over — перенесён из прошлого прогона в сокращённом повторе.
                     Хранится строкой, а не пропуском, иначе балл модуля
                     не пересчитать;
      reused       — подставлен из другого метода по общему конструкту
                     (включается позже, этап 5).

    item_version — версия формулировки вопроса на момент ответа.
    question_code ссылается на m4_questions.code: вопросы не удаляются,
    а выключаются, поэтому ответ не может потерять свой вопрос.
    """

    __tablename__ = "m4_answers"

    id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    run_id:        Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("m4_runs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_code: Mapped[str] = mapped_column(
        String(8), ForeignKey("m4_questions.code", ondelete="RESTRICT"), nullable=False,
    )
    value:         Mapped[str | None] = mapped_column(String(32), nullable=True)
    numeric_value: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    source:        Mapped[str] = mapped_column(String(16), nullable=False, default="direct", server_default="direct")
    item_version:  Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    updated_at:    Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    run: Mapped["M4Run"] = relationship(back_populates="answers")

    __table_args__ = (
        UniqueConstraint("run_id", "question_code", name="uq_m4_answer"),
        CheckConstraint("value IS NOT NULL OR numeric_value IS NOT NULL", name="chk_m4_answer_present"),
        CheckConstraint("source IN ('direct','carried_over','reused')", name="chk_m4_answer_source"),
    )


class M4Snapshot(Base):
    """Рассчитанный результат прогона — единственный источник для веба и PDF.

    Подавление разделов в сокращённом прогоне ставится здесь, при сборке
    снимка, а не в рендерах: иначе веб и PDF разойдутся. Снимок пишется один
    раз при расчёте и задним числом не пересчитывается.

    calc_version — версия движка расчёта: при изменении формулы старые
    снимки остаются посчитанными по старой и это видно.
    """

    __tablename__ = "m4_snapshots"

    run_id:                Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("m4_runs.id", ondelete="CASCADE"), primary_key=True,
    )
    calc_version:          Mapped[str] = mapped_column(String(16), nullable=False)
    module_scores:         Mapped[dict] = mapped_column(JSONB, nullable=False)
    constraint_module:     Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    fired_rules:           Mapped[list] = mapped_column(JSONB, nullable=False)
    unverified_rules:      Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence_index:      Mapped[int] = mapped_column(SmallInteger, nullable=False)
    confidence_components: Mapped[dict] = mapped_column(JSONB, nullable=False)
    resistance_factor:     Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    priority_queue:        Mapped[list] = mapped_column(JSONB, nullable=False)
    cross_check:           Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    reduced:               Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at:            Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["M4Run"] = relationship(back_populates="snapshot")

    __table_args__ = (
        CheckConstraint("constraint_module IS NULL OR (constraint_module >= 1 AND constraint_module <= 9)",
                        name="chk_m4_snapshot_constraint_module"),
        CheckConstraint("confidence_index >= 0 AND confidence_index <= 100", name="chk_m4_snapshot_confidence"),
        CheckConstraint("resistance_factor >= 1.0 AND resistance_factor <= 2.0",
                        name="chk_m4_snapshot_resistance"),
    )
