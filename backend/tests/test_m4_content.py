"""Контент Метода 4 в backend/content/m4 согласован сам с собой и с кодом
других методов.

Та же проверка, что делает seed_m4_content.py перед записью, но в CI: правка
JSON-файла, которая ломает ссылку правила на вопрос или связь конструкта с
пунктом Метода 3, падает здесь, а не при заливке на сервере.
"""
import seed_m4_content as seed


def test_content_files_are_consistent():
    content = seed.read_content()
    assert seed.check(content) == []


def test_content_volume():
    c = seed.read_content()
    assert len(c["modules"]) == 10
    assert len(c["questions"]) >= 120
    assert len(c["constructs"]) >= 21


def test_unknown_is_never_stored_as_option():
    """«Не знаю» подставляет код; строкой в вариантах его быть не должно,
    иначе база отклонит заливку (chk_m4_option_not_unknown)."""
    for q in seed.read_content()["questions"]:
        assert all(o["value"] != "unknown" for o in q["options"]), q["code"]


def test_no_links_to_deleted_bmc_draft():
    """Черновик опросника BMC из 54 утверждений удалён 23.09.2026."""
    for x in seed.read_content()["constructs"]:
        assert all(ln["method"] != "m2_bmc" for ln in x["links"]), x["code"]
