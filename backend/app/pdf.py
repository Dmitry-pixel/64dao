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

        # Playwright context
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
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

BMC_LABELS = {
    "segments":   "Потребительские сегменты",
    "value":      "Ценностные предложения",
    "channels":   "Каналы сбыта",
    "relations":  "Взаимоотношения с клиентами",
    "revenue":    "Потоки доходов",
    "resources":  "Ключевые ресурсы",
    "activities": "Ключевые виды деятельности",
    "partners":   "Ключевые партнёры",
    "costs":      "Структура издержек",
}

HEX_SYMBOLS = [
    "䷀","䷁","䷂","䷃","䷄","䷅","䷆","䷇","䷈","䷉","䷊","䷋",
    "䷌","䷍","䷎","䷏","䷐","䷑","䷒","䷓","䷔","䷕","䷖","䷗",
    "䷘","䷙","䷚","䷛","䷜","䷝","䷞","䷟","䷠","䷡","䷢","䷣",
]


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

    # Текущее состояние
    cs = (strategy.current_state or {}) if strategy else {}
    cs_rows = [(lbl, cs[k]) for k, lbl in CURRENT_STATE_LABELS.items() if cs.get(k)]

    # Сценарий
    sc = (strategy.scenario or {}) if strategy else {}
    sc_rows = [(lbl, sc[k]) for k, lbl in SCENARIO_LABELS.items() if sc.get(k)]

    # BMC блоки
    bmc_blocks = ""
    for key, label in BMC_LABELS.items():
        block = method2_data.get(key, {})
        score = int(block.get("score", 0)) if block else 0
        text  = str(block.get("text", "")) if block else ""
        preview = (text[:220] + "…") if len(text) > 220 else text
        bmc_blocks += f"""
        <div style="border:1px solid rgba(26,37,64,0.1);border-radius:5px;
                    padding:12px;background:rgba(255,255,255,0.5);">
          <div style="font-size:11px;font-weight:600;color:#1a2540;
                      font-family:Arial,sans-serif;margin-bottom:6px;">{label}</div>
          {_score_bar(score)}
          <div style="font-size:11px;color:rgba(26,37,64,0.55);
                      line-height:1.5;font-family:Arial,sans-serif;">
            {e(preview) if preview else '<em style="opacity:0.4;">Не заполнено</em>'}
          </div>
        </div>"""

    # Страница 2 (сценарий) — только если есть стратегия
    page2 = ""
    if strategy:
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
          {f'<div style="margin-top:24px;padding:16px 20px;border:1px solid rgba(192,57,43,0.2);border-radius:6px;background:rgba(192,57,43,0.04);"><div style="font-size:10px;color:#c0392b;letter-spacing:2px;text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:8px;">Целевое состояние</div><h3 style="font-size:16px;font-weight:500;color:#1a2540;margin-bottom:6px;">{e(strategy.transition_title)}</h3><p style="font-size:12px;color:rgba(26,37,64,0.65);font-family:Arial,sans-serif;line-height:1.7;margin:0;">{e(strategy.transition_description or "")}</p></div>' if strategy.transition_title else ""}
          <div style="margin-top:32px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
                      display:flex;justify-content:space-between;font-family:Arial,sans-serif;
                      font-size:10px;color:rgba(26,37,64,0.3);">
            <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
          </div>
        </div>"""

    page3_num = 3 if strategy else 2

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
<div style="width:210mm;height:297mm;background:#e8e4db;position:relative;
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
        Отчёт по стратегической диагностике
      </div>
      <h1 style="font-size:40px;font-weight:400;line-height:1.1;color:#1a2540;margin-bottom:20px;">
        Стратегический<br>профиль компании
      </h1>
      <div style="font-size:20px;color:rgba(26,37,64,0.7);margin-bottom:8px;">{e(company_name)}</div>
      <div style="font-size:13px;color:rgba(26,37,64,0.4);font-family:Arial,sans-serif;">{date_str}</div>
    </div>
    <div style="font-family:'Courier New',monospace;font-size:44px;font-weight:700;
                color:#1e3a8a;letter-spacing:8px;opacity:0.18;">{e(combination)}</div>
  </div>
</div>

<!-- СТРАНИЦА 1: ТЕКУЩЕЕ СОСТОЯНИЕ -->
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
  {f'<div style="border:1px solid rgba(26,37,64,0.12);border-radius:6px;padding:20px 24px;background:rgba(255,255,255,0.4);"><div style="display:inline-block;padding:3px 10px;border-radius:3px;font-size:10px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;background:rgba(30,58,138,0.08);border:1px solid rgba(30,58,138,0.2);color:#1e3a8a;margin-bottom:10px;">{e(strategy.stratagema_title or "")}</div><h3 style="font-size:16px;font-weight:500;color:#1a2540;margin-bottom:10px;">{e(strategy.title or "")}</h3><p style="font-size:13px;color:rgba(26,37,64,0.7);line-height:1.7;margin:0;font-family:Arial,sans-serif;">{e(strategy.lifecycle_description or "")}</p></div>' if strategy else ""}
  <div style="margin-top:32px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
              display:flex;justify-content:space-between;font-family:Arial,sans-serif;
              font-size:10px;color:rgba(26,37,64,0.3);">
    <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
  </div>
</div>

{page2}

<!-- СТРАНИЦА {page3_num}: КАНВА БИЗНЕС-МОДЕЛИ -->
<div style="padding:40px 50px;background:#e8e4db;min-height:297mm;">
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding-bottom:14px;border-bottom:1px solid rgba(26,37,64,0.12);margin-bottom:28px;">
    <span style="font-size:11px;font-weight:700;color:#c0392b;font-family:Arial,sans-serif;letter-spacing:2px;">64DAO</span>
    <span style="font-size:10px;color:rgba(26,37,64,0.3);font-family:Arial,sans-serif;">
      {e(company_name)} · стр. {page3_num}
    </span>
  </div>
  <div style="font-size:10px;color:rgba(26,37,64,0.3);letter-spacing:2px;
              text-transform:uppercase;font-family:Arial,sans-serif;margin-bottom:6px;">
    метод 2 — оценка бизнес-модели
  </div>
  <h1 style="font-size:28px;font-weight:400;color:#1a2540;margin-bottom:8px;">Канва бизнес-модели</h1>
  <p style="font-size:13px;color:rgba(26,37,64,0.55);line-height:1.7;
            font-family:Arial,sans-serif;margin-bottom:24px;">
    Оценка текущего состояния каждого блока бизнес-модели по методологии Остервальдера.
  </p>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px;">
    {bmc_blocks}
  </div>
  <div style="margin-top:32px;padding-top:12px;border-top:1px solid rgba(26,37,64,0.08);
              display:flex;justify-content:space-between;font-family:Arial,sans-serif;
              font-size:10px;color:rgba(26,37,64,0.3);">
    <span>64dao.ru</span><span>© 2024 64DAO — Конфиденциально</span>
  </div>
</div>

</body>
</html>"""
