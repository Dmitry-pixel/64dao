
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
