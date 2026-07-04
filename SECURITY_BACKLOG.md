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

## Остаточный риск — 2 CVE, одна первопричина

Обе удерживаются устаревшим python-jose. Обе низкоэксплуатируемы в текущей
конфигурации (JWT на HS256 — асимметричный/ASN.1-путь не задействован).

| CVE | Пакет | Почему остаётся | Эксплуатируемость |
|---|---|---|---|
| PYSEC-2025-185 | python-jose | без fix-версии | низкая (алгоритм задан явным списком в auth.py) |
| CVE-2026-30922 | pyasn1 0.4.8 | транзитивно: jose→rsa→pyasn1-modules удерживают pyasn1 <0.5 | низкая (HS256, ASN.1 не парсится) |

Прямой пин pyasn1==0.6.3 невозможен: ResolutionImpossible из-за python-jose.

---

## Задача №1 (приоритет высокий) — миграция python-jose → PyJWT

Первопричинное решение: закрывает ОБЕ остаточные CVE разом и упрощает дерево
(PyJWT для HS256 не тянет rsa/pyasn1 — они нужны только для асимметричных алгоритмов).

Scope — изменение кода в backend/app/auth.py:
- 7 вызовов jwt.encode/jwt.decode (строки ~38, 59, 87, 127, 133 + импорт стр. 5)
- Текущий паттерн: явный algorithm=settings.jwt_algorithm при encode,
  algorithms=[settings.jwt_algorithm] при decode — воспроизвести 1:1 в PyJWT
- jose.JWTError → jwt.PyJWTError (обработка ошибок декодирования)
- requirements.txt: убрать python-jose[cryptography], добавить PyJWT

Проверка после: прогон 144 тестов в dao64_test (особенно test_auth.py —
encode→decode цикл), затем финальный pip-audit → ожидаемо 0 уязвимостей.

Риск регрессии: умеренный, покрыт тестами. HS256 — прямой аналог, API PyJWT
близок к jose.

---

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
