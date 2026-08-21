"""Smoke-проверка боевого сайта: жив ли он и отдаёт ли то, что должен.

Запуск (host cron, каждые 15 минут):
    docker compose exec -T backend python -m app.jobs.smoke_prod

Зачем отдельная задача, если есть tests/test_smoke.py. Тесты помечены
маркером `live` и исключены из прогона (`addopts = -m "not live"` в
pytest.ini), поэтому не запускаются ни локально по умолчанию, ни в CI. Плюс
pytest не входит в боевой образ — запустить их на проде нечем. Проверки
здесь повторяют безопасную часть test_smoke.py и работают без pytest.

Что намеренно НЕ проверяется. Ни одного запроса с побочным эффектом:
никаких login/register/verify. Логин на несуществующий адрес сейчас
безвреден (ответ одинаков для любого email, письмо не уходит), но стоит
кому-то завести ящик из smoke-теста — и задача начнёт слать OTP каждые
15 минут. Проверка живости не должна зависеть от такой случайности.

Письмо уходит на support_email при СМЕНЕ состояния: сайт упал или сайт
восстановился. Повторные письма о продолжающейся аварии не шлются — иначе
за ночь простоя почта получит сотню одинаковых сообщений. Состояние лежит
в smoke_state.json в volume uploads, рядом с остальными рантайм-файлами.

Настройки (все необязательны):
  SMOKE_BASE_URL   — что проверяем (по умолчанию https://64dao.ru);
  SMOKE_TIMEOUT    — таймаут одного запроса в секундах (по умолчанию 10).
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.json_store import read_json, write_json

settings = get_settings()

BASE_URL = os.environ.get("SMOKE_BASE_URL", "https://64dao.ru").rstrip("/")
TIMEOUT = float(os.environ.get("SMOKE_TIMEOUT", "10"))

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
STATE_FILE = os.path.join(UPLOAD_DIR, "smoke_state.json")
DEFAULT_STATE = {"status": "unknown", "failing_since": None, "checked_at": None}

REDIRECTS = (301, 302, 307, 308)


def _health_ok(resp: httpx.Response) -> str | None:
    if resp.json().get("status") != "ok":
        return f"тело ответа не {{'status': 'ok'}}: {resp.text[:120]}"
    return None


def _impersonate_inactive(resp: httpx.Response) -> str | None:
    if resp.json().get("active") is not False:
        return f"ожидали active=false, получили {resp.text[:120]}"
    return None


def _pdf_if_present(resp: httpx.Response) -> str | None:
    # 404 здесь — не авария сайта, а незагруженный пример отчёта.
    if resp.status_code == 200 and "pdf" not in resp.headers.get("content-type", ""):
        return f"пример отчёта отдан не как PDF: {resp.headers.get('content-type')}"
    return None


# (описание, путь, допустимые коды, дополнительная проверка тела)
CHECKS: list[tuple[str, str, tuple[int, ...], object]] = [
    ("health бэкенда", "/api/health", (200,), _health_ok),
    ("кабинет закрыт без входа", "/api/auth/me", (401,), None),
    ("диагностики закрыты без входа", "/api/assessments", (401,), None),
    ("админка закрыта без входа", "/api/admin/stats", (401,), None),
    ("статус подмены пользователя", "/api/admin/impersonate/status", (200,), _impersonate_inactive),
    ("публичные документы", "/api/documents/user-agreement", (200, 404), None),
    ("несуществующий маршрут API", "/api/no_such_endpoint_xyz", (404,), None),
    ("пример отчёта (PDF)", "/api/sample-report/view", (200, 404), _pdf_if_present),
    ("главная страница", "/", (200, *REDIRECTS), None),
    ("страница входа", "/login", (200, *REDIRECTS), None),
]


async def run_checks(client: httpx.AsyncClient | None = None) -> list[str]:
    """Возвращает список провалов. Пустой список — всё в порядке.

    Готовый клиент принимается ради тестов: подменённый транспорт позволяет
    проверить разбор ответов, не выходя в сеть.
    """
    if client is None:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as own:
            return await _run_with(own)
    return await _run_with(client)


async def _run_with(client: httpx.AsyncClient) -> list[str]:
    failures: list[str] = []
    for title, path, allowed, extra in CHECKS:
        try:
            resp = await client.get(f"{BASE_URL}{path}")
        except Exception as e:
            # Недоступность — это и есть авария, ради которой всё затевалось.
            failures.append(f"{title} ({path}): запрос не прошёл — {e}")
            continue

        if resp.status_code not in allowed:
            failures.append(
                f"{title} ({path}): код {resp.status_code}, "
                f"ожидали {'/'.join(str(c) for c in allowed)}"
            )
            continue

        if extra is not None:
            try:
                problem = extra(resp)
            except Exception as e:
                problem = f"ответ не разобрать: {e}"
            if problem:
                failures.append(f"{title} ({path}): {problem}")

    return failures


def build_html(failures: list[str], failing_since: str | None) -> str:
    rows = "".join(f"<li>{f}</li>" for f in failures)
    since = f"<p>Первый сбой зафиксирован: {failing_since}</p>" if failing_since else ""
    return (
        f"<h2>64 ДАО: проверка сайта не прошла</h2>"
        f"<p>Адрес: {BASE_URL}</p>{since}"
        f"<ul>{rows}</ul>"
        f"<p>Проверка повторяется каждые 15 минут. Следующее письмо придёт "
        f"только когда сайт восстановится.</p>"
    )


def build_recovery_html(failing_since: str | None) -> str:
    since = f"<p>Сбой начался: {failing_since}</p>" if failing_since else ""
    return (f"<h2>64 ДАО: сайт снова отвечает</h2><p>Адрес: {BASE_URL}</p>"
            f"{since}<p>Все проверки пройдены.</p>")


async def _notify(subject: str, html: str) -> None:
    # Переиспользуем отправку из app.email, а не поднимаем свой SMTP:
    # хост, порт и режим TLS должны быть одни на всё приложение.
    from app.email import _send_message

    to = settings.support_email_address
    if not to or not settings.smtp_host:
        print("SMTP или support_email не настроены — письмо не отправлено")
        return
    await _send_message(to, subject, html)
    print(f"письмо отправлено на {to}")


async def main() -> int:
    now = datetime.now(UTC).isoformat()
    state = read_json(STATE_FILE, DEFAULT_STATE)
    was_failing = state.get("status") == "fail"

    failures = await run_checks()

    if failures:
        failing_since = state.get("failing_since") or now
        print(f"ПРОВАЛ ({len(failures)} из {len(CHECKS)}):")
        for f in failures:
            print(f"  - {f}")
        if not was_failing:
            await _notify("64 ДАО: сайт не отвечает как положено",
                          build_html(failures, failing_since))
        else:
            print("письмо не шлём: об этой аварии уже сообщали")
        write_json(STATE_FILE, {"status": "fail", "failing_since": failing_since,
                                "checked_at": now})
        return 1

    print(f"все {len(CHECKS)} проверок пройдены")
    if was_failing:
        await _notify("64 ДАО: сайт снова отвечает",
                      build_recovery_html(state.get("failing_since")))
    write_json(STATE_FILE, {"status": "ok", "failing_since": None, "checked_at": now})
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
