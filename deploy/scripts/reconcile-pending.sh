#!/usr/bin/env bash
# Ежечасная досверка зависших заказов: оплата прошла в банке, а у нас pending.
#
# Cron (каждый час в :25 — вне пиков и не совпадает с бэкапом в 03:00):
#   25 * * * * bash /var/www/64dao/deploy/scripts/reconcile-pending.sh >> /var/log/64dao-reconcile.log 2>&1
#
# Окно проверки: RECONCILE_STALE_MINUTES (по умолчанию 15) и
# RECONCILE_MAX_AGE_DAYS (по умолчанию 7) в backend/.env.
#
# В логе искать строки "вебхук не дошёл": каждая означает оплату, которую
# банк подтвердил, а мы узнали только сверкой. Если такие строки идут
# регулярно — проблема не в сверке, а в доставке вебхуков.
set -euo pipefail
cd /var/www/64dao
echo "=== $(date --iso-8601=seconds) ==="
exec docker compose exec -T backend python -m app.jobs.reconcile_pending
