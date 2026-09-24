"""Контроль доверия к API Точки: рукопожатие, издатель, сроки сертификатов.

Запуск (host cron, раз в неделю):
    docker compose exec -T backend python -m app.jobs.check_ca_expiry

Что наблюдаем и почему именно это (пересмотрено 2026-09-23):

1. РУКОПОЖАТИЕ тем же бандлом, что использует приложение (TOCHKA_SSL_VERIFY).
   Главная проверка. Счётчик дней отвечает на вопрос «когда сломается»,
   рукопожатие — на вопрос «работает ли сейчас». Доверие умеет отказать по
   причине, которой нет ни в одном счётчике: битый бандл после пересборки,
   переход банка на удостоверяющий центр, которого у нас нет, отзыв
   сертификата.

2. ИЗДАТЕЛЬ сертификата enter.tochka.com. Вебхука об этом не существует,
   узнать можно только опросом. 30 августа 2026 Точка перешла с TrustAsia на
   НУЦ Минцифры — именно эта проверка и заметила переход.

3. Срок КОРНЕВОГО сертификата НУЦ Минцифры (до 2032-02-27). Единственный
   якорь доверия на нашей стороне: цепочку Точка присылает целиком, включая
   выпускающий, и проверка упирается в наш корень.

4. Срок серверного сертификата Точки. Обновляет его банк, действий с нашей
   стороны нет, но близкое истечение — ранний признак, что у банка что-то
   идёт не так.

Чего здесь СОЗНАТЕЛЬНО больше нет: тревоги по сроку вендоренной копии
выпускающего сертификата. Проверено 2026-09-13 и 2026-09-23 — Точка присылает
свой выпускающий (выпуск 2024-07-15, до 2029-07-19), а на gu-st.ru лежит
предыдущее поколение (серийный 1002, до 2027-03-06), то самое, что вендорено
у нас. В построении цепочки наша копия не участвует, обновить её неоткуда, и
тревога по ней с 5 января 2027 была бы еженедельным письмом о несуществующей
проблеме. Срок копии остался в письме и логе как справка, без порога.

Недоступность банка — не повод для письма: это сетевой сбой, он лечится сам.
Отличаем по типу исключения: ошибка TLS — проблема доверия, ошибка сокета —
проблема связи. ssl.SSLError наследуется от OSError, поэтому порядок except
имеет значение.

Письма шлются по СМЕНЕ состояния, как в остальном мониторинге: «сломалось» и
потом «починилось», а не еженедельное повторение одного и того же.
Состояние — ca_check.json в volume uploads.
"""
from __future__ import annotations

import asyncio
import os
import socket
import ssl
import sys
import tempfile
from dataclasses import dataclass
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
TOCHKA_BUNDLE = os.environ.get(
    "TOCHKA_SSL_VERIFY", "/etc/ssl/tochka/tochka-ca-bundle.pem")

WARN_DAYS = settings.ca_expiry_warn_days
LEAF_WARN_DAYS = int(os.environ.get("CA_LEAF_WARN_DAYS", "14"))


@dataclass
class Observation:
    """Снимок наблюдаемого состояния. Без сети и почты — чтобы решение о
    письме проверялось тестом, а не боевым запуском раз в год."""

    root_days: int
    sub_days: int | None
    handshake_ok: bool | None  # True — прошло, False — доверие, None — сеть
    handshake_error: str
    issuer: str
    leaf_days: int | None


def decode_cert_file(path: Path | str) -> dict:
    """Разбор сертификата из файла средствами стандартной библиотеки.

    Через _ssl._test_decode_cert, а НЕ через load_verify_locations() +
    get_ca_certs(): второй способ молча отдаёт пустой список для не-CA
    сертификата — проверено, OpenSSL кладёт в X509_STORE только CA. Нам же
    нужен разбор именно серверного (не-CA) сертификата Точки, и тихо пустой
    результат здесь хуже исключения.

    Функция приватная, но это ровно то, чем пользуется сам модуль ssl, и она
    не менялась во всей линейке 3.x. Если её однажды уберут, задача упадёт на
    запуске с трассировкой в логе, а не соврёт результатом.
    """
    import _ssl

    return _ssl._test_decode_cert(str(path))


def decode_cert_der(der: bytes) -> dict:
    """То же для сертификата, полученного по сети: _test_decode_cert умеет
    только файл, поэтому кладём PEM во временный."""
    with tempfile.NamedTemporaryFile(
            "w", suffix=".pem", delete=False, encoding="ascii") as f:
        f.write(ssl.DER_cert_to_PEM_cert(der))
        tmp = f.name
    try:
        return decode_cert_file(tmp)
    finally:
        os.unlink(tmp)


def cert_not_after(path: Path) -> datetime:
    """Дата истечения сертификата из файла, в UTC.

    ssl.cert_time_to_seconds разбирает формат OpenSSL («Mar  6 11:25:19 2027
    GMT») — свой парсер строки писать не нужно, а strptime на нём спотыкается
    из-за двойного пробела в однозначных числах месяца.
    """
    return not_after_from_info(decode_cert_file(path))


def not_after_from_info(info: dict) -> datetime:
    return datetime.fromtimestamp(
        ssl.cert_time_to_seconds(info["notAfter"]), tz=UTC)


def days_left(not_after: datetime, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    return (not_after - now).days


def issuer_cn(cert: dict) -> str:
    """CN издателя. Издатель серверного сертификата — это и есть выпускающий
    CA, то самое, что меняется при переходе банка на другой УЦ."""
    for rdn in cert.get("issuer", ()):
        for key, value in rdn:
            if key == "commonName":
                return value
    return ""


def probe(host: str = TOCHKA_HOST, bundle: str | None = None,
          verify: bool = True, timeout: int = 15) -> dict:
    """Рукопожатие с host и разбор серверного сертификата.

    verify=True с bundle — ровно то доверие, которым пользуется приложение.
    verify=False — диагностический опрос: когда доверие сломалось, всё равно
    нужно знать, кто стал новым издателем, иначе письмо сообщает о поломке,
    но не о причине.
    """
    if verify:
        ctx = (ssl.create_default_context(cafile=bundle) if bundle
               else ssl.create_default_context())
    else:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    with (
        socket.create_connection((host, 443), timeout=timeout) as sock,
        ctx.wrap_socket(sock, server_hostname=host) as tls,
    ):
        cert = tls.getpeercert()
        if cert:
            return cert
        # Без проверки getpeercert() отдаёт None — берём DER и разбираем сами.
        der = tls.getpeercert(binary_form=True)
    return decode_cert_der(der) if der else {}


def observe() -> Observation:
    root_days = days_left(cert_not_after(ROOT_CERT))
    sub_days = days_left(cert_not_after(SUB_CERT)) if SUB_CERT.is_file() else None

    handshake_ok: bool | None = True
    error = ""
    cert: dict = {}
    bundle = TOCHKA_BUNDLE if Path(TOCHKA_BUNDLE).is_file() else None

    try:
        cert = probe(bundle=bundle)
    except ssl.SSLError as e:           # раньше OSError: SSLError его потомок
        handshake_ok = False
        error = f"{type(e).__name__}: {e}"
    except OSError as e:
        handshake_ok = None
        error = f"{type(e).__name__}: {e}"

    if handshake_ok is False:
        try:
            cert = probe(verify=False)
        except Exception as e:
            error += f"; диагностический опрос не удался ({type(e).__name__})"

    leaf_days = (days_left(not_after_from_info(cert))
                 if cert.get("notAfter") else None)

    return Observation(
        root_days=root_days,
        sub_days=sub_days,
        handshake_ok=handshake_ok,
        handshake_error=error,
        issuer=issuer_cn(cert) if cert else "",
        leaf_days=leaf_days,
    )


def decide(obs: Observation, state: dict,
           warn_days: int = WARN_DAYS,
           leaf_warn_days: int = LEAF_WARN_DAYS) -> tuple[bool, list[str], dict]:
    """Нужно ли письмо, по каким причинам и каким станет состояние.

    Чистая функция без сети и почты: решение «слать/не слать» — единственное
    место, где задача ошибается молча, либо не предупредив, либо завалив
    почту еженедельным повтором.
    """
    reasons: list[str] = []
    last_issuer = state.get("last_issuer")
    last_ok = state.get("handshake_ok")

    flags = {
        "handshake_ok": last_ok if obs.handshake_ok is None else obs.handshake_ok,
        "root_warned": bool(state.get("root_warned")),
        "leaf_warned": bool(state.get("leaf_warned")),
    }

    # 1. Рукопожатие. Сетевой сбой (None) молчит и состояние не меняет.
    if obs.handshake_ok is False and last_ok is not False:
        reasons.append(
            f"Рукопожатие с {TOCHKA_HOST} не прошло: {obs.handshake_error}. "
            "Оплата через банк сейчас не работает.")
    elif obs.handshake_ok is True and last_ok is False:
        reasons.append(f"Рукопожатие с {TOCHKA_HOST} восстановилось.")

    # 2. Смена издателя. На первом запуске сравнивать не с чем — молчим.
    if last_issuer and obs.issuer and obs.issuer != last_issuer:
        reasons.append(
            f"Сменился издатель сертификата {TOCHKA_HOST}: "
            f"было «{last_issuer}», стало «{obs.issuer}».")

    # 3. Корень — якорь доверия. Предупреждаем один раз, а не каждую неделю.
    if obs.root_days < warn_days:
        if not state.get("root_warned"):
            reasons.append(
                "Корневой сертификат НУЦ Минцифры истекает через "
                f"{obs.root_days} дн. Это якорь доверия: после истечения "
                "платежи откажут.")
        flags["root_warned"] = True
    else:
        flags["root_warned"] = False

    # 4. Сертификат банка. Обновляет Точка, но знать заранее полезно.
    if obs.leaf_days is not None:
        if obs.leaf_days < leaf_warn_days:
            if not state.get("leaf_warned"):
                reasons.append(
                    f"Сертификат {TOCHKA_HOST} истекает через "
                    f"{obs.leaf_days} дн. Обновляет его банк; если не обновит, "
                    "оплата встанет.")
            flags["leaf_warned"] = True
        else:
            flags["leaf_warned"] = False

    return bool(reasons), reasons, flags


def build_html(reasons: list[str], obs: Observation) -> str:
    items = "".join(f"<li>{r}</li>" for r in reasons)
    hs = {True: "прошло", False: "НЕ ПРОШЛО",
          None: "не проверено (сетевой сбой)"}[obs.handshake_ok]
    leaf = f"{obs.leaf_days} дн." if obs.leaf_days is not None else "неизвестно"
    sub = f"{obs.sub_days} дн." if obs.sub_days is not None else "нет файла"
    return (
        "<p><b>64 ДАО — проверка доверия к API Точки</b></p>"
        f"<ul>{items}</ul>"
        "<p><b>Состояние</b><br>"
        f"Рукопожатие с {TOCHKA_HOST}: {hs}<br>"
        f"Издатель сертификата {TOCHKA_HOST}: {obs.issuer or 'не определён'}<br>"
        f"Сертификат {TOCHKA_HOST} истекает через: {leaf}<br>"
        f"Корневой сертификат НУЦ Минцифры: {obs.root_days} дн.<br>"
        f"Вендоренная копия выпускающего: {sub} — в проверке цепочки "
        "не участвует, приведена справочно</p>"
        "<p><b>Что делать</b><br>"
        "• Рукопожатие не прошло или сменился издатель — DEPLOY.md, раздел 8a. "
        "Живая цепочка:<br>"
        f"<code>echo | openssl s_client -connect {TOCHKA_HOST}:443 "
        f"-servername {TOCHKA_HOST} -showcerts 2&gt;/dev/null | "
        "grep -E '^ *[0-9]+ s:|^ *i:|NotAfter'</code><br>"
        "• Истекает корневой сертификат — "
        "<code>./deploy/scripts/fetch-russian-ca.sh</code>, сверить отпечатки "
        "с gosuslugi.ru/crt, коммит, <code>docker compose build backend</code>, "
        "<code>up -d</code>, приёмка платежом 1 ₽ и возврат через "
        "/admin/orders<br>"
        f"• Истекает сертификат {TOCHKA_HOST} — действий с нашей стороны нет, "
        "обновляет банк</p>"
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
    if not ROOT_CERT.is_file():
        print(f"ОШИБКА: нет корневого сертификата в {CERT_DIR}. "
              "Образ собран без него — см. DEPLOY.md, раздел 8a.",
              file=sys.stderr)
        return 1

    obs = observe()
    state = read_json(STATE_FILE, {})

    hs = {True: "прошло", False: "НЕ ПРОШЛО", None: "не проверено (сеть)"}
    print(f"рукопожатие с {TOCHKA_HOST}: {hs[obs.handshake_ok]}"
          + (f" — {obs.handshake_error}" if obs.handshake_error else ""))
    print(f"издатель: {obs.issuer or 'не определён'} "
          f"(в прошлый раз: {state.get('last_issuer') or 'нет данных'})")
    print(f"сертификат банка: "
          f"{obs.leaf_days if obs.leaf_days is not None else '?'} дн., "
          f"корневой CA: {obs.root_days} дн.")
    print(f"вендоренная копия выпускающего: "
          f"{obs.sub_days if obs.sub_days is not None else 'нет файла'} дн. "
          "(справочно, в проверке цепочки не участвует)")

    need_mail, reasons, flags = decide(obs, state)
    if need_mail:
        for r in reasons:
            print(f"ВНИМАНИЕ: {r}")
        asyncio.run(_notify("64 ДАО: доверие к API Точки требует внимания",
                            build_html(reasons, obs)))
    else:
        print("действий не требуется")

    new_state = {**state, **flags,
                 "checked_at": datetime.now(UTC).isoformat()}
    # Издателя запоминаем, только если он определён: иначе сетевой сбой
    # сотрёт память и следующий успешный запуск промолчит о смене.
    if obs.issuer:
        new_state["last_issuer"] = obs.issuer
    write_json(STATE_FILE, new_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
