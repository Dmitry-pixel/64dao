# -*- coding: utf-8 -*-
"""
Единый store шаблонов писем: мердж с дефолтами, подстановка, изоляция пути.
БД не требуется.
"""
import json

import pytest

from app import email_templates_store as store


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    path = tmp_path / "email_templates.json"
    monkeypatch.setattr(store, "TEMPLATES_FILE", path)
    return path


def test_defaults_when_file_missing(isolated):
    data = store.read_templates()
    assert set(data) == set(store.DEFAULT_TEMPLATES)
    assert "repeat_diagnostic" in data


def test_saved_overrides_default(isolated):
    store.write_templates({"otp": {"subject": "X", "body_html": "<p>Y</p>"}})
    data = store.read_templates()
    assert data["otp"]["subject"] == "X"
    assert "welcome" in data and "repeat_diagnostic" in data


def test_new_default_appears_without_resaving(isolated):
    """Файл со старым набором ключей не должен прятать новый шаблон."""
    isolated.write_text(json.dumps({"otp": {"subject": "X", "body_html": ""}}),
                        encoding="utf-8")
    assert "repeat_diagnostic" in store.read_templates()


def test_description_comes_from_code_not_file(isolated):
    isolated.write_text(
        json.dumps({"otp": {"subject": "X", "body_html": "", "description": "мусор"}}),
        encoding="utf-8")
    assert store.read_templates()["otp"]["description"] == \
        store.DEFAULT_TEMPLATES["otp"]["description"]


def test_broken_file_falls_back_to_defaults(isolated):
    isolated.write_text("{ это не json", encoding="utf-8")
    assert set(store.read_templates()) == set(store.DEFAULT_TEMPLATES)


def test_render_substitutes_variables(isolated):
    subject, body = store.render("repeat_diagnostic", {
        "name_part": ", Дмитрий",
        "company_part": " компании «Ромашка»",
        "days_since": 97,
        "app_url": "https://64dao.ru",
    })
    assert subject == store.DEFAULT_TEMPLATES["repeat_diagnostic"]["subject"]
    assert ", Дмитрий" in body
    assert "компании «Ромашка»" in body
    assert "97" in body
    assert "https://64dao.ru/companies" in body
    for token in ("{name_part}", "{company_part}", "{days_since}", "{app_url}"):
        assert token not in body, "плейсхолдер %s остался неподставленным" % token


def test_render_unknown_key_returns_empty(isolated):
    assert store.render("нет-такого-шаблона", {}) == ("", "")
