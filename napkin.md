
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
