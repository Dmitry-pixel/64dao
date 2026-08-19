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

## Linting & CI

1. **[2026-08-19] Prod runs Python 3.11 — CI must match**
   Do instead: keep `python-version: "3.11"` in `ci.yml` and `target-version = "py311"` in `backend/ruff.toml`. `backend/Dockerfile` is `python:3.11-bullseye`; a 3.12 CI can go green while the container fails on 3.12-only syntax.

2. **[2026-08-19] Re-export modules break under ruff autofix (F401 + I001 together)**
   Do instead: keep the `per-file-ignores` entries for `app/finance_scoring.py`, `app/contour_summary.py`, `app/contour_route.py`, `app/email.py`, `app/routers/admin.py`. isort splits the import block so a line-level `# noqa: F401` stops covering the tail, then F401 deletes those names — this made `app.main` unimportable (lost `BlockUnderfilledError`).

3. **[2026-08-19] ruff is pinned to 0.15.11 in CI**
   Do instead: `pip install ruff==0.15.11`. An unpinned ruff ships new rules and turns CI red with no code change.

4. **[2026-08-19] ~90 lint findings are deliberately deferred, not forgotten**
   Do instead: E501 (281), E741 (56), E701/E702 (25), E402 (20), B905 (7) are listed with reasons in the `ignore` block of `backend/ruff.toml`. Enable one rule at a time; B905 and E402 change behaviour.

---

## Deploy & Git

1. **[2026-05-23] Full frontend redeploy command**
   Do instead: `ssh root@188.225.77.18 "cd /var/www/64dao && git reset --hard origin/main && docker compose build frontend && docker compose up -d"`

2. **[2026-05-23] Backend-only redeploy (faster)**
   Do instead (since 2026-07-30): backend code is bind-mounted (`./backend:/app`) — just `docker compose restart backend`. Rebuild only when requirements change.

4. **[2026-08-19] Never run `docker compose` from a repo clone on the server**
   Do instead: use a clone (e.g. `/root/64dao-lint`) for git and lint work only. `container_name` is hard-coded (`dao64_backend`, `dao64_db`), so `docker compose` from a clone collides with the live Postgres. Run tests in CI, not on the server.

5. **[2026-08-19] `/var/www/64dao/backend` is bind-mounted into the running container**
   Do instead: `git pull` there changes live code instantly. Then restart the service (`docker compose restart backend` is enough for code-only changes; `up -d --force-recreate` when compose/env changed) and check `docker compose logs --tail=25 backend` for `ImportError`/`Traceback`. Rollback: `git reset --hard <prev-sha>` + restart.

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

---
## Deploy & Git (added 2026-07-30)
1. **[2026-07-30] `.env` changes need `up -d`, not `restart`**
   Do instead: compose injects `env_file` at container creation, so `restart` reuses the old environment and the stale value silently wins over the file. Cost us an hour on `TOCHKA_MERCHANT_ID`.
2. **[2026-07-30] `TOCHKA_MERCHANT_ID` was declared twice in `.env`**
   Do instead: check for duplicate keys before editing — the last one wins, so filling the first has no effect.

---
## Payments & Tochka (added 2026-07-30)
1. **[2026-07-30] Tochka never sends a refund webhook**
   Do instead: reconcile via `GET /uapi/acquiring/v1.0/payments/{operationId}`. Only five webhook events exist, all for successful operations. A refund made in the bank UI reaches the app only through polling — `POST /api/payments/admin/reconcile`.
2. **[2026-07-30] Get Payment Operation Info returns `Data.Operation[]`, not `Data`**
   Do instead: use `tochka_client.extract_operation(resp)`. Reading `resp["Data"]["status"]` yields None silently, and the "webhook never arrived" fallback dies with it.
3. **[2026-07-30] `refund_payment` needs a non-empty body**
   Do instead: always send `{"Data": {"amount": N}}`. An empty body returns 400 "Field Data : Field required".
4. **[2026-07-30] A retried APPROVED webhook can resurrect a refunded order**
   Do instead: check `order.status == "refunded"` before applying anything. Tochka retries 30 times at 10s intervals until it gets HTTP 200.
5. **[2026-07-30] Credit spend is bound to an order, not counted globally**
   Do instead: set `assessments.order_id` when spending (mirror of `grant_id`). Follow-up diagnostics are part of the parent purchase and must never consume a credit.

---
## Async SQLAlchemy & Schema (added 2026-07-30)
1. **[2026-07-30] `orders.assessment_id` + `assessments.order_id` form an FK cycle**
   Do instead: give `Assessment.orders` and `Order.assessment` explicit `foreign_keys`, and the newer FK `use_alter=True`. Without the first, `configure_mappers()` fails and every ORM call 500s; without the second, `create_all` cannot sort tables.
2. **[2026-07-30] Reading a relationship without eager loading gives `greenlet_spawn` 500**
   Do instead: add `selectinload()` whenever a handler touches a related object. Hit twice: `/api/payments/orders`, then the refund branch of the webhook.
3. **[2026-07-30] `create_all` with checkfirst does not catch up with migrations**
   Do instead: conftest now runs `drop_all` before `create_all`. If the test DB still looks stale: `psql -d dao64_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"`.

---
## Runtime Settings (added 2026-07-30)
1. **[2026-07-30] All runtime flags go through `app/json_store.py`**
   Do instead: a new setting is a thin module with an `UPLOAD_DIR`-based path constant plus `read_json`/`write_json`. Never hardcode `/var/www/64dao/uploads` — tests then read and write production state.
2. **[2026-07-30] Keep the path as a module-level constant**
   Do instead: tests monkeypatch `X_SETTINGS_FILE` by name; hiding the path inside a class instance breaks that.
3. **[2026-07-30] `ENFORCE_CREDITS` is an admin toggle now, not env**
   Do instead: flip it on `/admin/payment-settings`. `.env` is only the default until `credits_settings.json` exists.

---
## Report Content (added 2026-07-30)
1. **[2026-07-30] `marketing_text`, `management_text`, `assm_*` and strategy `lifecycle_stage` are NOT in the report**
   Do instead: they live on `/hexagram/{combination}` pages (section 04 was deliberately unloaded). The PDF links there instead of repeating the text. Do not "fix" tests by re-adding these blocks.
