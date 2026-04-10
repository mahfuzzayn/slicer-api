# ARCHITECTURE.md — System Design

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                      COOLIFY (VPS)                       │
│                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ Traefik   │───▶│  slicer-api  │───▶│ PostgreSQL   │   │
│  │ (auto)    │    │  (container) │    │ (container)  │   │
│  │           │    │              │    │              │   │
│  │ HTTPS ✓   │    │ FastAPI      │    │ Users        │   │
│  │ Domain ✓  │    │ PrusaSlicer  │    │ API Keys     │   │
│  │ Certs ✓   │    │ Python 3.11  │    │ Jobs         │   │
│  └──────────┘    └──────────────┘    │ Plans        │   │
│                                       │ Filaments    │   │
│       Managed by Coolify              └──────────────┘   │
│       automatically                                      │
└─────────────────────────────────────────────────────────┘
```

Coolify handles: domain routing, HTTPS certificates, container builds, deployments, logs, and environment variables. You manage: your code, database schema, and business logic.

---

## Request Flow: POST /slice

This is the most important flow. Every line of your codebase exists to serve this pipeline.

```
Step 1: Customer sends request
────────────────────────────────
POST https://api.yourdomain.com/slice
Authorization: Bearer sk_a1b2c3d4...
Content-Type: multipart/form-data

[STL file + parameters]


Step 2: Traefik (Coolify's reverse proxy)
────────────────────────────────
- Terminates HTTPS
- Forwards to FastAPI container on port 8000


Step 3: FastAPI receives request
────────────────────────────────
app/main.py → app/routers/slice.py

3a. Auth check (app/dependencies.py)
    │
    ├── Extract "Bearer sk_a1b2c3d4..." from header
    ├── Hash the key with SHA-256
    ├── Query api_keys table for matching hash
    ├── Check: is_active=True, not expired
    ├── Join to users table, check: is_active=True
    │
    ├── FAIL → 401 {"error": {"code": "INVALID_API_KEY"}}
    └── PASS → Continue with user context

3b. Rate limit check (app/routers/slice.py)
    │
    ├── Count user's jobs this month from jobs table
    ├── Compare to user's plan.requests_per_month
    │
    ├── EXCEEDED → 429 {"error": {"code": "RATE_LIMIT_EXCEEDED"}}
    └── WITHIN LIMIT → Continue

3c. File validation (app/routers/slice.py)
    │
    ├── Check file extension is .stl
    ├── Check file size <= plan.max_file_size_mb
    │
    ├── INVALID → 400 {"error": {"code": "INVALID_FILE"}}
    └── VALID → Continue

3d. Parameter validation (app/models/schemas.py)
    │
    ├── Pydantic validates all parameters against SliceRequest model
    ├── layer_height: 0.05-0.6, fill_density: 0-100, etc.
    │
    ├── INVALID → 422 {"error": {"code": "VALIDATION_ERROR"}}
    └── VALID → Continue


Step 4: Create job record
────────────────────────────────
app/routers/slice.py

- INSERT into jobs table: status="running", user_id, params
- Generate job_id (UUID)


Step 5: Slice the STL file
────────────────────────────────
app/services/slicer.py

- Save uploaded file to temp directory
- Build PrusaSlicer command:
  prusa-slicer --export-gcode \
    --layer-height 0.2 \
    --fill-density 15% \
    --fill-pattern gyroid \
    --perimeters 3 \
    --output /tmp/xxx/output.gcode \
    /tmp/xxx/input.stl

- Execute with subprocess (timeout=120s)
- Returns path to .gcode file

  TIMEOUT → SlicerError → 500
  CRASH → SlicerError → 500


Step 6: Parse G-code output
────────────────────────────────
app/services/gcode_parser.py

- Read last 200 lines of .gcode file
- Extract via regex:
  ; filament used [mm] = 7068.30    → filament_mm
  ; filament used [cm3] = 17.00     → filament_cm3
  ; filament used [g] = 21.08       → filament_g (may be null)
  ; estimated printing time = 1h 48m → print_time
  ; first layer estimated printing time = 56s → first_layer_time


Step 7: Calculate cost
────────────────────────────────
app/services/pricing.py

- Look up filament from filaments table (e.g., PLA)
- Determine grams: filament_g or (filament_cm3 * density)

  material_cost  = (21.08g / 1000) × $20/kg     = $0.4216
  machine_cost   = 1.808 hours × $1.50/hr        = $2.7120
  total_cost     = $0.4216 + $2.7120              = $3.1336
  customer_price = $3.1336 × 1.5 markup           = $4.7004


Step 8: Update job + respond
────────────────────────────────
app/routers/slice.py

- UPDATE jobs: status="succeeded", result_json={pricing data}
- DELETE temp files (stl + gcode)
- Return JSON response with full breakdown


Step 9: Customer receives response
────────────────────────────────
{
  "request_id": "uuid",
  "job_id": "uuid",
  "quote": { ... },
  "pricing": { ... }
}
```

---

## Data Flow Between Tables

```
plans (1) ────────── (many) users
                              │
users (1) ────────── (many) api_keys
                              │
users (1) ────────── (many) jobs

filaments ── referenced by ── pricing engine (not FK, lookup by type)
```

**Key relationships:**

- A plan has many users. A user belongs to one plan.
- A user has many API keys (can rotate keys). A key belongs to one user.
- A user has many jobs. A job belongs to one user.
- Filaments are a reference table queried during pricing, not directly linked to jobs.

---

## Security Architecture

```
┌─────────────────────────────────────────────┐
│              Security Layers                 │
│                                              │
│  Layer 1: HTTPS (Traefik/Coolify)           │
│  ├── All traffic encrypted                   │
│  └── Certificates auto-renewed               │
│                                              │
│  Layer 2: API Key Auth (dependencies.py)     │
│  ├── Keys hashed with SHA-256               │
│  ├── Raw keys never stored                   │
│  ├── Keys have expiry dates                  │
│  └── Keys can be deactivated                 │
│                                              │
│  Layer 3: Rate Limiting (routers/slice.py)   │
│  ├── Per-user monthly quotas                 │
│  └── Per-plan file size limits               │
│                                              │
│  Layer 4: Input Validation                   │
│  ├── File type verification                  │
│  ├── File size limits                        │
│  ├── Parameter range enforcement             │
│  └── Pydantic schema validation              │
│                                              │
│  Layer 5: Process Isolation (slicer.py)      │
│  ├── Subprocess with timeout                 │
│  ├── No shell=True                           │
│  ├── Temp file cleanup in finally block      │
│  └── PrusaSlicer runs with limited scope     │
│                                              │
│  Layer 6: Database Security                  │
│  ├── PostgreSQL on internal network only     │
│  ├── No raw SQL (SQLAlchemy ORM only)        │
│  └── User isolation on all queries           │
└─────────────────────────────────────────────┘
```

---

## File Lifecycle

```
Upload                    Processing                  Cleanup
──────                    ──────────                  ───────
STL arrives ──▶ Save to /tmp/job_uuid/ ──▶ PrusaSlicer reads it
                                           │
                                           ▼
                                    G-code written to /tmp/job_uuid/
                                           │
                                           ▼
                                    Parser reads G-code
                                           │
                                           ▼
                                    Cost calculated
                                           │
                                           ▼
                               DELETE entire /tmp/job_uuid/
                               (in finally block — always runs)
```

No files are stored permanently in v1. All data lives in the database as JSON.
