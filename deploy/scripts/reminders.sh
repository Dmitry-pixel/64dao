#!/usr/bin/env bash
# PR6: ежедневный запуск email-напоминаний (host cron).
# Kill-switch: REMINDERS_ENABLED=false в backend/.env.
set -euo pipefail
cd /var/www/64dao
exec docker compose exec -T backend python -m app.jobs.reminders
