# Security Backlog — 64dao

Контекст: результат SAST-цикла от 2026-07-04 (commit b8f9a24).
Инструменты: bandit, semgrep, gitleaks, pip-audit, npm audit.

## Закрыто в цикле b8f9a24 (~40 CVE)

| Пакет | Было | Стало | CVE |
|---|---|---|---|
| python-jose | 3.3.0 | 3.4.0 | PYSEC-2024-232/233 (4 из 5) |
| fastapi | 0.115.5 | 0.139.0 | — (тянет starlette 1.3.1) |
| starlette | 0.41.3 | 1.3.1 | 8 CVE |
| python-multipart | 0.0.12 | 0.0.31 | 7 CVE |
| python-dotenv | 1.0.1 | 1.2.2 | CVE-2026-28684 |
| next | 14.2.5 | 14.2.35 | ~20 advisories (вкл. middleware bypass) |
| — | нет lock | package-lock.json | детерминизм сборок |

Верификация: 144/144 теста зелёные, landing 200 OK, backend стартует чисто.

---

## Остаточный риск — 0 CVE (закрыто в commit ниже)

Обе CVE устранены миграцией python-jose -> PyJWT 2.13.0.
jose удалён из дерева (PYSEC-2025-185); pyasn1 CVE-2026-30922 ушла
вместе с транзитивной цепочкой jose->rsa->pyasn1-modules.
pip-audit по requirements.txt: No known vulnerabilities found.
144/144 теста зелёные на PyJWT 2.13.0.

## Задача №1 — ВЫПОЛНЕНО (миграция python-jose -> PyJWT)

Статус: DONE. PyJWT 2.13.0 в проде, 0 CVE в дереве зависимостей.
auth.py: заменён импорт (jose->jwt) + 2 обработчика (JWTError->PyJWTError).
Вызовы encode/decode не менялись — HS256 API-совместим.
Урок метода: pip-audit -r в контейнере подмешивает CVE самого pip —
читать колонку Name, не строку 'Found N'.

## Задача №2 (условная) — апгрейд next 14 → 15

Триггер: появление в коде next/image ИЛИ realtime/WebSocket-функций.
Сейчас 4 остаточных next-CVE неэксплуатируемы (проверено grep):
- нет next/image → GHSA-h64f (DoS Image Opt) неприменим
- нет i18n, App Router → GHSA-36qx неприменим
- нет proxy_cache в nginx → GHSA-wfc6 (RSC cache poison) без вектора
- нет realtime → GHSA-c4j6 (SSRF WebSocket) без вектора

До появления триггера — не трогать (мажорная миграция, риск для мобильной вёрстки).

---

## Задача №3 (низкий) — чистка debug-логов в email.py

email.py строки 116/125/134/153: логируют OTP-код, reset-ссылку, PII.
Обёрнуты в if settings.debug — в проде DEBUG=false, не исполняются.
Гигиена: убрать при следующем плановом касании email.py.
Некорректна семантика logger.warning для OTP (стр. 116).

---

## Ложные срабатывания (подтверждено, не требуют действий)

- bandit B311 (auth.py random) — timing-джиттер против user enumeration, не токены
- middleware bypass — backend защищён Depends(require_admin), обход даёт пустую оболочку
- dangerouslySetInnerHTML (AboutShell/LegalShell) — контент только от админа
- gitleaks — чисто, 151 коммит, секретов нет
