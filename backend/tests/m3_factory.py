# -*- coding: utf-8 -*-
"""
Одна фабрика снимка расчёта Метода 3 на все тесты отчёта.

Раньше их было четыре: две в test_m3_pdf, по одной в test_m3_report_parity
и test_m3_verdict. Каждая знала свой кусок контракта, и при расширении
словаря результата отставали разные. За 8 августа это дважды дало один
и тот же провал: сначала `weights` не доехали до синтетики паритета,
потом до синтетики PDF. Оба раза ловили тесты — и оба раза уже после того,
как работа объявлялась готовой.

Здесь лежит ПОЛНЫЙ словарь: каждый ключ, который читает продуктовый код.
Расширился контракт — правится одно место, и все тесты видят это сразу.

Частичные словари остаются в тестах явными: проверки мягкой деградации
(снимок без весов, результат без баллов) обязаны показывать неполноту
в самом тесте, а не прятать её в фабрике.
"""
from app.m3_config import industry_weights
from app import m3_scoring as sc
from app import m3_verdict as vd

# Универсальный пресет: при нём правило «сумма весов» воспроизводит прежнее
# «по числу Ян» точно, поэтому ячейки образцов остаются в силе. Отраслевые
# веса проверяются отдельно, в test_m3_scoring и test_m3_verdict.
UNIVERSAL = industry_weights(18)


def breakdown(symbols: str, cells: tuple[str, str], weights=None) -> dict:
    """Вывод ячейки — так же, как его собирает build_report: разбор из
    символов и весов, уровень из снимка."""
    w = weights or UNIVERSAL
    out = {}
    for axis, level in (("strength", cells[0]), ("attract", cells[1])):
        d = {**sc.cell_detail(symbols, axis, w), "level": level}
        d["text"] = vd.cell_breakdown_text(axis, d)
        out[axis] = d
    return out


def result(**over) -> dict:
    """Полный снимок одного направления. Всё переопределяется через over."""
    symbols = over.get("symbols", "AAABBA")
    cells = (over.get("cell_strength", "high"), over.get("cell_attract", "low"))
    weights = over.get("weights", UNIVERSAL)

    base = {
        "object_id": "o1",
        "position": 1,
        "name": "Салонный канал B2B",
        "symbols": symbols,
        "weights": weights,
        "scores": {"l1": 3.0, "l2": 3.0, "l3": 4.0,
                   "l4": 2.0, "l5": 2.0, "l6": 3.0},
        "mobility": {"3": "old_yang"},
        "cell_strength": cells[0],
        "cell_attract": cells[1],
        "cell_key": f"{cells[0]}_{cells[1]}",
        "cell_label": "Высокая / Низкая",
        "cell_breakdown": breakdown(symbols, cells, weights),
        "coord_strength": 3.33,
        "coord_attract": 2.33,
        "current_hex": 26,
        "current_name": "Накопление",
        "target_hex": None,
        "target_lines": [],
        "risk_hex": 41,
        "risk_lines": [3],
        "v_index": 0.4909,
        "z_index": 0.4700,
        "v_rank": 1,
        "z_rank": 1,
        "weak_line": 5,
        "strong_line": 3,
        "tensions": [],
        "flags": [],
        "market_overrides": 0,
        "market_label": "Общий",
    }
    base.update(over)
    # Ячейки и вывод пересобираются после подстановки: тест, задавший
    # символы или веса, не обязан помнить про cell_breakdown.
    if "cell_breakdown" not in over:
        base["cell_breakdown"] = breakdown(
            base["symbols"],
            (base["cell_strength"], base["cell_attract"]),
            base["weights"],
        )
    if "cell_key" not in over:
        base["cell_key"] = f'{base["cell_strength"]}_{base["cell_attract"]}'
    return base
