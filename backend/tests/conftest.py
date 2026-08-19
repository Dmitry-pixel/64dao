"""
conftest.py — общие фикстуры для regression-тестов 64dao backend.

Архитектура:
- Тестовая БД: отдельная база `dao64_test` в том же Postgres-контейнере (dao64_db).
  Не трогает продовую `dao64`.
- Тесты запускаются ВНУТРИ backend-контейнера:
    docker compose exec backend pytest
  (Postgres-порт закрыт наружу в проде, доступен только из Docker-сети `internal`.)
- SQLAlchemy async (asyncpg), как в проде — db.py использует AsyncSession.
- Каждый тест получает чистую транзакцию с rollback в конце (изоляция тестов
  друг от друга без необходимости пересоздавать схему на каждый запуск).
- Аутентификация в тестах — через прямой вызов auth.create_token(), минуя
  OTP/email-флоу (OTP тестируется отдельно, см. test_auth.py).
- Паролей в системе нет: вход только по OTP, users.password_hash удалён
  миграцией 033.

ВАЖНО: переменная окружения DB_NAME должна быть переопределена на dao64_test
для тестового прогона — см. pytest.ini/conftest ниже (os.environ patch перед
импортом app.config, т.к. get_settings() кэширован через lru_cache).
"""
import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Изоляция тестового окружения ДО импорта app.config: get_settings()
# обёрнут в lru_cache, после первого вызова подмена не подействует.
# setdefault здесь не годится — DB_NAME приходит из боевого .env.
_TEST_UPLOADS = tempfile.mkdtemp(prefix="64dao-test-uploads-")
os.environ["DB_NAME"] = "dao64_test"
# Не поднимать Chromium при скачивании: отдаём сохранённый файл.
os.environ["REGENERATE_PDF_ON_DOWNLOAD"] = "false"
# Отвязать от боевого тома: site_mode.json оттуда управляет режимом
# техобслуживания и делал результат прогона зависимым от состояния прода.
os.environ["UPLOAD_DIR"] = _TEST_UPLOADS
os.environ["UPLOADS_DIR"] = _TEST_UPLOADS

from app.auth import create_token  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

settings = get_settings()

assert settings.db_name == "dao64_test", (
    f"Тесты должны идти против dao64_test, а не против '{settings.db_name}'. "
    "Проверьте переменную окружения DB_NAME перед запуском pytest."
)

test_engine = create_async_engine(settings.database_url, echo=False)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_database():
    async with test_engine.begin() as conn:
        # drop_all перед create_all: сам create_all с checkfirst молча
        # пропускает уже существующие таблицы. После миграции или упавшего
        # прогона схема оставалась старой, и весь набор падал каскадом —
        # 477 ошибок, за которыми не видно настоящей причины.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_test_database):
    async with test_engine.connect() as connection:
        async with connection.begin() as outer_transaction:
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            try:
                yield session
            finally:
                await session.close()
                await outer_transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Test User",
        company_name="Test Company",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    admin = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Test Admin",
        role="admin",
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


@pytest.fixture
def mock_email_senders(monkeypatch):
    import app.routers.auth as auth_router

    mocks = {
        "send_otp_email": AsyncMock(return_value=None),
        "send_welcome_email": AsyncMock(return_value=None),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(auth_router, name, mock)
    return mocks


def _set_auth_cookie(client: AsyncClient, user: User) -> None:
    """
    JWT-токен через create_token(), минуя OTP. Устанавливается через
    client.cookies.set() (cookie jar), а не через client.headers["Cookie"]
    (статический header) - это критично для тестов, где cookie должен
    реально обновляться между запросами через Set-Cookie от сервера
    (например impersonation: start_impersonation меняет auth-token, и
    последующий запрос должен видеть НОВОЕ значение, не старое).
    Статический header перекрывал бы любое обновление от Set-Cookie.
    """
    token = create_token(user_id=str(user.id), email=user.email, role=user.role)
    client.cookies.clear()
    client.cookies.set("auth-token", token)


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    _set_auth_cookie(client, test_user)
    return client


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, test_admin: User) -> AsyncClient:
    _set_auth_cookie(client, test_admin)
    return client
