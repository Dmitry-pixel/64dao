"""
64dao.ru — FastAPI Backend
Запуск локально: uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.limiter import limiter
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.pdf import close_browser
from app.routers import auth, assessments, reports, admin

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
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    (Path(settings.uploads_dir).parent / "images").mkdir(parents=True, exist_ok=True)
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url.rstrip("/"), "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

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

# ── Static uploads ────────────────────────────────────────────────────────────
uploads_parent = str(Path(settings.uploads_dir).parent)
app.mount("/uploads", StaticFiles(directory=uploads_parent), name="uploads")

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
