# 64dao — мультиконтурная диагностика: передаточный документ

Дата: 2026-07-21. Для продолжения работы в новой сессии.

---

## Что это за задача

Расширение диагностики Метода 1 в проекте 64dao.ru. К существующему финансовому контуру
(24 утверждения → гексаграмма зрелости) добавляются три однотипных: Продукт/Сервис, Рынок
и продажи, Операционные процессы. Пользователь проходит их из кабинета после основной
диагностики; отчёт дополняется секциями и сводной картой, которая указывает контур —
системное ограничение.

Основание — планы в репозитории (`64dao_contours_block_plan.md`, `64dao_expansion_master.md`,
`64dao_transition_route_plan.md`) плюс разбор с 14 решениями владельца. Разбор и план работ
лежат в этой же папке: `64dao_contours_plan_review.md`, `64dao_contours_workplan.md`.

**Метод 2 (BMC) в скоуп НЕ входит** — решение владельца, остаётся как есть.

---

## Инфраструктура и рабочие правила

- Сервер: `root@188.225.77.18`, путь `/var/www/64dao`. GitHub `Dmitry-pixel/64dao`, ветка `main`.
- Стек: FastAPI + SQLAlchemy 2 async + Alembic + PostgreSQL 16 + Next.js 14 App Router + Docker Compose.
- Работаем так: правки готовятся Python-скриптами (`cat > /tmp/x.py << 'PYEOF' … PYEOF`),
  с проверкой `assert content.count(old) == 1` перед заменой. Пользователь запускает команды
  в консоли на сервере и вставляет вывод обратно.
- **Backend без source volume**: после ЛЮБОЙ правки `.py` или `tests/` —
  `docker compose build backend && docker compose up -d backend`. `restart` НЕ подхватывает код.
- **Frontend**: `docker compose build --build-arg NEXT_PUBLIC_API_URL=https://64dao.ru frontend && docker compose up -d frontend`.
- Тесты в образе (Dockerfile ставит `requirements-test.txt`): `docker compose exec backend python -m pytest tests/X.py -q`. Файлы гонять по одному.
- БД: `docker compose exec -T db psql -U dao64 -d dao64`. Тестовая — `dao64_test`, изолирована.
- **Многострочные вставки в консоль пользователя рвутся** — длинные скрипты слать частями
  по 40–60 строк либо через `docker compose exec -T backend python < /tmp/file.py`.
- Проверять применение патча в контейнере через `grep` до тестов.

---

## Ключевые технические решения (14 поправок, все приняты)

1. `maturity_index` не меняется — число Ян-линий 0..6. Линия 5 остаётся.
2. Спецификация финблока восстановлена из git (`7d2d1ff`), файл `finance_hexagram_questionnare_spec.MD`.
3. Пути документов — корень репозитория, не `docs/`.
4. Админ-сброс контура — есть.
5. Версионирования отчёта нет: PDF пересобирается при каждом скачивании (`reports.py`, флаг `regenerate_pdf_on_download`).
6. Тай-брейк контура-ограничения: минимальный индекс → больше подвижных линий → при полном равенстве ограничение НЕ назначается (не по алфавиту).
7. Вето 4.1 — отдельным блоком «Условие, блокирующее трансформацию» до приоритетов.
8. `assessments.method` (`method1`/`method2`) — колонка уже была в БД вне alembic, миграция 009 её засыпает. Чинит баг: диагностика Метода 1 с комбинацией `AAAAAA` рендерилась как Метод 2.
9. Контурные секции — только 9 подразделов интерпретации, БЕЗ профиля стратегии (график ЖЦ, сценарий, маркетинг, предположения). Профиль только у финансовой функции.
10. Порядок разделов: 01 Текущее состояние · 02 Целевой сценарий · 03 Финансовая функция · 04 Сводная карта · 05–07 контуры.
11. `fin_content.contour` — sentinel `'common'`, не NULL (иначе UNIQUE не работает в PostgreSQL).
12. Per-contour флаги — runtime-store `contour_settings.py` (JSON в volume, через `UPLOAD_DIR`), не env.
13. Лимит «не знаю» = 3 на контур, плюс не более 1 на блок. Кнопка «Не знаю» гаснет при исчерпании обоих лимитов.
14. Заглушка перехода: «Описание перехода будет добавлено при публикации стратегии». `transition_description` пуст у всех 64 стратегий — контентная задача владельца.

**Правило паритета (решение владельца):** HTML-отчёт и PDF несут одинаковый состав разделов,
различается только форма. Каждый раздел добавляется одновременно в `finance_pdf.py` и в
`report/[id]/page.tsx` (теперь через общие компоненты).

---

## Сделано (этапы H, 0, 1, 2, 3, 4 — закоммичены; этап 5 — в процессе)

### Хотфикс H — коммит `c84e9b6`
Детект метода `is_method2` переведён с `method2_data is not None` на `bool(method2_data)` +
явный признак из `build_html_for_assessment`. Чинит потерю разделов у комбинации `AAAAAA`.

### Этап 0 — документы
Мастер-план и планы приведены к 14 решениям (скрипт `etap0_docs.py`). Спецификация финблока
восстановлена (`b7ca24b`). Сверка реализации со спецификацией — расхождений нет, кроме
намеренного лимита «не знаю».

### Этап 1 — миграция 009 (`3e12962`, `9dafc9d`)
Таблица `assessment_contours` (id, assessment_id, contour, answers, result JSONB, combination,
CHECK на contour/combination/jsonb_typeof). Колонка `assessments.method`. Колонка
`fin_content.contour` DEFAULT `'common'` + UNIQUE(kind,key,contour). Перенос finance-данных
из колонок `finance_*` (не удалены — rollback-окно до миграции 010). Финансовый контур пишется
двойной записью: в `assessment_contours` (основное) и в старые колонки. Модель `AssessmentContour`,
`AssessmentOut.passed_contours`.

Нюанс из прода: JSONB-поля хранили JSON-`null` вместо SQL NULL (SQLAlchemy `none_as_null`).
Миграция нормализует. Фильтр переноса — `jsonb_typeof(finance_result)='object'`.

### Этап 2 — обобщение скоринга (`cead5ba`)
`contour_scoring.py` — `ContourSpec` + `compute_contour_result(answers, spec)`. `finance_scoring.py`
стал тонкой обёрткой. Контрольный кейс §3.7 проходит байт-в-байт. `finance_interpret.build_interpretation`
получил параметр `blocks` и ключ `veto_block`. `load_content(session, contour)` с резолюцией через `common`.
Вето выводится отдельным блоком в PDF и HTML. HTML выровнен по составу разделов с PDF.

### Этап 3 — реестр, API, флаги (коммит с "этап 3")
`contours.py` — реестр 4 контуров, 96 утверждений из `64dao_contours_questionnaires_draft.md` v1.0,
`CONTOUR_ORDER = (finance, product, process, market)`, `INTRO_TEXTS`. `contour_settings.py` —
runtime-флаги. Эндпоинты: `GET /api/method1/contours`, `GET /api/method1/contour-items/{contour}`,
`POST /api/assessments/{id}/contours/{contour}`, `DELETE /api/admin/assessments/{id}/contours/{contour}`,
`GET|PUT /api/admin/contours`. Тесты: `test_contours.py` (27), `test_contours_api.py` (16).
Финансовый контур защищён от выключения и сброса.

### Этап 4 — фронт прохождения (`05163ab` + рефактор детекта)
`components/ContourSurvey.tsx` — общий степпер с экраном проверки ответов. Страница
`assessment/contour/[contour]`. Развилка `assessment/continue` — цепочка после каждого контура
(как переход к финблоку после 6 вопросов). Блоки контуров на дашборде и в `/admin/my-reports`
(с кнопками прохождения). Приглашение дополнить в отчёте. Финансовый блок Метода 1 переведён
на `ContourSurvey` — теперь единый степпер. Детект метода сведён в `lib/api.isMethod2` (был в 4 местах).
Лимит «не знаю» гасит кнопку и по блоку, и по анкете.

### Этап 5 — отчёт (В ПРОЦЕССЕ, НЕ ЗАКОММИЧЕНО)
**Бэкенд готов:**
- `contour_summary.py` — `build_summary(results)`: выбор ограничения, тай-брейки, разрыв. Тесты `test_contour_summary.py` (12).
- `finance_pdf.py` — `finance_section_html` обобщён в `contour_section_html(…, blocks, title, section_no)`; `finance_section_html` — обёртка (section_no=03). Добавлен `summary_card_html`.
- `assessments.py` — `load_report_contours(db, assessment, finance_result)` собирает секции контуров и сводную карту; используется и в PDF, и в эндпоинте `finance-interpretation` (теперь отдаёт `contours`, `summary`, `line_titles`).
- `pdf.py` — `build_report_html` получил `extra_contours`, `summary`; порядок разделов изменён; «Целевой сценарий» перенумерован в 02; блок `page2` (`if False:`) убран.

**Фронт готов:**
- `components/ContourReportSection.tsx` — 9 подразделов секции (стили передаются пропом, названия линий с сервера, профиль стратегии — через children только у финблока).
- `components/ContourSummaryCard.tsx` — таблица + вердикт (тексты дословно как в PDF).
- `report/[id]/page.tsx` — финансовая секция переведена на компонент, добавлены сводная карта и контурные секции, «Целевой сценарий» перенесён на позицию 02, оглавление вычисляется по составу отчёта.

**Проверено вживую:** PDF диагностики `790d45aa` (2 доп. контура) — порядок и нумерация верны.
HTML — «Целевой сценарий» переставлен, оглавление динамическое.

---

## Что осталось в этапе 5

1. **Финальная сверка HTML ↔ PDF** на диагностике `790d45aa`: состав разделов, названия линий
   контуров (должны отличаться от финансовых — «Продуктовые процессы» и т.д.), выделение
   контура-ограничения, вердикт сводной карты дословно.
2. **Разрывы страниц в PDF** при 4 контурах — визуальный контроль (`page-break-inside: avoid`).
3. **Фикстурный тест рендера** 4-контурного отчёта (план §5 предусматривает; оценить объём —
   решение по свёртке секций принимать по факту).
4. **Коммит этапа 5** — файлы: `contour_summary.py`, `finance_pdf.py`, `pdf.py`,
   `routers/assessments.py`, `tests/test_contour_summary.py`, `components/ContourReportSection.tsx`,
   `components/ContourSummaryCard.tsx`, `report/[id]/page.tsx`.

## Что осталось после этапа 5

- **Этап 6 — админка:** селектор контура в редакторе `fin_content` (переопределения контента),
  страница управления флагами контуров (сейчас только консольная команда `set_contour_enabled`),
  кнопка сброса контура в админке. Пункты в `AdminNav` (править только `frontend/components/AdminNav.tsx`).

## Follow-up (не блокирует, вне ядра этапов)

- F2: убрать откат `_load_contour` на колонки `finance_*` — вместе с миграцией 010 (удаление колонок после стабилизации).
- F4: аудит других таблиц на расхождение схема/модель (как было с `assessments.method`).
- F5: мёртвая `lifecycle_badge_html` в `build_report_html`.
- F7: 64 описания перехода (`transition_description`) — контент владельца.
- F9: `tax_settings.py` держит путь жёстко, не развязан с боевым томом через `UPLOAD_DIR` — тест `set_vat_enabled` переключил бы НДС в проде (таких тестов нет).

## Вне скоупа (роадмап, отдельные планы)

Фичи B (маршрут перехода), C (Метод 2 — отложен), D (AI-чат), E (динамика/подписка),
F (чек-листы) — после завершения A.

---

## Данные прода для проверки

- Диагностика `790d45aa` — Метод 1, 3 контура (finance, product, process).
- Диагностика `c2221690` — Метод 1, 2 контура (finance, product).
- Включённые контуры: все четыре (`set_contour_enabled` вызывался для product, process, market).
- Клиентов нет, все диагностики тестовые.

## Как продолжить

Первым шагом — открыть отчёт `790d45aa` в браузере и скачать его PDF, сверить по правилу
паритета. Затем закоммитить этап 5. Затем этап 6 (админка). Разбор и план работ — в файлах
`64dao_contours_plan_review.md` и `64dao_contours_workplan.md` этой папки.
