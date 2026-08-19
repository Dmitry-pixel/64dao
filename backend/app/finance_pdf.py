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


def section_badge(no: str, small: bool = False) -> str:
    """
    Номер верхнего раздела — плашка. Верхнеуровневые разделы должны читаться
    оглавлением при просмотре по диагонали; номера внутри секции контура
    остаются мелкими, иначе иерархия схлопывается в один уровень.

    Стиль зеркалит S.num в вебе (frontend/src/app/report/[id]/page.tsx).
    Подложка печатается: в body отчёта стоит print-color-adjust:exact.
    """
    # small — для Метода 3: его заголовок 13px и капителью, плашка в полный
    # размер там перевешивает название раздела.
    size, pad, radius, gap = (("11px", "3px 7px", "3px", "10px") if small
                              else ("13px", "4px 9px", "4px", "12px"))
    return (
        '<span style="display:inline-block;font-family:Arial,sans-serif;'
        f'font-size:{size};font-weight:500;color:#fff;background:#c0392b;'
        f'border-radius:{radius};padding:{pad};letter-spacing:1px;'
        f'margin-right:{gap};white-space:nowrap;">{e(no)}</span>'
    )


def contour_section_html(
    finance_result: dict,
    interp: dict,
    company_name: str,
    *,
    blocks: dict,
    title: str,
    section_no: str,
    description_html: str = "",
) -> str:
    """Раздел контура — подразделы Спецификации §5.8.

    Структура одна для всех контуров: меняются только набор заголовков блоков,
    название и номер раздела. Полный профиль стратегии остаётся только у
    финансового контура (Поправка П8); у остальных в description_html
    приходит одна ссылка на страницу гексаграммы."""
    ink, accent = _FIN_INK, _FIN_ACCENT
    lines = finance_result.get("lines", [])
    lines_by_num = {l["line"]: l for l in lines}
    moving_lines = finance_result.get("moving_lines", [])
    hc = finance_result.get("hexagram_current") or {}
    cur_code = finance_result.get("combination_current", "")

    def card(inner: str) -> str:
        return ('<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;'
                'padding:18px 20px;background:rgba(255,255,255,0.45);margin-bottom:16px;'
                f'page-break-inside:avoid;">{inner}</div>')

    # Номер раздела считается на месте: раздел про вето условный, и при
    # статичных номерах его отсутствие оставляло бы дыру в нумерации.
    _sec = [0]

    def h2(text: str) -> str:
        _sec[0] += 1
        return (f'<h2 style="font-size:18px;font-weight:400;color:{ink};margin:22px 0 12px;">'
                f'<span style="font-size:11px;color:{accent};margin-right:10px;">{_sec[0]:02d}</span>'
                f'{e(text)}</h2>')

    # 1 — заголовок + текущая гексаграмма
    moving_note = ("Подвижные линии: " + ", ".join(str(n) for n in moving_lines)) if moving_lines \
        else "Подвижных линий нет — конфигурация стабильна"
    header = (
        '<div style="display:flex;align-items:center;gap:20px;page-break-inside:avoid;">'
        f'{_finance_hexagram_svg(cur_code, moving_lines, 96)}'
        '<div>'
        f'<div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:{accent};font-weight:600;font-family:Arial,sans-serif;">{e(title)}</div>'
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
        param = blocks[n]["title"].split(". ", 1)[-1]
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

    # 4b — три уровня (сань-цай): второй разрез тех же шести линий.
    # Карточка собирается без заголовка: h2 увеличивает счётчик разделов и
    # вызывается только внутри return, иначе номер отщёлкнется раньше времени.
    _lv = interp.get("levels") or []
    if _lv:
        _inner = (f'<div style="font-size:12px;color:rgba(26,37,64,0.6);'
                  f'font-family:Arial,sans-serif;line-height:1.6;margin-bottom:14px;">'
                  f'{e(interp.get("levels_caveat") or "")}</div>')
        for _l in _lv:
            _tail = ""
            if _l.get("label_resulting"):
                _nums = ", ".join(str(n) for n in _l.get("moving_lines") or [])
                _tail = (f'<div style="font-size:12px;color:{accent};'
                         f'font-family:Arial,sans-serif;margin-top:4px;">'
                         f'Подвижны линии {e(_nums)}: состояние переходит в '
                         f'«{e(_l["label_resulting"])}».</div>')
            _note = ""
            if _l.get("caveat"):
                _note = (f'<div style="font-size:11px;color:rgba(26,37,64,0.5);'
                         f'font-family:Arial,sans-serif;margin-top:4px;">'
                         f'{e(_l["caveat"])}</div>')
            _inner += (
                '<div style="margin-bottom:14px;page-break-inside:avoid;">'
                f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;">'
                f'<b>{e(_l["title"])} — {e(_l["state_title"])}</b>'
                f'<span style="color:rgba(26,37,64,0.5);"> '
                f'({e(" + ".join(_l["line_titles"]))})</span></div>'
                f'<div style="font-size:12px;color:rgba(26,37,64,0.75);'
                f'font-family:Arial,sans-serif;margin-top:3px;line-height:1.6;">'
                f'{e(_l["text"])}</div>{_tail}{_note}</div>')
        levels_card = card(_inner)
    else:
        levels_card = ""

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

    # 7 — маршрут перехода (роадмап 2.1): цепочка гексаграмм + шаги
    route = interp.get("route") or []
    if route:
        chain = (f'<div style="text-align:center;">{_finance_hexagram_svg(cur_code, moving_lines, 58)}'
                 f'<div style="font-size:10px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;">№ {e(str(hc.get("number","")))}</div></div>')
        for st in route:
            ha = st.get("hexagram_after") or {}
            chain += (f'<div style="font-size:18px;color:{accent};align-self:center;">→</div>'
                      f'<div style="text-align:center;">{_finance_hexagram_svg(ha.get("code",""), [], 58)}'
                      f'<div style="font-size:10px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;">№ {e(str(ha.get("number","")))}</div></div>')
        chain_html = card(f'<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">{chain}</div>')
        caveat = ('<p style="font-size:12px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;'
                  'line-height:1.6;margin:0 0 12px;">Последовательность — рекомендуемая логика проработки, '
                  'а не жёсткое предписание: темп и параллельность шагов определяются ресурсами компании.</p>')
        steps_cards = ""
        for st in route:
            param = blocks[st["line"]]["title"].split(". ", 1)[-1]
            direction = "укрепить слабую позицию" if st.get("from_state") == "old_yin" else "стабилизировать перегрев"
            veto_note = (f' <span style="color:{accent};font-size:11px;">— снятие блокирующего условия</span>'
                         if st.get("is_veto") else "")
            mistake_html = (f'<div style="font-size:12px;color:{ink};font-family:Arial,sans-serif;margin-top:6px;">'
                            f'<span style="color:{accent};">Предостережение:</span> {e(st.get("mistake") or "")}</div>'
                            if st.get("is_last") and st.get("mistake") else "")
            steps_cards += (
                '<div style="border:1px solid rgba(26,37,64,0.1);border-radius:6px;padding:12px 16px;'
                'background:rgba(255,255,255,0.45);margin-bottom:10px;page-break-inside:avoid;">'
                f'<div style="font-size:13px;color:{ink};font-family:Arial,sans-serif;"><b>Шаг {st.get("order")}. Линия {st.get("line")} — {e(param)}</b> <span style="color:rgba(26,37,64,0.6);">({e(direction)})</span>{veto_note}</div>'
                f'<div style="font-size:12px;color:rgba(26,37,64,0.75);font-family:Arial,sans-serif;margin-top:5px;">{e(st.get("action_text") or "")}</div>'
                f'<div style="font-size:12px;color:rgba(26,37,64,0.55);font-family:Arial,sans-serif;margin-top:4px;">Состояние после шага: {e(st.get("after_essence") or "")}</div>'
                f'{mistake_html}'
                '</div>')
        route_html = chain_html + caveat + steps_cards
    else:
        route_html = card('<div style="font-size:13px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;">Подвижных линий нет — конфигурация стабильна, направленной трансформации не требуется.</div>')

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
        f'<span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">{e(company_name)} · {e(title.lower())}</span>'
        '</div>'
        f'<h2 style="font-size:22px;font-weight:400;color:{ink};margin:0 0 18px;">'
        f'{section_badge(section_no)}{e(title)}</h2>'
        f'{header}'
        f'{h2("Диагноз")}{diagnosis}'
        f'{description_html}'
        f'{h2("Профиль линий")}{card(profile)}'
        f'{h2("Ресурс и направление")}{quadrant}'
        f'{(h2("Три уровня") + levels_card) if levels_card else ""}'
        f'{h2("Ключевые напряжения")}{tensions_html}'
        + (f'{h2("Условие, блокирующее трансформацию")}{veto_html}' if vb else "")
        + f'{h2("Приоритеты вмешательства")}{priorities_html}'
        + f'{h2("Плановые шаги")}{planned_html}'
        f'{h2("Маршрут перехода")}{route_html}'
        f'{h2("Оговорки по данным")}{caveats_html}'
        f'{h2("Следующие шаги")}{steps_html}'
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);display:flex;justify-content:space-between;font-family:Arial,sans-serif;font-size:10px;color:rgba(26,37,64,0.3);">'
        '<span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>'
        '</div></div>'
    )


def finance_section_html(
    finance_result: dict, interp: dict, company_name: str, description_html: str = "",
    section_no: str = "03",
) -> str:
    """Финансовая функция — обёртка над общим рендером контура.

    Номер раздела по умолчанию 03: после переноса «Целевого сценария» на
    позицию 02 (Поправка П7) финансовая функция сдвинулась с 02 на 03.
    """
    from app.finance_items import BLOCKS
    return contour_section_html(
        finance_result, interp, company_name,
        blocks=BLOCKS, title="Финансовая функция", section_no=section_no,
        description_html=description_html,
    )



def summary_card_html(summary: dict, company_name: str, section_no: str = "04") -> str:
    """Сводная карта контуров (§2.4, Поправки П5 и П9).

    Выводится с двух пройденных контуров: сравнивать нечего, пока он один.
    """
    ink, accent = _FIN_INK, _FIN_ACCENT
    rows = summary.get("rows") or []

    th = ('<th style="text-align:left;padding:7px 8px;font-size:10px;text-transform:uppercase;'
          'letter-spacing:1px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;'
          'font-weight:400;">')

    body = ""
    for r in rows:
        cur = r.get("hexagram_current") or {}
        res = r.get("hexagram_resulting") or {}
        mark = r.get("is_constraint")
        bg = "background:rgba(192,57,43,0.06);" if mark else ""
        color = accent if mark else ink
        note = ('<span style="font-size:10px;"> — вероятная зона ограничения</span>'
                if mark else "")
        body += (
            f'<tr style="{bg}">'
            f'<td style="padding:9px 8px;font-size:13px;color:{color};">'
            f'{e(r.get("title") or "")}{note}</td>'
            f'<td style="padding:9px 8px;text-align:center;font-size:12px;color:{color};">'
            f'№{e(str(cur.get("number", "")))} {e(cur.get("name", ""))}</td>'
            f'<td style="padding:9px 8px;text-align:center;font-size:12px;color:{color};">'
            + (f'№{e(str(res.get("number", "")))} {e(res.get("name", ""))}' if res else "—")
            + '</td>'
            f'<td style="padding:9px 8px;text-align:center;font-family:monospace;font-size:13px;color:{color};">'
            f'{e(str(r.get("maturity_index")))}/6</td>'
            f'<td style="padding:9px 8px;text-align:center;font-family:monospace;font-size:13px;color:{color};">'
            f'{e(str(r.get("moving_count")))}</td>'
            '</tr>'
        )

    table = (
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="border-bottom:1px solid rgba(26,37,64,0.15);">'
        f'{th}Контур</th>{th}Сейчас</th>{th}Результирующая</th>'
        f'{th}Зрелость</th>{th}Подвижных</th></tr></thead>'
        f'<tbody>{body}</tbody></table>'
    )

    # Вывод о системном ограничении
    if summary.get("constraint"):
        name = next((r["title"] for r in rows if r["contour"] == summary["constraint"]), "")
        if summary.get("gap_significant"):
            verdict = (
                f'<b>{e(name)}</b> — наиболее вероятная зона системного ограничения по данным '
                f'диагностики. Отрыв от ближайшего контура — {e(str(summary.get("gap")))} балла '
                'зрелости, поэтому ресурсы рекомендуется сфокусировать здесь, а остальные '
                'контуры вести в поддерживающем режиме.'
            )
        else:
            verdict = (
                f'<b>{e(name)}</b> — наиболее вероятная зона системного ограничения по данным '
                'диагностики. Отрыв от остальных контуров невелик, поэтому работать с ними '
                'можно параллельно.'
            )
    else:
        tied = ", ".join(
            e(next((r["title"] for r in rows if r["contour"] == k), k))
            for k in (summary.get("tied") or [])
        )
        verdict = (
            'Контуры сопоставимы по зрелости'
            + (f' ({tied})' if tied else '')
            + ' — по данным диагностики одна функция не выделяется как ограничение. '
            'Выбор фокуса здесь остаётся управленческим решением, а не следствием расчёта.'
        )

    stable = summary.get("stable") or []
    stable_html = ""
    if stable:
        names = ", ".join(
            e(next((r["title"] for r in rows if r["contour"] == k), k)) for k in stable
        )
        stable_html = (
            '<p style="font-size:12px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;'
            f'line-height:1.6;margin:10px 0 0;">Без подвижных линий: {names}. '
            'Конфигурация устойчива, направленной трансформации не требуется.</p>'
        )

    # Сводный маршрут компании (роадмап 2.1)
    sr = summary.get("route") or {}
    summary_route_html = ""
    _stages = sr.get("stages") or []
    if _stages:
        _title_of = {r["contour"]: r["title"] for r in rows}
        _items = ""
        for st in _stages:
            cur = st.get("hexagram_current") or {}
            res = st.get("hexagram_resulting") or {}
            _title = _title_of.get(st["contour"], st["contour"])
            _items += (
                '<div style="display:flex;align-items:center;gap:12px;padding:8px 0;'
                'border-top:1px solid rgba(26,37,64,0.08);page-break-inside:avoid;">'
                f'<div style="font-size:12px;color:{accent};font-family:Arial,sans-serif;font-weight:700;min-width:58px;">Этап {st.get("stage")}</div>'
                f'<div style="flex:1;font-size:13px;color:{ink};font-family:Arial,sans-serif;">{e(_title)}'
                f'<div style="font-size:11px;color:rgba(26,37,64,0.55);">{st.get("route_len")} шаг(ов) · точка входа: линия {e(str(st.get("entry_line")))}</div></div>'
                f'<div style="display:flex;align-items:center;gap:6px;">{_finance_hexagram_svg(cur.get("code",""), [], 42)}'
                f'<span style="color:{accent};">→</span>{_finance_hexagram_svg(res.get("code",""), [], 42)}</div>'
                '</div>')
        _stable_route = ""
        if sr.get("stable"):
            _names2 = ", ".join(e(_title_of.get(k, k)) for k in sr["stable"])
            _stable_route = (f'<p style="font-size:12px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;'
                             f'margin:10px 0 0;">Стабильные контуры (без маршрута): {_names2}.</p>')
        _focus_route = ""
        if sr.get("focus_first"):
            _focus_route = (f'<p style="font-size:12px;color:{accent};font-family:Arial,sans-serif;margin:8px 0 0;">'
                            'Рекомендуется сфокусировать ресурсы на этапе 1; остальные контуры — в поддерживающем режиме.</p>')
        summary_route_html = (
            '<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:14px 18px;'
            'background:rgba(255,255,255,0.45);margin-top:16px;page-break-inside:avoid;">'
            f'<div style="font-size:11px;letter-spacing:1px;text-transform:uppercase;color:{accent};'
            'font-weight:600;font-family:Arial,sans-serif;margin-bottom:6px;">Сводный маршрут компании</div>'
            + _items + _stable_route + _focus_route +
            '</div>')

    # Матрица «контуры x уровни». Не свёртка: агрегировать контуры в одну
    # гексаграмму компании нечем. Даёт то, чего нет ни в зрелости, ни в
    # контуре-ограничении: один уровень слаб сразу в нескольких функциях —
    # это свойство организации, а не функции.
    lv_rows = summary.get("levels") or []
    levels_html = ""
    if lv_rows:
        _hdr = "".join(f'{th}{e(c["title"])}</th>' for c in lv_rows[0]["cells"])
        _body = ""
        for row in lv_rows:
            bg = ("background:rgba(192,57,43,0.06);" if row.get("systemic_weak")
                  else "background:rgba(26,37,64,0.04);" if row.get("systemic_strong")
                  else "")
            _tds = "".join(
                f'<td style="padding:8px;text-align:center;font-size:12px;'
                f'color:{accent if c["code"] == "BB" else ink};">{e(c["label"])}</td>'
                for c in row["cells"])
            _body += (
                f'<tr style="{bg}">'
                f'<td style="padding:8px;font-size:13px;color:{ink};">{e(row["title"])}'
                f'<span style="font-size:10px;color:rgba(26,37,64,0.45);"> · '
                f'{e(row["question"])}</span></td>' + _tds + '</tr>')
        _read = "".join(
            f'<p style="font-size:12px;color:{ink};font-family:Arial,sans-serif;'
            f'line-height:1.6;margin:8px 0 0;">{e(r["reading"])}</p>'
            for r in lv_rows if r.get("reading"))
        if not _read and summary.get("levels_note"):
            _read = ('<p style="font-size:12px;color:rgba(26,37,64,0.6);'
                     'font-family:Arial,sans-serif;line-height:1.6;margin:8px 0 0;">'
                     f'{e(summary["levels_note"])}</p>')
        levels_html = (
            '<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;'
            'padding:14px 18px;background:rgba(255,255,255,0.45);margin-top:16px;'
            'page-break-inside:avoid;">'
            f'<div style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
            f'color:{accent};font-weight:600;font-family:Arial,sans-serif;'
            'margin-bottom:8px;">Уровни по контурам</div>'
            '<table style="width:100%;border-collapse:collapse;">'
            '<thead><tr style="border-bottom:1px solid rgba(26,37,64,0.15);">'
            f'{th}Уровень</th>{_hdr}</tr></thead>'
            f'<tbody>{_body}</tbody></table>' + _read + '</div>')

    return (
        '<div style="padding:40px 50px;background:#e8e4db;page-break-before:always;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:24px;">'
        f'<span style="font-size:11px;font-weight:700;color:{accent};font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>'
        f'<span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">{e(company_name)} · сводная карта</span>'
        '</div>'
        f'<h2 style="font-size:22px;font-weight:400;color:{ink};margin:0 0 8px;">'
        f'{section_badge(section_no)}Сводная карта контуров</h2>'
        '<p style="font-size:12px;color:rgba(26,37,64,0.55);font-family:Arial,sans-serif;'
        'line-height:1.6;margin:0 0 18px;">Контуры оценены по одной шкале, поэтому их зрелость '
        'сравнима между собой. Гексаграммы контуров описывают зрелость функции и не связаны '
        'с гексаграммой раздела 01: там линии означают тип бизнеса, здесь — уровень зрелости.</p>'
        '<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:12px 16px;'
        'background:rgba(255,255,255,0.45);page-break-inside:avoid;">'
        + table +
        '</div>'
        '<div style="border:1px solid rgba(192,57,43,0.2);border-radius:6px;padding:16px 20px;'
        'background:rgba(192,57,43,0.04);margin-top:16px;page-break-inside:avoid;">'
        f'<p style="font-size:13px;color:{ink};font-family:Arial,sans-serif;line-height:1.7;margin:0;">{verdict}</p>'
        + stable_html +
        '</div>'
        + levels_html
        + summary_route_html +
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);'
        'display:flex;justify-content:space-between;font-family:Arial,sans-serif;font-size:10px;color:rgba(26,37,64,0.3);">'
        '<span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>'
        '</div></div>'
    )
