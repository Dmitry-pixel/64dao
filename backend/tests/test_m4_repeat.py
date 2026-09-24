"""Метод 4: один бесплатный экспресс на аккаунт и повтор полной диагностики.

Повтор устроен как у Метода 1: первичная полная диагностика (оплаченная
пакетом, не грантом) даёт право на один повтор без оплаты; после
использованного повтора новая диагностика компании снова платная и
продолжает её историю в отчёте («Динамика»).
"""
from sqlalchemy import select

from app.m4_models import M4Run
from app.routers.payments import revoke_order_access
from tests.test_m4_api import (  # noqa: F401
    API,
    _fill,
    _grant,
    _order,
    _run,
    content,
    enforce_on,
    m3_on,
)


async def _calc(client, run_id):
    r = await client.post(f"{API}/runs/{run_id}/calculate")
    assert r.status_code == 200, r.text
    return r.json()


async def _full(client, good=False, company="ООО Колесо"):
    r = await _run(client, "full", company_name=company)
    assert r.status_code == 201, r.text
    run = r.json()
    await _fill(client, run["id"], "full", good=good)
    await _calc(client, run["id"])
    return run


# ── Экспресс ──────────────────────────────────────────────────────────────────
async def test_one_free_express_per_account(auth_client, content):
    a = (await _run(auth_client, company_name="Первая")).json()
    b = (await _run(auth_client, company_name="Вторая")).json()      # черновик можно завести
    await _fill(auth_client, a["id"], "express")
    await _fill(auth_client, b["id"], "express")
    await _calc(auth_client, a["id"])
    # второй экспресс не считается и новый не заводится
    assert (await auth_client.post(f"{API}/runs/{b['id']}/calculate")).status_code == 403
    assert (await _run(auth_client, company_name="Третья")).status_code == 403
    cr = (await auth_client.get(f"{API}/credits")).json()
    assert cr["express_available"] == 0
    # удаление не возвращает экспресс
    await auth_client.delete(f"{API}/runs/{a['id']}")
    assert (await _run(auth_client, company_name="Четвёртая")).status_code == 403


async def test_admin_express_unlimited(admin_client, content):
    for name in ("А", "Б"):
        run = (await _run(admin_client, company_name=name)).json()
        await _fill(admin_client, run["id"], "express")
        await _calc(admin_client, run["id"])
    assert (await admin_client.get(f"{API}/credits")).json()["express_available"] is None


# ── Повтор ────────────────────────────────────────────────────────────────────
async def test_followup_is_free_once(auth_client, content, db_session, test_user, enforce_on):
    order = await _order(db_session, test_user)
    first = await _full(auth_client)
    primary = await db_session.get(M4Run, first["id"])
    assert primary.order_id == order.id and primary.followup_allowed == 1

    cr = (await auth_client.get(f"{API}/credits", params={"company_name": "ООО Колесо"})).json()
    assert cr["full_available"] == 0 and cr["followup_available"] is True

    second = await _full(auth_client, good=True)          # пакета нет, но повтор входит в стоимость
    row = await db_session.get(M4Run, second["id"])
    assert row.is_followup and row.parent_run_id == primary.id and row.order_id is None
    await db_session.refresh(primary)
    assert primary.followup_used == 1

    # третья диагностика — снова платная первичная
    assert (await _run(auth_client, "full")).status_code == 403
    await _order(db_session, test_user)
    third = await _full(auth_client)
    row3 = await db_session.get(M4Run, third["id"])
    assert not row3.is_followup and row3.order_id is not None and row3.followup_allowed == 1


async def test_grant_primary_gives_no_followup(auth_client, content, db_session, test_user, enforce_on):
    await _grant(db_session, test_user)
    first = await _full(auth_client)
    assert (await db_session.get(M4Run, first["id"])).followup_allowed == 0
    assert (await _run(auth_client, "full")).status_code == 403


async def test_followup_report_has_dynamics(auth_client, content):
    await _full(auth_client, good=False)
    second = await _full(auth_client, good=True)
    rep = (await auth_client.get(f"{API}/runs/{second['id']}/report")).json()
    assert rep["is_followup"] is True
    d = rep["dynamics"]
    assert d and len(d["modules"]) == 10
    assert any(m["trend"] in ("improved", "worsened") for m in d["modules"])
    assert d["cards"] and all(c["title"] for c in d["cards"])
    first_rep = await auth_client.get(f"{API}/runs")
    assert first_rep.status_code == 200


async def test_first_report_has_no_dynamics(auth_client, content):
    run = await _full(auth_client)
    rep = (await auth_client.get(f"{API}/runs/{run['id']}/report")).json()
    assert rep["dynamics"] is None and rep["is_followup"] is False


async def test_refund_closes_followup_too(auth_client, content, db_session, test_user, enforce_on):
    order = await _order(db_session, test_user)
    await _full(auth_client)
    second = await _full(auth_client, good=True)
    order.status = "refunded"
    revoked = await revoke_order_access(db_session, order)
    await db_session.flush()
    assert revoked["m4_runs"] == 2
    row = await db_session.get(M4Run, second["id"])
    assert row.status == "filled"
    assert (await auth_client.get(f"{API}/runs/{second['id']}/report")).status_code == 403


async def test_companies_show_m4_repeat(auth_client, content, db_session):
    await _full(auth_client)
    c = (await auth_client.get("/api/companies")).json()[0]
    assert c["m4_followup_available"] is True and c["m4_next_repeat_at"]
    await _full(auth_client, good=True)
    c = (await auth_client.get("/api/companies")).json()[0]
    assert c["m4_followup_available"] is False
    assert any(a["is_followup"] for a in c["assessments"] if a["method"] == "method4")
    runs = (await db_session.execute(select(M4Run))).scalars().all()
    assert len(runs) == 2


async def test_followup_pdf_has_dynamics(auth_client, content, monkeypatch):
    from pathlib import Path

    import app.pdf as pdf_mod

    captured = {}

    async def fake_generate(html, path, **kw):
        captured["html"] = html
        Path(path).write_bytes(b"%PDF-1.4 test")
        return path

    monkeypatch.setattr(pdf_mod, "generate_pdf", fake_generate)
    await _full(auth_client, good=False)
    second = await _full(auth_client, good=True)
    assert (await auth_client.get(f"{API}/runs/{second['id']}/pdf")).status_code == 200
    assert "Что изменилось" in captured["html"] and "Повторная диагностика" in captured["html"]
