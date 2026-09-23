"""Расчёт Метода 4: баллы модулей, ограничение, правила, достоверность, очередь.

Первая половина — на синтетическом контенте: проверяется сама механика.
Вторая — на настоящем контенте из backend/content/m4: расчёт не падает на
реальных вопросах и правилах и даёт осмысленный результат на типовых профилях.
"""
import json
from pathlib import Path

import pytest

import seed_m4_content as seed
from app import m4_engine as e
from app.m4_engine import Answer, Question, Recommendation, Rule

CONTENT = Path(seed.__file__).parent / "content" / "m4"


def q(code, module, **kw):
    kw.setdefault("tier", "u0")
    kw.setdefault("type", "scale3")
    if kw["type"] == "scale3":
        kw.setdefault("options", {"yes": 100, "partial": 50, "no": 0})
    if kw["type"] == "bool":
        kw.setdefault("options", {"yes": 100, "no": 0})
    return Question(code=code, module_code=module, **kw)


def A(v):
    return Answer(value=v)


def N(x):
    return Answer(number=x)


U = Answer(value="unknown")


# ── Балл вопроса и модуля ─────────────────────────────────────────────────────
def test_question_score_rules():
    assert e.question_score(q("a", 1), A("partial")) == 50
    assert e.question_score(q("a", 1, type="bool", reverse=True), A("yes")) == 0
    assert e.question_score(q("a", 1), U) is None
    assert e.question_score(q("a", 1, unknown_score=0), U) == 0
    assert e.question_score(q("a", 1, score_neutral=True), A("yes")) is None
    assert e.question_score(q("a", 1, type="number"), N(5)) is None
    thr = q("a", 1, type="number", threshold_based=True, metric_code="top_client_share")
    assert e.question_score(thr, N(30)) == 100
    assert e.question_score(thr, N(31)) == 0


def test_module_score_weights_facts():
    qs = [q("a", 1, weight=2, is_fact=True), q("b", 1, weight=2)]
    r = e.calculate(qs, {"a": A("yes"), "b": A("no")}, mode="express")
    # факт весит 2×1,5 = 3, мнение 2: (3×100 + 2×0) / 5 = 60
    assert r["modules"][1]["score"] == 60.0
    assert r["modules"][1]["state"] == "mid"
    assert r["modules"][2]["score"] is None


def test_unknown_does_not_move_score_but_counts():
    qs = [q("a", 1), q("b", 1)]
    r = e.calculate(qs, {"a": A("yes"), "b": U}, mode="express")
    assert r["modules"][1]["score"] == 100.0
    assert r["modules"][1]["unknown"] == 1


def test_no_accounting_flag():
    qs = [q(f"f{i}", 7, is_fact=True) for i in range(3)]
    r = e.calculate(qs, {f"f{i}": U for i in range(3)}, mode="express")
    assert r["modules"][7]["no_accounting"] is True


def test_applies_when_forms():
    parent = q("p", 1, type="bool")
    child_list = q("c1", 1, applies_when={"p": ["yes"]})
    child_str = q("c2", 1, applies_when={"p": "yes"})
    num = q("n", 2, type="number")
    child_num = q("c3", 2, applies_when={"n": ">1"})
    prof = q("c4", 3, applies_when={"profile.revenue_model": ["one_off"]})
    ans = {"p": A("no"), "c1": A("yes"), "c2": A("yes"), "n": N(1), "c3": A("no"), "c4": A("no")}
    r = e.calculate([parent, child_list, child_str, num, child_num, prof], ans,
                    mode="full", profile={"revenue_model": "subscription"})
    # дети выключены: их ответы в балл не идут
    assert r["modules"][1]["score"] == 0.0
    assert r["modules"][2]["score"] is None
    assert r["modules"][3]["score"] is None
    ans.update({"p": A("yes"), "n": N(2)})
    r = e.calculate([parent, child_list, child_str, num, child_num, prof], ans,
                    mode="full", profile={"revenue_model": "one_off"})
    assert r["modules"][1]["score"] == 100.0
    assert r["modules"][2]["score"] == 0.0
    assert r["modules"][3]["score"] == 0.0


# ── Системное ограничение ─────────────────────────────────────────────────────
def test_constraint_is_bottleneck_not_lowest():
    """Пример из описания метода: продукт 80, клиенты 75, люди 30 —
    ограничение в людях, хотя где-то балл может быть ещё ниже."""
    scores = {m: 60.0 for m in range(1, 11)}
    scores.update({4: 80.0, 6: 75.0, 5: 30.0, 1: 25.0})
    c = e.find_constraint(scores)
    assert c["module"] == 5
    assert 4 in c["blocked"] and 6 in c["blocked"]


def test_no_constraint_when_all_strong():
    assert e.find_constraint({m: 80.0 for m in range(1, 11)}) is None


def test_effect_module_is_never_constraint():
    scores = {m: 90.0 for m in range(1, 11)}
    scores[10] = 5.0
    assert e.find_constraint(scores) is None


def test_graph_matches_content():
    m = json.loads((CONTENT / "modules.json").read_text(encoding="utf-8"))
    edges = {(x["from"], x["to"], x["weight"]) for x in m["dependency_graph"]["edges"]}
    assert edges == set(e.EDGES)


def test_cause_effect_cases():
    base = {m: 80.0 for m in range(1, 10)}
    assert e.cause_effect({**base, 10: 30.0})["case"] == "causes_high_effect_low"
    low = {m: 30.0 for m in range(1, 10)}
    assert e.cause_effect({**low, 10: 80.0})["case"] == "causes_low_effect_high"
    assert e.cause_effect({**low, 10: 35.0})["case"] == "both_low"
    assert e.cause_effect({**base, 10: 75.0})["case"] == "consistent"


# ── Правила противоречий ──────────────────────────────────────────────────────
QS = {"x": q("x", 1, type="bool"), "y": q("y", 1, type="bool"),
      "n": q("n", 2, type="number"), "m": q("m", 2, type="number")}


def rule(cond):
    return Rule(code="CR-T", severity="high", conditions=cond)


def test_rule_fired_clear_unverified():
    r = rule({"all": [{"q": "x", "op": "eq", "value": "yes"}, {"q": "n", "op": "gte", "value": 2}]})
    assert e.evaluate_rule(r, {"x": A("yes"), "n": N(3)}, QS) == "fired"
    assert e.evaluate_rule(r, {"x": A("no"), "n": N(3)}, QS) == "clear"
    # ложное условие решает исход даже при неизвестном втором
    assert e.evaluate_rule(r, {"x": A("no"), "n": U}, QS) == "clear"
    assert e.evaluate_rule(r, {"x": A("yes"), "n": U}, QS) == "unverified"
    assert e.evaluate_rule(r, {"x": A("yes")}, QS) == "unverified"


def test_rule_any_and_gt_question():
    r = rule({"any": [{"q": "x", "op": "eq", "value": "yes"},
                      {"q": "n", "op": "gt_question", "value": "m", "margin": 5}]})
    assert e.evaluate_rule(r, {"x": U, "n": N(20), "m": N(10)}, QS) == "fired"
    assert e.evaluate_rule(r, {"x": A("no"), "n": N(12), "m": N(10)}, QS) == "clear"
    assert e.evaluate_rule(r, {"x": U, "n": N(12), "m": N(10)}, QS) == "unverified"


# ── Достоверность ─────────────────────────────────────────────────────────────
def test_confidence_unknown_share():
    qs = [q(f"o{i}", 1) for i in range(4)] + [q(f"f{i}", 2, is_fact=True) for i in range(2)]
    ans = {f"o{i}": A("partial") for i in range(4)} | {"f0": U, "f1": U}
    c = e.calculate(qs, ans, mode="express")["confidence"]
    # доля: факты вес 2 → 4 / 8 = 0,5 → штраф полный
    assert c["components"]["unknown_share"]["penalty"] == 40
    # половина «не знаю» — достоверность низкая, даже если штрафы дают 60
    assert c["index"] == 49 and c["level"] == "low"
    ans["f1"] = A("yes")
    c = e.calculate(qs, ans, mode="express")["confidence"]
    assert c["components"]["unknown_share"]["penalty"] == 20
    assert c["index"] == 80 and c["level"] == "high"


def test_unknown_with_score_is_not_counted_twice():
    qs = [q("a", 1, unknown_score=0, unknown_confidence_penalty=0), q("b", 1)]
    c = e.calculate(qs, {"a": U, "b": A("yes")}, mode="express")["confidence"]
    assert c["components"]["unknown_share"]["penalty"] == 0


def test_social_desirability():
    opinions = [q(f"o{i}", 1) for i in range(10)]
    facts = [q(f"f{i}", 2, is_fact=True) for i in range(4)]
    rosy = {f"o{i}": A("yes") for i in range(10)}
    c = e.calculate(opinions + facts, rosy | {f"f{i}": A("no") for i in range(4)}, mode="express")["confidence"]
    assert c["components"]["social_desirability"]["penalty"] == 30
    c = e.calculate(opinions + facts, rosy | {f"f{i}": A("yes") for i in range(4)}, mode="express")["confidence"]
    assert c["components"]["social_desirability"]["penalty"] == 0


def test_control_pairs():
    a = q("a", 1, control_pair="b")
    b = q("b", 10, control_pair="a")
    rev = q("r", 5, type="bool", reverse=True, control_pair="a")
    pct = q("p", 6, type="number", min_value=0, max_value=100, control_pair="a")
    pairs = e.control_pairs({x.code: x for x in (a, b, rev, pct)},
                            {"a": A("yes"), "b": A("no"), "r": A("no"), "p": N(10)})
    got = {tuple(p["pair"]): p["mismatch"] for p in pairs}
    assert got[("a", "b")] is True
    assert got[("a", "r")] is False     # обратный вопрос: «нет» = хорошо
    assert got[("a", "p")] is True


# ── Сопротивление и очередь ───────────────────────────────────────────────────
def test_resistance():
    assert e.resistance_factor({}) == 1.0
    assert e.resistance_factor({"M05-Q13": A("on_top"), "M05-Q14": A("yes")}) == 2.0
    assert e.resistance_factor({"M05-Q13": A("partly")}) == 1.0


def test_priority_queue_constraint_first_and_resistance():
    modules = {m: {"state": "high"} for m in range(1, 11)}
    modules.update({5: {"state": "low"}, 4: {"state": "mid"}, 1: {"state": "mid"}})
    recs = [Recommendation("m05_low", effect=2, speed_weeks=12, cost=3, module_code=5),
            Recommendation("m04_mid", effect=3, speed_weeks=4, cost=1, module_code=4),
            Recommendation("m01_mid", effect=2, speed_weeks=4, cost=1, module_code=1),
            Recommendation("cr_CR-01", effect=3, speed_weeks=2, cost=1, rule_code="CR-01")]
    constraint = {"module": 5, "blocked": [4, 6, 8, 9]}
    fired = [{"code": "CR-01", "severity": "high"}]
    queue = e.priority_queue(modules, fired, constraint, 1.0, recs)
    keys = [x["key"] for x in queue]
    assert keys[0] == "m05_low"                 # ограничение первым, хотя приоритет низкий
    assert keys[-1] == "m04_mid"                # заблокирован ограничением
    assert keys[1:3] == ["cr_CR-01", "m01_mid"]
    slow = e.priority_queue(modules, fired, constraint, 2.0, recs)
    assert slow[1]["priority"] == pytest.approx(queue[1]["priority"] / 2)


def test_express_has_no_constraint_and_rules():
    r = e.calculate([q("a", 1), q("b", 2, tier="u1")], {"a": A("no"), "b": A("no")}, mode="express",
                    rules=[rule({"q": "a", "op": "eq", "value": "no"})])
    assert "constraint" not in r and "fired_rules" not in r
    assert r["modules"][2]["score"] is None      # u1 в экспресс не входит


# ── Настоящий контент ─────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def content():
    c = seed.read_content()
    return {
        "questions": [e.question_from(x) for x in c["questions"]],
        "rules": [e.rule_from(x) for x in c["rules"]],
        "recs": [r for r in (e.recommendation_from(x) for x in c["cards"]) if r],
    }


def answer_all(questions, pick):
    out = {}
    for x in questions:
        if x.type in ("number", "money"):
            out[x.code] = Answer(number=pick(x, None))
        else:
            out[x.code] = Answer(value=pick(x, x.options))
    return out


def best(x, opts):
    if opts is None:
        return 0
    return max(opts, key=lambda v: (opts[v] is not None, (100 - opts[v]) if x.reverse else (opts[v] or 0)))


def worst(x, opts):
    if opts is None:
        return 99
    return min(opts, key=lambda v: (opts[v] is None, (100 - opts[v]) if x.reverse else (opts[v] or 0)))


def test_real_content_every_card_key_exists(content):
    keys = {r.key for r in content["recs"]}
    for m in range(1, 11):
        assert {f"m{m:02d}_low", f"m{m:02d}_mid"} <= keys
    for r in content["rules"]:
        assert f"cr_{r.code}" in keys


def test_real_content_best_case(content):
    qs = content["questions"]
    r = e.calculate(qs, answer_all(qs, best), profile={"revenue_model": "repeat"},
                    rules=content["rules"], recommendations=content["recs"])
    assert all(v["state"] == "high" for v in r["modules"].values() if v["score"] is not None)
    assert r["constraint"] is None
    assert r["priority_queue"] == [] or all(x["rule_code"] for x in r["priority_queue"])


def test_real_content_worst_case(content):
    qs = content["questions"]
    r = e.calculate(qs, answer_all(qs, worst), profile={"revenue_model": "one_off"},
                    rules=content["rules"], recommendations=content["recs"], mode="full")
    assert all(v["state"] == "low" for v in r["modules"].values() if v["score"] is not None)
    # всё слабое: ограничение всё равно выбирается — модуль с наибольшим числом зависимых
    assert r["constraint"] is not None
    assert r["cause_effect"]["case"] == "both_low"
    assert r["fired_rules"], "на худших ответах часть противоречий обязана сработать"
    assert r["priority_queue"][0]["is_constraint"]
    assert r["resistance"] == 2.0


def test_real_content_all_unknown(content):
    qs = content["questions"]
    ans = {x.code: U for x in qs}
    r = e.calculate(qs, ans, rules=content["rules"], recommendations=content["recs"])
    assert r["confidence"]["level"] == "low"
    assert r["fired_rules"] == []
    assert r["unverified_rules"]


def test_real_content_express(content):
    qs = content["questions"]
    u0 = [x for x in qs if x.tier == "u0"]
    assert len(u0) == 20
    r = e.calculate(qs, answer_all(u0, worst), mode="express")
    assert len(r["top_gaps"]) == 3
    assert all(r["modules"][m]["score"] is not None for m in range(1, 11))
