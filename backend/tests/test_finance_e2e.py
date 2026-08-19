# -*- coding: utf-8 -*-
"""
Этап 8 — E2E и регресс финансового блока. Требует БД (dao64_test).
"""
import uuid

import pytest
from sqlalchemy import select

import app.routers.assessments as assessments_router
from app.finance_interpret import build_interpretation, load_content
from app.models import Assessment, AssessmentContour, FinContent, Strategy
from app.pdf import build_report_html


def control_finance() -> dict:
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    return a


async def seed_minimal_content(db):
    rows = [
        ("tonality", "transitional", {"title": "Переходное состояние", "text": "Язык приоритизации."}),
        ("quadrant", "power_no_direction", {"title": "Сила без направления", "text": "Двигатель есть, руля нет."}),
        ("trigram", "AAA_lower", {"title": "Цянь", "text": "Двигатель на пике."}),
        ("trigram", "ABB_upper", {"title": "Чжэнь", "text": "Поддержка без направления."}),
        ("tension_rule", "R1", {"text": "Поддержка без стратегии."}),
        ("tension_rule", "R6", {"text": "Трансформация в турбулентной среде."}),
        ("tension_rule", "R8", {"text": "Рутина без развития."}),
        ("action_package", "line6_yin", {"title": "6. Стратегия", "text": "Стратегическая сессия, целевая модель, KPI."}),
    ]
    for kind, key, payload in rows:
        db.add(FinContent(id=uuid.uuid4(), kind=kind, key=key, payload=payload, sort=0, is_active=True))
    db.add(Strategy(
        id=uuid.uuid4(), combination="AAAABB",
        stratagema_title="Базовая стратагема",
        title="Сила",
        lifecycle_stage="Расцвет",
        scenario={"innovation_strategy": "Изменения через усиление"},
        scenario_text="Описание сценария развития для AAAABB.",
        marketing_text="Маркетинговые рекомендации для AAAABB.",
        management_text="Управленческие рекомендации для AAAABB.",
        transition_title="Переход к ясной цели",
        transition_description="Описание перехода.",
        assm_planning="Предположение по планированию.",
        fin_pattern_essence="Ресурс превышает ясность его применения.",
        fin_pattern_mistake="Активность ради активности.",
        is_published=True,
    ))
    await db.flush()


@pytest.mark.asyncio
async def test_e2e_finance_flow(auth_client, db_session):
    await seed_minimal_content(db_session)

    resp = await auth_client.post("/api/assessments", json={
        "method1_answers": {f"q{i}": "A" for i in range(1, 7)},
        "method1_combination": "AAAABB",
        "finance_answers": control_finance(),
        "company_name": "E2E Компания",
        "status": "completed",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    aid = data["id"]

    assert data["finance_combination"] == "AAAABB"
    assert data["finance_result"]["hexagram_current"]["number"] == 34
    assert data["finance_result"]["hexagram_resulting"]["number"] == 14
    assert data["finance_result"]["moving_lines"] == [6]

    fi = await auth_client.get(f"/api/assessments/{aid}/finance-interpretation")
    assert fi.status_code == 200, fi.text
    body = fi.json()
    assert body["has_finance"] is True
    interp = body["interpretation"]
    assert interp["tonality"]["title"] == "Переходное состояние"
    assert interp["quadrant"]["title"] == "Сила без направления"
    assert [t["id"] for t in interp["tensions"]] == ["R1", "R6", "R8"]
    assert interp["priorities"][0]["line"] == 6
    assert interp["trajectory"]["resulting"]["number"] == 14

    assessment = await db_session.scalar(select(Assessment).where(Assessment.id == uuid.UUID(aid)))
    fin = await db_session.scalar(select(AssessmentContour).where(
        AssessmentContour.assessment_id == uuid.UUID(aid),
        AssessmentContour.contour == "finance"))
    content = await load_content(db_session)
    interpretation = build_interpretation(fin.result, content)
    base_strategy = await db_session.scalar(select(Strategy).where(Strategy.combination == "AAAABB"))
    fin_strategy = await db_session.scalar(
        select(Strategy).where(Strategy.combination == fin.combination))

    html = build_report_html(
        company_name="E2E Компания", user_name="CFO", date_str="сегодня",
        combination=assessment.method1_combination, strategy=base_strategy, method2_data=None,
        finance_result=fin.result, finance_interpretation=interpretation,
        finance_strategy=fin_strategy,
    )

    fi_idx = html.index("Финансовая функция")
    base = html[:fi_idx]
    assert "Текущее состояние" in base
    assert "Базовая стратагема" in base
    assert "Ответы диагностики" in base
    assert "Параметры стратагемы" in base
    assert "Целевой сценарий" in html  # раздел идёт после финансового блока
    assert "Сценарий развития" not in base
    assert "Описание сценария развития для AAAABB." not in base

    fin = html[fi_idx:]
    for part in ("Диагноз", "Профиль линий", "Ресурс и направление", "Ключевые напряжения",
                 "Приоритеты вмешательства", "Маршрут перехода", "Оговорки по данным", "Следующие шаги"):
        assert part in fin, f"нет подраздела финраздела: {part}"
    assert "Описание сценария развития для AAAABB." in fin
    assert "№ 34" in fin and "№ 14" in fin
    assert "Поддержка без стратегии." in fin
    assert "Стратегическая сессия, целевая модель, KPI." in fin
    assert "3.25" in fin and "1.00" in fin


@pytest.mark.asyncio
async def test_legacy_without_finance_regenerates(auth_client, db_session, monkeypatch):
    monkeypatch.setattr(assessments_router.settings, "finance_block_required", False)
    await seed_minimal_content(db_session)

    resp = await auth_client.post("/api/assessments", json={
        "method1_answers": {f"q{i}": "A" for i in range(1, 7)},
        "method1_combination": "AAAABB",
        "company_name": "Legacy Co",
        "status": "completed",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["finance_combination"] is None
    assert data["finance_result"] is None

    fi = await auth_client.get(f"/api/assessments/{data['id']}/finance-interpretation")
    assert fi.status_code == 200
    assert fi.json()["has_finance"] is False

    base_strategy = await db_session.scalar(select(Strategy).where(Strategy.combination == "AAAABB"))
    html = build_report_html(
        company_name="Legacy Co", user_name="", date_str="сегодня",
        combination="AAAABB", strategy=base_strategy, method2_data=None,
    )
    assert "<!DOCTYPE html>" in html
    assert "Финансовая функция" not in html
    assert "Параметры стратагемы" in html


@pytest.mark.asyncio
async def test_flag_on_requires_finance_for_method1(auth_client, monkeypatch):
    monkeypatch.setattr(assessments_router.settings, "finance_block_required", True)
    resp = await auth_client.post("/api/assessments", json={
        "method1_answers": {f"q{i}": "A" for i in range(1, 7)},
        "method1_combination": "AAAABB",
        "status": "completed",
    })
    assert resp.status_code == 400

    resp2 = await auth_client.post("/api/assessments", json={
        "method1_answers": {f"q{i}": "A" for i in range(1, 7)},
        "method1_combination": "AAAAAA",
        "method2_data": {"Ценностное предложение": {"score": 4, "text": "ок"}},
        "status": "completed",
    })
    assert resp2.status_code == 200, resp2.text
