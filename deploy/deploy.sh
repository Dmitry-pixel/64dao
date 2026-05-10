#!/bin/bash
# ============================================================
# 64dao.ru — Скрипт деплоя обновлений
# Запускать на сервере: bash deploy.sh
# ============================================================

set -euo pipefail

APP_DIR="/var/www/64dao"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV="$APP_DIR/venv"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   64dao.ru — Deploy Update           ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Деплой бэкенда
if [ -d "$BACKEND_DIR/.git" ]; then
    echo "📥 Обновляем бэкенд..."
    cd "$BACKEND_DIR"
    git pull origin main

    echo "📦 Обновляем Python зависимости..."
    "$VENV/bin/pip" install -r requirements.txt -q

    echo "🗃️  Применяем миграции..."
    "$VENV/bin/alembic" upgrade head

    echo "🔄 Перезапускаем бэкенд..."
    systemctl restart 64dao-backend
    sleep 3
    systemctl is-active 64dao-backend && echo "✓ Backend: online" || echo "✗ Backend: FAILED"
fi

# Деплой фронтенда
if [ -d "$FRONTEND_DIR/.git" ] || [ -d "$FRONTEND_DIR/src" ]; then
    echo ""
    echo "📥 Обновляем фронтенд..."
    cd "$FRONTEND_DIR"
    [ -d ".git" ] && git pull origin main

    echo "📦 Устанавливаем Node зависимости..."
    npm install -q

    echo "🔨 Собираем Next.js..."
    npm run build

    echo "🔄 Перезапускаем фронтенд..."
    systemctl restart 64dao-frontend
    sleep 3
    systemctl is-active 64dao-frontend && echo "✓ Frontend: online" || echo "✗ Frontend: FAILED"
fi

echo ""
echo "✅ Деплой завершён"
echo "   journalctl -u 64dao-backend -f   — логи бэкенда"
echo "   journalctl -u 64dao-frontend -f  — логи фронтенда"
