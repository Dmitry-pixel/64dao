# -*- coding: utf-8 -*-
"""
Метод 3 — портфельный слой раздела 03.

Проверка на контрольном кейсе: правило обязано отобрать те же две линии,
что названы в образце 64dao-portfolio-report-sample.html версии 0.2, в том же
порядке и с теми же типами.
"""
import pytest

from app.m3_portfolio import (
    constraints, delta_line_reading, metric_readings, support_note,
    tact_note, yin_profile, yin_table,
)

# Пять направлений образца: символы и подвижность.
CONTROL = [
    ("Салонный канал B2B",       "AAABBA", {"3": "old_yang"}),
    ("Маркетплейсы",             "BABABA", {"3": "old_yin", "4": "old_yang"}),
    ("Интернет-магазин",         "ABBABA", {}),
    ("Контрактное производство", "ABAABA", {}),
    ("Обучение мастеров",        "BABAAA", {"1": "old_yin"}),
]


def _results(rows=CONTROL):
    return [
        {"name": n, "symbols": s, "mobility": m,
         "target_lines": [k for k, v in m.items() if v == "old_yin"],
         "risk_lines": [k for k, v in m.items() if v == "old_yang"]}
        for n, s, m in rows
    ]


def _summary(**over):
    base = {"sum_positions": 18, "sum_positions_max": 30, "turbulence": 4,
            "delta": 0, "distinct_cells": 4, "objects": 5}
    base.update(over)
    return base


# ── Профиль слабостей ─────────────────────────────────────────────────────────
def test_yin_counts_match_sample():
    """Образец: Л5 — 4, Л3 — 3, Л1 — 2, Л2 — 2, Л4 — 1, Л6 — 0."""
    counts = {r["line"]: r["yin"] for r in yin_profile(_results())}
    assert counts == {5: 4, 3: 3, 1: 2, 2: 2, 4: 1, 6: 0}


def test_rows_sorted_by_frequency_then_line():
    """
    Порядок — от самой частой слабости к самой редкой. При равенстве младшая
    линия первой: два одинаковых расчёта обязаны дать одинаковую таблицу.
    """
    order = [r["line"] for r in yin_profile(_results())]
    assert order == [5, 3, 1, 2, 4, 6]


def test_reading_distinguishes_company_from_direction():
    rows = {r["line"]: r["reading"] for r in yin_table(_results())}
    assert "Единичный случай" in rows[4]
    assert "Не является ограничением" in rows[6]
    assert "4 направлений из 5" in rows[5]


def test_universal_weakness_named_as_company_property():
    rows = _results([("A", "BBBBBB", {}), ("B", "BBBBBB", {}), ("C", "BBBBBB", {})])
    reading = {r["line"]: r["reading"] for r in yin_table(rows)}[1]
    assert "свойство компании, а не продукта" in reading


# ── Ограничения ───────────────────────────────────────────────────────────────
def test_selects_the_same_two_constraints_as_sample():
    found = constraints(_results())
    assert [c["line"] for c in found] == [5, 3]


def test_constraint_kind_follows_line_number():
    """
    Линии 1–3 — то, что компания делает сама, значит компетенция.
    Линии 4–6 — то, во что она поставлена, значит структурное.
    """
    kinds = {c["line"]: c["kind"] for c in constraints(_results())}
    assert kinds[5] == "structural"
    assert kinds[3] == "competence"


def test_structural_constraint_says_it_is_not_fixable_inside():
    body = next(c["body"] for c in constraints(_results()) if c["line"] == 5)
    assert "внутри направлений оно не исправляется" in body


def test_competence_constraint_warns_about_paying_twice():
    body = next(c["body"] for c in constraints(_results()) if c["line"] == 3)
    assert "кривую обучения" in body


def test_threshold_is_a_strict_majority():
    """
    Слабость у половины портфеля ещё может быть совпадением. Линии 1 и 2
    слабы у двух направлений из пяти и ограничениями не признаются.
    """
    lines = [c["line"] for c in constraints(_results())]
    assert 1 not in lines and 2 not in lines

    half = _results([("A", "BAAAAA", {}), ("B", "BAAAAA", {}),
                     ("C", "AAAAAA", {}), ("D", "AAAAAA", {})])
    assert constraints(half) == [], "ровно половина — ещё не ограничение"


def test_no_constraints_is_a_valid_outcome():
    strong = _results([("A", "AAAAAA", {}), ("B", "AAAAAA", {}), ("C", "AAAAAA", {})])
    assert constraints(strong) == []


def test_lone_strong_overheated_leaves_nothing_to_lean_on():
    """
    Перегретая сильная позиция опорой не является: она держится на пределе
    и без закрепления деградирует. Если она единственная, опереться не на что.
    """
    rows = _results([("Первое", "AAAAAA", {"1": "old_yang"}),
                     ("Второе", "BAAAAA", {}), ("Третье", "BAAAAA", {})])
    body = next(c["body"] for c in constraints(rows) if c["line"] == 1)
    assert "единственная сильная позиция перегрета: опереться не на что" in body


def test_lone_strong_healthy_is_named_by_direction():
    rows = _results([("Первое", "AAAAAA", {}),
                     ("Второе", "BAAAAA", {}), ("Третье", "BAAAAA", {})])
    body = next(c["body"] for c in constraints(rows) if c["line"] == 1)
    assert "единственная сильная позиция — у направления «Первое»" in body


def test_two_strong_one_overheated_reads_as_unstable_support():
    """
    На контрольном кейсе по линии 3 сильных две — «Салонный» и «Контрактное»,
    перегрета одна. Образец называет сильной только первую; расчёт этого не
    подтверждает и говорит о неустойчивой опоре, а не о единственной.
    """
    body = next(c["body"] for c in constraints(_results()) if c["line"] == 3)
    assert "из 2 сильных позиций одна перегрета: опора неустойчива" in body
    assert "единственная" not in body


def test_support_note_agrees_in_number():
    """«1 перегреты» — не по-русски."""
    rows = _results([("A", "AAAAAA", {"1": "old_yang"}), ("B", "AAAAAA", {"1": "old_yang"}),
                     ("C", "AAAAAA", {}), ("D", "BAAAAA", {}), ("E", "BAAAAA", {})])
    note = support_note(next(r for r in yin_profile(rows) if r["line"] == 1))
    assert "перегрето 2" in note


# ── Дельта линии ──────────────────────────────────────────────────────────────
def test_delta_line_counts_ripe_minus_overheated():
    """
    Дельта линии (delta_line) — назревшие минус перегретые ПО ЭТОЙ ЛИНИИ.
    Не путать с дельтой портфеля (Δ в шапке) и дельтой направления
    (delta_direction, входит в индекс V).
    """
    rows = {r["line"]: r for r in yin_profile(_results())}
    assert rows[3]["yin_ripe"] == 1 and rows[3]["yang_hot"] == 1
    assert rows[3]["delta_line"] == 0
    assert rows[1]["delta_line"] == 1, "назревшая слабость без перегрева"
    assert rows[4]["delta_line"] == -1, "перегрев без назревшей слабости"


def test_delta_line_readings_are_three_distinct_states():
    assert "энергия для исправления" in delta_line_reading(2)
    assert "замена, не рост" in delta_line_reading(0)
    assert "скорее просядет" in delta_line_reading(-2)


def test_delta_line_appears_in_constraint_body_only_when_nonzero():
    """Нулевая дельта по линии — норма, отдельной фразы не заслуживает."""
    zero = next(c["body"] for c in constraints(_results()) if c["line"] == 3)
    assert "энергия для исправления" not in zero
    assert "скорее просядет" not in zero


def test_portfolio_delta_is_named_apart_from_the_others():
    names = [m["name"] for m in metric_readings(_summary())]
    assert "Дельта портфеля Δ" in names


# ── Агрегаты ──────────────────────────────────────────────────────────────────
def test_metric_readings_match_sample_wording():
    readings = {m["name"]: m["reading"] for m in metric_readings(_summary())}
    assert readings["Сумма позиций"] == "Портфель чуть выше середины"
    assert readings["Подвижных линий, T"] == "Умеренная энергия перехода"
    assert readings["Занято ячеек"] == "Направления дифференцированы"
    assert "ровно столько же" in readings["Дельта портфеля Δ"]


def test_delta_sign_changes_the_reading():
    positive = {m["name"]: m["reading"] for m in metric_readings(_summary(delta=3))}
    negative = {m["name"]: m["reading"] for m in metric_readings(_summary(delta=-3))}
    assert "фазе роста" in positive["Дельта портфеля Δ"]
    assert "защиту достигнутого" in negative["Дельта портфеля Δ"]


def test_zero_turbulence_named_explicitly():
    """Ноль подвижных — не «мало энергии», а отдельное состояние портфеля."""
    reading = {m["name"]: m["reading"]
               for m in metric_readings(_summary(turbulence=0))}["Подвижных линий, T"]
    assert "стабильный упадок" in reading


def test_single_cell_portfolio_flagged_in_reading():
    reading = {m["name"]: m["reading"]
               for m in metric_readings(_summary(distinct_cells=1))}["Занято ячеек"]
    assert "формулировки их не различили" in reading


def test_metric_values_are_shown_as_fractions():
    values = {m["name"]: m["value"] for m in metric_readings(_summary())}
    assert values["Сумма позиций"] == "18 / 30"
    assert values["Подвижных линий, T"] == "4 / 30"
    assert values["Занято ячеек"] == "4 из 9"


def test_tact_note_counts_directions_not_lines():
    """
    Правило такта ограничивает число направлений в работе, а не число линий:
    узкое место — управленческий ресурс.
    """
    note = tact_note(_results(), _summary())
    assert "4 подвижных линий на 3 направлениях" in note
    assert "не более двух направлений" in note


# ── Порядок собственника против расчётного (§10.14) ───────────────────────────
from app import m3_portfolio as pf  # noqa: E402


def _ranked(*pairs):
    return [{"position": i, "name": n, "v_rank": v}
            for i, (n, v) in enumerate(pairs, start=1)]


REAL = _ranked(("Салонный канал B2B", 5), ("Маркетплейс", 1),
               ("Интернет-магазин", 4), ("Контрактное", 2), ("Обучение", 3))


def test_rank_comparison_is_none_without_ranks():
    """Сравнивать нечего — молчание честнее натяжки."""
    assert pf.rank_comparison(REAL, None) is None
    assert pf.rank_comparison(REAL, []) is None


def test_rank_comparison_is_none_on_length_mismatch():
    assert pf.rank_comparison(REAL, [1, 2, 3]) is None


def test_rank_comparison_puts_the_dispute_first():
    """
    Числа реального портфеля «Вверх»: собственник назвал [4,5,1,2,3].
    Три направления из пяти совпали, весь Спирмен −0,30 дала одна
    перестановка двух — таблица обязана показать её сверху.
    """
    cmp = pf.rank_comparison(REAL, [4, 5, 1, 2, 3])
    assert [r["name"] for r in cmp["rows"][:2]] == ["Маркетплейс", "Интернет-магазин"]
    assert cmp["rows"][0]["gap"] == 4
    assert cmp["rows"][1]["gap"] == -3
    assert cmp["agreed"] == 2
    assert [d["name"] for d in cmp["disputed"]] == ["Маркетплейс", "Интернет-магазин"]


def test_rank_comparison_full_agreement():
    cmp = pf.rank_comparison(REAL, [5, 1, 4, 2, 3])
    assert cmp["agreed"] == 5
    assert cmp["disputed"] == []
    text = pf.rank_comparison_reading(cmp, 1.0)
    assert "совпадают по существу" in text
    assert "1,00" in text


def test_reading_names_the_disputed_directions():
    text = pf.rank_comparison_reading(pf.rank_comparison(REAL, [4, 5, 1, 2, 3]), -0.30)
    assert "Маркетплейс" in text and "Интернет-магазин" in text
    # Запятая, а не точка: во всём отчёте дробные через запятую.
    assert "-0,30" in text and "-0.30" not in text
    assert "не дефект данных" in text
