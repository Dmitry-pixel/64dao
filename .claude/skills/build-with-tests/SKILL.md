---
name: build-with-tests
description: >
  Use when the user asks to build, implement, add, create, extend, or develop
  a feature on the 64dao project. Triggers on phrases like "build a feature",
  "implement an endpoint", "add support for", "create a route", "extend the
  admin panel", "write the code for". Covers the full workflow: read context,
  match existing patterns, write production code + tests, verify with typecheck
  and pytest.
---

# Build a production feature on 64dao

## Step 0 — Orient before writing anything

1. Read `CLAUDE.md` — stack, architecture, path aliases, deploy commands.
2. Read the user's brief or spec.
3. Identify the domain: `auth` · `assessments` · `reports` · `strategies` ·
   `admin` · `documents`.

## Step 1 — Read 2–3 similar features first

Open the closest existing router and its schemas before writing a line:

```bash
cat backend/app/routers/<domain>.py
cat backend/app/schemas.py     # find relevant In/Out schemas
cat backend/app/models.py      # check existing model fields
```

Match existing patterns exactly. Do not introduce new ones.

## Step 2 — Backend conventions

**Router** (`app/routers/<domain>.py`) — HTTP layer only:
- Parse request → auth check → DB query → return schema
- Business logic lives in `app/auth.py`, `app/pdf.py`, `app/email.py` — not in routers
- Auth: `Depends(get_current_user)`, admin: `Depends(require_admin)`
- List endpoints: always `selectinload()` for relationships — no N+1
- After mutations: `await db.flush()`. Never call `db.commit()` manually — it runs in `get_db()`
- Error messages in Russian: `HTTPException(status_code=404, detail="Диагностика не найдена")`

**Naming:**
- Router functions: `verb_noun` — `list_assessments`, `get_assessment`, `create_assessment`
- DB indexes: `ix_tablename_columnname`

**Schema pattern:**
```python
class ThingCreate(BaseModel):
    field: str

class ThingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    field: str
    created_at: datetime
```

## Step 3 — Frontend conventions

- All API calls go in `lib/api.ts` — not inline in page components
- `@/` resolves to `frontend/`, not `frontend/src/` — mind the path alias
- Next.js 14: use `params.id` directly, never `React.use(params)`
- New pages: `src/app/<route>/page.tsx`

## Step 4 — Write tests alongside the implementation

Tests live in `backend/tests/`. Two files, distinct responsibilities:

**`test_sanity.py`** — unit tests, no network, no DB:
- Import the function directly and test in isolation
- Class: `TestThingName`, method: `test_<what>_<expected_result>`
- Cover: happy path, edge cases (empty / None inputs), error cases
- Only test pure Python logic (`app/pdf.py`, `app/schemas.py`, utility functions)

**`test_smoke.py`** — HTTP tests against live VPS:
- Add to the matching existing class or create a new one following the same pattern
- Always guard with `require_vps` session fixture
- Test auth boundaries first: unauthenticated → 401, wrong role → 403

Write tests **after** the implementation in the same commit. Not a strict TDD
red-green loop — confirm the logic is correct first, then pin it with tests.

## Step 5 — Verify before shipping

Run in order:

```bash
# Type check
cd frontend && npx tsc --noEmit

# Lint
cd frontend && npx next lint

# Tests
cd backend && python -m pytest tests/ -v --tb=short
```

Fix all errors before declaring done. If a pre-existing test fails for an
unrelated reason, state it explicitly — do not silently skip.

## Step 6 — Deploy checklist

If a DB migration is needed:
```bash
ssh root@188.225.77.18 "docker exec dao64_backend alembic revision --autogenerate -m 'description'"
ssh root@188.225.77.18 "docker exec dao64_backend alembic upgrade head"
```

Deploy: `git push origin main` → rebuild only the changed service:
```bash
# Backend only
ssh root@188.225.77.18 "cd /var/www/64dao && git reset --hard origin/main && docker compose build backend && docker compose up -d backend"

# Frontend only
ssh root@188.225.77.18 "cd /var/www/64dao && git reset --hard origin/main && docker compose build frontend && docker compose up -d"
```

---

> Do not introduce new libraries, new architectural patterns, or new naming
> conventions without confirming with the user. When in doubt, match what
> already exists.
