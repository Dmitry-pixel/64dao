# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Web application for business strategy diagnostics based on 64 hexagrams (I Ching). Users answer 6 A/B questions → get a combination like `ABABBA` → system maps it to one of 64 strategies → generates a PDF report.

**Stack:** FastAPI 0.115 · PostgreSQL 16 · SQLAlchemy 2 async · Next.js 14 App Router · Docker Compose · FastPanel nginx (host)

## Key Commands

### Deploy to production (from local Windows, SSH to VPS)
```bash
# Full redeploy after git push
ssh root@188.225.77.18 "cd /var/www/64dao && git fetch origin && git reset --hard origin/main && docker compose build && docker compose up -d"

# Rebuild only backend (faster, after Python-only changes)
ssh root@188.225.77.18 "cd /var/www/64dao && git reset --hard origin/main && docker compose build backend && docker compose up -d backend"

# Rebuild only frontend (after TypeScript/Next.js changes)
ssh root@188.225.77.18 "cd /var/www/64dao && git reset --hard origin/main && docker compose build frontend && docker compose up -d"
```

### Logs and debugging
```bash
ssh root@188.225.77.18 "docker logs dao64_backend --tail 50"
ssh root@188.225.77.18 "docker logs dao64_frontend --tail 30"
ssh root@188.225.77.18 "curl -sk https://64dao.ru/api/health"
```

### Database migrations (Alembic)
```bash
# Run inside backend container on VPS
ssh root@188.225.77.18 "docker exec dao64_backend alembic upgrade head"
ssh root@188.225.77.18 "docker exec dao64_backend alembic revision --autogenerate -m 'description'"
```

### Local development
```bash
cp backend/.env.example backend/.env  # fill in DB, JWT, SMTP vars
cp frontend/.env.example frontend/.env.local
docker compose up -d --build
```

## Architecture

### Backend (`backend/`)
- **Entry:** `app/main.py` — mounts all routers, CORS, rate limiter (slowapi), lifespan
- **Auth:** `app/auth.py` — OTP email flow (no passwords for regular users), JWT in httpOnly cookie `auth-token`, impersonation token with `impersonated_by` field
- **Routers:** `app/routers/` — `auth`, `assessments`, `reports`, `admin` (each with `/api/<name>` prefix)
- **Models:** `app/models.py` — `User`, `OtpCode`, `Strategy`, `Assessment`, `Report`, `Order`
- **PDF:** `app/pdf.py` — uses Playwright to render HTML → PDF
- **Config:** `app/config.py` — all settings from `.env` via pydantic-settings

### Frontend (`frontend/`)
**Critical path alias:** `tsconfig.json` sets `"@/*": ["./*"]` — this means `@/` resolves to `frontend/`, NOT `frontend/src/`. So:
- `@/lib/api` → `frontend/lib/api.ts` ← **the real API client**
- `@/components/AdminNav` → `frontend/components/AdminNav.tsx`
- Files under `frontend/src/` must use `@/src/...` or relative imports to reach siblings

**App structure:**
- `src/app/` — Next.js App Router pages (all user-facing routes)
- `src/app/(auth)/` — login, register, verify (grouped, no extra layout)
- `components/` — shared components (AppNav, AdminNav, ImpersonationBanner, Logo)
- `lib/api.ts` — all API calls, centralized `adminApi` object
- `middleware.ts` — protects routes, redirects unauthenticated users

### Admin Impersonation
Admin can view the app as any non-admin user:
- `POST /api/admin/impersonate/{user_id}` — sets auth cookie with `impersonated_by` field
- `POST /api/admin/impersonate/stop` — restores admin cookie
- `GET /api/admin/impersonate/status` — frontend polls this to show banner
- `ImpersonationBanner` component is injected in root `layout.tsx`, shown globally when active

### Production Infrastructure
- **Server:** VPS 188.225.77.18, Ubuntu, FastPanel hosting panel
- **Nginx:** FastPanel's own nginx (`fastpanel2-nginx`) holds ports 80/443. Config at `/etc/nginx/fastpanel2-sites/64dao-static.conf`. Our Docker nginx is **disabled** (commented out in compose).
- **Docker containers:** `dao64_backend` (port 127.0.0.1:8000), `dao64_frontend` (port 127.0.0.1:3000), `dao64_db`. Nginx proxies `/api/` → backend, `/` → frontend.
- **Uploads volume:** `dao64_uploads` — persists between deploys, mounted at `/var/www/64dao/uploads`
- **SSH key:** `~/.ssh/id_ed25519` on dev machine is authorized on VPS root

### Build-time vs runtime env vars
`NEXT_PUBLIC_API_URL` is a **build-time** variable baked into the JS bundle. It must be set as a build `arg` in `docker-compose.yml` (currently `https://64dao.ru`). Changing it in `.env.local` at runtime has no effect.

### Data flow: Assessment → Strategy
1. User answers 6 questions (A or B each) → `method1_combination` = 6-char string e.g. `ABABBA`
2. Each combination maps to one of 64 hexagrams via binary index
3. `Strategy` table in DB stores content for each combination
4. `Assessment` status: `draft` → `completed` → `paid`
5. `Report` is generated as PDF via Playwright when assessment is paid/completed

## Important Constraints
- Next.js 14 (not 15): `params` in page components is a plain object, not a Promise. Do **not** use `React.use(params)` — use `params.id` directly.
- Async SQLAlchemy: always `await db.flush()` after mutations, commit happens in `get_db` dependency.
- CORS is strict: `allow_origins` must exactly match `settings.app_url` — no trailing slash.
- Admin setup: `POST /api/admin/setup` works only once (before any admin exists) and requires `ADMIN_SETUP_KEY` from `.env`.
