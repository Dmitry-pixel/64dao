# -*- coding: utf-8 -*-
"""
Слоты контента Метода 3: какие блоки разбора метод ожидает заполненными.

Отдельный модуль, а не список во фронте: ключи выводятся из правил метода
(девять ячеек матрицы, шесть линий, десять напряжений), и вторая их копия
на TypeScript разошлась бы при первой же правке. Ровно так разошлись копии
OBJECTS_MIN между схемой и расчётом.

Ни БД, ни файловой системы: чистые данные, считаются на каждый запрос.
"""
from app.m3_service import LINE_TITLES

CELL_LEVELS = ("low", "mid", "high")
CELL_LEVEL_RU = {"low": "низкая", "mid": "средняя", "high": "высокая"}

# Вид -> подпись вкладки. Порядок задаёт порядок вкладок в админке.
CONTENT_KINDS: tuple[tuple[str, str], ...] = (
    ("zone", "Зоны матрицы"),
    ("zone_reduced", "Зоны · одиночный режим"),
    ("weak_line", "Ведущая слабая линия"),
    ("strong_line", "Ведущая сильная линия"),
    ("tension", "Напряжения"),
)


def _zone_slots() -> list[dict]:
    return [
        {"key": f"{s}_{a}",
         "title": f"Сила {CELL_LEVEL_RU[s]}, привлекательность {CELL_LEVEL_RU[a]}"}
        for s in CELL_LEVELS for a in CELL_LEVELS
    ]


def _line_slots(prefix: str) -> list[dict]:
    return [{"key": f"{prefix}_L{n}", "title": f"Л{n} · {LINE_TITLES[n]}"}
            for n in range(1, 7)]


def content_catalog() -> list[dict]:
    """
    Полный список слотов по видам.

    zone_reduced намеренно перечисляет те же девять ключей, что и zone,
    хотя заполнены из них две: экран обязан показывать, где переопределения
    нет и в одиночный отчёт идёт общий текст.
    """
    out: list[dict] = []
    for kind, kind_title in CONTENT_KINDS:
        if kind in ("zone", "zone_reduced"):
            slots = _zone_slots()
        elif kind == "weak_line":
            slots = _line_slots("weak")
        elif kind == "strong_line":
            slots = _line_slots("strong")
        else:
            slots = [{"key": f"P{n}", "title": f"Напряжение P{n}"}
                     for n in range(1, 11)]
        out.append({"kind": kind, "kind_title": kind_title, "slots": slots})
    return out
