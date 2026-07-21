# -*- coding: utf-8 -*-
"""
Рендер PDF-раздела «Финансовая функция» (Спецификация §5.8).
Standalone-модуль: не импортирует pdf.py (без циклов). Вызывается из
build_report_html только при наличии finance_result (Метод 1).
"""
import html as _html

def e(text: str | None) -> str:
    return _html.escape(text or "", quote=True)

# ── Финансовая функция (Метод 1): рендер раздела отчёта ───────────────────────
from app.finance_items import BLOCKS as _FIN_BLOCKS

_FIN_INK = "#1a2540"
_FIN_ACCENT = "#c0392b"
_FIN_STATE_RU = {
    "young_yang": "Ян — устойчивая сильная позиция",
    "old_yang":   "Ян, подвижная — сила на пике",
    "young_yin":  "Инь — устойчивая слабая позиция",
    "old_yin":    "Инь, подвижная — изменение назрело",
}
_FIN_FLAG_RU = {
    "INCONSISTENT_BLOCK": "противоречивые ответы",
    "BORDERLINE_LINE":    "неустойчивое определение",
    "PARTIAL_BLOCK":      "один «Не знаю»",
    "VETO_APPLIED":       "вето",
    "VETO_UNKNOWN":        "4.1 неизвестно",
}


def _finance_hexagram_svg(combination: str, moving_lines, size: int = 96) -> str:
    """Как _hexagram_svg, но подвижные линии окрашены акцентом. line 1 снизу."""
    moving = set(moving_lines or [])
    line_h = size * 0.10
    gap    = size * 0.06
    step   = line_h + gap
    total_h = 6 * line_h + 5 * gap
    y_off  = (size - total_h) / 2
    w      = size * 0.82
    x0     = (size - w) / 2
    brk    = w * 0.22
    rx     = line_h / 4

    rects: list[str] = []
    for i, ch in enumerate(combination):
        line_no = i + 1
        color = _FIN_ACCENT if line_no in moving else _FIN_INK
        y = y_off + (5 - i) * step
        if ch == "A":
            rects.append(f'<rect x="{x0:.2f}" y="{y:.2f}" width="{w:.2f}" height="{line_h:.2f}" fill="{color}" rx="{rx:.2f}"/>')
        else:
            half = (w - brk) / 2
            rects.append(f'<rect x="{x0:.2f}" y="{y:.2f}" width="{half:.2f}" height="{line_h:.2f}" fill="{color}" rx="{rx:.2f}"/>')
            rects.append(f'<rect x="{x0 + half + brk:.2f}" y="{y:.2f}" width="{half:.2f}" height="{line_h:.2f}" fill="{color}" rx="{rx:.2f}"/>')
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
            f'xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;">'
            + "".join(rects) + "</svg>")


def finance_section_html(finance_result: dict, interp: dict, company_name: str, description_html: str = "") -> str:
    """Раздел «Финансовая функция» — 9 подразделов (Спецификация §5.8)."""
    ink, accent = _FIN_INK, _FIN_ACCENT
    lines = finance_result.get("lines", [])
    lines_by_num = {l["line"]: l for l in lines}
    moving_lines = finance_result.get("moving_lines", [])
    hc = finance_result.get("hexagram_current") or {}
    cur_code = finance_result.get("combination_current", "")
    res_code = finance_result.get("combination_resulting") or ""

    def card(inner: str) -> str:
        return ('<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;'
                'padding:18px 20px;background:rgba(255,255,255,0.45);margin-bottom:16px;'
                f'page-break-inside:avoid;">{inner}</div>')

    def h2(num: str, text: str) -> str:
        return (f'<h2 style="font-size:18px;font-weight:400;color:{ink};margin:22px 0 12px;">'
                f'{e(text)}</h2>')

    # 1 — заголовок + текущая гексаграмма
    moving_note = ("Подвижные линии: " + ", ".join(str(n) for n in moving_lines)) if moving_lines \
        else "Подвижных линий нет — конфигурация стабильна"
    header = (
        '<div style="display:flex;align-items:center;gap:20px;page-break-inside:avoid;">'
        f'{_finance_hexagram_svg(cur_code, moving_lines, 96)}'
        '<div>'
        f'<div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:{accent};font-weight:600;font-family:Arial,sans-serif;">Финансовая функция</div>'
        f'<div style="font-size:24px;color:{ink};margin-top:4px;">№ {e(str(hc.get("number","")))} «{e(hc.get("name",""))}»</div>'
        f'<div style="font-size:12px;color:rgba(26,37,64,0.5);font-family:monospace;letter-spacing:2px;margin-top:4px;">{e(cur_code)}</div>'
        f'<div style="font-size:11px;color:{accent};font-family:Arial,sans-serif;margin-top:6px;">{e(moving_note)}</div>'
        '</div></div>'
    )

    # 2 — диагноз
    ton = interp.get("tonality") or {}
    pat = interp.get("pattern_current") or {}
    mi = finance_result.get("maturity_index")
    diagnosis = card(
        f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;line-height:1.7;">'
        f'<b>{e(ton.get("title") or "")}</b> (индекс зрелости {e(str(mi))}/6). {e(ton.get("text") or "")}<br><br>'
        f'{e(pat.get("essence") or "")} <span style="color:{accent};">Типичная ошибка:</span> {e(pat.get("mistake") or "")}'
        '</div>')

    # 3 — профиль линий 6→1
    rows = ""
    for n in range(6, 0, -1):
        l = lines_by_num.get(n)
        if not l:
            continue
        param = _FIN_BLOCKS[n]["title"].split(". ", 1)[-1]
        state_ru = _FIN_STATE_RU.get(l["state"], l["state"])
        flags = " · ".join(_FIN_FLAG_RU.get(f, f) for f in l.get("flags", []))
        flag_html = f'<span style="color:{accent};font-size:11px;"> ⚠ {e(flags)}</span>' if flags else ""
        rows += (
            '<tr>'
            f'<td style="padding:6px 8px;font-family:Arial,sans-serif;font-size:12px;color:rgba(26,37,64,0.5);">{n}</td>'
            f'<td style="padding:6px 8px;font-size:13px;color:{ink};">{e(param)}</td>'
            f'<td style="padding:6px 8px;font-family:monospace;font-size:13px;color:{ink};">{l["score"]:.2f}</td>'
            f'<td style="padding:6px 8px;font-size:12px;color:rgba(26,37,64,0.7);">{e(state_ru)}{flag_html}</td>'
            '</tr>')
    th = ('<th style="text-align:left;padding:6px 8px;font-size:10px;text-transform:uppercase;'
          'letter-spacing:1px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;">')
    profile = (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:1px solid rgba(26,37,64,0.15);">'
        f'{th}Линия</th>{th}Параметр</th>{th}Балл</th>{th}Состояние</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')

    # 4 — квадрант + триграммы
    q = interp.get("quadrant") or {}
    tg = interp.get("trigrams") or {}
    low = tg.get("lower") or {}
    up = tg.get("upper") or {}
    quadrant = card(
        f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;line-height:1.7;">'
        f'<b>Квадрант: {e(q.get("title") or "")}</b>. {e(q.get("text") or "")}<br><br>'
        f'<b>Нижняя триграмма (двигатель) — {e(low.get("title") or "")}:</b> {e(low.get("text") or "")}<br>'
        f'<b>Верхняя триграмма (руль) — {e(up.get("title") or "")}:</b> {e(up.get("text") or "")}'
        '</div>')

    # 5 — напряжения
    tensions = interp.get("tensions") or []
    if tensions:
        items = "".join(f'<li style="margin-bottom:8px;">{e(t["text"])}</li>' for t in tensions)
        tensions_html = card(f'<ul style="margin:0;padding-left:18px;font-size:13px;color:{ink};font-family:Arial,sans-serif;line-height:1.6;">{items}</ul>')
    else:
        tensions_html = card('<div style="font-size:13px;color:rgba(26,37,64,0.5);font-family:Arial,sans-serif;">Явных напряжений между линиями не выявлено.</div>')

    # 6 — приоритеты
    pr = interp.get("priorities") or []
    if pr:
        items = ""
        for p in pr:
            items += (
                '<div style="margin-bottom:10px;">'
                f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;"><b>{e(p["block_title"])}</b> — {e(_FIN_STATE_RU.get(p["state"], p["state"]))}</div>'
                f'<div style="font-size:12px;color:rgba(26,37,64,0.7);font-family:Arial,sans-serif;margin-top:2px;">{e(p["package_text"])}</div>'
                '</div>')
        priorities_html = card(items)
    else:
        priorities_html = card('<div style="font-size:13px;color:rgba(26,37,64,0.5);font-family:Arial,sans-serif;">Подвижных линий нет — приоритетных зон вмешательства не выделено.</div>')

    # 6b — вето: условие, блокирующее трансформацию (Поправка П6)
    vb = interp.get("veto_block")
    if vb:
        veto_html = card(
            f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;line-height:1.7;">'
            f'<b>{e(vb.get("block_title") or "")}</b> — балл {vb.get("score")}, '
            f'линия переопределена в Инь по правилу вето: первое лицо не обозначило '
            f'развитие этой функции как приоритет.<br><br>'
            f'{e(vb.get("package_text") or "")}'
            '</div>')
    else:
        veto_html = ""

    # 6c — плановые шаги (иньские линии без подвижности)
    pl = interp.get("planned_steps") or []
    if pl:
        _items = ""
        for p in pl:
            _items += (
                '<div style="margin-bottom:10px;">'
                f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;">'
                f'<b>{e(p.get("block_title") or "")}</b></div>'
                f'<div style="font-size:12px;color:rgba(26,37,64,0.7);font-family:Arial,sans-serif;'
                f'margin-top:2px;">{e(p.get("package_text") or "")}</div>'
                '</div>')
        planned_html = card(_items)
    else:
        planned_html = card('<div style="font-size:13px;color:rgba(26,37,64,0.5);'
                            'font-family:Arial,sans-serif;">Плановых шагов не выделено.</div>')

    # 7 — траектория
    traj = interp.get("trajectory")
    if traj:
        cur_n = str((traj.get("current") or {}).get("number", ""))
        res_n = str((traj.get("resulting") or {}).get("number", ""))
        trajectory_html = card(
            '<div style="display:flex;align-items:center;gap:16px;">'
            f'<div style="text-align:center;">{_finance_hexagram_svg(cur_code, moving_lines, 70)}<div style="font-size:11px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;">№ {e(cur_n)}</div></div>'
            f'<div style="font-size:22px;color:{accent};">→</div>'
            f'<div style="text-align:center;">{_finance_hexagram_svg(res_code, [], 70)}<div style="font-size:11px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;">№ {e(res_n)}</div></div>'
            f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;line-height:1.6;">{e(traj.get("essence") or "")} <span style="color:{accent};">Предостережение:</span> {e(traj.get("mistake") or "")}</div>'
            '</div>')
    else:
        trajectory_html = card('<div style="font-size:13px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;">Подвижных линий нет — конфигурация стабильна, направленной трансформации не требуется.</div>')

    # 8 — оговорки
    caveats = interp.get("caveats") or []
    if caveats:
        items = "".join(f'<li style="margin-bottom:6px;">{e(c)}</li>' for c in caveats)
        caveats_html = card(f'<ul style="margin:0;padding-left:18px;font-size:12px;color:rgba(26,37,64,0.7);font-family:Arial,sans-serif;line-height:1.5;">{items}</ul>')
    else:
        caveats_html = card('<div style="font-size:12px;color:rgba(26,37,64,0.5);font-family:Arial,sans-serif;">Оговорок по качеству данных нет.</div>')

    # 9 — следующие шаги
    steps = interp.get("next_steps") or []
    if steps:
        items = "".join(f'<li style="margin-bottom:6px;">{e(s)}</li>' for s in steps)
        steps_html = card(f'<ol style="margin:0;padding-left:18px;font-size:13px;color:{ink};font-family:Arial,sans-serif;line-height:1.6;">{items}</ol>')
    else:
        steps_html = card('<div style="font-size:13px;color:rgba(26,37,64,0.5);font-family:Arial,sans-serif;">Немедленных шагов не требуется.</div>')

    return (
        '<div style="padding:40px 50px;background:#e8e4db;page-break-before:always;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:24px;">'
        f'<span style="font-size:11px;font-weight:700;color:{accent};font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>'
        f'<span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">{e(company_name)} · финансовая функция</span>'
        '</div>'
        f'<h2 style="font-size:22px;font-weight:400;color:{ink};margin:0 0 18px;">'
        f'<span style="font-size:11px;color:{accent};margin-right:10px;">02</span>Финансовая функция</h2>'
        f'{header}'
        f'{h2("01","Диагноз")}{diagnosis}'
        f'{description_html}'
        f'{h2("02","Профиль линий")}{card(profile)}'
        f'{h2("03","Ресурс и направление")}{quadrant}'
        f'{h2("04","Ключевые напряжения")}{tensions_html}'
        + (f'{h2("05","Условие, блокирующее трансформацию")}{veto_html}' if vb else "")
        + f'{h2("06","Приоритеты вмешательства")}{priorities_html}'
        + f'{h2("07","Плановые шаги")}{planned_html}'
        f'{h2("06","Траектория")}{trajectory_html}'
        f'{h2("07","Оговорки по данным")}{caveats_html}'
        f'{h2("08","Следующие шаги")}{steps_html}'
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);display:flex;justify-content:space-between;font-family:Arial,sans-serif;font-size:10px;color:rgba(26,37,64,0.3);">'
        '<span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>'
        '</div></div>'
    )
