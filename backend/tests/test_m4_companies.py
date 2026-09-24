"""Метод 4 в «Моих компаниях»: рассчитанные прогоны видны в своей компании,
черновики и удалённые — нет, повтор и «Динамика» Методов 1–2 от них не
появляются."""
from tests.test_m4_api import API, _fill, _run, content, m3_on  # noqa: F401


async def _calculated(client, mode="express", company="ООО Колесо"):
    run = (await _run(client, mode, company_name=company)).json()
    await _fill(client, run["id"], mode)
    assert (await client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 200
    return run["id"]


async def test_calculated_runs_listed_in_company(auth_client, content):
    express = await _calculated(auth_client)
    full = await _calculated(auth_client, "full")
    await _run(auth_client, "express", company_name="Черновик")      # не рассчитан
    companies = (await auth_client.get("/api/companies")).json()
    assert [c["name"] for c in companies] == ["ООО Колесо"]
    c = companies[0]
    assert c["id"] and c["assessment_count"] == 2
    got = {a["id"]: (a["method"], a["mode"]) for a in c["assessments"]}
    assert got == {express: ("method4", "express"), full: ("method4", "full")}
    # у компании только с Методом 4 нет повтора и «Динамики» Методов 1–2
    assert c["repeat_days"] is None and c["next_repeat_at"] is None
    assert c["followup_available"] is False and c["dynamics_available"] is False


async def test_deleted_run_disappears(auth_client, content):
    run_id = await _calculated(auth_client)
    assert (await auth_client.delete(f"{API}/runs/{run_id}")).status_code == 204
    assert (await auth_client.get("/api/companies")).json() == []
