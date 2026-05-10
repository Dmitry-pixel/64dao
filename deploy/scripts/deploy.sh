#!/bin/bash
# ============================================================
# deploy.sh — Деплой / обновление 64dao.ru
#
# Использование:
#   bash deploy.sh --mode docker     # Docker Compose (рекомендуется)
#   bash deploy.sh --mode systemd    # без Docker (uvicorn + next start)
# ============================================================

set -euo pipefail

# Параметры
MODE="docker"
APP_DIR="/var/www/64dao"
VENV="${APP_DIR}/venv"

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode) MODE="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }
info() { echo -e "  → $*"; }

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   64dao.ru — Deploy [mode: ${MODE}]"
echo "╚══════════════════════════════════════════╝"
echo ""

cd "${APP_DIR}"

# ── Обновление кода из Git ────────────────────────────────────────────────────
if [ -d .git ]; then
    info "git pull origin main..."
    git pull origin main
    ok "Код: $(git log -1 --format='%h %s (%ar)')"
else
    warn "Git не инициализирован — используем текущий код"
fi

# ── Docker режим ──────────────────────────────────────────────────────────────
if [ "${MODE}" = "docker" ]; then

    info "Пересборка образов..."
    docker compose build --no-cache backend frontend

    info "Применяем миграции Alembic..."
    docker compose run --rm --no-deps backend \
        sh -c "alembic upgrade head" 2>&1 | tail -5

    info "Перезапуск сервисов..."
    docker compose up -d --force-recreate backend frontend nginx

    # Ждём что сервисы поднялись
    echo -n "  Ждём healthy статус"
    for i in $(seq 1 30); do
        sleep 2
        echo -n "."
        if docker compose ps | grep -q "healthy"; then
            echo ""
            break
        fi
    done

    # Итоговый статус
    echo ""
    docker compose ps
    echo ""

    # Проверяем API
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        ok "API health: OK"
    else
        err "API health: FAILED — проверьте логи: docker compose logs backend"
    fi

    ok "Docker deploy завершён"

# ── Systemd режим ─────────────────────────────────────────────────────────────
elif [ "${MODE}" = "systemd" ]; then

    # Python venv
    if [ ! -d "${VENV}" ]; then
        info "Создаём Python venv..."
        python3.11 -m venv "${VENV}"
    fi

    info "Обновляем Python зависимости..."
    "${VENV}/bin/pip" install -r "${APP_DIR}/backend/requirements.txt" -q

    info "Playwright Chromium..."
    "${VENV}/bin/playwright" install chromium --with-deps > /dev/null 2>&1 || \
    "${VENV}/bin/playwright" install chromium > /dev/null 2>&1
    ok "Playwright готов"

    info "Миграции Alembic..."
    cd "${APP_DIR}/backend"
    "${VENV}/bin/alembic" upgrade head
    cd "${APP_DIR}"
    ok "Миграции применены"

    info "Frontend: npm ci + build..."
    cd "${APP_DIR}/frontend"
    npm ci --quiet
    npm run build
    cd "${APP_DIR}"
    ok "Next.js собран"

    # Перезапуск сервисов
    info "Перезапуск backend..."
    systemctl restart 64dao-backend
    sleep 3
    if systemctl is-active --quiet 64dao-backend; then
        ok "Backend: online"
    else
        err "Backend: FAILED"
        journalctl -u 64dao-backend -n 20 --no-pager
        exit 1
    fi

    info "Перезапуск frontend..."
    systemctl restart 64dao-frontend
    sleep 3
    if systemctl is-active --quiet 64dao-frontend; then
        ok "Frontend: online"
    else
        err "Frontend: FAILED"
        journalctl -u 64dao-frontend -n 20 --no-pager
        exit 1
    fi

    ok "Systemd deploy завершён"

else
    err "Неизвестный режим: ${MODE}. Используйте --mode docker или --mode systemd"
    exit 1
fi

echo ""
echo "  Статус:  docker compose ps  / systemctl status 64dao-backend"
echo "  Логи:    docker compose logs -f backend  / journalctl -u 64dao-backend -f"
echo "  Health:  curl https://64dao.ru/api/health"
echo ""
