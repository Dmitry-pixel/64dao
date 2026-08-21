"""Контроль диска и бэкапов (app/jobs/check_storage.py).

Проверяются правила, а не сбор данных: цифры с хоста приходят переменными
окружения, поэтому тест просто подставляет их. Отдельно проверяется главное
свойство бэкапа — что «файл существует» недостаточно.
"""
import pytest

import app.jobs.check_storage as job

MB = 1024 * 1024


@pytest.fixture(autouse=True)
def no_db(monkeypatch):
    """Размер базы берётся из Postgres — в этих тестах он не нужен."""
    async def fake_size():
        return 120 * MB

    monkeypatch.setattr(job, "db_size_bytes", fake_size)


@pytest.fixture
def host_env(monkeypatch):
    """Здоровая картина с хоста; отдельные значения тест переопределяет."""
    def apply(**over):
        values = {
            "DISK_FREE_PERCENT": "42",
            "DB_BACKUP_AGE_MIN": "300",
            "DB_BACKUP_SIZE": str(50 * MB),
            "DB_BACKUP_PREV_SIZE": str(49 * MB),
            "UP_BACKUP_AGE_MIN": "300",
            "UP_BACKUP_SIZE": str(200 * MB),
        }
        values.update({k: str(v) for k, v in over.items()})
        for k, v in values.items():
            monkeypatch.setenv(k, v)

    return apply


@pytest.mark.asyncio
async def test_healthy_storage_has_no_problems(host_env):
    host_env()
    problems, report = await job.collect_problems()
    assert problems == []
    assert any("размер базы" in r for r in report)


@pytest.mark.asyncio
async def test_low_disk_space_is_reported(host_env):
    host_env(DISK_FREE_PERCENT="7")
    problems, _ = await job.collect_problems()
    assert len(problems) == 1
    assert "диск" in problems[0]


@pytest.mark.asyncio
async def test_stale_backup_is_reported(host_env):
    """Бэкап мог перестать делаться молча — узнаём по возрасту файла."""
    host_env(DB_BACKUP_AGE_MIN=60 * 40)  # 40 часов
    problems, _ = await job.collect_problems()
    assert len(problems) == 1
    assert "бэкап БД" in problems[0]


@pytest.mark.asyncio
async def test_empty_backup_is_reported(host_env):
    """Пустой архив выглядит как успешный бэкап, пока не понадобится."""
    host_env(DB_BACKUP_SIZE=512)
    problems, _ = await job.collect_problems()
    assert len(problems) == 1
    assert "пустой архив" in problems[0]


@pytest.mark.asyncio
async def test_shrunken_backup_is_reported(host_env):
    """Прерванный pg_dump тоже оставляет файл — просто короче обычного."""
    host_env(DB_BACKUP_SIZE=10 * MB, DB_BACKUP_PREV_SIZE=50 * MB)
    problems, _ = await job.collect_problems()
    assert len(problems) == 1
    assert "усох" in problems[0]


@pytest.mark.asyncio
async def test_small_shrink_is_not_reported(host_env):
    """Обычное колебание размера тревогой быть не должно."""
    host_env(DB_BACKUP_SIZE=45 * MB, DB_BACKUP_PREV_SIZE=50 * MB)
    problems, _ = await job.collect_problems()
    assert problems == []


@pytest.mark.asyncio
async def test_missing_backup_file_is_reported(host_env):
    """Каталог пуст — скрипт передаёт пустые значения."""
    host_env(DB_BACKUP_AGE_MIN="", DB_BACKUP_SIZE="")
    problems, _ = await job.collect_problems()
    assert len(problems) == 1
    assert "нет данных о последнем бэкапе" in problems[0]


@pytest.mark.asyncio
async def test_uploads_backup_checked_too(host_env):
    host_env(UP_BACKUP_AGE_MIN=60 * 50)
    problems, _ = await job.collect_problems()
    assert len(problems) == 1
    assert "uploads" in problems[0]


@pytest.mark.asyncio
async def test_run_without_host_data_is_not_an_alarm(monkeypatch):
    """Ручной запуск внутри контейнера: данных нет, но это не авария."""
    for var in job.HOST_VARS:
        monkeypatch.delenv(var, raising=False)
    problems, report = await job.collect_problems()
    assert problems == []
    assert any("check-storage.sh" in r for r in report)


# ── Правила писем ────────────────────────────────────────────────────────────


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "STATE_FILE", str(tmp_path / "storage_state.json"))


@pytest.fixture
def sent(monkeypatch):
    box: list[tuple[str, str]] = []

    async def fake_notify(subject, html):
        box.append((subject, html))

    monkeypatch.setattr(job, "_notify", fake_notify)
    return box


@pytest.mark.asyncio
async def test_letter_once_then_on_recovery(state_file, sent, monkeypatch):
    async def broken():
        return ["диск: свободно 7% — меньше порога 15%"], ["свободно на диске: 7%"]

    async def fine():
        return [], ["свободно на диске: 40%"]

    monkeypatch.setattr(job, "collect_problems", broken)
    assert await job.main() == 1
    assert len(sent) == 1

    assert await job.main() == 1
    assert len(sent) == 1, "о той же проблеме второй раз не пишем"

    monkeypatch.setattr(job, "collect_problems", fine)
    assert await job.main() == 0
    assert len(sent) == 2
    assert "снова порядок" in sent[1][0]
