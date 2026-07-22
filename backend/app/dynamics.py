# -*- coding: utf-8 -*-
"""
Расчёт динамики компании (роадмап 3.1). Чистые функции: на вход — снимки
диагностик (base combination + result контуров), на выход — сравнение
последняя↔предыдущая (или ↔первая). БД и FastAPI не участвуют — тестируется
изолированно. Нового контента не требуется (§3).

snapshot = {
  "id": str, "created_at": iso-str, "combination": base A/B | None,
  "method": "method1"|"method2",
  "contours": {contour_key: result_dict},   # снимки assessment_contours.result
}
"""
from __future__ import annotations

from app.contour_summary import build_summary


def contour_diff(prev: dict, curr: dict) -> dict:
    """Сравнение одного контура между двумя прогонами."""
    p_lines = {l["line"]: l for l in prev.get("lines", [])}
    c_lines = {l["line"]: l for l in curr.get("lines", [])}

    line_changes = []
    for n in range(1, 7):
        pl, cl = p_lines.get(n), c_lines.get(n)
        if not pl or not cl or pl["symbol"] == cl["symbol"]:
            continue
        line_changes.append({
            "line": n,
            "line_key": cl.get("block"),
            "from": pl["symbol"],
            "to": cl["symbol"],
            "direction": "yin_to_yang" if cl["symbol"] == "A" else "yang_to_yin",
        })

    prev_moving = set(prev.get("moving_lines") or [])
    curr_moving = set(curr.get("moving_lines") or [])
    p_mi = prev.get("maturity_index") or 0
    c_mi = curr.get("maturity_index") or 0
    reached = bool(prev.get("combination_resulting")
                   and curr.get("combination_current") == prev.get("combination_resulting"))

    return {
        "maturity_from": prev.get("maturity_index"),
        "maturity_to": curr.get("maturity_index"),
        "maturity_delta": c_mi - p_mi,
        "line_changes": line_changes,
        "moving_closed": sorted(prev_moving - curr_moving),
        "moving_new": sorted(curr_moving - prev_moving),
        "reached_prev_target": reached,
        "hexagram_from": prev.get("hexagram_current"),
        "hexagram_to": curr.get("hexagram_current"),
    }


def summarize_contours(contour_diffs: dict[str, dict]) -> dict:
    """Списки улучшилось / деградировало / без изменений по Δзрелости."""
    improved, degraded, unchanged = [], [], []
    for c, d in contour_diffs.items():
        delta = d["maturity_delta"]
        (improved if delta > 0 else degraded if delta < 0 else unchanged).append(c)
    return {
        "improved": sorted(improved),
        "degraded": sorted(degraded),
        "unchanged": sorted(unchanged),
    }


def constraint_change(prev_contours: dict, curr_contours: dict) -> dict:
    ps = build_summary(prev_contours)
    cs = build_summary(curr_contours)
    p = ps.get("constraint") if ps else None
    c = cs.get("constraint") if cs else None
    return {"from": p, "to": c, "changed": p != c}


def base_pair_diff(base: dict, curr: dict) -> dict:
    b = base.get("combination")
    c = curr.get("combination")
    return {"combination_from": b, "combination_to": c, "changed": b != c}


def _brief(s: dict) -> dict:
    return {
        "id": s.get("id"),
        "created_at": s.get("created_at"),
        "combination": s.get("combination"),
        "contours": sorted(s.get("contours", {}).keys()),
    }


def build_company_dynamics(snapshots: list[dict], mode: str = "previous") -> dict:
    """Сравнение последней диагностики с предыдущей (mode='previous') или с
    первой (mode='first'). Нужно ≥2 диагностики, иначе available=False."""
    ordered = sorted(snapshots, key=lambda s: s.get("created_at") or "")
    timeline = [_brief(s) for s in ordered]

    if len(ordered) < 2:
        return {"available": False, "count": len(ordered), "timeline": timeline}

    curr = ordered[-1]
    base = ordered[0] if mode == "first" else ordered[-2]

    prev_c = base.get("contours", {}) or {}
    curr_c = curr.get("contours", {}) or {}
    shared = sorted(set(prev_c) & set(curr_c))
    diffs = {c: contour_diff(prev_c[c], curr_c[c]) for c in shared}

    return {
        "available": True,
        "count": len(ordered),
        "mode": "first" if mode == "first" else "previous",
        "compare_from": {"id": base.get("id"), "created_at": base.get("created_at")},
        "compare_to": {"id": curr.get("id"), "created_at": curr.get("created_at")},
        "timeline": timeline,
        "base_pair": base_pair_diff(base, curr),
        "contours": diffs,
        "constraint": constraint_change(prev_c, curr_c),
        "summary": summarize_contours(diffs),
    }
