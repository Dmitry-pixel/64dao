# -*- coding: utf-8 -*-
"""
Runtime-настройки рассылки: нормализация, хранение, API админки.
"""
import json

import pytest

from app import reminders_settings as rs


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    path = tmp_path / "reminders_settings.json"
    monkeypatch.setattr(rs, "SETTINGS_FILE", path)
    return path


# ── Нормализация ────────────────────────────────────────────────────────────

def test_defaults_when_file_missing():
    assert rs.read() == {"enabled": True, "repeat_enabled": True, "repeat_days": 90}


def test_too_small_period_is_clamped():
    """Опечатка в админке не должна превращать напоминание в спам."""
    assert rs.normalize({"repeat_days": 1})["repeat_days"] == rs.REPEAT_DAYS_MIN


def test_too_large_period_is_clamped():
    assert rs.normalize({"repeat_days": 99999})["repeat_days"] == rs.REPEAT_DAYS_MAX


def test_garbage_period_falls_back_to_default():
    assert rs.normalize({"repeat_days": "много"})["repeat_days"] == 90
    assert rs.normalize({"repeat_days": None})["repeat_days"] == 90


def test_unknown_keys_are_dropped():
    out = rs.normalize({"enabled": False, "hack": "rm -rf"})
    assert out == {"enabled": False, "repeat_enabled": True, "repeat_days": 90}


def test_write_returns_normalized_and_persists(isolated):
    saved = rs.write({"enabled": False, "repeat_days": 3})
    assert saved["repeat_days"] == rs.REPEAT_DAYS_MIN
    assert saved["enabled"] is False
    assert rs.read() == saved
    on_disk = json.loads(isolated.read_text(encoding="utf-8"))
    assert on_disk["repeat_days"] == rs.REPEAT_DAYS_MIN


def test_broken_file_falls_back_to_defaults(isolated):
    isolated.write_text("не json", encoding="utf-8")
    assert rs.read()["repeat_days"] == 90


# ── API админки ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_returns_defaults(admin_client):
    resp = await admin_client.get("/api/admin/reminders-settings")
    assert resp.status_code == 200
    assert resp.json()["repeat_days"] == 90


@pytest.mark.asyncio
async def test_put_saves_and_clamps(admin_client):
    resp = await admin_client.put("/api/admin/reminders-settings",
                                  json={"enabled": False, "repeat_days": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["repeat_days"] == rs.REPEAT_DAYS_MIN

    again = await admin_client.get("/api/admin/reminders-settings")
    assert again.json() == body


@pytest.mark.asyncio
async def test_regular_user_forbidden(auth_client):
    assert (await auth_client.get("/api/admin/reminders-settings")).status_code == 403
    assert (await auth_client.put("/api/admin/reminders-settings",
                                  json={"enabled": False})).status_code == 403
