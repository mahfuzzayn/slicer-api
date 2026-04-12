# Testing Guide — Slicer API

A complete guide to testing, verifying, and debugging every part of the Slicer API. Follow this from top to bottom to confirm the entire system works, or jump to a specific section when troubleshooting.

---

## Table of Contents

1. [Before You Start](#before-you-start)
2. [Testing the Health Endpoint](#1-testing-the-health-endpoint)
3. [Testing Authentication](#2-testing-authentication)
4. [Testing File Validation](#3-testing-file-validation)
5. [Testing the Slice Endpoint](#4-testing-the-slice-endpoint)
6. [Testing the Jobs Endpoints](#5-testing-the-jobs-endpoints)
7. [Testing Rate Limiting](#6-testing-rate-limiting)
8. [Testing Without PrusaSlicer](#7-testing-without-prusaslicer)
9. [Verifying the Database](#8-verifying-the-database)
10. [Verifying Pricing Math](#9-verifying-pricing-math)
11. [Reading Server Logs](#10-reading-server-logs)
12. [Running the Automated Test Suite](#11-running-the-automated-test-suite)
13. [Using the Interactive API Docs](#12-using-the-interactive-api-docs)
14. [Common Problems and Fixes](#13-common-problems-and-fixes)

---

## Before You Start

Make sure you have completed the setup from README.md:

- [x] Virtual environment created and activated
- [x] Dependencies installed (`pip install -r requirements.txt`)
- [x] `.env` file created with your database credentials
- [x] Database created and migrations applied (`alembic upgrade head`)
- [x] Data seeded (plans, filaments, test user)
- [x] You have an API key saved (starts with `sk_`)

**Start the server before running any tests:**

```bash
uvicorn app.main:app --reload
```

The `--reload` flag automatically restarts the server when you change code. You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Keep this terminal open.** Open a second terminal for running tests.

---

## 1. Testing the Health Endpoint

The simplest test. No API key needed.

### In a browser

Open: [http://localhost:8000/health](http://localhost:8000/health)

### With curl

```bash
curl http://localhost:8000/health
```

### Expected response

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-04-12T16:01:49.001620"
}
```

### What to check

- `status` is `"ok"`
- `version` matches the `APP_VERSION` in your `.env`
- `timestamp` is a valid UTC time (should be close to your current time)

### If it fails

| Symptom | Cause | Fix |
|---------|-------|-----|
| Connection refused | Server is not running | Run `uvicorn app.main:app --reload` |
| Port already in use | Another app is on port 8000 | Use `--port 8001` or stop the other app |
| Module not found error | Virtual environment not activated | Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux) |

---

## 2. Testing Authentication

Every endpoint except `/health` requires an API key in the `Authorization` header.

### Test 1: No API key at all

```bash
curl http://localhost:8000/jobs
```

**Expected:** 401 error

```json
{
  "error": {
    "code": "MISSING_API_KEY",
    "message": "Missing Authorization header",
    "details": {}
  }
}
```

### Test 2: Wrong format (missing "Bearer")

```bash
curl -H "Authorization: sk_your_key_here" http://localhost:8000/jobs
```

**Expected:** 401 error

```json
{
  "error": {
    "code": "MISSING_API_KEY",
    "message": "Authorization header must be 'Bearer <api_key>'",
    "details": {}
  }
}
```

### Test 3: Invalid API key

```bash
curl -H "Authorization: Bearer sk_this_key_does_not_exist" http://localhost:8000/jobs
```

**Expected:** 401 error

```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is not valid or has been deactivated",
    "details": {}
  }
}
```

### Test 4: Valid API key

```bash
curl -H "Authorization: Bearer sk_YOUR_REAL_KEY" http://localhost:8000/jobs
```

**Expected:** 200 success with an empty jobs list

```json
{
  "jobs": [],
  "pagination": {"page": 1, "per_page": 20, "total": 0, "total_pages": 0}
}
```

### How to create additional test users

```bash
python scripts/create_user.py --name "Second User" --email "user2@test.com" --plan starter
```

This gives you a second API key to test user isolation (one user cannot see another user's jobs).

---

## 3. Testing File Validation

The API only accepts `.stl` files under the plan's size limit.

### Test 1: No file uploaded

```bash
curl -X POST http://localhost:8000/slice -H "Authorization: Bearer sk_YOUR_KEY"
```

**Expected:** 422 error (validation — file is required)

### Test 2: Wrong file type

```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@some_file.txt"
```

(On Mac/Linux use `\` instead of `^` for line continuation)

**Expected:** 400 error

```json
{
  "error": {
    "code": "INVALID_FILE",
    "message": "Only .stl files are accepted",
    "details": {}
  }
}
```

### Test 3: File too large

If your plan is "starter" (25 MB limit), try uploading a file larger than 25 MB:

**Expected:** 413 error

```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File size exceeds your plan's limit",
    "details": {
      "file_size_mb": 30.5,
      "max_allowed_mb": 25
    }
  }
}
```

### Test 4: Empty file with .stl extension

Create an empty file named `empty.stl` and upload it:

```bash
echo.> empty.stl
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@empty.stl"
```

**Expected:** 400 error — empty file rejected

---

## 4. Testing the Slice Endpoint

This is the core feature. **Requires PrusaSlicer installed** on the machine running the API.

### Basic slice request

```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@your-model.stl" ^
  -F "layer_height=0.2" ^
  -F "fill_density=20" ^
  -F "fill_pattern=grid" ^
  -F "perimeters=3" ^
  -F "support_material=false" ^
  -F "filament_type=PLA"
```

**Expected:** 200 with full pricing

```json
{
  "request_id": "f47ac10b-...",
  "job_id": "c3a42232-...",
  "status": "succeeded",
  "quote": {
    "filament_mm": 7068.3,
    "filament_cm3": 17.0,
    "filament_g": 21.08,
    "estimated_print_time": "1h 48m 29s",
    "estimated_print_time_hours": 1.8081,
    "first_layer_time": "56s"
  },
  "pricing": {
    "material_cost": 0.4216,
    "machine_cost": 2.712,
    "total_cost": 3.1336,
    "customer_price": 4.7004,
    "currency": "USD"
  },
  "details": {
    "filament_type": "PLA",
    "cost_per_kg": 20.0,
    "density_g_per_cm3": 1.24,
    "machine_rate_per_hour": 1.5,
    "markup_multiplier": 1.5
  },
  "parameters": {
    "layer_height": 0.2,
    "fill_density": 20,
    "fill_pattern": "grid",
    "perimeters": 3,
    "support_material": false,
    "filament_type": "PLA"
  }
}
```

### What to check in the response

- `request_id` and `job_id` are valid UUIDs
- `status` is `"succeeded"`
- All numbers in `quote` are actual numbers (not strings like `"7068.3"`)
- `pricing.customer_price` = `pricing.total_cost` x `details.markup_multiplier`
- `pricing.total_cost` = `pricing.material_cost` + `pricing.machine_cost`

### Check response headers

```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -v
```

The `-v` flag shows headers. Look for:

```
X-Request-ID: f47ac10b-...
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 499
X-RateLimit-Reset: 2026-05-01T00:00:00Z
```

### Test with different filament types

```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -F "filament_type=PETG"
```

Try each: `PLA`, `ABS`, `PETG`, `TPU`, `Nylon`, `ASA`, `PC`, `PVA`

Each should return different `cost_per_kg` and `density_g_per_cm3` values matching the filament table.

### Test with custom pricing overrides

```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -F "machine_rate_per_hour=3.00" ^
  -F "markup_multiplier=2.0"
```

The response `details` section should reflect your overrides, and the pricing math should use them.

### Test with different print settings

**High quality (slow, more material):**
```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -F "layer_height=0.1" ^
  -F "fill_density=80" ^
  -F "perimeters=5" ^
  -F "support_material=true"
```

**Draft quality (fast, less material):**
```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -F "layer_height=0.4" ^
  -F "fill_density=10" ^
  -F "perimeters=1"
```

The high-quality print should cost significantly more than the draft.

### Test invalid parameters

**Layer height out of range:**
```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -F "layer_height=5.0"
```

**Expected:** 422 — layer_height must be 0.05 to 0.6

**Fill density out of range:**
```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -F "fill_density=200"
```

**Expected:** 422 — fill_density must be 0 to 100

**Invalid fill pattern:**
```bash
curl -X POST http://localhost:8000/slice ^
  -H "Authorization: Bearer sk_YOUR_KEY" ^
  -F "file=@model.stl" ^
  -F "fill_pattern=invalid_pattern"
```

**Expected:** 422 — must be one of: grid, gyroid, honeycomb, rectilinear, triangles, cubic, line, concentric

---

## 5. Testing the Jobs Endpoints

### List all jobs

```bash
curl -H "Authorization: Bearer sk_YOUR_KEY" http://localhost:8000/jobs
```

**Expected:** A list of all your previous slice requests

```json
{
  "jobs": [
    {
      "job_id": "c3a42232-...",
      "status": "succeeded",
      "file_name": "model.stl",
      "filament_type": "PLA",
      "customer_price": 4.7004,
      "created_at": "2026-04-12T16:05:00Z",
      "completed_at": "2026-04-12T16:05:28Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

### Pagination

```bash
curl -H "Authorization: Bearer sk_YOUR_KEY" "http://localhost:8000/jobs?page=1&per_page=5"
```

### Filter by status

```bash
curl -H "Authorization: Bearer sk_YOUR_KEY" "http://localhost:8000/jobs?status=succeeded"
curl -H "Authorization: Bearer sk_YOUR_KEY" "http://localhost:8000/jobs?status=failed"
```

### Get a specific job

Copy a `job_id` from the list response, then:

```bash
curl -H "Authorization: Bearer sk_YOUR_KEY" http://localhost:8000/jobs/PASTE_JOB_ID_HERE
```

**Expected:** Full job details including parameters, quote, pricing, and details.

### Test user isolation

Create a second user:

```bash
python scripts/create_user.py --name "Other User" --email "other@test.com" --plan starter
```

Use that user's key to try accessing the first user's job:

```bash
curl -H "Authorization: Bearer sk_OTHER_USERS_KEY" http://localhost:8000/jobs/FIRST_USERS_JOB_ID
```

**Expected:** 404 — one user cannot see another user's jobs

```json
{
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "Job not found",
    "details": {}
  }
}
```

### Test with non-existent job ID

```bash
curl -H "Authorization: Bearer sk_YOUR_KEY" http://localhost:8000/jobs/00000000-0000-0000-0000-000000000000
```

**Expected:** 404

---

## 6. Testing Rate Limiting

Each plan has a monthly request limit (starter = 500). The API counts jobs created this month.

### Check your current usage

Look at the response headers after a `/slice` request:

```
X-RateLimit-Limit: 500         <-- your plan's monthly limit
X-RateLimit-Remaining: 498     <-- requests left this month
X-RateLimit-Reset: 2026-05-01T00:00:00Z  <-- when the counter resets
```

### Test the rate limit

To test without making 500 real requests, temporarily create a plan with a very low limit:

```bash
python scripts/create_plan.py --name testplan --monthly-price 0 --requests-per-month 2 --max-file-size-mb 50
python scripts/create_user.py --name "Rate Test" --email "rate@test.com" --plan testplan
```

Now use that user's key to make 3 slice requests. The third one should fail:

**Expected on the 3rd request:** 429 error

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "You have exceeded your monthly request quota",
    "details": {
      "limit": 2,
      "used": 2,
      "resets_at": "2026-05-01T00:00:00Z"
    }
  }
}
```

---

## 7. Testing Without PrusaSlicer

If PrusaSlicer is not installed on your machine, the `/slice` endpoint will return:

```json
{
  "error": {
    "code": "SLICER_ERROR",
    "message": "PrusaSlicer binary not found at /usr/bin/prusa-slicer",
    "details": {}
  }
}
```

**This is expected.** Everything else still works:

| What You Can Test | Works Without PrusaSlicer? |
|-------------------|--------------------------|
| `GET /health` | Yes |
| Authentication (valid/invalid keys) | Yes |
| File validation (wrong type, too large) | Yes |
| `GET /jobs` (list and detail) | Yes |
| Rate limiting (counter increments) | Yes |
| Parameter validation (bad values) | Yes |
| `POST /slice` full success | **No** — needs PrusaSlicer |

The Docker image includes PrusaSlicer, so the full flow works in production.

### Installing PrusaSlicer locally (optional)

1. Download from: https://www.prusa3d.com/page/prusaslicer_424/
2. Install it
3. Find the executable path:
   - **Windows:** Usually `C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe`
   - **Mac:** `/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer`
   - **Linux:** `/usr/bin/prusa-slicer` or `/usr/local/bin/prusa-slicer`
4. Update `PRUSASLICER_PATH` in your `.env` file
5. Restart the server

---

## 8. Verifying the Database

You can inspect the database directly to verify data was stored correctly.

### Connect to the database

```bash
psql -U postgres -h localhost -p YOUR_PORT -d slicer_api
```

### View all tables

```sql
\dt
```

### Check plans

```sql
SELECT name, monthly_price, requests_per_month, max_file_size_mb FROM plans;
```

**Expected:**

```
    name     | monthly_price | requests_per_month | max_file_size_mb
-------------+---------------+--------------------+------------------
 starter     |         29.00 |                500 |               25
 professional|         99.00 |               2000 |               50
 enterprise  |        299.00 |              10000 |              100
```

### Check filaments

```sql
SELECT type, cost_per_kg, density_g_per_cm3 FROM filaments ORDER BY type;
```

### Check users and their plans

```sql
SELECT u.name, u.email, p.name AS plan FROM users u JOIN plans p ON u.plan_id = p.id;
```

### Check API keys (only hashes and prefixes — raw keys are never stored)

```sql
SELECT key_prefix, label, is_active, last_used_at FROM api_keys;
```

The `last_used_at` column updates every time someone authenticates with that key. Use this to verify auth is working.

### Check jobs

```sql
SELECT id, status, file_name, processing_time_ms, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;
```

### Check a job's full result

```sql
SELECT result_json FROM jobs WHERE id = 'PASTE_JOB_UUID_HERE';
```

This shows the complete pricing breakdown stored for that job.

### Count jobs this month (rate limit check)

```sql
SELECT COUNT(*) FROM jobs
WHERE user_id = 'PASTE_USER_UUID'
AND created_at >= date_trunc('month', NOW());
```

---

## 9. Verifying Pricing Math

The pricing formula is:

```
material_cost  = (filament_grams / 1000) x cost_per_kg
machine_cost   = print_time_hours x machine_rate_per_hour
total_cost     = material_cost + machine_cost
customer_price = total_cost x markup_multiplier
```

### Worked example

Given:
- Filament used: 21.08 grams
- Filament type: PLA ($20.00/kg)
- Print time: 1h 48m 29s = 1.8081 hours
- Machine rate: $1.50/hour (default)
- Markup: 1.5x (default)

Calculate:

```
material_cost  = (21.08 / 1000) x 20.00     = 0.4216
machine_cost   = 1.8081 x 1.50               = 2.7122
total_cost     = 0.4216 + 2.7122             = 3.1338
customer_price = 3.1338 x 1.5                = 4.7007
```

Compare these numbers against what the API returned. They should match (with minor rounding differences at the 4th decimal place).

### Filament gram fallback

If PrusaSlicer does not output `filament_g` (rare but possible), the API falls back to:

```
filament_g = filament_cm3 x density_g_per_cm3
```

For PLA: `filament_g = 17.0 x 1.24 = 21.08`

You can verify this by checking if `quote.filament_g` in the response matches `quote.filament_cm3 x details.density_g_per_cm3`.

---

## 10. Reading Server Logs

The terminal running `uvicorn` shows every request in real time.

### Normal request log

```
INFO:     127.0.0.1:52341 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52342 - "POST /slice HTTP/1.1" 200 OK
INFO:     127.0.0.1:52343 - "GET /jobs HTTP/1.1" 200 OK
```

### What the status codes mean

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Everything worked |
| 400 | Bad request | Client sent invalid data (wrong file type, bad parameters) |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not found | Job ID doesn't exist or belongs to another user |
| 413 | File too large | File exceeds plan limit |
| 422 | Validation error | Parameters failed Pydantic validation |
| 429 | Rate limited | Monthly quota exceeded |
| 500 | Server error | Something broke — check the full error in the terminal |

### Seeing full error details

If you get a 500 error, the terminal running uvicorn will show the full Python traceback. Read it from bottom to top — the last line usually tells you what went wrong.

---

## 11. Running the Automated Test Suite

The project includes a test script that checks 10 scenarios automatically.

### Setup

**Windows:**
```bash
set BASE_URL=http://localhost:8000
set TEST_API_KEY=sk_YOUR_KEY_HERE
python tests/test_api.py
```

**Mac / Linux:**
```bash
export BASE_URL=http://localhost:8000
export TEST_API_KEY=sk_YOUR_KEY_HERE
python tests/test_api.py
```

### Expected output (without PrusaSlicer)

```
Running tests against http://localhost:8000
TEST_API_KEY set: True

[OK] health returns 200 ok
[OK] slice without auth returns 401
[OK] slice with invalid key returns 401
[OK] slice without file returns 422
[OK] slice with non-STL returns 400
[FAIL] slice with valid STL returns 200       <-- needs PrusaSlicer
[OK] list jobs returns 200
[FAIL] get job returns 200                    <-- no job was created
[OK] get non-existent job returns 404
[OK] rate limit returns 429

Results: 8/10 passed
```

8/10 is the expected result without PrusaSlicer. The 2 failures are normal.

### Expected output (with PrusaSlicer)

All 10 should show `[OK]`.

---

## 12. Using the Interactive API Docs

FastAPI auto-generates interactive documentation.

### Open the docs

Go to: [http://localhost:8000/docs](http://localhost:8000/docs)

### Authorize

1. Click the green **Authorize** button at the top right
2. In the "Value" field, type: `Bearer sk_YOUR_KEY_HERE`
3. Click **Authorize**, then **Close**

Now all your requests from the docs page will include your API key.

### Try an endpoint

1. Click on any endpoint to expand it
2. Click **Try it out**
3. Fill in the parameters or upload a file
4. Click **Execute**
5. The response appears below with status code, headers, and body

### Alternative docs format

There is also a simpler docs page at: [http://localhost:8000/redoc](http://localhost:8000/redoc)

This is read-only (no "try it out") but easier to read for understanding the API structure.

---

## 13. Common Problems and Fixes

### "Connection refused" when calling the API

**Cause:** Server is not running.

**Fix:** Open a terminal, navigate to the project folder, activate the venv, and run:
```bash
uvicorn app.main:app --reload
```

### "Module not found" errors

**Cause:** Virtual environment is not activated.

**Fix:**
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

You should see `(venv)` in your terminal prompt.

### "Could not connect to database"

**Cause:** PostgreSQL is not running or the connection details are wrong.

**Fix:**
1. Check PostgreSQL is running:
   - Windows: `net start | findstr postgres`
   - Mac: `brew services list | grep postgres`
   - Linux: `systemctl status postgresql`
2. Check your `.env` file — verify `DATABASE_URL` has the correct username, password, host, and port

### "relation does not exist" errors

**Cause:** Migrations have not been applied.

**Fix:**
```bash
alembic upgrade head
```

### "PrusaSlicer binary not found"

**Cause:** PrusaSlicer is not installed or `PRUSASLICER_PATH` in `.env` points to the wrong location.

**Fix:** Install PrusaSlicer and update the path in `.env`. See [Testing Without PrusaSlicer](#7-testing-without-prusaslicer) for details.

### "Slicing timed out after 120 seconds"

**Cause:** The STL file is very large or complex and PrusaSlicer took too long.

**Fix:** Try a smaller/simpler STL file. The 120-second timeout is a safety limit.

### Jobs list shows "failed" status

**Cause:** The slice request started but PrusaSlicer encountered an error.

**Fix:** Check the job details for the error message:
```bash
curl -H "Authorization: Bearer sk_YOUR_KEY" http://localhost:8000/jobs/JOB_ID
```

The `error_message` field will explain what went wrong.

### API key not working after restart

**Cause:** The API key is stored as a hash in the database. It survives restarts. If it stopped working, the key might have been deactivated.

**Fix:** Check in the database:
```sql
SELECT key_prefix, is_active, expires_at FROM api_keys;
```

If `is_active` is `false`, the key was deactivated. Create a new user/key.

---

Built by **Agrow Software Team**
