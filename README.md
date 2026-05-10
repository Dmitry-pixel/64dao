# 64 ДАО

Веб-приложение для стратегической диагностики бизнеса по методологии 64 стратагем.

**Стек:** FastAPI (Python 3.11+) · PostgreSQL 16 · Next.js 14 (TypeScript) · Nginx · Docker.

## Структура

```
backend/        — FastAPI + SQLAlchemy + Alembic
frontend/       — Next.js (App Router)
deploy/         — nginx, systemd-юниты, server-setup, бэкап-скрипты
docker-compose.yml
DEPLOY.md       — пошаговая инструкция по деплою на VPS
```

## Быстрый старт (Docker)

```bash
git clone <ваш-репо> && cd 64dao
cp backend/.env.example   backend/.env       # отредактировать
cp frontend/.env.example  frontend/.env.local
docker compose up -d --build
```

Полная инструкция по продакшен-деплою: см. [DEPLOY.md](DEPLOY.md).
