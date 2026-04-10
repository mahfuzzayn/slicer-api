# PROMPTS.md — Step-by-Step Claude Code Execution Plan

## How to Use This File

Execute each prompt one at a time in Claude Code. Wait for completion and verify the checkpoint before moving to the next prompt. Do NOT skip ahead. If something breaks, fix it before continuing.

After each prompt, update CHANGELOG.md with what was done.

---

## Phase 1: Project Foundation (Prompts 1–3)

### Prompt 1 — Project Scaffold

```
Read CLAUDE.md for project rules.

IMPORTANT CONTEXT: We are restructuring an existing working MVP (a single app.py file) into a
clean project layout. The existing code is in docs/ai/EXISTING-MVP.md — READ IT FIRST.
Preserve the working PrusaSlicer subprocess pattern, G-code parsing logic, and validation
approach from the MVP. Do not reinvent what already works.

Create the slicer-api project structure as defined in CLAUDE.md.

Create these files:
- requirements.txt with all dependencies listed in CLAUDE.md
- .env.example with all environment variables from CLAUDE.md
- .gitignore (Python standard: __pycache__, .env, *.pyc, venv/, .vscode/, uploads/, *.gcode, *.stl, out/)
- app/__init__.py (empty)
- app/main.py — FastAPI app with lifespan, CORS middleware allowing all origins, and include routers for health, slice, and jobs
- app/config.py — Pydantic BaseSettings class loading all env vars from .env with defaults

Do not create any endpoints yet. Just the app shell that starts.
```

**Checkpoint:** `uvicorn app.main:app --reload` starts without errors (will show "no route" warnings, that's fine).

---

### Prompt 2 — Database Setup

```
Read docs/project/SCHEMA.md for the complete database design.

Create:
- app/models/database.py — SQLAlchemy async engine, sessionmaker, Base class. Use DATABASE_URL from config.
- app/models/tables.py — All 5 table models (users, api_keys, jobs, plans, filaments) exactly matching SCHEMA.md. Use UUID primary keys, UTC timestamps, proper foreign keys with ondelete settings.
- app/models/__init__.py — Export all models

Set up Alembic:
- Run alembic init migrations
- Configure alembic.ini and migrations/env.py to use DATABASE_URL from config and import all models
- Generate initial migration: alembic revision --autogenerate -m "initial schema"

Do NOT use async SQLAlchemy. Use standard synchronous SQLAlchemy for simplicity. The app volume doesn't need async DB.
```

**Checkpoint:** `alembic upgrade head` runs without errors. Tables visible in PostgreSQL with `\dt` command.

---

### Prompt 3 — Pydantic Schemas

```
Read docs/project/API-SPEC.md for exact request/response formats.

Create app/models/schemas.py with Pydantic models for:

Request models:
- SliceRequest: layer_height (float, 0.05-0.6), fill_density (int, 0-100), fill_pattern (enum), perimeters (int, 1-10), support_material (bool), filament_type (enum), machine_rate_per_hour (optional float), markup_multiplier (optional float)

Response models:
- HealthResponse: status, version, timestamp
- SliceResponse: request_id, job_id, quote object, pricing object, parameters object
- JobResponse: job_id, status, created_at, completed_at, parameters, result
- JobListResponse: jobs list, pagination (page, per_page, total)
- ErrorResponse: error object with code, message, details

Use Field() with descriptions and examples on every field.
All enums should be string enums (StrEnum or Literal types).

Allowed fill_patterns: grid, gyroid, honeycomb, rectilinear, triangles, cubic, line, concentric
Allowed filament_types: PLA, ABS, PETG, TPU, Nylon, ASA, PC, PVA
```

**Checkpoint:** Import schemas in Python shell without errors. Validate a sample SliceRequest with edge-case values.

---

## Phase 2: Core Services (Prompts 4–6)

### Prompt 4 — Security + Auth

```
Read CLAUDE.md security rules.

Create app/utils/security.py:
- generate_api_key() — Returns tuple of (raw_key, key_hash, key_prefix). Raw key is 32 random bytes, URL-safe base64 encoded, prefixed with "sk_". Hash is SHA-256 of the raw key. Prefix is first 8 chars after "sk_".
- hash_api_key(raw_key) — Returns SHA-256 hash of the given key.

Create app/dependencies.py:
- get_db() — Yields a database session (dependency)
- get_current_user(request, db) — Extracts Bearer token from Authorization header. Hashes it. Looks up in api_keys table (must be is_active=True, not expired). Joins to users table (must be is_active=True). Returns the user object. Raises 401 HTTPException with ErrorResponse format if anything fails.

Create app/utils/errors.py:
- Custom exception classes: AuthenticationError, AuthorizationError, ValidationError, NotFoundError, RateLimitError, SlicerError
- Exception handlers that return consistent ErrorResponse JSON with proper HTTP codes
- Register all exception handlers in main.py

Wire auth dependency into main.py but don't protect routes yet (we'll do that when creating routers).
```

**Checkpoint:** Import security module. Generate a key. Hash it. Verify hash matches. Import dependencies without errors.

---

### Prompt 5 — PrusaSlicer Service + G-code Parser

```
Read CLAUDE.md for PrusaSlicer rules.
Read docs/ai/EXISTING-MVP.md for the working implementation reference.

Create app/services/slicer.py:
- slice_file(stl_path, params) function that:
  1. Creates a temp directory for output using Python's tempfile module
  2. Builds PrusaSlicer command as argument list (NEVER shell=True)
  3. Maps params to CLI flags:
     --layer-height, --fill-density (convert integer to string with % like "15%"), --fill-pattern, --perimeters, --support-material (boolean flag: include only if True), --output
  4. Runs subprocess with 120-second timeout
  5. Returns path to generated .gcode file
  6. On timeout: raises SlicerError with "Slicing timed out after 120 seconds"
  7. On non-zero exit: raises SlicerError with stderr output (truncate to last 2000 chars like the MVP does)

  IMPORTANT — Preserve these patterns from the existing MVP:
  - --support-material is a boolean flag. When support is enabled, pass just "--support-material" with no value. When disabled, omit it entirely. This was a bug that was already fixed in the MVP.
  - The STL file path must be the LAST argument in the command list.
  - Use PRUSASLICER_PATH from config instead of hardcoded "prusa-slicer".

Create app/services/gcode_parser.py:
- parse_gcode(gcode_path) function that:
  1. Reads the gcode file
  2. Uses the EXACT regex patterns from the existing MVP:
     - "^; filament used \[mm\] = (.+)$"
     - "^; filament used \[cm3\] = (.+)$"
     - "^; filament used \[g\] = (.+)$"
     - "^; total filament cost = (.+)$"
     - "^; estimated printing time \(normal mode\) = (.+)$"
     - "^; estimated first layer printing time \(normal mode\) = (.+)$"
  3. Returns a dict with all parsed values as floats (not strings like the MVP), None for any not found
  4. Time parsing must handle formats: "1h 48m 29s", "48m 29s", "29s", "1d 2h 30m"

  These regex patterns are TESTED AND WORKING against real PrusaSlicer output. Do not modify them.

  Optimization: Parse from the END of the file (last 200 lines) since PrusaSlicer puts stats at the bottom.
```

**Checkpoint:** If PrusaSlicer is installed locally, test with a real STL file. If not, verify the code logic by reading it. Parser should handle all time formats correctly.

---

### Prompt 6 — Pricing Engine

```
Read docs/project/API-SPEC.md for the pricing response format.

Create app/services/pricing.py:
- calculate_cost(parsed_gcode, filament_record, machine_rate, markup) function that:

  1. Determine filament grams:
     - Use parsed_gcode["filament_g"] if available
     - Fallback: parsed_gcode["filament_cm3"] * filament_record.density_g_per_cm3
     - Fallback: raise SlicerError("Could not determine filament usage")

  2. Calculate:
     - material_cost = (filament_grams / 1000) * filament_record.cost_per_kg
     - machine_cost = print_time_hours * machine_rate
     - total_cost = material_cost + machine_cost
     - customer_price = total_cost * markup

  3. Return a dict matching the pricing response in API-SPEC.md:
     - All values rounded to 4 decimal places
     - Include full breakdown: material_cost, machine_cost, total_cost, customer_price
     - Include details: filament_grams, filament_type, print_time_hours, cost_per_kg, machine_rate, markup, currency

  4. Parse print time string to hours (float). "1h 48m 29s" → 1.8081 hours

  machine_rate defaults to DEFAULT_MACHINE_RATE_PER_HOUR from config.
  markup defaults to DEFAULT_MARKUP_MULTIPLIER from config.
  Both can be overridden by the customer in the request.
```

**Checkpoint:** Unit test the calculation with known values. 98.2g PLA at $25/kg + 2.4h at $1.50/hr + 1.5x markup should produce a clear, correct breakdown.

---

## Phase 3: API Endpoints (Prompts 7–9)

### Prompt 7 — Health + Slice Endpoints

```
Read docs/project/API-SPEC.md for exact endpoint specs.

Create app/routers/health.py:
- GET /health — Returns HealthResponse. No auth required. Include app version from config.

Create app/routers/slice.py:
- POST /slice — Protected by get_current_user dependency.
  Flow:
  1. Validate uploaded file (check extension is .stl, check size <= MAX_FILE_SIZE_MB)
  2. Check rate limit: count user's jobs this month from DB, compare to plan.requests_per_month. If exceeded, raise RateLimitError.
  3. Create job record in DB with status="running"
  4. Save uploaded file to temp location
  5. Call slicer.slice_file()
  6. Call gcode_parser.parse_gcode()
  7. Look up filament from DB by filament_type
  8. Call pricing.calculate_cost()
  9. Update job record: status="succeeded", result_json=pricing result
  10. Clean up temp files (in finally block)
  11. Return SliceResponse

  On any error:
  - Update job record: status="failed", error_message=str(error)
  - Clean up temp files
  - Raise appropriate HTTP error

  Include request_id (UUID) in response and X-Request-ID header.
  Include rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

Register routers in main.py with appropriate prefixes.
```

**Checkpoint:** POST /slice with valid auth + STL file returns full pricing response. POST without auth returns 401. POST with invalid file returns 400.

---

### Prompt 8 — Jobs Endpoints

```
Read docs/project/API-SPEC.md for jobs endpoint specs.

Create app/routers/jobs.py:
- GET /jobs — Protected by get_current_user.
  - Returns paginated list of the authenticated user's jobs
  - Query params: page (default 1), per_page (default 20, max 100), status (optional filter)
  - Order by created_at descending (newest first)
  - Returns JobListResponse with pagination metadata

- GET /jobs/{job_id} — Protected by get_current_user.
  - Returns single job by UUID
  - Must belong to authenticated user (don't return other users' jobs)
  - Returns JobResponse
  - If job not found or belongs to another user: 404

Register router in main.py.
```

**Checkpoint:** Create a job via POST /slice, then retrieve it via GET /jobs/{id}. List jobs via GET /jobs. Verify pagination works. Verify user isolation (can't see other users' jobs).

---

### Prompt 9 — Admin CLI Scripts

```
Create scripts/create_plan.py:
- CLI script that creates subscription plans in the database
- Takes arguments: --name, --monthly-price, --requests-per-month, --max-file-size-mb
- Creates a default set of plans if run with --seed flag:
  - Starter: $29/month, 500 requests, 25MB max file
  - Professional: $99/month, 2000 requests, 50MB max file
  - Enterprise: $299/month, 10000 requests, 100MB max file
- Prints confirmation with plan details

Create scripts/create_user.py:
- Takes arguments: --name, --email, --plan (plan name, default "starter")
- Creates user record
- Generates API key
- Assigns plan
- Prints the raw API key ONE TIME with a warning that it won't be shown again

Create scripts/seed_filaments.py:
- Seeds the filaments table with common materials:
  - PLA: density 1.24 g/cm3, $20/kg
  - ABS: density 1.04 g/cm3, $22/kg
  - PETG: density 1.27 g/cm3, $25/kg
  - TPU: density 1.21 g/cm3, $35/kg
  - Nylon: density 1.14 g/cm3, $40/kg
  - ASA: density 1.07 g/cm3, $28/kg
  - PC: density 1.20 g/cm3, $45/kg
  - PVA: density 1.23 g/cm3, $50/kg
- Uses upsert logic (update if exists, insert if not)

All scripts must:
- Load .env for DATABASE_URL
- Create their own DB session
- Handle errors gracefully with clear messages
- Be runnable as: python scripts/create_user.py --name "Acme" --email "acme@co.com"
```

**Checkpoint:** Run seed scripts. Verify data in database. Create a user and test their API key against /slice.

---

## Phase 4: Deployment (Prompts 10–11)

### Prompt 10 — Dockerfile

```
Create a Dockerfile for the slicer-api that:

1. Uses python:3.11-slim as base image
2. Installs system dependencies: PrusaSlicer (or downloads AppImage if apt package unavailable), and any required libs
3. Sets working directory to /app
4. Copies requirements.txt and installs Python dependencies
5. Copies the entire project
6. Exposes port 8000
7. CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000

Important notes:
- PrusaSlicer installation in Docker can be tricky. Try apt-get install prusa-slicer first. If not available in the base image repos, download the Linux AppImage from GitHub releases, extract it, and put it in /usr/local/bin.
- Make sure xvfb or similar is NOT needed (CLI mode doesn't need display)
- The PRUSASLICER_PATH env var should point to wherever PrusaSlicer ends up
- Keep the image as small as possible but functional

Also create .dockerignore:
- .git, .env, __pycache__, *.pyc, venv/, .vscode/, node_modules/, docs/
```

**Checkpoint:** `docker build -t slicer-api .` succeeds. `docker run -p 8000:8000 slicer-api` starts the app (will fail on DB connection if no PostgreSQL, but the container should start).

---

### Prompt 11 — Startup + Migration Script

```
Create a startup script that Coolify can use as the container entrypoint.

Create scripts/start.sh:
#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting slicer-api..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

Update the Dockerfile CMD to use this script instead of calling uvicorn directly.
Make sure the script is executable (chmod +x).

This ensures migrations run automatically on every deployment — no manual steps needed.
```

**Checkpoint:** Docker container starts, runs migrations, and serves the API.

---

## Phase 5: Final Verification (Prompt 12)

### Prompt 12 — Integration Test Suite

```
Create tests/test_api.py with integration tests using Python's requests library (not pytest fixtures — keep it simple and runnable standalone).

Test cases:
1. GET /health returns 200 with status "ok"
2. POST /slice without auth returns 401
3. POST /slice with invalid key returns 401
4. POST /slice with valid key but no file returns 422
5. POST /slice with valid key + non-STL file returns 400
6. POST /slice with valid key + valid STL returns 200 with complete pricing
7. GET /jobs returns list of user's jobs
8. GET /jobs/{id} returns specific job
9. GET /jobs/{id} with wrong user returns 404
10. POST /slice beyond rate limit returns 429

Make the test file configurable:
- BASE_URL from env (default http://localhost:8000)
- TEST_API_KEY from env
- TEST_STL_PATH from env

Include a small valid binary STL file embedded as bytes in the test (a simple cube) so tests can run without external files.

The tests should be runnable as: python tests/test_api.py
```

**Checkpoint:** All 10 tests pass against local server. Same tests pass against production URL after deployment.

---

## Execution Notes

1. **One prompt at a time.** Do not combine prompts.
2. **Verify each checkpoint** before moving to the next prompt.
3. **If something breaks,** fix it with Claude Code before continuing. Add the fix to CHANGELOG.md.
4. **If Claude Code suggests changes to the spec,** evaluate them. If they make sense, update the relevant doc (API-SPEC.md, SCHEMA.md, etc.) and then proceed.
5. **Total estimated time:** 4-8 hours for all 12 prompts with Claude Code, depending on PrusaSlicer installation complexity.