"""Контроль срока сертификатов НУЦ Минцифры и смены CA у Точки.

Запуск (host cron, раз в неделю):
    docker compose exec -T backend python -m app.jobs.check_ca_expiry

Зачем два разных наблюдения в одной задаче:

1. Срок выпускающего сертификата. На 2026-08 он истекает 2027-03-06.
   Сам по себе истёкший intermediate вряд ли что-то сломает: для проверки
   сервера нужен КОРНЕВОЙ сертификат (действует до 2032), а выпускающий
   сервер присылает в составе цепочки. Но устаревшая копия intermediate в
   хранилище умеет ломать построение цепочки — так в 2020–2021 падали
   клиенты на AddTrust и DST Root X3. Это плановое обслуживание, а не
   ожидаемая авария.

2. Кто сейчас выпустил сертификат enter.tochka.com. На 2026-08 это
   TrustAsia, чей корень есть в certifi. Переход Точки на НУЦ Минцифры
   меняет приоритет: обновление становится срочным, а тихую подсказку на
   странице покупки пора менять на явное предупреждение (см. DEPLOY.md,
   раздел 8a). Вебхука об этом не существует — узнать можно только опросом.

Письмо уходит на support_email при выполнении любого условия:
  - до истечения выпускающего меньше CA_EXPIRY_WARN_DAYS (по умолчанию 60);
  - издатель сертификата Точки отличается от запомненного в прошлый запуск.

Состояние (последний известный издатель) лежит в ca_check.json в volume
uploads — рядом с остальными рантайм-настройками.
"""
from __future__ import annotations

import asyncio
import os
import socket
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.json_store import read_json, write_json

settings = get_settings()

CERT_DIR = Path(os.environ.get(
    "RUSSIAN_CA_DIR", "/usr/local/share/ca-certificates/russian-trusted"))
SUB_CERT = CERT_DIR / "russian_trusted_sub_ca.crt"
ROOT_CERT = CERT_DIR / "russian_trusted_root_ca.crt"

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
STATE_FILE = Path(UPLOAD_DIR) / "ca_check.json"

TOCHKA_HOST = "enter.tochka.com"
WARN_DAYS = settings.ca_expiry_warn_days


def cert_not_after(path: Path) -> datetime:
    """Дата истечения сертификата в UTC.

    ssl.cert_time_to_seconds разбирает формат OpenSSL ("Mar  6 11:25:19 2027
    GMT") — свой парсер строки писать не нужно, а strptime на нём спотыкается
    из-за двойного пробела в однозначных числах месяца.
    """
    pem = path.read_text(encoding="ascii", errors="ignore")
    der = ssl.PEM_cert_to_DER_cert(pem)
    # _ssl._test_decode_cert требует файл, поэтому берём готовый разбор ssl
    # через временную загрузку в контекст: он отдаёт notAfter в том же формате.
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cadata=der)
    (info,) = ctx.get_ca_certs()
    return datetime.fromtimestamp(
        ssl.cert_time_to_seconds(info["notAfter"]), tz=UTC)


def days_left(not_after: datetime, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    return (not_after - now).days


def probe_issuer(host: str = TOCHKA_HOST, bundle: str | None = None) -> str:
    """CN издателя сертификата host.

    Издатель серверного сертификата — это и есть выпускающий CA, то самое,
    что меняется при переходе банка на другой удостоверяющий центр.
    """
    ctx = ssl.create_default_context()
    if bundle:
        ctx.load_verify_locations(bundle)
    with socket.create_connection((host, 443), timeout=15) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            cert = tls.getpeercert() or {}
    for rdn in cert.get("issuer", ()):
        for key, value in rdn:
            if key == "commonName":
                return value
    return ""


def decide(sub_days: int, issuer: str, last_issuer: str | None,
           warn_days: int = WARN_DAYS) -> tuple[bool, list[str]]:
    """Нужно ли письмо и по каким причинам.

    Вынесено отдельной функцией без сети и почты — иначе решение
    «слать/не слать» проверяется только боевым запуском.
    """
    reasons: list[str] = []
    if sub_days < warn_days:
        reasons.append(
            f"Выпускающий сертификат НУЦ Минцифры истекает через {sub_days} дн.")
    if last_issuer and issuer and issuer != last_issuer:
        reasons.append(
            f"Сменился издатель сертификата {TOCHKA_HOST}: "
            f"было «{last_issuer}», стало «{issuer}».")
    return bool(reasons), reasons


def build_html(reasons: list[str], sub_days: int, issuer: str) -> str:
    items = "".join(f"<li>{r}</li>" for r in reasons)
    return (
        "<p><b>64 ДАО — проверка сертификатов</b></p>"
        f"<ul>{items}</ul>"
        f"<p>Выпускающий CA: осталось {sub_days} дн.<br>"
        f"Издатель сертификата {TOCHKA_HOST}: {issuer or 'не определён'}</p>"
        "<p>Что делать — DEPLOY.md, раздел 8a, подраздел «Обслуживание»:<br>"
        "1. <code>./deploy/scripts/fetch-russian-ca.sh</code><br>"
        "2. сверить отпечатки с gosuslugi.ru/crt<br>"
        "3. если изменились — коммит, <code>docker compose build backend</code>, "
        "<code>up -d</code><br>"
        "4. приёмка тестовым платежом 1 ₽ и возврат через /admin/orders</p>"
    )


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


def main() -> int:
    if not SUB_CERT.is_file() or not ROOT_CERT.is_file():
        print(f"ОШИБКА: нет сертификатов в {CERT_DIR}. "
              "Образ собран без них — см. DEPLOY.md, раздел 8a.", file=sys.stderr)
        return 1

    sub_days = days_left(cert_not_after(SUB_CERT))
    root_days = days_left(cert_not_after(ROOT_CERT))

    try:
        issuer = probe_issuer()
    except Exception as e:
        # Недоступность банка — не повод падать: срок сертификата проверить
        # всё равно нужно, а сетевые сбои лечатся сами.
        print(f"не удалось опросить {TOCHKA_HOST}: {type(e).__name__}: {e}")
        issuer = ""

    state = read_json(STATE_FILE, {"last_issuer": None})
    last_issuer = state.get("last_issuer")

    print(f"корневой CA: {root_days} дн., выпускающий CA: {sub_days} дн.")
    print(f"издатель {TOCHKA_HOST}: {issuer or 'не определён'} "
          f"(в прошлый раз: {last_issuer or 'нет данных'})")

    need_mail, reasons = decide(sub_days, issuer, last_issuer)
    if need_mail:
        for r in reasons:
            print(f"ВНИМАНИЕ: {r}")
        asyncio.run(_notify("64 ДАО: сертификаты требуют внимания",
                            build_html(reasons, sub_days, issuer)))
    else:
        print("действий не требуется")

    # Запоминаем издателя даже без письма: первый запуск только фиксирует
    # исходное состояние, письмо пойдёт со следующего изменения.
    if issuer:
        write_json(STATE_FILE, {**state, "last_issuer": issuer,
                                "checked_at": datetime.now(UTC).isoformat()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
