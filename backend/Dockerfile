FROM python:3.11-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl wget ca-certificates openssl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

# ── Сертификаты НУЦ Минцифры России ──────────────────────────────────────────
# На 2026-08 enter.tochka.com отдаётся по сертификату TrustAsia, который есть в
# certifi. Сертификаты Минцифры ставим на упреждение: если TrustAsia отзовут,
# Точка переключится на НУЦ Минцифры, которого в стандартных хранилищах нет,
# и httpx упадёт с SSLCertVerificationError.
#
# Файлы вендорятся в репозиторий (backend/certs/), обновление —
# ./deploy/scripts/fetch-russian-ca.sh. Источник: https://www.gosuslugi.ru/crt
#
# Кладём ВНЕ /app: в docker-compose.yml поверх /app монтируется ./backend
# с хоста, и всё, что образ положил в /app, перекрывается бинд-маунтом.
COPY certs/russian_trusted_root_ca.crt certs/russian_trusted_sub_ca.crt \
     /usr/local/share/ca-certificates/russian-trusted/

COPY scripts/build_ca_bundle.py /usr/local/bin/build_ca_bundle.py

RUN update-ca-certificates && python /usr/local/bin/build_ca_bundle.py

# Бандл «стандартные CA + Минцифры». Явный verify= в клиенте Точки оставляет
# доверие к CA Минцифры в границах вызовов к банку.
ENV TOCHKA_CA_BUNDLE=/etc/ssl/tochka/tochka-ca-bundle.pem


COPY requirements-test.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements-test.txt
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
