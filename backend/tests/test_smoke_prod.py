"""Smoke-проверка боевого сайта (app/jobs/smoke_prod.py).

В сеть не ходим: httpx.MockTransport отвечает вместо прода. Проверяется
разбор ответов и — отдельно — правила отправки письма: молчать, пока авария
продолжается, и сообщить, когда сайт вернулся.
"""
import httpx
import pytest

import app.jobs.smoke_prod as job

OK_BODIES = {
    "/api/health": (200, {"status": "ok"}, None),
    "/api/auth/me": (401, {"detail": "unauthorized"}, None),
    "/api/assessments": (401, {"detail": "unauthorized"}, None),
    "/api/admin/stats": (401, {"detail": "unauthorized"}, None),
    "/api/admin/impersonate/status": (200, {"active": False}, None),
    "/api/documents/user-agreement": (200, {"title": "x", "content": "y"}, None),
    "/api/no_such_endpoint_xyz": (404, {"detail": "not found"}, None),
    "/api/sample-report/view": (200, b"%PDF-1.4", "application/pdf"),
    "/": (200, b"<html></html>", "text/html"),
    "/login": (200, b"<html></html>", "text/html"),
}


def _transport(overrides=None, raise_on=None):
    """Отвечает как здоровый прод; overrides подменяет отдельные пути."""
    overrides = overrides or {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if raise_on and path == raise_on:
            raise httpx.ConnectError("прод недоступен")
        status, body, content_type = overrides.get(path, OK_BODIES[path])
        if isinstance(body, bytes):
            return httpx.Response(status, content=body,
                                  headers={"content-type": content_type})
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


async def _run(transport) -> list[str]:
    async with httpx.AsyncClient(transport=transport) as client:
        return await job.run_checks(client)


@pytest.mark.asyncio
async def test_healthy_site_has_no_failures():
    assert await _run(_transport()) == []


@pytest.mark.asyncio
async def test_backend_down_is_reported():
    failures = await _run(_transport({"/api/health": (502, {"detail": "bad gateway"}, None)}))
    assert len(failures) == 1
    assert "/api/health" in failures[0] and "502" in failures[0]


@pytest.mark.asyncio
async def test_health_wrong_body_is_reported():
    """200 с чужим телом — тоже авария: отвечает не наше приложение."""
    failures = await _run(_transport({"/api/health": (200, {"status": "degraded"}, None)}))
    assert len(failures) == 1
    assert "status" in failures[0]


@pytest.mark.asyncio
async def test_open_cabinet_is_reported():
    """Если кабинет вдруг отвечает без входа — это дыра, а не «сайт живой»."""
    failures = await _run(_transport({"/api/auth/me": (200, {"email": "a@b.c"}, None)}))
    assert len(failures) == 1
    assert "/api/auth/me" in failures[0]


@pytest.mark.asyncio
async def test_unreachable_host_is_reported():
    failures = await _run(_transport(raise_on="/api/health"))
    assert any("запрос не прошёл" in f for f in failures)


@pytest.mark.asyncio
async def test_sample_report_missing_is_not_a_failure():
    """404 у примера отчёта — не загружен файл, а не авария сайта."""
    assert await _run(_transport({"/api/sample-report/view": (404, {"detail": "нет"}, None)})) == []


@pytest.mark.asyncio
async def test_sample_report_not_pdf_is_reported():
    """200, но вместо PDF — HTML: значит отдаётся страница ошибки."""
    failures = await _run(_transport(
        {"/api/sample-report/view": (200, b"<html>oops</html>", "text/html")}))
    assert len(failures) == 1
    assert "PDF" in failures[0]


@pytest.mark.asyncio
async def test_redirect_on_frontend_is_allowed():
    """Редирект на /login — штатное поведение, не падение."""
    assert await _run(_transport({"/": (307, b"", "text/html")})) == []


# ── Правила отправки письма ──────────────────────────────────────────────────


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    path = tmp_path / "smoke_state.json"
    monkeypatch.setattr(job, "STATE_FILE", str(path))
    return path


@pytest.fixture
def sent(monkeypatch):
    box: list[tuple[str, str]] = []

    async def fake_notify(subject, html):
        box.append((subject, html))

    monkeypatch.setattr(job, "_notify", fake_notify)
    return box


@pytest.mark.asyncio
async def test_first_failure_sends_one_letter(state_file, sent, monkeypatch):
    async def failing(client=None):
        return ["health бэкенда (/api/health): код 502, ожидали 200"]

    monkeypatch.setattr(job, "run_checks", failing)

    assert await job.main() == 1
    assert len(sent) == 1
    assert "не отвечает" in sent[0][0]

    # Вторая проверка при той же аварии писем больше не шлёт.
    assert await job.main() == 1
    assert len(sent) == 1, "о продолжающейся аварии письмо повторно не шлётся"


@pytest.mark.asyncio
async def test_recovery_sends_letter(state_file, sent, monkeypatch):
    async def failing(client=None):
        return ["health бэкенда (/api/health): код 502, ожидали 200"]

    async def healthy(client=None):
        return []

    monkeypatch.setattr(job, "run_checks", failing)
    await job.main()
    assert len(sent) == 1

    monkeypatch.setattr(job, "run_checks", healthy)
    assert await job.main() == 0
    assert len(sent) == 2
    assert "снова отвечает" in sent[1][0]

    # Здоровый прогон подряд писем не добавляет.
    assert await job.main() == 0
    assert len(sent) == 2
