# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — сборщик HTML для PDF.

Конвенция проекта: вёрстка отчёта существует в двух экземплярах — React для
веба и питоновский сборщик для PDF, синхронизируются вручную. Так сделано у
Метода 2 (finance_pdf.py), здесь то же самое.

Геометрия карты портфеля вынесена в m3_map: это единственная часть, которая
может разойтись с вебом молча, и у неё отдельный тест против эталона.

Источник вёрстки — 64dao-portfolio-report-sample.html версии 0.2. Порядок
разделов его: шапка, 00 исходные данные, 01 карта, 02 разбор, 03 портфельные
ограничения, 04 решение, оговорки. Титульной страницы нет — в отличие от
Методов 1 и 2 документ начинается шапкой.
"""
from __future__ import annotations

import html as html_lib
from typing import Any

from app.m3_map import map_caption, render_map_svg
from app.m3_portfolio import (
    constraints,
    metric_readings,
    rank_comparison,
    rank_comparison_reading,
    tact_note,
    yin_table,
)
from app.m3_verdict import (
    cell_breakdown_text,
    cell_label,
    execution_reason,
    market_label,
    verdict_for,
)
from app.m3_verdict import transition as trajectory

# ── Палитра образца ───────────────────────────────────────────────────────────
BG = "#e8e4db"
PAPER = "#f4f2ec"
DARK = "#1a2540"
RED = "#c0392b"
BLUE = "#1e3a8a"
LINE = "#cfc9bc"
MUTED = "#6b6559"
ROW_LINE = "#e2ddd2"

SERIF = "Georgia,'Times New Roman',serif"

PORTFOLIO_FLAG_LABELS = {
    "UNIFORM_PORTFOLIO": "все направления в одной ячейке — формулировки их не различили",
    "SELF_INFLATION": "оценки систематически завышены",
    "RANK_MISMATCH": "расчёт расходится с порядком, названным собственником",
}

PROFITABILITY_LABELS = {
    "profitable": "прибыльно",
    "marginal": "на грани",
    "unprofitable": "убыточно",
    "unknown": "не указана",
}


def e(text: Any) -> str:
    return html_lib.escape("" if text is None else str(text), quote=True)


# ── Числа ─────────────────────────────────────────────────────────────────────
def num(value: float | None, digits: int = 0, dash: str = "—") -> str:
    """
    Число по-русски: запятая как десятичный разделитель, как в образце.

    Веб сейчас печатает точку (toFixed). Требование «веб и PDF одинаково»
    означает, что фронт тоже переходит на запятую, — иначе одно и то же
    значение выглядит по-разному в двух каналах одного отчёта.
    """
    if value is None:
        return dash
    return f"{float(value):.{digits}f}".replace(".", ",")


def signed_percent(value: float | None) -> str:
    """Динамика выручки: знак обязателен, иначе падение читается как рост."""
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{num(value, 0)}%"


def signed(value: int | None) -> str:
    if value is None:
        return "—"
    return f"+{value}" if value > 0 else str(value)


# ── Каркас страницы ───────────────────────────────────────────────────────────
def page(body: str, first: bool = False) -> str:
    """
    Раздел документа. Разрыв страницы ставится перед разделом, а не после:
    иначе последний тянет за собой пустую страницу.

    Колонтитулов внутри нет намеренно. Свёрстанные блоком, они не умеют
    повторяться: в разделе на пять страниц шапка рисовалась один раз сверху,
    подвал один раз снизу, страницы между ними оставались голыми, а подвал,
    не поместившийся на последнюю, утягивал за собой пустую страницу.
    Теперь колонтитулы печатает браузер — см. header_template/footer_template.
    """
    brk = "" if first else "page-break-before:always;"
    return f'<div style="padding:0 40px;background:{BG};{brk}">{body}</div>'


def header_template(company_name: str) -> str:
    """
    Печатный колонтитул. Живёт в поле страницы, повторяется на каждой.

    Шрифт задаётся явно и в пунктах: собственный CSS документа сюда не
    доходит, а по умолчанию браузер печатает колонтитул десятым кеглем
    системным шрифтом.
    """
    return (
        f'<div style="width:100%;font-size:8pt;font-family:Arial,sans-serif;'
        f'color:{MUTED};padding:0 12mm;display:flex;justify-content:space-between;'
        f'border-bottom:0.5pt solid {LINE};padding-bottom:2mm;">'
        f'<span style="font-weight:bold;color:{RED};letter-spacing:1pt;">64DAO</span>'
        f'<span>{e(company_name)}</span></div>'
    )


def footer_template() -> str:
    """Подвал с номером страницы: в документе на дюжину листов он нужнее,
    чем повтор адреса сайта на каждой."""
    return (
        f'<div style="width:100%;font-size:8pt;font-family:Arial,sans-serif;'
        f'color:{MUTED};padding:0 12mm;display:flex;justify-content:space-between;'
        f'border-top:0.5pt solid {LINE};padding-top:2mm;">'
        f'<span>64dao.ru · © 2024 64DAO — Конфиденциально</span>'
        f'<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
        f'</div>'
    )


# Поля под печатные колонтитулы. Боковых нет: фон страницы должен доходить
# до края, а отступ содержимого задаёт сам раздел.
PDF_MARGIN = {"top": "16mm", "right": "0", "bottom": "14mm", "left": "0"}


def section_title(number: str, title: str) -> str:
    from app.finance_pdf import section_badge

    return (
        f'<h2 style="font-size:13px;letter-spacing:0.10em;text-transform:uppercase;'
        f'font-weight:normal;color:{MUTED};border-bottom:1px solid {LINE};'
        f'padding-bottom:6px;margin:20px 0 13px;font-family:{SERIF};">'
        f'{section_badge(number, small=True)}{e(title)}</h2>'
    )


def banner(title: str, body: str, warn: bool = False) -> str:
    color = RED if warn else BLUE
    return (
        f'<div style="border-left:3px solid {color};background:{PAPER};'
        f'padding:8px 12px;margin:8px 0;font-size:13px;font-family:{SERIF};'
        f'line-height:1.5;page-break-inside:avoid;">'
        f'<span style="font-size:11px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:{MUTED};display:block;margin-bottom:5px;">{e(title)}</span>{body}</div>'
    )


def table(headers: list[tuple[str, bool]], rows: list[list[str]]) -> str:
    """headers — пары (подпись, выравнивание по правому краю)."""
    th = "".join(
        f'<th style="text-align:{"right" if right else "left"};font-weight:normal;'
        f'color:{MUTED};font-size:11px;letter-spacing:0.04em;text-transform:uppercase;'
        f'border-bottom:1px solid {LINE};padding:7px 8px 7px 0;vertical-align:bottom;">'
        f"{e(label)}</th>"
        for label, right in headers
    )
    body = ""
    for row in rows:
        cells = "".join(
            f'<td style="padding:7px 8px 7px 0;border-bottom:1px solid {ROW_LINE};'
            f'vertical-align:top;text-align:{"right" if headers[i][1] else "left"};">'
            f"{cell}</td>"
            for i, cell in enumerate(row)
        )
        body += f"<tr>{cells}</tr>"
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:13px;'
        f'margin:12px 0;font-family:{SERIF};">'
        f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"
    )


# ── Шапка отчёта ──────────────────────────────────────────────────────────────
def report_header(
    company_name: str,
    portfolio: Any,
    summary: dict[str, Any],
    industry_name: str | None = None,
) -> str:
    """
    Заголовок — название отчёта вместе с названием компании, как в Методе 1.
    Строка «Матрица силы» стоит в заголовке, а не в надзаголовке, чтобы не
    дублироваться. Титульной страницы нет.
    """
    title = getattr(portfolio, "title", None) or "Портфель без названия"
    # У портфелей, созданных до миграции 024, название компании
    # разрешается в название портфеля — подзаголовок повторял бы заголовок
    # слово в слово. Печатаем его только когда он что-то добавляет.
    subtitle = "" if title == company_name else (
        f'<div style="font-size:14px;color:{MUTED};">{e(title)}</div>'
    )
    calculated = getattr(portfolio, "calculated_at", None)
    meta: list[str] = []
    if calculated is not None:
        meta.append(f"Рассчитано {calculated.strftime('%d.%m.%Y')}")
    meta.append(f"Направлений: {summary['objects']}")
    meta.append(f"Сумма позиций: {summary['sum_positions']} из {summary['sum_positions_max']}")
    meta.append(f"Подвижных линий: {summary['turbulence']}")
    meta.append(f"Δ: {signed(summary['delta'])}")
    if industry_name:
        meta.append(f"Веса: {industry_name}")

    meta_html = "".join(
        f'<span style="margin-right:24px;white-space:nowrap;">{e(m)}</span>' for m in meta
    )
    return f"""<header style="border-bottom:2px solid {DARK};padding-bottom:16px;font-family:{SERIF};">
<div style="font-size:11px;letter-spacing:0.18em;color:{MUTED};text-transform:uppercase;font-family:Arial,sans-serif;">64DAO · Метод 3</div>
<h1 style="font-size:26px;margin:9px 0 6px;font-weight:normal;color:{DARK};">Матрица силы · {e(company_name)}</h1>
{subtitle}
<div style="font-size:12px;color:{MUTED};margin-top:11px;line-height:1.9;">{meta_html}</div>
</header>"""


def data_status_banner(summary: dict[str, Any], flag_labels: dict[str, str]) -> str:
    """
    Статус данных. При портфельном флаге вердикты аллокации удержаны: диагноз
    и маршруты в отчёте есть, распределение ресурса — нет.
    """
    spearman = summary.get("spearman")
    # Величина расхождения печатается в обеих ветках. Раньше Спирмен выводился
    # только там, где проверки пройдены, — то есть молчал ровно тогда, когда
    # расхождение и было. Читатель видел название флага и не мог отличить
    # «почти согласны» от «противоположны».
    rho = ("" if spearman is None
           else f" Ранговая корреляция с вашим порядком — {num(spearman, 2)}.")
    if summary.get("verdicts_held"):
        flags = "; ".join(flag_labels.get(f, f) for f in summary.get("flags") or [])
        return banner(
            "Вердикты аллокации удержаны",
            f"Сработал портфельный флаг качества данных: {e(flags)}. "
            f"Диагноз и маршруты ниже приведены, распределение ресурса — нет.{rho}",
            warn=True,
        )
    agreement = ""
    if spearman is not None:
        agreement = (
            f" Корреляция расчётного приоритета с порядком, названным вами до "
            f"диагностики, — {num(spearman, 2)}."
        )
    return banner(
        "Статус данных",
        "Проверки полноты и согласованности пройдены. Вердикты выданы "
        f"в полном объёме.{agreement} Частные оговорки — в конце отчёта.",
    )


# ── 00 Исходные данные ────────────────────────────────────────────────────────



def objects_section(
    objects: list[Any],
    market_by_object: dict[str, str] | None = None,
) -> str:
    """
    Числовые якоря: то, что респондент знает точно, а не оценивает.

    Колонка «Рынок» в образце показывает, наследует ли направление рыночный
    блок или переопределяет его. Источник — наличие ответов блока Р* у
    направления, а не флаги скрининга: флаг говорит, что спросили, а не что
    ответили. Этих данных в снимке расчёта нет, поэтому колонка рисуется
    только когда вызывающая сторона их передала. Пока m3_service их не
    отдаёт, столбца просто нет — это лучше, чем столбец, который врёт.
    """
    show_market = market_by_object is not None
    headers = [
        ("№", False), ("Направление", False), ("Выручка", True),
        ("Динамика", True), ("Доля", True), ("Прибыльность", False),
    ]
    if show_market:
        headers.append(("Рынок", False))

    rows = []
    for o in objects:
        oid = str(o.id)
        row = [
            e(o.position),
            e(o.name),
            num(getattr(o, "revenue", None), 0),
            signed_percent(_f(getattr(o, "revenue_dynamics", None))),
            "—" if getattr(o, "revenue_share", None) is None
            else f"{num(o.revenue_share, 0)}%",
            e(PROFITABILITY_LABELS.get(getattr(o, "profitability", "unknown"),
                                       getattr(o, "profitability", ""))),
        ]
        if show_market:
            row.append(e(market_by_object.get(oid, "—")))
        rows.append(row)

    return section_title("00", "Исходные данные") + table(headers, rows)


def _f(value: Any) -> float | None:
    """Numeric из БД приходит Decimal — приводим, иначе форматирование падает."""
    return None if value is None else float(value)


# ── 01 Карта портфеля ─────────────────────────────────────────────────────────
def map_section(
    results: list[dict[str, Any]],
    shares: dict[str, float | None],
    summary: dict[str, Any],
) -> str:
    """
    Карта и таблица направлений под ней. Таблица есть в образце и отвечает на
    вопрос, который по кругам не прочитать: какая у направления конфигурация
    линий. Две точки в одной ячейке могут иметь противоположные вердикты —
    ровно это в образце показано на направлениях 2 и 3.
    """
    svg = render_map_svg(results, shares)
    caption = map_caption(results)

    rows = []
    for r in results:
        rows.append([
            e(r["position"]),
            e(r["name"]),
            e(cell_label(r["cell_strength"], r["cell_attract"])),
            f'<span style="font-family:\'Courier New\',monospace;letter-spacing:0.14em;">'
            f'{e(r["symbols"])}</span>',
            e(r["current_hex"]),
            "—" if r.get("target_hex") is None
            else f'<span style="color:{BLUE};">{e(r["target_hex"])}</span>',
            "—" if r.get("risk_hex") is None
            else f'<span style="color:{RED};">{e(r["risk_hex"])}</span>',
            e(len(r.get("mobility") or {})),
        ])

    cells_note = (
        f"Занято разных ячеек: {summary['distinct_cells']} из 9."
        if summary.get("distinct_cells") is not None else ""
    )

    return (
        section_title("01", "Карта портфеля")
        + f'<div style="page-break-inside:avoid;">{svg}'
        + f'<div style="font-size:12px;color:{MUTED};line-height:1.7;margin-top:8px;'
        f'max-width:430px;font-family:{SERIF};">{e(caption)}</div></div>'
        + f'<p style="font-size:12px;color:{MUTED};line-height:1.7;font-family:{SERIF};">'
        f"Ячейку задаёт сумма отраслевых весов сильных линий в триграмме, положение внутри ячейки — "
        f"взвешенная координата по отраслевому пресету. {e(cells_note)}</p>"
        + table(
            [("№", False), ("Направление", False), ("Ячейка", False), ("Код", False),
             ("Текущая", True), ("Цель", True), ("Риск", True), ("Подв.", True)],
            rows,
        )
    )


# ── 02 Разбор направлений ─────────────────────────────────────────────────────
LINE_TITLES = {
    1: "ресурсы и юнит-экономика",
    2: "продукт и дифференциация",
    3: "каналы и доля",
    4: "спрос сегмента",
    5: "структура рынка, маржа",
    6: "макро и регулирование",
}

MOBILITY_LABELS = {
    "old_yin": "Старый Инь · подвижная",
    "old_yang": "Старый Ян · подвижная",
}

STEP_LABELS = {
    "route": "Шаг маршрута",
    "hold": "Пакет удержания",
    "prep": "Подготовительный шаг",
    "decision": "Решение владельца",
}

FLAG_LABELS = {
    "BORDERLINE_LINE": "пограничный балл линии",
    "NEAR_OLD_YANG": "балл подходит к границе перегрева",
    "NEAR_OLD_YIN": "балл подходит к границе назревшей слабости",
    "VETO_UNPROFITABLE": "вето по убыточности: символ линии 1 понижен до Инь "
                         "независимо от балла",
    "VETO_UNKNOWN": "прибыльность не указана — это сам по себе диагноз линии ресурсов",
    "VETO_MOBILITY_CONFLICT": "вето и перегрев на одной линии — случай требует разбора вручную",
    "REVENUE_CONTRADICTION": "выручка падает при высокой оценке спроса",
    "ECONOMY_CONTRADICTION": "направление убыточно при высокой оценке экономики",
    "SCALE_CONTRADICTION": "крупная доля выручки при слабом канале",
    "STRAIGHTLINING": "все шесть линий совпали — анкета заполнена однородно",
}


def line_glyph(yang: bool, moving: bool) -> str:
    """
    Глиф линии. Инь — разрыв посередине, Ян — сплошная. Подвижная красная:
    именно подвижность несёт рекомендацию, а не сам символ.
    """
    color = RED if moving else DARK
    bar = (f'<span style="display:inline-block;height:9px;background:{color};'
           'vertical-align:middle;')
    if yang:
        return f'{bar}width:66px;"></span>'
    return (
        f'{bar}width:28px;"></span>'
        '<span style="display:inline-block;width:10px;"></span>'
        f'{bar}width:28px;"></span>'
    )


def lines_block(result: dict[str, Any]) -> str:
    """Шесть линий сверху вниз: Л6 первой, как в гексаграмме."""
    rows = ""
    for n in (6, 5, 4, 3, 2, 1):
        yang = result["symbols"][n - 1] == "A"
        state = (result.get("mobility") or {}).get(str(n))
        label = MOBILITY_LABELS.get(state) if state else ("Ян" if yang else "Инь")
        score = (result.get("scores") or {}).get(f"l{n}")
        rows += (
            f'<tr><td style="width:76px;padding:3px 10px 3px 0;">'
            f"{line_glyph(yang, bool(state))}</td>"
            f'<td style="padding:2px 0;font-size:13px;">Л{n} · {e(LINE_TITLES[n])}</td>'
            f'<td style="padding:3px 0;font-size:13px;text-align:right;width:46px;'
            f'color:{MUTED};">{num(score, 2)}</td>'
            f'<td style="padding:3px 0 3px 14px;font-size:12px;width:160px;'
            f'color:{RED if state else MUTED};">{e(label)}</td></tr>'
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;margin:10px 0;'
        f'font-family:{SERIF};page-break-inside:avoid;"><tbody>{rows}</tbody></table>'
    )


def cell_breakdown_block(result: dict[str, Any]) -> str:
    """
    Вывод ячейки под таблицей линий. Печатается всегда, а не только когда
    расходится с баллами: иначе клиент не поймёт, почему у одного
    направления пояснение есть, а у другого нет. Заодно делает отраслевой
    пресет видимым — до этого выбор области на входе нигде не всплывал.

    У снимков до ревизии 030 весов нет, и блока не будет: достраивать их
    задним числом значит выдумать данные.
    """
    breakdown = result.get("cell_breakdown")
    if not breakdown:
        return ""
    rows = "".join(
        f'<div style="margin:2px 0;">{e(cell_breakdown_text(axis, breakdown[axis]))}</div>'
        for axis in ("strength", "attract") if breakdown.get(axis)
    )
    return (
        f'<div style="font-size:12px;color:{MUTED};margin:-4px 0 10px;'
        f'font-family:{SERIF};page-break-inside:avoid;">{rows}</div>'
    )


def hexagram_line(result: dict[str, Any]) -> str:
    """Код, текущая гексаграмма и оба вектора одной строкой."""
    parts = [
        f'<span style="font-family:\'Courier New\',monospace;font-size:15px;'
        f'letter-spacing:0.14em;">{e(result["symbols"])}</span>',
        f'текущая № {e(result["current_hex"])}',
    ]
    if result.get("target_hex") is not None:
        parts.append(f'<span style="color:{BLUE};">цель № {e(result["target_hex"])}</span>')
    if result.get("risk_hex") is not None:
        parts.append(f'<span style="color:{RED};">риск № {e(result["risk_hex"])}</span>')
    if result.get("target_hex") is None and result.get("risk_hex") is None:
        parts.append(f'<span style="color:{MUTED};">подвижных линий нет — '
                     "ограничение стабильно</span>")
    return (
        f'<div style="font-size:13px;margin-top:4px;color:{DARK};">'
        + '<span style="margin-right:20px;">'
        + '</span><span style="margin-right:20px;">'.join(parts)
        + "</span></div>"
    )


def facts_line(result: dict[str, Any], obj: Any) -> str:
    """Строка фактов под заголовком: зона, деньги, ранги."""
    bits = [e(cell_label(result["cell_strength"], result["cell_attract"]))]
    revenue = _f(getattr(obj, "revenue", None))
    if revenue is not None:
        bits.append(f"{num(revenue, 0)} млн ₽")
    dynamics = _f(getattr(obj, "revenue_dynamics", None))
    if dynamics is not None:
        bits.append(f"{signed_percent(dynamics)} за год")
    share = _f(getattr(obj, "revenue_share", None))
    if share is not None:
        bits.append(f"{num(share, 0)}% выручки")
    bits.append(f'V = {num(result["v_index"], 3)} (ранг {e(result["v_rank"])})')
    bits.append(f'Z = {num(result["z_index"], 3)} (ранг {e(result["z_rank"])})')
    return (f'<div style="font-size:12px;color:{MUTED};margin-top:6px;">'
            + " · ".join(bits) + "</div>")


def route_block(steps: list[Any], result: dict[str, Any]) -> str:
    """
    Маршрут и пакеты удержания. Шаги берутся из чек-листа: он и есть маршрут,
    второй его копии в отчёте быть не должно.

    Целевое состояние печатается номером гексаграммы и переходом по матрице.
    Ячейка целевой и рисковой гексаграмм считается точно: её задаёт то же
    правило, что и текущую (сумма отраслевых весов линий-Ян), а символы
    получаются инверсией известных линий. Догадки здесь нет —
    см. m3_verdict.transition.
    """
    if not steps:
        return (
            '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
            'page-break-after:avoid;'
            f'color:{MUTED};font-weight:normal;margin:20px 0 8px;">Маршрут</h4>'
            f'<p style="font-size:13px;margin:5px 0;font-family:{SERIF};">'
            "Подвижных линий нет — маршрут не строится. Флаг «ограничение "
            "стабильно».</p>"
        )

    items = ""
    for s in steps:
        line = getattr(s, "line", None)
        head = STEP_LABELS.get(getattr(s, "step_type", ""), getattr(s, "step_type", ""))
        if line:
            head += f" · линия {line}"
        budget = "" if not getattr(s, "needs_budget", False) else (
            f'<span style="color:{MUTED};"> · требует бюджета</span>')
        items += (
            f'<li style="margin:5px 0;font-size:13px;line-height:1.48;page-break-inside:avoid;">'
            f'<span style="font-size:11px;letter-spacing:0.06em;text-transform:uppercase;'
            f'color:{RED};display:block;margin-bottom:3px;">{e(head)}</span>'
            f"{e(getattr(s, 'step_text', ''))}{budget}</li>"
        )

    transition = ""
    for kind, lead in (("target", "Целевое состояние"),
                       ("risk", "Сценарий эрозии без закрепления")):
        to_hex = result.get(f"{kind}_hex")
        if to_hex is None:
            continue
        move = trajectory(result, kind)
        tail = f", {move['phrase']}" if move else ""
        transition += (
            f'<p style="font-size:12px;color:{MUTED};margin:5px 0;">'
            f'{lead}: № {e(result["current_hex"])} → № {e(to_hex)}{e(tail)}.</p>'
        )

    return (
        '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
            'page-break-after:avoid;'
        f'color:{MUTED};font-weight:normal;margin:9px 0 4px;">Маршрут и пакеты</h4>'
        f'<ul style="margin:8px 0;padding-left:20px;font-family:{SERIF};">{items}</ul>'
        + transition
    )


def verdict_block(verdict: dict[str, Any]) -> str:
    """
    Вердикт замыкает разбор. Считается по позиции в матрице GE/McKinsey и
    уточняется подвижностью линий — см. m3_verdict.
    """
    notes = " · ".join(verdict["notes"])
    return (
        f'<div style="border-top:1px solid {LINE};margin-top:11px;padding-top:9px;'
        f'font-size:14px;font-family:{SERIF};page-break-inside:avoid;">'
        f'<b style="font-weight:normal;color:{RED};">{e(verdict["verdict"])}.</b> '
        f'<span style="color:{MUTED};font-size:12.5px;">Зона матрицы: '
        f'{e(verdict["zone_ru"])} ({e(verdict["zone_en"])}). {e(notes)}.</span></div>'
    )


def object_card(
    result: dict[str, Any],
    narrative: list[dict[str, Any]],
    obj: Any,
    steps: list[Any],
    verdict: dict[str, Any],
) -> str:
    """Карточка направления. Порядок блоков — как в образце."""
    heading = (
        f'<h3 style="font-size:18px;font-weight:normal;margin:0 0 6px;color:{DARK};">'
        f'{e(result["position"])} · {e(result["name"])}</h3>'
    )

    body = ""
    tensions: list[dict[str, Any]] = []
    for block in narrative:
        if block["kind"] == "tension":
            tensions.append(block)
            continue
        body += (
            '<div style="page-break-inside:avoid;">'
            '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
            'page-break-after:avoid;'
            f'color:{MUTED};font-weight:normal;margin:9px 0 4px;">{e(block["title"])}</h4>'
            f'<p style="font-size:13.5px;margin:4px 0;line-height:1.48;'
            f'font-family:{SERIF};">{e(block["body"])}</p></div>'
        )
        if block.get("mistake"):
            body += banner("Типичная ошибка", e(block["mistake"]))

    if tensions:
        items = "".join(
            f'<li style="margin:4px 0;font-size:13px;line-height:1.48;page-break-inside:avoid;">'
            f'<b style="font-weight:normal;color:{RED};">{e(t["key"])}</b> '
            f'{e(t["body"])}</li>'
            for t in tensions
        )
        body += (
            '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
            'page-break-after:avoid;'
            f'color:{MUTED};font-weight:normal;margin:9px 0 4px;">Напряжения</h4>'
            f'<ul style="margin:8px 0;padding-left:20px;font-family:{SERIF};">{items}</ul>'
        )

    # Маршрут, оговорки и вердикт — итог карточки: «что делать» и «вывод».
    # Они склеены в один неделимый блок. Если карточка не помещается на
    # странице (у направления с тремя напряжениями текст длиннее полосы —
    # это содержание, а не оформление), разрыв падает перед этим блоком, и
    # на следующую страницу уезжает цельный кусок. Раньше уезжал один
    # вердикт в две строки и читался как начало нового направления.
    tail = route_block(steps, result)
    if result.get("flags"):
        text = "; ".join(FLAG_LABELS.get(f, f) for f in result["flags"])
        tail += banner("Оговорки по данным направления", e(text) + ".", warn=True)

    # Шапка держится вместе со строками линий: заголовок направления,
    # оторванный от своей таблицы, читается как чужой.
    head = (
        '<div style="page-break-inside:avoid;">'
        + heading
        + facts_line(result, obj)
        + hexagram_line(result)
        + lines_block(result)
        + cell_breakdown_block(result)
        + "</div>"
    )
    # Запрета разрыва на самой карточке нет. Замер показал: карточки в
    # контрольном портфеле — от 938 до 1122 пикселей при полосе набора в
    # 1010. Три из пяти выше полосы, и запрет их не спасает: браузер всё
    # равно обязан разорвать блок, который не помещается на странице, — но
    # сначала гонит его на новую, оставляя предыдущую полупустой.
    #
    # Поэтому разрыв разрешён, но управляем: неделимы шапка со строками
    # линий, каждый блок разбора, пункты списков и хвост «маршрут + вердикт».
    # Разрыв падает между ними.
    return (
        f'<section style="background:{PAPER};border:1px solid {LINE};'
        f'padding:13px 16px;margin:0 0 12px;font-family:{SERIF};">'
        + head
        + body
        + f'<div style="page-break-inside:avoid;">{tail}{verdict_block(verdict)}</div>'
        + "</section>"
    )


# ── 03 Портфельные ограничения ────────────────────────────────────────────────
def constraints_section(
    results: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    """
    Слой, которого нет ни в одной карточке направления: что повторяется и,
    значит, принадлежит компании. Всё считается из снимка — см. m3_portfolio.
    """
    intro = (
        f'<p style="font-size:13.5px;line-height:1.7;margin:10px 0;'
        f'font-family:{SERIF};">Раздел отвечает на вопрос, который нельзя '
        "задать, оценивая направления по отдельности: какая слабость "
        "повторяется и, значит, принадлежит компании, а не продукту.</p>"
    )

    yin_rows = [
        [f'Л{r["line"]}', e(r["factor"]), e(r["yin"]),
         signed(r["delta_line"]), e(r["reading"])]
        for r in yin_table(results)
    ]
    yin_html = table(
        [("Линия", False), ("Фактор", False), (f'Инь из {len(results)}', True),
         ("Дельта линии", True), ("Прочтение", False)],
        yin_rows,
    )

    blocks = ""
    for i, c in enumerate(constraints(results), 1):
        blocks += (
            f'<div style="background:{PAPER};border:1px solid {LINE};'
            f'padding:16px 20px;margin:16px 0;page-break-inside:avoid;">'
            f'<div style="font-size:11px;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:{RED};margin-bottom:7px;">'
            f'Ограничение {i} · {e(c["kind_title"])}</div>'
            f'<p style="font-size:13.5px;line-height:1.7;margin:0;'
            f'font-family:{SERIF};">{e(c["body"])}</p></div>'
        )
    if not blocks:
        blocks = (
            f'<p style="font-size:13px;color:{MUTED};line-height:1.7;'
            f'font-family:{SERIF};">Ни одна слабость не повторяется у '
            "большинства направлений: общего ограничения компании расчёт "
            "не фиксирует. Работать нужно по направлениям.</p>"
        )

    metrics_html = table(
        [("Показатель", False), ("Значение", True), ("Прочтение", False)],
        [[e(m["name"]), e(m["value"]), e(m["reading"])]
         for m in metric_readings(summary)],
    )

    tact = (
        f'<p style="font-size:12.5px;color:{MUTED};line-height:1.7;'
        f'margin:12px 0;font-family:{SERIF};">{e(tact_note(results, summary))}</p>'
    )

    # Ниже порога сравнения раздела нет: ограничение компании выводится
    # строгим большинством направлений, а большинство из одного направления
    # это само направление. Заслон нужен здесь отдельно от build_report:
    # PDF собирает раздел сам, вызывая m3_portfolio, а не читает payload.
    if (summary or {}).get("reduced"):
        return ""
    return (
        section_title("03", "Портфельные ограничения")
        + intro + yin_html + blocks + metrics_html + tact
    )


# ── 04 Решение о распределении ресурсов ───────────────────────────────────────
STEP_TYPE_LABELS = {
    "route": "маршрут",
    "hold": "удержание",
    "prep": "подготовительный",
    "decision": "решение",
}


def _rank_table(
    order: list[str],
    results_by_id: dict[str, dict[str, Any]],
    index_key: str,
    last_column: str,
    reason_for,
) -> str:
    rows = []
    for position, oid in enumerate(order, 1):
        r = results_by_id.get(oid)
        if r is None:
            continue
        rows.append([
            e(position),
            f'{e(r["position"])} · {e(r["name"])}',
            num(r[index_key], 3),
            e(reason_for(r)),
        ])
    return table(
        [("Ранг", False), ("Направление", False), (index_key[0].upper(), True),
         (last_column, False)],
        rows,
    )


def checklist_table(
    steps: list[Any],
    objects_by_id: dict[str, Any],
    generated_at: Any,
) -> str:
    """
    Чек-лист по волнам. Отметки печатаются в состоянии на момент скачивания,
    поэтому в подвале раздела стоит время формирования: PDF пересобирается на
    каждый запрос, и каждая копия — честный срез, а не вечная истина.

    Шаг типа «решение» уходит в отдельную группу «вне маршрута»: он не меняет
    ни одной линии и в правиле такта не участвует.
    """
    if not steps:
        return (f'<p style="font-size:13px;color:{MUTED};font-family:{SERIF};">'
                "Чек-лист пуст: расчёт не построил ни одного шага.</p>")

    waves: dict[int, list[Any]] = {}
    outside: list[Any] = []
    for s in steps:
        if getattr(s, "step_type", "") == "decision":
            outside.append(s)
        else:
            waves.setdefault(getattr(s, "wave", 1), []).append(s)

    groups: list[tuple[str, list[Any]]] = [
        (f"Волна {w}", waves[w]) for w in sorted(waves)
    ]
    if outside:
        groups.append(("Вне маршрута", outside))

    html = ""
    for title, group in groups:
        rows = []
        for s in group:
            obj = objects_by_id.get(str(getattr(s, "object_id", "") or ""))
            mark = "☑" if getattr(s, "done", False) else "☐"
            text = e(getattr(s, "step_text", ""))
            if getattr(s, "done", False):
                text = f'<span style="text-decoration:line-through;color:{MUTED};">{text}</span>'
            line = getattr(s, "line", None)
            rows.append([
                f"{mark} {text}",
                e(getattr(obj, "position", "—") if obj else "—"),
                f"Л{line}" if line else "—",
                e(STEP_TYPE_LABELS.get(getattr(s, "step_type", ""), "")),
                "да" if getattr(s, "needs_budget", False) else "нет",
            ])
        html += (
            f'<div style="font-size:12px;letter-spacing:0.06em;'
            f'text-transform:uppercase;color:{RED};margin:18px 0 4px;">{e(title)}</div>'
            + table(
                [("Шаг", False), ("Напр.", True), ("Линия", True),
                 ("Тип", False), ("Бюджет", True)],
                rows,
            )
        )

    stamp = ""
    if generated_at is not None:
        stamp = (f'<p style="font-size:11px;color:{MUTED};margin:8px 0 0;'
                 f'font-family:{SERIF};">Отметки приведены на '
                 f'{generated_at.strftime("%d.%m.%Y %H:%M")} — момент формирования '
                 "документа. Актуальное состояние всегда в личном кабинете.</p>")
    return html + stamp


def rank_comparison_block(results: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    """
    Ваш порядок против расчётного.

    Раньше расхождение существовало одной строкой в шапке и удерживало
    вердикты аллокации. Собственник не видел ни своего порядка, ни величины
    расхождения, ни направлений, на которых оно сидит, — при том что это
    самый содержательный результат диагностики.
    """
    cmp = rank_comparison(results, summary.get("owner_ranks"))
    if not cmp:
        return ""
    rows = [
        [
            f'{e(r["position"])} · {e(r["name"])}',
            e(r["owner_rank"]),
            e(r["v_rank"]),
            "—" if r["gap"] == 0 else e(f'{r["gap"]:+d}'),
        ]
        for r in cmp["rows"]
    ]
    return (
        '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
        'page-break-after:avoid;'
        f'color:{MUTED};font-weight:normal;margin:22px 0 6px;">'
        "Ваш порядок против расчётного</h4>"
        + table(
            [("Направление", False), ("Вы", True), ("Расчёт", True), ("Δ", True)],
            rows,
        )
        + f'<p style="font-size:13px;line-height:1.65;margin:8px 0 0;'
        f'font-family:{SERIF};color:{MUTED};">'
        f'{e(rank_comparison_reading(cmp, summary.get("spearman")))}</p>'
    )


def decision_section(
    results_by_id: dict[str, dict[str, Any]],
    objects_by_id: dict[str, Any],
    investment_order: list[str],
    execution_order: list[str],
    steps: list[Any],
    decision: Any | None,
    generated_at: Any = None,
    verdicts_held: bool = False,
    results: list[dict[str, Any]] | None = None,
    summary: dict[str, Any] | None = None,
) -> str:
    """
    Два списка отвечают на разные вопросы, и их расхождение — результат,
    а не дефект расчёта.
    """
    intro = (
        f'<p style="font-size:13.5px;line-height:1.7;margin:10px 0;'
        f'font-family:{SERIF};">Приоритет вложения отвечает на вопрос, куда '
        "осмысленно направить деньги на рост. Очередь исполнения — что нельзя "
        "потерять и что горит. Их расхождение не дефект: направление с крупной "
        "долей выручки защищают первым, а вкладывать в него не обязательно.</p>"
    )

    comparison = (rank_comparison_block(results, summary)
                  if results is not None and summary is not None else "")

    invest = (
        '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
            'page-break-after:avoid;'
        f'color:{MUTED};font-weight:normal;margin:22px 0 6px;">'
        "Приоритет вложения — где деньги дадут больший эффект</h4>"
        + _rank_table(investment_order, results_by_id, "v_index", "Вердикт",
                      lambda r: verdict_for(r)["verdict"])
    )

    execute = (
        '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
            'page-break-after:avoid;'
        f'color:{MUTED};font-weight:normal;margin:22px 0 6px;">'
        "Очередь исполнения — с чего начинать и что защищать</h4>"
        + _rank_table(
            execution_order, results_by_id, "z_index", "Почему здесь",
            lambda r: execution_reason(
                r,
                _f(getattr(objects_by_id.get(str(r["object_id"])), "revenue_share", None)),
            ),
        )
    )

    tradeoff = ""
    if investment_order and execution_order and investment_order[-1] == execution_order[0]:
        cow = results_by_id.get(execution_order[0])
        if cow:
            tradeoff = banner(
                "Ключевой trade-off",
                f'Направление «{e(cow["name"])}» последнее по приоритету вложения '
                "и первое по очереди исполнения. Это денежная корова: защищать "
                "в первую очередь, вкладывать в рост — в последнюю. Единый "
                "показатель это различие уничтожил бы.",
            )

    decided = ""
    if decision is not None:
        option = getattr(decision, "accepted_option", "")
        when = getattr(decision, "decided_at", None)
        head = ("Принята рекомендация метода" if option == "method"
                else "Принят собственный порядок")
        if when is not None:
            head += f" · решение от {when.strftime('%d.%m.%Y')}"
        waves = getattr(decision, "waves", None) or {}
        parts = []
        for w in sorted(waves, key=lambda k: int(k)):
            names = [
                f'{results_by_id[str(oid)]["position"]} · {results_by_id[str(oid)]["name"]}'
                for oid in waves[w] if str(oid) in results_by_id
            ]
            if names:
                parts.append(f"волна {w} — {'; '.join(names)}")
        decided = banner(head, e(". ".join(parts)) + "." if parts else "Состав волн не указан.")

        cost = getattr(decision, "cost_accepted", None)
        if cost:
            decided += banner(
                "Цена решения, принятая осознанно",
                e(cost) + " Отложенное направление со старым Инь теряет энергию "
                "перехода: назревшая слабость либо снимется сама, либо перестанет "
                "быть назревшей. Это предсказание, которое проверит следующая "
                "диагностика.",
            )

        triggers = getattr(decision, "review_triggers", None) or []
        if triggers:
            items = "".join(f"<li style=\"margin:5px 0;\">{e(t)}</li>" for t in triggers)
            decided += banner(
                "Условия пересмотра решения",
                f'<ul style="margin:6px 0 0;padding-left:20px;">{items}</ul>'
                '<p style="margin:8px 0 0;">Наступление любого означает пересобрать '
                "волны, а не продолжать по инерции.</p>",
            )
    else:
        decided = banner(
            "Решение по волнам не зафиксировано",
            "Все шаги приведены одним списком. Пока порядок не принят, повторная "
            "диагностика истолкует неизменившееся направление как невыполнение "
            "рекомендаций, а не как исполнение плана.",
            warn=True,
        )

    held = ""
    if verdicts_held:
        held = banner(
            "Вердикты удержаны",
            "Списки приведены как расчёт, но не как рекомендация: качество данных "
            "не позволяет опереться на них при распределении ресурса.",
            warn=True,
        )

    checklist = (
        '<h4 style="font-size:12px;letter-spacing:0.06em;text-transform:uppercase;'
            'page-break-after:avoid;'
        f'color:{MUTED};font-weight:normal;margin:24px 0 6px;">Чек-лист по волнам</h4>'
        + checklist_table(steps, objects_by_id, generated_at)
    )

    # Распределение ресурса между направлениями при одном направлении
    # не определено, а при двух вырождается в выбор из двух.
    if (summary or {}).get("reduced"):
        return ""
    return (
        section_title("04", "Решение о распределении ресурсов")
        # Сравнение идёт перед списками: оно объясняет, почему расчётный
        # порядок может выглядеть неожиданно, и читается до, а не после.
        + intro + comparison + invest + execute + tradeoff + held + decided + checklist
    )


# ── Оговорки по данным ────────────────────────────────────────────────────────
# Диапазоны порогов дублируют m3_config.DEFAULT_M3_CONFIG. Значения приходят
# параметром config, если вызывающий их передал; локальные — на случай вызова
# без конфига (тесты сборщика не поднимают файловую систему).
# Флаги, чей адрес — линия 1 и только она. VETO_UNKNOWN сюда не входит:
# там вето не срабатывало, символ никто не понижал, и печатать балл значило
# бы намекать на подмену, которой не было.
VETO_LINE_ONE = ("VETO_UNPROFITABLE", "VETO_MOBILITY_CONFLICT")

FLAG_RANGES = {
    "BORDERLINE_LINE": ("borderline_line", (2.30, 2.70)),
    "NEAR_OLD_YANG": ("near_old_yang", (3.30, 3.49)),
    "NEAR_OLD_YIN": ("near_old_yin", (1.51, 1.70)),
}


def flag_location(
    result: dict[str, Any],
    flag: str,
    config: dict[str, Any] | None = None,
) -> str:
    """
    Где именно сработал флаг. «Направление 4, линия 3 (2,67)» полезнее, чем
    «Направление 4»: оговорка без адреса не проверяема.

    Линии восстанавливаются по баллам и порогам — в снимке расчёта хранится
    факт срабатывания, но не место.
    """
    where = f'{result["position"]} · {result["name"]}'

    # Вето сидит на фиксированной линии, а не в диапазоне баллов, и именно
    # у него адрес нужнее всего: в блоке линий стоит Инь, а балл может быть
    # выше порога. Без числа оговорка не объясняет противоречие, которое
    # читатель уже увидел. В вебе номер не нужен — там ярлык печатается
    # в самой карточке, под таблицей линий.
    if flag in VETO_LINE_ONE:
        score = (result.get("scores") or {}).get("l1")
        return f"{where}: линия 1 ({num(score, 2)})" if score is not None else where

    entry = FLAG_RANGES.get(flag)
    if entry is None:
        return where
    key, default = entry
    low, high = (config or {}).get(key, default)
    hits = [
        f'линия {n} ({num((result.get("scores") or {}).get(f"l{n}"), 2)})'
        for n in range(1, 7)
        if (s := (result.get("scores") or {}).get(f"l{n}")) is not None
        and low <= s <= high
    ]
    return f"{where}: {', '.join(hits)}" if hits else where


def disclaimers_section(
    objects: list[dict[str, Any]],
    summary: dict[str, Any],
    disclaimers: list[str],
    flag_labels: dict[str, str],
    portfolio_flag_labels: dict[str, str],
    config: dict[str, Any] | None = None,
) -> str:
    """
    Оговорки таблицей, а не списком: у каждой должен быть адрес. Общие
    дисклеймеры метода идут отдельным блоком после неё.
    """
    rows = []
    for flag in summary.get("flags") or []:
        rows.append([e(flag), "Портфель целиком",
                     e(portfolio_flag_labels.get(flag, flag))])
    for item in objects:
        result = item.get("result", item)
        for flag in result.get("flags") or []:
            rows.append([
                e(flag),
                e(flag_location(result, flag, config)),
                e(flag_labels.get(flag, flag)),
            ])

    if rows:
        body = table([("Флаг", False), ("Где", False), ("Что означает", False)], rows)
    else:
        body = (f'<p style="font-size:13px;color:{MUTED};font-family:{SERIF};">'
                "Проверки полноты и согласованности пройдены без замечаний.</p>")

    general = "".join(
        f'<li style="margin:7px 0;font-size:13px;">{e(d)}</li>' for d in disclaimers
    )
    tail = (
        f'<p style="font-size:12.5px;color:{MUTED};line-height:1.7;margin:14px 0 0;'
        f'font-family:{SERIF};">Отчёт построен на вашей самооценке и введённых '
        "вами числовых показателях. Это инструмент поддержки решения, он не "
        "заменяет финансовый анализ. Оценки отражают восприятие одного "
        "респондента: диагностика с участием второго руководителя показала бы "
        "расхождения, которые сами по себе информативны.</p>"
    )
    return (
        section_title("", "Оговорки по данным") + body
        + (f'<ul style="margin:12px 0;padding-left:20px;font-family:{SERIF};">'
           f"{general}</ul>" if general else "")
        + tail
    )


# ── Сборка документа ──────────────────────────────────────────────────────────
def build_portfolio_report_html(
    report: dict[str, Any],
    steps: list[Any],
    decision: Any | None,
    company_name: str,
    generated_at: Any,
    industry_name: str | None = None,
    flag_labels: dict[str, str] | None = None,
    portfolio_flag_labels: dict[str, str] | None = None,
    market_by_object: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """
    Полный HTML отчёта. Порядок разделов — образца: шапка, 00, 01, 02, 03, 04,
    оговорки. Титульной страницы нет.

    Каждое направление получает свой лист: карточка с шестью линиями, разбором
    и маршрутом на половину листа не помещается, а разрыв посреди неё делает
    отчёт нечитаемым.
    """
    flag_labels = flag_labels or FLAG_LABELS
    # Колонка «Рынок» собирается из самого отчёта: правило (что считать
    # переопределением) живёт в расчёте, здесь только формулировка. Параметр
    # оставлен ради тестов, которые проверяют разметку таблицы отдельно.
    if market_by_object is None:
        market_by_object = {
            str(x["result"]["object_id"]): market_label(
                x["result"].get("market_overrides", 0))
            for x in report["objects"]
        }
    portfolio_flag_labels = portfolio_flag_labels or PORTFOLIO_FLAG_LABELS

    portfolio = report["portfolio"]
    summary = report["summary"]
    objects = report["objects"]
    results = [o["result"] for o in objects]
    results_by_id = {str(r["object_id"]): r for r in results}
    objects_by_id = {str(o.id): o for o in getattr(portfolio, "objects", [])}
    shares = {
        str(o.id): _f(getattr(o, "revenue_share", None))
        for o in getattr(portfolio, "objects", [])
    }
    steps_by_object: dict[str, list[Any]] = {}
    for s in steps:
        steps_by_object.setdefault(str(getattr(s, "object_id", "") or ""), []).append(s)

    sheets: list[str] = []

    sheets.append(page(
        report_header(company_name, portfolio, summary, industry_name)
        + data_status_banner(summary, portfolio_flag_labels)
        + objects_section(
            sorted(getattr(portfolio, "objects", []), key=lambda o: getattr(o, "position", 0)),
            market_by_object,
        ),
        first=True,
    ))

    sheets.append(page(
        map_section(results, shares, summary),
    ))

    # Карточки идут подряд одним листом, а не по листу на направление.
    # Прежнее правило стоило пяти страниц из семнадцати: содержимое карточки
    # — 837 пикселей при листе в 1123, но с зазорами секция вырастала до
    # 1082–1200 и утягивала второй лист с хвостом в 300–500 знаков.
    #
    # Разрыв теперь падает между блоками карточки: у неделимых кусков —
    # таблицы линий, баннеров, вердикта, шапки — стоит page-break-inside:avoid.
    # На самой карточке запрета нет и быть не может: она выше листа, и запрет
    # заставлял браузер переносить её целиком (первый лист оставался пустым,
    # а карточка всё равно ломалась).
    cards = "".join(
        (section_title("02", "Разбор направлений — в порядке приоритета вложения")
         if index == 0 else "")
        + object_card(
            item["result"], item["narrative"],
            objects_by_id.get(str(item["result"]["object_id"])),
            steps_by_object.get(str(item["result"]["object_id"]), []),
            verdict_for(item["result"]),
        )
        for index, item in enumerate(objects)
    )
    sheets.append(page(cards))

    sheets.append(page(
        constraints_section(results, summary),
    ))

    sheets.append(page(
        decision_section(
            results_by_id, objects_by_id,
            [str(x) for x in report["investment_order"]],
            [str(x) for x in report["execution_order"]],
            steps, decision, generated_at,
            verdicts_held=bool(summary.get("verdicts_held")),
            results=results, summary=summary,
        ),
    ))

    sheets.append(page(
        disclaimers_section(
            objects, summary, report.get("disclaimers") or [],
            flag_labels, portfolio_flag_labels, config,
        ),
    ))

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Матрица силы — {e(company_name)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: {SERIF};
    background: {BG};
    color: {DARK};
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
</style>
</head>
<body>
{"".join(sheets)}
</body>
</html>"""
