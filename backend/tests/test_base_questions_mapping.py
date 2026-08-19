# -*- coding: utf-8 -*-
"""
Единственность источника и согласованность 6 базовых вопросов Метода 1.

Эталон — app/method1_questions.BASE_QUESTIONS. Всё остальное обязано совпадать
с ним или брать его напрямую. Рассинхрон второго вопроса приводил к тому, что
линия 2 комбинации формировалась противоположно замыслу и подбиралась не та
гексаграмма из 64.

Утверждённая ориентация: A = Ян = «Быстрый последователь», B = Инь = «Первопроходец».

Тест не требует БД. Фронтовые файлы проверяются, только если доступны:
внутри backend-контейнера их нет, проверки пропускаются.
"""
import re
from pathlib import Path

import pytest

from app.method1_questions import (
    ANSWERS,
    BASE_QUESTIONS,
    LC_FIELDS,
    LC_LABELS,
    QUESTION_LABELS,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

FRONTEND_SOURCES = {
    "анкета": ("frontend/src/app/assessment/page.tsx", "full"),
    "веб-отчёт": ("frontend/src/app/report/[id]/page.tsx", "short"),
    "админка": ("frontend/src/app/admin/strategies/[combination]/page.tsx", "full"),
}

REQUIRED_KEYS = {"lc_key", "label", "q", "help", "a", "b", "a_full", "b_full"}


def _tsx_pairs(rel_path: str) -> list[tuple[str, str]]:
    path = REPO_ROOT / rel_path
    if not path.exists():
        pytest.skip(f"{rel_path} недоступен (backend-контейнер без фронта)")
    src = path.read_text(encoding="utf-8")
    a = re.findall(r"a: '(.*?)'", src)[:6]
    b = re.findall(r"b: '(.*?)'", src)[:6]
    if len(a) != 6 or len(b) != 6:
        pytest.skip(f"{rel_path}: формулировки больше не объявлены локально ({len(a)}/{len(b)})")
    return list(zip(a, b))


def test_structure_is_complete():
    assert len(BASE_QUESTIONS) == 6
    for i, q in enumerate(BASE_QUESTIONS, start=1):
        assert set(q) >= REQUIRED_KEYS, f"Вопрос {i}: не хватает ключей {REQUIRED_KEYS - set(q)}"
        assert all(str(q[k]).strip() for k in REQUIRED_KEYS), f"Вопрос {i}: пустое поле"


def test_derived_views_match_source():
    assert [q["lc_key"] for q in BASE_QUESTIONS] == LC_FIELDS
    assert [(q["lc_key"], q["label"]) for q in BASE_QUESTIONS] == LC_LABELS
    assert [q["label"] for q in BASE_QUESTIONS] == QUESTION_LABELS
    assert [(q["a_full"], q["b_full"]) for q in BASE_QUESTIONS] == ANSWERS


def test_question_two_orientation_is_pinned():
    """Решение методолога: A = адаптация подтверждённого, B = создание нового.

    При сознательном пересмотре ориентации правится этот тест вместе с
    единым источником — молча разъехаться они больше не могут.
    """
    q = BASE_QUESTIONS[1]
    assert q["a"].startswith("Быстрый последователь")
    assert q["b"].startswith("Первопроходец")
    assert q["a_full"].startswith("Быстрый последователь")
    assert q["b_full"].startswith("Первопроходец")


def test_short_form_is_prefix_of_full_form():
    """Краткая и развёрнутая формы не должны противоречить друг другу."""
    for i, q in enumerate(BASE_QUESTIONS, start=1):
        assert q["a_full"].startswith(q["a"]), f"Вопрос {i}: A-формы разошлись"
        assert q["b_full"].startswith(q["b"]), f"Вопрос {i}: B-формы разошлись"


def test_seed_lifecycle_has_no_local_copies():
    """seed_lifecycle.py обязан импортировать формулировки, а не хранить свои."""
    src = (BACKEND_ROOT / "seed_lifecycle.py").read_text(encoding="utf-8")
    assert "from app.method1_questions import" in src
    for marker in ("Первопроходец", "Быстрый последователь", "Рост выручки"):
        assert marker not in src, f"В seed_lifecycle.py осталась локальная копия: {marker!r}"


def test_pdf_has_no_local_lc_labels():
    """pdf.py обязан брать подписи блоков ЖЦ из единого источника."""
    src = (BACKEND_ROOT / "app" / "pdf.py").read_text(encoding="utf-8")
    assert "LC_LABELS" in src
    assert '"lc_profit",    "Формирование прибыли"' not in src


@pytest.mark.parametrize("name", sorted(FRONTEND_SOURCES))
def test_frontend_sources_match_source_of_truth(name: str):
    """Пока фронт держит свои копии — они обязаны совпадать с эталоном."""
    rel_path, form = FRONTEND_SOURCES[name]
    pairs = _tsx_pairs(rel_path)
    key_a, key_b = ("a_full", "b_full") if form == "full" else ("a", "b")
    for idx, (a, b) in enumerate(pairs, start=0):
        exp = BASE_QUESTIONS[idx]
        assert a == exp[key_a], f"{name}, вопрос {idx + 1}: A = {a!r}, эталон {exp[key_a]!r}"
        assert b == exp[key_b], f"{name}, вопрос {idx + 1}: B = {b!r}, эталон {exp[key_b]!r}"
