# ENV-SETUP.md — Local Development Setup

Step-by-step guide to get slicer-api running on your local machine.

---

## Prerequisites

You need these installed before starting:

### 1. Python 3.11+

**Check if installed:**

```bash
python3 --version
```

**Install (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**Install (macOS):**

```bash
brew install python@3.11
```

**Install (Windows):**
Download from https://python.org/downloads — check "Add to PATH" during install.

---

### 2. PostgreSQL

**Check if installed:**

```bash
psql --version
```

**Install (Ubuntu/Debian):**

```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Install (macOS):**

```bash
brew install postgresql@15
brew services start postgresql@15
```

**Install (Windows):**
Download from https://www.postgresql.org/download/windows/ — use the installer.

**Create the database:**

```bash
# Switch to postgres user (Linux)
sudo -u postgres psql

# Or just run psql (macOS/Windows)
psql -U postgres
```

Then run these SQL commands:

```sql
CREATE USER slicer_user WITH PASSWORD 'slicer_dev_password';
CREATE DATABASE slicer_api OWNER slicer_user;
GRANT ALL PRIVILEGES ON DATABASE slicer_api TO slicer_user;
\q
```

---

### 3. PrusaSlicer

**Check if installed:**

```bash
prusa-slicer --version
```

**Install (Ubuntu/Debian):**

```bash
# Try apt first
sudo apt install prusa-slicer

# If not available, download AppImage from:
# https://github.com/prusa3d/PrusaSlicer/releases
# Then:
chmod +x PrusaSlicer-*.AppImage
sudo mv PrusaSlicer-*.AppImage /usr/local/bin/prusa-slicer
```

**Install (macOS):**

```bash
brew install --cask prusaslicer
# CLI available at: /Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer
```

**Install (Windows):**
Download from https://www.prusa3d.com/page/prusaslicer_424/ — the CLI is included.

---

### 4. Git

**Check if installed:**

```bash
git --version
```

If not installed: `sudo apt install git` (Linux) or `brew install git` (macOS) or download from https://git-scm.com (Windows).

---

## Project Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/slicer-api.git
cd slicer-api
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
```

**Activate it:**

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt. Always activate venv before working.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create .env File

```bash
cp .env.example .env
```

Edit `.env` with your local values:

```
DATABASE_URL=postgresql://slicer_user:slicer_dev_password@localhost:5432/slicer_api
API_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
MAX_FILE_SIZE_MB=50
PRUSASLICER_PATH=/usr/bin/prusa-slicer
DEFAULT_MACHINE_RATE_PER_HOUR=1.50
DEFAULT_MARKUP_MULTIPLIER=1.5
```

Adjust `PRUSASLICER_PATH` to wherever PrusaSlicer is installed on your machine.

### Step 5: Run Database Migrations

```bash
alembic upgrade head
```

This creates all tables. If you see errors, check your DATABASE_URL in `.env`.

### Step 6: Seed Initial Data

```bash
python scripts/seed_filaments.py
python scripts/create_plan.py --seed
```

### Step 7: Create a Test User

```bash
python scripts/create_user.py --name "Test User" --email "test@localhost.com"
```

**Save the API key it prints!** You'll need it for testing.

### Step 8: Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--reload` auto-restarts when you change code. Only use in development.

### Step 9: Verify It Works

Open browser: http://localhost:8000/health

Should return:

```json
{ "status": "ok", "version": "1.0.0", "timestamp": "..." }
```

Open Swagger docs: http://localhost:8000/docs

---

## Common Issues

### "ModuleNotFoundError"

You forgot to activate the virtual environment. Run `source venv/bin/activate`.

### "Connection refused" on database

PostgreSQL isn't running. Start it:

```bash
sudo systemctl start postgresql   # Linux
brew services start postgresql@15  # macOS
```

### "alembic: command not found"

Activate venv first, or run `pip install alembic`.

### PrusaSlicer "command not found"

Check the path in your `.env`. Find it with:

```bash
which prusa-slicer          # Linux/macOS
where prusa-slicer          # Windows
```

### Port 8000 already in use

Another process is using it. Either kill it or use a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

---

## Daily Development Workflow

```bash
# 1. Navigate to project
cd slicer-api

# 2. Activate virtual environment
source venv/bin/activate

# 3. Pull latest code
git pull origin main

# 4. Install any new dependencies
pip install -r requirements.txt

# 5. Run any new migrations
alembic upgrade head

# 6. Start the server
uvicorn app.main:app --reload

# 7. Make changes, test, commit
git add .
git commit -m "Description of changes"
git push origin main
```

---

## Useful Commands

| Task                 | Command                                            |
| -------------------- | -------------------------------------------------- |
| Start server         | `uvicorn app.main:app --reload`                    |
| Run migrations       | `alembic upgrade head`                             |
| Create new migration | `alembic revision --autogenerate -m "description"` |
| Check database       | `psql -U slicer_user -d slicer_api`                |
| List tables          | `\dt` (inside psql)                                |
| View table data      | `SELECT * FROM users;` (inside psql)               |
| Run tests            | `python tests/test_api.py`                         |
| Deactivate venv      | `deactivate`                                       |
