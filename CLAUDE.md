# CLAUDE.md

Guidance for Claude / AI agents working in this repository. Keep it truthful: if a rule here contradicts the code, fix the code or fix this file — do not leave both.

## Session Lifecycle

- **Starting:** read `napkin.md` (real gotchas) and the latest handoff if one exists. Resume context.
- **Ending:** if work is in-progress, write a handoff. Save any correction from the operator so the same mistake isn't repeated.

## How I Work

- Direct, no fluff. Skip preambles.
- NO em dashes. Use colons or split sentences.
- Lead with recommendations, not option lists.
- Production-ready code, not "a starting point."
- One focused sub-agent per task (see `.claude/agents/`). Keep the main chat clean.
- Verify before calling it done: run the relevant tests, check the diff, confirm the patch is in the running container.

## Project

Web app for business strategy diagnostics based on 64 hexagrams / stratagems (I Ching). User answers 6 A/B questions -> a 6-char combination like `ABABBA` -> mapped to one of 64 strategies -> structured report (HTML in the account + PDF). Single-operator SaaS (ИП Подласов Д.С.), Russian-language, `64dao.ru`. Monetization: one-off paid reports via Точка Банк (no subscriptions, no multi-tenancy).

## Stack (actual)

- **Backend:** FastAPI 0.139 · SQLAlchemy 2 async · asyncpg · PostgreSQL 16 · Alembic 1.14 · Pydantic v2 + pydantic-settings · PyJWT 2.13 (HS256) · passlib[bcrypt] · aiosmtplib · slowapi · Playwright 1.49 (Chromium, HTML->PDF).
- **Frontend:** Next.js 14.2.35 App Router · React 18 · TypeScript 5 · Tailwind · react-hook-form + zod · lucide-react. Standalone Docker output.
- **Infra:** Docker Compose · FastPanel nginx on the host (ports 80/443) · VPS.
- **Payments:** Точка Банк acquiring (JWT auth, RS256 webhook signature). **No Stripe.**
- **Email:** aiosmtplib to `smtp.timeweb.ru:465`, in-house template system in `app/email.py`. **No Resend.**
- **Jobs:** none. Scheduling is host cron (backup, docker cache cleanup). **No BullMQ, no in-app scheduler.**

There is no Prisma, no ORM other than SQLAlchemy, no message queue, and no tenant isolation layer. Ignore any past reference to those.

## Key Commands

**Local dev (Docker):**
```bash
cp backend/.env.example  backend/.env        # fill DB, JWT, SMTP, Точка vars
cp frontend/.env.example frontend/.env.local
docker compose up -d --build
```

**Backend tests** (pytest is NOT in the prod image — install first):
```bash
docker compose exec backend pip install -r requirements-test.txt
docker compose exec backend pytest tests/ -q          # run per-file if cross-file InterfaceError appears
# `live`-marked tests (test_smoke.py, test_sanity.py::TestLiveAPI) hit https://64dao.ru and need network
```

**Frontend scripts** (from `frontend/package.json`): `next dev` · `next build` · `next start` · `next lint`. There is no `test` or `typecheck` script — type errors surface during `next build`.

**Migrations (Alembic, inside backend container):**
```bash
docker exec dao64_backend alembic upgrade head
docker exec dao64_backend alembic revision --autogenerate -m "description"
```

## Deploy (manual, push from the server over SSH)

There is **no CI/CD**. Deploy is manual. Updates are committed and pushed from the VPS itself.

```bash
# On the VPS:
cd /var/www/64dao
git add <files> && git commit -m "..." && git push origin main
docker compose build backend && docker compose up -d backend      # backend-only
docker compose build frontend && docker compose up -d frontend    # frontend-only
docker compose build && docker compose up -d                      # full
```

**Backend source IS mounted** (`docker-compose.yml` mounts `./backend:/app` next to `uploads`). `uvicorn` runs without `--reload`, so a `.py` change needs `docker compose restart backend`, not a rebuild. Rebuild only when dependencies or the Dockerfile change. Frontend is the opposite: it is baked into the image and always needs `build` then `up -d`.

After a schema change, run `alembic upgrade head` in the container as a separate step: it is not part of the build. The migration file is visible to the container immediately (mounted source), but push it to `origin/main` BEFORE upgrading prod, or the version pointer in the database references a revision missing from git.

**Logs / health:**
```bash
docker logs dao64_backend --tail 50
curl -sk https://64dao.ru/api/health
```

**Rollback:** `git reset --hard <prev>` + rebuild. Alembic downgrades are not routinely tested — check the migration's `downgrade()` before relying on it.

## Architecture

- API routes stay thin and call into helper modules; there is no formal service layer and none is needed at this scale.
- Domain settings (price, VAT, Точка token, site mode) live as JSON files in the `dao64_uploads` volume via dedicated modules: `pricing_store.py`, `tax_settings.py`, `tochka_settings.py`, `site_mode.py`. Read/write only through these, never duplicate the defaults.
- Use the existing email template system in `app/email.py`; do not add a new one.
- Do not add cron inside the app. Host cron handles backup and cache cleanup.

### Backend (`backend/app/`)
- **Entry:** `main.py` — mounts routers, CORS (exact `app_url`, no trailing slash), slowapi rate limiter, global exception handler, `/api/health`, static `/uploads` mount, lifespan.
- **Auth:** `auth.py` — OTP email flow (regular users are passwordless), JWT in httpOnly+secure+samesite cookie `auth-token`; admin impersonation token carries `impersonated_by`; user-enumeration timing jitter on login.
- **Rate limiter:** `limiter.py` — keys by real client IP via `X-Real-IP` (set by nginx `/api`), not the proxy IP. Do not revert to bare `get_remote_address` or the limit becomes global.
- **Routers:** `routers/` — `auth`, `assessments`, `reports`, `admin`, `strategies`, `documents`, `payments`, `pricing`, `contact`, `support`, `social_links`, `sample_report`, `site_mode` (each `/api/<name>`).
- **Models:** `models.py` — `User`, `OtpCode`, `Strategy`, `Assessment`, `Report`, `Order`.
- **PDF:** `pdf.py` — Playwright renders HTML -> PDF. Report sections 01-04 are synchronized between HTML and PDF. Do not modify the combination-assembly or the U+4DC0..U+4DFF hexagram-symbol logic.
- **Payments:** `tochka_client.py` (`create_payment_with_receipt`, `get_payment_status`, `refund_payment`, `verify_and_decode_webhook`). Webhook body is a bare RS256 JWT string (Content-Type text/plain), verified against Точка's public key — not JSON.
- **Config:** `config.py` — pydantic-settings from `.env`. Feature flags: `enforce_credits` (default False); payment enable lives in `pricing.json`.

### Frontend (`frontend/`)
- **Path alias:** `tsconfig.json` sets `"@/*": ["./*"]` -> `@/` resolves to `frontend/`, NOT `frontend/src/`.
  - `@/lib/api` -> `frontend/lib/api.ts` (the real API client)
  - `@/components/AdminNav` -> `frontend/components/AdminNav.tsx`
- **Pages:** `src/app/` (App Router). `(auth)` group = login/register/verify/forgot/reset. Admin under `src/app/admin/*`.
- **Shared components:** `frontend/components/`. NOTE: `frontend/src/components/` is dead code (a stale duplicate `AdminNav.tsx` lives there) — do not import from it; prefer deleting it.
- `middleware.ts` guards routes; real authorization is enforced server-side via `Depends(require_admin)` / `get_current_user`.
- `styled-jsx` (`<style jsx>`) works only in Client Components. For Server Component pages, put `@media` rules in `globals.css`.
- Dynamic `[slug]` routes need `generateStaticParams()` or they go `force-dynamic`/`no-store` and block crawling (see `napkin.md`).

### Admin impersonation
`POST /api/admin/impersonate/{user_id}` (admin-only) · `POST /api/admin/impersonate/stop` · `GET /api/admin/impersonate/status` (both current-user, work while impersonating).

### Production infrastructure
- VPS, Ubuntu, FastPanel. FastPanel's own nginx (`fastpanel2-nginx`) holds 80/443; the compose nginx service is disabled. The LIVE vhost is on the host at `/usr/local/fastpanel2-nginx/vhosts/64dao.conf` (outside this repo); `deploy/nginx/*.conf` are reference copies and DO drift from it. Verify on the host before trusting them.
- `location /uploads/` proxies to the backend and is hardened with `deny` rules for `*.json` (secrets/config) and `/uploads/reports/` (PII). If FastPanel regenerates the vhost, re-add these and re-check `curl https://64dao.ru/uploads/tochka_settings.json` returns 404.
- Containers: `dao64_backend` (127.0.0.1:8000), `dao64_frontend` (127.0.0.1:3000), `dao64_db`. Volume `dao64_uploads` mounted at `/var/www/64dao/uploads`.

### Build-time vs runtime env
`NEXT_PUBLIC_API_URL` is baked into the JS bundle at build time via the `build.args` in `docker-compose.yml` (`https://64dao.ru`). Changing it in `.env.local` at runtime has no effect.

## Important Constraints

- Next.js 14 (not 15): `params` in page components is a plain object. Use `params.id` directly, not `React.use(params)`.
- Async SQLAlchemy: `await db.flush()` after mutations; commit happens in the `get_db` dependency.
- CORS is strict: `allow_origins` must exactly match `settings.app_url` (no trailing slash).
- Admin bootstrap: `POST /api/admin/setup` works once (before any admin exists) and requires `ADMIN_SETUP_KEY`.
- `role` CheckConstraint allows only `('user','admin')`. Code still references an `editor` role (`assessments.py`, `strategies.py`) — those branches are currently dead. Resolve before relying on `editor`.
- Secrets and JSON settings must NOT be reachable via nginx static `/uploads/`. Storing credentials there exposed them publicly once — keep the nginx `deny` rules in place.
- Schema changes go through Alembic only. Do not hand-edit the DB on prod without a paired migration. New migrations must reach `origin/main` BEFORE `alembic upgrade` on prod, or the version pointer will reference a missing revision.

## Testing

- Tests in `backend/tests/` (auth, assessments, reports, strategies, admin, sanity, smoke).
- Every feature: success, validation-failure, and not-found tests.
- Do not mock the database unless existing tests do.
- Uncovered routers (add smoke when touched): `payments`, `support`, `contact`, `site_mode`, `social_links`, `sample_report`.

## Don't do

- Do not log raw payment payloads, OTP codes, reset links, or PII (debug logs in `email.py` are gated behind `settings.debug`; keep it that way).
- Do not return raw database errors to the client.
- Do not edit migrations after they are merged.
- Do not enable `ENFORCE_CREDITS` / `pricing.payment_enabled` until `payments` has smoke coverage.
- Do not mix a refactor and a behavior change in one commit without saying so.
