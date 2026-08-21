#!/usr/bin/env bash
# Проверка боевого сайта каждые 15 минут: жив ли и отдаёт ли то, что должен.
#
# Cron (в :07, :22, :37, :52 — вразнобой с остальными задачами):
#   7,22,37,52 * * * * bash /var/www/64dao/deploy/scripts/smoke-prod.sh >> /var/log/64dao-smoke.log 2>&1
#
# Письмо на SUPPORT_EMAIL уходит при смене состояния: сайт упал или
# восстановился. О продолжающейся аварии повторных писем нет.
#
# Настройки (backend/.env, обе необязательны):
#   SMOKE_BASE_URL — что проверяем (по умолчанию https://64dao.ru);
#   SMOKE_TIMEOUT  — таймаут запроса в секундах (по умолчанию 10).
#
# Проверка идёт снаружи, через публичный адрес: так же, как её видит клиент,
# то есть вместе с nginx, TLS и фронтендом, а не только контейнер бэкенда.
set -euo pipefail
cd /var/www/64dao
echo "=== $(date --iso-8601=seconds) ==="
exec docker compose exec -T backend python -m app.jobs.smoke_prod
