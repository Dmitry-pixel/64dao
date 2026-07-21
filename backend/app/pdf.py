"""
PDF-генерация через Playwright (Python).

Браузер запускается один раз (singleton) и переиспользуется.
Каждый запрос получает отдельный Page, который закрывается после генерации.
"""
import asyncio
import html as html_lib
from pathlib import Path
from typing import Any

from app.finance_pdf import finance_section_html
from app.method1_questions import BASE_QUESTIONS

from playwright.async_api import async_playwright, Browser, Playwright


# ── Singleton state ───────────────────────────────────────────────────────────
_pw: Playwright | None = None
_browser: Browser | None = None
_lock = asyncio.Lock()


async def _get_browser() -> Browser:
    """Возвращает существующий браузер или запускает новый."""
    global _pw, _browser

    async with _lock:
        if _browser and _browser.is_connected():
            return _browser

        # Закрываем старые ресурсы перед перезапуском
        try:
            if _browser:
                await _browser.close()
        except Exception:
            pass
        try:
            if _pw:
                await _pw.stop()
        except Exception:
            pass
        _browser = None
        _pw = None

        # Запускаем новый Playwright + Chromium
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                # --single-process убран: нестабилен в Docker, вызывает краши
            ],
        )

        return _browser


async def close_browser() -> None:
    """Вызывается при shutdown FastAPI."""
    global _pw, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _pw:
        await _pw.stop()
        _pw = None


# ── HTML escaping ─────────────────────────────────────────────────────────────
def e(text: str | None) -> str:
    """Экранирует HTML-спецсимволы в пользовательском контенте."""
    return html_lib.escape(text or "", quote=True)


# ── SVG hexagram (font-independent, matches HexagramSVG component) ────────────
def _hexagram_svg(combination: str, size: int = 110, color: str = "#1a2540") -> str:
    """
    Генерирует inline SVG гексаграммы по той же логике, что HexagramSVG во фронтенде.
    i=0 = нижняя линия (line 1), i=5 = верхняя (line 6).
    y = y_offset + (5 - i) * step → line 6 визуально сверху, line 1 снизу.
    Используем solid hex цвет (без rgba) для надёжного рендера в Playwright PDF.
    """
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
        y = y_off + (5 - i) * step  # i=0 = нижняя линия (line 1), i=5 = верхняя (line 6)
        if ch == "A":
            rects.append(
                f'<rect x="{x0:.2f}" y="{y:.2f}" width="{w:.2f}" '
                f'height="{line_h:.2f}" fill="{color}" rx="{rx:.2f}"/>'
            )
        else:
            half = (w - brk) / 2
            rects.append(
                f'<rect x="{x0:.2f}" y="{y:.2f}" width="{half:.2f}" '
                f'height="{line_h:.2f}" fill="{color}" rx="{rx:.2f}"/>'
            )
            rects.append(
                f'<rect x="{x0 + half + brk:.2f}" y="{y:.2f}" width="{half:.2f}" '
                f'height="{line_h:.2f}" fill="{color}" rx="{rx:.2f}"/>'
            )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;">'
        + "".join(rects)
        + "</svg>"
    )


# ── PDF generation ────────────────────────────────────────────────────────────
async def generate_pdf(html_content: str, output_path: str) -> str:
    """
    Рендерит HTML в PDF через Playwright.
    Возвращает путь к созданному файлу.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    browser = await _get_browser()
    page = await browser.new_page()

    try:
        await page.set_content(html_content, wait_until="domcontentloaded")
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
    finally:
        await page.close()

    return output_path


# ── Report data helpers ───────────────────────────────────────────────────────
def _score_bar(score: int) -> str:
    if not score:
        return (
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">'
            f'<span style="font-size:11px;color:rgba(26,37,64,0.4);font-style:italic;font-family:Arial,sans-serif;">Не оценено</span>'
            f'</div>'
        )
    bars = "".join(
        f'<span style="display:inline-block;width:22px;height:5px;border-radius:3px;'
        f'margin-right:3px;background:{"#1e3a8a" if n <= score else "#e5e7eb"};"></span>'
        for n in range(1, 6)
    )
    return (
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">'
        f'{bars}'
        f'<span style="font-size:11px;color:rgba(26,37,64,0.5);font-family:Arial,sans-serif;">{score}&nbsp;/&nbsp;5</span>'
        f'</div>'
    )


def _table_rows(rows: list[tuple[str, str | None]]) -> str:
    html = ""
    for i, (label, value) in enumerate(rows):
        bg = "background:#f9fafb;" if i % 2 == 0 else ""
        val_html = (e(value) if value
                    else '<em style="opacity:0.4;font-weight:400;color:rgba(26,37,64,0.4);">Не заполнено</em>')
        html += (
            f"<tr>"
            f'<td style="border:1px solid #d1d5db;padding:7px 10px;{bg}'
            f'font-size:12px;color:#6b7280;width:45%;vertical-align:top;">{e(label)}</td>'
            f'<td style="border:1px solid #d1d5db;padding:7px 10px;{bg}'
            f'font-size:12px;color:#111827;font-weight:500;vertical-align:top;">{val_html}</td>'
            f"</tr>"
        )
    return f'<table style="width:100%;border-collapse:collapse;margin-bottom:16px;"><tbody>{html}</tbody></table>'


SCENARIO_LABELS = {
    "innovation_strategy":   "Стратегия изменений",
    "innovation_type":       "Тип изменений",
    "value_discipline":      "Ценностная дисциплина",
    "leadership_principles": "Принципы лидерства",
    "growth_strategy":       "Стратегия роста",
    "focus":                 "Фокус",
}

# Ключи должны точно совпадать с b.title в BMC_BLOCKS на фронтенде (assessment/page.tsx)
BMC_KEYS = [
    "Ценностное предложение",
    "Отношения с клиентами",
    "Ключевые ресурсы",
    "Потоки доходов",
    "Ключевые партнёры",
    "Сегменты клиентов",
    "Ключевые активности",
    "Каналы",
    "Структура издержек",
]

BMC_HELP = {
    "Ценностное предложение": "Какую конкретную пользу клиент получает? Чем вы отличаетесь от альтернатив?",
    "Отношения с клиентами": "Какие связи компания выстраивает: персональные, самообслуживание, сообщество?",
    "Ключевые ресурсы": "Какие активы, люди, технологии и капитал необходимы для работы?",
    "Потоки доходов": "Как компания зарабатывает: продажи, подписка, лицензии, комиссии?",
    "Ключевые партнёры": "Кто помогает компании создавать и доставлять ценность? Какие альянсы и поставщики критичны?",
    "Сегменты клиентов": "Кто ваш клиент? Существует ли несколько сегментов с разными потребностями?",
    "Ключевые активности": "Что компания делает каждый день, чтобы создавать ценность для клиента?",
    "Каналы": "Через какие каналы клиенты узнают о продукте и получают его?",
    "Структура издержек": "Какие затраты ключевые? Постоянные или переменные? На чём фокус?",
}

HEX_SYMBOLS = [
    "䷀","䷁","䷂","䷃","䷄","䷅","䷆","䷇","䷈","䷉","䷊","䷋",
    "䷌","䷍","䷎","䷏","䷐","䷑","䷒","䷓","䷔","䷕","䷖","䷗",
    "䷘","䷙","䷚","䷛","䷜","䷝","䷞","䷟","䷠","䷡","䷢","䷣",
]

# ── Hexagram data ─────────────────────────────────────────────────────────────
# (number, name, combination)
from .hexagrams import HEXAGRAM_LIST as _HEXAGRAM_LIST

# combination → (number, name)
_HEXAGRAM_BY_COMBO: dict[str, tuple[int, str]] = {
    combo: (num, name) for num, name, combo in _HEXAGRAM_LIST
}

# number → name
_HEXAGRAM_BY_NUM: dict[int, str] = {
    num: name for num, name, _ in _HEXAGRAM_LIST
}

# number → combination
_COMBO_BY_NUM: dict[int, str] = {num: combo for num, name, combo in _HEXAGRAM_LIST}

# Таблица соответствия: номер текущей гексаграммы → номер целевой
_TARGET_HEXAGRAM: dict[int, int] = {
     1:  9,  2: 62,  3: 49,  4:  7,  5: 63,  6:  6,  7: 62,  8: 23,
     9: 37, 10: 25, 11: 36, 12:  9, 13: 37, 14: 26, 15: 11, 16: 54,
    17: 63, 18: 64, 19: 34, 20: 33, 21: 64, 22: 18, 23: 56, 24: 19,
    25: 37, 26: 22, 27:  4, 28: 44, 29:  3, 30: 22, 31: 43, 32: 44,
    33:  1, 34:  1, 35: 64, 36: 37, 37: 63, 38: 21, 39:  5, 40: 46,
    41: 27, 42:  3, 43:  5, 44: 33, 45: 58, 46: 57, 47: 44, 48: 47,
    49: 63, 50: 18, 51: 25, 52: 18, 53: 39, 54: 11, 55: 36, 56: 14,
    57: 44, 58:  5, 59: 44, 60: 43, 61: 42, 62: 33, 63: 17, 64: 40,
}


def get_target_hexagram_info(combination: str) -> tuple[int, str, str] | None:
    """
    По комбинации (напр. ABABBA) возвращает (номер, название, символ)
    целевой гексаграммы. Символ — Unicode U+4DC0 + num - 1.
    Возвращает None, если комбинация не найдена.
    """
    entry = _HEXAGRAM_BY_COMBO.get(combination)
    if not entry:
        return None
    current_num, _ = entry
    target_num = _TARGET_HEXAGRAM.get(current_num)
    if not target_num:
        return None
    target_name = _HEXAGRAM_BY_NUM.get(target_num, "")
    target_symbol = chr(0x4DC0 + target_num - 1)
    return target_num, target_name, target_symbol


_ASSUMPTION_FIELDS = [
    ("assm_planning",    "Планирование"),
    ("assm_growth",      "Рост и производительность"),
    ("assm_advertising", "Реклама"),
    ("assm_feedback",    "Обратная связь"),
    ("assm_risk",        "Риск"),
    ("assm_product",     "Выбор продукта"),
    ("assm_service",     "Сервис"),
    ("assm_startup",     "Стартап"),
    ("assm_investment",  "Инвестиции и финансы"),
    ("assm_contracts",   "Договора и соглашения"),
    ("assm_sync",        "Синхронизация"),
    ("assm_creative",    "Творческий вклад"),
    ("assm_interaction", "Взаимодействие"),
    ("assm_resources",   "Достаточность ресурсов"),
    ("assm_research",    "Исследование и разработка"),
    ("assm_trade",       "Международная торговля"),
    ("assm_failures",    "Источники неудач"),
    ("assm_success",     "Источники удачи"),
]

def _assumptions_block(strategy: Any) -> str:
    """HTML-блок 'Предположения, лежащие в основе принятия решения. Связи с будущим'."""
    if not strategy:
        return ""
    items = ""
    for field, label in _ASSUMPTION_FIELDS:
        val = getattr(strategy, field, None)
        items += (
            '<div style="margin-bottom:16px;">'
            '<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;'
            'text-transform:uppercase;color:#c0392b;font-family:Arial,sans-serif;margin-bottom:4px;">'
            + e(label) +
            '</div>'
            '<p style="font-size:13px;color:rgba(26,37,64,0.7);line-height:1.7;'
            'margin:0;font-family:Arial,sans-serif;">'
            + (e(val) if val else '<em style="opacity:0.4;">Не заполнено</em>') +
            '</p>'
            '</div>'
        )
    return (
        '<h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:24px 0 12px;">'
        'Предположения, лежащие в основе принятия решения. Связи с будущим'
        '</h2>'
        '<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:24px;'
        'background:rgba(255,255,255,0.4);">'
        + items +
        '</div>'
    )


def _transition_block(strategy: Any, target_hex_info: tuple | None) -> str:
    """Раздел 03 «Целевой сценарий»: только описание перехода."""
    if not strategy:
        return ""
    desc_html = (e(strategy.transition_description)
                 if strategy.transition_description
                 else '<em style="opacity:0.4;">Описание перехода будет добавлено при публикации стратегии.</em>')
    return (
        '<div style="padding:16px 20px;'
        'border:1px solid rgba(192,57,43,0.2);border-radius:6px;'
        'background:rgba(192,57,43,0.04);">'
        '<div style="font-size:10px;color:#c0392b;letter-spacing:2px;'
        'text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:12px;">'
        '<span style="margin-right:8px;">03</span>Целевой сценарий'
        '</div>'
        '<div style="font-size:10px;color:rgba(26,37,64,0.45);text-transform:uppercase;'
        'letter-spacing:1px;font-family:Arial,sans-serif;margin-bottom:6px;">Описание перехода</div>'
        '<p style="font-size:12px;color:rgba(26,37,64,0.65);'
        'font-family:Arial,sans-serif;line-height:1.7;margin:0;">'
        + desc_html +
        '</p>'
        '</div>'
    )


_LC_LABELS = [
    ("lc_profit",    "Формирование прибыли"),
    ("lc_strategy",  "Рыночная стратегия"),
    ("lc_decisions", "Принятие решений"),
    ("lc_consumer",  "Тип потребителя"),
    ("lc_market",    "Статус рынка"),
    ("lc_value",     "Тип ценности"),
]


def _lifecycle_blocks(strategy: Any, combination: str, with_lc: bool = True) -> str:
    """6 блоков жизненного цикла для PDF — по одному на каждый вопрос."""
    header = ""
    if strategy and strategy.stratagema_title:
        header = f'<div style="display:block;padding:12px 16px;border-radius:6px;font-size:13px;font-family:Arial,sans-serif;line-height:1.6;background:rgba(30,58,138,0.08);border:1px solid rgba(30,58,138,0.2);color:#1e3a8a;margin-bottom:12px;">{e(strategy.stratagema_title)}</div>'
    if strategy and strategy.title:
        header += f'<h3 style="font-size:16px;font-weight:500;color:#1a2540;margin-bottom:16px;font-family:Arial,sans-serif;">{e(strategy.title)}</h3>'

    blocks_html = ""
    for i, (field, label) in enumerate(_LC_LABELS):
        value = (getattr(strategy, field, None) or "") if strategy else ""
        blocks_html += f"""
<div style="background:rgba(255,255,255,0.5);border:1px solid rgba(26,37,64,0.1);border-radius:6px;padding:12px 14px;">
  <div style="margin-bottom:6px;">
    <span style="font-size:9px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;color:rgba(26,37,64,0.45);font-weight:600;">{e(label)}</span>
  </div>
  <p style="font-size:12px;color:#1a2540;line-height:1.6;margin:0;font-family:Arial,sans-serif;">{e(value) if value else '<em style="opacity:0.35;">Не заполнено</em>'}</p>
</div>"""

    grid_html = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">{blocks_html}</div>'
        if with_lc else ""
    )
    return f"""<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:20px 24px;background:rgba(255,255,255,0.4);">
{header}
{grid_html}
</div>"""




def _hex_diagram_html(combination: str, scenario: dict | None) -> str:
    """Раздел 01: гексаграмма по центру, ответы слева, параметры стратагемы справа."""
    sc = scenario or {}
    labels = list(SCENARIO_LABELS.items())

    def line_html(ch: str) -> str:
        if ch == "A":
            return '<div style="width:110px;height:11px;background:#1a2540;border-radius:2px;"></div>'
        half = '<div style="width:46px;height:11px;background:#1a2540;border-radius:2px;"></div>'
        return ('<div style="width:110px;height:11px;display:flex;'
                'justify-content:space-between;">' + half + half + '</div>')

    k = ('font-size:8px;letter-spacing:1px;text-transform:uppercase;color:#c0392b;'
         'font-weight:700;font-family:Arial,sans-serif;margin-bottom:2px;')
    qs = ('font-size:9.5px;line-height:1.35;color:rgba(26,37,64,0.5);'
          'font-family:Arial,sans-serif;margin-bottom:2px;')
    v = 'font-size:11px;line-height:1.4;color:#1a2540;font-family:Arial,sans-serif;'
    dash = 'flex:0 0 34px;height:0;border-top:1.5px dashed rgba(26,37,64,0.25);'
    empty = '<em style="opacity:0.4;">Не заполнено</em>'

    rows = ""
    for j, i in enumerate([5, 4, 3, 2, 1, 0]):
        ch = combination[i] if i < len(combination) else ""
        bq = BASE_QUESTIONS[i]
        ans = e(bq["a"]) if ch == "A" else (e(bq["b"]) if ch == "B" else "—")
        key, label = labels[j]
        pval = sc.get(key) or None
        rows += (
            '<div style="display:flex;align-items:center;min-height:74px;page-break-inside:avoid;">'
            '<div style="flex:1 1 0;min-width:0;text-align:right;padding-right:10px;">'
            f'<div style="{k}">Линия {i + 1} · Вопрос {i + 1}</div>'
            f'<div style="{qs}">{e(bq["q"])}</div>'
            f'<div style="{v}">{ans}</div></div>'
            f'<div style="{dash}"></div>'
            f'<div style="flex:0 0 110px;display:flex;justify-content:center;">{line_html(ch)}</div>'
            f'<div style="{dash}"></div>'
            '<div style="flex:1 1 0;min-width:0;padding-left:10px;">'
            f'<div style="{k}">Линия {i + 1} · {e(label)}</div>'
            f'<div style="{v}">{e(pval) if pval else empty}</div></div>'
            '</div>'
        )

    hdr = ('font-size:9px;letter-spacing:1.4px;text-transform:uppercase;'
           'color:rgba(26,37,64,0.45);font-weight:700;font-family:Arial,sans-serif;')
    return (
        '<div style="margin-top:6px;">'
        '<div style="display:flex;padding-bottom:8px;margin-bottom:6px;'
        'border-bottom:1px solid rgba(26,37,64,0.1);">'
        f'<div style="flex:1 1 0;text-align:right;padding-right:44px;{hdr}">Ответы диагностики</div>'
        '<div style="flex:0 0 110px;"></div>'
        f'<div style="flex:1 1 0;padding-left:44px;{hdr}">Параметры стратагемы</div>'
        '</div>'
        + rows +
        '<div style="font-size:9px;color:rgba(26,37,64,0.35);text-align:center;'
        'margin-top:8px;font-family:Arial,sans-serif;">линия 1 — нижняя</div>'
        '</div>'
    )




_LC_CHART_Y = [192, 98, 52, 138, 78]


def _catmull(pts) -> str:
    d = "M %.1f %.1f" % pts[0]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[i + 1]
        d += " C %.1f %.1f, %.1f %.1f, %.1f %.1f" % (
            p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
            p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6,
            p2[0], p2[1],
        )
    return d


def _lifecycle_chart_html(stages, index) -> str:
    """График стадии жизненного цикла с отметкой текущей стадии."""
    if not stages or len(stages) < 2:
        return ""
    x0, x1 = 80.0, 740.0
    n = len(stages)
    pts = [
        (x0 + (x1 - x0) * i / (n - 1),
         float(_LC_CHART_Y[i] if i < len(_LC_CHART_Y) else 120))
        for i in range(n)
    ]
    cur = -1
    for i, s in enumerate(stages):
        if s.get("sort_order") == index:
            cur = i
    parts = []
    for i, (x, y) in enumerate(pts):
        on = i == cur
        if on:
            parts.append(
                f'<line x1="{x:.1f}" y1="{y + 11:.1f}" x2="{x:.1f}" y2="206" '
                f'stroke="#c0392b" stroke-width="1.5" stroke-dasharray="4 4"/>'
            )
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{9 if on else 5}" '
            f'fill="{"#c0392b" if on else "#fdfcf9"}" '
            f'stroke="{"#c0392b" if on else "#1a2540"}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="228" text-anchor="middle" font-family="Arial,sans-serif" '
            f'font-size="{14.5 if on else 12.5}" font-weight="{700 if on else 400}" '
            f'fill="{"#c0392b" if on else "rgba(26,37,64,0.5)"}">{e(stages[i].get("name"))}</text>'
        )
    stage = stages[cur] if cur >= 0 else None
    title = e(stage.get("name")) if stage else '<em style="opacity:0.4;">Не определена</em>'
    desc = e(stage.get("description")) if stage and stage.get("description") else ""
    desc_html = (
        f'<p style="font-size:12px;color:rgba(26,37,64,0.7);line-height:1.6;'
        f'margin:8px 0 0;font-family:Arial,sans-serif;">{desc}</p>'
    ) if desc else ""
    return (
        '<div style="margin:14px 0 18px;page-break-inside:avoid;">'
        '<div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#c0392b;'
        'font-weight:700;font-family:Arial,sans-serif;margin-bottom:6px;">Стадия жизненного цикла</div>'
        f'<div style="font-size:17px;color:#1a2540;font-family:Georgia,serif;">{title}</div>'
        '<svg viewBox="0 0 820 252" width="100%" xmlns="http://www.w3.org/2000/svg" '
        'style="display:block;margin-top:10px;">'
        '<line x1="40" y1="206" x2="780" y2="206" stroke="rgba(26,37,64,0.2)" stroke-width="1"/>'
        f'<path d="{_catmull(pts)}" fill="none" stroke="#1e3a8a" stroke-width="2.5"/>'
        + "".join(parts) +
        '</svg>'
        + desc_html +
        '</div>'
    )


def _finance_description_html(finance_strategy: Any | None, lifecycle_stages=None) -> str:
    """Описание из strategies по фин-комбинации: стадия ЖЦ, ЖЦ-блоки, сценарий,
    маркетинг, управление, предположения. Пусто, если стратегии нет."""
    if not finance_strategy:
        return ""
    fs = finance_strategy

    def txt_block(title: str, val: str | None) -> str:
        body = e(val) if val else '<em style="opacity:0.4;">Не заполнено</em>'
        return (f'<h2 style="font-size:16px;font-weight:400;color:#1a2540;margin:18px 0 10px;">{e(title)}</h2>'
                '<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:16px 20px;'
                'background:rgba(255,255,255,0.4);page-break-inside:avoid;">'
                f'<p style="font-size:13px;color:rgba(26,37,64,0.72);line-height:1.7;margin:0;font-family:Arial,sans-serif;">{body}</p></div>')

    stage = getattr(fs, "lifecycle_stage", None)
    stage_badge = (f'<div style="display:inline-block;padding:4px 14px;border-radius:4px;font-size:13px;'
                   f'font-family:Arial,sans-serif;background:rgba(192,57,43,0.08);border:1px solid rgba(192,57,43,0.2);'
                   f'color:#c0392b;margin:6px 0 14px;">Стадия жизненного цикла: {e(stage)}</div>') if stage else ""

    combo = getattr(fs, "combination", "") or ""
    parts = [
        '<h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:22px 0 12px;">'
        '<span style="font-size:11px;color:#c0392b;margin-right:8px;">Описание</span>Стратегический профиль финансовой гексаграммы</h2>',
        stage_badge,
        _lifecycle_chart_html(lifecycle_stages, getattr(fs, "lifecycle_stage_index", None)),
        _lifecycle_blocks(fs, combo, with_lc=False),
        txt_block("Сценарий развития", getattr(fs, "scenario_text", None)),
        txt_block("Маркетинг", getattr(fs, "marketing_text", None)),
        txt_block("Управление", getattr(fs, "management_text", None)),
        _assumptions_block(fs),
    ]
    return "".join(parts)


def build_report_html(
    company_name: str,
    user_name: str,
    date_str: str,
    combination: str,
    strategy: Any | None,
    method2_data: dict[str, Any] | None,
    finance_result: dict | None = None,
    finance_interpretation: dict | None = None,
    finance_strategy: Any | None = None,
    lifecycle_stages=None,
    is_method2: bool | None = None,
) -> str:
    """Собирает полный HTML отчёта (все данные уже экранированы через e()).

    method2_data:
      None  → Метод 1 (нет данных BMC)
      {}    → Метод 2, данные пустые (legacy/пустая анкета)
      {...} → Метод 2, данные заполнены
    """

    # Метод определяется вызывающей стороной (build_html_for_assessment).
    # Fallback для прямых вызовов: пустой method2_data = НЕ Метод 2, иначе
    # диагностика Метода 1 с комбинацией AAAAAA теряет разделы 01 и финблок.
    if is_method2 is None:
        is_method2 = bool(method2_data) and (not combination or combination == 'AAAAAA')

    # Нормализуем для рендеринга
    method2_data = method2_data or {}

    hex_grid = "".join(
        f'<div style="display:flex;align-items:center;justify-content:center;'
        f'font-size:32px;color:#1a2540;">{s}</div>'
        for s in HEX_SYMBOLS
    )

    # Целевая гексаграмма — вычисляем заранее, чтобы не усложнять f-строки
    target_hex_info = get_target_hexagram_info(combination) if combination else None

    # Сценарий — всегда все строки, пустые с заглушкой
    sc = (strategy.scenario or {}) if strategy else {}
    sc_rows = [(lbl, sc.get(k) or None) for k, lbl in SCENARIO_LABELS.items()]

    # BMC: сетка оценок (только баллы, без текста)
    bmc_score_grid = ""
    # BMC: комментарии (только тексты, без баллов)
    bmc_comments = ""
    for label in BMC_KEYS:
        block = method2_data.get(label, {})
        score = max(0, min(5, int(block.get("score") or 0))) if block else 0
        text  = str(block.get("text") or "") if block else ""
        # Карточка оценки
        bmc_score_grid += f"""
        <div style="border:1px solid rgba(26,37,64,0.1);border-radius:5px;
                    padding:12px;background:rgba(255,255,255,0.5);">
          <div style="font-size:11px;font-weight:600;color:#1a2540;
                      font-family:Arial,sans-serif;margin-bottom:8px;">{e(label)}</div>
          {_score_bar(score)}
        </div>"""
        # Блок комментария
        help_text = BMC_HELP.get(label, "")
        bmc_comments += f"""
        <div style="border:1px solid rgba(26,37,64,0.1);border-radius:5px;
                    padding:14px 16px;background:rgba(255,255,255,0.5);">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="font-size:11px;font-weight:600;color:#1a2540;
                        font-family:Arial,sans-serif;">{e(label)}</div>
            <div style="flex-shrink:0;">{_score_bar(score)}</div>
          </div>
          {f'<div style="font-size:11px;color:rgba(26,37,64,0.5);line-height:1.5;font-family:Arial,sans-serif;margin-bottom:8px;">{e(help_text)}</div>' if help_text else ''}
          <div style="font-size:12px;color:rgba(26,37,64,0.7);
                      line-height:1.6;font-family:Arial,sans-serif;">
            {e(text) if text else '<em style="opacity:0.4;">Не заполнено</em>'}
          </div>
        </div>"""

    # Блок "Предположения" — строим до page2, чтобы вставить простой переменной
    assumptions_html = _assumptions_block(strategy)
    # Блок "Целевой сценарий" — строим до page2, чтобы вставить простой переменной
    transition_html = _transition_block(strategy, target_hex_info)

    # ── Обложка ──────────────────────────────────────────────────────────────
    if is_method2:
        cover_label = "Отчёт по бизнес-модели"
        cover_title = f"Бизнес-модель<br>{e(company_name)}"
        cover_combo = ""
    else:
        cover_label = "Отчёт по стратегической диагностике"
        cover_title = "Стратегический<br>профиль компании"
        hex_entry = _HEXAGRAM_BY_COMBO.get(combination)
        if hex_entry and combination:
            hex_num, hex_name_str = hex_entry
            # Используем тот же Unicode-символ, что и в HTML-отчёте браузера
            hex_char = chr(0x4DC0 + hex_num - 1)
            cover_combo = (
                f'<div style="margin-top:28px;">'
                f'<div style="font-size:100px;line-height:1;color:#1a2540;margin-bottom:10px;'
                f'font-family:Georgia,\'Times New Roman\',serif;">{hex_char}</div>'
                f'<div style="font-size:12px;color:rgba(26,37,64,0.5);font-family:Arial,sans-serif;'
                f'letter-spacing:2px;font-weight:600;">{e(hex_name_str)}</div>'
                f'</div>'
            )
        else:
            cover_combo = ""
        


    # ── Страница 1 (только для Method 1): Жизненный цикл + Таблица ──────
    page1 = ""
    if not is_method2:
        lifecycle_badge_html = (
            f'<div style="display:inline-block;padding:4px 14px;border-radius:4px;font-size:13px;'
            f'font-family:Arial,sans-serif;background:rgba(192,57,43,0.08);'
            f'border:1px solid rgba(192,57,43,0.2);color:#c0392b;margin-bottom:20px;">'
            f'{e(strategy.lifecycle_stage or "")}</div>'
        ) if strategy and strategy.lifecycle_stage else ""

        current_state_html = f"""
<div style="background:rgba(26,37,64,0.03);border-radius:6px;padding:14px 18px;margin-bottom:18px;">
  <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#c0392b;font-weight:600;font-family:Arial,sans-serif;">Стратагема</div>
  <div style="font-size:17px;color:#1a2540;margin-top:6px;font-family:Georgia,serif;">{e(strategy.stratagema_title) if strategy and strategy.stratagema_title else '<em style="opacity:0.4;font-size:14px;">Не заполнено</em>'}</div>
</div>"""

        page1 = f"""
<div style="padding:40px 50px;page-break-after:always;background:#e8e4db;min-height:297mm;">
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:28px;">
    <span style="font-size:11px;font-weight:700;color:#c0392b;font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>
    <span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">
      {e(company_name)} · стр. 1
    </span>
  </div>
  <h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:0 0 10px;"><span style="font-size:11px;color:#c0392b;margin-right:8px;">01</span>Текущее состояние</h2>
  {current_state_html}
  {_hex_diagram_html(combination, sc)}
  <div style="margin-top:32px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
              display:flex;justify-content:space-between;font-family:Arial,sans-serif;
              font-size:10px;color:rgba(26,37,64,0.3);">
    <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
  </div>
</div>"""

    # ── Страница 2: Сценарий + Маркетинг + Управление + Предположения + Переход ──
    page2 = ""
    if False:  # база облегчена: сценарий/маркетинг/управление/предположения → раздел «Финансовая функция»
        def _text_block(text: str | None) -> str:
            val = (e(text) if text else '<em style="opacity:0.4;">Не заполнено</em>')
            return (
                '<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:20px;'
                'background:rgba(255,255,255,0.4);margin-bottom:20px;">'
                f'<p style="font-size:13px;color:rgba(26,37,64,0.7);line-height:1.7;margin:0;font-family:Arial,sans-serif;">{val}</p>'
                '</div>'
            )

        page2 = f"""
        <div style="padding:40px 50px;page-break-after:always;background:#e8e4db;min-height:297mm;">
          <div style="display:flex;justify-content:space-between;align-items:center;
                      padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:28px;">
            <span style="font-size:11px;font-weight:700;color:#c0392b;font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>
            <span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">
              {e(company_name)} · стр. 2
            </span>
          </div>
          <h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:0 0 12px;"><span style="font-size:11px;color:#c0392b;margin-right:8px;">02</span>Сценарий развития</h2>
          {_text_block(strategy.scenario_text)}
          <h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:0 0 12px;">Маркетинг</h2>
          {_text_block(strategy.marketing_text)}
          <h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:0 0 12px;">Управление</h2>
          {_text_block(strategy.management_text)}
          {assumptions_html}
          {transition_html}
          <div style="margin-top:32px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
                      display:flex;justify-content:space-between;font-family:Arial,sans-serif;
                      font-size:10px;color:rgba(26,37,64,0.3);">
            <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
          </div>
        </div>"""

    # Номер страницы BMC
    if is_method2:
        bmc_page_num = 1
    elif strategy:
        bmc_page_num = 3
    else:
        bmc_page_num = 2

    # BMC показываем только если есть данные
    bmc_section = ""
    if method2_data:
        bmc_section = f"""
<!-- СТРАНИЦА {bmc_page_num}: КАНВА БИЗНЕС-МОДЕЛИ — ОЦЕНКИ -->
<div style="padding:40px 50px;background:#e8e4db;page-break-after:always;">
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:28px;">
    <span style="font-size:11px;font-weight:700;color:#c0392b;font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>
    <span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">
      {e(company_name)} · стр. {bmc_page_num}
    </span>
  </div>
  <div style="font-size:10px;color:rgba(26,37,64,0.3);letter-spacing:2px;
              text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:6px;">
    {"бизнес-модель" if is_method2 else "метод 2 — оценка бизнес-модели"}
  </div>
  <h1 style="font-size:28px;font-weight:400;color:#1a2540;margin-bottom:8px;">Оценка блоков бизнес-модели</h1>
  <p style="font-size:13px;color:rgba(26,37,64,0.55);line-height:1.7;
            font-family:Arial,sans-serif;margin-bottom:24px;">
    Текущее состояние каждого блока по шкале 1–5.
  </p>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:32px;">
    {bmc_score_grid}
  </div>
  <div style="margin-top:auto;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
              display:flex;justify-content:space-between;font-family:Arial,sans-serif;
              font-size:10px;color:rgba(26,37,64,0.3);">
    <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
  </div>
</div>

<!-- СТРАНИЦА {bmc_page_num + 1}: КОММЕНТАРИИ -->
<div style="padding:40px 50px;background:#e8e4db;">
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:28px;">
    <span style="font-size:11px;font-weight:700;color:#c0392b;font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>
    <span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">
      {e(company_name)} · стр. {bmc_page_num + 1}
    </span>
  </div>
  <div style="font-size:10px;color:rgba(26,37,64,0.3);letter-spacing:2px;
              text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:6px;">комментарии</div>
  <h1 style="font-size:28px;font-weight:400;color:#1a2540;margin-bottom:24px;">Детальный анализ блоков</h1>
  <div style="display:grid;grid-template-columns:1fr;gap:12px;">
    {bmc_comments}
  </div>
  <div style="margin-top:32px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
              display:flex;justify-content:space-between;font-family:Arial,sans-serif;
              font-size:10px;color:rgba(26,37,64,0.3);">
    <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
  </div>
</div>"""

    # ── Финансовая функция (Метод 1, только при наличии результата скоринга) ──
    finance_section = ""
    if (not is_method2) and finance_result and finance_interpretation:
        finance_section = finance_section_html(
            finance_result, finance_interpretation, company_name,
            _finance_description_html(finance_strategy, lifecycle_stages),
        )

    transition_page = (
        f'<div style="padding:40px 50px;background:#e8e4db;">{transition_html}</div>'
        if transition_html else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Отчёт 64DAO — {e(company_name)}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{
    font-family: 'Georgia','Times New Roman',serif;
    background: #e8e4db;
    color: #1a2540;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  @media print {{
    .page-break {{ page-break-after: always; }}
  }}
</style>
</head>
<body>

<!-- ОБЛОЖКА -->
<div style="width:210mm;min-height:297mm;background:#e8e4db;position:relative;
            page-break-after:always;">
  <div style="position:absolute;right:0;top:0;width:55%;height:100%;
              display:grid;grid-template-columns:repeat(6,1fr);gap:2px;opacity:0.08;overflow:hidden;">
    {hex_grid}
  </div>
  <div style="position:relative;z-index:2;padding:60px 50px;
              display:flex;flex-direction:column;min-height:297mm;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:auto;">
      <div style="width:44px;height:44px;border:2px solid #c0392b;border-radius:4px;
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-size:10px;font-weight:700;color:#c0392b;line-height:1.1;font-family:Arial,sans-serif;">
        <span>64</span><span style="letter-spacing:2px">DAO</span>
      </div>
      <span style="font-size:12px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;letter-spacing:1px;">
        Стратегическая диагностика
      </span>
    </div>
    <div style="max-width:480px;padding-top:60px;">
      <div style="font-size:10px;color:rgba(26,37,64,0.3);letter-spacing:2px;
                  text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:16px;">
        {cover_label}
      </div>
      <h1 style="font-size:40px;font-weight:400;line-height:1.1;color:#1a2540;margin-bottom:20px;">
        {cover_title}
      </h1>
      {"" if is_method2 else f'<div style="font-size:20px;color:rgba(26,37,64,0.7);margin-bottom:8px;">{e(company_name)}</div>'}
      <div style="font-size:13px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;margin-bottom:0;">{date_str}</div>
      {cover_combo}
    </div>
  </div>
</div>

{page1}

{page2}

{finance_section}

{transition_page}

{bmc_section}

</body>
</html>"""
