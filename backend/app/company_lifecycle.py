# -*- coding: utf-8 -*-
"""
Жизненный цикл компании: агрегация 4 контуров в единый диагноз.

Чистые функции без БД и FastAPI: диагноз — детерминированная функция от
обогащённых снимков result контуров. Обогащение (lifecycle_stage текущей и
результирующей гексаграммы из Strategy) делает вызывающий код.

Три слоя вывода:
- Точка: стадия контура-ограничения. Система движется со скоростью узкого
  места (логика теории ограничений), поэтому цикл компании привязан к
  constraint из contour_summary, а не к финансовому контуру.
- Вектор: переход стадии current -> resulting по каждому контуру.
- Архетип: категориальный паттерн дисбаланса. Принципиально БЕЗ арифметики
  над стадиями: шкала стадий циклическая (упадок -> обновление -> зарождение),
  среднее и разность индексов по ней не определены. Стадии сравниваются
  только через принадлежность категориям Драйвер/Якорь/Стабилизатор.

Playbook — рамка вокруг маршрута, а не его замена: архетип задаёт
стратегический контекст (семантика линий 5-6: среда и стратегия), тактика
берётся из build_route по фактическим подвижным линиям контура-ограничения.
Две компании с одним архетипом, но разными ответами получат разные шаги.
"""
from __future__ import annotations

from app.contour_route import build_route
from app.contours import CONTOUR_ORDER, LINE_TITLES

# ── Стадии и категории ───────────────────────────────────────────────────────
# Категории вместо чисел: единственная легитимная операция над циклической
# шкалой — проверка принадлежности множеству.
DRIVER_STAGES = frozenset({"расцвет", "обновление"})   # тянут систему вперёд
ANCHOR_STAGES = frozenset({"зарождение", "упадок"})    # узкие места / хрупкость
STABILIZER_STAGES = frozenset({"зрелость"})            # cash flow, инерция
KNOWN_STAGES = DRIVER_STAGES | ANCHOR_STAGES | STABILIZER_STAGES

# Фронт создаёт и монетизирует ценность, бэк её обеспечивает и учитывает.
FRONT_CONTOURS = frozenset({"product", "market"})
BACK_CONTOURS = frozenset({"finance", "process"})

# Стадия компании определяется только по полной картине: агрегат по 2-3
# контурам выдавал бы частичный срез за системный диагноз.
REQUIRED_CONTOURS = 4

# ── Архетипы ─────────────────────────────────────────────────────────────────
ARCH_SYNCHRONOUS_BREAKTHROUGH = "synchronous_breakthrough"
ARCH_SYSTEMIC_CHAOS = "systemic_chaos"
ARCH_TRANSFORMATION_GAP = "transformation_gap"
ARCH_OPERATIONAL_DEBT = "operational_debt"
ARCH_STABLE_MATURITY = "stable_maturity"
ARCH_MIXED = "mixed"

ARCHETYPE_TITLES = {
    ARCH_SYNCHRONOUS_BREAKTHROUGH: "Синхронный прорыв",
    ARCH_SYSTEMIC_CHAOS: "Системный хаос",
    ARCH_TRANSFORMATION_GAP: "Трансформационный разрыв",
    ARCH_OPERATIONAL_DEBT: "Операционный долг",
    ARCH_STABLE_MATURITY: "Стабильная зрелость",
    ARCH_MIXED: "Смешанный дисбаланс",
}

# Стратегическая рамка архетипа: семантика линий 5 (внешняя среда) и
# 6 (видение и стратегия). Конкретные шаги по линиям 1-4 сюда не входят —
# их даёт маршрут подвижных линий контура-ограничения.
ARCHETYPE_FRAMES = {
    ARCH_OPERATIONAL_DEBT: {
        "environment": "Пауза рыночной экспансии: спрос уже опережает "
                       "способность системы его обслужить. Фокус на удержании "
                       "текущих клиентов, а не на захвате новых.",
        "strategy": "Стабилизация обеспечивающих функций: довести операции "
                    "и финансы до уровня, который выдерживает текущий спрос. "
                    "Инновации во фронте замораживаются до закрытия маршрута.",
    },
    ARCH_TRANSFORMATION_GAP: {
        "environment": "Разведка смежных сегментов и сценариев спроса: "
                       "текущий рынок продукта истощается быстрее, чем "
                       "обеспечивающие функции это ощущают.",
        "strategy": "Ресурсы зрелых функций направляются на обновление "
                    "фронта: защищённый бюджет и мандат на эксперименты "
                    "вне действующей операционной модели.",
    },
    ARCH_SYSTEMIC_CHAOS: {
        "environment": "Сужение периметра: один сегмент, один канал. "
                       "Внешние возможности игнорируются, пока нет ядра.",
        "strategy": "Вывести в устойчивое состояние ОДИН контур (обычно "
                    "финансы или операции) и только затем расширять фокус. "
                    "Единственный связующий элемент — видение из базовой "
                    "диагностики.",
    },
    ARCH_SYNCHRONOUS_BREAKTHROUGH: {
        "environment": "Масштабирование модели на смежные рынки, пока "
                       "окно согласованности открыто.",
        "strategy": "Защита от энтропии: буферы, резервы, преемственность "
                    "ключевых ролей. Реструктуризация не чинит, а укрепляет.",
    },
    ARCH_STABLE_MATURITY: {
        "environment": "Мониторинг ранних сигналов смены цикла: зрелость "
                       "без подвижных линий — предвестник упадка, а не "
                       "гарантия стабильности.",
        "strategy": "Плановое обновление до кризиса: выделенный контур "
                    "поиска новых точек роста при сохранении ядра.",
    },
    ARCH_MIXED: {
        "environment": "Разнонаправленные сигналы фронта и бэка: внешняя "
                       "картина не сводится к одному вектору.",
        "strategy": "Паттерн не сводится к типовому сценарию — требуется "
                    "стратегическая сессия по паре Драйвер/Якорь.",
    },
}

# Пороги верификационного слоя (сумма по 4 контурам, всего 24 линии)
TURBULENCE_THRESHOLD = 8   # подвижных линий >= 8 из 24 — трансформация всей системы
PRESSURE_THRESHOLD = 4     # |баланс старых Инь/Ян| >= 4 — выраженный вектор


def _stage_of(result: dict) -> str | None:
    """Нормализованная стадия из обогащённого снимка; None — если нет/чужая."""
    raw = (result.get("lifecycle_stage") or "").strip().lower()
    return raw if raw in KNOWN_STAGES else None


def classify_archetype(stages: dict[str, str | None]) -> tuple[str, list[str]]:
    """Категориальный архетип дисбаланса по стадиям 4 контуров.

    stages: {ключ контура: стадия | None}. Возвращает (архетип, флаги).
    Правила упорядочены по приоритету; None-стадии не участвуют в подсчётах
    и помечаются флагом STAGE_UNKNOWN (без молчаливой подмены на «зрелость»).
    """
    flags: list[str] = []
    known = {k: v for k, v in stages.items() if v is not None}
    if len(known) < len(stages):
        flags.append("STAGE_UNKNOWN")

    drivers = {k for k, v in known.items() if v in DRIVER_STAGES}
    anchors = {k for k, v in known.items() if v in ANCHOR_STAGES}
    stabilizers = {k for k, v in known.items() if v in STABILIZER_STAGES}

    front_anchor = bool(anchors & FRONT_CONTOURS)
    back_anchor = bool(anchors & BACK_CONTOURS)

    if len(drivers) >= 3:
        return ARCH_SYNCHRONOUS_BREAKTHROUGH, flags
    if len(anchors) >= 3:
        return ARCH_SYSTEMIC_CHAOS, flags
    if front_anchor and not back_anchor:
        return ARCH_TRANSFORMATION_GAP, flags
    if back_anchor and not front_anchor:
        return ARCH_OPERATIONAL_DEBT, flags
    if len(stabilizers) >= 3 and not anchors:
        return ARCH_STABLE_MATURITY, flags
    if front_anchor and back_anchor:
        # Якоря по обе стороны при наличии драйверов — типовой сценарий
        # неприменим, честно отдаём на стратегическую сессию.
        flags.append("ARCHETYPE_AMBIGUOUS")
    return ARCH_MIXED, flags


def _line_balance(result: dict) -> int:
    """Баланс подвижных линий контура: старый Инь +1 (рост), старый Ян -1
    (перегрев). Равен дельте maturity_index при переходе к resulting."""
    balance = 0
    for line in result.get("lines", []):
        if line.get("state") == "old_yin":
            balance += 1
        elif line.get("state") == "old_yang":
            balance -= 1
    return balance


def lifecycle_progress(results: dict[str, dict]) -> dict:
    """Сколько контуров пройдено и чего не хватает до жизненного цикла компании.

    Принцип матрёшки: шесть базовых вопросов дают общую картину компании,
    контуры раскрывают её детали. Стадия компании берётся у контура-ограничения,
    поэтому нужны все четыре: по одному-двум это был бы частичный срез,
    выданный за системный диагноз.
    """
    from app.contours import CONTOURS

    passed = [k for k in CONTOUR_ORDER if results.get(k)]
    missing = [k for k in CONTOUR_ORDER if not results.get(k)]
    return {
        "passed": len(passed),
        "required": REQUIRED_CONTOURS,
        "passed_contours": passed,
        "missing_contours": missing,
        "missing_titles": [CONTOURS[k].title for k in missing if k in CONTOURS],
        "available": len(passed) >= REQUIRED_CONTOURS,
    }


def build_company_lifecycle(results: dict[str, dict], summary: dict | None) -> dict | None:
    """Главная точка входа.

    results: {ключ контура: снимок result, обогащённый lifecycle_stage и
    transition_lifecycle_stage из Strategy}. summary — результат
    build_summary() по тем же контурам. None — если пройдены не все 4 контура
    или сводная карта не построена.
    """
    known = {k: v for k, v in results.items() if k in CONTOUR_ORDER and v}
    if len(known) < REQUIRED_CONTOURS or not summary:
        return None

    quality_flags: list[str] = []

    # ── Точка: стадия контура-ограничения ────────────────────────────────
    constraint = summary.get("constraint")
    tied = summary.get("tied") or []
    stage = None
    if constraint:
        stage = _stage_of(known[constraint])
        if stage is None:
            quality_flags.append("STAGE_UNKNOWN")
    else:
        # Ничья не разрешается фиксированным порядком (см. contour_summary):
        # стадия остаётся неопределённой, наружу отдаётся список претендентов.
        quality_flags.append("CONSTRAINT_TIED")

    if not summary.get("gap_significant"):
        # Отрыв ограничения незначим — «точка» условна, опираться на вектор.
        quality_flags.append("GAP_NOT_SIGNIFICANT")

    # ── Вектор: переход стадий по каждому контуру ─────────────────────────
    vector = {}
    for key in CONTOUR_ORDER:
        r = known.get(key)
        if not r:
            continue
        to_raw = (r.get("transition_lifecycle_stage") or "").strip().lower()
        vector[key] = {
            "from": _stage_of(r),
            "to": to_raw if to_raw in KNOWN_STAGES else None,
            "moving_count": len(r.get("moving_lines") or []),
        }

    # ── Архетип ───────────────────────────────────────────────────────────
    stages = {k: _stage_of(v) for k, v in known.items()}
    archetype, arch_flags = classify_archetype(stages)
    for f in arch_flags:
        if f not in quality_flags:
            quality_flags.append(f)

    # ── Playbook: рамка (линии 5-6) + тактика из маршрута ограничения ─────
    tactics: list[dict] = []
    if constraint:
        r = known[constraint]
        tactics = build_route(r["lines"], r["combination_current"])
        # Названия линий отдаём с бэкенда: единственный источник — LINE_TITLES.
        for _st in tactics:
            _st["line_title"] = LINE_TITLES.get(
                _st.get("line_key"), _st.get("line_key"))
        if not tactics:
            # Ограничение без подвижных линий: система «застряла» в узком
            # месте без внутреннего запроса на изменение — работа начинается
            # со стратегической сессии, а не с маршрута.
            quality_flags.append("CONSTRAINT_STABLE")

    playbook = {
        "frame": ARCHETYPE_FRAMES[archetype],  # семантика линий 5-6
        "tactics": tactics,                    # фактические подвижные линии
        "tactics_source": constraint,
    }

    # ── Верификационный слой: расчётные агрегаты (без вердикта) ──────────
    maturity_sum = sum(k.get("maturity_index") or 0 for k in known.values())
    moving_total = sum(len(k.get("moving_lines") or []) for k in known.values())
    delta = sum(_line_balance(k) for k in known.values())

    if moving_total >= TURBULENCE_THRESHOLD:
        quality_flags.append("HIGH_TURBULENCE")
    if moving_total == 0:
        # Не аномалия, а валидное состояние (в т.ч. глубокий стабильный
        # упадок) — информативный флаг для консультанта.
        quality_flags.append("NO_INTERNAL_PRESSURE")
    if delta >= PRESSURE_THRESHOLD:
        quality_flags.append("RENEWAL_PRESSURE")
    elif delta <= -PRESSURE_THRESHOLD:
        quality_flags.append("OVERHEAT_RISK")

    return {
        "stage": stage,
        "constraint": constraint,
        "tied": tied,
        "gap_significant": bool(summary.get("gap_significant")),
        "vector": vector,
        "archetype": archetype,
        "archetype_title": ARCHETYPE_TITLES[archetype],
        "playbook": playbook,
        "verification": {
            "maturity_sum": maturity_sum,    # 0-24, позиция
            "moving_total": moving_total,    # 0-24, энергия перехода
            "delta": delta,                  # баланс роста/перегрева
        },
        "quality_flags": quality_flags,
    }
