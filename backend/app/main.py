"""
64dao.ru — FastAPI Backend
Запуск локально: uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import DBAPIError

from app.config import get_settings
from app.limiter import limiter
from app.pdf import close_browser
from app.routers import (
    admin,
    assessments,
    auth,
    checklist,
    companies,
    contact,
    documents,
    fin_content,
    m3,
    method1,
    payments,
    pricing,
    reports,
    sample_report,
    site_mode,
    social_links,
    strategies,
    support,
)

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate limiter (in-memory) ──────────────────────────────────────────────────
# Переключение на Redis одной строкой:
# limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Выполняется один раз на старте, до приёма трафика: блокировка event loop
    # здесь ни на что не влияет.
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
    (Path(settings.uploads_dir).parent / "images").mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
    logger.info("64dao backend started")
    yield
    await close_browser()
    logger.info("64dao backend stopped")


app = FastAPI(
    title="64dao API",
    version="1.0.0",
    docs_url="/api/docs"  if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Подключаем limiter к app.state
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda req, exc: JSONResponse(
        {"detail": "Слишком много запросов. Попробуйте через минуту."},
        status_code=429,
    ),
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# rstrip("/") — защита от trailing slash в APP_URL (https://64dao.ru/ → 403 preflight)
# FastAPI при allow_credentials=True требует точного совпадения origin
# localhost — только для локальной разработки. В проде он в списке лишний:
# вместе с allow_credentials=True это доверенный origin, поднять который на
# машине жертвы дешевле, чем кажется.
_origins = [settings.app_url.rstrip("/")]
if settings.debug:
    _origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Ошибки данных в запросе ───────────────────────────────────────────────────
def _is_data_error(exc: BaseException | None) -> bool:
    """Есть ли в цепочке причин asyncpg.DataError.

    SQLAlchemy заворачивает исключение драйвера дважды: DBAPIError.orig — это
    AsyncAdapt_asyncpg_dbapi.Error, а настоящий DataError лежит в его
    __cause__. Проверять по строке сообщения нельзя — текст меняется от
    версии к версии драйвера.
    """
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if isinstance(exc, asyncpg.exceptions.DataError):
            return True
        exc = getattr(exc, "__cause__", None)
    return False


@app.exception_handler(DBAPIError)
async def db_error_handler(request: Request, exc: DBAPIError):
    """Некорректный идентификатор в пути -> 400, а не 500 со стектрейсом.

    Фронт умеет подставить в путь литерал "null": на /purchases кнопка
    «Открыть» строила ссылку из order.assessment_id, который пуст у заказов
    Метода 3 и у кредитов, купленных заранее. asyncpg отвечал DataError
    «invalid UUID», и каждый такой заход писал в логи полный стектрейс как
    внутреннюю ошибку сервера.

    Один обработчик вместо валидации в 26 эндпоинтах с UUID в пути: он
    закрывает и те, что появятся позже. Настоящие ошибки БД по-прежнему
    уходят в 500 с трассировкой.
    """
    if _is_data_error(getattr(exc, "orig", None)):
        logger.warning("Некорректный параметр в запросе %s: %s",
                       request.url.path, getattr(exc, "orig", exc))
        return JSONResponse(
            status_code=400,
            content={"detail": "Некорректный идентификатор в запросе"},
        )
    logger.error("Ошибка БД на %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Внутренняя ошибка сервера"})


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Внутренняя ошибка сервера"})

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(assessments.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(strategies.router)
app.include_router(documents.router)
app.include_router(payments.router)
app.include_router(pricing.router)
app.include_router(contact.router)
app.include_router(social_links.router)
app.include_router(sample_report.router)
app.include_router(support.router)
app.include_router(site_mode.router)
app.include_router(fin_content.router)
app.include_router(method1.router)
app.include_router(companies.router)
app.include_router(checklist.router)

# Метод 3 «Матрица силы». Роутер подключён всегда — доступ гасится флагом
# settings.m3_enabled внутри эндпоинтов, а не отсутствием маршрутов:
# так включение не требует пересборки образа.
app.include_router(m3.router)
app.include_router(m3.reports_router)
app.include_router(m3.admin_router)

# ── Статика /uploads снята намеренно ──────────────────────────────────────────
# Здесь монтировался родительский каталог uploads целиком. Вместе с ним
# наружу уходили все рантайм-настройки из тома dao64_uploads: проверено
# запросом GET /uploads/tochka_settings.json — 200, 776 байт, JWT банка
# открытым текстом. Наружу это не пробивалось лишь потому, что действующий
# конфиг nginx не содержал location /uploads/ — при том что на диске лежал
# 64dao-static.conf, который его проксировал, просто не подключённый.
#
# Потребителей у монтирования не было: во фронтенде ноль обращений к
# /uploads, а всё содержимое каталога отдаётся своими эндпоинтами с
# проверкой доступа — отчёты через /api/reports/{id}/download (владение и
# отзыв после возврата), документы через /api/documents/{slug},
# sample_report через /api/sample-report/view, соцссылки через
# /api/social-links. strategies.image_url пуст у всех записей.
#
# Если появится загрузка изображений — монтировать ТОЛЬКО подкаталог
# images/, никогда не родительский.

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
