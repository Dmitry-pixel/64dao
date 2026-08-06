# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — юнит-тесты расчётного ядра. Без БД и фикстур.

Обязательный минимум из §8 инструкции разработчику:
  1. маппинг кода в номер: пять контрольных значений + полный обход 64 кодов;
  2. контрольный кейс целиком: коды, номера, целевые и рисковые гексаграммы,
     ячейки, координаты, V, Z, ранги;
  3. портфельные агрегаты контрольного кейса: 18 · 4 · 0 · 4 ячейки · Спирмен 0,60;
  4. свойство шкалы: ни один достижимый балл не равен 1,50 · 2,50 · 3,50;
  5. вето по убыточности;
  6. целевая и рисковая гексаграммы порознь;
  7. инфлированная анкета: SELF_INFLATION, STRAIGHTLINING, verdicts_held.

Фикстура — контрольный кейс из metod-3-pilot-template.xlsx (производитель
косметики, 5 направлений). Ожидаемые значения взяты с листа «Расчёт».
"""
import itertools
import json

import pytest

from app.hexagrams import HEXAGRAM_LIST, hexagram_by_code
from app.m3_config import DEFAULT_M3_CONFIG, industry_weights, average_presets
from app import m3_scoring as sc
from app.m3_scoring import (
    BLOCK_ARBITER, BLOCK_MARKET, BLOCK_OBJECT, ITEM_LINE, REVERSE_ITEMS,
    InvalidAnswerError, LineUndefinedError, PortfolioSizeError,
    arbiter_required, calculate, effective_value, leading_lines, line_scores,
    r2, rank_desc, score_object, spearman, tensions, trajectory,
)

# ── Контрольный кейс ──────────────────────────────────────────────────────────
PORTFOLIO_ANSWERS = {
    f"{BLOCK_MARKET}1": 2, f"{BLOCK_MARKET}2": 2, f"{BLOCK_MARKET}3": 3,
    f"{BLOCK_MARKET}4": 3, f"{BLOCK_MARKET}5": 3, f"{BLOCK_MARKET}6": 2,
}


def _obj(position, name, revenue, dyn, share, profitability, industry, answers):
    return {
        "id": position, "position": position, "name": name,
        "revenue": revenue, "revenue_dynamics": dyn, "revenue_share": share,
        "profitability": profitability, "industry_id": industry,
        "answers": answers,
    }


def _a(**kw):
    """Ответы направления: n1..n8 -> Н1..Н8, a1..a4 -> А1..А4, p1s.. -> Р1*.."""
    out = {}
    for k, v in kw.items():
        if k.startswith("n"):
            out[f"{BLOCK_OBJECT}{k[1:]}"] = v
        elif k.startswith("a"):
            out[f"{BLOCK_ARBITER}{k[1:]}"] = v
        elif k.startswith("p"):
            out[f"{BLOCK_MARKET}{k[1:]}*"] = v
        else:  # pragma: no cover
            raise KeyError(k)
    return out


CONTROL_CASE = {
    "industry_id": 2,
    "answers": PORTFOLIO_ANSWERS,
    "owner_ranks": [3, 1, 5, 4, 2],
    "objects": [
        _obj(1, "Салонный канал B2B", 180, -5, 45, "profitable", 2,
             _a(n1=3, n2=2, n3=3, n4=2, n5=4, n6=1, n7=2, n8=3)),
        _obj(2, "Маркетплейсы", 120, 60, 30, "marginal", 7,
             _a(n1=2, n2=3, n3=3, n4=2, n5=1, n6=4, n7=4, n8=1,
                p1=1, p2=2, p3=3)),
        _obj(3, "Интернет-магазин", 32, 10, 8, "marginal", 7,
             _a(n1=3, n2=2, n3=2, n4=3, n5=2, n6=3, n7=3, n8=2)),
        _obj(4, "Контрактное пр-во", 48, 15, 12, "profitable", 2,
             _a(n1=3, n2=2, n3=2, n4=3, n5=3, n6=3, a3=3, n7=3, n8=2)),
        _obj(5, "Обучение мастеров", 20, 40, 5, "marginal", 10,
             _a(n1=1, n2=4, n3=3, n4=2, n5=2, n6=3, n7=3, n8=2,
                p1=3, p2=3, p3=3, p4=4, p5=3, p6=2)),
    ],
}

# Лист «Расчёт» шаблона пилота.
EXPECTED = [
    {"name": "Салонный канал B2B",
     "scores": [3.00, 3.00, 4.00, 2.00, 2.00, 3.00],
     "symbols": "AAABBA", "hex": 26, "cell": "high_low",
     "cs": 3.30, "ca": 2.25, "target": None, "risk": 41,
     "v": 0.4909, "z": 0.4700, "vr": 5, "zr": 1},
    {"name": "Маркетплейсы",
     "scores": [2.00, 3.00, 1.00, 4.00, 1.67, 3.00],
     "symbols": "BABABA", "hex": 64, "cell": "low_mid",
     "cs": 1.80, "ca": 2.87, "target": 50, "risk": 4,
     "v": 0.5472, "z": 0.3800, "vr": 2, "zr": 2},
    {"name": "Интернет-магазин",
     "scores": [3.00, 2.00, 2.00, 3.00, 2.00, 3.00],
     "symbols": "ABBABA", "hex": 21, "cell": "low_mid",
     "cs": 2.30, "ca": 2.60, "target": None, "risk": None,
     "v": 0.5083, "z": 0.0480, "vr": 4, "zr": 4},
    {"name": "Контрактное пр-во",
     "scores": [3.00, 2.00, 2.67, 3.00, 2.00, 3.00],
     "symbols": "ABAABA", "hex": 30, "cell": "mid_mid",
     "cs": 2.65, "ca": 2.55, "target": None, "risk": None,
     "v": 0.5350, "z": 0.0720, "vr": 3, "zr": 3},
    {"name": "Обучение мастеров",
     "scores": [1.00, 3.00, 2.00, 3.00, 2.67, 3.33],
     "symbols": "BABAAA", "hex": 6, "cell": "low_high",
     "cs": 2.15, "ca": 3.00, "target": 10, "risk": None,
     "v": 0.6192, "z": 0.0300, "vr": 1, "zr": 5},
]


@pytest.fixture(scope="module")
def control():
    return calculate(CONTROL_CASE)


# ── 1. Маппинг кода в номер гексаграммы ───────────────────────────────────────
class TestHexagramMapping:
    """Контрольные значения действующей методички воспроизводятся точно."""

    @pytest.mark.parametrize("code,number", [
        ("AAAABB", 34), ("AAAABA", 14), ("BBAABB", 62),
        ("BAAABB", 32), ("BAABBB", 46),
    ])
    def test_reference_values(self, code, number):
        assert hexagram_by_code(code)[0] == number

    def test_all_64_codes_unique(self):
        codes = ["".join(c) for c in itertools.product("AB", repeat=6)]
        assert len(codes) == 64
        numbers = [hexagram_by_code(c)[0] for c in codes]
        assert sorted(numbers) == list(range(1, 65))

    def test_single_source_of_truth(self):
        """Второй таблицы соответствия в проекте быть не должно."""
        assert len(HEXAGRAM_LIST) == 64
        for num, name, code in HEXAGRAM_LIST:
            assert hexagram_by_code(code) == (num, name)

    def test_unknown_code_raises(self):
        with pytest.raises(KeyError):
            hexagram_by_code("AAAAAC")


# ── Алфавит анкеты ────────────────────────────────────────────────────────────
class TestItemCodes:
    def test_block_letters_are_cyrillic(self):
        """Латинские P/H/A визуально неотличимы от Р/Н/А и ломают анкету."""
        assert (ord(BLOCK_MARKET), ord(BLOCK_OBJECT), ord(BLOCK_ARBITER)) == (
            0x0420, 0x041D, 0x0410
        )

    def test_item_line_map_is_complete(self):
        # 6 Р + 6 Р* + 8 Н + 4 А
        assert len(ITEM_LINE) == 24
        assert ITEM_LINE[f"{BLOCK_OBJECT}1"] == 1
        assert ITEM_LINE[f"{BLOCK_OBJECT}8"] == 4
        assert ITEM_LINE[f"{BLOCK_MARKET}3"] == 5
        assert ITEM_LINE[f"{BLOCK_MARKET}4*"] == 6

    def test_reverse_items(self):
        assert len(REVERSE_ITEMS) == 8
        assert effective_value(f"{BLOCK_OBJECT}2", 4) == 1.0
        assert effective_value(f"{BLOCK_OBJECT}1", 4) == 4.0

    @pytest.mark.parametrize("bad", [0, 5, -1, 2.5, True, "3"])
    def test_invalid_raw_rejected(self, bad):
        with pytest.raises(InvalidAnswerError):
            effective_value(f"{BLOCK_OBJECT}1", bad)


# ── 2. Контрольный кейс целиком ───────────────────────────────────────────────
class TestControlCase:
    def test_object_count(self, control):
        assert len(control["objects"]) == 5

    @pytest.mark.parametrize("i", range(5))
    def test_line_scores(self, control, i):
        got = control["objects"][i]["scores"]
        assert [got[f"l{n}"] for n in range(1, 7)] == EXPECTED[i]["scores"]

    @pytest.mark.parametrize("i", range(5))
    def test_symbols_and_number(self, control, i):
        r, e = control["objects"][i], EXPECTED[i]
        assert r["symbols"] == e["symbols"]
        assert r["current_hex"] == e["hex"]

    @pytest.mark.parametrize("i", range(5))
    def test_cells(self, control, i):
        assert control["objects"][i]["cell_key"] == EXPECTED[i]["cell"]

    @pytest.mark.parametrize("i", range(5))
    def test_coordinates(self, control, i):
        r, e = control["objects"][i], EXPECTED[i]
        assert (r["coord_strength"], r["coord_attract"]) == (e["cs"], e["ca"])

    @pytest.mark.parametrize("i", range(5))
    def test_trajectory(self, control, i):
        r, e = control["objects"][i], EXPECTED[i]
        assert r["target_hex"] == e["target"]
        assert r["risk_hex"] == e["risk"]

    @pytest.mark.parametrize("i", range(5))
    def test_indices_and_ranks(self, control, i):
        r, e = control["objects"][i], EXPECTED[i]
        assert r["v_index"] == e["v"]
        assert r["z_index"] == e["z"]
        assert r["v_rank"] == e["vr"]
        assert r["z_rank"] == e["zr"]

    def test_cash_cow_last_by_v_first_by_z(self, control):
        """Ровно то поведение, которого не хватало наивной формуле (§16)."""
        cow = control["objects"][0]
        assert cow["v_rank"] == 5 and cow["z_rank"] == 1

    def test_arbiter_only_on_line3_of_object4(self):
        need = {
            o["position"]: arbiter_required(PORTFOLIO_ANSWERS, o["answers"])
            for o in CONTROL_CASE["objects"]
        }
        assert need == {1: [], 2: [], 3: [], 4: [3], 5: []}

    def test_object_flags(self, control):
        got = {o["name"]: set(o["flags"]) for o in control["objects"]}
        assert got["Салонный канал B2B"] == set()
        assert got["Маркетплейсы"] == {"NEAR_OLD_YIN", "SCALE_CONTRADICTION"}
        assert got["Интернет-магазин"] == set()
        assert got["Контрактное пр-во"] == {"BORDERLINE_LINE"}
        assert got["Обучение мастеров"] == {"BORDERLINE_LINE", "NEAR_OLD_YANG"}

    def test_tensions_limited_to_three(self, control):
        by_name = {o["name"]: o["tensions"] for o in control["objects"]}
        assert by_name["Маркетплейсы"] == ["P1", "P3", "P4"]
        assert by_name["Интернет-магазин"] == ["P4", "P5", "P10"]
        for t in by_name.values():
            assert len(t) <= 3

    def test_market_lines_inherited_unless_overridden(self, control):
        """
        Направления 1, 3, 4 не переопределяли рынок — Л5 и Л6 у них общие.
        Несогласованность образца отчёта (§12.2 спецификации) не воспроизводится.
        """
        s = [o["scores"] for o in control["objects"]]
        assert s[0]["l5"] == s[2]["l5"] == s[3]["l5"] == 2.00
        assert s[0]["l6"] == s[2]["l6"] == s[3]["l6"] == 3.00


# ── 3. Портфельные агрегаты ───────────────────────────────────────────────────
class TestControlPortfolio:
    def test_aggregates(self, control):
        p = control["portfolio"]
        assert p["sum_positions"] == 18
        assert p["sum_positions_max"] == 30
        assert p["turbulence"] == 4
        assert p["old_yin_total"] == 2
        assert p["old_yang_total"] == 2
        assert p["delta"] == 0
        assert p["distinct_cells"] == 4

    def test_spearman_in_pilot_corridor(self, control):
        rho = control["portfolio"]["spearman"]
        assert rho == 0.60
        assert 0.50 <= rho <= 0.85          # критерий 3 пилота

    def test_no_portfolio_flags_verdicts_released(self, control):
        assert control["portfolio"]["flags"] == []
        assert control["portfolio"]["verdicts_held"] is False

    def test_pilot_acceptance_metrics(self, control):
        p = control["portfolio"]
        assert p["distinct_cells"] >= 3      # критерий 1
        assert p["spread_share"] == 0.50     # критерий 2: не более 0,50

    def test_portfolio_size_bounds(self):
        with pytest.raises(PortfolioSizeError):
            calculate({**CONTROL_CASE, "objects": CONTROL_CASE["objects"][:2]})
        with pytest.raises(PortfolioSizeError):
            calculate({**CONTROL_CASE, "objects": CONTROL_CASE["objects"] * 2})


# ── 4. Свойство шкалы ─────────────────────────────────────────────────────────
class TestScaleProperty:
    """
    Тест на конструкцию, а не на данные: он ломается, если сломано правило
    арбитра. Пограничных случаев в методе не остаётся в принципе.
    """
    THRESHOLDS = {1.50, 2.50, 3.50}

    def test_two_item_lines_after_arbiter_rule(self):
        cfg = DEFAULT_M3_CONFIG
        reachable = set()
        for a, b in itertools.product((1, 2, 3, 4), repeat=2):
            needs = abs(a - b) >= cfg["arbiter_gap"] or r2((a + b) / 2) in cfg["arbiter_midpoints"]
            if needs:
                for c in (1, 2, 3, 4):
                    reachable.add(r2((a + b + c) / 3))
            else:
                reachable.add(r2((a + b) / 2))
        assert not (reachable & self.THRESHOLDS)
        assert {1.00, 2.00, 3.00, 4.00} <= reachable

    def test_three_item_lines(self):
        reachable = {
            r2(sum(t) / 3) for t in itertools.product((1, 2, 3, 4), repeat=3)
        }
        assert not (reachable & self.THRESHOLDS)

    def test_flag_windows_hit_reachable_values(self):
        cfg = DEFAULT_M3_CONFIG
        assert cfg["borderline_line"][0] <= 2.33 <= cfg["borderline_line"][1]
        assert cfg["borderline_line"][0] <= 2.67 <= cfg["borderline_line"][1]
        assert cfg["near_old_yang"][0] <= 3.33 <= cfg["near_old_yang"][1]
        assert cfg["near_old_yin"][0] <= 1.67 <= cfg["near_old_yin"][1]
        # 2,00 и 3,00 — уверенные оценки полного согласия, флага не получают.
        for v in (2.00, 3.00):
            assert not (cfg["borderline_line"][0] <= v <= cfg["borderline_line"][1])

    def test_arbiter_fires_on_every_threshold_midpoint(self):
        for a, b in [(1, 2), (2, 3), (3, 4)]:
            answers = {f"{BLOCK_OBJECT}1": a, f"{BLOCK_OBJECT}2": 5 - b}
            assert 1 in arbiter_required(PORTFOLIO_ANSWERS, answers)

    def test_arbiter_fires_on_gap_two(self):
        answers = {f"{BLOCK_OBJECT}1": 1, f"{BLOCK_OBJECT}2": 2}   # 1 и 3
        assert 1 in arbiter_required(PORTFOLIO_ANSWERS, answers)


# ── 5. Вето ───────────────────────────────────────────────────────────────────
class TestVeto:
    def _one(self, profitability, n1=4, n2=1):
        obj = _obj(1, "X", 100, 0, 10, profitability, 2,
                   _a(n1=n1, n2=n2, n3=3, n4=2, n5=3, n6=2, n7=3, n8=2))
        return score_object(obj, PORTFOLIO_ANSWERS)

    def test_unprofitable_forces_yin_on_line1(self):
        r = self._one("unprofitable")
        assert r["scores"]["l1"] == 4.00        # балл не трогаем
        assert r["symbols"][0] == "B"           # символ принудительно Инь
        assert "VETO_UNPROFITABLE" in r["flags"]
        assert "ECONOMY_CONTRADICTION" in r["flags"]

    def test_mobility_by_actual_score(self):
        r = self._one("unprofitable")
        assert r["mobility"]["1"] == "old_yang"
        assert "VETO_MOBILITY_CONFLICT" in r["flags"]

    def test_profitable_keeps_yang(self):
        r = self._one("profitable")
        assert r["symbols"][0] == "A"
        assert "VETO_UNPROFITABLE" not in r["flags"]

    def test_unknown_flags_but_does_not_veto(self):
        r = self._one("unknown")
        assert r["symbols"][0] == "A"
        assert "VETO_UNKNOWN" in r["flags"]
        assert "VETO_UNPROFITABLE" not in r["flags"]


# ── 6. Целевая и рисковая гексаграммы ─────────────────────────────────────────
class TestTrajectory:
    def test_no_old_yin_no_target(self):
        t = trajectory("AAABBA", {3: "old_yang"})
        assert t["target_hex"] is None
        assert t["risk_hex"] == 41 and t["risk_lines"] == [3]

    def test_no_old_yang_no_risk(self):
        t = trajectory("BABAAA", {1: "old_yin"})
        assert t["risk_hex"] is None
        assert t["target_hex"] == 10 and t["target_lines"] == [1]

    def test_no_moving_lines_stable(self):
        t = trajectory("ABBABA", {})
        assert t["target_hex"] is None and t["risk_hex"] is None

    def test_both_groups_never_inverted_together(self):
        """
        Гексаграмма от одновременной инверсии старых Инь и старых Ян
        не описывает ни один реальный сценарий (§14).
        """
        symbols, mob = "BABABA", {3: "old_yin", 4: "old_yang"}
        t = trajectory(symbols, mob)
        assert t["target_hex"] == 50 and t["risk_hex"] == 4
        assert t["target_hex"] != t["risk_hex"]
        both = hexagram_by_code("BAABBA")[0]     # инверсия Л3 и Л4 сразу
        assert both not in (t["target_hex"], t["risk_hex"])

    def test_target_and_risk_differ_from_current(self):
        t = trajectory("BABABA", {3: "old_yin", 4: "old_yang"})
        assert t["target_code"] != "BABABA" != t["risk_code"]


# ── 7. Инфлированная анкета ───────────────────────────────────────────────────
class TestSelfInflation:
    @staticmethod
    @pytest.fixture(scope="class")
    def inflated():
        answers = _a(n1=4, n2=4, n3=4, n4=4, n5=4, n6=4, n7=4, n8=4,
                     a1=4, a2=4, a3=4, a4=4)
        market = {f"{BLOCK_MARKET}{i}": 4 for i in range(1, 7)}
        objects = [
            _obj(i, f"Направление {i}", 100, 0, 100 / 3, "profitable", 18, dict(answers))
            for i in range(1, 4)
        ]
        return calculate({"industry_id": 18, "answers": market, "objects": objects})

    def test_all_lines_equal_three(self, inflated):
        for o in inflated["objects"]:
            assert set(o["scores"].values()) == {3.00}

    def test_straightlining_on_every_object(self, inflated):
        for o in inflated["objects"]:
            assert "STRAIGHTLINING" in o["flags"]

    def test_portfolio_flags_and_hold(self, inflated):
        p = inflated["portfolio"]
        assert "SELF_INFLATION" in p["flags"]
        assert "UNIFORM_PORTFOLIO" in p["flags"]
        assert p["verdicts_held"] is True

    def test_control_case_not_inflated(self, control):
        assert "SELF_INFLATION" not in control["portfolio"]["flags"]


# ── Ведущие линии и разрешение ничьих ─────────────────────────────────────────
class TestLeadingLines:
    def test_weak_tie_takes_lower_line(self):
        scores = {1: 3.0, 2: 2.0, 3: 2.0, 4: 3.0, 5: 2.0, 6: 3.0}
        assert leading_lines(scores)["weak_line"] == 2

    def test_strong_tie_takes_upper_line(self):
        scores = {1: 3.0, 2: 2.0, 3: 2.0, 4: 3.0, 5: 2.0, 6: 3.0}
        assert leading_lines(scores)["strong_line"] == 6

    def test_weak_and_strong_coincide_only_on_straightlining(self):
        flat = {n: 3.0 for n in range(1, 7)}
        led = leading_lines(flat)
        assert led["weak_line"] == 1 and led["strong_line"] == 6


# ── Вспомогательные функции ───────────────────────────────────────────────────
class TestHelpers:
    def test_rank_desc_is_permutation(self):
        assert rank_desc([0.49, 0.55, 0.51, 0.53, 0.62]) == [5, 2, 4, 3, 1]
        assert sorted(rank_desc([1.0, 1.0, 1.0])) == [1, 2, 3]

    def test_spearman_control_value(self):
        assert spearman([5, 2, 4, 3, 1], [3, 1, 5, 4, 2]) == 0.60

    def test_spearman_identity_and_inverse(self):
        assert spearman([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == 1.00
        assert spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == -1.00

    def test_industry_weights_sum_to_100_per_axis(self):
        for iid in DEFAULT_M3_CONFIG["industry_presets"]:
            w = industry_weights(iid)
            assert w["L1"] + w["L2"] + w["L3"] == 100
            assert w["L4"] + w["L5"] + w["L6"] == 100

    def test_unknown_industry_falls_back_to_universal(self):
        assert industry_weights(999) == industry_weights(18)
        assert industry_weights(None) == industry_weights(18)

    def test_string_keys_survive_json_roundtrip(self):
        """
        Конфиг, сохранённый через админку, вернётся из JSON со строковыми
        ключами. Молчаливый уход в универсальный пресет здесь опаснее падения:
        расчёт продолжится и отдаст неверные координаты.
        """
        cfg = json.loads(json.dumps(DEFAULT_M3_CONFIG))
        assert set(cfg["industry_presets"]) == {str(i) for i in range(1, 19)}
        assert industry_weights(2, cfg) == industry_weights(2)
        assert industry_weights(12, cfg)["L1"] == 55

    def test_average_presets_normalised(self):
        w = average_presets([1, 2, 7])
        assert w["L1"] + w["L2"] + w["L3"] == 100
        assert w["L4"] + w["L5"] + w["L6"] == 100

    def test_line_undefined_when_all_unknown(self):
        answers = {f"{BLOCK_OBJECT}{i}": None for i in range(1, 9)}
        with pytest.raises(LineUndefinedError):
            line_scores(PORTFOLIO_ANSWERS, answers)

    def test_partial_unknown_averages_the_rest(self):
        answers = _a(n1=3, n3=3, n4=2, n5=3, n6=2, n7=3, n8=2)
        answers[f"{BLOCK_OBJECT}2"] = None
        assert line_scores(PORTFOLIO_ANSWERS, answers)[1] == 3.00

    def test_tension_p7_phase_transition(self):
        assert "P7" in tensions("AAAAAA", {1: "old_yang", 2: "old_yang", 3: "old_yang"})

    def test_tension_p6_needs_old_yang_on_line3(self):
        assert "P6" in tensions("AAAAAA", {3: "old_yang"})
        assert "P6" not in tensions("AAAAAA", {3: "old_yin"})


# ── Колонка «Рынок»: чей рыночный слой пошёл в расчёт ─────────────────────────

def test_market_override_count_matches_resolution_rule():
    """Считается тем же признаком, что и подмена: ответ есть и не «не знаю»."""
    answers = {"Р1*": 3, "Р2*": 2, "Р3*": 1}
    assert sc.market_override_count(answers) == 3


def test_market_override_count_ignores_dont_know():
    """value IS NULL — «не знаю»: resolve_line_items такой ответ не подменяет,
    значит и колонка не должна называть направление переопределённым."""
    assert sc.market_override_count({"Р1*": None, "Р2*": 4}) == 1


def test_market_override_count_ignores_portfolio_answers():
    """Пункты без звёздочки — общий блок портфеля, не переопределение."""
    assert sc.market_override_count({"Р1": 3, "Р2": 4}) == 0


def test_market_override_count_full_set():
    full = {f"Р{i}*": 2 for i in range(1, 7)}
    assert sc.market_override_count(full) == sc.MARKET_ITEMS_TOTAL


def test_partial_override_actually_changes_line_score():
    """Проверка, что частичное переопределение — рабочее состояние, а не
    недозаполненность: один ответ Р* уже меняет балл линии."""
    portfolio = {"Р1": 1, "Р2": 1, "Р3": 1}
    without = sc.line_score(5, portfolio, {})
    with_one = sc.line_score(5, portfolio, {"Р1*": 4})
    assert with_one > without
