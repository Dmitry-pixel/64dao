# -*- coding: utf-8 -*-
"""
Тип перехода направления Метода 3 между двумя замерами (Transition Report).

Чистые функции: на вход снимки двух расчётов одного направления, на выход
оси перехода и итоговый тип. БД не участвует, тестируется изолированно.
Правила и тексты: claude/m3-transition-rules-draft.md в материалах проекта.

Пока тексты не написаны, результат видит только администратор
(/admin/m3-transitions). Клиентский отчёт не меняется.

Что берётся из снимка, а не пересчитывается. Символы и назревшие/рисковые
линии читаются из сохранённого расчёта (m3_results.symbols, target_lines,
risk_lines), а не из текущих порогов конфига: пороги можно поменять в
админке, а сравнение обязано остаться воспроизводимым. Баллы l1..l6 нужны
только для отсечения шума (MIN_DELTA).
"""
from __future__ import annotations

from typing import Any

YANG = "A"

# Сдвиг балла, ниже которого смена символа считается шумом ответа
# (2,6 → 2,4), а не изменением в компании. Предложение, не методика:
# уточнить по первым реальным повторам.
MIN_DELTA = 0.5

STRENGTH_LINES = (1, 2, 3)   # конкурентная сила: то, что компания делает сама

TYPE_TITLES = {
    "T1": "Перелом",
    "T2": "Срыв в риск",
    "T3": "Обмен",
    "T4": "Проработка назревшего",
    "T5": "Частичная проработка",
    "T6": "Рыночный сдвиг",
    "T7": "Внутренний сдвиг",
    "T8": "Стабильность",
    "T9": "Застой",
    "T10": "Разнонаправленное движение",
}


def _scale(k: int) -> str:
    if k == 0:
        return "0"
    if k == 1:
        return "1"
    if k <= 3:
        return "2-3"
    if k <= 5:
        return "4-5"
    return "6"


def _intent(intent: dict[str, list[int]] | None, now_symbols: str) -> dict[str, Any]:
    """Совпало ли движение с намерением.

    Намерение = шаги чек-листа первого замера, отмеченные клиентом как
    выполненные: маршрутный шаг (назревшее) ждёт, что линия станет Ян;
    шаг удержания ждёт, что линия останется Ян. Других шагов клиент не
    обещал, поэтому прочие линии в сверку не входят.
    """
    strengthen = sorted(set((intent or {}).get("strengthen") or []))
    hold = sorted(set((intent or {}).get("hold") or []))
    lines = strengthen + [n for n in hold if n not in strengthen]
    if not lines:
        return {"value": "нет данных", "met": [], "missed": []}
    met = [n for n in lines if now_symbols[n - 1] == YANG]
    missed = [n for n in lines if n not in met]
    value = "совпало" if not missed else "против" if not met else "частично"
    return {"value": value, "met": met, "missed": missed}


def classify(prev: dict[str, Any], now: dict[str, Any],
             intent: dict[str, list[int]] | None = None,
             min_delta: float = MIN_DELTA) -> dict[str, Any]:
    """
    prev: {"scores": [l1..l6], "symbols": "ABAB..", "target_lines": [..], "risk_lines": [..]}
    now:  {"scores": [l1..l6], "symbols": "ABAB.."}
    intent: {"strengthen": [линии], "hold": [линии]} или None.
    """
    ps, ns = prev["symbols"], now["symbols"]
    pv, nv = [float(x) for x in prev["scores"]], [float(x) for x in now["scores"]]
    target = sorted(prev.get("target_lines") or [])
    risk = sorted(prev.get("risk_lines") or [])

    flips = [n for n in range(1, 7) if ps[n - 1] != ns[n - 1]]
    # Округление: баллы хранятся с двумя знаками, разность 3.0 - 2.5 во
    # float может оказаться 0.4999… и выпасть из значимых.
    sig = [n for n in flips if round(abs(nv[n - 1] - pv[n - 1]), 4) >= min_delta]
    border = [n for n in flips if n not in sig]
    k = len(sig)

    if k == 0:
        where = "—"
    elif max(sig) <= 3:
        where = "сила"
    elif min(sig) >= 4:
        where = "рынок"
    else:
        where = "обе"

    up = sum(1 for n in sig if ns[n - 1] == YANG)
    down = k - up
    direction = ("—" if k == 0 else "усиление" if up > down
                 else "ослабление" if down > up else "перераспределение")

    # Назревшее и риск сверяются по символу, без порога шума: вопрос не
    # «насколько сдвинулось», а «перешла ли линия в нужное состояние».
    closed = [n for n in target if ns[n - 1] == YANG]
    if not target:
        target_state = "нет"
    elif len(closed) == len(target):
        target_state = "полностью"
    else:
        target_state = "частично" if closed else "не проработано"

    fell = [n for n in risk if ns[n - 1] != YANG]
    if not risk:
        risk_state = "нет"
    elif len(fell) == len(risk):
        risk_state = "реализовался"
    else:
        risk_state = "частично" if fell else "удержан"

    # Порядок проверок = приоритет типа: первый подошедший и есть тип.
    if k >= 4:
        t = "T1"
    elif risk_state == "реализовался" and target_state != "полностью":
        t = "T2"
    elif closed and fell:
        t = "T3"
    elif target_state == "полностью":
        t = "T4"
    elif target_state == "частично":
        t = "T5"
    elif k and where == "рынок":
        t = "T6"
    elif k and where == "сила":
        t = "T7"
    elif k == 0 and not target:
        t = "T8"
    elif k == 0:
        t = "T9"
    else:
        t = "T10"

    return {
        "type": t,
        "type_title": TYPE_TITLES[t],
        "prev_symbols": ps,
        "now_symbols": ns,
        "changed": sig,
        "borderline": border,
        "scale": _scale(k),
        "where": where,
        "direction": direction,
        "target": target_state,
        "risk": risk_state,
        "intent": _intent(intent, ns),
    }


def scores_of(row: Any) -> list[float]:
    """Баллы l1..l6 из строки m3_results."""
    return [float(getattr(row, f"l{n}")) for n in range(1, 7)]
