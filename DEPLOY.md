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
8a. [Сертификат НУЦ Минцифры (для API Точки)](#8a-сертификат-нуц-минцифры-для-api-точки)
9. [Первый запуск и администратор](#9-первый-запуск-и-администратор)
10. [Настройка бэкапов](#10-настройка-бэкапов)
10a. [Досверка зависших оплат](#10a-досверка-зависших-оплат)
10b. [Проверка живости сайта](#10b-проверка-живости-сайта)
10c. [Диск, база и бэкапы](#10c-диск-база-и-бэкапы)
10d. [Наблюдатель 5xx](#10d-наблюдатель-5xx)
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
- **UFW Firewall** — открывает только 22, 80, 443 (на боевом сервере дополнительно 8888 — панель FastPanel и 10050 — агент Zabbix, только для адресов мониторинга Timeweb)
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

## 8a. Сертификат НУЦ Минцифры (для API Точки)

### Что это решает, а что нет

Это не сертификат для 64dao.ru — домен обслуживается Let's Encrypt (раздел 8).
Речь о корневом сертификате НУЦ Минцифры в хранилище доверия контейнера backend.

| Соединение | Хост | CA | Чьё хранилище | Решается здесь |
|---|---|---|---|---|
| backend -> API банка | enter.tochka.com | НУЦ Минцифры | контейнер backend | Да |
| браузер клиента -> страница оплаты | merch.securepaytb.ru | GlobalSign | устройство клиента | Нет, и не нужно |
| браузер -> 64dao.ru | 64dao.ru | Let's Encrypt | устройство клиента | не требуется |

**Исправлено 2026-09-24.** Здесь было написано, что клиент уходит на paymentLink
на `*.tochka.com`. Это неверно: ссылка из `orders.tochka_payment_link` ведёт на
эквайринговый домен `merch.securepaytb.ru`, и он отдаётся коммерческим CA
GlobalSign, чей корень есть в Chrome, Firefox и Safari по умолчанию.

Значит клиентской проблемы с сертификатами не существует. Переход Точки на
Минцифры 30 августа 2026 затронул только серверное соединение с API.

Эта строка прожила в документе два месяца непроверенной, и на ней успели
построиться два решения — страница помощи `/help/payment-certificate` и экран
подтверждения перед оплатой (откачен 2026-09-24). Проверка стоила одной команды
`openssl s_client`.

### Состояние на 2026-09-25

Цепочка `enter.tochka.com`:

```
0  CN=*.tochka.com, O=Joint-Stock Company Tochka   NotAfter: Jun 18 2027
1  CN=Russian Trusted Sub CA                        NotAfter: Jul 19 2029
2  CN=Russian Trusted Root CA                       NotAfter: Feb 27 2032
```

Точка присылает полную цепочку, включая корень. Доверие держится на нашем
вендоренном КОРНЕ (до 2032). Выпускающий сертификат в проверке не участвует —
банк присылает свой.

Цепочка `merch.securepaytb.ru`: `*.securepaytb.ru` -> GlobalSign GCC R46 DV TLS
CA 2025 -> GlobalSign Root R46 (до 2046).

### Установка

```bash
cd /var/www/64dao
./deploy/scripts/fetch-russian-ca.sh
docker compose build backend
docker compose up -d --force-recreate backend
```

docker compose restart НЕДОСТАТОЧНО: сертификаты вкомпилированы в образ.
--force-recreate тоже обязателен — без него compose оставляет работать
контейнер на старом образе (наступали 2026-08-18, см. раздел 11).

Проверенные отпечатки SHA-256:

```
root: D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31
sub:  BB:BD:E2:10:3E:79:0B:99:9E:C6:2B:D0:3C:F6:25:A5:A2:E7:C3:16:E1:0A:FE:6A:49:0E:ED:EA:D8:B3:FD:9B
```

### Как устроено

- сертификаты вендорятся в backend/certs/ — сборка не зависит от gu-st.ru;
- Dockerfile вызывает update-ca-certificates (системное хранилище контейнера для
  curl/wget/Playwright) и scripts/build_ca_bundle.py, который собирает
  /etc/ssl/tochka/tochka-ca-bundle.pem = certifi + Минцифры;
- app/tochka_client.py передаёт бандл в httpx во все 4 вызова;
- пути лежат ВНЕ /app: в docker-compose.yml поверх /app монтируется ./backend
  с хоста и перекрывает всё, что образ положил в /app;
- блок сертификатов стоит ПОСЛЕ playwright install: иначе обнуляется кеш слоя
  с Chromium и сборка растягивается с 8 секунд до 2m43s.

### Вендоренный выпускающий сертификат устарел — и это нормально

Наша копия sub истекает 2027-03-06 (серийный 1002, выпуск 02.03.2022). В бою
Точка использует ДРУГОЙ sub с тем же именем: выпуск 15.07.2024, до 19.07.2029.

Проверено 2026-09-23: повторный запуск `fetch-russian-ca.sh` скачал тот же самый
сертификат, git diff пуст. На лендинге gu-st.ru лежит предыдущее поколение —
то, что вендорено у нас. Актуальный sub там не публикуется вовсе.

Следствия:

- прежний вывод «просроченный sub = отказ оплаты» НЕВЕРЕН и снят;
- файл остаётся лежать как безвредная страховка: OpenSSL 1.1+ перебирает
  альтернативные пути построения цепочки, что подтверждает рабочее рукопожатие;
- тревога по его сроку убрана из мониторинга, иначе с 5 января 2027 письмо
  приходило бы каждую неделю о несуществующей проблеме;
- обновить его через fetch-russian-ca.sh нельзя — скрипт обновляет то, что
  опубликовано, а опубликовано старое.

### Грабли (наступали 2026-08-18)

gu-st.ru отдаёт файлы с CRLF и без завершающего перевода строки. При склейке через
cat последняя строка одного файла срасталась с первой строкой следующего:

```
-----END CERTIFICATE----------BEGIN CERTIFICATE-----
```

OpenSSL валил весь бандл с [X509] PEM lib, при этом каждый сертификат по
отдельности парсился нормально. Поэтому бандл собирается build_ca_bundle.py
(вырезание PEM-блоков + нормализация) и проверяется загрузкой в ssl на сборке:
битый бандл роняет docker build, а не доезжает до рантайма.

Вывод на будущее: счётчик вхождений BEGIN CERTIFICATE — не проверка. Проверка —
это загрузка артефакта тем же кодом, что использует рантайм.

### Проверка

```bash
docker compose exec -T backend python -c "from app.tochka_client import TOCHKA_SSL_VERIFY; print(TOCHKA_SSL_VERIFY)"
docker compose exec -T backend pytest tests/test_tochka_tls.py -q
docker compose exec -T backend python -c "import httpx,os; v=os.getenv('TOCHKA_SSL_VERIFY') or '/etc/ssl/tochka/tochka-ca-bundle.pem'; print('TLS OK', httpx.get('https://enter.tochka.com/uapi/open-banking/v1.0/', verify=v).status_code)"
```

Значение должно быть путём к бандлу, не True. `TLS OK 403` = рукопожатие прошло
(403 — API отшивает запрос без JWT, это норма).

Полная приёмка — только тестовым платежом на 1 рубль через /admin/test-payment:
синтетика покрывает лишь один из четырёх вызовов httpx. Последняя такая приёмка
2026-09-25: заказ создан 09:11, стал paid в 09:13 без ручного вмешательства,
возврат через /admin/orders отработал.

### Обслуживание

Что и когда истекает:

| Что | Где | Срок | Требует действий |
|---|---|---|---|
| Russian Trusted Root CA | backend/certs/, в образе | 27.02.2032 | Раз в ~6 лет |
| Наша копия Russian Trusted Sub CA | там же | 06.03.2027 | Нет, см. выше |
| Sub, который реально работает | присылает Точка | 19.07.2029 | Нет |
| Лист *.tochka.com | присылает Точка | 18.06.2027 | Нет, обновляет банк |
| Лист *.securepaytb.ru | эквайер | 13.03.2027 | Нет, обновляет эквайер |

Реальная ручная работа здесь — один корневой сертификат примерно раз в шесть лет.

#### Автоматический контроль

Host cron раз в неделю запускает `deploy/scripts/check-ca-expiry.sh`, внутри —
`app/jobs/check_ca_expiry.py`. Задача наблюдает пять вещей и шлёт письмо на
`SUPPORT_EMAIL` при СМЕНЕ СОСТОЯНИЯ, а не при каждом срабатывании условия:

| Наблюдение | Источник | Условие письма |
|---|---|---|
| Рукопожатие с enter.tochka.com бандлом приложения | живое соединение | не прошло -> письмо; восстановилось -> письмо |
| Издатель сертификата enter.tochka.com | живое соединение | сменился |
| Срок корня НУЦ Минцифры | файл в образе | меньше CA_EXPIRY_WARN_DAYS (60), один раз |
| Срок сертификата банка | живое соединение | меньше CA_LEAF_WARN_DAYS (14) |
| Доверие к merch.securepaytb.ru по корням Mozilla | живое соединение | перестало проходить / сменился издатель / истекает |

Главная здесь — ПЕРВАЯ. Счётчик дней отвечает на вопрос «когда сломается»,
рукопожатие — на вопрос «работает ли сейчас». Доверие умеет отказать по причине,
которой нет ни в одном счётчике: битый бандл после пересборки, переход банка на
неизвестный нам УЦ, отзыв сертификата.

Две вещи, которые легко сделать неправильно (обе закреплены тестами):

- **Сетевой сбой не равен отказу доверия.** ssl.SSLError наследуется от OSError,
  поэтому порядок except значим: ошибка TLS -> тревога, ошибка сокета -> молчание
  и состояние не перезаписывается. Иначе таймаут банка выглядел бы как поломка, а
  следующий успешный запуск — как восстановление.
- **Страница оплаты проверяется корнями Mozilla (certifi), а НЕ системным
  хранилищем контейнера.** В системное через update-ca-certificates добавлен
  корень Минцифры, и «проверка прошла» там означала бы лишь то, что мы сами его
  положили. Вопрос же стоит иначе: откроется ли страница у клиента, который
  ничего не устанавливал.

Хост страницы оплаты вынесен в `PAY_PAGE_HOST` — сменится эквайер, правится
переменной окружения.

Установка cron:

```bash
crontab -e
# Воскресенье 04:10 — после ночного бэкапа в 03:00
10 4 * * 0 bash /var/www/64dao/deploy/scripts/check-ca-expiry.sh >> /var/log/64dao-ca-check.log 2>&1
```

Ручной запуск и проверка:

```bash
bash /var/www/64dao/deploy/scripts/check-ca-expiry.sh
docker compose exec -T backend pytest tests/test_check_ca_expiry.py -q
```

Первый запуск только запоминает текущих издателей в `ca_check.json` (volume
uploads) — письма о смене пойдут со следующего изменения.

#### Процедура по письму

Читать по причине, указанной в письме. Прежняя универсальная инструкция
«запустить fetch-russian-ca.sh» нерабочая: скрипт обновляет только то, что
опубликовано на gu-st.ru.

**Рукопожатие с банком не проходит.** Оплата сейчас не работает.

1. Посмотреть живую цепочку:
   `echo | openssl s_client -connect enter.tochka.com:443 -servername enter.tochka.com -showcerts 2>/dev/null | grep -E '^ *[0-9]+ s:|^ *i:|NotAfter'`
2. Если корень в цепочке незнакомый — добавить его в backend/certs/, пересобрать
   образ, поднять с --force-recreate.
3. Если цепочка прежняя — проверить бандл: он мог не попасть в образ при сборке.
4. Приёмка платежом 1 ₽ и возврат.

**Сменился издатель enter.tochka.com.** Само по себе не авария: если рукопожатие
проходит, новый УЦ нам уже знаком. Убедиться по первой строке письма и записать
переход в claude/mincifry-ca-tochka.md.

**Истекает корневой сертификат Минцифры.** Это плановая работа раз в несколько
лет: fetch-russian-ca.sh, сверить отпечатки с https://www.gosuslugi.ru/crt,
коммит, build backend, up -d --force-recreate, приёмка платежом.

**Сменился издатель или истекает сертификат merch.securepaytb.ru.** Это про
клиента, а не про нас. Если проверка по корням Mozilla перестала проходить —
у клиентов в Chrome, Firefox и Safari оплата открывается с предупреждением
безопасности. Наших действий с сертификатами тут нет, но именно в этом случае
имеет смысл вернуть предупреждение на странице покупки и обновить
`/help/payment-certificate`.

### Раздел «Сертификаты» в админке

`GET /api/admin/certs` + страница `/admin/certs` (блок «Система») показывают то
же, что письмо: результат рукопожатия, издателей и сроки обоих хостов, сроки и
отпечатки вендоренных сертификатов, дату последней плановой проверки.

Решения, которые важно не переиграть:

- **Только чтение.** Загрузки сертификатов через админку нет и не планируется:
  интерфейс, умеющий добавлять корневые CA, — это интерфейс загрузки якорей
  доверия. Получивший доступ к админке встаёт между нами и банком, а JWT уходит
  в заголовке Authorization. Операция нужна раз в несколько лет и делается на
  сервере — постоянный риск ради редкой операции невыгоден.
- **Один источник истины:** страница вызывает ту же observe(), что и задача.
- **Открывается без опроса банка** (`?probe=0`), живое рукопожатие — по кнопке,
  потому что при недоступности банка оно ждёт до 15 секунд.
- **Наше соединение и взгляд клиента — разные блоки.** Смешать их значит
  повторить ошибку, из которой вырос откаченный экран подтверждения.

Проверка регистрации роута — через HTTP и OpenAPI, не перебором app.routes: в
текущей версии FastAPI там лежат объекты _IncludedRouter без атрибута path.

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/api/admin/certs   # 401
docker compose exec -T backend python -c "from app.main import app; print([p for p in app.openapi()['paths'] if 'certs' in p])"
```

main.py читается при старте, поэтому после правки регистрации роутера нужен
docker compose restart backend — хотя сам код и смонтирован с хоста.

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

## 10a. Досверка зависших оплат

Точка повторяет доставку вебхука 30 раз с интервалом 10 секунд — около пяти
минут. Если сервер в это окно недоступен (деплой, перезапуск, сбой сети),
повторы заканчиваются, и заказ остаётся `pending`: деньги списаны, доступ не
выдан. Кредиты считаются по оплаченным заказам, поэтому один незакрытый
статус — ровно один неоткрытый отчёт.

Задача `deploy/scripts/reconcile-pending.sh` раз в час спрашивает у банка
статус зависших заказов и доводит их до `paid` (или `failed`). Ручная сверка
никуда не делась — `POST /api/payments/admin/reconcile` по-прежнему проходит
и по возвратам, — но она требует, чтобы кто-то заметил проблему.

### Установка cron

```bash
crontab -e
# Каждый час в :25 — вне пиков и не совпадает с бэкапом в 03:00
25 * * * * bash /var/www/64dao/deploy/scripts/reconcile-pending.sh >> /var/log/64dao-reconcile.log 2>&1
```

### Настройки (backend/.env, обе необязательны)

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `RECONCILE_STALE_MINUTES` | 15 | Заказы моложе этого срока банк ещё повторяет сам — не трогаем |
| `RECONCILE_MAX_AGE_DAYS` | 7 | Дальше этой границы `pending` — брошенная корзина |

### Ручной запуск и проверка

```bash
bash /var/www/64dao/deploy/scripts/reconcile-pending.sh
docker compose exec -T backend pytest tests/test_reconcile_pending.py -q
```

В логе `/var/log/64dao-reconcile.log` смотреть строки «вебхук не дошёл»:
каждая — оплата, которую банк подтвердил, а мы узнали только сверкой. Если
такие строки идут регулярно, чинить надо доставку вебхуков, а не сверку.

---

## 10b. Проверка живости сайта

Smoke-тесты в `backend/tests/test_smoke.py` помечены маркером `live` и
исключены из прогона (`addopts = -m "not live"`), поэтому не запускаются ни
локально, ни в CI. Вдобавок pytest не входит в боевой образ. То есть
автоматической проверки, что сайт вообще отвечает, до этого не было.

Задача `deploy/scripts/smoke-prod.sh` каждые 15 минут проходит по десяти
проверкам: health бэкенда, закрытость кабинета и админки без входа,
публичные документы, 404 на несуществующем маршруте, отдача примера отчёта
в PDF, главная страница и страница входа. Запросов с побочными эффектами
нет — никаких login и register, чтобы задача не рассылала коды.

Проверка идёт снаружи, через публичный адрес: вместе с nginx, TLS и
фронтендом, ровно как её видит клиент.

### Письма

Уходят на `SUPPORT_EMAIL` при смене состояния: «сайт не отвечает» и потом
«сайт снова отвечает». О продолжающейся аварии повторных писем нет — иначе
за ночь простоя придёт сотня одинаковых. Состояние хранится в
`smoke_state.json` в volume uploads.

### Установка cron

```bash
crontab -e
# В :07, :22, :37, :52 — вразнобой с остальными задачами
7,22,37,52 * * * * bash /var/www/64dao/deploy/scripts/smoke-prod.sh >> /var/log/64dao-smoke.log 2>&1
```

### Настройки (backend/.env, обе необязательны)

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `SMOKE_BASE_URL` | `https://64dao.ru` | Что проверяем |
| `SMOKE_TIMEOUT` | 10 | Таймаут одного запроса, секунды |

### Ручной запуск и проверка

```bash
bash /var/www/64dao/deploy/scripts/smoke-prod.sh
docker compose exec -T backend pytest tests/test_smoke_prod.py -q
```

Здоровый ответ — `все 10 проверок пройдены`. При провале задача печатает
список и возвращает код 1.

---

## 10c. Диск, база и бэкапы

Бэкапы делаются по расписанию с 03:00, но до этого никто не проверял, что
они действительно делаются. Молчаливый отказ здесь опаснее всего: каталог
с архивами выглядит наполненным, а внутри последнего файла — обрывок или
ноль байт, и выясняется это в момент, когда бэкап понадобился.

Задача `deploy/scripts/check-storage.sh` раз в сутки проверяет:

- свободное место на диске;
- возраст последнего дампа БД — бэкап мог перестать делаться;
- размер дампа — пустой архив выглядит как успешный бэкап;
- резкое падение размера: прерванный `pg_dump` тоже оставляет файл, просто
  короче обычного;
- то же для архива uploads.

Размер базы задача берёт сама запросом к Postgres и печатает в отчёт.

Устроено в два слоя: бэкапы и диск видны только с хоста, поэтому цифры
собирает shell-скрипт и передаёт в контейнер, а пороги и письмо живут в
`app/jobs/check_storage.py` — рядом с остальными задачами и общим SMTP.

### Установка cron

```bash
crontab -e
# 04:40 — после ночного бэкапа в 03:00, чтобы проверять свежий
40 4 * * * bash /var/www/64dao/deploy/scripts/check-storage.sh >> /var/log/64dao-storage.log 2>&1
```

### Настройки (backend/.env, все необязательны)

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `STORAGE_DISK_WARN_PERCENT` | 15 | Меньше этой доли свободного места — тревога |
| `BACKUP_MAX_AGE_HOURS` | 26 | Старше — бэкап считается несделанным |
| `BACKUP_MIN_BYTES` | 10240 | Меньше — архив считается пустым |
| `BACKUP_SHRINK_PERCENT` | 50 | На сколько дамп может усохнуть относительно предыдущего |

### Ручной запуск и проверка

```bash
bash /var/www/64dao/deploy/scripts/check-storage.sh
docker compose exec -T backend pytest tests/test_check_storage.py -q
```

Здоровый ответ — показатели и строка `хранилище в порядке`. Проверить, что
письмо доходит, можно завышенным порогом:

```bash
cd /var/www/64dao && STORAGE_DISK_WARN_PERCENT=99 bash deploy/scripts/check-storage.sh
```

Порог 99% гарантированно сработает, уйдёт письмо, а следующий обычный запуск
пришлёт «с хранилищем снова порядок».

---

## 10d. Наблюдатель 5xx

Отдельно от задач в cron на хосте работает наблюдатель за ответами 5xx.
Он читает общий access-лог FastPanel и присылает письмо на админский ящик,
когда сайт начинает отвечать ошибками сервера.

| Что | Где |
|---|---|
| Скрипт | `/opt/64dao-alerts/alert_watcher.py` (в репозитории его нет) |
| Запуск | `64dao-alerts.timer` → `64dao-alerts.service` |
| Настройки | `/etc/64dao-alerts.env` (права только root, в репозиторий не кладётся) |
| Читает | `/var/log/fastpanel2/fastpanel2.access.log` |
| Отправка | `smtp.timeweb.ru:465`, локальный exim не используется |

Ключи в `/etc/64dao-alerts.env`: `NGINX_ACCESS_LOG`, `STATE_FILE`,
`WEBHOOK_PATH`, `SITE_NAME`, `MAX_SAMPLES`, `SMTP_HOST`, `SMTP_PORT`,
`SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `ALERT_EMAIL_TO`.

`backup.sh` сохраняет юниты `64dao-alerts.service` и `.timer`, но не сам
скрипт и не env-файл. При переезде на новый сервер их нужно перенести
вручную, иначе наблюдатель молча пропадёт.

### Проверка

```bash
systemctl is-active 64dao-alerts.timer
systemctl list-timers 64dao-alerts.timer --no-pager
journalctl -u 64dao-alerts.service -n 20 --no-pager
# ключи настроек без значений
sed -E 's/=.*/=***/' /etc/64dao-alerts.env
```

Access-лог ротирует `/etc/logrotate.d/fastpanel2-nginx`. Отключать или
переносить этот лог нельзя: наблюдатель перестанет видеть ошибки.

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

### Ручная пересборка одного сервиса

```bash
docker compose build frontend
docker compose up -d --force-recreate frontend
```

`--force-recreate` обязателен. Без него `docker compose up -d` может оставить
контейнер на прежнем образе и ответить `Running` вместо `Started` — сборка
проходит, а в проде остаётся старый код. Проверка, что развернулось именно то,
что собрано:

```bash
docker inspect --format 'контейнер: {{.Image}}' dao64_frontend
docker images --no-trunc --format 'образ:      {{.ID}}' 64dao-frontend
```

Идентификаторы должны совпадать. Скрипт `deploy.sh` этой ошибке не подвержен:
он вызывает `up -d --force-recreate`.

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

Полный разбор по категориям с пометками «можно удалить автоматически» /
«нужна проверка» / «не трогать» даёт `deploy/scripts/disk_audit.sh`.
Скрипт только читает, ничего не удаляет:

```bash
bash /var/www/64dao/deploy/scripts/disk_audit.sh 2>&1 | tee /root/disk_audit_report.txt
```

Образ `alpine` не удалять: он используется при восстановлении uploads
из бэкапа (раздел 10).

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
