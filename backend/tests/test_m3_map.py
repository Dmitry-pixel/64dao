# -*- coding: utf-8 -*-
"""
Метод 3 — геометрия карты портфеля.

Карта существует в двух экземплярах: PortfolioMap.tsx для веба и m3_map.py
для PDF. Это единственная часть отчёта, расхождение в которой не видно
глазом, поэтому она проверяется не «похоже ли», а сверкой с эталоном,
снятым прогоном настоящего кода фронта в Node.

Эталон пересобирается командой:
    node backend/tests/fixtures/gen_m3_map_reference.js

Тесты не поднимают БД и не требуют conftest: модуль чистый.
"""
import itertools
import json
import math
from pathlib import Path

import pytest

from app import m3_map
from app.m3_map import (
    CELL, EDGE_GAP, GRID, PAD_L, PAD_T, Placed,
    in_cell, layout, map_caption, radius, render_map_svg, vector,
)

FIXTURES = Path(__file__).parent / "fixtures"
CASES = json.loads((FIXTURES / "m3_map_cases.json").read_text(encoding="utf-8"))
REFERENCE = json.loads((FIXTURES / "m3_map_reference.json").read_text(encoding="utf-8"))


def _obj(oid="o1", position=1, name="Направление", cs="mid", ca="mid",
         coord_s=2.5, coord_a=2.5, target=(), risk=()):
    return {
        "object_id": oid, "position": position, "name": name,
        "cell_strength": cs, "cell_attract": ca,
        "coord_strength": coord_s, "coord_attract": coord_a,
        "cell_label": "Средняя / Средняя",
        "target_lines": list(target), "risk_lines": list(risk),
    }


# ── Сверка с эталоном веба ────────────────────────────────────────────────────
@pytest.mark.parametrize("case_name", sorted(CASES))
def test_layout_matches_web_reference(case_name):
    """
    Координаты, радиусы и векторы совпадают с прогоном PortfolioMap.tsx
    до последнего знака. Набор кейсов покрывает контрольный кейс пилота,
    совпавшие центры, границы шкалы, восемь направлений в одной ячейке,
    порядок обхода и долю, дающую радиус ровно .5.
    """
    case = CASES[case_name]
    placed = layout(case["results"], case["shares"])

    for result, expected in zip(case["results"], REFERENCE[case_name]):
        p = placed[result["object_id"]]
        where = f"{case_name}/{result['object_id']}"
        assert p.x == expected["x"], f"{where}: координата X разошлась с вебом"
        assert p.y == expected["y"], f"{where}: координата Y разошлась с вебом"
        assert p.r == expected["r"], f"{where}: радиус разошёлся с вебом"
        assert p.col == expected["col"] and p.row == expected["row"]

        for kind, key in (("target", "target"), ("risk", "risk")):
            got = vector(p, result[f"{kind}_lines"], kind)
            exp = expected[key]
            assert (got is None) == (exp is None), f"{where}: наличие вектора {kind}"
            if exp is not None:
                assert got == pytest.approx(exp), f"{where}: вектор {kind}"


def test_reference_covers_control_case():
    """Контрольный кейс пилота — пять направлений — в наборе присутствует."""
    assert len(CASES["control"]["results"]) == 5
    assert len(REFERENCE["control"]) == 5


# ── Радиус ────────────────────────────────────────────────────────────────────
def test_radius_half_rounds_up_like_js():
    """
    ЛОВУШКА, ради которой существует _js_round. Доля 6,25% даёт ровно 14,5:
    sqrt(0,0625) = 0,25 представимо в двоичной точно, 0,25 * 22 = 5,5.
    Math.round в JS → 15, round() в Python → 14 (округление к чётному).
    Радиус входит в раздвигание, поэтому ошибка сместила бы всю раскладку.
    """
    assert 9 + math.sqrt(6.25 / 100) * 22 == 14.5
    assert round(14.5) == 14           # поведение Python, которое нам не годится
    assert radius(6.25) == 15          # поведение веба, которое нам нужно


def test_radius_floor_and_ceiling():
    assert radius(None) == 9, "доля не указана — минимальный круг, не ноль"
    assert radius(0) == 9
    assert radius(100) == 31
    assert radius(150) == 31, "доля выше 100% зажимается"
    assert radius(-5) == 9, "отрицательная доля зажимается"


def test_radius_grows_by_area_not_radius():
    """Учетверение доли увеличивает радиус вдвое сверх пола в 9 пикселей."""
    assert radius(25) - 9 == pytest.approx((radius(100) - 9) / 2, abs=1)


# ── Позиция внутри ячейки ─────────────────────────────────────────────────────
def test_in_cell_uses_central_60_percent():
    """У краёв круги наезжали бы на соседние ячейки, и зона читалась бы неверно."""
    assert in_cell(0, 1.0) == pytest.approx(CELL * 0.2)
    assert in_cell(0, 4.0) == pytest.approx(CELL * 0.8)
    assert in_cell(0, 2.5) == pytest.approx(CELL * 0.5)


def test_in_cell_clamps_out_of_range_coords():
    assert in_cell(0, 0.0) == in_cell(0, 1.0)
    assert in_cell(0, 9.9) == in_cell(0, 4.0)


def test_in_cell_offsets_by_cell_index():
    assert in_cell(2, 2.5) - in_cell(0, 2.5) == pytest.approx(2 * CELL)


# ── Раскладка ─────────────────────────────────────────────────────────────────
def test_circle_never_leaves_its_own_cell():
    """
    Ячейка важнее координаты: она несёт зону, координата лишь уточняет место
    внутри. После раздвигания круг зажимается в границы своей ячейки.
    """
    case = CASES["eight_one_cell"]
    for oid, p in layout(case["results"], case["shares"]).items():
        left = PAD_L + p.col * CELL
        right = PAD_L + (p.col + 1) * CELL
        bottom = PAD_T + GRID - p.row * CELL
        top = PAD_T + GRID - (p.row + 1) * CELL
        assert left - 0.001 <= p.x <= right + 0.001, f"{oid} вышел за ячейку по X"
        assert top - 0.001 <= p.y <= bottom + 0.001, f"{oid} вышел за ячейку по Y"


def test_overlapping_directions_are_pushed_apart():
    """
    Направления 2 и 3 контрольного кейса стоят в одной ячейке. Без прохода
    раздвигания расстояние между центрами было 10 при сумме радиусов 36.
    """
    case = CASES["control"]
    placed = layout(case["results"], case["shares"])
    a, b = placed["o2"], placed["o3"]
    distance = math.hypot(b.x - a.x, b.y - a.y)
    assert distance > a.r + b.r, "круги одной ячейки продолжают накладываться"


def test_layout_is_deterministic():
    """Одинаковый расчёт обязан давать одинаковую картинку."""
    case = CASES["control"]
    first = layout(case["results"], case["shares"])
    second = layout(case["results"], case["shares"])
    assert {k: (v.x, v.y, v.r) for k, v in first.items()} == \
           {k: (v.x, v.y, v.r) for k, v in second.items()}


def test_layout_depends_on_input_order():
    """
    Раздвигание идёт цепочкой, поэтому порядок обхода значим. В отчёте
    направления идут в порядке ранга V — сортировка по позиции или по id
    даст другую картинку при тех же данных. Тест фиксирует зависимость,
    чтобы её не сочли случайной.
    """
    case = CASES["order_sensitive"]
    straight = layout(case["results"], case["shares"])
    reversed_ = layout(list(reversed(case["results"])), case["shares"])
    assert any(
        (straight[k].x, straight[k].y) != (reversed_[k].x, reversed_[k].y)
        for k in straight
    ), "порядок перестал влиять на раскладку — сверьте с PortfolioMap.tsx"


def test_coincident_centres_are_pushed_apart():
    """
    До 03.08.2026 полностью совпавшие координаты давали нулевой вектор
    отталкивания, и круги оставались друг на друге: два направления с
    одинаковыми баллами читались как одно. При шкале в два-три пункта
    совпадение вероятно, поэтому при нулевом расстоянии круги расходятся
    по углу от порядкового номера пары.
    """
    case = CASES["identical"]
    placed = layout(case["results"], case["shares"])
    points = {(p.x, p.y) for p in placed.values()}
    assert len(points) == len(case["results"]), (
        "круги снова слиплись — сверьте с PortfolioMap.tsx, "
        "затем пересоберите эталон"
    )
    for a, b in itertools.combinations(placed.values(), 2):
        assert math.hypot(b.x - a.x, b.y - a.y) > 1.0, "расхождение символическое"


# ── Векторы ───────────────────────────────────────────────────────────────────
def test_vector_absent_without_moving_lines():
    assert vector(Placed(200, 200, 20, 1, 1), [], "target") is None
    assert vector(Placed(200, 200, 20, 1, 1), [], "risk") is None


def test_target_and_risk_point_opposite_ways():
    """
    По горизонтали рост конкурентной силы идёт ВЛЕВО: ось развёрнута под
    матрицу GE/McKinsey. Поэтому целевой вектор ведёт влево, рисковый вправо.
    """
    p = Placed(200, 200, 20, 1, 1)
    target = vector(p, [1], "target")
    risk = vector(p, [1], "risk")
    assert target["x2"] < target["x1"] < p.x, "цель обязана вести к росту силы"
    assert risk["x2"] > risk["x1"] > p.x, "эрозия обязана вести к падению силы"


def test_target_goes_up_on_the_attractiveness_axis():
    """По вертикали разворота нет: рост привлекательности — вверх."""
    p = Placed(200, 200, 20, 1, 1)
    target = vector(p, [4], "target")
    risk = vector(p, [4], "risk")
    assert target["y2"] < target["y1"] < p.y
    assert risk["y2"] > risk["y1"] > p.y


def test_axis_follows_where_moving_lines_are():
    """Линии 1–3 — конкурентная сила (горизонталь), 4–6 — привлекательность."""
    p = Placed(200, 200, 20, 1, 1)
    horizontal = vector(p, [1, 2], "target")
    vertical = vector(p, [4, 5], "target")
    assert horizontal["y1"] == horizontal["y2"] == p.y
    assert vertical["x1"] == vertical["x2"] == p.x


def test_axis_tie_goes_horizontal():
    """При равенстве подвижных по осям ведём по горизонтали."""
    p = Placed(200, 200, 20, 1, 1)
    tie = vector(p, [3, 4], "target")
    assert tie["y1"] == tie["y2"] == p.y


def test_vector_starts_outside_the_circle():
    p = Placed(200, 200, 20, 1, 1)
    target = vector(p, [1], "target")
    assert abs(target["x1"] - p.x) > p.r, "стрелка начинается внутри круга"


# ── Ориентация осей ───────────────────────────────────────────────────────────
def test_strong_competitiveness_is_on_the_left():
    """
    Ось развёрнута под матрицу GE/McKinsey: сильная слева, слабая справа.
    До 03.08.2026 было наоборот, и направление с высокой силой при низкой
    привлекательности вставало в правый нижний угол — там, где в каноне
    стоит кандидат на закрытие.
    """
    strong = layout([_obj_geom("s", "high", "mid")], {"s": 20})["s"]
    weak = layout([_obj_geom("w", "low", "mid")], {"w": 20})["w"]
    assert strong.x < weak.x


def test_invest_zone_is_top_left_and_exit_is_bottom_right():
    invest = layout([_obj_geom("i", "high", "high")], {"i": 20})["i"]
    exit_ = layout([_obj_geom("e", "low", "low")], {"e": 20})["e"]
    assert invest.x < exit_.x, "«Инвестировать» обязана быть левее «Выходить»"
    assert invest.y < exit_.y, "«Инвестировать» обязана быть выше «Выходить»"


def test_stronger_coordinate_moves_left_inside_its_own_cell():
    """
    Внутри колонки зеркало тоже нужно: без него направление с силой 4,00
    встало бы у правого края сильной колонки, то есть ближе к средней.
    """
    stronger = layout([_obj_geom("a", "high", "mid", coord_s=4.0)], {"a": 20})["a"]
    weaker = layout([_obj_geom("b", "high", "mid", coord_s=1.0)], {"b": 20})["b"]
    assert stronger.x < weaker.x


def test_axis_labels_run_strong_to_weak():
    svg = render_map_svg([_obj("a", 1, "Первое")], {"a": 20})
    strong_at = svg.index("Сильная")
    weak_at = svg.index("Слабая")
    assert strong_at < weak_at, "подписи оси идут не в порядке сильная → слабая"


def _obj_geom(oid, cs, ca, coord_s=2.5, coord_a=2.5):
    return {"object_id": oid, "cell_strength": cs, "cell_attract": ca,
            "coord_strength": coord_s, "coord_attract": coord_a,
            "target_lines": [], "risk_lines": []}


# ── SVG ───────────────────────────────────────────────────────────────────────
def test_svg_draws_one_circle_per_direction():
    results = [_obj("a", 1, "Первое"), _obj("b", 2, "Второе", cs="high")]
    svg = render_map_svg(results, {"a": 40, "b": 20})
    assert svg.count("<circle") == 2
    assert ">1</text>" in svg and ">2</text>" in svg


def test_svg_marks_stable_direction_with_dashes():
    """Пунктир — подвижных линий нет, двигаться направлению сейчас нечем."""
    stable = render_map_svg([_obj("a", 1, "Стабильное")], {"a": 30})
    moving = render_map_svg([_obj("a", 1, "Подвижное", target=[1])], {"a": 30})
    assert 'stroke-dasharray="3 2"' in stable
    assert 'stroke-dasharray="3 2"' not in moving


def test_svg_draws_both_vectors_for_direction_with_both():
    svg = render_map_svg([_obj("a", 1, "Оба", target=[3], risk=[4])], {"a": 30})
    assert svg.count("marker-end=") == 2, "нарисованы не обе стрелки"
    assert "url(#m3-up)" in svg and "url(#m3-dn)" in svg

    one_way = render_map_svg([_obj("a", 1, "Только цель", target=[3])], {"a": 30})
    assert one_way.count("marker-end=") == 1


def test_svg_escapes_direction_name_in_aria_label():
    svg = render_map_svg([_obj("a", 1, '<script>alert(1)</script>')], {"a": 30})
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_svg_has_no_react_only_attributes():
    """Playwright печатает inline SVG; camelCase-атрибуты React ему чужие."""
    svg = render_map_svg([_obj("a", 1, "Первое", target=[1])], {"a": 30})
    for attribute in ("strokeWidth", "textAnchor", "strokeDasharray", "markerEnd"):
        assert attribute not in svg


def test_numbers_are_formatted_like_js():
    """Целые без дробной части: '106', а не '106.0'."""
    svg = render_map_svg([_obj("a", 1, "Первое", coord_s=2.5, coord_a=2.5)], {"a": 0})
    assert 'cx="205"' in svg


# ── Подпись ───────────────────────────────────────────────────────────────────
def test_caption_mentions_only_what_is_on_the_map():
    only_target = map_caption([_obj("a", 1, "A", target=[1])])
    assert "Синяя стрелка" in only_target
    assert "Красная" not in only_target
    assert "Пунктирный" not in only_target

    only_stable = map_caption([_obj("a", 1, "A")])
    assert "Пунктирный" in only_stable
    assert "Синяя стрелка" not in only_stable


def test_caption_always_explains_circle_size():
    assert "доля направления в выручке" in map_caption([_obj()])


# ── Обрезка вектора по рамке ──────────────────────────────────────────────────
from app.m3_map import VECTOR_MIN, _clip_to_grid  # noqa: E402


def test_arrow_never_leaves_the_grid():
    """
    Длина вектора фиксированная, а зажимается только круг. У направления
    в крайней ячейке стрелка уезжала за сетку и висела в пустоте.
    """
    for case in CASES.values():
        placed = layout(case["results"], case["shares"])
        for r in case["results"]:
            p = placed[r["object_id"]]
            for kind in ("target", "risk"):
                v = vector(p, r[f"{kind}_lines"], kind)
                if v is None:
                    continue
                for key in ("x1", "x2"):
                    assert PAD_L - 0.001 <= v[key] <= PAD_L + GRID + 0.001
                for key in ("y1", "y2"):
                    assert PAD_T - 0.001 <= v[key] <= PAD_T + GRID + 0.001


def test_arrow_is_dropped_when_clipping_leaves_a_stub():
    """
    Огрызок в три пикселя направления не показывает. Цель и риск всё равно
    названы номерами гексаграмм в таблице под картой, так что информация
    не теряется.
    """
    outside = {"x1": PAD_L + GRID + 5, "y1": 100, "x2": PAD_L + GRID + 47, "y2": 100}
    assert _clip_to_grid(outside) is None


def test_arrow_survives_clipping_when_enough_remains():
    partly = {"x1": PAD_L + GRID - 30, "y1": 100, "x2": PAD_L + GRID + 12, "y2": 100}
    clipped = _clip_to_grid(partly)
    assert clipped is not None
    assert clipped["x2"] == PAD_L + GRID
    assert clipped["x2"] - clipped["x1"] >= VECTOR_MIN


# ── Ключи долей выручки ───────────────────────────────────────────────────────
# Дефект живого отчёта: в PDF все круги рисовались одного минимального
# размера, а в вебе — по доле выручки. Причина не в геометрии, а в типах
# ключей: сборщик PDF строит доли из ORM (str(uuid)), а object_id в
# результате расчёта остаётся uuid.UUID. Лукап молча не находил долю.

def _one_object_case(object_id):
    return [{
        "object_id": object_id, "position": 1, "name": "Направление",
        "cell_strength": "low", "cell_attract": "mid", "cell_label": "x",
        "coord_strength": 2.0, "coord_attract": 2.0,
        "target_lines": [4], "risk_lines": [5],
    }]


def test_share_lookup_survives_uuid_keys():
    """Ключ-UUID и ключ-строка дают один и тот же радиус."""
    import uuid as _uuid

    oid = _uuid.uuid4()
    by_str = layout(_one_object_case(oid), {str(oid): 45.0})
    by_uuid = layout(_one_object_case(oid), {oid: 45.0})
    assert by_str[oid].r == by_uuid[oid].r == radius(45.0)


def test_map_svg_identical_for_both_key_types():
    """Расхождение веба и PDF было видно именно на собранном SVG."""
    import uuid as _uuid

    oid = _uuid.uuid4()
    assert (render_map_svg(_one_object_case(oid), {str(oid): 45.0})
            == render_map_svg(_one_object_case(oid), {oid: 45.0}))


def test_missing_share_still_falls_back_to_minimum():
    """Доля неизвестна — минимальный радиус, а не исключение."""
    import uuid as _uuid

    oid = _uuid.uuid4()
    assert layout(_one_object_case(oid), {})[oid].r == radius(None)
