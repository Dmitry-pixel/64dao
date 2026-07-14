# Napkin Runbook — 64dao

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

---

## Architecture & Critical Path Aliases

1. **[2026-05-23] `@/` resolves to `frontend/`, NOT `frontend/src/`**
   Do instead: `@/lib/api` → `frontend/lib/api.ts`; `@/components/X` → `frontend/components/X.tsx`. Files under `frontend/src/` must use `@/src/...` or relative imports.

2. **[2026-05-23] `NEXT_PUBLIC_API_URL` is build-time baked into JS bundle**
   Do instead: set it as build `arg` in `docker-compose.yml`. Changing `.env.local` at runtime has zero effect.

3. **[2026-05-23] Next.js 14 (not 15): params is a plain object**
   Do instead: use `params.id` directly. Do NOT use `React.use(params)`.

---

## FastAPI Gotchas

1. **[2026-05-23] Static routes must come BEFORE dynamic routes**
   Do instead: define `/api/admin/impersonate/stop` BEFORE `/api/admin/impersonate/{user_id}`, or FastAPI treats "stop" as a user_id.

2. **[2026-05-23] Async SQLAlchemy: always `await db.flush()` after mutations**
   Do instead: use `db.flush()`, never `db.commit()` in routers — commit happens in the `get_db` dependency.

---

## Hexagram Display (Core Domain Logic)

1. **[2026-05-23] Assessment cards: show strategy_image_url if set, else hexFor fallback**
   Do instead: in dashboard and my-reports hex-block, check `a.strategy_image_url` first → `<img src={API + url}>`. Only fall back to `hexFor()` Unicode if image_url is null. All 64 strategies have images uploaded in DB.

2. **[2026-05-23] hexFor must use King Wen sequence, NOT binary index**
   Do instead: `String.fromCodePoint(0x4DC0 + kingWenNumber - 1)`. Never use `parseInt(binary, 2)` as index — gives wrong hexagram. King Wen map lives in `AdminNav.tsx` (`HEX_INFO`) and `report/[id]/page.tsx` (`HEX_INFO`).

3. **[2026-05-23] HexagramSVG: totalH must fit inside viewBox (Firefox clips strictly)**
   Do instead: `lineH = size * 0.10`, `gap = size * 0.06` → `totalH = 0.90 * size`. Chrome allows SVG overflow; Firefox clips at viewBox edge.

4. **[2026-05-23] AdminNav.tsx is the single source of truth for hexFor, hexNameFor, HexagramSVG**
   Do instead: import from `@/components/AdminNav`. Don't duplicate hex logic in page files unnecessarily.

---

## Deploy & Git

1. **[2026-05-23] Full frontend redeploy command**
   Do instead: `ssh root@188.225.77.18 "cd /var/www/64dao && git reset --hard origin/main && docker compose build frontend && docker compose up -d"`

2. **[2026-05-23] Backend-only redeploy (faster)**
   Do instead: `docker compose build backend && docker compose up -d backend`

3. **[2026-05-23] git index.lock on Windows blocks git commands**
   Do instead: `Remove-Item "...\.git\index.lock" -Force` in PowerShell before retrying.

4. **[2026-05-23] Chrome caches Next.js JS chunks aggressively**
   Do instead: after frontend deploy, clear Chrome cache via `chrome://settings/clearBrowserData` → All time → Cached images and files. Hard refresh (Ctrl+Shift+R) is NOT enough.

---

## User Directives

1. **[2026-05-23] Responses: concise, structured, no fluff, no emotional support**
   Do instead: facts / hypotheses / interpretations / recommendations — clearly separated. Indicate confidence level.

2. **[2026-05-23] I Ching used as strategic analysis framework, not mysticism**
   Do instead: treat hexagrams as archetypes for motivation, decision style, team roles. No religious framing unless explicitly requested.

---

## Testing

1. **[2026-07-14] pytest: нужен `-e DB_NAME=dao64_test` + установка перед каждым прогоном**
   Do instead: `docker compose exec backend pip install -q -r requirements-test.txt` (pytest НЕ в prod-образе, исчезает после каждой пересборки), затем `docker compose exec -e DB_NAME=dao64_test backend pytest tests/<file>.py -v`. Без `-e DB_NAME=dao64_test` conftest падает (assert-защита от прогона по проду `dao64`). Запускать файлы по одному — иначе флейки cross-file InterfaceError. Если базы нет: `docker compose exec db psql -U dao64 -d dao64 -c "CREATE DATABASE dao64_test OWNER dao64;"`.
