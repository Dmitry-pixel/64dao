
## SEO / Next.js Gotchas

1. **[2026-07-06] Динамический сегмент [slug] без generateStaticParams → force-dynamic → no-store**
   Do instead: добавить `generateStaticParams()` в `page.tsx` для `/documents/[slug]` (и любых будущих `[param]`-роутов) — иначе Cache-Control: private/no-store, нестабильный ответ под краулерами (воспроизведено: Google Rich Results Test — Crawl failed до фикса, valid item после).

2. **[2026-07-06] JSON-LD в Next.js App Router**
   Do instead: `<script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(data)}} />` без `<head>` — рендерится в body корректно. Компонент `frontend/components/JsonLd.tsx`, переиспользуется на всех страницах.

## [2026-07-23] Session notes
- PR4b/тест-долг (540d6bb), PR6 email-напоминания (00ec7df), PR5 гейт повтора (28aa48e) — выкачены в origin/main.
- PR6: за 14 дней до конца подписки + «пора повторить» через 90 дней (только подписчикам); cron 06:00 UTC → deploy/scripts/reminders.sh; kill-switch REMINDERS_ENABLED=false.
- PR5: повтор диагностики компании (≥1 завершённой) — только по активной подписке; админ — bypass.
- Доставка патчей через FastPanel-консоль: hex + md5-гейт по ДЕКОДИРОВАННОМУ файлу
  (переносы строк в консоли ломают хеш самого hex, но не сами данные).

## [2026-07-23] Фича F — чек-листы шагов маршрута (выкачено)
- Бэкенд ac97099: миграция 015 + модель RouteProgress (route_progress: assessment_id, contour, line, done_at; наличие строки = шаг выполнен). GET/PUT /api/assessments/{id}/checklist. Хелпер enrich_route в finance_interpret (единый источник обогащения маршрута action_text). Роутер checklist зарегистрирован в main.py. Тесты test_checklist.py (6).
- Фронт 5682c02: страница frontend/src/app/report/[id]/checklist/page.tsx + кнопка «Чек-лист действий» в отчёте (рядом со «Скачать PDF»).
- Без гейта подписки (часть купленной диагностики); все контуры с маршрутом; прогресс % на лету; маршрут детерминирован — в БД только отметки.
- Хвосты на будущее (F2): подпункты шагов от админа, пользовательские пункты.

## [2026-07-26] Окружение, почта, консоль

1. **docker compose restart НЕ перечитывает .env**
   env_file подставляется при создании контейнера. Симптом: на диске новый
   пароль, приложение видит старый; падает не сразу, а при следующем up -d.
   Do instead: после правки backend/.env — docker compose up -d backend.

2. **Правка .env через nano в FastPanel-консоли ломает файл**
   Дважды склеивались соседние строки: DB_USER=dao64 и DB_PASS превратились
   в DB_USER=dao?DB_PASS=... Повреждение тихое, всплывает при пересоздании.
   Do instead: точечная замена через python3 -c с assert на число вхождений;
   редактор открывать только на чтение.

3. **Резервные копии .env не закрывались .gitignore**
   backend/.env игнорировался, backend/.env.bak нет. Секреты ушли бы в
   публичный remote при git add -A. Шаблон backend/.env.* добавлен.
   Do instead: копии удалять сразу после использования.

4. **Timeweb: From обязан совпадать с логином SMTP**
   550 5.7.1 You are not allowed to send messages as support@64dao.ru при
   логине noreply@. Do instead: не давать выбор отправителя в интерфейсе;
   для другого ящика нужны отдельные SMTP-доступы.

5. **Отправка почты была сломана и это не всплывало**
   Пароль ящика сменили в панели, .env остался старым. Писем к отправке не
   было, формы никто не дёргал, в логах чисто.
   Do instead: держать проверку отправки в приёмке перед запуском с клиентами.

6. **now() в PostgreSQL это время начала транзакции**
   Две записи, созданные в одном тесте, получают одинаковый created_at, и
   сортировка по нему даёт произвольный порядок.
   Do instead: в тестах различать записи по признаку, а не по порядку.

## [2026-07-27] Раздел 09 «Динамика» и правило паритета

1. **Раздел 09 — только в PDF. В HTML-отчёт не добавлять.**
   Решение владельца: для экрана есть отдельная кнопка «Динамика» и страница
   `/companies/[id]/dynamics`. `frontend/components/DynamicsSection.tsx`
   намеренно не подключён ни к одной странице — это не забытый код.
   Do instead: правки динамики вести в `dynamics_block.py` (PDF) и на странице
   динамики; состав данных держать одинаковым.

2. **Названия контуров и линий отдаёт бэкенд, клиенты словарей не держат.**
   Первоисточники: `contours.py::CONTOURS[k].title` и `contours.py::LINE_TITLES`.
   В payload динамики уходят `contour_titles` и `line_title` у каждого
   `line_changes[]`. Локальные `CONTOUR_TITLE` / `LINE_LABEL` на фронте удалены.
   Хвост: дубль `CONTOUR_TITLE` остался в `admin/user/[id]/page.tsx` — там
   другой эндпоинт, названий не отдаёт.

3. **Две кнопки «Скачать PDF» на карточке путали: качали базовую диагностику.**
   Симптом: «раздела 09 в PDF нет», хотя он есть. Синяя кнопка справа — базовая
   диагностика, ссылка в блоке повторной — followup.
   Do instead: ссылка в `NestedFollowups.tsx` переименована в
   «Скачать PDF с динамикой». При жалобах на состав PDF первым делом проверять,
   какой `assessment_id` в ссылке.

4. **`regenerate_pdf_on_download = True` (config.py).**
   PDF пересобирается при каждом скачивании, кэша файлов нет. Значит после
   пересборки контейнера достаточно перескачать отчёт.

5. **Код не смонтирован в контейнеры — нужен ребилд.**
   Правка на диске не видна приложению до `docker compose up -d --build`.
   Do instead: после каждого патча проверять образ через
   `docker compose exec -T backend python -c "import inspect; ..."`.

6. **Патчи через python3-heredoc с assert на число вхождений.**
   Якоря брать из `repr()`: в шаблоне `pdf.py` двойные переводы строк, из-за
   чего наивный якорь `"{bmc_section}\n</body>"` не находится.

## [2026-07-27] Названия линий — один источник

1. **`contours.py::LINE_TITLES` — единственный источник названий шести линий.**
   Состав согласован с формулировками анкеты (`_spec` block_titles), в
   контур-нейтральном виде: Процессы / Технологии и системы / Команда /
   Поддержка руководства / Внешняя среда / Видение и стратегия.
   Потребители получают `line_title` в payload и своих словарей не держат:
   раздел 03 (шаги маршрута, через `build_company_lifecycle`) и раздел 09
   (`line_changes[]`, через `contour_diff`).
   Удалены дубли: `pdf.py::_CL_LINE_TITLES`, `CompanyLifecycleSection.tsx`,
   `ContourShiftLine.tsx`, `dynamics/page.tsx`.

2. **В БД названий линий нет — только машинный ключ.**
   `assessment_contours.result.lines[].block` = `processes|systems|team|
   leadership|environment|strategy`. Переименование терминов не требует
   миграции; правится в одном месте.

3. **Названия контуров: `CONTOURS[k].title`, отдаются как `contour_titles`.**
   Хвост: дубль `CONTOUR_TITLE` остался в `admin/user/[id]/page.tsx` — там
   другой эндпоинт, названий не отдаёт.

4. **Формулировки анкеты (`_spec` block_titles) контур-специфичны намеренно.**
   `processes` = «Продуктовые процессы» / «Основные операционные процессы» /
   «Коммерческие процессы»; `environment` у market = «Рыночная среда».
   Do instead: к `LINE_TITLES` их не сводить — это разные уровни абстракции.
