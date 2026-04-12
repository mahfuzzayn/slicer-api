# Slicer API

A ready-to-deploy REST API that takes 3D model files (STL), slices them using PrusaSlicer, and returns an accurate cost estimate — covering material, machine time, and markup.

Built for B2B use: your customers send an STL file with print settings, and get back a detailed price quote in seconds.

---

## What Does It Do?

Imagine you run a 3D printing business. A customer uploads their 3D model and says:

> "How much would this cost to print in PLA, with 20% infill, at 0.2mm layer height?"

This API answers that question automatically:

1. **Receives** the 3D model file (STL format) and print settings
2. **Slices** it using PrusaSlicer (the same software used by real 3D printers)
3. **Calculates** exactly how much filament is needed (in grams)
4. **Estimates** how long the print will take
5. **Computes** the total cost: material + machine time + your profit markup
6. **Returns** a full price breakdown as JSON

**Example response:**

```json
{
  "quote": {
    "filament_g": 21.08,
    "estimated_print_time": "1h 48m 29s"
  },
  "pricing": {
    "material_cost": 0.42,
    "machine_cost": 2.71,
    "total_cost": 3.13,
    "customer_price": 4.70,
    "currency": "USD"
  }
}
```

---

## What It Uses

| What | Technology | Why |
|------|-----------|-----|
| Language | Python 3.11 | Fast to build, huge ecosystem |
| Web Framework | FastAPI | Modern, automatic docs, built-in validation |
| Database | PostgreSQL | Reliable, production-grade |
| ORM | SQLAlchemy 2.0 | Safe database queries, no raw SQL |
| Migrations | Alembic | Database schema versioning |
| Slicer | PrusaSlicer CLI | Industry-standard, accurate G-code output |
| Server | Uvicorn | High-performance Python web server |
| Deployment | Docker + Coolify | One-click deploys with HTTPS |

---

## How It Works (The Full Picture)

```
Customer                          Slicer API                        PrusaSlicer
────────                          ──────────                        ───────────
   │                                  │                                  │
   │  POST /slice                     │                                  │
   │  + STL file                      │                                  │
   │  + print settings                │                                  │
   │─────────────────────────────────>│                                  │
   │                                  │                                  │
   │                          1. Check API key                           │
   │                          2. Check rate limit                        │
   │                          3. Validate file                           │
   │                          4. Save to temp folder                     │
   │                                  │                                  │
   │                                  │  Run PrusaSlicer CLI             │
   │                                  │────────────────────────────────->│
   │                                  │                                  │
   │                                  │  G-code file with stats          │
   │                                  │<────────────────────────────────│
   │                                  │                                  │
   │                          5. Parse filament usage                    │
   │                          6. Calculate costs                         │
   │                          7. Save job to database                    │
   │                          8. Delete temp files                       │
   │                                  │                                  │
   │  JSON pricing response           │                                  │
   │<─────────────────────────────────│                                  │
```

### Security

- Every request needs an API key (like a password for the API)
- API keys are hashed before storage (like how websites store passwords)
- Each customer has a monthly request limit based on their plan
- File uploads are validated (only STL files, size limits enforced)
- No files are stored permanently — everything is cleaned up after processing

---

## API Endpoints

| Method | Path | Auth | What It Does |
|--------|------|------|-------------|
| `GET` | `/health` | No | Check if the API is running |
| `POST` | `/slice` | Yes | Upload STL + get price quote |
| `GET` | `/jobs` | Yes | List your past slice requests |
| `GET` | `/jobs/{id}` | Yes | Get details of a specific job |

Full API documentation is auto-generated at `http://localhost:8000/docs` when the server is running.

---

## How to Run Locally

### Prerequisites

You need these installed on your computer:

1. **Python 3.11 or newer** — [Download here](https://www.python.org/downloads/)
2. **PostgreSQL 15 or newer** — [Download here](https://www.postgresql.org/download/)
3. **PrusaSlicer** (optional for local testing) — [Download here](https://www.prusa3d.com/page/prusaslicer_424/)

### Step 1: Clone the Repository

```bash
git clone https://github.com/mahfuzzayn/slicer-api.git
cd slicer-api
```

### Step 2: Create a Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt. This means the virtual environment is active.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, and everything else the project needs.

### Step 4: Create the Environment File

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Now open `.env` in any text editor and update these values:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/slicer_api
API_ENV=development
SECRET_KEY=paste-a-random-string-here
MAX_FILE_SIZE_MB=50
PRUSASLICER_PATH=/usr/bin/prusa-slicer
DEFAULT_MACHINE_RATE_PER_HOUR=1.50
DEFAULT_MARKUP_MULTIPLIER=1.5
APP_VERSION=1.0.0
```

**Important notes:**
- Replace `YOUR_PASSWORD` with your PostgreSQL password
- Replace `5432` with your PostgreSQL port if it is different
- To generate a random secret key, run: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- On Windows, `PRUSASLICER_PATH` would be something like `C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe`

### Step 5: Create the Database

Open a terminal and connect to PostgreSQL:

```bash
psql -U postgres -h localhost -p 5432
```

Then run:

```sql
CREATE DATABASE slicer_api;
\q
```

Now apply the database tables:

```bash
alembic upgrade head
```

You should see:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 20260411_init, initial schema
```

### Step 6: Seed Initial Data

Run these three scripts to populate the database with plans, materials, and a test user:

```bash
python scripts/create_plan.py --seed
python scripts/seed_filaments.py
python scripts/create_user.py --name "Test User" --email "test@example.com" --plan starter
```

The last command will print an API key. **Save this key** — it is shown only once and cannot be retrieved later.

```
API KEY (shown ONCE — store it securely, it cannot be retrieved again):
  sk_Ot8LMA7Pm...
```

### Step 7: Start the Server

```bash
uvicorn app.main:app --reload
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

The API is now running.

---

## How to Test

### Quick Test: Health Check

Open your browser and go to: [http://localhost:8000/health](http://localhost:8000/health)

You should see:

```json
{"status": "ok", "version": "1.0.0", "timestamp": "..."}
```

### Quick Test: Interactive API Docs

Go to: [http://localhost:8000/docs](http://localhost:8000/docs)

This opens an interactive page where you can try every endpoint directly in your browser. Click on any endpoint, hit "Try it out", fill in the fields, and click "Execute".

For authenticated endpoints, click the "Authorize" button at the top and enter: `Bearer sk_YOUR_API_KEY_HERE`

### Test with curl (Terminal)

**Check if API is running:**
```bash
curl http://localhost:8000/health
```

**List jobs (with auth):**
```bash
curl -H "Authorization: Bearer sk_YOUR_API_KEY" http://localhost:8000/jobs
```

**Slice an STL file (requires PrusaSlicer installed):**
```bash
curl -X POST http://localhost:8000/slice \
  -H "Authorization: Bearer sk_YOUR_API_KEY" \
  -F "file=@your-model.stl" \
  -F "layer_height=0.2" \
  -F "fill_density=20" \
  -F "fill_pattern=grid" \
  -F "perimeters=3" \
  -F "support_material=false" \
  -F "filament_type=PLA"
```

### Run the Full Test Suite

```bash
set BASE_URL=http://localhost:8000
set TEST_API_KEY=sk_YOUR_API_KEY
python tests/test_api.py
```

On Mac/Linux use `export` instead of `set`.

Expected output:

```
[OK] health returns 200 ok
[OK] slice without auth returns 401
[OK] slice with invalid key returns 401
[OK] slice without file returns 422
[OK] slice with non-STL returns 400
[OK] slice with valid STL returns 200        <-- requires PrusaSlicer
[OK] list jobs returns 200
[OK] get job returns 200                     <-- requires a successful slice
[OK] get non-existent job returns 404
[OK] rate limit returns 429

Results: 10/10 passed
```

Note: Tests 6 and 8 require PrusaSlicer to be installed. All other tests work without it.

---

## Subscription Plans

The API has three built-in plans that control how many requests a customer can make per month:

| Plan | Price | Requests/Month | Max File Size |
|------|-------|---------------|--------------|
| Starter | $29/mo | 500 | 25 MB |
| Professional | $99/mo | 2,000 | 50 MB |
| Enterprise | $299/mo | 10,000 | 100 MB |

### Supported Filament Types

| Type | Cost/kg | Density |
|------|---------|---------|
| PLA | $20 | 1.24 g/cm3 |
| ABS | $22 | 1.04 g/cm3 |
| PETG | $25 | 1.27 g/cm3 |
| TPU | $35 | 1.21 g/cm3 |
| Nylon | $40 | 1.14 g/cm3 |
| ASA | $28 | 1.07 g/cm3 |
| PC | $45 | 1.20 g/cm3 |
| PVA | $50 | 1.23 g/cm3 |

---

## Project Structure

```
slicer-api/
├── app/
│   ├── main.py              # App entry point
│   ├── config.py            # Settings (from .env)
│   ├── dependencies.py      # Auth + database injection
│   ├── models/
│   │   ├── database.py      # Database connection
│   │   ├── tables.py        # Database table definitions
│   │   └── schemas.py       # Request/response formats
│   ├── routers/
│   │   ├── health.py        # GET /health
│   │   ├── slice.py         # POST /slice
│   │   └── jobs.py          # GET /jobs
│   ├── services/
│   │   ├── slicer.py        # Runs PrusaSlicer
│   │   ├── gcode_parser.py  # Reads slicer output
│   │   └── pricing.py       # Calculates costs
│   └── utils/
│       ├── security.py      # API key generation
│       └── errors.py        # Error handling
├── scripts/
│   ├── create_plan.py       # Create subscription plans
│   ├── create_user.py       # Create users + API keys
│   ├── seed_filaments.py    # Load filament data
│   └── start.sh             # Docker startup script
├── migrations/              # Database version history
├── tests/
│   └── test_api.py          # Integration tests
├── Dockerfile               # Container build instructions
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── .gitignore               # Files excluded from git
```

---

## Admin Commands

**Create a new customer:**
```bash
python scripts/create_user.py --name "Acme Corp" --email "api@acme.com" --plan professional
```

**Create a custom plan:**
```bash
python scripts/create_plan.py --name custom --monthly-price 149 --requests-per-month 5000 --max-file-size-mb 75
```

**Re-seed filament prices (updates existing, adds new):**
```bash
python scripts/seed_filaments.py
```

---

## Deployment

The project includes a Dockerfile that bundles Python, PrusaSlicer, and the API into a single container. Designed for deployment on Coolify (or any Docker host).

```bash
docker build -t slicer-api .
docker run -p 8000:8000 --env-file .env slicer-api
```

The container automatically runs database migrations on startup before serving requests.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `connection refused` on database | Make sure PostgreSQL is running. On Windows: `net start postgresql-x64-18` |
| `PrusaSlicer binary not found` | Install PrusaSlicer and update `PRUSASLICER_PATH` in your `.env` |
| `INVALID_API_KEY` on requests | Make sure you include `Authorization: Bearer sk_...` header |
| `alembic upgrade head` fails | Check that `DATABASE_URL` in `.env` is correct and the database exists |
| Port already in use | Another process is using port 8000. Stop it or use `--port 8001` |

---

Built by **Agrow Software Team**
