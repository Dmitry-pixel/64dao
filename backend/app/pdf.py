"""
PDF-генерация через Playwright (Python).

Браузер запускается один раз (singleton) и переиспользуется.
Каждый запрос получает отдельный Page, который закрывается после генерации.
"""
import asyncio
import html as html_lib
from pathlib import Path
from typing import Any

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
    bars = "".join(
        f'<span style="display:inline-block;width:22px;height:5px;border-radius:3px;'
        f'margin-right:3px;background:{"#1e3a8a" if n <= score else "#e5e7eb"};"></span>'
        for n in range(1, 6)
    )
    return f'<div style="margin-bottom:6px;">{bars}</div>'


def _table_rows(rows: list[tuple[str, str]]) -> str:
    html = ""
    for i, (label, value) in enumerate(rows):
        bg = "background:#f9fafb;" if i % 2 == 0 else ""
        html += (
            f"<tr>"
            f'<td style="border:1px solid #d1d5db;padding:7px 10px;{bg}'
            f'font-size:12px;color:#6b7280;width:45%;vertical-align:top;">{e(label)}</td>'
            f'<td style="border:1px solid #d1d5db;padding:7px 10px;{bg}'
            f'font-size:12px;color:#111827;font-weight:500;vertical-align:top;">{e(value)}</td>'
            f"</tr>"
        )
    return f'<table style="width:100%;border-collapse:collapse;margin-bottom:16px;"><tbody>{html}</tbody></table>'


CURRENT_STATE_LABELS = {
    "value_type":     "Тип ценности",
    "market_status":  "Статус рынка",
    "consumer_type":  "Тип потребителя",
    "organization":   "Организация управления",
    "strategy":       "Бизнес-стратегия",
    "goal":           "Бизнес-цель",
}

SCENARIO_LABELS = {
    "innovation_strategy":   "Инновационная стратегия",
    "innovation_type":       "Тип инновации",
    "value_discipline":      "Ценностная дисциплина",
    "leadership_principles": "Принципы лидерства",
    "growth_strategy":       "Стратегия роста",
    "focus":                 "Фокус",
}

# Ключи должны точно совпадать с b.title в BMC_BLOCKS на фронтенде (assessment/page.tsx)
BMC_KEYS = [
    "Ключевые партнёры",
    "Ключевые активности",
    "Ключевые ресурсы",
    "Ценностное предложение",
    "Отношения с клиентами",
    "Каналы",
    "Сегменты клиентов",
    "Структура издержек",
    "Потоки доходов",
]

HEX_SYMBOLS = [
    "䷀","䷁","䷂","䷃","䷄","䷅","䷆","䷇","䷈","䷉","䷊","䷋",
    "䷌","䷍","䷎","䷏","䷐","䷑","䷒","䷓","䷔","䷕","䷖","䷗",
    "䷘","䷙","䷚","䷛","䷜","䷝","䷞","䷟","䷠","䷡","䷢","䷣",
]

# ── Hexagram data ─────────────────────────────────────────────────────────────
# (number, name, combination)
_HEXAGRAM_LIST = [
    (1,  "Действие",              "AAAAAA"),
    (2,  "Реакция",               "BBBBBB"),
    (3,  "Появление",             "ABBBAB"),
    (4,  "Формализация",          "BABBBA"),
    (5,  "Бдительность",          "AAABAB"),
    (6,  "Раздор",                "BABAAA"),
    (7,  "Управление",            "BABBBB"),
    (8,  "Объединение",           "BBBBAB"),
    (9,  "Развитие",              "AAABAA"),
    (10, "Последовательность",    "AABAAA"),
    (11, "Достижение",            "AAABBB"),
    (12, "Препятствие",           "BBBAAA"),
    (13, "Осознанность",          "ABAAAA"),
    (14, "Процветание",           "AAAABA"),
    (15, "Смирение",              "BBABBB"),
    (16, "Радость",               "BBBABB"),
    (17, "Соответствие",          "ABBAAB"),
    (18, "Диссонанс",             "BAABBA"),
    (19, "Подход",                "AABBBB"),
    (20, "Наблюдать",             "BBBBAA"),
    (21, "Устранять",             "ABBABA"),
    (22, "Изящество",             "ABABBA"),
    (23, "Разрушение",            "BBBBBA"),
    (24, "Возрождение",           "ABBBBB"),
    (25, "Естественность",        "ABBAAA"),
    (26, "Изобилие",              "AAABBA"),
    (27, "Умеренность",           "ABBBBA"),
    (28, "Избыток",               "BAAAAB"),
    (29, "Решимость",             "BABBAB"),
    (30, "Великолепие",           "ABAABA"),
    (31, "Влияние",               "BBAAAB"),
    (32, "Выносливость",          "BAAABB"),
    (33, "Благоразумие",          "BBAAAA"),
    (34, "Сила",                  "AAAABB"),
    (35, "Благоприятный",         "BBBABA"),
    (36, "Неблагоприятный",       "ABABBB"),
    (37, "Гармония",              "ABABAA"),
    (38, "Полярность",            "AABABA"),
    (39, "Трудность",             "BBABAB"),
    (40, "Избавление",            "BABABB"),
    (41, "Убыток",                "AABBBA"),
    (42, "Прибыль",               "ABBBAA"),
    (43, "Прорыв",                "AAAAAB"),
    (44, "Встреча",               "BAAAAA"),
    (45, "Объединение",           "BBBAAB"),
    (46, "Самоотдача",            "BAABBB"),
    (47, "Понимание",             "BABAAB"),
    (48, "Глубина",               "BAABAB"),
    (49, "Реформа",               "ABAAAB"),
    (50, "Ценности",              "BAAABA"),
    (51, "Смелость",              "ABBABB"),
    (52, "Сосредоточенность",     "BBABBA"),
    (53, "Готовность",            "BBABAA"),
    (54, "Амбиции",               "AABABB"),
    (55, "Изобилие",              "ABAABB"),
    (56, "Стимулирование",        "BBAABA"),
    (57, "Интуиция",              "BABBAA"),
    (58, "Бодрость",              "AABAAB"),
    (59, "Установление связей",   "BAABAA"),
    (60, "Реализм",               "AABBAB"),
    (61, "Внутренняя правда",     "AABBAA"),
    (62, "Точность",              "BBAABB"),
    (63, "Завершение",            "ABABAB"),
    (64, "Незавершённость",       "BABABA"),
]

# combination → (number, name)
_HEXAGRAM_BY_COMBO: dict[str, tuple[int, str]] = {
    combo: (num, name) for num, name, combo in _HEXAGRAM_LIST
}

# number → name
_HEXAGRAM_BY_NUM: dict[int, str] = {
    num: name for num, name, _ in _HEXAGRAM_LIST
}

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
    ("assm_feedback",    "Братная связь"),
    ("assm_risk",        "Риск"),
    ("assm_product",     "Выбор продукта"),
    ("assm_service",     "Сервис"),
    ("assm_startup",     "Стартап"),
    ("assm_investment",  "Инвестиции и финансы"),
    ("assm_contracts",   "Договора и соглашения"),
    ("assm_sync",        "Синхронизация"),
    ("assm_creative",    "Творческий вклад"),
    ("assm_interaction", "Взаимодействие"),
]

def _assumptions_block(strategy: Any) -> str:
    """HTML-блок 'Предположения, лежащие в основе принятия решения. Связи с будущим'."""
    if not strategy:
        return ""
    items = ""
    for field, label in _ASSUMPTION_FIELDS:
        val = getattr(strategy, field, None)
        if val:
            items += (
                '<div style="margin-bottom:16px;">'
                '<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;'
                'text-transform:uppercase;color:#c0392b;font-family:Arial,sans-serif;margin-bottom:4px;">'
                + e(label) +
                '</div>'
                '<p style="font-size:13px;color:rgba(26,37,64,0.7);line-height:1.7;'
                'margin:0;font-family:Arial,sans-serif;">'
                + e(val) +
                '</p>'
                '</div>'
            )
    if not items:
        return ""
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
    """HTML-блок 'Целевое состояние' с символом и названием целевой гексаграммы."""
    if not strategy or not strategy.transition_title:
        return ""

    if target_hex_info:
        t_num, t_name, t_symbol = target_hex_info
        hex_col = (
            '<div style="text-align:center;flex-shrink:0;min-width:90px;">'
            '<div style="font-size:64px;line-height:1;color:#1a2540;margin-bottom:6px;">'
            + t_symbol +
            '</div>'
            '<div style="font-size:10px;color:#c0392b;font-family:Arial,sans-serif;'
            'letter-spacing:1px;font-weight:600;">'
            + "Гексаграмма " + str(t_num) +
            '</div>'
            '<div style="font-size:11px;color:rgba(26,37,64,0.7);font-family:Arial,sans-serif;'
            'margin-top:3px;">'
            + e(t_name) +
            '</div>'
            '</div>'
        )
    else:
        hex_col = ""

    title_html = e(strategy.transition_title)
    desc_html  = e(strategy.transition_description or "")

    return (
        '<div style="margin-top:24px;padding:16px 20px;'
        'border:1px solid rgba(192,57,43,0.2);border-radius:6px;'
        'background:rgba(192,57,43,0.04);">'
        '<div style="font-size:10px;color:#c0392b;letter-spacing:2px;'
        'text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:12px;">'
        'Целевое состояние'
        '</div>'
        '<div style="display:flex;align-items:flex-start;gap:20px;">'
        + hex_col +
        '<div style="flex:1;">'
        '<h3 style="font-size:16px;font-weight:500;color:#1a2540;margin-bottom:6px;">'
        + title_html +
        '</h3>'
        '<p style="font-size:12px;color:rgba(26,37,64,0.65);'
        'font-family:Arial,sans-serif;line-height:1.7;margin:0;">'
        + desc_html +
        '</p>'
        '</div>'
        '</div>'
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


def _lifecycle_blocks(strategy: Any, combination: str) -> str:
    """6 блоков жизненного цикла для PDF — по одному на каждый вопрос."""
    header = ""
    if strategy and strategy.stratagema_title:
        header = f'<div style="display:inline-block;padding:3px 10px;border-radius:3px;font-size:10px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;background:rgba(30,58,138,0.08);border:1px solid rgba(30,58,138,0.2);color:#1e3a8a;margin-bottom:10px;">{e(strategy.stratagema_title)}</div>'
    if strategy and strategy.title:
        header += f'<h3 style="font-size:16px;font-weight:500;color:#1a2540;margin-bottom:16px;font-family:Arial,sans-serif;">{e(strategy.title)}</h3>'

    blocks_html = ""
    for i, (field, label) in enumerate(_LC_LABELS):
        letter = combination[i] if i < len(combination) else "A"
        value = (getattr(strategy, field, None) or "") if strategy else ""
        badge_bg = "rgba(30,58,138,0.1)" if letter == "A" else "rgba(26,37,64,0.06)"
        badge_color = "#1e3a8a" if letter == "A" else "#1a2540"
        badge_border = "rgba(30,58,138,0.2)" if letter == "A" else "rgba(26,37,64,0.15)"
        blocks_html += f"""
<div style="background:rgba(255,255,255,0.5);border:1px solid rgba(26,37,64,0.1);border-radius:6px;padding:12px 14px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <span style="width:18px;height:18px;border-radius:50%;background:{badge_bg};border:1px solid {badge_border};color:{badge_color};display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:10px;font-weight:700;flex-shrink:0;">{letter}</span>
    <span style="font-size:9px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;color:rgba(26,37,64,0.45);font-weight:600;">{e(label)}</span>
  </div>
  <p style="font-size:12px;color:#1a2540;line-height:1.6;margin:0;font-family:Arial,sans-serif;">{e(value)}</p>
</div>"""

    return f"""<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:20px 24px;background:rgba(255,255,255,0.4);">
{header}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
{blocks_html}
</div>
</div>"""


def build_report_html(
    company_name: str,
    user_name: str,
    date_str: str,
    combination: str,
    strategy: Any | None,
    method2_data: dict[str, Any],
) -> str:
    """Собирает полный HTML отчёта (все данные уже экранированы через e())."""

    hex_grid = "".join(
        f'<div style="display:flex;align-items:center;justify-content:center;'
        f'font-size:32px;color:#1a2540;">{s}</div>'
        for s in HEX_SYMBOLS
    )

    # Целевая гексаграмма — вычисляем заранее, чтобы не усложнять f-строки
    target_hex_info = get_target_hexagram_info(combination) if combination else None

    # Текущее состояние
    cs = (strategy.current_state or {}) if strategy else {}
    cs_rows = [(lbl, cs[k]) for k, lbl in CURRENT_STATE_LABELS.items() if cs.get(k)]

    # Сценарий
    sc = (strategy.scenario or {}) if strategy else {}
    sc_rows = [(lbl, sc[k]) for k, lbl in SCENARIO_LABELS.items() if sc.get(k)]

    # BMC: сетка оценок (только баллы, без текста)
    bmc_score_grid = ""
    # BMC: комментарии (только тексты, без баллов)
    bmc_comments = ""
    for label in BMC_KEYS:
        block = method2_data.get(label, {})
        score = int(block.get("score", 0)) if block else 0
        text  = str(block.get("text", "")) if block else ""
        # Карточка оценки
        bmc_score_grid += f"""
        <div style="border:1px solid rgba(26,37,64,0.1);border-radius:5px;
                    padding:12px;background:rgba(255,255,255,0.5);">
          <div style="font-size:11px;font-weight:600;color:#1a2540;
                      font-family:Arial,sans-serif;margin-bottom:8px;">{e(label)}</div>
          {_score_bar(score)}
        </div>"""
        # Блок комментария
        bmc_comments += f"""
        <div style="border:1px solid rgba(26,37,64,0.1);border-radius:5px;
                    padding:14px 16px;background:rgba(255,255,255,0.5);">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="font-size:11px;font-weight:600;color:#1a2540;
                        font-family:Arial,sans-serif;">{e(label)}</div>
            <div style="flex-shrink:0;">{_score_bar(score)}</div>
          </div>
          <div style="font-size:12px;color:rgba(26,37,64,0.7);
                      line-height:1.6;font-family:Arial,sans-serif;">
            {e(text) if text else '<em style="opacity:0.4;">Не заполнено</em>'}
          </div>
        </div>"""

    # Блок "Предположения" — строим до page2, чтобы вставить простой переменной
    assumptions_html = _assumptions_block(strategy)
    # Блок "Целевое состояние" — строим до page2, чтобы вставить простой переменной
    transition_html = _transition_block(strategy, target_hex_info)

    # Определяем тип отчёта
    is_method2 = not combination

    # ── Обложка ──────────────────────────────────────────────────────────────
    if is_method2:
        cover_label = "Отчёт по бизнес-модели"
        cover_title = f"Бизнес-модель<br>{e(company_name)}"
        cover_combo = ""
    else:
        cover_label = "Отчёт по стратегической диагностике"
        cover_title = "Стратегический<br>профиль компании"
        cover_combo = f'<div style="font-family:\'Courier New\',monospace;font-size:44px;font-weight:700;color:#1e3a8a;letter-spacing:8px;opacity:0.18;">{e(combination)}</div>'

    # ── Страница 1 (только для Method 1) ──────────────────────────────────
    page1 = ""
    if not is_method2:
        page1 = f"""
<div style="padding:40px 50px;page-break-after:always;background:#e8e4db;min-height:297mm;">
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:28px;">
    <span style="font-size:11px;font-weight:700;color:#c0392b;font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>
    <span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">
      {e(company_name)} · стр. 1
    </span>
  </div>
  <div style="font-size:10px;color:rgba(26,37,64,0.3);letter-spacing:2px;
              text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:6px;">текущее состояние</div>
  <h1 style="font-size:28px;font-weight:400;color:#1a2540;margin-bottom:8px;">Стратегический профиль</h1>
  <p style="font-size:13px;color:rgba(26,37,64,0.55);line-height:1.7;
            font-family:Arial,sans-serif;margin-bottom:24px;">
    На основании выбранных ответов определена следующая комбинация параметров бизнес-модели.
  </p>
  <div style="font-family:'Courier New',monospace;font-size:44px;font-weight:700;
              color:#1e3a8a;letter-spacing:8px;margin-bottom:20px;">{e(combination)}</div>
  <h2 style="font-size:18px;font-weight:400;color:#1a2540;margin-bottom:12px;">Текущее состояние</h2>
  {_table_rows(cs_rows) if cs_rows else ""}
  {f'<div style="display:inline-block;padding:3px 10px;border-radius:3px;font-size:10px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;background:rgba(192,57,43,0.08);border:1px solid rgba(192,57,43,0.2);color:#c0392b;margin-bottom:12px;">{e(strategy.lifecycle_stage or "")}</div>' if strategy and strategy.lifecycle_stage else ""}
  {_lifecycle_blocks(strategy, combination) if strategy else ""}
  <div style="margin-top:32px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
              display:flex;justify-content:space-between;font-family:Arial,sans-serif;
              font-size:10px;color:rgba(26,37,64,0.3);">
    <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
  </div>
</div>"""

    # ── Страница 2 (сценарий) — только для Method 1 ──────────────────────
    page2 = ""
    if strategy and not is_method2:
        page2 = f"""
        <div style="padding:40px 50px;page-break-after:always;background:#e8e4db;min-height:297mm;">
          <div style="display:flex;justify-content:space-between;align-items:center;
                      padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:28px;">
            <span style="font-size:11px;font-weight:700;color:#c0392b;font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>
            <span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">
              {e(company_name)} · стр. 2
            </span>
          </div>
          <div style="font-size:10px;color:rgba(26,37,64,0.3);letter-spacing:2px;
                      text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:6px;">
            стратегические требования
          </div>
          <h1 style="font-size:28px;font-weight:400;color:#1a2540;margin:0 0 20px;">
            Сценарий и рекомендации
          </h1>
          {f'<h2 style="font-size:18px;font-weight:400;color:#1a2540;margin-bottom:12px;">Параметры сценария</h2>{_table_rows(sc_rows)}' if sc_rows else ""}
          {f'<h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:20px 0 12px;">Описание стратегии</h2><div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:20px;background:rgba(255,255,255,0.4);"><p style="font-size:13px;color:rgba(26,37,64,0.7);line-height:1.7;margin:0;font-family:Arial,sans-serif;">{e(strategy.scenario_text)}</p></div>' if strategy.scenario_text else ""}
          {f'<h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:20px 0 12px;">Маркетинг</h2><div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:20px;background:rgba(255,255,255,0.4);"><p style="font-size:13px;color:rgba(26,37,64,0.7);line-height:1.7;margin:0;font-family:Arial,sans-serif;">{e(strategy.marketing_text)}</p></div>' if strategy.marketing_text else ""}
          {f'<h2 style="font-size:18px;font-weight:400;color:#1a2540;margin:20px 0 12px;">Управление</h2><div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:20px;background:rgba(255,255,255,0.4);"><p style="font-size:13px;color:rgba(26,37,64,0.7);line-height:1.7;margin:0;font-family:Arial,sans-serif;">{e(strategy.management_text)}</p></div>' if strategy.management_text else ""}
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
            overflow:hidden;display:flex;flex-direction:column;page-break-after:always;">
  <div style="position:absolute;right:0;top:0;width:55%;height:100%;
              display:grid;grid-template-columns:repeat(6,1fr);gap:2px;opacity:0.08;">
    {hex_grid}
  </div>
  <div style="position:relative;z-index:2;padding:60px 50px;
              display:flex;flex-direction:column;justify-content:space-between;height:100%;">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="width:44px;height:44px;border:2px solid #c0392b;border-radius:4px;
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-size:10px;font-weight:700;color:#c0392b;line-height:1.1;font-family:Arial,sans-serif;">
        <span>64</span><span style="letter-spacing:2px">DAO</span>
      </div>
      <span style="font-size:12px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;letter-spacing:1px;">
        Стратегическая диагностика
      </span>
    </div>
    <div style="max-width:380px;">
      <div style="font-size:10px;color:rgba(26,37,64,0.3);letter-spacing:2px;
                  text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:16px;">
        {cover_label}
      </div>
      <h1 style="font-size:40px;font-weight:400;line-height:1.1;color:#1a2540;margin-bottom:20px;">
        {cover_title}
      </h1>
      {"" if is_method2 else f'<div style="font-size:20px;color:rgba(26,37,64,0.7);margin-bottom:8px;">{e(company_name)}</div>'}
      <div style="font-size:13px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;">{date_str}</div>
    </div>
    {cover_combo}
  </div>
</div>

{page1}

{page2}

{bmc_section}

</body>
</html>"""
