# -*- coding: utf-8 -*-
"""
Метод 4 «Алмазное колесо» — расчёт.

Чистые функции без базы: на вход контент (вопросы с вариантами, правила,
карточки рекомендаций), ответы и профиль компании; на выход — снимок
результата. Базу и API подключает слой прогонов, здесь их нет намеренно:
расчёт должен одинаково работать в тесте, в пересчёте и в отчёте.

Что считается:
  1. Балл каждого из 10 модулей (0–100) и его состояние: низкий / средний / высокий.
  2. Три главных разрыва — для экспресса.
  3. Системное ограничение — модуль с низким баллом, от которого зависят
     сильные модули. Не самый низкий балл.
  4. Причины против следствия: модули 1–9 против модуля 10 «Финансы».
  5. Сработавшие правила противоречий и правила, которые нельзя проверить.
  6. Индекс достоверности: «не знаю», социальная желательность, контрольные пары.
  7. Коэффициент сопротивления изменениям (1,0–2,0).
  8. Очередь действий: рекомендации по приоритету.

Методические параметры собраны в CONFIG и помечены: это калибровка, а не
закон. После первых диагностик их придётся сдвинуть по фактическому
распределению ответов — поэтому они в одном месте и с объяснением.
"""
from __future__ import annotations

from dataclasses import dataclass, field

CALC_VERSION = "m4-1.0"

# ── Калибровка ────────────────────────────────────────────────────────────────
CONFIG = {
    # Границы состояний модуля — те же, что в cards.json (state_thresholds).
    "state_low_below": 40,
    "state_high_from": 70,
    # Факт весит больше самооценки: «сколько SKU» надёжнее «насколько вы
    # сфокусированы». Множитель к весу вопроса.
    "fact_weight_multiplier": 1.5,
    # Причины против следствия: расхождение, начиная с которого случай
    # считается несогласованным, и уровень «оба низкие».
    "cause_effect_gap": 25,
    "cause_effect_both_low": 50,
    # Индекс достоверности (modules.json → confidence_index).
    "unknown_max_penalty": 40,
    "unknown_full_penalty_share": 0.5,   # при 50% «не знаю» штраф полный
    # Три штрафа ограничены 40/30/30, и одними «не знаю» индекс не опустить
    # ниже 60. Поэтому отдельное правило: половина ответов «не знаю» —
    # достоверность низкая, какими бы ни были остальные компоненты.
    "unknown_force_low_share": 0.5,
    "social_max_penalty": 30,
    "social_trigger_share": 0.70,        # >70% оценок в верхней трети
    "social_top_third": 67,
    "social_fact_gap": 20,               # факты «не подтверждают», если их доля ниже на 20 п.
    "pair_penalty_each": 10,
    "pair_max_penalty": 30,
    "pair_mismatch_gap": 60,             # расхождение нормированных ответов пары
    "confidence_high_from": 75,
    "confidence_medium_from": 50,
    # «Не знаю» на три и более фактических вопроса модуля — диагноз:
    # в компании нет учёта по этому направлению.
    "no_accounting_unknown_facts": 3,
    # Сопротивление изменениям (README, раздел «Сопротивление изменениям»).
    "resistance_q_resourcing": ("M05-Q13", "on_top", 0.5),
    "resistance_q_reversals": ("M05-Q14", "yes", 0.5),
}

# Граф зависимостей: ребро A → B — слабость в A ограничивает отдачу от B.
# Это логика метода, а не текст: в админке не правится. Совпадение с
# content/m4/modules.json проверяет тест.
EDGES: list[tuple[int, int, int]] = [
    (2, 3, 3), (2, 4, 3), (2, 6, 2), (2, 7, 2), (3, 4, 3), (3, 9, 3), (4, 9, 2),
    (4, 10, 3), (5, 4, 2), (5, 6, 3), (5, 8, 3), (5, 9, 2), (6, 9, 2), (6, 10, 3),
    (7, 8, 3), (7, 10, 2), (8, 10, 2), (9, 10, 3), (1, 7, 1), (1, 10, 2),
]
EFFECT_MODULE = 10
MODULES = range(1, 11)

UNKNOWN = "unknown"


# ── Входные данные ────────────────────────────────────────────────────────────
@dataclass
class Question:
    code: str
    module_code: int
    type: str
    weight: int = 1
    is_fact: bool = False
    tier: str = "u1"
    reverse: bool = False
    score_neutral: bool = False
    score_excluded: bool = False
    threshold_based: bool = False
    unknown_score: int | None = None
    unknown_confidence_penalty: int = 1
    control_pair: str | None = None
    applies_when: dict | None = None
    metric_code: str | None = None
    min_value: int | None = None
    max_value: int | None = None
    options: dict[str, int | None] = field(default_factory=dict)   # value → балл


@dataclass
class Answer:
    value: str | None = None          # значение варианта или "unknown"
    number: float | None = None       # для number / money

    @property
    def unknown(self) -> bool:
        return self.value == UNKNOWN


@dataclass
class Rule:
    code: str
    severity: str
    conditions: dict


@dataclass
class Recommendation:
    key: str                          # m01_low … / cr_CR-01 …
    effect: int
    speed_weeks: int
    cost: int
    module_code: int | None = None
    rule_code: str | None = None


# Универсальные пороги (thresholds-decision.json): защитимы в любой отрасли.
THRESHOLDS = {
    "top_client_share": 30,
    "dso_days": 60,
    "top_product_revenue_share": 50,
}


# ── Загрузка из контента ──────────────────────────────────────────────────────
def _g(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def question_from(o) -> Question:
    """Строка m4_questions (ORM-объект или словарь из seed) → Question.
    Выключенные в админке вопросы вызывающий отсеивает сам."""
    opts = _g(o, "options") or []
    return Question(
        code=_g(o, "code"), module_code=_g(o, "module_code"), type=_g(o, "type"),
        weight=_g(o, "weight", 1), is_fact=bool(_g(o, "is_fact")), tier=_g(o, "tier", "u1"),
        reverse=bool(_g(o, "reverse")), score_neutral=bool(_g(o, "score_neutral")),
        score_excluded=bool(_g(o, "score_excluded")), threshold_based=bool(_g(o, "threshold_based")),
        unknown_score=_g(o, "unknown_score"),
        unknown_confidence_penalty=_g(o, "unknown_confidence_penalty", 1),
        control_pair=_g(o, "control_pair"), applies_when=_g(o, "applies_when"),
        metric_code=_g(o, "metric_code"), min_value=_g(o, "min_value"), max_value=_g(o, "max_value"),
        options={_g(x, "value"): _g(x, "score") for x in opts},
    )


def rule_from(o) -> Rule:
    return Rule(code=_g(o, "code"), severity=_g(o, "severity"), conditions=_g(o, "conditions"))


def recommendation_from(o) -> Recommendation | None:
    """Карточка kind=recommendation → Recommendation; прочие карточки — None."""
    if _g(o, "kind") != "recommendation":
        return None
    return Recommendation(
        key=_g(o, "key"), effect=_g(o, "effect"), speed_weeks=_g(o, "speed_weeks"), cost=_g(o, "cost"),
        module_code=_g(o, "module_code"), rule_code=_g(o, "rule_code"),
    )


# ── Балл вопроса ──────────────────────────────────────────────────────────────
def question_score(q: Question, a: Answer | None) -> float | None:
    """Балл ответа 0–100 или None, если ответ в балл не идёт.

    Числа сообщаются как факты и в балл не идут — кроме трёх вопросов с
    универсальным порогом: там превышение порога само по себе диагноз.
    «Не знаю» в балл идёт только у вопросов, где задан unknown_score.
    """
    if a is None or q.score_neutral or q.score_excluded:
        return None
    if a.unknown:
        return None if q.unknown_score is None else float(q.unknown_score)
    if q.type in ("number", "money"):
        if not q.threshold_based or a.number is None or q.metric_code not in THRESHOLDS:
            return None
        return 100.0 if a.number <= THRESHOLDS[q.metric_code] else 0.0
    raw = q.options.get(a.value or "")
    if raw is None:
        return None
    return float(100 - raw if q.reverse else raw)


_CMP = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b, "<": lambda a, b: a < b}


def _matches(val, a: Answer | None, cond) -> bool:
    """Три формы условия в контенте: список значений, одно значение,
    сравнение с числом ('>1')."""
    if isinstance(cond, list):
        return val in cond
    if isinstance(cond, str):
        for op in (">=", "<=", ">", "<"):
            if cond.startswith(op):
                num = a.number if a else None
                return num is not None and _CMP[op](num, float(cond[len(op):]))
    return val == cond


def applies(q: Question, answers: dict[str, Answer], profile: dict) -> bool:
    """Условие показа: {"M01-Q09": ["yes"]}, {"M02-Q04": "yes"}, {"M02-Q10": ">1"}
    или {"profile.revenue_model": [...]}. Пока условие не выполнено, вопрос не
    задаётся и в расчёте не участвует."""
    for ref, cond in (q.applies_when or {}).items():
        if ref.startswith("profile."):
            if not _matches(profile.get(ref.split(".", 1)[1]), None, cond):
                return False
            continue
        a = answers.get(ref)
        if not _matches(a.value if a else None, a, cond):
            return False
    return True


def state_of(score: float | None) -> str | None:
    if score is None:
        return None
    if score < CONFIG["state_low_below"]:
        return "low"
    if score >= CONFIG["state_high_from"]:
        return "high"
    return "mid"


# ── Правила противоречий ──────────────────────────────────────────────────────
class _Unknown(Exception):
    """Условие нельзя проверить: нет ответа или ответ «не знаю»."""


def _operand(qcode: str, answers: dict[str, Answer], questions: dict[str, Question]):
    a = answers.get(qcode)
    if a is None or a.unknown:
        raise _Unknown(qcode)
    q = questions.get(qcode)
    if q is not None and q.type in ("number", "money"):
        if a.number is None:
            raise _Unknown(qcode)
        return a.number
    return a.value


def _cond(node: dict, answers, questions) -> bool:
    if "all" in node:
        return _all(node["all"], answers, questions)
    if "any" in node:
        return _any(node["any"], answers, questions)
    left = _operand(node["q"], answers, questions)
    op, value = node["op"], node.get("value")
    if op == "eq":
        return left == value
    if op == "in":
        return left in value
    if op == "gt_question":
        right = _operand(value, answers, questions)
        return left > right + node.get("margin", 0)
    left = float(left)
    return {"lt": left < value, "lte": left <= value, "gt": left > value, "gte": left >= value}[op]


def _all(items, answers, questions) -> bool:
    unknown = False
    for it in items:
        try:
            if not _cond(it, answers, questions):
                return False          # одно ложное — правило точно не сработало
        except _Unknown:
            unknown = True
    if unknown:
        raise _Unknown("all")
    return True


def _any(items, answers, questions) -> bool:
    unknown = False
    for it in items:
        try:
            if _cond(it, answers, questions):
                return True           # одно истинное — достаточно
        except _Unknown:
            unknown = True
    if unknown:
        raise _Unknown("any")
    return False


def evaluate_rule(rule: Rule, answers, questions) -> str:
    """'fired' | 'clear' | 'unverified' — последнее, если исход зависит от
    вопроса без ответа. Такое правило не выдаётся ни как сработавшее, ни как
    отсутствующее: отчёт помечает его непроверенным."""
    try:
        return "fired" if _cond(rule.conditions, answers, questions) else "clear"
    except _Unknown:
        return "unverified"


# ── Контрольные пары ──────────────────────────────────────────────────────────
def _pair_norm(q: Question, a: Answer | None) -> float | None:
    """Ответ, приведённый к шкале 0–100 в «хорошую» сторону. Для числа
    в процентах (0–100) — само число; для прочих чисел — факт знания:
    назвал число — 100."""
    if a is None or a.unknown:
        return None
    if q.type in ("number", "money"):
        if a.number is None:
            return None
        if q.min_value == 0 and q.max_value == 100:
            return float(a.number)
        return 100.0
    raw = q.options.get(a.value or "")
    if raw is None:
        return None
    return float(100 - raw if q.reverse else raw)


def control_pairs(questions: dict[str, Question], answers: dict[str, Answer]) -> list[dict]:
    seen, out = set(), []
    for q in questions.values():
        p = q.control_pair
        if not p or p not in questions:
            continue
        key = tuple(sorted((q.code, p)))
        if key in seen:
            continue
        seen.add(key)
        a, b = _pair_norm(q, answers.get(q.code)), _pair_norm(questions[p], answers.get(p))
        if a is None or b is None:
            continue
        out.append({"pair": list(key), "mismatch": abs(a - b) >= CONFIG["pair_mismatch_gap"]})
    return out


# ── Системное ограничение ─────────────────────────────────────────────────────
def find_constraint(scores: dict[int, float | None]) -> dict | None:
    """Модуль с низким баллом и максимальным влиянием на сильные модули.

    Сила узла = слабость узла × Σ(вес ребра × балл цели / 100). Слабый модуль,
    за которым стоят сильные, получает высокую оценку: пока он не развязан,
    вложения в сильные не дают отдачи. Модуль 10 — следствие, ограничением
    не бывает. Если слабых модулей нет (все ≥ высокого порога) — ограничения нет.
    """
    best = None
    for m in MODULES:
        s = scores.get(m)
        if m == EFFECT_MODULE or s is None or s >= CONFIG["state_high_from"]:
            continue
        influence = sum(w * (scores.get(t) or 0) / 100 for f, t, w in EDGES if f == m)
        if influence == 0:
            continue
        strength = (100 - s) / 100 * influence
        if best is None or strength > best["strength"]:
            best = {"module": m, "score": s, "strength": round(strength, 3),
                    "blocked": [t for f, t, _ in EDGES if f == m]}
    return best


def cause_effect(scores: dict[int, float | None]) -> dict | None:
    causes = [scores[m] for m in MODULES if m != EFFECT_MODULE and scores.get(m) is not None]
    effect = scores.get(EFFECT_MODULE)
    if not causes or effect is None:
        return None
    avg = sum(causes) / len(causes)
    gap = CONFIG["cause_effect_gap"]
    if avg - effect >= gap:
        case = "causes_high_effect_low"      # данные недостоверны или лаг
    elif effect - avg >= gap:
        case = "causes_low_effect_high"      # живёт на конъюнктуре, а не на управлении
    elif avg < CONFIG["cause_effect_both_low"] and effect < CONFIG["cause_effect_both_low"]:
        case = "both_low"                    # прямая работа по узкому месту
    else:
        case = "consistent"
    return {"causes_avg": round(avg, 1), "effect": round(effect, 1), "case": case}


# ── Главная функция ───────────────────────────────────────────────────────────
def calculate(
    questions: list[Question],
    answers: dict[str, Answer],
    *,
    mode: str = "full",
    profile: dict | None = None,
    rules: list[Rule] | None = None,
    recommendations: list[Recommendation] | None = None,
) -> dict:
    """Снимок результата прогона. mode: 'express' — только вопросы u0, без
    ограничения, правил и очереди действий; 'full' — всё."""
    profile = profile or {}
    qs = {q.code: q for q in questions if mode == "full" or q.tier == "u0"}
    active = {c: q for c, q in qs.items() if applies(q, answers, profile)}
    # Ответы на вопросы, которые сейчас не задаются (клиент сменил ответ на
    # родительский), в расчёт не идут — ни в баллы, ни в правила.
    answers = {c: a for c, a in answers.items() if c in active}

    # Баллы модулей
    modules: dict[int, dict] = {}
    for m in MODULES:
        num = den = 0.0
        asked = unknown = unknown_facts = 0
        for q in active.values():
            if q.module_code != m:
                continue
            a = answers.get(q.code)
            if a is None:
                continue
            asked += 1
            if a.unknown:
                unknown += 1
                unknown_facts += int(q.is_fact)
            s = question_score(q, a)
            if s is None:
                continue
            w = q.weight * (CONFIG["fact_weight_multiplier"] if q.is_fact else 1)
            num += w * s
            den += w
        score = round(num / den, 1) if den else None
        modules[m] = {
            "score": score, "state": state_of(score), "answered": asked, "unknown": unknown,
            "no_accounting": unknown_facts >= CONFIG["no_accounting_unknown_facts"],
        }
    scores = {m: v["score"] for m, v in modules.items()}

    causes = [(m, s) for m, s in scores.items() if m != EFFECT_MODULE and s is not None]
    top_gaps = [m for m, _ in sorted(causes, key=lambda x: x[1])[:3]]

    result = {
        "calc_version": CALC_VERSION,
        "mode": mode,
        "modules": modules,
        "top_gaps": top_gaps,
        "confidence": confidence(active, answers),
        "metrics": {q.metric_code: answers[q.code].number for q in active.values()
                    if q.metric_code and q.code in answers and answers[q.code].number is not None},
    }
    if mode == "express":
        return result

    constraint = find_constraint(scores)
    fired, unverified = [], []
    for r in rules or []:
        verdict = evaluate_rule(r, answers, qs)
        if verdict == "fired":
            fired.append({"code": r.code, "severity": r.severity})
        elif verdict == "unverified":
            unverified.append(r.code)
    fired.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))

    resistance = resistance_factor(answers)
    result.update({
        "constraint": constraint,
        "cause_effect": cause_effect(scores),
        "fired_rules": fired,
        "unverified_rules": unverified,
        "resistance": resistance,
        "priority_queue": priority_queue(modules, fired, constraint, resistance, recommendations or []),
    })
    return result


# ── Достоверность ─────────────────────────────────────────────────────────────
def confidence(active: dict[str, Question], answers: dict[str, Answer]) -> dict:
    # 1. «Не знаю» с двойным весом для фактов. Вопросы, где «не знаю» —
    #    содержательный ответ (штраф 0), в долю не входят: иначе один ответ
    #    учитывался бы дважды.
    num = den = 0.0
    for q in active.values():
        a = answers.get(q.code)
        if a is None or q.unknown_confidence_penalty == 0:
            continue
        w = 2 if q.is_fact else 1
        den += w
        if a.unknown:
            num += w * q.unknown_confidence_penalty
    share = num / den if den else 0.0
    p_unknown = round(CONFIG["unknown_max_penalty"] * min(1.0, share / CONFIG["unknown_full_penalty_share"]))

    # 2. Социальная желательность: самооценки массово в верхней трети, а
    #    факты это не подтверждают.
    def top_share(fact: bool) -> float | None:
        vals = [question_score(q, answers.get(q.code)) for q in active.values()
                if q.is_fact == fact and q.type not in ("number", "money")]
        vals = [v for v in vals if v is not None]
        return sum(v >= CONFIG["social_top_third"] for v in vals) / len(vals) if vals else None

    opinion, facts = top_share(False), top_share(True)
    p_social = 0
    rosy = opinion is not None and opinion > CONFIG["social_trigger_share"]
    unconfirmed = facts is None or (opinion is not None and facts <= opinion - CONFIG["social_fact_gap"] / 100)
    if rosy and unconfirmed:
        excess = (opinion - CONFIG["social_trigger_share"]) / (1 - CONFIG["social_trigger_share"])
        p_social = round(CONFIG["social_max_penalty"] * min(1.0, max(excess, 0.2)))

    # 3. Контрольные пары.
    pairs = control_pairs(active, answers)
    mismatches = [p["pair"] for p in pairs if p["mismatch"]]
    p_pairs = min(CONFIG["pair_max_penalty"], CONFIG["pair_penalty_each"] * len(mismatches))

    index = max(0, 100 - p_unknown - p_social - p_pairs)
    if share >= CONFIG["unknown_force_low_share"]:
        index = min(index, CONFIG["confidence_medium_from"] - 1)
    level = ("high" if index >= CONFIG["confidence_high_from"]
             else "medium" if index >= CONFIG["confidence_medium_from"] else "low")
    return {
        "index": index,
        "level": level,
        "components": {
            "unknown_share": {"share": round(share, 3), "penalty": p_unknown},
            "social_desirability": {"opinion_top_share": None if opinion is None else round(opinion, 3),
                                    "fact_top_share": None if facts is None else round(facts, 3),
                                    "penalty": p_social},
            "control_pair_mismatch": {"checked": len(pairs), "mismatches": mismatches, "penalty": p_pairs},
        },
    }


def resistance_factor(answers: dict[str, Answer]) -> float:
    r = 1.0
    for key in ("resistance_q_resourcing", "resistance_q_reversals"):
        code, bad_value, add = CONFIG[key]
        a = answers.get(code)
        if a is not None and a.value == bad_value:
            r += add
    return round(min(2.0, r), 2)


# ── Очередь действий ──────────────────────────────────────────────────────────
def priority_queue(modules: dict[int, dict], fired: list[dict], constraint: dict | None,
                   resistance: float, recs: list[Recommendation]) -> list[dict]:
    """Приоритет = эффект × 12 / недели ÷ (затраты × сопротивление).

    Рекомендация по системному ограничению идёт первой независимо от
    приоритета: пока оно не снято, остальное отдачи не даст. Рекомендации по
    модулям, которые ограничение блокирует, уходят в конец с пометкой.
    """
    by_key = {r.key: r for r in recs}
    wanted: list[Recommendation] = []
    for m, v in modules.items():
        if v["state"] in ("low", "mid"):
            r = by_key.get(f"m{m:02d}_{v['state']}")
            if r:
                wanted.append(r)
    for f in fired:
        r = by_key.get(f"cr_{f['code']}")
        if r:
            wanted.append(r)

    c_mod = constraint["module"] if constraint else None
    blocked = set(constraint["blocked"]) if constraint else set()
    out = []
    for r in wanted:
        prio = r.effect * 12 / r.speed_weeks / (r.cost * resistance)
        out.append({
            "key": r.key, "module_code": r.module_code, "rule_code": r.rule_code,
            "priority": round(prio, 3), "effect": r.effect, "speed_weeks": r.speed_weeks, "cost": r.cost,
            "is_constraint": r.module_code is not None and r.module_code == c_mod,
            "blocked_by_constraint": r.module_code in blocked,
        })
    out.sort(key=lambda x: (not x["is_constraint"], x["blocked_by_constraint"], -x["priority"]))
    return out
