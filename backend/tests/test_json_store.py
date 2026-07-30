# -*- coding: utf-8 -*-
"""Общая механика рантайм-настроек (app/json_store.py)."""
import json

from app.json_store import read_json, write_json


def test_missing_file_returns_defaults(tmp_path):
    assert read_json(tmp_path / "нет.json", {"a": 1}) == {"a": 1}


def test_file_overrides_defaults(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"a": 2}), encoding="utf-8")
    assert read_json(p, {"a": 1, "b": 3}) == {"a": 2, "b": 3}


def test_corrupt_file_falls_back(tmp_path):
    """Обрезанный файл не должен ронять приложение: до атомарной записи
    такое состояние возникало при падении посреди write_text."""
    p = tmp_path / "s.json"
    p.write_text('{"a": 1', encoding="utf-8")
    assert read_json(p, {"a": 1}) == {"a": 1}


def test_non_dict_falls_back(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("[1, 2]", encoding="utf-8")
    assert read_json(p, {"a": 1}) == {"a": 1}


def test_write_is_atomic_and_leaves_no_temp(tmp_path):
    p = tmp_path / "sub" / "s.json"
    write_json(p, {"a": 1})
    assert read_json(p) == {"a": 1}
    assert list(p.parent.iterdir()) == [p]
