# -*- coding: utf-8 -*-
"""
Резолвер базовых вопросов Метода 1: дефолты из кода + переопределения из БД.

Тексты редактируются в админке (/admin/fin-content, вид «Базовые вопросы») и
хранятся в fin_content: kind='base_question', key='q1'..'q6', contour='common'.

Код остаётся источником значений по умолчанию. Если строки в БД нет, она
выключена или в ней нет нужного поля — берётся дефолт из app.method1_questions.
Анкета и отчёты не ломаются даже при пустой таблице.

Поля lc_* больше не читаются из strategies: они вычисляются из комбинации и
актуальных текстов (lc_values), поэтому не устаревают после правки в админке.
"""
from __future__ import annotations

from app.method1_questions import BASE_QUESTIONS as DEFAULT_QUESTIONS

KIND = "base_question"
KEYS: tuple[str, ...] = tuple(f"q{i}" for i in range(1, 7))

# Что можно править в админке. lc_key и label — структура, правке не подлежат:
# lc_key связывает вопрос с полем отчёта, порядок вопросов = порядок линий.
EDITABLE_FIELDS: tuple[str, ...] = ("q", "help", "a", "b", "a_full", "b_full")
STRUCTURAL_FIELDS: tuple[str, ...] = ("lc_key", "label")


def key_for(index: int) -> str:
    """q1..q6 по индексу 0..5."""
    return KEYS[index]


def index_of(key: str) -> int:
    return KEYS.index(key)


def default_payload(index: int) -> dict:
    """Payload вопроса по умолчанию — ровно то, что лежит в коде."""
    return dict(DEFAULT_QUESTIONS[index])


def merge_rows(rows: list) -> list[dict]:
    """Наложить строки fin_content поверх дефолтов.

    rows: объекты с полями key/payload/is_active (или словари). Неизвестные
    ключи игнорируются, выключенные строки не применяются, пустые строки
    payload не затирают дефолт.
    """
    by_key: dict[str, dict] = {}
    for r in rows or []:
        key = r.get("key") if isinstance(r, dict) else getattr(r, "key", None)
        payload = r.get("payload") if isinstance(r, dict) else getattr(r, "payload", None)
        active = r.get("is_active") if isinstance(r, dict) else getattr(r, "is_active", True)
        if key not in KEYS or not isinstance(payload, dict) or not active:
            continue
        by_key[key] = payload

    out: list[dict] = []
    for i in range(len(DEFAULT_QUESTIONS)):
        q = default_payload(i)
        payload = by_key.get(key_for(i)) or {}
        for f in EDITABLE_FIELDS:
            v = payload.get(f)
            if isinstance(v, str) and v.strip():
                q[f] = v.strip()
        out.append(q)
    return out


async def load_questions(session) -> list[dict]:
    """Актуальные тексты вопросов: БД поверх дефолтов. Ошибка БД — не повод
    ронять отчёт, поэтому при любой проблеме возвращаются дефолты."""
    try:
        from sqlalchemy import select

        from app.models import FinContent

        rows = (await session.execute(
            select(FinContent).where(
                FinContent.kind == KIND,
                FinContent.contour == "common",
            )
        )).scalars().all()
        return merge_rows(list(rows))
    except Exception:
        return [default_payload(i) for i in range(len(DEFAULT_QUESTIONS))]


def lc_values(combination: str | None, questions: list[dict] | None = None) -> dict[str, str]:
    """Значения блоков жизненного цикла по комбинации.

    Буква A -> развёрнутый ответ A, B -> развёрнутый ответ B.
    Возвращает {lc_key: текст}. Пустая или короткая комбинация -> пустой словарь.
    """
    qs = questions or [default_payload(i) for i in range(len(DEFAULT_QUESTIONS))]
    if not combination or len(combination) < len(qs):
        return {}
    out: dict[str, str] = {}
    for i, q in enumerate(qs):
        letter = combination[i]
        if letter not in ("A", "B"):
            continue
        out[q["lc_key"]] = q["a_full"] if letter == "A" else q["b_full"]
    return out


def lifecycle_description(combination: str | None, questions: list[dict] | None = None) -> str:
    """Сводный текст жизненного цикла — тот же формат, что писал seed_lifecycle."""
    qs = questions or [default_payload(i) for i in range(len(DEFAULT_QUESTIONS))]
    if not combination or len(combination) < len(qs):
        return ""
    lines = []
    for i, q in enumerate(qs):
        ans = q["a_full"] if combination[i] == "A" else q["b_full"]
        lines.append(f"{i + 1}. {q['label']} – {ans}.")
    return "\n".join(lines)


# ── Защита от переворота смысла ──────────────────────────────────────────────
# Формулировки править можно, менять ответы местами — нельзя: буква A всегда
# даёт линию Ян, B — Инь, и от этого зависит, какая из 64 гексаграмм подберётся.
# Ровно эта ошибка однажды уже привела к подбору не той гексаграммы.

def normalize(text: str) -> str:
    """Огрубление текста для сравнения: регистр, пробелы и пунктуация не в счёт."""
    if not isinstance(text, str):
        return ""
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower())
    return " ".join(cleaned.split())


class BaseQuestionEditError(ValueError):
    """Правка базового вопроса отклонена."""


def validate_edit(key: str, contour: str, payload: dict, current: dict | None = None) -> None:
    """Проверить правку базового вопроса. Бросает BaseQuestionEditError.

    current — payload, который лежит сейчас (для новых строк можно не передавать,
    тогда сравнение идёт с дефолтом из кода).
    """
    if key not in KEYS:
        raise BaseQuestionEditError(
            f"Ключ вопроса должен быть одним из: {', '.join(KEYS)}"
        )
    if contour != "common":
        raise BaseQuestionEditError("Базовые вопросы не переопределяются по контурам")
    if not isinstance(payload, dict):
        raise BaseQuestionEditError("Некорректный формат данных")

    base = dict(default_payload(index_of(key)))
    if current:
        base.update({k: v for k, v in current.items() if isinstance(v, str)})

    for field in STRUCTURAL_FIELDS:
        if field in payload and str(payload[field]).strip() != str(base[field]).strip():
            raise BaseQuestionEditError(
                f"Поле «{field}» задаёт структуру расчёта и не редактируется"
            )

    for field in EDITABLE_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise BaseQuestionEditError(f"Поле «{field}» не может быть пустым")

    # Переворот: новый ответ A совпал с нынешним ответом B (или наоборот).
    for a_field, b_field in (("a", "b"), ("a_full", "b_full")):
        new_a = normalize(payload.get(a_field, ""))
        new_b = normalize(payload.get(b_field, ""))
        cur_a = normalize(base.get(a_field, ""))
        cur_b = normalize(base.get(b_field, ""))
        if new_a and cur_b and new_a == cur_b:
            raise BaseQuestionEditError(
                "Ответы А и Б нельзя менять местами: ответ А всегда даёт линию Ян, "
                "Б — Инь, и от этого зависит подбор гексаграммы. "
                "Меняйте формулировку, не переставляя стороны."
            )
        if new_b and cur_a and new_b == cur_a:
            raise BaseQuestionEditError(
                "Ответы А и Б нельзя менять местами: ответ Б всегда даёт линию Инь. "
                "Меняйте формулировку, не переставляя стороны."
            )
