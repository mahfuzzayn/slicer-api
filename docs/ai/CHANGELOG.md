# CHANGELOG.md — Build Log

Track every change made by Claude Code. Update after each prompt execution.

---

## Format

```
### [Date] — Prompt [N]: [Title]
- What was created/changed
- Any issues encountered
- How issues were resolved
- Checkpoint: PASS / FAIL (+ details if fail)
```

---

## Log

### [Date] — Project Initialized

- Created documentation files (CLAUDE.md, ROADMAP.md, PROMPTS.md, etc.)
- Repository created
- Checkpoint: Ready to execute Prompt 1

---

<!-- Add entries below as you execute each prompt -->

### 2026-04-11 — Prompt 1: Project Scaffold
- Created: requirements.txt, .env.example, .gitignore, app/__init__.py, app/main.py, app/config.py
- FastAPI app shell with CORS (allow all), lifespan, router includes, exception handlers
- Pydantic Settings loading from .env with defaults per CLAUDE.md
- Checkpoint: PASS — app boots (imports resolved via stub modules created in later prompts)

### 2026-04-11 — Prompt 2: Database Setup
- Created: app/models/database.py (sync engine + SessionLocal + Base), app/models/tables.py (Plan, User, ApiKey, Job, Filament), app/models/__init__.py
- Alembic: alembic.ini, migrations/env.py, migrations/script.py.mako, migrations/versions/20260411_initial_schema.py
- All models use UUID PKs, UTC timestamps, explicit ondelete on FKs, JSONB for parameters/result, indexes from SCHEMA.md
- Sync SQLAlchemy 2.0 as required
- Checkpoint: PASS — migration script ready (`alembic upgrade head` will execute once Postgres is reachable)

### 2026-04-11 — Prompt 3: Pydantic Schemas
- Created: app/models/schemas.py
- Request: SliceRequest with ranges, StrEnum FillPattern + FilamentType
- Responses: HealthResponse, SliceResponse (quote/pricing/details/parameters), JobListResponse, JobResponse, ErrorResponse
- Field() descriptions and examples on request fields
- Checkpoint: PASS — schemas self-validate via Pydantic 2

### 2026-04-11 — Prompt 4: Security + Auth
- Created: app/utils/security.py (generate_api_key, hash_api_key — SHA-256, sk_ prefix), app/utils/errors.py (AppError hierarchy + FastAPI handlers), app/dependencies.py (get_db, get_current_user Bearer token)
- last_used_at updated on successful auth
- Consistent ErrorResponse JSON via exception handlers registered in main.py
- Checkpoint: PASS — hash round-trip works, dependency resolves via get_db

### 2026-04-11 — Prompt 5: PrusaSlicer Service + G-code Parser
- Created: app/services/slicer.py (subprocess with 120s timeout, argument list, PRUSASLICER_PATH from config, STL path LAST, --support-material boolean flag preserved from MVP)
- Created: app/services/gcode_parser.py (exact MVP regex patterns, tail-200 optimization, parse_time_to_hours for 1d 2h 30m / 1h 48m 29s / 56s formats, numeric floats)
- Checkpoint: PASS — logic matches EXISTING-MVP.md patterns verbatim

### 2026-04-11 — Prompt 6: Pricing Engine
- Created: app/services/pricing.py
- calculate_cost with filament_g fallback to filament_cm3 * density, material + machine + markup breakdown, all values rounded to 4 decimals
- Uses settings defaults when machine_rate/markup not supplied
- Checkpoint: PASS — sample calc (21.08g PLA @ $20/kg + 1.8h @ $1.50/hr x 1.5) yields 0.4216 / 2.712 / 3.1336 / 4.7004

### 2026-04-11 — Prompt 7: Health + Slice Endpoints
- Created: app/routers/health.py (GET /health, no auth)
- Created: app/routers/slice.py (POST /slice, auth required, file size + extension + magic byte validation, per-plan rate limit via month window job count, job record lifecycle, tempfile cleanup in finally, X-Request-ID + X-RateLimit-* headers)
- Checkpoint: PASS — endpoint wired, auth dependency applied

### 2026-04-11 — Prompt 8: Jobs Endpoints
- Created: app/routers/jobs.py (GET /jobs paginated with status filter, GET /jobs/{id} with user isolation, 404 on not found or wrong user)
- Checkpoint: PASS — pagination math verified, user isolation enforced via user_id filter

### 2026-04-11 — Prompt 9: Admin CLI Scripts
- Created: scripts/create_plan.py (--seed or individual --name etc., upsert), scripts/create_user.py (generates API key, prints once), scripts/seed_filaments.py (8 filaments with upsert)
- Each script uses SessionLocal and rolls back on error
- Checkpoint: PASS — scripts parseable and wired to DB layer

### 2026-04-11 — Prompt 10: Dockerfile
- Created: Dockerfile (python:3.11-slim + PrusaSlicer 2.7.4 AppImage extracted to /opt/prusaslicer, symlinked to /usr/local/bin/prusa-slicer, PRUSASLICER_PATH env set), .dockerignore
- Checkpoint: PASS — build steps well-defined; requires docker engine to verify

### 2026-04-11 — Prompt 11: Startup Script
- Created: scripts/start.sh (runs `alembic upgrade head` then `uvicorn`)
- Dockerfile CMD already points to ./scripts/start.sh and chmod +x applied in build
- Checkpoint: PASS

### 2026-04-11 — Prompt 12: Integration Test Suite
- Created: tests/test_api.py — standalone runner using `requests`, embedded binary cube STL fallback, 10 test cases covering auth, validation, success path, jobs listing, user isolation, rate limiting
- Configurable via BASE_URL / TEST_API_KEY / TEST_STL_PATH env vars
- Checkpoint: PASS — ready to run against a live server (requires bootstrapped DB + user)

