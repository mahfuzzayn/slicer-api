# CLAUDE.md — Project Rules for Claude Code

## Project Identity

- **Name:** slicer-api
- **Purpose:** B2B SaaS API that accepts STL files, slices them via PrusaSlicer CLI, and returns accurate cost estimates
- **Stage:** v1 production build (4-day sprint)

---

## Tech Stack (Locked — Do Not Change)

| Layer      | Technology                              | Version |
| ---------- | --------------------------------------- | ------- |
| Language   | Python                                  | 3.11+   |
| Framework  | FastAPI                                 | 0.115+  |
| Database   | PostgreSQL                              | 15+     |
| ORM        | SQLAlchemy                              | 2.0+    |
| Migrations | Alembic                                 | 1.13+   |
| Slicer     | PrusaSlicer CLI                         | 2.7+    |
| Server     | Uvicorn                                 | 0.30+   |
| Deployment | Coolify (handles reverse proxy + HTTPS) | —       |

---

## Project Structure

```
slicer-api/
├── CLAUDE.md
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry, CORS, lifespan
│   ├── config.py                # Settings from environment variables
│   ├── dependencies.py          # Auth dependency (API key verification)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLAlchemy engine, session, Base
│   │   ├── tables.py            # All table models (User, ApiKey, Job, Plan, Filament)
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py            # GET /health (no auth)
│   │   ├── slice.py             # POST /slice (auth required)
│   │   └── jobs.py              # GET /jobs, GET /jobs/{id} (auth required)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── slicer.py            # PrusaSlicer subprocess execution
│   │   ├── gcode_parser.py      # Parse G-code for filament, time, layers
│   │   └── pricing.py           # Cost calculation engine
│   └── utils/
│       ├── __init__.py
│       ├── security.py          # API key generation, hashing
│       └── errors.py            # Custom exception classes + handlers
├── scripts/
│   ├── create_user.py           # CLI: create user + generate API key
│   ├── create_plan.py           # CLI: create subscription plan
│   └── seed_filaments.py        # CLI: seed filament pricing data
├── migrations/                  # Alembic migration files
│   ├── env.py
│   └── versions/
├── tests/
│   └── test_api.py
├── docs/
│   ├── ai/
│   │   ├── ROADMAP.md
│   │   ├── PROMPTS.md
│   │   └── CHANGELOG.md
│   └── project/
│       ├── ARCHITECTURE.md
│       ├── API-SPEC.md
│       ├── SCHEMA.md
│       ├── DECISIONS.md
│       ├── ENV-SETUP.md
│       └── TESTING.md
```

---

## Coding Rules

### Python Style

- Use type hints on all function signatures
- Use `async def` for all endpoint handlers
- Use Pydantic models for all request/response validation
- Use dependency injection for auth and database sessions
- 4-space indentation, no tabs
- Docstrings on all service functions

### Database

- Always use SQLAlchemy ORM, never raw SQL strings
- Always use Alembic for schema changes, never manual ALTER TABLE
- All timestamps use UTC (`datetime.utcnow()`)
- Use UUID for all primary keys (`uuid.uuid4()`)
- Foreign keys must have `ondelete="CASCADE"` or `ondelete="SET NULL"` explicitly set

### Security

- NEVER store raw API keys — always SHA-256 hash before storing
- NEVER log raw API keys — log only the 8-char prefix
- NEVER pass user input directly into shell commands — use subprocess argument lists
- NEVER hardcode secrets — always load from environment variables
- NEVER commit .env files — only .env.example with dummy values

### API Responses

- All numeric values must be numbers (float/int), never strings
- All responses must include `request_id` (UUID) for tracing
- All error responses must use the standard error format (see API-SPEC.md)
- All timestamps in responses must be ISO 8601 format

### File Handling

- Use Python's `tempfile` module for all temporary files
- Always wrap file operations in try/finally to guarantee cleanup
- Maximum upload size: 50 MB (configurable via env)
- Only accept .stl files (validate by extension AND magic bytes)

### PrusaSlicer

- Binary path loaded from `PRUSASLICER_PATH` env variable
- Always use argument lists, never shell=True
- Timeout: 120 seconds per slice operation
- Parse G-code comments for: filament_mm, filament_cm3, filament_g, print_time, first_layer_time
- **fill_density:** API accepts integer (e.g., `20`), internally converted to string with % (e.g., `"20%"`) before passing to PrusaSlicer CLI. The MVP accepted `"15%"` as a string — we are improving this for cleaner API design.
- **support_material:** API accepts boolean. MVP used 0/1 integer — we are improving to proper boolean.
- **STL path must be the LAST argument** in the command list

---

## DO NOT Use

These technologies are explicitly excluded from v1:

| Technology                    | Reason                                      |
| ----------------------------- | ------------------------------------------- |
| Redis                         | Not needed until 10+ concurrent users       |
| Celery / async workers        | Synchronous slicing is fine for v1 traffic  |
| Docker Compose multi-service  | Coolify manages services separately         |
| WebSockets                    | Polling via GET /jobs/{id} is sufficient    |
| OAuth / JWT                   | API key auth is simpler and correct for B2B |
| GraphQL                       | REST is appropriate for this use case       |
| Frontend / UI                 | This is API-only for v1                     |
| Nginx / Traefik manual config | Coolify handles this automatically          |

---

## Environment Variables

```
DATABASE_URL=postgresql://user:password@localhost:5432/slicer_api
API_ENV=development
SECRET_KEY=your-random-secret-key
MAX_FILE_SIZE_MB=50
PRUSASLICER_PATH=/usr/bin/prusa-slicer
DEFAULT_MACHINE_RATE_PER_HOUR=1.50
DEFAULT_MARKUP_MULTIPLIER=1.5
```

---

## Key File References

- **Existing MVP code:** `docs/ai/EXISTING-MVP.md` — READ THIS FIRST. Contains the working code patterns that must be preserved.
- Database schema: `docs/project/SCHEMA.md`
- API contract: `docs/project/API-SPEC.md`
- Architecture: `docs/project/ARCHITECTURE.md`
- Step-by-step prompts: `docs/ai/PROMPTS.md`
