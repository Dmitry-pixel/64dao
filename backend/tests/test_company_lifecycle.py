# -*- coding: utf-8 -*-
"""
Жизненный цикл компании: категориальные архетипы, композиция с маршрутом,
флаги качества. Чистая логика, БД не нужна.

Ключевые контрпримеры зафиксированы против арифметики над циклической
шкалой стадий: {упадок, обновление} НЕ усредняются в «зрелость».
"""
from app.company_lifecycle import (
    ARCH_MIXED,
    ARCH_OPERATIONAL_DEBT,
    ARCH_STABLE_MATURITY,
    ARCH_SYNCHRONOUS_BREAKTHROUGH,
    ARCH_SYSTEMIC_CHAOS,
    ARCH_TRANSFORMATION_GAP,
    build_company_lifecycle,
    classify_archetype,
)
from app.contour_summary import build_summary


# ── Хелперы ──────────────────────────────────────────────────────────────────

LINE_KEYS = ["processes", "systems", "team", "leadership", "environment", "strategy"]


def _line(n: int, symbol: str, moving: bool) -> dict:
    state = ("old_yang" if moving else "young_yang") if symbol == "A" else \
            ("old_yin" if moving else "young_yin")
    return {
        "line": n, "block": LINE_KEYS[n - 1], "score": 2.5,
        "symbol": symbol, "state": state, "moving": moving, "flags": [],
    }


def res(combo: str = "AAAAAA", moving: list[int] | None = None,
        stage: str | None = "зрелость", to_stage: str | None = None) -> dict:
    """Снимок result контура, обогащённый стадиями (как после JOIN на strategies)."""
    moving = moving or []
    lines = [_line(i, combo[i - 1], i in moving) for i in range(1, 7)]
    resulting = "".join(
        ("B" if c == "A" else "A") if i in moving else c
        for i, c in enumerate(combo, start=1)
    ) if moving else None
    return {
        "lines": lines,
        "combination_current": combo,
        "combination_resulting": resulting,
        "moving_lines": moving,
        "maturity_index": combo.count("A"),
        "hexagram_current": {"code": combo, "number": 1, "name": "x"},
        "hexagram_resulting": {"code": resulting, "number": 2, "name": "y"} if resulting else None,
        "lifecycle_stage": stage,
        "transition_lifecycle_stage": to_stage,
    }


def full(finance: dict, product: dict, process: dict, market: dict) -> dict:
    return {"finance": finance, "product": product, "process": process, "market": market}


def build(contours: dict) -> dict | None:
    return build_company_lifecycle(contours, build_summary(contours))


# ── Доступность ──────────────────────────────────────────────────────────────

def test_none_when_not_all_four_contours():
    c = {"finance": res(), "product": res(), "market": res()}
    assert build_company_lifecycle(c, build_summary(c)) is None


def test_none_without_summary():
    c = full(res(), res(), res(), res())
    assert build_company_lifecycle(c, None) is None


# ── Архетипы: контрпримеры против арифметики над стадиями ───────────────────

def test_decline_plus_renewal_is_not_stable_maturity():
    """{упадок=4, обновление=5}: среднее индексов дало бы 4.5 ≈ «зрелость».
    Категориальная классификация обязана увидеть кризисный дисбаланс."""
    arch, _ = classify_archetype({
        "product": "обновление", "market": "обновление",
        "finance": "упадок", "process": "упадок",
    })
    assert arch == ARCH_OPERATIONAL_DEBT
    assert arch != ARCH_STABLE_MATURITY


def test_renewal_back_decline_front_is_transformation_gap():
    arch, _ = classify_archetype({
        "finance": "обновление", "process": "обновление",
        "product": "упадок", "market": "упадок",
    })
    assert arch == ARCH_TRANSFORMATION_GAP


def test_operational_debt_classic():
    """Фронт тянет, бэк тормозит — классический перегрев продаж."""
    arch, _ = classify_archetype({
        "product": "расцвет", "market": "расцвет",
        "finance": "зарождение", "process": "зрелость",
    })
    assert arch == ARCH_OPERATIONAL_DEBT


def test_transformation_gap_classic():
    """Зрелый бэк, истощающийся фронт — «дойная корова» на грани."""
    arch, _ = classify_archetype({
        "finance": "зрелость", "process": "зрелость",
        "product": "упадок", "market": "зарождение",
    })
    assert arch == ARCH_TRANSFORMATION_GAP


def test_systemic_chaos_three_anchors():
    arch, _ = classify_archetype({
        "finance": "зарождение", "process": "упадок",
        "product": "зарождение", "market": "зрелость",
    })
    assert arch == ARCH_SYSTEMIC_CHAOS


def test_synchronous_breakthrough_three_drivers():
    arch, _ = classify_archetype({
        "finance": "расцвет", "process": "обновление",
        "product": "расцвет", "market": "зрелость",
    })
    assert arch == ARCH_SYNCHRONOUS_BREAKTHROUGH


def test_stable_maturity_requires_no_anchors():
    arch, _ = classify_archetype({
        "finance": "зрелость", "process": "зрелость",
        "product": "зрелость", "market": "расцвет",
    })
    assert arch == ARCH_STABLE_MATURITY


def test_anchors_both_sides_is_ambiguous_mixed():
    """Якоря и во фронте, и в бэке: типовой сценарий неприменим — честный
    MIXED с флагом, а не подгонка под ближайший архетип."""
    arch, flags = classify_archetype({
        "product": "расцвет", "market": "упадок",
        "finance": "расцвет", "process": "упадок",
    })
    assert arch == ARCH_MIXED
    assert "ARCHETYPE_AMBIGUOUS" in flags


def test_unknown_stage_flagged_not_defaulted():
    """Отсутствующая стадия не подменяется «зрелостью» молча."""
    arch, flags = classify_archetype({
        "finance": None, "process": "зрелость",
        "product": "зрелость", "market": "зрелость",
    })
    assert "STAGE_UNKNOWN" in flags
    assert arch == ARCH_STABLE_MATURITY  # по трём известным


# ── Точка и ничья ограничения ────────────────────────────────────────────────

def test_stage_taken_from_constraint_not_finance():
    c = full(
        finance=res("AAAAAA", stage="зрелость"),          # зрелость 6
        product=res("BBBBBA", stage="зарождение"),        # зрелость 1 -> constraint
        process=res("AAABBB", stage="зрелость"),
        market=res("AAAABB", stage="расцвет"),
    )
    out = build(c)
    assert out["constraint"] == "product"
    assert out["stage"] == "зарождение"


def test_constraint_tie_leaves_stage_undefined():
    c = full(
        finance=res("BBBAAA", stage="зрелость"),
        product=res("AAABBB", stage="упадок"),
        process=res("AAAAAA", stage="зрелость"),
        market=res("AAAAAB", stage="расцвет"),
    )
    out = build(c)
    assert out["constraint"] is None
    assert out["stage"] is None
    assert set(out["tied"]) == {"finance", "product"}
    assert "CONSTRAINT_TIED" in out["quality_flags"]


# ── Playbook: рамка + маршрут, а не статический список ───────────────────────

def test_tactics_come_from_constraint_route():
    """Тактика — фактические подвижные линии ограничения (old_yin раньше
    old_yang, снизу вверх), а не шаблон архетипа."""
    c = full(
        finance=res("BABBBB", moving=[1, 2], stage="зарождение"),  # 1=B old_yin, 2=A old_yang
        product=res("AAAAAA", stage="расцвет"),
        process=res("AAAABB", stage="зрелость"),
        market=res("AAAAAB", stage="расцвет"),
    )
    out = build(c)
    assert out["constraint"] == "finance"
    steps = out["playbook"]["tactics"]
    assert [s["line"] for s in steps] == [1, 2]           # old_yin первым
    assert steps[0]["action_key"] == "line1_yin"
    assert steps[1]["action_key"] == "line2_oldyang"
    assert out["playbook"]["tactics_source"] == "finance"
    assert "environment" in out["playbook"]["frame"]
    assert "strategy" in out["playbook"]["frame"]


def test_two_companies_same_archetype_different_tactics():
    """Один архетип, разные ответы -> разные маршруты. Статический playbook
    этого не различал бы."""
    base = dict(product=res("AAAAAA", stage="расцвет"),
                process=res("AAAABB", stage="зрелость"),
                market=res("AAAAAB", stage="расцвет"))
    out1 = build(full(finance=res("BBBBBB", moving=[1], stage="упадок"), **base))
    out2 = build(full(finance=res("BBBBBB", moving=[5, 6], stage="упадок"), **base))
    assert out1["archetype"] == out2["archetype"] == ARCH_OPERATIONAL_DEBT
    assert [s["line"] for s in out1["playbook"]["tactics"]] == [1]
    assert [s["line"] for s in out2["playbook"]["tactics"]] == [5, 6]


def test_stable_constraint_flagged():
    c = full(
        finance=res("BBBBBB", stage="упадок"),  # ограничение без подвижных линий
        product=res("AAAAAA", stage="расцвет"),
        process=res("AAAABB", stage="зрелость"),
        market=res("AAAAAB", stage="расцвет"),
    )
    out = build(c)
    assert out["playbook"]["tactics"] == []
    assert "CONSTRAINT_STABLE" in out["quality_flags"]


# ── Вектор и верификационный слой ────────────────────────────────────────────

def test_vector_contains_all_contours_with_transitions():
    c = full(
        finance=res("BBBBBB", moving=[1], stage="упадок", to_stage="зарождение"),
        product=res("AAAAAA", stage="расцвет"),
        process=res("AAAABB", stage="зрелость"),
        market=res("AAAAAB", stage="расцвет"),
    )
    out = build(c)
    assert out["vector"]["finance"] == {"from": "упадок", "to": "зарождение", "moving_count": 1}
    assert out["vector"]["product"]["to"] is None


def test_delta_counts_old_yin_positive_old_yang_negative():
    c = full(
        finance=res("BBBBBB", moving=[1, 2], stage="упадок"),   # 2 old_yin: +2
        product=res("AAAAAA", moving=[1], stage="расцвет"),     # 1 old_yang: -1
        process=res("AAAABB", stage="зрелость"),
        market=res("AAAAAB", stage="расцвет"),
    )
    out = build(c)
    v = out["verification"]
    assert v["delta"] == 1
    assert v["moving_total"] == 3
    assert v["maturity_sum"] == 6 + 6 + 4 + 5 - 6  # 0+6+4+5 = 15


def test_no_moving_lines_is_valid_state_not_anomaly():
    """Глубокий стабильный упадок — валидный диагноз, а не ошибка данных."""
    c = full(
        finance=res("BBBBBB", stage="упадок"),
        product=res("BBBBBA", stage="упадок"),
        process=res("BBBBAA", stage="зарождение"),
        market=res("BBBAAA", stage="зарождение"),
    )
    out = build(c)
    assert out is not None
    assert "NO_INTERNAL_PRESSURE" in out["quality_flags"]
    assert out["archetype"] == ARCH_SYSTEMIC_CHAOS


def test_high_turbulence_flag():
    c = full(
        finance=res("BBBBBB", moving=[1, 2, 3], stage="упадок"),
        product=res("AAAAAA", moving=[4, 5, 6], stage="расцвет"),
        process=res("AAAABB", moving=[1, 2], stage="зрелость"),
        market=res("AAAAAB", stage="расцвет"),
    )
    out = build(c)
    assert out["verification"]["moving_total"] == 8
    assert "HIGH_TURBULENCE" in out["quality_flags"]


def test_gap_not_significant_flagged():
    c = full(
        finance=res("BBBAAA", stage="зрелость"),   # 3
        product=res("AAAABB", stage="зрелость"),   # 4
        process=res("AAAAAB", stage="зрелость"),   # 5
        market=res("AAAAAA", stage="расцвет"),     # 6
    )
    out = build(c)
    assert out["constraint"] == "finance"
    assert "GAP_NOT_SIGNIFICANT" in out["quality_flags"]
