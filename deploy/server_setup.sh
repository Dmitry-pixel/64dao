#!/bin/bash
# ============================================================
# 64dao.ru — Полный скрипт установки и деплоя
# Запускать от root на чистом Ubuntu 22.04
# Использование: bash server_setup.sh
# ============================================================

set -euo pipefail

DOMAIN="64dao.ru"
APP_DIR="/var/www/64dao"
VENV="$APP_DIR/venv"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
UPLOADS_DIR="$APP_DIR/uploads"
DB_NAME="dao64"
DB_USER="dao64"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       64dao.ru — Server Setup Script                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. SYSTEM UPDATE ──────────────────────────────────────────────────────────
echo "[1/10] Обновление системы..."
apt update -qq && apt upgrade -y -qq
apt install -y -qq curl wget git unzip htop software-properties-common
echo "✓ Система обновлена"

# ── 2. POSTGRESQL ─────────────────────────────────────────────────────────────
echo ""
echo "[2/10] Установка PostgreSQL 16..."
apt install -y -qq postgresql-16 postgresql-client-16

systemctl enable postgresql
systemctl start postgresql

# Создаём пользователя и БД
DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || \
sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASS';"

sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "✓ PostgreSQL настроен"
echo "  DB_USER=$DB_USER"
echo "  DB_PASS=$DB_PASS  ← сохраните!"
echo "  DB_NAME=$DB_NAME"

# ── 3. PYTHON ─────────────────────────────────────────────────────────────────
echo ""
echo "[3/10] Установка Python 3.11..."
apt install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip
echo "✓ Python $(python3.11 --version)"

# ── 4. NODE.JS ────────────────────────────────────────────────────────────────
echo ""
echo "[4/10] Установка Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
apt install -y -qq nodejs
echo "✓ Node.js $(node --version)"

# ── 5. NGINX ──────────────────────────────────────────────────────────────────
echo ""
echo "[5/10] Установка и настройка Nginx..."
apt install -y -qq nginx certbot python3-certbot-nginx

# Создаём конфигурацию
cp /tmp/nginx-64dao.conf /etc/nginx/sites-available/64dao 2>/dev/null || \
cat > /etc/nginx/sites-available/64dao << 'NGINX_EOF'
# Временный конфиг (без SSL) — будет обновлён certbot
server {
    listen 80;
    server_name 64dao.ru www.64dao.ru;

    client_max_body_size 10M;
    access_log /var/log/nginx/64dao.access.log;
    error_log  /var/log/nginx/64dao.error.log;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_pass_header Set-Cookie;
    }

    location /uploads/ {
        alias /var/www/64dao/uploads/;
        expires 30d;
        autoindex off;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/64dao /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "✓ Nginx настроен"

# ── 6. DIRECTORIES ────────────────────────────────────────────────────────────
echo ""
echo "[6/10] Создание директорий..."
mkdir -p "$BACKEND_DIR" "$FRONTEND_DIR" "$UPLOADS_DIR/images"
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"
echo "✓ Директории созданы: $APP_DIR"

# ── 7. PYTHON VENV + BACKEND ──────────────────────────────────────────────────
echo ""
echo "[7/10] Python venv и зависимости бэкенда..."
python3.11 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip -q
"$VENV/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q

# Playwright: устанавливаем Chromium
"$VENV/bin/playwright" install chromium
"$VENV/bin/playwright" install-deps chromium

CHROMIUM_PATH=$("$VENV/bin/playwright" run-server --browser chromium -- which chromium 2>/dev/null || echo "")
echo "✓ Python venv и Playwright настроены"

# ── 8. ENV FILES ──────────────────────────────────────────────────────────────
echo ""
echo "[8/10] Создание .env файлов..."

JWT_SECRET=$(python3.11 -c "import secrets; print(secrets.token_hex(32))")
ADMIN_KEY=$(python3.11 -c "import secrets; print(secrets.token_urlsafe(24))")

# Backend .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
cat > "$BACKEND_DIR/.env" << EOF
DB_USER=$DB_USER
DB_PASS=$DB_PASS
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME

JWT_SECRET=$JWT_SECRET

SMTP_HOST=smtp.timeweb.com
SMTP_PORT=465
SMTP_USER=noreply@$DOMAIN
SMTP_PASS=ЗАПОЛНИТЕ_ПАРОЛЬ_ПОЧТЫ
SMTP_FROM=64DAO <noreply@$DOMAIN>
SMTP_USE_TLS=true

APP_URL=https://$DOMAIN
ADMIN_SETUP_KEY=$ADMIN_KEY
UPLOADS_DIR=$UPLOADS_DIR/reports
DEBUG=false
EOF
    echo "  ✓ $BACKEND_DIR/.env создан"
    echo "  ⚠️  Заполните SMTP_PASS в $BACKEND_DIR/.env"
else
    echo "  .env уже существует — пропускаем"
fi

# Frontend .env.local
if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
cat > "$FRONTEND_DIR/.env.local" << EOF
NEXT_PUBLIC_API_URL=https://$DOMAIN/api
NODE_ENV=production
EOF
    echo "  ✓ $FRONTEND_DIR/.env.local создан"
fi

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║  СОХРАНИТЕ ЭТИ ДАННЫЕ!                      ║"
echo "  ║  DB_PASS=$DB_PASS"
echo "  ║  JWT_SECRET=$JWT_SECRET"
echo "  ║  ADMIN_SETUP_KEY=$ADMIN_KEY"
echo "  ╚══════════════════════════════════════════════╝"

# ── 9. ALEMBIC MIGRATIONS ─────────────────────────────────────────────────────
echo ""
echo "[9/10] Запуск миграций Alembic..."
cd "$BACKEND_DIR"
"$VENV/bin/alembic" upgrade head
echo "✓ Миграции применены"

# ── 10. SYSTEMD SERVICES ──────────────────────────────────────────────────────
echo ""
echo "[10/10] Настройка systemd сервисов..."

# Backend service
cat > /etc/systemd/system/64dao-backend.service << EOF
[Unit]
Description=64dao FastAPI Backend
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --loop asyncio --log-level info
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=64dao-backend

[Install]
WantedBy=multi-user.target
EOF

# Frontend service
cat > /etc/systemd/system/64dao-frontend.service << EOF
[Unit]
Description=64dao Next.js Frontend
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=$FRONTEND_DIR
EnvironmentFile=$FRONTEND_DIR/.env.local
Environment=NODE_ENV=production
ExecStart=/usr/bin/node node_modules/.bin/next start -p 3000
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=64dao-frontend

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable 64dao-backend 64dao-frontend
echo "✓ Systemd сервисы настроены (не запущены — сначала заполните .env)"

# ── DONE ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              ✅ Сервер подготовлен!                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Следующие шаги:"
echo ""
echo "  1. Скопируйте код бэкенда в $BACKEND_DIR/"
echo "     rsync -av ./backend/ www-data@SERVER:$BACKEND_DIR/"
echo ""
echo "  2. Скопируйте код фронтенда в $FRONTEND_DIR/"
echo "     rsync -av ./frontend/ www-data@SERVER:$FRONTEND_DIR/"
echo "     cd $FRONTEND_DIR && npm install && npm run build"
echo ""
echo "  3. Заполните SMTP_PASS в $BACKEND_DIR/.env"
echo ""
echo "  4. Запустите сервисы:"
echo "     systemctl start 64dao-backend 64dao-frontend"
echo "     systemctl status 64dao-backend"
echo ""
echo "  5. SSL-сертификат (после настройки DNS):"
echo "     certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo ""
echo "  6. Создайте администратора:"
echo "     https://$DOMAIN/api/admin/setup"
echo "     Ключ: $ADMIN_KEY"
echo ""
echo "  Полезные команды:"
echo "    journalctl -u 64dao-backend -f   # логи бэкенда"
echo "    journalctl -u 64dao-frontend -f  # логи фронтенда"
echo "    systemctl restart 64dao-backend  # перезапуск"
