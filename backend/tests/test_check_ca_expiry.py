"""Проверка доверия к API Точки: расчёт сроков и решение «слать письмо».

Сеть и почта здесь не участвуют намеренно. Решение о письме — единственное
место, где задача ошибается молча: не отправит предупреждение об отказе
оплаты или завалит почту еженедельным повтором. Боевым запуском это
проверяется раз в год, тестом — на каждом прогоне.

Переписано 2026-09-23 вместе с задачей: тревога по сроку вендоренной копии
выпускающего сертификата убрана, добавлены рукопожатие, срок корня и срок
сертификата банка.
"""
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.jobs.check_ca_expiry import (
    Observation,
    build_html,
    cert_not_after,
    days_left,
    decide,
    decode_cert_der,
)

CERTS = Path(__file__).resolve().parents[1] / "certs"
NOW = datetime(2026, 9, 23, tzinfo=UTC)

ISSUER = "Russian Trusted Sub CA"
OLD_ISSUER = "TrustAsia DV TLS RSA CA 2024"


def obs(**kw) -> Observation:
    """Наблюдение «всё в порядке», поля переопределяются точечно."""
    base = dict(
        root_days=1980,      # корень НУЦ Минцифры до 2032
        sub_days=164,        # вендоренная копия до 2027-03-06 — справочно
        handshake_ok=True,
        handshake_error="",
        issuer=ISSUER,
        leaf_days=268,       # сертификат Точки до 2027-06-18
    )
    base.update(kw)
    return Observation(**base)


def test_days_left_counts_from_given_moment():
    assert days_left(NOW + timedelta(days=200), now=NOW) == 200
    assert days_left(NOW - timedelta(days=1), now=NOW) == -1


@pytest.mark.skipif(not (CERTS / "russian_trusted_root_ca.crt").is_file(),
                    reason="сертификаты не вендорены в этой копии репозитория")
def test_reads_real_vendored_certs():
    """Разбор идёт через ssl, а не через свой парсер строки даты.

    OpenSSL печатает notAfter как «Mar  6 11:25:19 2027 GMT» — с двойным
    пробелом для однозначного числа, на котором strptime спотыкается.
    """
    root = cert_not_after(CERTS / "russian_trusted_root_ca.crt")
    assert root.year == 2032
    sub = cert_not_after(CERTS / "russian_trusted_sub_ca.crt")
    assert sub.year == 2027 and sub.month == 3


@pytest.mark.skipif(not (CERTS / "russian_trusted_root_ca.crt").is_file(),
                    reason="сертификаты не вендорены в этой копии репозитория")
def test_decodes_certificate_received_over_network():
    """Сертификат из сети разбирается через временный файл.

    Прежний способ (load_verify_locations + get_ca_certs) для не-CA
    сертификата молча отдаёт пустой список, а по сети мы получаем именно
    не-CA — серверный сертификат Точки. Тихо пустой результат здесь означал
    бы письмо «доверие сломалось» без указания нового издателя.
    """
    pem = (CERTS / "russian_trusted_root_ca.crt").read_text()
    info = decode_cert_der(ssl.PEM_cert_to_DER_cert(pem))
    assert info["notAfter"].endswith("2032 GMT")


# --- рукопожатие: главная проверка -----------------------------------------

def test_quiet_when_everything_works():
    need, reasons, _ = decide(obs(), {"last_issuer": ISSUER,
                                      "handshake_ok": True})
    assert need is False
    assert reasons == []


def test_mail_when_handshake_broken():
    need, reasons, flags = decide(
        obs(handshake_ok=False, handshake_error="SSLCertVerificationError: x"),
        {"last_issuer": ISSUER, "handshake_ok": True})
    assert need is True
    assert "не прошло" in reasons[0]
    assert flags["handshake_ok"] is False


def test_no_repeat_mail_while_handshake_stays_broken():
    """Неделя простоя не должна давать неделю одинаковых писем."""
    need, _, _ = decide(
        obs(handshake_ok=False, handshake_error="SSLCertVerificationError: x"),
        {"last_issuer": ISSUER, "handshake_ok": False})
    assert need is False


def test_mail_when_handshake_restored():
    need, reasons, flags = decide(obs(), {"last_issuer": ISSUER,
                                          "handshake_ok": False})
    assert need is True
    assert "восстановилось" in reasons[0]
    assert flags["handshake_ok"] is True


def test_network_failure_is_not_an_alarm_and_keeps_state():
    """Банк недоступен — сетевой сбой, а не отказ доверия.

    Состояние не перезаписывается: иначе таймаут выглядел бы как поломка,
    а следующий успешный запуск — как восстановление.
    """
    need, reasons, flags = decide(
        obs(handshake_ok=None, handshake_error="timeout", issuer="",
            leaf_days=None),
        {"last_issuer": ISSUER, "handshake_ok": True})
    assert need is False
    assert flags["handshake_ok"] is True


# --- смена издателя ---------------------------------------------------------

def test_mail_when_issuer_changed():
    need, reasons, _ = decide(obs(), {"last_issuer": OLD_ISSUER,
                                      "handshake_ok": True})
    assert need is True
    assert ISSUER in reasons[0]


def test_first_run_only_records_issuer():
    """Без сохранённого издателя сравнивать не с чем — письма быть не должно."""
    need, _, _ = decide(obs(), {})
    assert need is False


def test_no_mail_when_issuer_undetermined():
    need, _, _ = decide(obs(issuer=""), {"last_issuer": ISSUER,
                                         "handshake_ok": True})
    assert need is False


# --- сроки ------------------------------------------------------------------

def test_vendored_sub_expiry_never_alarms():
    """Регрессия на правку 2026-09-23.

    Вендоренная копия выпускающего истекает 2027-03-06, обновить её неоткуда
    (gu-st.ru отдаёт тот же сертификат), и в построении цепочки она не
    участвует — Точка присылает свой выпускающий. Тревога по ней была бы
    еженедельным письмом о несуществующей проблеме.
    """
    need, reasons, _ = decide(obs(sub_days=3),
                              {"last_issuer": ISSUER, "handshake_ok": True})
    assert need is False
    need, _, _ = decide(obs(sub_days=-30),
                        {"last_issuer": ISSUER, "handshake_ok": True})
    assert need is False


def test_mail_when_root_expiry_close():
    need, reasons, flags = decide(obs(root_days=59),
                                  {"last_issuer": ISSUER, "handshake_ok": True})
    assert need is True
    assert "Корневой" in reasons[0] and "59" in reasons[0]
    assert flags["root_warned"] is True


def test_root_expiry_warns_once_not_weekly():
    need, _, _ = decide(obs(root_days=59),
                        {"last_issuer": ISSUER, "handshake_ok": True,
                         "root_warned": True})
    assert need is False


def test_root_warning_rearms_after_renewal():
    """Поставили новый корень — флаг снимается, следующее истечение снова
    даст письмо."""
    _, _, flags = decide(obs(root_days=1980),
                         {"last_issuer": ISSUER, "handshake_ok": True,
                          "root_warned": True})
    assert flags["root_warned"] is False


def test_mail_when_bank_certificate_expires_soon():
    need, reasons, _ = decide(obs(leaf_days=10),
                              {"last_issuer": ISSUER, "handshake_ok": True})
    assert need is True
    assert "истекает через 10" in reasons[0]


def test_bank_certificate_warns_once():
    need, _, _ = decide(obs(leaf_days=10),
                        {"last_issuer": ISSUER, "handshake_ok": True,
                         "leaf_warned": True})
    assert need is False


def test_expired_root_still_warns():
    need, _, _ = decide(obs(root_days=-3),
                        {"last_issuer": ISSUER, "handshake_ok": True})
    assert need is True


# --- письмо -----------------------------------------------------------------

def test_html_is_self_sufficient():
    """Получатель не обязан помнить, где лежит процедура."""
    html = build_html(["причина"], obs(root_days=12))
    assert "fetch-russian-ca.sh" in html
    assert "gosuslugi.ru/crt" in html
    assert "openssl s_client" in html


def test_html_marks_vendored_sub_as_informational():
    """Прежнее письмо смешивало срок нашей копии с именем издателя Точки и
    читалось как «надо срочно обновлять». Теперь оговорка обязательна."""
    html = build_html(["причина"], obs())
    assert "в проверке цепочки не участвует" in html


def test_html_reports_broken_handshake_visibly():
    html = build_html(["причина"], obs(handshake_ok=False))
    assert "НЕ ПРОШЛО" in html
