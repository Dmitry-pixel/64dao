# -*- coding: utf-8 -*-
"""
Метод 4 «Алмазное колесо» — HTML для PDF.

Вход — та же структура, что отдаёт веб-отчёт (m4_report.build): порядок
разделов, отбор карточек и тексты здесь не решаются, только вёрстка. Поэтому
веб и PDF не расходятся по содержанию; расходиться может только вид.

Палитра, колонтитулы и заголовки разделов — общие с PDF Метода 3 (m3_pdf):
один продукт, один вид документа.

Колесо рисуется той же геометрией, что компонент M4Wheel на фронтенде:
спицы по номеру модуля по часовой стрелке от верха, кольца 40 и 70.
"""
from __future__ import annotations

import math
from typing import Any

from app.m3_pdf import BG, DARK, LINE, MUTED, PAPER, RED, SERIF, banner, e, page, section_title

STATE_COLOR = {"low": RED, "mid": "#c8902a", "high": "#2e7d5b"}
STATE_LABEL = {"low": "низкий", "mid": "средний", "high": "высокий"}
SEVERITY_LABEL = {"high": "серьёзное", "medium": "заметное", "low": "слабое"}

P = f"font-size:13px;line-height:1.6;margin:0 0 8px;font-family:{SERIF};"
SUB = (f"font-size:10px;letter-spacing:0.08em;text-transform:uppercase;color:{MUTED};"
       f"margin:10px 0 3px;font-family:Arial,sans-serif;")
CARD = (f"background:{PAPER};border:1px solid {LINE};border-radius:4px;padding:12px 16px;"
        f"margin:0 0 10px;page-break-inside:avoid;")


def rnd(v: float) -> int:
    """Округление как Math.round во вебе. Встроенное в Питон банковское
    (34,5 даёт 34), и одна цифра выглядела бы в вебе и PDF по-разному."""
    return int(math.floor(v + 0.5))


def _state(score: float | None) -> str | None:
    if score is None:
        return None
    return "low" if score < 40 else "high" if score >= 70 else "mid"


def _score(score: float | None, state: str | None) -> str:
    color = STATE_COLOR.get(state or "", MUTED)
    txt = "—" if score is None else str(rnd(score))
    lbl = STATE_LABEL.get(state or "", "нет данных")
    return (f'<span style="font-family:Arial,sans-serif;font-size:11px;color:{color};'
            f'white-space:nowrap;">{txt} · {lbl}</span>')


def wheel_svg(modules: list[dict], highlight: int | None) -> str:
    cx, cy, r = 400, 250, 170

    def pt(i: int, v: float) -> tuple[float, float]:
        a = math.radians(-90 + i * 36)
        return cx + math.cos(a) * r * v / 100, cy + math.sin(a) * r * v / 100

    by_code = {m["code"]: m for m in modules}
    parts = ['<svg viewBox="0 0 800 500" width="100%" xmlns="http://www.w3.org/2000/svg" '
             'style="display:block;">']
    for ring in (40, 70, 100):
        dash = "" if ring == 100 else ' stroke-dasharray="3 4"'
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r * ring / 100:.1f}" fill="none" '
                     f'stroke="rgba(26,37,64,0.18)"{dash}/>')
    for i in range(10):
        x, y = pt(i, 100)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="rgba(26,37,64,0.14)"/>')
    pts = [pt(i, by_code.get(i + 1, {}).get("score") or 0) for i in range(10)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    parts.append(f'<polygon points="{poly}" fill="rgba(26,37,64,0.12)" stroke="{DARK}" stroke-width="1.5"/>')
    for i in range(10):
        m = by_code.get(i + 1, {"code": i + 1, "name": "", "score": None})
        v = m.get("score")
        st = _state(v)
        color = STATE_COLOR.get(st or "", "#999")
        x, y = pt(i, v or 0)
        lx, ly = pt(i, 118)
        anchor = "middle" if abs(lx - cx) < 20 else "start" if lx > cx else "end"
        hl = m["code"] == highlight
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{7 if hl else 4.5}" fill="{color}"'
                     + (f' stroke="{DARK}" stroke-width="2"' if hl else "") + "/>")
        weight = ' font-weight="700"' if hl else ""
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-family="Arial,sans-serif" '
                     f'font-size="12" fill="{DARK}"{weight}>{m["code"]}. {e(m.get("name"))}</text>')
        parts.append(f'<text x="{lx:.1f}" y="{ly + 15:.1f}" text-anchor="{anchor}" font-family="Arial,sans-serif" '
                     f'font-size="12" fill="{color}">{"—" if v is None else rnd(v)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _mistake(text: str | None) -> str:
    if not text:
        return ""
    return (f'<p style="font-size:12px;line-height:1.55;color:{MUTED};border-left:2px solid {RED};'
            f'padding-left:10px;margin:8px 0 0;font-family:{SERIF};"><b>Типичная ошибка.</b> {e(text)}</p>')


def _card_body(card: dict | None) -> str:
    if not card:
        return ""
    return (f'<div style="font-size:16px;margin:0 0 6px;font-family:{SERIF};color:{DARK};">{e(card["title"])}</div>'
            f'<p style="{P}">{e(card["body"])}</p>' + _mistake(card.get("mistake")))


def _list(items: list[str] | None, ordered: bool = False) -> str:
    if not items:
        return ""
    tag = "ol" if ordered else "ul"
    lis = "".join(f"<li>{e(x)}</li>" for x in items)
    return f'<{tag} style="{P}padding-left:18px;margin-bottom:4px;">{lis}</{tag}>'


def _tag(text: str, color: str = DARK, bg: str = "rgba(26,37,64,0.08)") -> str:
    return (f'<span style="display:inline-block;font-family:Arial,sans-serif;font-size:10px;'
            f'padding:1px 7px;border-radius:8px;margin-right:5px;background:{bg};color:{color};">{e(text)}</span>')


# ── Разделы ───────────────────────────────────────────────────────────────────
def header(rep: dict) -> str:
    run = rep["run"]
    meta = []
    if run.get("calculated_at"):
        meta.append(f"Рассчитано {run['calculated_at'].strftime('%d.%m.%Y')}")
    meta.append("Полная диагностика" if run["mode"] == "full" else "Экспресс-диагностика")
    meta.append(f"Достоверность ответов: {rep['confidence']['index']} из 100")
    meta_html = "".join(f'<span style="margin-right:24px;white-space:nowrap;">{e(m)}</span>' for m in meta)
    return (
        f'<header style="border-bottom:2px solid {DARK};padding-bottom:14px;font-family:{SERIF};">'
        f'<div style="font-size:11px;letter-spacing:0.18em;color:{MUTED};text-transform:uppercase;'
        f'font-family:Arial,sans-serif;">64DAO · Метод 4</div>'
        f'<h1 style="font-size:26px;margin:9px 0 6px;font-weight:normal;color:{DARK};">'
        f'Алмазное колесо · {e(run.get("company_name") or "Компания")}</h1>'
        f'<div style="font-size:12px;color:{MUTED};margin-top:9px;line-height:1.9;">{meta_html}</div>'
        f'</header>'
    )


def summary(rep: dict) -> str:
    full = rep["run"]["mode"] == "full"
    c = rep["constraint"]
    parts = []
    if full and c:
        blocked = ", ".join(b["name"] for b in c["blocked"])
        parts.append(f'Системное ограничение — <b>{c["module"]}. {e(c["name"])}</b>. '
                     f'От него зависит отдача модулей: {e(blocked)}. Начинать с него.')
    elif full:
        parts.append("Все управленческие модули на высоком уровне — системного ограничения нет.")
    gaps = "; ".join(f'{g["code"]}. {g["name"]}' for g in rep["top_gaps"])
    parts.append(f"Самые большие разрывы: {e(gaps)}.")
    if rep.get("cause_effect") and rep["cause_effect"].get("text"):
        parts.append(e(rep["cause_effect"]["text"]))
    return banner("Главное", "<br><br>".join(parts))


def constraint_section(no: str, rep: dict) -> str:
    c = rep["constraint"]
    return (
        section_title(no, "Системное ограничение")
        + f'<p style="{P}color:{MUTED};">Не самый низкий балл, а модуль, от которого зависят сильные. '
          f'Пока он не подтянут, вложения в зависимые модули окупаются хуже.</p>'
        + f'<div style="{CARD}border-left:3px solid {RED};">'
          f'<div style="font-size:11px;color:{MUTED};font-family:Arial,sans-serif;margin-bottom:6px;">'
          f'{c["module"]}. {e(c["name"])} · {_score(c["score"], _state(c["score"]))}</div>'
        + _card_body(c.get("card")) + "</div>"
    )


def actions_section(no: str, rep: dict) -> str:
    lead = ("Действия по порядку: сначала системное ограничение, затем то, что даёт больший результат "
            "быстрее и дешевле")
    if rep.get("resistance", 1) > 1:
        lead += " — с поправкой на то, что изменения в компании даются с сопротивлением"
    lead += ". Действия по модулям, которые зависят от ограничения, стоят в конце."
    out = [section_title(no, "С чего начинать"), f'<p style="{P}color:{MUTED};">{e(lead)}</p>']
    for a in rep["actions"]:
        tags = _tag(str(a["n"]), "#fff", DARK)
        if a["is_constraint"]:
            tags += _tag("системное ограничение", RED, "rgba(192,57,43,0.12)")
        if a["blocked_by_constraint"]:
            tags += _tag("после снятия ограничения")
        tags += _tag(a.get("module_name") or "противоречие")
        body = f'<p style="{P}">{e(a["body"])}</p>' if a.get("body") else ""
        steps = (f'<div style="{SUB}">Шаги</div>' + _list(a["steps"], ordered=True)) if a.get("steps") else ""
        opts = (f'<div style="{SUB}">Выберите один из вариантов</div>' + _list(a["options"])
                if a.get("options") else "")
        first = (f'<div style="{SUB}">С чего начать</div><p style="{P}">{e(a["first_step"])}</p>'
                 if a.get("first_step") else "")
        check = (f'<div style="{SUB}">Как проверить</div><p style="{P}">{e(a["how_to_check"])}</p>'
                 if a.get("how_to_check") else "")
        meta = (f'<div style="font-size:10px;color:{MUTED};font-family:Arial,sans-serif;margin-top:6px;">'
                f'Вклад в результат {a["effect"]} из 3 · первый результат через {a["speed_weeks"]} нед. · '
                f'затраты на внедрение {a["cost"]} из 3</div>')
        out.append(
            f'<div style="{CARD}"><div style="margin-bottom:6px;">{tags}</div>'
            f'<div style="font-size:16px;margin:0 0 6px;font-family:{SERIF};color:{DARK};">{e(a["title"])}</div>'
            f"{body}{steps}{opts}{first}{check}{meta}</div>"
        )
    return "".join(out)


def contradictions_section(no: str, rep: dict) -> str:
    out = [
        section_title(no, "Противоречия"),
        f'<p style="{P}color:{MUTED};">Сочетания ответов, которые по отдельности выглядят нормально, '
        f'а вместе указывают на то, что компания работает против себя.</p>',
    ]
    for x in rep["contradictions"]:
        color = RED if x["severity"] == "high" else DARK
        out.append(
            f'<div style="{CARD}"><div style="margin-bottom:6px;">'
            f'{_tag(SEVERITY_LABEL.get(x["severity"], ""), color)}</div>'
            f'<div style="font-size:16px;margin:0 0 6px;font-family:{SERIF};color:{DARK};">{e(x["title"])}</div>'
            f'<p style="{P}">{e(x["diagnosis"])}</p>'
            f'<div style="{SUB}">Что происходит</div><p style="{P}">{e(x["what_happens"])}</p>'
            f'<div style="{SUB}">Как развязать — один из вариантов</div>{_list(x["fix_one_of"])}'
            f'<div style="{SUB}">Цена бездействия</div><p style="{P}">{e(x["cost_of_inaction"])}</p></div>'
        )
    if rep["unverified"]:
        titles = "; ".join(u["title"] for u in rep["unverified"])
        out.append(f'<p style="font-size:11px;color:{MUTED};font-family:Arial,sans-serif;">'
                   f'Не удалось проверить из-за ответов «Не знаю»: {e(titles)}.</p>')
    return "".join(out)


def modules_section(no: str, rep: dict) -> str:
    c = rep["constraint"]
    out = [section_title(no, "Состояние модулей")]
    for m in rep["modules"]:
        mark = f' · <span style="color:{RED};">системное ограничение</span>' if c and c["module"] == m["code"] else ""
        acc = (f'<p style="font-size:11px;color:{MUTED};font-family:Arial,sans-serif;margin:6px 0 0;">'
               f'На большинство вопросов о фактах этого модуля ответ «Не знаю»: в компании нет учёта '
               f'по этому направлению. Это само по себе диагноз.</p>') if m["no_accounting"] else ""
        out.append(
            f'<div style="{CARD}"><div style="display:flex;justify-content:space-between;margin-bottom:6px;'
            f'font-size:11px;color:{MUTED};font-family:Arial,sans-serif;">'
            f'<span>{m["code"]}. {e(m["name"])}{mark}</span>{_score(m["score"], m["state"])}</div>'
            + _card_body(m.get("card")) + acc + "</div>"
        )
    return "".join(out)


def confidence_section(no: str, rep: dict) -> str:
    conf = rep["confidence"]
    acc = ""
    if conf["no_accounting"]:
        acc = (f'<p style="font-size:11px;color:{MUTED};font-family:Arial,sans-serif;margin:6px 0 0;">'
               f'Нет учёта: {e(", ".join(m["name"] for m in conf["no_accounting"]))}.</p>')
    return (
        section_title(no, "Достоверность ответов")
        + f'<div style="{CARD}"><div style="font-size:11px;color:{MUTED};font-family:Arial,sans-serif;'
          f'margin-bottom:6px;">Индекс {conf["index"]} из 100</div>'
        + _card_body(conf.get("card")) + acc + "</div>"
    )


def build_report_html(rep: dict[str, Any]) -> str:
    full = rep["run"]["mode"] == "full"
    first = header(rep)
    if rep["confidence"]["cautious"]:
        first += banner("Осторожный режим",
                        "Слишком много ответов «Не знаю» или ответы расходятся между собой. "
                        "Выводы ниже — гипотезы для проверки, а не основание для решений.", warn=True)
    wheel = wheel_svg(rep["modules"], (rep["constraint"] or {}).get("module"))
    first += (f'<div style="margin:14px 0 4px;">{wheel}</div>'
              f'<p style="font-size:11px;color:{MUTED};font-family:Arial,sans-serif;margin:0 0 10px;">'
              f'Балл модуля от 0 до 100. Пунктирные кольца — границы 40 и 70: ниже 40 — низкий уровень, '
              f'от 70 — высокий. Модуль 10 «Финансы» — следствие решений в остальных девяти.</p>')
    first += summary(rep)
    sheets = [page(first, first=True)]

    n = 0

    def num() -> str:
        nonlocal n
        n += 1
        return f"{n:02d}"

    if full and rep["constraint"]:
        sheets.append(page(constraint_section(num(), rep)
                           + (actions_section(num(), rep) if rep["actions"] else "")))
    elif full and rep["actions"]:
        sheets.append(page(actions_section(num(), rep)))
    if full and (rep["contradictions"] or rep["unverified"]):
        sheets.append(page(contradictions_section(num(), rep)))
    sheets.append(page(modules_section(num(), rep)))
    tail = confidence_section(num(), rep)
    if not full:
        tail += banner("Что даст полная диагностика",
                       "Экспресс показывает разрывы, но не называет модуль, который сдерживает остальные, "
                       "не ищет противоречия и не выстраивает очередь действий. Это делает полная "
                       "диагностика — ответы экспресса в неё перенесутся.")
    sheets.append(page(tail))

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Алмазное колесо — {e(rep["run"].get("company_name") or "")}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: {SERIF}; background: {BG}; color: {DARK};
         -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  li {{ margin-bottom: 2px; }}
</style>
</head>
<body>
{"".join(sheets)}
</body>
</html>"""
