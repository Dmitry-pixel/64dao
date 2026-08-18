# backend/certs — сертификаты НУЦ Минцифры России

| Файл | Что это |
|---|---|
| `russian_trusted_root_ca.crt` | Корневой «Russian Trusted Root CA» |
| `russian_trusted_sub_ca.crt`  | Выпускающий «Russian Trusted Sub CA» |

Формат PEM. Источник: <https://www.gosuslugi.ru/crt>.

## Зачем

На 2026-08 `enter.tochka.com` отдаётся по сертификату TrustAsia, который есть
в certifi. Сертификаты Минцифры ставятся на упреждение: если TrustAsia отзовут,
Точка переключится на НУЦ Минцифры, которого в стандартных хранилищах нет,
и вызовы бэкенда упадут с `unable to get local issuer certificate`.

Файлы вкомпилируются в backend-образ (`backend/Dockerfile`) и склеиваются
с бандлом certifi в `/etc/ssl/tochka/tochka-ca-bundle.pem`, который
`app/tochka_client.py` передаёт в httpx через `verify=`.

## Обновление

    ./deploy/scripts/fetch-russian-ca.sh

Сверьте SHA-256-отпечатки с gosuslugi.ru перед коммитом.

## Чего эти файлы НЕ решают

Влияют только на исходящие соединения сервера. Браузер клиента, которого
редиректим на `paymentLink` (`*.tochka.com`), использует своё хранилище.
