# 64dao.ru — Инструкция по деплою на VPS

## Оглавление
1. [Предварительные требования](#1-предварительные-требования)
2. [Подготовка сервера](#2-подготовка-сервера)
3. [DNS и домен](#3-dns-и-домен)
4. [Загрузка кода](#4-загрузка-кода)
5. [Настройка окружения](#5-настройка-окружения)
6. [Docker-деплой (рекомендуется)](#6-docker-деплой-рекомендуется)
7. [Systemd-деплой (без Docker)](#7-systemd-деплой-без-docker)
8. [SSL-сертификат](#8-ssl-сертификат)
9. [Первый запуск и администратор](#9-первый-запуск-и-администратор)
10. [Настройка бэкапов](#10-настройка-бэкапов)
11. [Обновление кода](#11-обновление-кода)
12. [Мониторинг и логи](#12-мониторинг-и-логи)
13. [Решение проблем](#13-решение-проблем)

---

## 1. Предварительные требования

### Сервер
| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Диск | 20 GB SSD | 40 GB SSD |
| ОС | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Что нужно заранее
- VPS с Ubuntu 22.04 и SSH-доступом от root
- Домен `64dao.ru` с доступом к DNS-записям
- Данные SMTP-сервера (хостинг-провайдер, Yandex, Mail.ru)
- SSH-ключ на вашем компьютере

---

## 2. Подготовка сервера

### Подключитесь к серверу
```bash
ssh root@ВАШ_IP
```

### Запустите скрипт первичной настройки
```bash
# Загрузите скрипт на сервер
curl -fsSL https://raw.githubusercontent.com/ВАШ_РЕПО/main/deploy/scripts/server-setup.sh \
  -o /tmp/server-setup.sh

# Запустите от root
bash /tmp/server-setup.sh
```

Скрипт автоматически установит:
- **UFW Firewall** — открывает только 22, 80, 443
- **Fail2ban** — защита от брутфорса SSH и Nginx
- **Docker + Docker Compose** — для контейнерного деплоя
- **Node.js 20** — для деплоя без Docker
- **Python 3.11** — для деплоя без Docker
- **Nginx + Certbot** — веб-сервер и SSL
- Создаёт системного пользователя `dao64`
- Создаёт директории `/var/www/64dao/` и `/var/backups/64dao/`

### Проверьте результат
```bash
ufw status
docker --version
node --version
python3.11 --version
```

---

## 3. DNS и домен

В панели управления доменом добавьте A-записи:

```
Тип    Имя    Значение           TTL
A      @      ВАШ_IP_VPS        300
A      www    ВАШ_IP_VPS        300
```

Проверьте обновление DNS (может занять от 5 минут до 24 часов):
```bash
# С вашего компьютера:
nslookup 64dao.ru
# Должен вернуть IP вашего VPS
```

---

## 4. Загрузка кода

### Вариант A: через Git (рекомендуется)
```bash
# На сервере:
cd /var/www/64dao
git clone https://github.com/ВАШ_ЛОГИН/64dao.git .
# или если репозиторий приватный:
git clone https://ВАШ_ТОКЕН@github.com/ВАШ_ЛОГИН/64dao.git .
```

### Вариант B: через SCP с локального компьютера
```bash
# С вашего компьютера:
scp -r ./64dao-python/* root@ВАШ_IP:/var/www/64dao/
```

### Вариант C: загрузить архив
```bash
# На сервере:
cd /var/www/64dao
wget https://ССЫЛКА_НА_АРХИВ/64dao-python-v5.zip
unzip 64dao-python-v5.zip
mv 64dao-python/* . && rmdir 64dao-python
```

---

## 5. Настройка окружения

### Backend (.env)
```bash
cd /var/www/64dao/backend
cp .env.example .env
nano .env
```

Заполните все значения:

```env
# База данных
DB_USER=dao64
DB_PASS=придумайте-надёжный-пароль-20-символов
DB_HOST=localhost   # или "db" для Docker
DB_NAME=dao64

# JWT (минимум 32 символа)
# Генерация: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=сгенерируйте-секретную-строку-здесь

# SMTP (пример для Timeweb)
SMTP_HOST=smtp.timeweb.com
SMTP_PORT=465
SMTP_USER=noreply@64dao.ru
SMTP_PASS=пароль-от-почтового-ящика
SMTP_USE_TLS=true

# Приложение
APP_URL=https://64dao.ru
DEBUG=false
UPLOADS_DIR=/var/www/64dao/uploads/reports

# Первичная настройка (удалить после создания admin)
ADMIN_SETUP_KEY=придумайте-секретный-ключ
```

### Frontend (.env.local)
```bash
cd /var/www/64dao/frontend
cp .env.example .env.local
nano .env.local
```

```env
NEXT_PUBLIC_API_URL=https://64dao.ru/api
ADMIN_SECRET=ТОТ_ЖЕ_JWT_SECRET_ЧТО_В_BACKEND
```

> ⚠️ `ADMIN_SECRET` во фронтенде используется middleware.ts для валидации JWT-куки в Edge Runtime. Должен совпадать с `JWT_SECRET` бэкенда.

---

## 6. Docker-деплой (рекомендуется)

### Первый запуск
```bash
cd /var/www/64dao

# Сборка образов
docker compose build

# Запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps
```

Ожидаемый результат:
```
NAME              STATUS
dao64_db          Up (healthy)
dao64_backend     Up (healthy)
dao64_frontend    Up (healthy)
dao64_nginx       Up (healthy)
```

### Применение миграций
```bash
docker compose exec backend alembic upgrade head
```

### Проверка работоспособности
```bash
# Health check бэкенда
curl http://localhost:8000/api/health

# Health check через Nginx (после SSL)
curl https://64dao.ru/api/health
```

---

## 7. Systemd-деплой (без Docker)

Используйте если Docker не подходит по требованиям хостинга.

### Установка PostgreSQL
```bash
apt install -y postgresql-16
sudo -u postgres psql -c "CREATE USER dao64 WITH PASSWORD 'ваш-пароль';"
sudo -u postgres psql -c "CREATE DATABASE dao64 OWNER dao64;"
```

### Python venv и зависимости
```bash
cd /var/www/64dao
python3.11 -m venv venv
venv/bin/pip install -r backend/requirements.txt

# Playwright: установить Chromium
venv/bin/playwright install chromium
venv/bin/playwright install-deps chromium
```

### Next.js сборка
```bash
cd /var/www/64dao/frontend
npm ci
npm run build
```

### Применение миграций
```bash
cd /var/www/64dao/backend
../venv/bin/alembic upgrade head
```

### Установка systemd юнитов
```bash
# Копируем юниты
cp /var/www/64dao/deploy/systemd/64dao-backend.service /etc/systemd/system/
cp /var/www/64dao/deploy/systemd/64dao-frontend.service /etc/systemd/system/

# Перезагружаем systemd
systemctl daemon-reload

# Включаем автозапуск
systemctl enable 64dao-backend 64dao-frontend

# Запускаем
systemctl start 64dao-backend
systemctl start 64dao-frontend

# Проверяем
systemctl status 64dao-backend
systemctl status 64dao-frontend
```

### Установка Nginx конфигурации
```bash
# Копируем конфиги
cp /var/www/64dao/deploy/nginx/nginx.conf /etc/nginx/nginx.conf
cp /var/www/64dao/deploy/nginx/64dao.conf /etc/nginx/conf.d/64dao.conf

# Проверяем синтаксис
nginx -t

# Перезагружаем
systemctl reload nginx
```

---

## 8. SSL-сертификат

> Выполняйте только после того как DNS обновился и домен указывает на ваш IP.

### Для Nginx на хосте (systemd-режим)
```bash
certbot --nginx -d 64dao.ru -d www.64dao.ru
```

Certbot спросит:
- Email для уведомлений об истечении → введите ваш email
- Согласие с условиями → Y
- Перенаправление HTTP→HTTPS → 2 (Yes)

### Для Docker-режима
```bash
# Временно останавливаем Nginx контейнер
docker compose stop nginx

# Получаем сертификат (standalone режим)
certbot certonly --standalone \
  -d 64dao.ru \
  -d www.64dao.ru \
  --non-interactive \
  --agree-tos \
  --email ВАШ@EMAIL.RU

# Запускаем обратно
docker compose start nginx
```

### Автообновление сертификата
```bash
# Проверяем что автообновление работает
certbot renew --dry-run

# Добавляем в cron (если не добавился автоматически)
crontab -e
# Добавьте строку:
0 12 * * * certbot renew --quiet && systemctl reload nginx
```

---

## 9. Первый запуск и администратор

### Создание первого администратора

Откройте в браузере: **https://64dao.ru/api/admin/setup**

Или через curl:
```bash
curl -X POST https://64dao.ru/api/admin/setup \
  -H "Content-Type: application/json" \
  -d '{
    "setup_key": "ВАШ_ADMIN_SETUP_KEY_ИЗ_ENV",
    "email": "admin@64dao.ru",
    "password": "надёжный-пароль-администратора",
    "full_name": "Имя Администратора"
  }'
```

Ответ: `{"success": true, "message": "Администратор создан."}`

> ⚠️ После создания администратора страница `/api/admin/setup` автоматически отключается.

### Загрузка начальных данных (seed)
Seed-данные (стратегия AAABAA) загружаются автоматически через Alembic при `alembic upgrade head`.

### Проверка auth-flow
```bash
# 1. Запрос OTP на email
curl -X POST https://64dao.ru/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@64dao.ru"}'

# 2. Проверка OTP (код придёт на почту)
curl -X POST https://64dao.ru/api/auth/verify \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email": "admin@64dao.ru", "code": "12345"}'

# Кука auth-token сохранится в cookies.txt
```

---

## 10. Настройка бэкапов

### Установка cron-задачи
```bash
# Открываем crontab
crontab -e

# Добавляем строку (запуск в 03:00 каждую ночь):
0 3 * * * bash /var/www/64dao/deploy/scripts/backup.sh >> /var/log/64dao-backup.log 2>&1
```

### Ручной запуск
```bash
bash /var/www/64dao/deploy/scripts/backup.sh
```

### Проверка бэкапов
```bash
ls -lh /var/backups/64dao/db/
ls -lh /var/backups/64dao/uploads/
```

### Восстановление из бэкапа
```bash
# PostgreSQL
gunzip < /var/backups/64dao/db/db_2024-01-01_03-00-00.sql.gz | \
  sudo -u postgres psql dao64

# Uploads — ТОЛЬКО в том dao64_uploads, НЕ на хостовый путь.
#
# Распаковка в /var/www/64dao/uploads/ создаёт на хосте каталог с
# рантайм-настройками, среди которых tochka_settings.json с JWT банка.
# Приложение работает с томом; хостовый путь отдаётся другим механизмом
# и правила deny в vhosts/64dao.conf его не прикрывают. Восстановление
# туда превращает аварийную процедуру в утечку.
#
# Бэкап снимается из тома (backup.sh: tar czf ... -C /data .),
# восстанавливается симметрично.
docker run --rm \
  -v dao64_uploads:/data \
  -v /var/backups/64dao/uploads:/bk:ro \
  alpine tar xzf /bk/uploads_2024-01-01_03-00-00.tar.gz -C /data
```

---

## 11. Обновление кода

### Docker-режим
```bash
cd /var/www/64dao
bash deploy/scripts/deploy.sh --mode docker
```

Скрипт выполнит:
1. `git pull` (если есть git)
2. `docker compose build`
3. `alembic upgrade head`
4. `docker compose up -d --force-recreate`

### Systemd-режим
```bash
bash /var/www/64dao/deploy/scripts/deploy.sh --mode systemd
```

### Быстрый перезапуск без пересборки
```bash
# Docker:
docker compose restart backend frontend

# Systemd:
systemctl restart 64dao-backend 64dao-frontend
```

---

## 12. Мониторинг и логи

### Просмотр логов

**Docker:**
```bash
# Все сервисы
docker compose logs -f

# Только backend
docker compose logs -f backend

# Последние 100 строк
docker compose logs --tail=100 backend
```

**Systemd:**
```bash
# Backend в реальном времени
journalctl -u 64dao-backend -f

# Frontend за последний час
journalctl -u 64dao-frontend --since "1 hour ago"

# Nginx
tail -f /var/log/nginx/64dao.error.log
tail -f /var/log/nginx/64dao.access.log
```

### Health checks
```bash
# API health
curl -sf https://64dao.ru/api/health | python3 -m json.tool

# Статус Docker
docker compose ps

# Статус Systemd
systemctl status 64dao-backend 64dao-frontend

# Использование ресурсов
htop
df -h
docker stats --no-stream
```

### Статус бэкапов
```bash
tail -50 /var/log/64dao-backup.log
```

---

## 13. Решение проблем

### Backend не запускается
```bash
# Docker
docker compose logs backend | tail -50

# Systemd
journalctl -u 64dao-backend -n 50

# Частые причины:
# - Неверные данные в .env (проверьте DB_PASS, JWT_SECRET)
# - PostgreSQL недоступен (docker compose ps db)
# - Порт 8000 занят (ss -tlnp | grep 8000)
```

### OTP-письма не приходят
```bash
# Включите DEBUG=true в backend/.env для вывода OTP в лог
# Docker:
docker compose logs backend | grep "DEBUG OTP"

# Systemd:
journalctl -u 64dao-backend | grep "DEBUG OTP"

# Проверьте SMTP настройки:
python3 -c "
import asyncio, aiosmtplib
from email.mime.text import MIMEText
msg = MIMEText('Test')
msg['Subject'] = 'Test'
msg['From'] = 'noreply@64dao.ru'
msg['To'] = 'ваш@email.ru'
asyncio.run(aiosmtplib.send(msg, hostname='smtp.timeweb.com', port=465,
    username='noreply@64dao.ru', password='ПАРОЛЬ', use_tls=True))
print('OK')
"
```

### Куки не передаются (CORS ошибки)
```bash
# Проверьте APP_URL в backend/.env — без trailing slash
echo $APP_URL  # должно быть https://64dao.ru (не https://64dao.ru/)

# Проверьте что Nginx передаёт Set-Cookie
curl -vI https://64dao.ru/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.ru"}' 2>&1 | grep -i "set-cookie"
```

### 502 Bad Gateway
```bash
# Backend не запущен или упал
docker compose ps   # проверьте статус
curl localhost:8000/api/health  # проверьте напрямую

# Frontend не запущен
curl localhost:3000   # должен вернуть HTML
```

### SSL ошибки
```bash
# Проверьте сертификат
certbot certificates

# Принудительное обновление
certbot renew --force-renewal

# Проверьте что DNS указывает на ваш IP
dig 64dao.ru +short
```

### Место на диске закончилось
```bash
# Что занимает место:
df -h
du -sh /var/www/64dao/uploads/*
du -sh /var/backups/64dao/*
docker system df

# Очистка Docker мусора
docker system prune -f

# Старые логи
journalctl --vacuum-size=500M
```

---

## Полезные команды

```bash
# ── Docker ──────────────────────────────────────────────────
docker compose up -d              # запуск
docker compose down               # остановка
docker compose restart backend    # перезапуск одного сервиса
docker compose exec backend bash  # войти в контейнер
docker compose exec db psql -U dao64 dao64  # подключиться к БД

# ── Alembic ─────────────────────────────────────────────────
# Docker:
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current

# Systemd:
cd /var/www/64dao/backend && ../venv/bin/alembic upgrade head

# ── PostgreSQL ───────────────────────────────────────────────
sudo -u postgres psql dao64          # войти в БД
\dt                                  # список таблиц
SELECT count(*) FROM users;          # пример запроса
\q                                   # выход

# ── Certbot ─────────────────────────────────────────────────
certbot certificates                 # список сертификатов
certbot renew --dry-run              # тест обновления
certbot renew                        # принудительное обновление
```
