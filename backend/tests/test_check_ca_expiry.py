"""Проверка сертификатов: расчёт срока и решение «слать письмо или нет».

Сеть и почта здесь не участвуют намеренно. Решение о письме — единственное
место, где задача может ошибиться молча: не отправить предупреждение или
завалить почту еженедельным спамом. Боевым запуском это проверяется один
раз в год, тестом — на каждом прогоне.
"""
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.jobs.check_ca_expiry import (
    build_html,
    cert_not_after,
    days_left,
    decide,
)

CERTS = Path(__file__).resolve().parents[1] / "certs"
NOW = datetime(2026, 8, 18, tzinfo=UTC)


def test_days_left_counts_from_given_moment():
    assert days_left(NOW + timedelta(days=200), now=NOW) == 200
    assert days_left(NOW - timedelta(days=1), now=NOW) == -1


@pytest.mark.skipif(not (CERTS / "russian_trusted_sub_ca.crt").is_file(),
                    reason="сертификаты не вендорены в этой копии репозитория")
def test_reads_real_vendored_certs():
    """Разбор идёт через ssl, а не через свой парсер строки даты.

    OpenSSL печатает notAfter как «Mar  6 11:25:19 2027 GMT» — с двойным
    пробелом для однозначного числа, на котором strptime спотыкается.
    """
    sub = cert_not_after(CERTS / "russian_trusted_sub_ca.crt")
    root = cert_not_after(CERTS / "russian_trusted_root_ca.crt")
    assert sub.year == 2027 and sub.month == 3
    assert root.year == 2032
    # Выпускающий истекает раньше корневого — именно он и определяет срок
    # следующего обслуживания.
    assert sub < root


def test_no_mail_when_far_from_expiry_and_issuer_unchanged():
    need, reasons = decide(200, "TrustAsia DV TLS RSA CA 2024",
                           "TrustAsia DV TLS RSA CA 2024")
    assert need is False
    assert reasons == []


def test_mail_when_expiry_close():
    need, reasons = decide(59, "TrustAsia DV TLS RSA CA 2024",
                           "TrustAsia DV TLS RSA CA 2024")
    assert need is True
    assert "59" in reasons[0]


def test_mail_when_issuer_changed():
    """Переход Точки на НУЦ Минцифры меняет приоритет задачи со срочностью."""
    need, reasons = decide(200, "Russian Trusted Sub CA",
                           "TrustAsia DV TLS RSA CA 2024")
    assert need is True
    assert "Russian Trusted Sub CA" in reasons[0]


def test_first_run_only_records_issuer():
    """Без сохранённого издателя письма быть не должно.

    Иначе первый же запуск после установки задачи отправляет ложную тревогу
    «издатель изменился» — сравнивать не с чем.
    """
    need, reasons = decide(200, "TrustAsia DV TLS RSA CA 2024", None)
    assert need is False


def test_no_mail_when_probe_failed():
    """Банк недоступен — это сетевой сбой, а не смена CA."""
    need, reasons = decide(200, "", "TrustAsia DV TLS RSA CA 2024")
    assert need is False


def test_expired_certificate_still_warns():
    need, reasons = decide(-3, "TrustAsia DV TLS RSA CA 2024",
                           "TrustAsia DV TLS RSA CA 2024")
    assert need is True


def test_html_contains_procedure_link():
    html = build_html(["причина"], 12, "TrustAsia DV TLS RSA CA 2024")
    # Письмо должно быть самодостаточным: получатель не обязан помнить,
    # где лежит процедура.
    assert "fetch-russian-ca.sh" in html
    assert "gosuslugi.ru/crt" in html
