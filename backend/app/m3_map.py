# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — карта портфеля для PDF.

Отдельный модуль, а не часть m3_pdf: это единственный кусок отчёта, который
не верстает, а считает, и единственный, который может разойтись с вебом
молча. Текст, разъехавшийся с фронтом, видно глазом; точку, сдвинутую на три
пикселя, — нет. Отдельный модуль даёт отдельный тест на геометрию.

Порт frontend/components/m3/PortfolioMap.tsx. Алгоритм повторяется буквально,
включая порядок обхода и мутацию точек внутри цикла: результат зависит и от
того, и от другого. Расхождения с оригиналом, которые пришлось обойти явно,
помечены в коде словом ЛОВУШКА.

Синхронизация с фронтом ручная — конвенция проекта (так же сделан
finance_pdf для Метода 2). Тест test_m3_map сверяет вывод с фикстурой,
снятой прогоном настоящего PortfolioMap.tsx в Node.
"""
from __future__ import annotations

import html as html_lib
import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

# ── Геометрия. Значения обязаны совпадать с PortfolioMap.tsx ──────────────────
PAD_L = 70
PAD_T = 20
GRID = 270
CELL = GRID / 3
VB_W = 400
VB_H = 330

MAX_PASSES = 60      # столько же проходов раздвигания, сколько в вебе
MIN_GAP = 4          # зазор между кругами
EDGE_GAP = 2         # отступ круга от границы своей ячейки
VECTOR_LEN = 42
VECTOR_GAP = 6
VECTOR_MIN = 10      # короче этого стрелка нечитаема — лучше не рисовать

C_PAPER = "#f4f2ec"
C_LINE = "#cfc9bc"
C_DARK = "#1a2540"
C_MUTED = "#6b6559"
C_BLUE = "#1e3a8a"
C_RED = "#c0392b"

# Строка — привлекательность рынка. Индекс 0 — нижний ряд, «низкая».
ROW_INDEX = {"low": 0, "mid": 1, "high": 2}

# Колонка — конкурентная сила. Ось направлена как в матрице GE/McKinsey:
# СИЛЬНАЯ СЛЕВА, слабая справа. Поэтому «Инвестировать» приходится на левый
# верхний угол, а «Избегать / выходить» — на правый нижний, и клиент,
# видевший матрицу раньше, читает картинку без переучивания.
#
# До 03.08.2026 ось шла наоборот (low: 0), и направление с высокой силой при
# низкой привлекательности вставало в правый нижний угол — то есть туда, где
# в каноне стоит кандидат на закрытие. Смысл ячейки был верен, читалась она
# противоположно.
COL_INDEX = {"high": 0, "mid": 1, "low": 2}

# Знак горизонтали. Рост конкурентной силы теперь идёт влево, поэтому целевой
# вектор по горизонтали ведёт влево, а рисковый вправо.
X_SIGN = -1


def _js_round(x: float) -> int:
    """
    ЛОВУШКА. Math.round в JS округляет 0,5 вверх, round() в Python — к
    чётному. Радиус входит в раздвигание, поэтому расхождение на единицу
    смещает не один круг, а всю раскладку.

    Проверяемый пример: доля 6,25% даёт 9 + sqrt(0,0625)*22 = 14,5 ровно
    (0,25 представимо в двоичной точно). Math.round → 15, round → 14.
    """
    return math.floor(x + 0.5)


def _num(v: float) -> str:
    """Число в строку так же, как это делает JS при подстановке в атрибут:
    целое без дробной части, дробное — кратчайшим представлением."""
    f = float(v)
    if f == int(f):
        return str(int(f))
    return repr(f)


def e(text: str | None) -> str:
    return html_lib.escape(text or "", quote=True)


# ── Раскладка ─────────────────────────────────────────────────────────────────
@dataclass
class Placed:
    x: float
    y: float
    r: int
    col: int
    row: int


def in_cell(index: int, coord: float, reverse: bool = False) -> float:
    """
    Позиция внутри ячейки: 0,2 … 0,8 от её ширины по координате 1…4.

    reverse нужен горизонтали. Ось силы направлена вправо-налево, и без
    зеркала направление с силой 4,00 внутри сильной колонки встало бы у её
    правого края — то есть ближе к средней колонке, а не дальше от неё.
    """
    f = min(1.0, max(0.0, (coord - 1) / 3))
    if reverse:
        f = 1.0 - f
    return index * CELL + CELL * (0.2 + 0.6 * f)


def radius(share: float | None) -> int:
    """
    Радиус по доле выручки. Пропорциональна доле площадь, а не радиус: глаз
    сравнивает площади, и линейный радиус преувеличил бы крупные направления
    втрое. Пол в 9 пикселей — иначе доля 3% превращается в точку.
    """
    s = min(100.0, max(0.0, float(share) if share is not None else 0.0))
    return _js_round(9 + math.sqrt(s / 100) * 22)


def layout(
    results: list[dict[str, Any]],
    shares: dict[str, float | None],
) -> dict[str, Placed]:
    """
    Ячейку задаёт сумма отраслевых весов сильных линий, координата ставит точку
    внутри уже выбранной ячейки. После координатной расстановки идёт
    детерминированный проход раздвигания: пары отталкиваются вдоль линии
    центров, затем каждый круг зажимается в границы СВОЕЙ ячейки. Ячейка
    важнее точной позиции — она несёт зону.

    ЛОВУШКА. Порядок обхода задан порядком `results`, а в вебе это порядок
    после сортировки по рангу V. Список, отсортированный по позиции или по
    id, даст другую картинку при тех же данных.

    ЛОВУШКА. Точки правятся по ссылке прямо внутри двойного цикла, и
    следующая пара видит уже сдвинутые координаты. Порт на неизменяемых
    структурах даёт другой результат.
    """
    # Ключи долей приводим к строке. Веб-отчёт отдаёт их из JSON строками,
    # сборщик PDF — из ORM, и там object_id остаётся uuid.UUID. Лукап по
    # разнотипным ключам молча не находил долю, и в PDF ВСЕ круги рисовались
    # минимальным радиусом 9 вместо 9–31: карта переставала показывать
    # различие направлений по доле выручки. Вместе с радиусом сдвигалось
    # начало вектора (gap = r + VECTOR_GAP), поэтому обрезка по рамке давала
    # другой набор стрелок, и картинки веба и PDF расходились.
    shares_by_id = {str(k): v for k, v in shares.items()}

    pts: dict[str, Placed] = {}
    for r in results:
        # Неизвестная сила трактуется как слабая — крайняя правая колонка.
        col = COL_INDEX.get(r["cell_strength"], 2)
        row = ROW_INDEX.get(r["cell_attract"], 0)
        pts[r["object_id"]] = Placed(
            x=PAD_L + in_cell(col, r["coord_strength"], reverse=True),
            y=PAD_T + GRID - in_cell(row, r["coord_attract"]),
            r=radius(shares_by_id.get(str(r["object_id"]))),
            col=col,
            row=row,
        )

    ids = [r["object_id"] for r in results]
    for _ in range(MAX_PASSES):
        moved = False
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a = pts[ids[i]]
                b = pts[ids[j]]
                dx = b.x - a.x
                dy = b.y - a.y
                d = math.sqrt(dx * dx + dy * dy)
                # Полностью совпавшие координаты дают нулевой вектор
                # отталкивания, и круги остались бы друг на друге: два
                # направления с одинаковыми баллами читались бы как одно.
                # При шкале в два-три пункта совпадение вероятно, поэтому
                # расталкиваем по углу от порядкового номера пары — правило
                # детерминированное, картинка воспроизводима.
                if d < 1e-9:
                    angle = 2 * math.pi * j / len(ids)
                    ux, uy = math.cos(angle), math.sin(angle)
                    d = 0.01
                else:
                    ux, uy = dx / d, dy / d
                need = a.r + b.r + MIN_GAP
                if d < need:
                    push = (need - d) / 2
                    a.x -= ux * push
                    a.y -= uy * push
                    b.x += ux * push
                    b.y += uy * push
                    moved = True
        for oid in ids:
            p = pts[oid]
            x0 = PAD_L + p.col * CELL + p.r + EDGE_GAP
            x1 = PAD_L + (p.col + 1) * CELL - p.r - EDGE_GAP
            y1 = PAD_T + GRID - p.row * CELL - p.r - EDGE_GAP
            y0 = PAD_T + GRID - (p.row + 1) * CELL + p.r + EDGE_GAP
            # min/max от обеих границ: у крупного круга в узкой ячейке
            # x0 может оказаться больше x1, и тогда круг встаёт по центру.
            p.x = min(max(p.x, min(x0, x1)), max(x0, x1))
            p.y = min(max(p.y, min(y0, y1)), max(y0, y1))
        if not moved:
            break
    return pts


def vector(
    p: Placed,
    lines: Iterable[int],
    kind: Literal["target", "risk"],
) -> dict[str, float] | None:
    """
    Вектор от круга: направление смещения по матрице, а не точка прибытия.

    Целевой — проработка назревшего, в сторону роста. Рисковый — эрозия,
    в сторону падения. Линии 1–3 — конкурентная сила (горизонталь), 4–6 —
    привлекательность (вертикаль); ведём по той оси, где подвижных больше.
    При равенстве — по горизонтали.

    По вертикали рост — вверх. По горизонтали рост — ВЛЕВО: ось силы
    развёрнута под матрицу GE/McKinsey, отсюда X_SIGN.
    """
    lines = list(lines)
    if not lines:
        return None
    gap = p.r + VECTOR_GAP
    direction = 1 if kind == "target" else -1
    horizontal = sum(1 for n in lines if n <= 3)
    along_x = horizontal >= len(lines) - horizontal
    if along_x:
        dx = direction * X_SIGN
        frm = p.x + dx * gap
        v = {"x1": frm, "y1": p.y, "x2": frm + dx * VECTOR_LEN, "y2": p.y}
    else:
        frm = p.y - direction * gap
        v = {"x1": p.x, "y1": frm, "x2": p.x, "y2": frm - direction * VECTOR_LEN}
    return _clip_to_grid(v)


def _clip_to_grid(v: dict[str, float]) -> dict[str, float] | None:
    """
    Стрелка обрезается по рамке матрицы.

    Длина вектора фиксированная, а зажимается только круг, поэтому у направления
    в крайней ячейке стрелка уезжала за сетку и висела в пустоте. Обрезаем.

    Если после обрезки осталось меньше VECTOR_MIN, стрелку не рисуем вовсе:
    огрызок в три пикселя направление не показывает, а цель и риск в отчёте
    всё равно названы номерами гексаграмм в таблице под картой.
    """
    x1 = min(max(v["x1"], PAD_L), PAD_L + GRID)
    x2 = min(max(v["x2"], PAD_L), PAD_L + GRID)
    y1 = min(max(v["y1"], PAD_T), PAD_T + GRID)
    y2 = min(max(v["y2"], PAD_T), PAD_T + GRID)
    if math.hypot(x2 - x1, y2 - y1) < VECTOR_MIN:
        return None
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


# ── SVG ───────────────────────────────────────────────────────────────────────
def _grid_svg() -> str:
    parts = [
        f'<rect x="{PAD_L}" y="{PAD_T}" width="{GRID}" height="{GRID}" '
        f'fill="{C_PAPER}" stroke="{C_LINE}"/>'
    ]
    for i in (1, 2):
        x = _num(PAD_L + i * CELL)
        parts.append(
            f'<line x1="{x}" y1="{PAD_T}" x2="{x}" y2="{PAD_T + GRID}" stroke="{C_LINE}"/>'
        )
        y = _num(PAD_T + i * CELL)
        parts.append(
            f'<line x1="{PAD_L}" y1="{y}" x2="{PAD_L + GRID}" y2="{y}" stroke="{C_LINE}"/>'
        )
    for y, label in ((68, "Выс."), (158, "Сред."), (248, "Низ.")):
        parts.append(
            f'<text x="{PAD_L - 8}" y="{y}" font-size="11" text-anchor="end" '
            f'fill="{C_MUTED}">{label}</text>'
        )
    parts.append(
        f'<text x="{PAD_L}" y="13" font-size="11" fill="{C_MUTED}">'
        "Привлекательность рынка</text>"
    )
    # Подписи слева направо: сильная, средняя, слабая — как в GE/McKinsey.
    for x, label in ((115, "Сильная"), (205, "Средняя"), (295, "Слабая")):
        parts.append(
            f'<text x="{x}" y="306" font-size="11" text-anchor="middle" '
            f'fill="{C_MUTED}">{label}</text>'
        )
    parts.append(
        f'<text x="205" y="324" font-size="11" text-anchor="middle" '
        f'fill="{C_MUTED}">Конкурентоспособность бизнеса</text>'
    )
    return "".join(parts)


def _arrow(v: dict[str, float], color: str, marker: str) -> str:
    return (
        f'<path d="M {_num(v["x1"])} {_num(v["y1"])} L {_num(v["x2"])} {_num(v["y2"])}" '
        f'stroke="{color}" stroke-width="2" marker-end="url(#{marker})"/>'
    )


def render_map_svg(
    results: list[dict[str, Any]],
    shares: dict[str, float | None],
    width: int = 400,
) -> str:
    """
    Карта портфеля как inline SVG. Порядок `results` значим — см. layout().

    Playwright печатает inline SVG без оговорок, поэтому картинка в PDF и в
    вебе строится одним и тем же способом, а не растром.
    """
    placed = layout(results, shares)

    label = "; ".join(
        f'{r["position"]}. {r["name"]}: {r["cell_label"]}' for r in results
    )

    body: list[str] = []
    for r in results:
        p = placed[r["object_id"]]
        t = vector(p, r.get("target_lines") or [], "target")
        k = vector(p, r.get("risk_lines") or [], "risk")
        stable = not (r.get("target_lines") or []) and not (r.get("risk_lines") or [])
        if t:
            body.append(_arrow(t, C_BLUE, "m3-up"))
        if k:
            body.append(_arrow(k, C_RED, "m3-dn"))
        dash = ' stroke-dasharray="3 2"' if stable else ""
        body.append(
            f'<circle cx="{_num(p.x)}" cy="{_num(p.y)}" r="{p.r}" '
            f'fill="{C_PAPER}" stroke="{C_DARK}" stroke-width="1.5"{dash}/>'
        )
        body.append(
            f'<text x="{_num(p.x)}" y="{_num(p.y + 4)}" font-size="10" '
            f'text-anchor="middle" fill="{C_DARK}">{e(str(r["position"]))}</text>'
        )

    return (
        f'<svg viewBox="0 0 {VB_W} {VB_H}" width="{width}" '
        'xmlns="http://www.w3.org/2000/svg" style="max-width:100%;height:auto;" '
        f'role="img" aria-label="Матрица три на три, направлений: {len(results)}. {e(label)}">'
        '<defs>'
        '<marker id="m3-up" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_BLUE}"/></marker>'
        '<marker id="m3-dn" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_RED}"/></marker>'
        '</defs>'
        + _grid_svg()
        + "".join(body)
        + "</svg>"
    )


def map_caption(results: list[dict[str, Any]]) -> str:
    """Подпись под картой. Состав фраз зависит от того, что на карте есть."""
    has_target = any(r.get("target_lines") for r in results)
    has_risk = any(r.get("risk_lines") for r in results)
    has_stable = any(
        not (r.get("target_lines") or []) and not (r.get("risk_lines") or [])
        for r in results
    )
    parts = ["Размер круга — доля направления в выручке "
             "(пропорциональна площадь, не радиус)."]
    if has_target:
        parts.append("Синяя стрелка — целевое состояние: куда придёт направление, "
                     "если проработать назревшее.")
    if has_risk:
        parts.append("Красная — сценарий эрозии: куда сползёт, если не закрепить "
                     "достигнутое.")
    if has_stable:
        parts.append("Пунктирный контур — подвижных линий нет, ограничение "
                     "стабильно.")
    return " ".join(parts)
