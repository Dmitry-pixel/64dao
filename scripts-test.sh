#!/bin/sh
# Прогон regression-набора во временном контейнере.
# Работающий бэкенд не затрагивается, продовая БД тоже:
# conftest.py подменяет DB_NAME, UPLOAD_DIR и флаг регенерации PDF.
set -e
cd "$(dirname "$0")"
docker compose build backend
docker compose run --rm backend sh -c \
  "pip install -q -r requirements-test.txt pytest-timeout && pytest -q --timeout=90 $*"
