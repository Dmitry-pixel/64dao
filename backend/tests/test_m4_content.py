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


def test_profile_options_match_database():
    """Варианты в форме профиля совпадают с ограничениями таблицы
    company_profiles: иначе форма предложит значение, которое база отклонит."""
    import json

    from app.models import REVENUE_MODELS, REVENUE_RANGES

    prof = json.loads((seed.CONTENT / "company-profile.json").read_text(encoding="utf-8"))
    fields = {f["code"]: f for f in prof["required"] + prof["optional"]}
    assert tuple(o["value"] for o in fields["revenue_model"]["options"]) == REVENUE_MODELS
    assert tuple(o["value"] for o in fields["revenue_range"]["options"]) == REVENUE_RANGES


def test_applies_when_profile_values_exist():
    """Условия показа вопросов по профилю ссылаются на существующие значения."""
    from app.models import REVENUE_MODELS

    for q in seed.read_content()["questions"]:
        for ref, values in (q["applies_when"] or {}).items():
            if ref == "profile.revenue_model":
                assert set(values) <= set(REVENUE_MODELS), q["code"]
