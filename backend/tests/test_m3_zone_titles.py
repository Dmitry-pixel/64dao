# -*- coding: utf-8 -*-
"""
Замок на заголовки зон Метода 3.

Заголовок блока зоны и ярлык позиции печатаются в одной карточке отчёта:
разбор ведёт название зоны, вердикт ниже добавляет «Зона матрицы: <zone_ru>»
(m3_pdf.verdict_block, веб — report/m3/[id]/page.tsx). Пока имена не
пересекаются, это два взгляда на одну ячейку. Как только заголовок занимает
слово ЧУЖОЙ позиции, читатель видит противоречие в одном абзаце.

Так и вышло с high_low: заголовок «Сбор урожая» при позиции hold
(«Удерживать»), тогда как «Собирать урожай» — ярлык соседней ячейки mid_low.
Найдено вычиткой, исправлено на «Рынок исчерпан, удержание».

Границы замка. Тест читает константы сидов, а не базу. Для kind zone это
одно и то же: seed_m3.seed_content перезаписывает title при каждом прогоне.
Для kind zone_reduced — нет: seed_m3_zone_reduced существующие строки
пропускает, и правка заголовка через админку тесту не видна.
"""
from app import m3_verdict as vd

import seed_m3
import seed_m3_zone_reduced

# Корни слов, которыми названа каждая позиция матрицы. Список ведётся руками:
# автоматическая нарезка zone_ru даёт корень «развива» и для build
# («Избирательно развивать»), и для limited («Ограниченное развитие»), после
# чего замок падает на верных заголовках.
STANCE_STEMS: dict[str, tuple[str, ...]] = {
    "invest":  ("инвестир",),
    "protect": ("защищ",),
    "build":   ("избирательн",),
    "hold":    ("удерж",),
    "limited": ("ограничен",),
    "harvest": ("урожа", "собира"),
    "exit":    ("выход", "избега"),
}


def stance_by_cell() -> dict[str, str]:
    """Ключ контентного блока -> позиция матрицы: 'high_low' -> 'hold'."""
    return {f"{s}_{a}": stance for (s, a), (stance, _ru, _en) in vd.ZONES.items()}


def zone_titles() -> list[tuple[str, str, str]]:
    """(вид, ключ ячейки, заголовок) по обоим корпусам текстов."""
    rows = [(b["kind"], b["key"], b["title"])
            for b in seed_m3.CONTENT_BLOCKS if b["kind"] == "zone"]
    rows += [("zone_reduced", key, title)
             for key, (title, _body, _mistake) in seed_m3_zone_reduced.ROWS.items()]
    return rows


def test_stems_cover_every_stance():
    """Позиция без корней в словаре молча выпадает из проверки ниже."""
    missing = sorted({z[0] for z in vd.ZONES.values()} - set(STANCE_STEMS))
    assert missing == [], f"Позиции без корней: {missing}"


def test_every_zone_key_is_a_matrix_cell():
    """Заголовок под ключом, которого нет в матрице, не печатается никогда."""
    cells = set(stance_by_cell())
    unknown = sorted({(kind, key) for kind, key, _t in zone_titles()
                      if key not in cells})
    assert unknown == [], f"Ключи вне матрицы: {unknown}"


def test_zone_title_does_not_borrow_another_stance():
    """
    Заголовок вправе повторять слово СВОЕЙ позиции («Кандидат на выход» при
    stance exit) и обязан не занимать слово чужой.
    """
    stance = stance_by_cell()
    offenders = []
    for kind, key, title in zone_titles():
        own = stance[key]
        low = title.lower()
        for other, stems in STANCE_STEMS.items():
            if other == own:
                continue
            for stem in stems:
                if stem in low:
                    offenders.append((kind, key, title, own, other, stem))
    assert offenders == [], (
        "Заголовок зоны занял слово чужой позиции матрицы: " + "; ".join(
            f"{k}/{key} «{t}» при stance {own}, корень «{stem}» принадлежит {other}"
            for k, key, t, own, other, stem in offenders
        )
    )
