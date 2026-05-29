"""
Sanity-тесты для 64DAO backend.
Запуск: cd backend && python -m pytest tests/test_sanity.py -v --tb=short
"""

import re
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pdf import (
    _hexagram_svg,
    _HEXAGRAM_BY_COMBO,
    _HEXAGRAM_LIST,
    _HEXAGRAM_BY_NUM,
    _TARGET_HEXAGRAM,
    get_target_hexagram_info,
    build_report_html,
    HEX_SYMBOLS,
)

BASE_URL = "https://64dao.ru"


# ── 1. SVG: порядок линий ────────────────────────────────────────────────────

class TestHexagramSVG:

    def _rects(self, svg):
        out = []
        for m in re.finditer(r'<rect\s[^/]*/>', svg):
            attrs = {}
            for a in re.finditer(r'(\w+)="([^"]+)"', m.group()):
                try:
                    attrs[a.group(1)] = float(a.group(2))
                except ValueError:
                    pass
            out.append(attrs)
        return out

    def test_yang_solid_one_rect_per_line(self):
        assert len(self._rects(_hexagram_svg("AAAAAA"))) == 6

    def test_yin_broken_two_rects_per_line(self):
        assert len(self._rects(_hexagram_svg("BBBBBB"))) == 12

    def test_mixed_rect_count(self):
        # 3 A + 3 B = 3 + 6 = 9
        assert len(self._rects(_hexagram_svg("ABABAB"))) == 9

    def test_line0_is_bottom(self):
        """combination[0] = нижняя линия → самый большой y."""
        rects = self._rects(_hexagram_svg("ABBBBB"))
        yg = {}
        for r in rects:
            k = round(r["y"], 1)
            yg.setdefault(k, []).append(r)
        yang_y  = [k for k, v in yg.items() if len(v) == 1]
        yin_ys  = [k for k, v in yg.items() if len(v) == 2]
        assert len(yang_y) == 1
        assert yang_y[0] > max(yin_ys), (
            f"line0 (янь) должна быть НИЖЕ всех инь: yang_y={yang_y[0]:.1f} max_yin={max(yin_ys):.1f}")

    def test_line5_is_top(self):
        """combination[5] = верхняя линия → самый маленький y."""
        rects = self._rects(_hexagram_svg("BBBBBA"))
        yg = {}
        for r in rects:
            k = round(r["y"], 1)
            yg.setdefault(k, []).append(r)
        yang_y = [k for k, v in yg.items() if len(v) == 1]
        yin_ys = [k for k, v in yg.items() if len(v) == 2]
        assert len(yang_y) == 1
        assert yang_y[0] < min(yin_ys), (
            f"line5 (янь) должна быть ВЫШЕ всех инь: yang_y={yang_y[0]:.1f} min_yin={min(yin_ys):.1f}")

    def test_equal_spacing(self):
        rects = self._rects(_hexagram_svg("AAAAAA"))
        ys = sorted(r["y"] for r in rects)
        steps = [round(ys[i+1] - ys[i], 2) for i in range(5)]
        assert len(set(steps)) == 1, f"Неравномерный шаг: {steps}"

    def test_svg_structure(self):
        svg = _hexagram_svg("ABABBA")
        assert svg.startswith("<svg") and svg.endswith("</svg>")
        assert "xmlns=" in svg

    def test_sizes(self):
        for size in [48, 80, 200]:
            assert f'width="{size}"' in _hexagram_svg("AAAAAA", size=size)


# ── 2. Таблица 64 комбинаций ─────────────────────────────────────────────────

class TestHexagramTable:

    def test_exactly_64(self):
        assert len(_HEXAGRAM_LIST) == 64

    def test_unique_combos(self):
        combos = [c for _, _, c in _HEXAGRAM_LIST]
        assert len(set(combos)) == 64

    def test_numbers_1_to_64(self):
        assert sorted(n for n, _, _ in _HEXAGRAM_LIST) == list(range(1, 65))

    def test_combo_format(self):
        for num, name, combo in _HEXAGRAM_LIST:
            assert re.fullmatch(r"[AB]{6}", combo), f"#{num} '{name}': '{combo}'"

    def test_by_combo_dict(self):
        assert len(_HEXAGRAM_BY_COMBO) == 64
        for num, name, combo in _HEXAGRAM_LIST:
            assert _HEXAGRAM_BY_COMBO[combo] == (num, name)

    def test_by_num_dict(self):
        assert len(_HEXAGRAM_BY_NUM) == 64
        for num, name, _ in _HEXAGRAM_LIST:
            assert _HEXAGRAM_BY_NUM[num] == name

    def test_spot_check(self):
        assert _HEXAGRAM_BY_COMBO["AAAAAA"] == (1, "Действие")
        assert _HEXAGRAM_BY_COMBO["BBBBBB"] == (2, "Реакция")
        assert _HEXAGRAM_BY_COMBO["ABABAB"] == (63, "Завершение")
        assert _HEXAGRAM_BY_COMBO["BABABA"] == (64, "Незавершённость")


# ── 3. Целевые гексаграммы ───────────────────────────────────────────────────

class TestTargetHexagram:

    def test_all_64_have_target(self):
        assert len(_TARGET_HEXAGRAM) == 64
        for n in range(1, 65):
            assert n in _TARGET_HEXAGRAM

    def test_targets_in_range(self):
        for src, tgt in _TARGET_HEXAGRAM.items():
            assert 1 <= tgt <= 64, f"#{src} -> invalid target {tgt}"

    def test_returns_tuple(self):
        num, name, sym = get_target_hexagram_info("AAAAAA")
        assert 1 <= num <= 64
        assert len(name) > 0
        assert len(sym) == 1

    def test_unknown_returns_none(self):
        assert get_target_hexagram_info("XXXXXX") is None
        assert get_target_hexagram_info("") is None

    def test_symbol_unicode_range(self):
        for _, _, combo in _HEXAGRAM_LIST:
            _, _, sym = get_target_hexagram_info(combo)
            cp = ord(sym)
            assert 0x4DC0 <= cp <= 0x4DFF, f"U+{cp:04X} вне диапазона гексаграмм"


# ── 4. HTML-отчёт ────────────────────────────────────────────────────────────

class TestBuildReportHTML:

    def _html(self, combo="ABABBA", strategy=None, m2=None):
        return build_report_html(
            company_name="Test Corp",
            user_name="Test User",
            date_str="24 мая 2026",
            combination=combo,
            strategy=strategy,
            method2_data=m2,  # None = Метод 1, {} или {...} = Метод 2
        )

    def test_returns_nonempty_string(self):
        html = self._html()
        assert len(html) > 500

    def test_doctype_and_tags(self):
        html = self._html()
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_company_in_html(self):
        assert "Test Corp" in self._html()

    def test_no_strategy_ok(self):
        assert "<!DOCTYPE html>" in self._html(strategy=None)

    def test_method2_only(self):
        html = self._html(combo="", m2={"Ключевые партнёры": {"score": 3, "text": "Тест партнёры"}})
        assert "Бизнес-модель" in html
        assert "Тест партнёры" in html

    def test_xss_escaped(self):
        html = build_report_html(
            company_name='<script>xss</script>',
            user_name="u", date_str="d",
            combination="AAAAAA", strategy=None, method2_data={},
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_all_64_combos(self):
        for _, _, combo in _HEXAGRAM_LIST:
            assert "<!DOCTYPE html>" in self._html(combo=combo)

    def test_cover_hex_symbol(self):
        html = self._html(combo="AAAAAA")  # #1 = U+4DC0 = ䷀
        assert "䷀" in html


# ── 5. Live smoke (VPS) ──────────────────────────────────────────────────────

class TestLiveAPI:

    @pytest.fixture(autouse=True)
    def need_network(self):
        import socket
        try:
            socket.setdefaulttimeout(3)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("64dao.ru", 443))
            s.close()
        except Exception:
            pytest.skip("64dao.ru недоступен")

    def test_health(self):
        import urllib.request, json
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=10) as r:
            assert r.status == 200
            assert json.loads(r.read()).get("status") == "ok"

    def test_login_endpoint_exists(self):
        import urllib.request, urllib.error
        req = urllib.request.Request(
            f"{BASE_URL}/api/auth/login",
            data=b"{}", headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            assert e.code in (422, 400), f"expected 422/400, got {e.code}"

    def test_assessments_needs_auth(self):
        import urllib.request, urllib.error
        try:
            urllib.request.urlopen(f"{BASE_URL}/api/assessments", timeout=10)
            pytest.fail("expected 401")
        except urllib.error.HTTPError as e:
            assert e.code == 401, f"expected 401, got {e.code}"

    def test_unknown_route_404(self):
        import urllib.request, urllib.error
        try:
            urllib.request.urlopen(f"{BASE_URL}/api/no_such_endpoint_xyz", timeout=10)
            pytest.fail("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404, f"expected 404, got {e.code}"
