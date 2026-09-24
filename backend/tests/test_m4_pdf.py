"""PDF Метода 4: HTML собирается из той же структуры, что веб-отчёт.

Хромиум в тестах не запускается: генерация подменяется, проверяется HTML
и то, что эндпоинт отдаёт файл только рассчитанному прогону.
"""
from pathlib import Path

import app.pdf as pdf_mod
from app import m4_pdf
from tests.test_m4_api import API, _fill, _run, content, m3_on  # noqa: F401


async def _calculated(client, mode="full"):
    run = (await _run(client, mode)).json()
    await _fill(client, run["id"], mode)
    assert (await client.post(f"{API}/runs/{run['id']}/calculate")).status_code == 200
    return run["id"]


def test_rounding_matches_web():
    # Math.round во вебе: 34,5 → 35; встроенный round в Питоне дал бы 34
    assert m4_pdf.rnd(34.5) == 35 and m4_pdf.rnd(34.4) == 34 and m4_pdf.rnd(0) == 0


async def test_pdf_endpoint(auth_client, content, monkeypatch):
    captured = {}

    async def fake_generate(html, path, **kw):
        captured["html"] = html
        captured["kw"] = kw
        Path(path).write_bytes(b"%PDF-1.4 test")
        return path

    monkeypatch.setattr(pdf_mod, "generate_pdf", fake_generate)
    run_id = await _calculated(auth_client)
    r = await auth_client.get(f"{API}/runs/{run_id}/pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert "attachment" in r.headers["content-disposition"]
    html = captured["html"]
    for title in ("Алмазное колесо · ООО Колесо", "Системное ограничение", "С чего начинать",
                  "Противоречия", "Состояние модулей", "Достоверность ответов", "<svg"):
        assert title in html, title
    for word in ("source_ref", "note_internal", "гл."):
        assert word not in html
    assert "ООО Колесо" in captured["kw"]["header_html"]


async def test_express_pdf_has_no_full_sections(auth_client, content, monkeypatch):
    captured = {}

    async def fake_generate(html, path, **kw):
        captured["html"] = html
        Path(path).write_bytes(b"%PDF-1.4 test")
        return path

    monkeypatch.setattr(pdf_mod, "generate_pdf", fake_generate)
    run_id = await _calculated(auth_client, "express")
    assert (await auth_client.get(f"{API}/runs/{run_id}/pdf")).status_code == 200
    assert "С чего начинать" not in captured["html"]
    assert "Что даст полная диагностика" in captured["html"]


async def test_pdf_closed_until_calculated(auth_client, content):
    run = (await _run(auth_client)).json()
    assert (await auth_client.get(f"{API}/runs/{run['id']}/pdf")).status_code == 403
