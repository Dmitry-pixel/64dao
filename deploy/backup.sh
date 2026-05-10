#!/bin/bash
# ============================================================
# 64dao.ru — Скрипт ночного бэкапа
# Установка: crontab -e
# Добавьте: 0 3 * * * /var/www/64dao/backup.sh >> /var/log/64dao-backup.log 2>&1
# ============================================================

set -euo pipefail

BACKUP_DIR="/var/backups/64dao"
DB_NAME="dao64"
DB_USER="dao64"
UPLOADS_DIR="/var/www/64dao/uploads"
KEEP_DAYS=30

DATE=$(date +%Y-%m-%d_%H-%M)
mkdir -p "$BACKUP_DIR"

echo "[$DATE] Starting backup..."

# ── PostgreSQL dump ────────────────────────────────────────────────────────────
PG_FILE="$BACKUP_DIR/db_${DATE}.sql.gz"
sudo -u postgres pg_dump "$DB_NAME" | gzip > "$PG_FILE"
echo "[$DATE] DB backup: $PG_FILE ($(du -sh "$PG_FILE" | cut -f1))"

# ── Uploads (PDF отчёты + изображения) ────────────────────────────────────────
UPLOADS_FILE="$BACKUP_DIR/uploads_${DATE}.tar.gz"
tar -czf "$UPLOADS_FILE" -C "$UPLOADS_DIR" . 2>/dev/null || true
echo "[$DATE] Uploads backup: $UPLOADS_FILE ($(du -sh "$UPLOADS_FILE" | cut -f1))"

# ── Удаляем старые бэкапы ─────────────────────────────────────────────────────
find "$BACKUP_DIR" -name "*.gz" -mtime +${KEEP_DAYS} -delete
echo "[$DATE] Old backups cleaned (older than ${KEEP_DAYS} days)"

echo "[$DATE] Backup complete ✓"
