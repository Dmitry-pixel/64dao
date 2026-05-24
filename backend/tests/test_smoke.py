"""
Smoke-тесты для 64DAO — полное покрытие API и фронтенд-страниц.

Запуск:
    cd backend && python -m pytest tests/test_smoke.py -v --tb=short

Все тесты автоматически пропускаются если 64dao.ru недоступен.
"""

import json
import socket
import urllib.request
import urllib.error
import pytest

BASE = "https://64dao.ru"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _reachable() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("64dao.ru", 443))
        s.close()
        return True
    except Exception:
        return False


def _parse(raw: bytes) -> dict | str:
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode("utf-8", errors="replace")


def get(path: str, *, cookie: str | None = None):
    """HTTP GET → (status_code, body). Не бросает исключений."""
    req = urllib.request.Request(f"{BASE}{path}")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, _parse(r.read())
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())


def post(path: str, payload: dict | None = None, *, cookie: str | None = None):
    """HTTP POST JSON → (status_code, body). Не бросает исключений."""
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, _parse(r.read())
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())


# ── Session-level skip ────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def require_vps():
    if not _reachable():
        pytest.skip("64dao.ru недоступен — пропускаем все smoke-тесты")


# ── 1. Health ────────────────────────────────────────────────────────────────


class TestHealth:

    def test_health_status_ok(self):
        status, body = get("/api/health")
        assert status == 200, f"Ожидали 200, получили {status}"
        assert isinstance(body, dict) and body.get("status") == "ok", (
            f"Неверный ответ: {body}"
        )

    def test_unknown_api_route_404(self):
        status, _ = get("/api/__smoke_test_nonexistent__")
        assert status == 404

    def test_root_reachable(self):
        """/ может редиректить на /login или /dashboard — это норма."""
        status, _ = get("/")
        assert status in (200, 301, 302, 307, 308), f"/ вернул {status}"


# ── 2. Публичные документы ───────────────────────────────────────────────────


class TestPublicDocuments:

    @pytest.mark.parametrize("slug", [
        "user-agreement",
        "privacy-policy",
        "personal-data-consent",
        "about",
    ])
    def test_known_slug_200_or_404(self, slug):
        """Известный slug — 200 (опубликован) или 404 (черновик). Не 500."""
        status, _ = get(f"/api/documents/{slug}")
        assert status in (200, 404), f"/api/documents/{slug} → {status}"

    def test_unknown_slug_404(self):
        status, _ = get("/api/documents/__nonexistent_slug__")
        assert status == 404

    def test_published_doc_has_content(self):
        """Если какой-то документ опубликован — проверяем структуру ответа."""
        for slug in ("user-agreement", "privacy-policy", "about"):
            status, body = get(f"/api/documents/{slug}")
            if status == 200:
                assert isinstance(body, dict), "Ожидали JSON-объект"
                assert "content" in body, "Нет поля content"
                assert "title" in body, "Нет поля title"
                assert body.get("published") is True
                return
        pytest.skip("Ни один документ не опубликован")


# ── 3. Auth ──────────────────────────────────────────────────────────────────


class TestAuth:

    def test_me_without_cookie_401(self):
        status, _ = get("/api/auth/me")
        assert status == 401

    def test_login_empty_body_422(self):
        status, _ = post("/api/auth/login", {})
        assert status == 422

    def test_login_invalid_email_422(self):
        status, _ = post("/api/auth/login", {"email": "not-an-email"})
        assert status == 422

    def test_login_valid_email_200(self):
        """Валидный email — бэкенд принимает (OTP отправляется на почту)."""
        status, body = post("/api/auth/login", {"email": "smoke_test@example.com"})
        assert status == 200, f"Ожидали 200, получили {status}: {body}"

    def test_register_empty_body_422(self):
        status, _ = post("/api/auth/register", {})
        assert status == 422

    def test_verify_empty_body_422(self):
        status, _ = post("/api/auth/verify", {})
        assert status == 422

    def test_verify_wrong_otp_400_or_422(self):
        status, _ = post("/api/auth/verify", {
            "email": "smoke_test@example.com",
            "code": "000000",
        })
        assert status in (400, 422)

    def test_logout_always_200(self):
        """logout работает без авторизации — очищает cookie."""
        status, body = post("/api/auth/logout")
        assert status == 200
        assert isinstance(body, dict) and (
            body.get("ok") is True or body.get("success") is True
        )

    def test_forgot_password_valid_email(self):
        status, _ = post("/api/auth/forgot-password", {"email": "smoke@example.com"})
        assert status == 200

    def test_reset_password_invalid_token(self):
        status, _ = post("/api/auth/reset-password", {
            "token": "invalid_token",
            "new_password": "test123456",
        })
        assert status in (400, 422)


# ── 4. Assessments — требуют авторизации ─────────────────────────────────────


class TestAssessmentsRequireAuth:

    def test_list_401(self):
        status, _ = get("/api/assessments")
        assert status == 401

    def test_create_401(self):
        status, _ = post("/api/assessments", {"method1_combination": "AAAAAA"})
        assert status == 401

    def test_get_by_id_401(self):
        status, _ = get("/api/assessments/00000000-0000-0000-0000-000000000000")
        assert status == 401

    def test_delete_401(self):
        import urllib.request
        req = urllib.request.Request(
            f"{BASE}/api/assessments/00000000-0000-0000-0000-000000000000",
            method="DELETE",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            assert False, "Ожидали 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_generate_report_401(self):
        status, _ = post(
            "/api/assessments/00000000-0000-0000-0000-000000000000/generate-report"
        )
        assert status == 401

    def test_get_strategy_401(self):
        status, _ = get(
            "/api/assessments/00000000-0000-0000-0000-000000000000/strategy"
        )
        assert status == 401


# ── 5. Reports — требуют авторизации ─────────────────────────────────────────


class TestReportsRequireAuth:

    def test_download_401(self):
        status, _ = get("/api/reports/00000000-0000-0000-0000-000000000000/download")
        assert status == 401


# ── 6. Strategies — требуют авторизации ──────────────────────────────────────


class TestStrategiesRequireAuth:

    def test_list_all_401(self):
        status, _ = get("/api/strategies/all")
        assert status == 401

    def test_get_by_combo_401(self):
        status, _ = get("/api/strategies/AAAAAA")
        assert status == 401


# ── 7. Admin — требуют авторизации ───────────────────────────────────────────


ADMIN_GET_ENDPOINTS = [
    "/api/admin/stats",
    "/api/admin/users",
    "/api/admin/strategies",
    "/api/admin/logs",
    "/api/admin/pricing",
    "/api/admin/email-templates",
    "/api/admin/documents/about",
    "/api/admin/documents/user-agreement",
    "/api/admin/documents/privacy-policy",
    "/api/admin/documents/personal-data-consent",
    "/api/admin/reports",
]


class TestAdminRequireAuth:

    @pytest.mark.parametrize("path", ADMIN_GET_ENDPOINTS)
    def test_get_requires_auth(self, path):
        status, _ = get(path)
        assert status == 401, f"Ожидали 401 для {path}, получили {status}"

    def test_impersonate_stop_401(self):
        status, _ = post("/api/admin/impersonate/stop")
        assert status == 401

    def test_impersonate_user_401(self):
        status, _ = post(
            "/api/admin/impersonate/00000000-0000-0000-0000-000000000000"
        )
        assert status == 401

    def test_impersonate_status_no_auth(self):
        """Этот endpoint публичный — возвращает active:false без cookie."""
        status, body = get("/api/admin/impersonate/status")
        assert status == 200
        assert isinstance(body, dict)
        assert body.get("active") is False


# ── 8. Frontend страницы ──────────────────────────────────────────────────────


class TestFrontendPages:

    @pytest.mark.parametrize("path,desc", [
        ("/",          "главная"),
        ("/login",     "логин"),
        ("/about",     "о нас"),
        ("/dashboard", "дашборд (редирект на логин)"),
    ])
    def test_page_reachable(self, path, desc):
        """Страница отдаёт HTTP-ответ (200 или redirect — не 500/502)."""
        status, _ = get(path)
        assert status in (200, 301, 302, 307, 308), (
            f"Страница {desc} ({path}) вернула {status}"
        )

    def test_nonexistent_page_returns_content(self):
        """Next.js рендерит 404-страницу с кодом 404."""
        status, _ = get("/this_page_does_not_exist_xyz")
        # Next.js может вернуть 200 со страницей 404 или настоящий 404
        assert status in (200, 404)
