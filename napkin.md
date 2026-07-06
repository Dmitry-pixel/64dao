
## SEO / Next.js Gotchas

1. **[2026-07-06] Динамический сегмент [slug] без generateStaticParams → force-dynamic → no-store**
   Do instead: добавить `generateStaticParams()` в `page.tsx` для `/documents/[slug]` (и любых будущих `[param]`-роутов) — иначе Cache-Control: private/no-store, нестабильный ответ под краулерами (воспроизведено: Google Rich Results Test — Crawl failed до фикса, valid item после).

2. **[2026-07-06] JSON-LD в Next.js App Router**
   Do instead: `<script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(data)}} />` без `<head>` — рендерится в body корректно. Компонент `frontend/components/JsonLd.tsx`, переиспользуется на всех страницах.
