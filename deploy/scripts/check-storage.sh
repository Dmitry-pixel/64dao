#!/usr/bin/env bash
# Ежедневный контроль диска, размера базы и состояния бэкапов.
#
# Cron (04:40, после ночного бэкапа в 03:00 — чтобы проверять свежий):
#   40 4 * * * bash /var/www/64dao/deploy/scripts/check-storage.sh >> /var/log/64dao-storage.log 2>&1
#
# Скрипт собирает то, что видно только с хоста — свободное место и файлы
# бэкапов, — и передаёт цифры в контейнер. Пороги и письмо живут в
# app/jobs/check_storage.py, рядом с остальными задачами и общим SMTP.
#
# Настройки порогов — в backend/.env: STORAGE_DISK_WARN_PERCENT,
# BACKUP_MAX_AGE_HOURS, BACKUP_MIN_BYTES, BACKUP_SHRINK_PERCENT.
set -euo pipefail
cd /var/www/64dao

BACKUP_ROOT="/var/backups/64dao"

echo "=== $(date --iso-8601=seconds) ==="

# Доля свободного места на разделе с приложением.
DISK_FREE_PERCENT=$(df -P /var/www | awk 'NR==2 {gsub("%","",$5); print 100-$5}')

# Два последних дампа БД: свежий и предыдущий — чтобы заметить, что дамп
# внезапно стал вдвое короче (прерванный pg_dump оставляет файл, просто
# короче обычного).
mapfile -t DB_FILES < <(ls -1t "${BACKUP_ROOT}/db/"*.sql.gz 2>/dev/null || true)
DB_BACKUP_AGE_MIN=""; DB_BACKUP_SIZE=""; DB_BACKUP_PREV_SIZE=""
if [ "${#DB_FILES[@]}" -gt 0 ]; then
  DB_BACKUP_SIZE=$(stat -c %s "${DB_FILES[0]}")
  DB_BACKUP_AGE_MIN=$(( ( $(date +%s) - $(stat -c %Y "${DB_FILES[0]}") ) / 60 ))
  [ "${#DB_FILES[@]}" -gt 1 ] && DB_BACKUP_PREV_SIZE=$(stat -c %s "${DB_FILES[1]}")
fi

mapfile -t UP_FILES < <(ls -1t "${BACKUP_ROOT}/uploads/"*.tar.gz 2>/dev/null || true)
UP_BACKUP_AGE_MIN=""; UP_BACKUP_SIZE=""
if [ "${#UP_FILES[@]}" -gt 0 ]; then
  UP_BACKUP_SIZE=$(stat -c %s "${UP_FILES[0]}")
  UP_BACKUP_AGE_MIN=$(( ( $(date +%s) - $(stat -c %Y "${UP_FILES[0]}") ) / 60 ))
fi

# Пороги обычно живут в backend/.env и попадают в контейнер сами. Но если
# переменная задана в окружении вызова — пробрасываем её: так проверяется,
# что письмо доходит (STORAGE_DISK_WARN_PERCENT=99 роняет проверку намеренно).
THRESHOLDS=()
for var in STORAGE_DISK_WARN_PERCENT BACKUP_MAX_AGE_HOURS BACKUP_MIN_BYTES BACKUP_SHRINK_PERCENT; do
  if [ -n "${!var:-}" ]; then
    THRESHOLDS+=(-e "${var}=${!var}")
  fi
done

exec docker compose exec -T \
  "${THRESHOLDS[@]+"${THRESHOLDS[@]}"}" \
  -e DISK_FREE_PERCENT="${DISK_FREE_PERCENT}" \
  -e DB_BACKUP_AGE_MIN="${DB_BACKUP_AGE_MIN}" \
  -e DB_BACKUP_SIZE="${DB_BACKUP_SIZE}" \
  -e DB_BACKUP_PREV_SIZE="${DB_BACKUP_PREV_SIZE}" \
  -e UP_BACKUP_AGE_MIN="${UP_BACKUP_AGE_MIN}" \
  -e UP_BACKUP_SIZE="${UP_BACKUP_SIZE}" \
  backend python -m app.jobs.check_storage
