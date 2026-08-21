"""Контроль места на диске, размера базы и состояния бэкапов.

Запуск (host cron, раз в сутки):
    bash deploy/scripts/check-storage.sh

Почему в два слоя. Бэкапы лежат на хосте (`/var/backups/64dao`), а диск —
это диск хоста; контейнер ни того, ни другого не видит. Поэтому факты
собирает скрипт на хосте и передаёт сюда переменными окружения, а правила,
пороги и письмо живут здесь — рядом с остальными задачами и общим SMTP.

Что проверяется:
  1. Свободное место на диске.
  2. Возраст последнего дампа БД: бэкап мог перестать делаться молча.
  3. Размер последнего дампа: пустой архив выглядит как успешный бэкап,
     пока не понадобится восстановление.
  4. Резкое падение размера дампа: pg_dump, прерванный на середине, тоже
     оставляет файл — просто короче обычного.
  5. То же для архива uploads.

Размер базы задача берёт сама, запросом к Postgres: сравнить его с местом
на диске полезно, когда решаешь, доживёт ли сервер до следующей уборки.

Письмо уходит на support_email при СМЕНЕ состояния, как у smoke_prod:
о продолжающейся проблеме повторных писем нет. Состояние —
storage_state.json в volume uploads.

Настройки (все необязательны):
  STORAGE_DISK_WARN_PERCENT — сколько процентов свободного места считать
    тревогой (по умолчанию 15);
  BACKUP_MAX_AGE_HOURS      — старше этого бэкап считается несделанным (26,
    с запасом к суточному расписанию);
  BACKUP_MIN_BYTES          — меньше этого дамп считается пустым (10240);
  BACKUP_SHRINK_PERCENT     — на сколько процентов дамп может усохнуть
    относительно предыдущего, прежде чем это станет тревогой (50).
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime

from sqlalchemy import text

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.json_store import read_json, write_json

logger = logging.getLogger(__name__)
settings = get_settings()

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
STATE_FILE = os.path.join(UPLOAD_DIR, "storage_state.json")
DEFAULT_STATE = {"status": "unknown", "since": None, "checked_at": None}


def _setting(name: str, default: float) -> float:
    """Пустая строка — это «не задано»: docker compose передаёт переменные и
    без значения, и float("") уронил бы задачу вместо проверки."""
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


DISK_WARN_PERCENT = _setting("STORAGE_DISK_WARN_PERCENT", 15)
BACKUP_MAX_AGE_HOURS = _setting("BACKUP_MAX_AGE_HOURS", 26)
BACKUP_MIN_BYTES = int(_setting("BACKUP_MIN_BYTES", 10240))
BACKUP_SHRINK_PERCENT = _setting("BACKUP_SHRINK_PERCENT", 50)

# Что должен передать скрипт с хоста.
HOST_VARS = (
    "DISK_FREE_PERCENT",
    "DB_BACKUP_AGE_MIN", "DB_BACKUP_SIZE", "DB_BACKUP_PREV_SIZE",
    "UP_BACKUP_AGE_MIN", "UP_BACKUP_SIZE",
)


def human(size: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024 or unit == "ГБ":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ГБ"


def _num(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def check_backup(kind: str, age_min: float | None, size: float | None,
                 prev_size: float | None) -> list[str]:
    problems: list[str] = []
    if age_min is None or size is None:
        problems.append(f"{kind}: нет данных о последнем бэкапе — файла нет или каталог пуст")
        return problems

    if age_min > BACKUP_MAX_AGE_HOURS * 60:
        problems.append(
            f"{kind}: последний бэкап сделан {age_min / 60:.1f} ч назад — "
            f"дольше допустимых {BACKUP_MAX_AGE_HOURS:.0f} ч"
        )
    if size < BACKUP_MIN_BYTES:
        problems.append(
            f"{kind}: размер последнего бэкапа {human(size)} — это пустой архив"
        )
    elif prev_size and prev_size > 0:
        shrink = (prev_size - size) / prev_size * 100
        if shrink > BACKUP_SHRINK_PERCENT:
            problems.append(
                f"{kind}: бэкап усох на {shrink:.0f}% "
                f"({human(prev_size)} → {human(size)}) — похоже на прерванный дамп"
            )
    return problems


async def db_size_bytes() -> int | None:
    try:
        async with AsyncSessionLocal() as session:
            return await session.scalar(
                text("SELECT pg_database_size(current_database())")
            )
    except Exception:
        logger.exception("не удалось получить размер базы")
        return None


async def collect_problems() -> tuple[list[str], list[str]]:
    """Возвращает (проблемы, строки отчёта)."""
    problems: list[str] = []
    report: list[str] = []

    if not any(os.environ.get(v, "").strip() for v in HOST_VARS):
        # Ручной запуск внутри контейнера без скрипта: данных с хоста нет.
        # Это не авария, но и проверить нечего — говорим об этом прямо.
        report.append("данные с хоста не переданы: запускайте через "
                      "deploy/scripts/check-storage.sh")
        size = await db_size_bytes()
        if size:
            report.append(f"размер базы: {human(size)}")
        return problems, report

    free_percent = _num("DISK_FREE_PERCENT")
    if free_percent is None:
        problems.append("диск: скрипт не передал долю свободного места")
    else:
        report.append(f"свободно на диске: {free_percent:.0f}%")
        if free_percent < DISK_WARN_PERCENT:
            problems.append(
                f"диск: свободно {free_percent:.0f}% — меньше порога "
                f"{DISK_WARN_PERCENT:.0f}%"
            )

    problems += check_backup("бэкап БД", _num("DB_BACKUP_AGE_MIN"),
                             _num("DB_BACKUP_SIZE"), _num("DB_BACKUP_PREV_SIZE"))
    problems += check_backup("бэкап uploads", _num("UP_BACKUP_AGE_MIN"),
                             _num("UP_BACKUP_SIZE"), None)

    db_size = _num("DB_BACKUP_SIZE")
    if db_size:
        report.append(f"последний дамп БД: {human(db_size)}")

    size = await db_size_bytes()
    if size:
        report.append(f"размер базы: {human(size)}")

    return problems, report


def build_html(problems: list[str], report: list[str]) -> str:
    rows = "".join(f"<li>{p}</li>" for p in problems)
    facts = "".join(f"<li>{r}</li>" for r in report)
    return (
        f"<h2>64 ДАО: хранилище требует внимания</h2><ul>{rows}</ul>"
        f"<h3>Показатели</h3><ul>{facts}</ul>"
        f"<p>Повторных писем об этой же проблеме не будет — следующее придёт, "
        f"когда всё вернётся в норму.</p>"
    )


def build_recovery_html(report: list[str]) -> str:
    facts = "".join(f"<li>{r}</li>" for r in report)
    return (f"<h2>64 ДАО: с хранилищем снова порядок</h2>"
            f"<h3>Показатели</h3><ul>{facts}</ul>")


async def _notify(subject: str, html: str) -> None:
    from app.email import _send_message

    to = settings.support_email_address
    if not to or not settings.smtp_host:
        print("SMTP или support_email не настроены — письмо не отправлено")
        return
    await _send_message(to, subject, html)
    print(f"письмо отправлено на {to}")


async def main() -> int:
    now = datetime.now(UTC).isoformat()
    state = read_json(STATE_FILE, DEFAULT_STATE)
    was_failing = state.get("status") == "fail"

    problems, report = await collect_problems()
    for line in report:
        print(line)

    if problems:
        print(f"ПРОБЛЕМЫ ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        if not was_failing:
            await _notify("64 ДАО: хранилище требует внимания",
                          build_html(problems, report))
        else:
            print("письмо не шлём: об этом уже сообщали")
        write_json(STATE_FILE, {"status": "fail", "since": state.get("since") or now,
                                "checked_at": now})
        return 1

    print("хранилище в порядке")
    if was_failing:
        await _notify("64 ДАО: с хранилищем снова порядок", build_recovery_html(report))
    write_json(STATE_FILE, {"status": "ok", "since": None, "checked_at": now})
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
