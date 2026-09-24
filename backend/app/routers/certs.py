"""Раздел «Сертификаты» в админке: что лежит в бандле и работает ли доверие.

Только чтение. Загрузки сертификатов через админку здесь нет и не планируется:
интерфейс, умеющий добавлять корневые CA, — это интерфейс загрузки якорей
доверия. Получивший доступ к админке добавляет свой CA и встаёт между нами и
банком, а JWT Точки уходит в заголовке Authorization. Обновление корня нужно
примерно раз в шесть лет и делается на сервере: fetch-russian-ca.sh, сверка
отпечатков с gosuslugi.ru/crt, пересборка образа. Постоянный риск ради
операции раз в несколько лет — плохой обмен.

Данные берутся из app.jobs.check_ca_expiry — той же observe(), что работает в
еженедельной задаче. Страница и письмо не должны расходиться в том, что
считают нормой: два независимых определения «всё хорошо» рано или поздно
разъезжаются, и тогда непонятно, какому верить.
"""
from __future__ import annotations

import hashlib
import ssl
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from app.auth import require_admin
from app.jobs.check_ca_expiry import (
    CERT_DIR,
    LEAF_WARN_DAYS,
    ROOT_CERT,
    STATE_FILE,
    SUB_CERT,
    TOCHKA_BUNDLE,
    TOCHKA_HOST,
    WARN_DAYS,
    days_left,
    decode_cert_file,
    not_after_from_info,
    observe,
)
from app.json_store import read_json
from app.models import User

router = APIRouter()


def _cn(rdns) -> str:
    for rdn in rdns or ():
        for key, value in rdn:
            if key == "commonName":
                return value
    return ""


def _card(path: Path, role: str) -> dict | None:
    """Карточка сертификата из файла: кто, до какой даты, отпечаток.

    Отпечаток приводится в том же виде, что печатает openssl, — чтобы сверить
    его с gosuslugi.ru/crt, не заходя на сервер. Это ровно та процедура, что
    описана в DEPLOY.md, раздел 8a.

    role различает два файла по смыслу, а не по имени:
      anchor        — корень, единственный якорь доверия на нашей стороне;
      informational — вендоренная копия выпускающего. В построении цепочки не
                      участвует: Точка присылает свой выпускающий сама, и он
                      другого поколения (до 2029 против нашего до 2027).
                      Лежит как страховка, сроком не управляет ничем.
    """
    if not path.is_file():
        return None
    pem = path.read_text(encoding="ascii", errors="ignore")
    der = ssl.PEM_cert_to_DER_cert(pem)
    info = decode_cert_file(path)
    not_after = not_after_from_info(info)
    digest = hashlib.sha256(der).hexdigest().upper()
    return {
        "file": path.name,
        "role": role,
        "subject": _cn(info.get("subject")),
        "issuer": _cn(info.get("issuer")),
        "not_after": not_after.isoformat(),
        "days_left": days_left(not_after),
        "sha256": ":".join(digest[i:i + 2] for i in range(0, len(digest), 2)),
    }


def _bundle_exists() -> bool:
    """Отдельной синхронной функцией: вызов Path.is_file() прямо в async-
    обработчике ruff запрещает (ASYNC240), и CI падал на этой строке.
    Проверка — один stat локального файла, пул потоков ей не нужен."""
    return Path(TOCHKA_BUNDLE).is_file()


@router.get("/api/admin/certs")
async def read_certs(
    probe: bool = Query(True, description="опрашивать банк вживую"),
    admin: User = Depends(require_admin),
):
    """Состояние доверия к API банка.

    probe=0 отдаёт только сроки из файлов и результат последней плановой
    проверки — мгновенно. Живой опрос ждёт до 15 секунд, если банк не
    отвечает, и держать на этом открытие страницы незачем: рукопожатие
    запускается кнопкой, когда его действительно хотят.

    observe() блокирующая (socket + ssl), поэтому уходит в пул потоков.
    Иначе один медленный ответ банка встал бы поперёк всего event loop, и
    раздел диагностики сам стал бы причиной недоступности сайта.
    """
    data: dict = {
        "host": TOCHKA_HOST,
        "bundle": TOCHKA_BUNDLE,
        "bundle_exists": _bundle_exists(),
        "cert_dir": str(CERT_DIR),
        "warn_days": WARN_DAYS,
        "leaf_warn_days": LEAF_WARN_DAYS,
        "root": _card(ROOT_CERT, "anchor"),
        "sub": _card(SUB_CERT, "informational"),
        "last_check": read_json(STATE_FILE, {}),
        "probe": None,
    }

    if probe:
        obs = await run_in_threadpool(observe)
        data["probe"] = {
            # None означает «не удалось проверить»: сетевой сбой, а не отказ
            # доверия. Три состояния, не два — иначе таймаут банка на странице
            # выглядит как поломка сертификатов.
            "handshake_ok": obs.handshake_ok,
            "handshake_error": obs.handshake_error,
            "issuer": obs.issuer,
            "leaf_days": obs.leaf_days,
        }

    return data
