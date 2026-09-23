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
    is_effect:       Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    sort:            Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:       Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    module_code: Mapped[int] = mapped_column(SmallInteger, ForeignKey("m4_modules.code", ondelete="RESTRICT"), nullable=False, index=True)
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
    unknown_allowed:            Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    unknown_score:              Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    unknown_confidence_penalty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")

    metric_code:     Mapped[str | None] = mapped_column(String(48), nullable=True)
    threshold_based: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    control_pair:    Mapped[str | None] = mapped_column(String(8), nullable=True)
    applies_when:    Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    construct_code:  Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    source_ref:      Mapped[str | None] = mapped_column(Text, nullable=True)

    item_version: Mapped[int]  = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sort:         Mapped[int]  = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    is_active:    Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("m4_questions.id", ondelete="CASCADE"), nullable=False, index=True)
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
