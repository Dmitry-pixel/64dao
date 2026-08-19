# -*- coding: utf-8 -*-
"""
Тесты интерпретации (Этап 3): правила напряжений R1–R12 + сборка слоёв A–E.
Чистая логика — БД не нужна.
"""
from app.finance_interpret import (
    PLACEHOLDER,
    build_interpretation,
    evaluate_rules,
    tonality_key,
)
from app.finance_scoring import compute_finance_result


# ── Хелперы ───────────────────────────────────────────────────────────────────
def mk(symbols: str, moving=(), states: dict | None = None) -> list[dict]:
    states = states or {}
    lines = []
    for i, s in enumerate(symbols, start=1):
        mv = i in moving
        st = states.get(i)
        if st is None:
            st = ("old_yang" if mv else "young_yang") if s == "A" else ("old_yin" if mv else "young_yin")
        lines.append({"line": i, "symbol": s, "state": st, "moving": mv, "flags": []})
    return lines


def control_answers() -> dict:
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    return a


# ── Правила: контрольный кейс §5.8 -> R1, R6, R8 ──────────────────────────────
def test_rules_control_case_fires_R1_R6_R8():
    # AAAABB, подвижная линия 6 (старый Инь)
    lines = mk("AAAABB", moving={6})
    assert evaluate_rules(lines) == ["R1", "R6", "R8"]


def test_rules_none_fire_all_strong_static():
    assert evaluate_rules(mk("AAAAAA")) == []


def test_rule_R3_vs_R4_mutually_exclusive():
    # sym2=A, sym3=B -> R4 (и не R3)
    r_r4 = evaluate_rules(mk("AABAAA"))
    assert "R4" in r_r4 and "R3" not in r_r4
    # sym3=A, sym2=B -> R3 (и не R4)
    r_r3 = evaluate_rules(mk("ABAAAA"))
    assert "R3" in r_r3 and "R4" not in r_r3


def test_rule_R9_old_yang_line4():
    lines = mk("AAAAAA", moving={4}, states={4: "old_yang"})
    assert "R9" in evaluate_rules(lines)


def test_rule_R12_three_moving():
    lines = mk("BBBAAA", moving={1, 2, 3},
               states={1: "old_yin", 2: "old_yin", 3: "old_yin"})
    assert "R12" in evaluate_rules(lines)


def test_rule_R7_strategy_without_sponsor():
    # Л4=B и Л6=A
    assert "R7" in evaluate_rules(mk("AAABAA"))  # sym4=B,sym6=A


# ── Тональность (§5.2) ────────────────────────────────────────────────────────
def test_tonality_thresholds():
    assert tonality_key(6) == "mature"
    assert tonality_key(5) == "mature"
    assert tonality_key(4) == "transitional"
    assert tonality_key(3) == "transitional"
    assert tonality_key(2) == "crisis"
    assert tonality_key(0) == "crisis"


# ── Контент для сборки (соответствует сид-структуре fin_content) ──────────────
def control_content() -> dict:
    return {
        "tonality": {"transitional": {"title": "Переходное состояние",
                                      "text": "Язык приоритизации."}},
        "quadrant": {"power_no_direction": {"title": "Сила без направления",
                                            "text": "Двигатель есть, руля нет."}},
        "trigram": {"AAA_lower": {"title": "Цянь", "text": "Двигатель на пике."},
                    "ABB_upper": {"title": "Чжэнь", "text": "Поддержка без направления."}},
        "tension_rule": {"R1": {"text": "Поддержка без стратегии."},
                         "R6": {"text": "Трансформация в турбулентной среде."},
                         "R8": {"text": "Рутина без развития."}},
        "action_package": {"line6_yin": {"title": "6. Стратегия",
                                         "text": "Стратегическая сессия, целевая модель, KPI."}},
        "fin_pattern": {
            "AAAABB": {"essence": "Ресурс превышает ясность его применения.",
                       "mistake": "Активность ради активности."},
            "AAAABA": {"essence": "Ресурс на службе ясной цели.",
                       "mistake": "Прекращение инвестиций на фоне успеха."},
        },
    }


# ── Полная сборка на контрольном кейсе ────────────────────────────────────────
def test_build_interpretation_control_case():
    result = compute_finance_result(control_answers())
    interp = build_interpretation(result, control_content())

    assert interp["tonality"]["key"] == "transitional"
    assert interp["quadrant"]["key"] == "power_no_direction"
    assert interp["trigrams"]["lower"]["code"] == "AAA"
    assert interp["trigrams"]["lower"]["title"] == "Цянь"
    assert interp["trigrams"]["upper"]["code"] == "ABB"
    assert interp["trigrams"]["upper"]["title"] == "Чжэнь"

    assert interp["pattern_current"]["essence"].startswith("Ресурс превышает")
    assert [t["id"] for t in interp["tensions"]] == ["R1", "R6", "R8"]

    # приоритет: единственная подвижная — линия 6 (старый Инь)
    assert len(interp["priorities"]) == 1
    assert interp["priorities"][0]["line"] == 6
    assert interp["priorities"][0]["state"] == "old_yin"
    assert "Стратегическая сессия" in interp["priorities"][0]["package_text"]

    # траектория -> результирующая #14
    assert interp["trajectory"]["resulting"]["number"] == 14
    assert interp["trajectory"]["essence"].startswith("Ресурс на службе")

    # оговорка по флагу INCONSISTENT_BLOCK на линии 3
    assert any("Линия 3" in c and "противоречив" in c for c in interp["caveats"])

    # следующие шаги — из пакета подвижной линии
    assert interp["next_steps"] == [interp["priorities"][0]["package_text"]]


# ── Неактивное/отсутствующее правило не выводится ─────────────────────────────
def test_inactive_rule_not_shown():
    result = compute_finance_result(control_answers())
    content = control_content()
    del content["tension_rule"]["R6"]      # имитируем is_active=false (нет в content)
    interp = build_interpretation(result, content)
    assert [t["id"] for t in interp["tensions"]] == ["R1", "R8"]


# ── Нет подвижных линий -> траектория None, приоритетов нет ────────────────────
def test_no_moving_no_trajectory():
    result = compute_finance_result({i: 3 for b in range(1, 7) for i in [f"{b}.{p}" for p in range(1, 5)]})
    interp = build_interpretation(result, control_content())
    assert interp["trajectory"] is None
    assert interp["priorities"] == []
    assert interp["next_steps"] == []


# ── Отсутствие паттерна -> заглушка «Не заполнено» ────────────────────────────
def test_missing_pattern_placeholder():
    result = compute_finance_result(control_answers())
    content = control_content()
    del content["fin_pattern"]["AAAABB"]
    interp = build_interpretation(result, content)
    assert interp["pattern_current"]["essence"] == PLACEHOLDER


# ── Оговорка о низкой полноте данных ─────────────────────────────────────────
def test_low_data_caveat_in_report():
    a = control_answers()
    a["1.1"] = None; a["2.1"] = None; a["3.1"] = None
    result = compute_finance_result(a)
    interp = build_interpretation(result, control_content())
    assert any("полнота данных" in c for c in interp["caveats"])


# ── Вето: отдельный блок до приоритетов (Поправка П6) ─────────────────────────
def veto_answers() -> dict:
    """Все блоки нейтральны (3), блок 4 сильный, но 4.1 = 1 -> вето сработало.
    Блок 4: сырые [1, 4, 4, 1], после инверсии 4.4 -> [1, 4, 4, 4], среднее 3.25.
    По §3.3 линия переопределяется в Инь, подвижной не становится."""
    a = {f"{b}.{p}": 3 for b in range(1, 7) for p in range(1, 5)}
    for p, v in enumerate([1, 4, 4, 1], 1):
        a[f"4.{p}"] = v
    return a


def test_veto_block_present_and_line_excluded():
    r = compute_finance_result(veto_answers())
    l4 = next(l for l in r["lines"] if l["line"] == 4)
    assert "VETO_APPLIED" in l4["flags"]
    assert l4["symbol"] == "B" and l4["moving"] is False

    interp = build_interpretation(r, control_content())

    vb = interp["veto_block"]
    assert vb is not None
    assert vb["line"] == 4
    assert vb["score"] == l4["score"]

    # Линия 4 не дублируется ни в приоритетах, ни в плановых шагах
    assert all(p["line"] != 4 for p in interp["priorities"])
    assert all(p["line"] != 4 for p in interp["planned_steps"])


def test_veto_first_in_next_steps():
    r = compute_finance_result(veto_answers())
    interp = build_interpretation(r, control_content())
    vb = interp["veto_block"]
    if vb["package_text"] != PLACEHOLDER:
        assert interp["next_steps"][0] == vb["package_text"]


def test_no_veto_block_without_veto():
    r = compute_finance_result(control_answers())
    interp = build_interpretation(r, control_content())
    assert interp["veto_block"] is None
    # Контрольный кейс: линия 6 остаётся приоритетом
    assert interp["priorities"][0]["line"] == 6
