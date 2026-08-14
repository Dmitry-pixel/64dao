# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — сервисный слой.

Всё, что требует БД: разрешение анкеты по отрасли, сохранение ответов,
запуск расчёта и запись снимка, композиционная сборка разбора.
Сама арифметика живёт в m3_scoring и остаётся чистой — сюда она приходит
готовыми словарями.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app import m3_portfolio as pf
from app import m3_scoring as sc
from app import m3_verdict as vd
from app.m3_config import DEFAULT_M3_CONFIG, industry_weights, read_m3_config
from app.m3_models import (
    M3Answer, M3ChecklistStep, M3Content, M3Hint, M3Item, M3Object,
    M3Portfolio, M3PortfolioResult, M3Result, M3Weight,
)

LINE_TITLES = {
    1: "Ресурсы и юнит-экономика",
    2: "Продукт и дифференциация",
    3: "Каналы и доля",
    4: "Спрос сегмента",
    5: "Структура рынка и маржа",
    6: "Макро и регулирование",
}

# Линии, которыми компания управляет сама. Деление то же, что у осей матрицы
# и у раздела 03: 1–3 конкурентная сила, 4–6 привлекательность рынка.
INTERNAL_LINES = (1, 2, 3)

DISCLAIMER_WEIGHTS = (
    "Отраслевые веса — экспертные априорные оценки, не эмпирические. "
    "Они задают начальную точку и подлежат пересмотру по мере накопления отчётов."
)
DISCLAIMER_HEXAGRAM = (
    "Номер гексаграммы — идентификатор конфигурации шести линий, а не отсылка "
    "к традиции. Название выводится для связи с Методами 1 и 2 и в трактовке "
    "не участвует."
)
DISCLAIMER_LINES = (
    "Соответствие линий факторам — конструктивное правило модели, а не "
    "свойство традиции. Линии 1–3 описывают то, что компания делает сама, "
    "линии 4–6 — то, во что она поставлена. Положение третьей линии "
    "используется как аналогия для фактора, соединяющего внутренний контур "
    "с рынком."
)
DISCLAIMER_HELD = (
    "Вердикты аллокации удержаны: сработал портфельный флаг качества данных. "
    "Диагноз и маршруты приведены, распределение ресурса — нет."
)
DISCLAIMER_LINE5 = (
    "Инь на линии 5 — не оценка вашей работы. Он означает, что рынок структурно "
    "не даёт зарабатывать: цена диктуется сверху, а вход дёшев."
)
DISCLAIMER_LINE4 = (
    "Очень высокий балл линии 4 не означает «всё отлично». Он означает, что "
    "текущий спрос выше устойчивого уровня, и метод предупреждает об откате."
)


class M3ServiceError(ValueError):
    """Ошибка сервисного слоя, разворачивается роутером в 4xx."""


# ── Конфиг ────────────────────────────────────────────────────────────────────
def get_config() -> dict:
    """Конфиг с оверрайдами из тома. Отдельная функция, чтобы тесты
    подменяли её одной строкой, а не трогали файловую систему."""
    return read_m3_config()


async def resolve_weights(db: AsyncSession, industry_id: int | None, config: dict) -> dict[str, int]:
    """
    Веса отрасли: сначала строка в m3_weights (её правит админка),
    иначе дефолт из конфига. Пустая таблица — рабочее состояние, а не ошибка:
    расчёт не должен падать до того, как выполнен сид.
    """
    if industry_id is not None:
        row = await db.scalar(select(M3Weight).where(M3Weight.industry_id == industry_id))
        if row:
            return {
                "L1": row.w_l1, "L2": row.w_l2, "L3": row.w_l3,
                "L4": row.w_l4, "L5": row.w_l5, "L6": row.w_l6,
            }
    return industry_weights(industry_id, config)


# ── Анкета ────────────────────────────────────────────────────────────────────
async def load_items(db: AsyncSession, industry_ids: set[int | None]) -> dict[str, M3Item]:
    """
    Активные пункты последней версии. Отраслевая версия замещает общую —
    тот же приём, что в Методе 2 для слоя common и контурных версий.

    Ключ результата — код пункта. Если для отрасли есть переопределение,
    в словарь попадает оно; иначе общий слой (industry_id IS NULL).
    """
    rows = (await db.execute(
        select(M3Item).where(M3Item.is_active.is_(True))
    )).scalars().all()

    wanted = {i for i in industry_ids if i is not None}
    best: dict[str, M3Item] = {}
    for it in rows:
        if it.industry_id is not None and it.industry_id not in wanted:
            continue
        cur = best.get(it.code)
        if cur is None:
            best[it.code] = it
            continue
        # Отраслевой слой сильнее общего; внутри слоя — старшая версия.
        cur_rank = (cur.industry_id is not None, cur.item_version)
        new_rank = (it.industry_id is not None, it.item_version)
        if new_rank > cur_rank:
            best[it.code] = it
    return best


async def load_hints(db: AsyncSession, industry_ids: set[int]) -> dict[tuple[int, str], str]:
    if not industry_ids:
        return {}
    rows = (await db.execute(
        select(M3Hint).where(M3Hint.industry_id.in_(industry_ids))
    )).scalars().all()
    return {(h.industry_id, h.item_code): h.text for h in rows}


async def build_questionnaire(db: AsyncSession, portfolio: M3Portfolio) -> dict:
    """
    Анкета, разрешённая по отрасли, с подсказками уровня 2.

    Арбитры отдаются отдельным списком и на фронте показываются только по
    ответу /arbiter-required: адаптивность в том и состоит, что пункт
    появляется при неоднозначности, а не заранее.
    """
    objects = list(portfolio.objects)
    industries = {portfolio.industry_id} | {o.industry_id for o in objects}
    items = await load_items(db, industries)
    hints = await load_hints(db, {i for i in industries if i is not None})

    # Пропуск блока Р* привязан к ЧИСЛУ НАПРАВЛЕНИЙ, РАВНОМУ ЕДИНИЦЕ, а не
    # к флагу reduced: при двух направлениях reduced тоже истинен, но уровни
    # портфеля и направления уже различимы, и шаг нужен. При одном они
    # совпадают, и шесть пунктов Р* переспрашивают блок Р. Расчёт не меняется:
    # resolve_line_items берёт ответ Р для линий 5 и 6, когда Р* нет.
    single_object = len(objects) == 1

    # Подсказка привязана к отрасли портфеля: у направлений отрасли могут
    # различаться, и одну подсказку под общим пунктом выбрать нельзя.
    def hint_for(code: str) -> str | None:
        base = code.rstrip(sc.OVERRIDE)
        if portfolio.industry_id is None:
            return None
        return hints.get((portfolio.industry_id, base))

    def pack(codes: list[str], arbiter: bool = False) -> list[dict]:
        out = []
        for code in codes:
            it = items.get(code)
            if it is None:
                continue
            out.append({
                "id": it.id, "block": it.block, "code": it.code, "line": it.line,
                "text": it.text, "is_reverse": it.is_reverse,
                "item_version": it.item_version,
                "hint": hint_for(code), "is_arbiter": arbiter,
            })
        return out

    market = [f"{sc.BLOCK_MARKET}{i}" for i in range(1, 7)]
    override = [f"{c}{sc.OVERRIDE}" for c in market]
    obj_codes = [f"{sc.BLOCK_OBJECT}{i}" for i in range(1, 9)]
    arb_codes = [f"{sc.BLOCK_ARBITER}{i}" for i in range(1, 5)]

    return {
        "portfolio_id": portfolio.id,
        "market_items": pack(market),
        "object_items": pack(obj_codes),
        "override_items": [] if single_object else pack(override),
        "arbiter_items": pack(arb_codes, arbiter=True),
        "objects": objects,
    }


# ── Ответы ────────────────────────────────────────────────────────────────────
async def save_answers(
    db: AsyncSession,
    portfolio: M3Portfolio,
    incoming: list[dict],
) -> int:
    """
    Инкрементальное сохранение. Возвращает число записанных ответов.

    Пункт блока Р сохраняется с object_id IS NULL. Пункт блока Р* — с
    object_id направления: переопределение живёт на направлении, а не
    на портфеле.
    """
    industries = {portfolio.industry_id} | {o.industry_id for o in portfolio.objects}
    items = await load_items(db, industries)
    obj_ids = {o.id for o in portfolio.objects}

    existing = {
        (a.object_id, a.item_id): a
        for a in (await db.execute(
            select(M3Answer).where(M3Answer.portfolio_id == portfolio.id)
        )).scalars().all()
    }

    written = 0
    for row in incoming:
        code = row["item_code"]
        item = items.get(code)
        if item is None:
            raise M3ServiceError(f"Пункт {code} не найден в активной анкете")

        object_id = row.get("object_id")
        is_portfolio_level = code in sc.MARKET_ITEM_LINE
        if is_portfolio_level:
            if object_id is not None:
                raise M3ServiceError(
                    f"Пункт {code} заполняется один раз на портфель, "
                    "направление указывать не нужно"
                )
        else:
            if object_id is None:
                raise M3ServiceError(f"Для пункта {code} нужно указать направление")
            if object_id not in obj_ids:
                raise M3ServiceError("Направление не принадлежит этому портфелю")

        key = (object_id, item.id)
        if key in existing:
            existing[key].value = row.get("value")
        else:
            db.add(M3Answer(
                portfolio_id=portfolio.id, object_id=object_id,
                item_id=item.id, item_code=code, value=row.get("value"),
            ))
        written += 1

    await db.flush()
    if portfolio.status == "draft":
        portfolio.status = "filled"
    return written


async def collect_answers(db: AsyncSession, portfolio: M3Portfolio) -> tuple[dict, dict]:
    """(ответы портфеля, ответы по направлениям) в виде словарей код -> значение."""
    rows = (await db.execute(
        select(M3Answer).where(M3Answer.portfolio_id == portfolio.id)
    )).scalars().all()

    portfolio_answers: dict[str, int | None] = {}
    object_answers: dict[uuid.UUID, dict[str, int | None]] = {
        o.id: {} for o in portfolio.objects
    }
    for a in rows:
        if a.object_id is None:
            portfolio_answers[a.item_code] = a.value
        elif a.object_id in object_answers:
            object_answers[a.object_id][a.item_code] = a.value
    return portfolio_answers, object_answers


async def arbiter_required(db: AsyncSession, portfolio: M3Portfolio) -> list[dict]:
    """По каким линиям каждого направления нужен адаптивный пункт."""
    config = get_config()
    portfolio_answers, object_answers = await collect_answers(db, portfolio)
    industries = {portfolio.industry_id} | {o.industry_id for o in portfolio.objects}
    items = await load_items(db, industries)

    out = []
    for o in portfolio.objects:
        lines = sc.arbiter_required(portfolio_answers, object_answers.get(o.id, {}), config)
        needed = []
        for line in lines:
            code = sc.ARBITER_BY_LINE.get(line)
            it = items.get(code) if code else None
            if it is None:
                continue
            needed.append({
                "id": it.id, "block": it.block, "code": it.code, "line": it.line,
                "text": it.text, "is_reverse": it.is_reverse,
                "item_version": it.item_version, "hint": None, "is_arbiter": True,
            })
        out.append({
            "object_id": o.id, "position": o.position, "name": o.name,
            "lines": lines, "items": needed,
        })
    return out


# ── Расчёт ────────────────────────────────────────────────────────────────────
async def calculate(db: AsyncSession, portfolio: M3Portfolio) -> dict:
    """
    Полный расчёт портфеля и запись снимка в m3_results / m3_portfolio_results.
    Повторный вызов перезаписывает снимок: расчёт детерминирован от ответов.
    """
    config = get_config()
    objects = list(portfolio.objects)
    # Границы из config, а не из DEFAULT_M3_CONFIG: раньше проверка читала
    # дефолты, а сообщение — переопределение из админки, и при правке
    # порога текст ошибки расходился с самой проверкой.
    if not config["objects_min"] <= len(objects) <= config["objects_max"]:
        raise M3ServiceError(
            f"Направлений в портфеле: {len(objects)}. Допустимо от "
            f"{config['objects_min']} до {config['objects_max']}."
        )

    portfolio_answers, object_answers = await collect_answers(db, portfolio)
    industries = {portfolio.industry_id} | {o.industry_id for o in objects}
    items = await load_items(db, industries)

    payload_objects = []
    item_versions: dict[uuid.UUID, dict] = {}
    for o in objects:
        answers = object_answers.get(o.id, {})
        weights = await resolve_weights(db, o.industry_id or portfolio.industry_id, config)
        payload_objects.append({
            "id": o.id, "position": o.position, "name": o.name,
            "revenue_dynamics": float(o.revenue_dynamics) if o.revenue_dynamics is not None else None,
            "revenue_share": float(o.revenue_share) if o.revenue_share is not None else None,
            "profitability": o.profitability,
            "industry_id": o.industry_id or portfolio.industry_id,
            "weights": weights,
            "answers": answers,
        })
        used = set(answers) | set(portfolio_answers)
        item_versions[o.id] = {
            code: items[code].item_version for code in sorted(used) if code in items
        }

    try:
        calc = sc.calculate({
            "industry_id": portfolio.industry_id,
            "answers": portfolio_answers,
            "objects": payload_objects,
            "owner_ranks": portfolio.owner_ranks,
        }, config)
    except sc.M3ScoringError as e:
        raise M3ServiceError(str(e)) from e

    await db.execute(delete(M3Result).where(M3Result.portfolio_id == portfolio.id))
    await db.execute(
        delete(M3PortfolioResult).where(M3PortfolioResult.portfolio_id == portfolio.id)
    )

    for r in calc["objects"]:
        db.add(M3Result(
            portfolio_id=portfolio.id, object_id=r["object_id"],
            l1=r["scores"]["l1"], l2=r["scores"]["l2"], l3=r["scores"]["l3"],
            l4=r["scores"]["l4"], l5=r["scores"]["l5"], l6=r["scores"]["l6"],
            symbols=r["symbols"], mobility=r["mobility"], weights=r["weights"],
            cell_strength=r["cell_strength"], cell_attract=r["cell_attract"],
            coord_strength=r["coord_strength"], coord_attract=r["coord_attract"],
            current_hex=r["current_hex"],
            target_hex=r["target_hex"], target_lines=r["target_lines"] or None,
            risk_hex=r["risk_hex"], risk_lines=r["risk_lines"] or None,
            v_index=r["v_index"], z_index=r["z_index"],
            v_rank=r["v_rank"], z_rank=r["z_rank"],
            weak_line=r["weak_line"], strong_line=r["strong_line"],
            tensions=r["tensions"], flags=r["flags"],
            item_versions={str(k): v for k, v in item_versions[r["object_id"]].items()},
        ))

    p = calc["portfolio"]
    db.add(M3PortfolioResult(
        portfolio_id=portfolio.id,
        sum_positions=p["sum_positions"], turbulence=p["turbulence"],
        delta=p["delta"], distinct_cells=p["distinct_cells"],
        spearman=p["spearman"], flags=p["flags"],
        verdicts_held=p["verdicts_held"],
        reduced=p["reduced"],
    ))

    portfolio.status = "calculated"
    from sqlalchemy import func as sa_func
    portfolio.calculated_at = sa_func.now()
    await db.flush()

    await rebuild_checklist(db, portfolio, calc)
    return calc


# ── Чек-лист ──────────────────────────────────────────────────────────────────
async def rebuild_checklist(db: AsyncSession, portfolio: M3Portfolio, calc: dict) -> None:
    """
    Плоский чек-лист по результатам расчёта. Волны расставляются позже,
    решением по trade-off: до него все шаги в первой волне.

    Старый Инь даёт маршрутный шаг — работу над назревшей слабостью.
    Старый Ян даёт шаг удержания: цель там остаться на месте, а не
    переместиться, поэтому промежуточных состояний у него нет.

    Глагол зависит от оси. Линии 1–3 описывают то, что компания делает сама:
    их прорабатывают и защищают. Линии 4–6 — то, во что она поставлена;
    их не меняют. Пока формулировка была общей, отчёт предлагал «проработать
    назревшее по линии 6 — макро и регулирование, требует бюджета», то есть
    выделить деньги на проработку регулирования. Внешний фактор меняют
    не им самим, а своей зависимостью от него.

    Бюджет у внешнего «назревшего» сохраняется: сменить каналы или сегмент
    стоит денег, и это осмысленная трата. У внешнего перегрева бюджета нет —
    действие там состоит в том, чтобы перестать рассчитывать на текущий
    уровень (та же мысль, что в DISCLAIMER_LINE4).
    """
    await db.execute(delete(M3ChecklistStep).where(M3ChecklistStep.portfolio_id == portfolio.id))
    by_id = {o.id: o for o in portfolio.objects}

    for r in calc["objects"]:
        obj = by_id.get(r["object_id"])
        if obj is None:
            continue
        for line in r["target_lines"]:
            verb = ("проработать назревшее" if line in INTERNAL_LINES
                    else "снизить зависимость")
            db.add(M3ChecklistStep(
                portfolio_id=portfolio.id, object_id=obj.id, line=line,
                step_type="route", wave=1, needs_budget=True,
                step_text=f"{obj.name}: {verb} по линии {line} — "
                          f"{LINE_TITLES[line].lower()}",
            ))
        for line in r["risk_lines"]:
            internal = line in INTERNAL_LINES
            verb = ("защитить достигнутое" if internal
                    else "не закладываться на текущий уровень")
            db.add(M3ChecklistStep(
                portfolio_id=portfolio.id, object_id=obj.id, line=line,
                step_type="hold", wave=1, needs_budget=False,
                step_text=f"{obj.name}: {verb} по линии {line} — "
                          f"{LINE_TITLES[line].lower()}",
            ))
        if not r["target_lines"] and not r["risk_lines"]:
            db.add(M3ChecklistStep(
                portfolio_id=portfolio.id, object_id=obj.id, line=None,
                step_type="prep", wave=1, needs_budget=False,
                step_text=f"{obj.name}: ограничение стабильно, подвижных линий нет — "
                          "пересчитать юнит-экономику перед следующим решением",
            ))
    await db.flush()


# ── Разбор ────────────────────────────────────────────────────────────────────
async def load_content(db: AsyncSession) -> dict[tuple[str, str], M3Content]:
    rows = (await db.execute(
        select(M3Content).where(M3Content.is_active.is_(True))
    )).scalars().all()
    # Отраслевое переопределение сильнее общего слоя, как в анкете.
    best: dict[tuple[str, str], M3Content] = {}
    for c in rows:
        k = (c.kind, c.key)
        if k not in best or (c.industry_id is not None and best[k].industry_id is None):
            best[k] = c
    return best


def _zone_block(result: dict, content: dict):
    """
    Блок зоны с откатом. В сокращённом режиме сначала ищется zone_reduced,
    и только при его отсутствии берётся общий zone.

    Откат, а не обязательная пара: две зоны из девяти в одиночном отчёте
    лгут прямым текстом («источник денег для остального портфеля»,
    «останется одним из»), остальные семь читаются нормально. Заводить им
    строки-дубликаты значит завести семь мест, где тексты разойдутся.

    Тот же приём, что у контурного переопределения в fin_content: запись
    существует только там, где она что-то меняет.
    """
    key = result["cell_key"]
    if result.get("reduced"):
        override = content.get(("zone_reduced", key))
        if override is not None:
            return override
    return content.get(("zone", key))


def compose_narrative(result: dict, content: dict) -> list[dict]:
    """
    Композиционная сборка вместо 64 уникальных текстов:
    зона + ведущая слабая + ведущая сильная + до трёх напряжений,
    типичная ошибка из блока зоны замыкает разбор.

    Отсутствующий блок пропускается молча: контентная работа идёт
    параллельно разработке, и незаполненный текст не должен ронять отчёт.

    Наружу зона отдаётся с kind 'zone' в обоих режимах. На этом значении
    завязаны обе вёрстки: m3_pdf печатает по нему баннер «Типичная ошибка»,
    веб — свой блок. Режим меняет текст, а не структуру отчёта.
    """
    out = []

    zone = _zone_block(result, content)
    if zone is not None:
        out.append({
            "kind": "zone", "key": result["cell_key"],
            "title": zone.title, "body": zone.body, "mistake": zone.mistake,
        })

    keys = [
        ("weak_line", f"weak_L{result['weak_line']}"),
        ("strong_line", f"strong_L{result['strong_line']}"),
    ] + [("tension", t) for t in result["tensions"]]

    for kind, key in keys:
        block = content.get((kind, key))
        if block is None:
            continue
        out.append({
            "kind": kind, "key": key, "title": block.title,
            "body": block.body, "mistake": None,
        })
    return out


DISCLAIMER_REDUCED = (
    "Диагностика проведена по {what}. Портфельный слой не рассчитан: профиль "
    "линий по портфелю, сравнение с порядком приоритетов и карта долей выручки "
    "определены только при сравнении направлений. Позиция в матрице, разбор "
    "линий и маршрут перехода действительны."
)


def disclaimers(calc: dict) -> list[str]:
    out = [DISCLAIMER_WEIGHTS, DISCLAIMER_HEXAGRAM, DISCLAIMER_LINES]
    if calc["portfolio"].get("reduced"):
        # Первой строкой: она объясняет, почему в отчёте нет половины разделов.
        n = calc["portfolio"]["objects"]
        out.insert(0, DISCLAIMER_REDUCED.format(
            what="одному направлению" if n == 1 else "двум направлениям"))
    if calc["portfolio"]["verdicts_held"]:
        out.insert(0, DISCLAIMER_HELD)
    if any(r["symbols"][4] == sc.YIN for r in calc["objects"]):
        out.append(DISCLAIMER_LINE5)
    if any(r["mobility"].get("4") == sc.OLD_YANG for r in calc["objects"]):
        out.append(DISCLAIMER_LINE4)
    return out


def enrich_result(item: dict, share: float | None,
                  reduced: bool = False) -> dict:
    """
    Дописывает в результат направления вердикт, траекторию и причину места
    в очереди исполнения. Мутирует переданный словарь и возвращает его же.

    Отдельная функция, а не три строки внутри build_report: тест сверяет
    вердикт из API с вердиктом в PDF, и для этого ему нужен вход без БД.

    Всё три величины — производные от снимка, а не контент. Их считает
    m3_verdict, и те же функции на том же словаре вызывает m3_pdf.
    """
    # Признак ставится на сам результат, а не прокидывается параметром:
    # verdict_for зовут ещё два места в m3_pdf на тех же словарях, и так
    # переопределение доезжает до них без правки сигнатур.
    item["reduced"] = reduced
    item["verdict"] = vd.verdict_for(item)
    item["trajectory"] = {
        "target": vd.transition(item, "target"),
        "risk": vd.transition(item, "risk"),
    }
    item["execution_reason"] = vd.execution_reason(item, share)
    return item


def _rank_comparison_payload(results: list[dict], summary: dict) -> dict | None:
    """
    Сравнение порядка собственника с расчётным плюс готовое прочтение.

    Текст собирается здесь, а не в вебе: у формулировки уже есть один
    потребитель в PDF, и третья её копия на TypeScript разошлась бы —
    ровно так, как это вышло с cellBreakdownText.
    """
    cmp = pf.rank_comparison(results, summary.get("owner_ranks"))
    if not cmp:
        return None
    return {**cmp, "reading": pf.rank_comparison_reading(cmp, summary.get("spearman"))}


async def build_report(db: AsyncSession, portfolio: M3Portfolio) -> dict:
    """
    Отчёт собирается из сохранённого снимка, а не пересчитывается: выданный
    отчёт не должен меняться от правки формулировки пункта или веса.
    """
    results = (await db.execute(
        select(M3Result).where(M3Result.portfolio_id == portfolio.id)
    )).scalars().all()
    if not results:
        raise M3ServiceError("Портфель ещё не рассчитан")

    summary = await db.scalar(
        select(M3PortfolioResult).where(M3PortfolioResult.portfolio_id == portfolio.id)
    )
    content = await load_content(db)
    by_id = {o.id: o for o in portfolio.objects}
    # Ответы нужны ради колонки «Рынок» в разделе 00: сколько пунктов рынка
    # направление переопределило своими. Снимок расчёта этого не хранит —
    # он хранит результат, а не источник каждого балла.
    _, object_answers = await collect_answers(db, portfolio)

    packed = []
    for r in results:
        o = by_id.get(r.object_id)
        if o is None:
            continue
        cell_key = f"{r.cell_strength}_{r.cell_attract}"
        code = r.symbols
        _, hex_name = sc.hexagram_by_code(code)
        item = {
            "object_id": r.object_id, "name": o.name, "position": o.position,
            "scores": {f"l{i}": float(getattr(r, f"l{i}")) for i in range(1, 7)},
            "symbols": code, "mobility": r.mobility or {},
            # Веса нужны не только выводу ячейки: m3_verdict.transition
            # пересчитывает по ним ячейки перехода. Без них переход
            # не строится вовсе — тихо, для всех направлений сразу.
            "weights": r.weights,
            "cell_strength": r.cell_strength, "cell_attract": r.cell_attract,
            "cell_key": cell_key,
            # Формулировка одна на оба отчёта — из m3_verdict, а не из
            # CELL_LABEL_RU: там осталось старое «низкая конкурентная среда»,
            # которое называет не ту сущность.
            "cell_label": vd.cell_label(r.cell_strength, r.cell_attract),
            "coord_strength": float(r.coord_strength),
            "coord_attract": float(r.coord_attract),
            "current_hex": r.current_hex, "current_name": hex_name,
            "target_hex": r.target_hex, "target_lines": list(r.target_lines or []),
            "risk_hex": r.risk_hex, "risk_lines": list(r.risk_lines or []),
            "v_index": float(r.v_index), "z_index": float(r.z_index),
            "v_rank": r.v_rank, "z_rank": r.z_rank,
            "weak_line": r.weak_line, "strong_line": r.strong_line,
            "tensions": list(r.tensions or []), "flags": list(r.flags or []),
            "market_overrides": sc.market_override_count(
                object_answers.get(r.object_id, {})),
        }
        # Готовая подпись, а не только число: копия формулировки на TypeScript
        # разошлась бы с питоновской, а поймать это нечем — тест паритета
        # видит только сторону PDF.
        item["market_label"] = vd.market_label(item["market_overrides"])
        if r.weights:
            # Вывод ячейки для карточки (§10.1a). Считается из снимка, а не
            # заново из анкеты: symbols и weights уже зафиксированы.
            #
            # Уровень берётся из снимка, а не из свежего расчёта: пороги
            # лежат в конфиге и могут смениться после того, как отчёт был
            # рассчитан. Расходиться должна сумма с порогом, а не отчёт
            # сам с собой.
            breakdown = {}
            for axis, level in (("strength", r.cell_strength),
                                ("attract", r.cell_attract)):
                d = sc.cell_detail(code, axis, r.weights)
                d["level"] = level
                # Строка собирается здесь по той же причине, что и market_label:
                # веб печатает готовое, своей копии формулировки не держит.
                d["text"] = vd.cell_breakdown_text(axis, d)
                breakdown[axis] = d
            item["cell_breakdown"] = breakdown
        enrich_result(
            item,
            float(o.revenue_share) if o.revenue_share is not None else None,
            bool(summary and summary.reduced),
        )
        packed.append({"result": item, "narrative": compose_narrative(item, content)})

    # Разделы 02 и 04 отчёта: разбор идёт в порядке ранга V, а решение
    # о распределении показывает два списка сразу — их расхождение и есть
    # результат, а не дефект.
    packed.sort(key=lambda x: x["result"]["v_rank"])
    investment = [x["result"]["object_id"] for x in packed]
    execution = [
        x["result"]["object_id"]
        for x in sorted(packed, key=lambda x: x["result"]["z_rank"])
    ]

    calc_like = {
        "objects": [x["result"] for x in packed],
        "portfolio": {"verdicts_held": bool(summary and summary.verdicts_held)},
    }

    summary_out = {
        "objects": len(packed),
        "sum_positions": summary.sum_positions if summary else 0,
        "sum_positions_max": 6 * len(packed),
        "turbulence": summary.turbulence if summary else 0,
        "delta": summary.delta if summary else 0,
        "distinct_cells": summary.distinct_cells if summary else 0,
        "spearman": float(summary.spearman) if summary and summary.spearman is not None else None,
        # Порядок собственника нужен разделу расхождения. Раньше он влиял на
        # отчёт (через флаг), но в отчёт не попадал — увидеть, что именно
        # назвали, было невозможно.
        "owner_ranks": list(portfolio.owner_ranks or []) or None,
        "flags": list(summary.flags or []) if summary else [],
        "verdicts_held": bool(summary and summary.verdicts_held),
        "reduced": bool(summary and summary.reduced),
    }

    # Раздел 03. Ограничения компании выводятся из снимка строгим большинством,
    # а не берутся из таблицы контента: линия, слабая у большинства направлений,
    # перестаёт быть свойством продукта и становится свойством компании.
    results_only = [x["result"] for x in packed]
    if summary_out["reduced"]:
        # Ниже порога сравнения портфельный разбор не считается. Функции его
        # переживают, но врут: ограничение компании выводится строгим
        # большинством направлений, а большинство из одного направления —
        # это само направление, и свойство продукта выдаётся за свойство
        # компании. Подавление стоит здесь, а не в рендерах: правило одно,
        # отчёта два.
        analysis = {
            "yin_table": [], "constraints": [], "metrics": [],
            "tact_note": None, "rank_comparison": None,
        }
    else:
        analysis = {
            "yin_table": pf.yin_table(results_only),
            "constraints": pf.constraints(results_only),
            "metrics": pf.metric_readings(summary_out),
            "tact_note": pf.tact_note(results_only, summary_out),
            "rank_comparison": _rank_comparison_payload(results_only, summary_out),
        }

    return {
        "portfolio": portfolio,
        "summary": summary_out,
        "objects": packed,
        "investment_order": investment,
        "execution_order": execution,
        "analysis": analysis,
        "disclaimers": disclaimers(calc_like),
    }
