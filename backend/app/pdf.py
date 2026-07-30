"""
PDF-генерация через Playwright (Python).

Браузер запускается один раз (singleton) и переиспользуется.
Каждый запрос получает отдельный Page, который закрывается после генерации.
"""
import asyncio
import html as html_lib
from pathlib import Path
from typing import Any

from app.finance_pdf import finance_section_html, contour_section_html, summary_card_html
from app.method1_questions import BASE_QUESTIONS, LC_LABELS  # дефолты

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
from app.hexagrams import _HEXAGRAM_BY_COMBO, _HEXAGRAM_BY_NUM, _TARGET_HEXAGRAM, get_target_hexagram_info
from app.transition_block import transition_block
# Подписи блоков ЖЦ — из единого источника вопросов, без локальной копии.
_LC_LABELS = LC_LABELS

def _lifecycle_blocks(strategy: Any, combination: str, with_lc: bool = True,
                      questions: list[dict] | None = None) -> str:
    """6 блоков жизненного цикла для PDF — по одному на каждый вопрос."""
    header = ""
    if strategy and strategy.stratagema_title:
        header = f'<div style="display:block;padding:12px 16px;border-radius:6px;font-size:13px;font-family:Arial,sans-serif;line-height:1.6;background:rgba(30,58,138,0.08);border:1px solid rgba(30,58,138,0.2);color:#1e3a8a;margin-bottom:12px;">{e(strategy.stratagema_title)}</div>'
    if strategy and strategy.title:
        header += f'<h3 style="font-size:16px;font-weight:500;color:#1a2540;margin-bottom:16px;font-family:Arial,sans-serif;">{e(strategy.title)}</h3>'

    # Значения блоков — авторский контент из карточки стратагемы, а не
    # производная от комбинации: их правит методолог, код их не пересчитывает.
    labels = ([(q["lc_key"], q["label"]) for q in questions] if questions else _LC_LABELS)

    blocks_html = ""
    for i, (field, label) in enumerate(labels):
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
    """Описание из strategies по фин-комбинации: ЖЦ-блоки и сценарий.
    Пусто, если стратегии нет. Стадия ЖЦ, маркетинг, управление и
    предположения вынесены на страницы гексаграмм."""
    if not finance_strategy:
        return ""
    fs = finance_strategy

    def txt_block(title: str, val: str | None) -> str:
        body = e(val) if val else '<em style="opacity:0.4;">Не заполнено</em>'
        return (f'<h2 style="font-size:16px;font-weight:400;color:#1a2540;margin:18px 0 10px;">{e(title)}</h2>'
                '<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:16px 20px;'
                'background:rgba(255,255,255,0.4);page-break-inside:avoid;">'
                f'<p style="font-size:13px;color:rgba(26,37,64,0.72);line-height:1.7;margin:0;font-family:Arial,sans-serif;">{body}</p></div>')

    # Стадия ЖЦ и график намеренно НЕ выводятся здесь: жизненный цикл --
    # свойство компании (контур-ограничение), а не финансовой функции.
    combo = getattr(fs, "combination", "") or ""
    parts = [
        '<h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:22px 0 12px;">'
        '<span style="font-size:11px;color:#c0392b;margin-right:8px;">Описание</span>Стратегический профиль финансовой гексаграммы</h2>',
        _lifecycle_blocks(fs, combo, with_lc=False),
        txt_block("Сценарий развития", getattr(fs, "scenario_text", None)),
    ]
    return "".join(parts)


_CL_FLAG_LABELS = {
    "CONSTRAINT_TIED": "Несколько контуров делят минимальную зрелость — ограничение неустойчиво, стадия не фиксируется.",
    "CONSTRAINT_STABLE": "Контур-ограничение без подвижных линий: внутреннего запроса на изменение нет, работа начинается со стратегической сессии.",
    "GAP_NOT_SIGNIFICANT": "Отрыв ограничения от остальных контуров незначим — точка условна, опирайтесь на вектор.",
    "STAGE_UNKNOWN": "Для части гексаграмм стадия жизненного цикла не заполнена в базе стратегий.",
    "ARCHETYPE_AMBIGUOUS": "Якорные стадии и во фронте, и в бэке: типовой сценарий неприменим.",
    "HIGH_TURBULENCE": "Высокая доля подвижных линий: система в фазе широкой трансформации.",
    "NO_INTERNAL_PRESSURE": "Подвижных линий нет ни в одном контуре: конфигурация стабильна (в т.ч. возможен стабильный упадок).",
    "RENEWAL_PRESSURE": "Выраженное давление роста: назревшие слабости преобладают над перегревом.",
    "OVERHEAT_RISK": "Выраженный риск перегрева: подвижные сильные позиции преобладают.",
}



def company_lifecycle_html(lc: dict, lifecycle_stages=None,
                           section_no: str = "03", company_name: str = "") -> str:
    """Раздел «Жизненный цикл компании»: точка (стадия ограничения), архетип
    с рамкой линий 5-6, тактика из маршрута ограничения, вектор по контурам.
    Самостоятельный раздел-страница ПЕРЕД финансовой функцией: цикл — свойство
    компании (контур-ограничение), а не финансового блока."""
    from app.contours import CONTOURS
    ink = "#1a2540"

    def _title(key):
        return CONTOURS[key].title if key in CONTOURS else (key or "")

    # Точка: график стадий с отметкой стадии контура-ограничения
    stage = lc.get("stage")
    chart = ""
    if stage and lifecycle_stages:
        idx = next((st.get("sort_order") for st in lifecycle_stages
                    if (st.get("name") or "").strip().lower() == stage), None)
        chart = _lifecycle_chart_html(lifecycle_stages, idx)
    constraint = lc.get("constraint")
    if constraint:
        point = (f'<p style="font-size:13px;color:rgba(26,37,64,0.72);line-height:1.7;margin:0 0 12px;font-family:Arial,sans-serif;">'
                 f'Стадия определяется по контуру-ограничению — <b>{e(_title(constraint))}</b>: '
                 'система движется со скоростью узкого места.</p>')
    else:
        tied = ", ".join(_title(t) for t in (lc.get("tied") or []))
        point = (f'<p style="font-size:13px;color:rgba(26,37,64,0.72);line-height:1.7;margin:0 0 12px;font-family:Arial,sans-serif;">'
                 f'Стадия не фиксируется: минимальную зрелость делят контуры — {e(tied)}. '
                 'Требуется дообследование или стратегическая сессия.</p>')

    # Архетип и рамка (семантика линий 5-6)
    frame = lc.get("playbook", {}).get("frame") or {}
    arch = (f'<div style="display:inline-block;padding:4px 14px;border-radius:4px;font-size:13px;'
            f'font-family:Arial,sans-serif;background:rgba(30,58,138,0.08);border:1px solid rgba(30,58,138,0.2);'
            f'color:#1e3a8a;margin:2px 0 12px;">Архетип: {e(lc.get("archetype_title") or "")}</div>')
    frame_html = ""
    for fkey, flabel in (("environment", "Линия 5 — Внешняя среда"),
                         ("strategy", "Линия 6 — Видение и стратегия")):
        if frame.get(fkey):
            frame_html += (
                '<div style="background:rgba(255,255,255,0.5);border:1px solid rgba(26,37,64,0.1);'
                'border-radius:6px;padding:12px 14px;margin-bottom:8px;page-break-inside:avoid;">'
                f'<div style="font-size:9px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;'
                f'color:rgba(26,37,64,0.45);font-weight:600;margin-bottom:6px;">{flabel} — стратегическая рамка</div>'
                f'<p style="font-size:12px;color:{ink};line-height:1.6;margin:0;font-family:Arial,sans-serif;">{e(frame[fkey])}</p></div>')

    # Тактика: шаги маршрута контура-ограничения (детали — в его разделе)
    tactics = lc.get("playbook", {}).get("tactics") or []
    steps_html = ""
    for st in tactics:
        param = st.get("line_title") or st.get("line_key") or ""
        direction = ("укрепить слабую позицию" if st.get("from_state") == "old_yin"
                     else "стабилизировать перегрев")
        steps_html += (f'<li style="margin-bottom:6px;">Шаг {st.get("order")}. Линия {st.get("line")} — '
                       f'{e(param)} <span style="color:rgba(26,37,64,0.6);">({e(direction)})</span></li>')
    if steps_html:
        tactics_html = (
            f'<p style="font-size:12px;color:rgba(26,37,64,0.6);font-family:Arial,sans-serif;margin:0 0 8px;">'
            f'Тактика — фактические подвижные линии контура «{e(_title(constraint))}» '
            '(детальные действия — в разделе этого контура):</p>'
            f'<ul style="margin:0 0 12px;padding-left:18px;font-size:12px;color:{ink};'
            f'font-family:Arial,sans-serif;line-height:1.5;">{steps_html}</ul>')
    else:
        tactics_html = ""

    # Вектор: переход стадий по контурам
    vec = lc.get("vector") or {}
    vrows = ""
    for key, v in vec.items():
        to = v.get("to")
        vrows += (f'<tr><td style="padding:7px 8px;font-size:12px;color:{ink};font-family:Arial,sans-serif;">{e(_title(key))}</td>'
                  f'<td style="padding:7px 8px;text-align:center;font-size:12px;color:{ink};font-family:Arial,sans-serif;">{e(v.get("from") or "—")}</td>'
                  f'<td style="padding:7px 8px;text-align:center;font-size:12px;color:{ink};font-family:Arial,sans-serif;">'
                  + (e(to) if to else '<span style="opacity:0.45;">без перехода</span>') + '</td>'
                  f'<td style="padding:7px 8px;text-align:center;font-family:monospace;font-size:12px;color:{ink};">{e(str(v.get("moving_count", 0)))}</td></tr>')
    th = ('<th style="text-align:left;padding:7px 8px;font-size:10px;text-transform:uppercase;'
          'letter-spacing:1px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;font-weight:400;">')
    vector_html = (
        '<table style="width:100%;border-collapse:collapse;margin-bottom:12px;">'
        f'<thead><tr style="border-bottom:1px solid rgba(26,37,64,0.15);">{th}Контур</th>'
        f'{th.replace("text-align:left","text-align:center")}Стадия сейчас</th>'
        f'{th.replace("text-align:left","text-align:center")}Стадия после перехода</th>'
        f'{th.replace("text-align:left","text-align:center")}Подвижных линий</th></tr></thead>'
        f'<tbody>{vrows}</tbody></table>') if vrows else ""

    # Флаги качества
    notes = [(_CL_FLAG_LABELS.get(f) or f) for f in (lc.get("quality_flags") or [])]
    notes_html = ""
    if notes:
        items = "".join(f'<li style="margin-bottom:5px;">{e(n)}</li>' for n in notes)
        notes_html = (f'<ul style="margin:0;padding-left:18px;font-size:11px;color:rgba(26,37,64,0.6);'
                      f'font-family:Arial,sans-serif;line-height:1.5;">{items}</ul>')

    accent = "#c0392b"
    return (
        '<div style="padding:40px 50px;background:#e8e4db;page-break-before:always;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:24px;">'
        f'<span style="font-size:11px;font-weight:700;color:{accent};font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>'
        f'<span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">{e(company_name)} · жизненный цикл</span>'
        '</div>'
        f'<h2 style="font-size:22px;font-weight:400;color:{ink};margin:0 0 12px;">'
        f'<span style="font-size:11px;color:{accent};margin-right:10px;">{e(section_no)}</span>Жизненный цикл компании</h2>'
        + point + chart + arch + frame_html + tactics_html + vector_html + notes_html +
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);'
        'display:flex;justify-content:space-between;font-family:Arial,sans-serif;font-size:10px;color:rgba(26,37,64,0.3);">'
        '<span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>'
        '</div></div>')


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
    extra_contours: list | None = None,
    summary: dict | None = None,
    target_strategy: Any | None = None,
    dynamics: dict | None = None,
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

    # Блок "Целевой сценарий" — строим заранее, чтобы вставить простой переменной
    transition_html = transition_block(strategy, target_strategy, _hexagram_svg(target_strategy.combination, size=88) if target_strategy is not None else '')

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

    # ── Жизненный цикл компании: раздел 03 ПЕРЕД финансовой функцией ──
    # Цикл — свойство компании (контур-ограничение), поэтому это отдельный
    # раздел, а не часть финансового блока. Его наличие сдвигает нумерацию
    # финансов/сводной/контуров на +1.
    lc = summary.get("company_lifecycle") if summary else None
    lifecycle_page = ""
    _shift = 0
    if (not is_method2) and lc:
        lifecycle_page = company_lifecycle_html(
            lc, lifecycle_stages, section_no="03", company_name=company_name)
        _shift = 1

    # ── Финансовая функция (Метод 1, только при наличии результата скоринга) ──
    finance_section = ""
    if (not is_method2) and finance_result and finance_interpretation:
        finance_section = finance_section_html(
            finance_result, finance_interpretation, company_name,
            _finance_description_html(finance_strategy, lifecycle_stages),
            section_no=f"{3 + _shift:02d}",
        )

    transition_page = (
        f'<div style="padding:40px 50px;background:#e8e4db;">{transition_html}</div>'
        if (transition_html and not is_method2) else ""
    )

    # Сводная карта и секции дополнительных контуров (Поправки П7 и П8).
    # Полный профиль стратегии остаётся только у финансового контура, поэтому
    # description_html здесь пустой.
    summary_section = ""
    contour_sections = ""
    if not is_method2:
        if summary:
            summary_section = summary_card_html(
                summary, company_name, section_no=f"{4 + _shift:02d}")
        if extra_contours:
            from app.contours import get_spec as _spec_of
            _cno = 5 + _shift
            for _c in extra_contours:
                contour_sections += contour_section_html(
                    _c["result"], _c["interp"], company_name,
                    blocks=_spec_of(_c["contour"]).blocks,
                    title=_c["title"],
                    section_no=f"{_cno:02d}",
                )
                _cno += 1

    # ── Раздел 09 «Динамика» (только повторный отчёт) ────────────────────
    # Номер фиксированный: раздел идёт последним и не участвует в сдвиге
    # нумерации контуров. dynamics_section_html вернёт "", если сравнивать
    # не с чем (нет предыдущего замера).
    dynamics_page = ""
    if dynamics and not is_method2:
        from app.contours import CONTOURS as _CONTOURS
        from app.dynamics_block import dynamics_section_html
        _dyn_body = dynamics_section_html(
            dynamics, section_no="09",
            titles={_k: _s.title for _k, _s in _CONTOURS.items()},
        )
        if _dyn_body:
            dynamics_page = (
                '<div style="padding:40px 50px;background:#e8e4db;'
                'page-break-before:always;">'
                + _dyn_body + '</div>'
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

{transition_page}

{lifecycle_page}

{finance_section}

{summary_section}

{contour_sections}

{bmc_section}

{dynamics_page}

</body>
</html>"""
