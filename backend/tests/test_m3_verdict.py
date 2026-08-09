# -*- coding: utf-8 -*-
"""
Метод 3 — вердикт по позиции в матрице GE/McKinsey.

Главный тест — воспроизведение всех пяти вердиктов образца
64dao-portfolio-report-sample.html версии 0.2. Если правило их не даёт,
значит вердикт не выводится из зоны и подвижности, и его придётся заводить
контентом.
"""
import pytest

from app.m3_verdict import (
    VERDICTS, ZONES, mobility_state, verdict_for, zone_of,
)


def _r(cs, ca, target=(), risk=(), v_rank=3, z_rank=3):
    return {
        "cell_strength": cs, "cell_attract": ca,
        "target_lines": list(target), "risk_lines": list(risk),
        "v_rank": v_rank, "z_rank": z_rank,
    }


# ── Воспроизведение образца ───────────────────────────────────────────────────
SAMPLE = [
    # направление, сила, привлекательность, цель, риск, вердикт образца
    ("5 · Обучение мастеров",       "low",  "high", (1,), (),   "Инвестировать точечно"),
    ("2 · Маркетплейсы",            "low",  "mid",  (3,), (4,), "Селективно, со сроком"),
    ("4 · Контрактное производство", "mid", "mid",  (),   (),   "Удерживать, не развивать"),
    ("3 · Интернет-магазин",        "low",  "mid",  (),   (),   "Пересборка или выход"),
    ("1 · Салонный канал B2B",      "high", "low",  (),   (3,), "Не инвестировать в рост. Закрепить"),
]


@pytest.mark.parametrize("name,cs,ca,target,risk,expected", SAMPLE)
def test_reproduces_sample_verdicts(name, cs, ca, target, risk, expected):
    assert verdict_for(_r(cs, ca, target, risk))["verdict"] == expected, name


def test_same_cell_opposite_verdicts():
    """
    Тезис образца: классическая матрица выдала бы направлениям 2 и 3
    одинаковую рекомендацию, потому что клетка одна. Метод 3 различает их по
    подвижности — у одного есть внутренний запрос на изменение, у другого нет.
    """
    marketplace = verdict_for(_r("low", "mid", target=(3,), risk=(4,)))
    webstore = verdict_for(_r("low", "mid"))
    assert marketplace["zone_ru"] == webstore["zone_ru"], "клетка обязана совпасть"
    assert marketplace["verdict"] != webstore["verdict"], "вердикты обязаны разойтись"


# ── Зоны ──────────────────────────────────────────────────────────────────────
def test_all_nine_zones_defined():
    assert len(ZONES) == 9
    for strength in ("low", "mid", "high"):
        for attract in ("low", "mid", "high"):
            assert (strength, attract) in ZONES


def test_zone_labels_follow_ge_mckinsey():
    assert zone_of(_r("high", "high"))[1] == "Инвестировать"
    assert zone_of(_r("low", "low"))[1] == "Избегать / выходить"
    assert zone_of(_r("mid", "mid"))[1] == "Удерживать"
    assert zone_of(_r("low", "high"))[1] == "Избирательно развивать"
    assert zone_of(_r("high", "low"))[1] == "Удерживать"


def test_zone_carries_english_name():
    """Английское имя узнаваемо клиентом, который видел матрицу раньше."""
    assert zone_of(_r("high", "high"))[2] == "Invest / Grow"
    assert zone_of(_r("mid", "low"))[2] == "Harvest"


def test_unknown_zone_is_an_error_not_a_default():
    """Молчаливый дефолт спрятал бы дефект расчёта в текст вердикта."""
    with pytest.raises(ValueError):
        zone_of(_r("unknown", "mid"))


# ── Подвижность ───────────────────────────────────────────────────────────────
def test_mobility_states():
    assert mobility_state(_r("mid", "mid")) == "stable"
    assert mobility_state(_r("mid", "mid", target=(1,))) == "target"
    assert mobility_state(_r("mid", "mid", risk=(4,))) == "risk"
    assert mobility_state(_r("mid", "mid", target=(1,), risk=(4,))) == "both"


def test_every_zone_and_state_combination_has_a_verdict():
    """36 сочетаний: девять зон на четыре состояния подвижности."""
    stances = {stance for stance, _, _ in ZONES.values()}
    assert len(VERDICTS) == len(stances) * 4
    for stance in stances:
        for state in ("both", "target", "risk", "stable"):
            assert (stance, state) in VERDICTS


def test_stable_in_weak_zone_means_no_money_will_help():
    """
    Отсутствие подвижных линий в слабой зоне — не «спокойно», а «вкладывать
    не во что»: слабость не назрела и давления на изменение не создаёт.
    """
    assert verdict_for(_r("low", "mid"))["verdict"] == "Пересборка или выход"
    assert verdict_for(_r("low", "low"))["verdict"] == "Пересборка или выход"


def test_stable_in_strong_zone_means_carry_on():
    assert verdict_for(_r("high", "high"))["verdict"] == "Наращивать по плану"


# ── Приписки по рангам ────────────────────────────────────────────────────────
def test_first_by_z_is_flagged_as_first_to_protect():
    """Денежную корову защищают первой, что бы ни говорила её зона."""
    out = verdict_for(_r("high", "low", risk=(3,), v_rank=5, z_rank=1))
    assert "первое место в очереди защиты" in out["notes"]
    assert "первое место по приоритету вложения" not in out["notes"]


def test_first_by_v_is_flagged_separately():
    out = verdict_for(_r("low", "high", target=(1,), v_rank=1, z_rank=5))
    assert "первое место по приоритету вложения" in out["notes"]


def test_mobility_note_always_present():
    for result in (_r("mid", "mid"), _r("mid", "mid", target=(1,))):
        assert verdict_for(result)["notes"]


# ── Траектория по матрице ─────────────────────────────────────────────────────
from app.m3_config import industry_weights  # noqa: E402
from tests import m3_factory as factory  # noqa: E402
from app.m3_verdict import cells_of, symbols_after, transition  # noqa: E402

# Ячейки образца считались по числу Ян. Универсальный пресет 18 (34/33/33)
# воспроизводит это правило точно — на нём формулировки образца и держатся,
# а отраслевые веса проверяются отдельно, в test_m3_scoring.
UNIVERSAL = industry_weights(18)

# Пять направлений образца: символы, текущая ячейка по его подписи,
# подвижные линии и номера гексаграмм.
SAMPLE_TRAJECTORY = [
    ("5 Обучение мастеров",    "BABAAA", ("low", "high"),  6,  [1], 10, [],  None),
    ("2 Маркетплейсы",         "BABABA", ("low", "mid"),   64, [3], 50, [4], 4),
    ("1 Салонный канал B2B",   "AAABBA", ("high", "low"),  26, [],  None, [3], 41),
    ("3 Интернет-магазин",     "ABBABA", ("low", "mid"),   21, [],  None, [], None),
    ("4 Контрактное произв-во", "ABAABA", ("mid", "mid"),  30, [],  None, [], None),
]


def _traj(symbols, current, tl, th, rl, rh, weights=None):
    """Обёртка над общей фабрикой: переходу нужны символы, векторы и веса."""
    return factory.result(
        symbols=symbols, current_hex=current,
        target_lines=list(tl), target_hex=th,
        risk_lines=list(rl), risk_hex=rh,
        weights=weights or UNIVERSAL,
    )


@pytest.mark.parametrize("name,symbols,cells,cur,tl,th,rl,rh", SAMPLE_TRAJECTORY)
def test_current_cell_derived_from_symbols_matches_sample(
        name, symbols, cells, cur, tl, th, rl, rh):
    """
    Ячейка выводится из символов через то же правило, что и в расчёте
    (m3_scoring.cell_of). Тест сверяет вывод с подписями образца и страхует
    от расхождения: разойдясь, они поставили бы в один абзац отчёта две
    несовместимые ячейки одного направления.
    """
    assert cells_of(symbols, UNIVERSAL) == cells, name


def test_symbols_after_inverts_only_named_lines():
    assert symbols_after("BABAAA", [1]) == "AABAAA"
    assert symbols_after("BABABA", [3, 4]) == "BAABBA"
    assert symbols_after("AAABBA", []) == "AAABBA"


def test_target_transition_matches_sample_wording():
    """Образец: «№ 6 → № 10, конкурентная сила переходит из низкой в среднюю»."""
    move = transition(_traj("BABAAA", 6, [1], 10, [], None), "target")
    assert move["to_hex"] == 10
    assert move["phrase"] == "конкурентная сила переходит из низкой в среднюю"


def test_risk_transition_matches_sample_wording():
    """Образец: «№ 26 → № 41, конкурентная сила падает с высокой до средней»."""
    move = transition(_traj("AAABBA", 26, [], None, [3], 41), "risk")
    assert move["phrase"] == "конкурентная сила падает с высокой до средней"


def test_risk_on_attractiveness_axis():
    """Образец: «№ 64 → № 4, привлекательность падает до низкой»."""
    move = transition(_traj("BABABA", 64, [3], 50, [4], 4), "risk")
    assert move["phrase"] == "привлекательность рынка падает со средней до низкой"


def test_preposition_is_so_before_srednyaya():
    """«с средней» — не по-русски."""
    move = transition(_traj("BABABA", 64, [3], 50, [4], 4), "risk")
    assert "со средней" in move["phrase"]
    assert "с средней" not in move["phrase"]


def test_no_transition_without_moving_lines():
    assert transition(_traj("ABBABA", 21, [], None, [], None), "target") is None
    assert transition(_traj("ABAABA", 30, [], None, [], None), "risk") is None


def test_no_transition_when_zone_does_not_move():
    """
    Подвижная линия может остаться внутри своей триграммы и зону не сдвинуть.
    Печатать «переходит из средней в среднюю» незачем.
    """
    # AABABA: нижняя триграмма A,A,B — два Ян, средняя. Инверсия линии 3
    # даёт три Ян и переход; инверсия линии 1 — один Ян, тоже переход.
    # Берём случай без сдвига: нижняя A,B,B (один Ян, низкая), инверсия
    # линии 2 даёт A,A,B — два Ян. Значит нужен другой пример.
    stable = _traj("ABBBBB", 2, [4], 24, [], None)
    move = transition(stable, "target")
    assert move is None or move["moves"], "пустой переход печататься не должен"


def test_cells_of_rejects_wrong_length():
    with pytest.raises(ValueError):
        cells_of("AAA", UNIVERSAL)


def test_transition_is_silent_without_weights():
    """
    Снимок до ревизии 030 весов не хранит. Считать ячейку перехода по старому
    правилу нельзя — в одном абзаце оказались бы две несовместимые ячейки.
    """
    old_snapshot = {"symbols": "BABAAA", "current_hex": 6,
                    "target_lines": [1], "target_hex": 10,
                    "risk_lines": [], "risk_hex": None}
    assert transition(old_snapshot, "target") is None


def test_industry_weights_can_move_the_transition_cell():
    """
    Правило теперь весовое, и это видно: один Ян на Л1 при весе 45
    («Производство») даёт среднюю силу, а при универсальном пресете — низкую.
    """
    prod = industry_weights(2)
    assert cells_of("ABBBBB", prod)[0] == "mid"
    assert cells_of("ABBBBB", UNIVERSAL)[0] == "low"


# ── Очередь исполнения ────────────────────────────────────────────────────────
from app.m3_verdict import execution_reason  # noqa: E402

# Пять направлений образца: сила, привлекательность, цель, риск, доля.
SAMPLE_EXECUTION = [
    ("1 Салонный канал B2B",   "high", "low",  (),   (3,), 45,
     "цена ошибки максимальна"),
    ("2 Маркетплейсы",         "low",  "mid",  (3,), (4,), 30,
     "окно закрывается само"),
    ("4 Контрактное произв-во", "mid", "mid",  (),   (),   12,
     "стабильно, срочности нет"),
    ("3 Интернет-магазин",     "low",  "mid",  (),   (),   8,
     "вне маршрута"),
    ("5 Обучение мастеров",    "low",  "high", (1,), (),   5,
     "отложить можно без потерь"),
]


@pytest.mark.parametrize("name,cs,ca,target,risk,share,expected", SAMPLE_EXECUTION)
def test_execution_reason_matches_sample(name, cs, ca, target, risk, share, expected):
    reason = execution_reason(_r(cs, ca, target, risk), share)
    assert expected in reason, f"{name}: получено «{reason}»"


def test_large_share_with_overheat_outranks_everything():
    """
    Денежную корову защищают первой не потому, что она перспективна, а потому
    что цена ошибки на ней максимальна.
    """
    reason = execution_reason(_r("high", "low", risk=(3,)), 45)
    assert "45% выручки" in reason
    assert "цена ошибки максимальна" in reason


def test_moderate_share_with_overheat_reads_as_closing_window():
    reason = execution_reason(_r("low", "mid", target=(3,), risk=(4,)), 30)
    assert "окно закрывается само" in reason
    assert "цена ошибки" not in reason


def test_stable_weak_zone_needs_a_decision_not_a_route():
    """
    Стабильность в слабой зоне — не спокойствие: маршрута нет, значит решение
    принимается вне его. В сильной зоне то же состояние означает «просто нет
    срочности».
    """
    assert "вне маршрута" in execution_reason(_r("low", "mid"), 8)
    assert "срочности нет" in execution_reason(_r("mid", "mid"), 12)


def test_share_is_printed_without_trailing_zero():
    assert "45%" in execution_reason(_r("high", "low", risk=(3,)), 45.0)
    assert "45.0%" not in execution_reason(_r("high", "low", risk=(3,)), 45.0)


def test_unknown_share_still_yields_a_reason():
    """Доля может быть не указана — место в очереди от этого не исчезает."""
    reason = execution_reason(_r("high", "low", risk=(3,)), None)
    assert reason
    assert "%" not in reason


# ── Подпись ячейки ────────────────────────────────────────────────────────────
from app.m3_verdict import cell_label  # noqa: E402


def test_cell_label_names_both_axes_in_full():
    """
    «Низкая / Высокая» не говорит, чего низкая и чего высокая, а оси разные
    по природе: горизонталь про компанию, вертикаль про рынок.
    """
    assert cell_label("low", "high") == (
        "Низкая конкурентоспособность бизнеса / Высокая привлекательность рынка"
    )
    assert cell_label("high", "low") == (
        "Высокая конкурентоспособность бизнеса / Низкая привлекательность рынка"
    )
    assert cell_label("mid", "mid") == (
        "Средняя конкурентоспособность бизнеса / Средняя привлекательность рынка"
    )


def test_cell_label_does_not_call_the_x_axis_an_environment():
    """
    «Конкурентная среда» описывала бы рынок, и обе оси стали бы про рынок —
    различие, ради которого матрица существует, потерялось бы.
    """
    label = cell_label("low", "high")
    assert "среда" not in label
    assert "конкурентоспособность бизнеса" in label


def test_cell_label_rejects_unknown_level():
    with pytest.raises(ValueError):
        cell_label("unknown", "high")


# ── Вывод ячейки (§10.1a) ─────────────────────────────────────────────────────
from app import m3_verdict as vd  # noqa: E402


class TestCellBreakdownText:
    """
    Формулировка зафиксирована точной строкой. Она продублирована в
    frontend/lib/m3.ts (cellBreakdownText), автоматически их не сверить —
    поэтому пиньтуем питоновскую сторону, чтобы правка была заметна.
    """

    def test_two_yang_lines(self):
        d = {"level": "high", "sum": 75, "total": 100,
             "lines": [{"line": 2, "weight": 45}, {"line": 3, "weight": 30}]}
        assert vd.cell_breakdown_text("strength", d) == (
            "Сила: Ян на Л2 (45) + Л3 (30) = 75 из 100 → высокая"
        )

    def test_no_yang_lines(self):
        d = {"level": "low", "sum": 0, "total": 100, "lines": []}
        assert vd.cell_breakdown_text("attract", d) == (
            "Рынок: Ян нет — 0 из 100 → низкая"
        )
