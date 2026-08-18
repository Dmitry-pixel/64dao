#!/usr/bin/env bash
# Еженедельная проверка сертификатов НУЦ Минцифры и издателя сертификата Точки.
#
# Cron (воскресенье, 04:10 — после ночного бэкапа в 03:00):
#   10 4 * * 0 bash /var/www/64dao/deploy/scripts/check-ca-expiry.sh >> /var/log/64dao-ca-check.log 2>&1
#
# Порог предупреждения: CA_EXPIRY_WARN_DAYS в backend/.env (по умолчанию 60).
# Что делать по письму — DEPLOY.md, раздел 8a, подраздел «Обслуживание».
set -euo pipefail
cd /var/www/64dao
echo "=== $(date --iso-8601=seconds) ==="
exec docker compose exec -T backend python -m app.jobs.check_ca_expiry
