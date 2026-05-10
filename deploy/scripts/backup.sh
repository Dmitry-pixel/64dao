#!/bin/bash
# ============================================================
# backup.sh — Ночной бэкап 64dao.ru
#
# Что бэкапит:
#   1. PostgreSQL (полный дамп через pg_dump)
#   2. Uploads (PDF-отчёты + изображения стратегий)
#   3. Конфиги (.env файлы)
#
# Установка cron (запуск в 03:00 каждый день):
#   crontab -e
#   0 3 * * * /var/www/64dao/deploy/scripts/backup.sh >> /var/log/64dao-backup.log 2>&1
#
# Ручной запуск:
#   bash /var/www/64dao/deploy/scripts/backup.sh
# ============================================================

set -euo pipefail

# ── Конфигурация ──────────────────────────────────────────────────────────────
BACKUP_ROOT="/var/backups/64dao"
APP_DIR="/var/www/64dao"
DB_NAME="${DB_NAME:-dao64}"
DB_USER="${DB_USER:-dao64}"
KEEP_DAYS=30               # хранить бэкапы N дней
DATE=$(date +%Y-%m-%d_%H-%M-%S)
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# ── Цвета для вывода ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "${LOG_PREFIX} ${GREEN}✓${NC} $*"; }
log_err()  { echo -e "${LOG_PREFIX} ${RED}✗${NC} $*"; }
log_warn() { echo -e "${LOG_PREFIX} ${YELLOW}⚠${NC} $*"; }
log_info() { echo -e "${LOG_PREFIX}   $*"; }

# ── Создаём директории ────────────────────────────────────────────────────────
mkdir -p "${BACKUP_ROOT}/db"
mkdir -p "${BACKUP_ROOT}/uploads"
mkdir -p "${BACKUP_ROOT}/configs"

echo ""
log_info "═══════════════════════════════════════════"
log_info "  64dao.ru Backup — ${DATE}"
log_info "═══════════════════════════════════════════"

# ── 1. PostgreSQL dump ────────────────────────────────────────────────────────
log_info "Начинаем дамп PostgreSQL..."

DB_FILE="${BACKUP_ROOT}/db/db_${DATE}.sql.gz"

# Определяем источник: Docker или локальный PostgreSQL
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "dao64_db"; then
    # Docker-режим
    docker exec dao64_db pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --no-password \
        --verbose \
        2>/dev/null | gzip > "${DB_FILE}"
    log_ok "PostgreSQL (Docker) → ${DB_FILE} ($(du -sh "${DB_FILE}" | cut -f1))"
elif sudo -u postgres psql -lqt 2>/dev/null | grep -q "${DB_NAME}"; then
    # Локальный PostgreSQL
    sudo -u postgres pg_dump "${DB_NAME}" | gzip > "${DB_FILE}"
    log_ok "PostgreSQL (local) → ${DB_FILE} ($(du -sh "${DB_FILE}" | cut -f1))"
else
    log_err "PostgreSQL недоступен! Пропускаем дамп БД."
    DB_FILE=""
fi

# ── 2. Uploads (PDF + images) ─────────────────────────────────────────────────
log_info "Архивируем uploads..."

UPLOADS_SRC="${APP_DIR}/uploads"
UPLOADS_FILE="${BACKUP_ROOT}/uploads/uploads_${DATE}.tar.gz"

# Docker-режим: копируем из volume
if docker volume ls --format '{{.Name}}' 2>/dev/null | grep -q "dao64_uploads"; then
    docker run --rm \
        -v dao64_uploads:/data:ro \
        -v "${BACKUP_ROOT}/uploads":/backup \
        alpine tar czf "/backup/uploads_${DATE}.tar.gz" -C /data . 2>/dev/null
    log_ok "Uploads (Docker volume) → ${UPLOADS_FILE}"
elif [ -d "${UPLOADS_SRC}" ]; then
    tar czf "${UPLOADS_FILE}" -C "${UPLOADS_SRC}" . 2>/dev/null || true
    log_ok "Uploads (local) → ${UPLOADS_FILE} ($(du -sh "${UPLOADS_FILE}" | cut -f1))"
else
    log_warn "Директория uploads не найдена, пропускаем"
fi

# ── 3. Конфиги ────────────────────────────────────────────────────────────────
log_info "Сохраняем конфиги..."

CONFIG_FILE="${BACKUP_ROOT}/configs/configs_${DATE}.tar.gz"
CONFIG_FILES=()

# Собираем только существующие файлы
for f in \
    "${APP_DIR}/backend/.env" \
    "${APP_DIR}/frontend/.env.local" \
    "/etc/nginx/sites-available/64dao" \
    "/etc/nginx/conf.d/64dao.conf" \
    "/etc/systemd/system/64dao-backend.service" \
    "/etc/systemd/system/64dao-frontend.service"; do
    [ -f "$f" ] && CONFIG_FILES+=("$f")
done

if [ ${#CONFIG_FILES[@]} -gt 0 ]; then
    tar czf "${CONFIG_FILE}" "${CONFIG_FILES[@]}" 2>/dev/null || true
    log_ok "Конфиги → ${CONFIG_FILE}"
else
    log_warn "Конфиги не найдены"
fi

# ── 4. Удаление старых бэкапов ────────────────────────────────────────────────
log_info "Удаляем бэкапы старше ${KEEP_DAYS} дней..."

DELETED=0
for dir in db uploads configs; do
    while IFS= read -r file; do
        rm -f "$file"
        ((DELETED++)) || true
    done < <(find "${BACKUP_ROOT}/${dir}" -name "*.gz" -mtime "+${KEEP_DAYS}" 2>/dev/null)
done

log_ok "Удалено старых файлов: ${DELETED}"

# ── 5. Проверка места на диске ────────────────────────────────────────────────
DISK_USAGE=$(df -h "${BACKUP_ROOT}" | tail -1 | awk '{print $5}')
DISK_AVAIL=$(df -h "${BACKUP_ROOT}" | tail -1 | awk '{print $4}')
log_info "Использование диска: ${DISK_USAGE} (свободно: ${DISK_AVAIL})"

# Предупреждение если диска меньше 1 GB
DISK_AVAIL_KB=$(df "${BACKUP_ROOT}" | tail -1 | awk '{print $4}')
if [ "${DISK_AVAIL_KB}" -lt 1048576 ]; then
    log_warn "Мало свободного места на диске! Рекомендуем очистить старые бэкапы."
fi

# ── 6. Итог ───────────────────────────────────────────────────────────────────
echo ""
log_info "Содержимое бэкапа:"
du -sh "${BACKUP_ROOT}"/{db,uploads,configs} 2>/dev/null | \
    while read size dir; do log_info "  ${dir}: ${size}"; done

echo ""
log_ok "Бэкап завершён: ${DATE}"
log_info "═══════════════════════════════════════════"
echo ""
