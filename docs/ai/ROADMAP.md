# ROADMAP.md — 4-Day Sprint Plan

## Overview

Build and deploy a production-ready B2B slicing API in 4 days using Claude Code as the primary builder.

**Start state:** Working MVP (Mahi's app.py) with basic slicing and cost calculation.
**End state:** Authenticated, database-backed API deployed on Coolify with subscription tiers, rate limiting, and proper error handling.

---

## Day 1 — Build the Complete v1

**Goal:** Entire codebase built and running locally.

**Method:** Execute PROMPTS.md step by step with Claude Code.

### What Gets Built

| Component         | Details                                              |
| ----------------- | ---------------------------------------------------- |
| Project structure | Clean FastAPI project layout                         |
| Database models   | users, api_keys, jobs, plans, filaments tables       |
| Auth system       | API key generation, hashing, verification middleware |
| Slice endpoint    | POST /slice with full validation                     |
| Jobs endpoints    | GET /jobs, GET /jobs/{id} with pagination            |
| Health endpoint   | GET /health (no auth)                                |
| Slicer service    | PrusaSlicer subprocess with timeout and cleanup      |
| G-code parser     | Extract filament usage, print time, layers           |
| Pricing engine    | material + machine + markup calculation              |
| Error handling    | Consistent error format, proper HTTP codes           |
| Rate limiting     | Database-based, per-plan limits                      |
| Admin scripts     | create_user, create_plan, seed_filaments             |
| Dockerfile        | Single container for Coolify deployment              |
| Alembic setup     | Database migrations configured                       |

### Checkpoints

- [ ] App starts locally with `uvicorn app.main:app --reload`
- [ ] GET /health returns 200
- [ ] POST /slice without key returns 401
- [ ] POST /slice with valid key + STL returns cost quote
- [ ] GET /jobs/{id} returns job details
- [ ] Rate limit triggers 429 when exceeded

### End of Day 1 Deliverable

Complete codebase on GitHub. All endpoints functional locally.

---

## Day 2 — Understand, Verify, Fix

**Goal:** You understand every file. All bugs fixed. Code is deployment-ready.

### Morning: Code Walkthrough

Read every file in this order (this traces the request flow):

1. `app/main.py` — Where the app starts, what middleware is loaded
2. `app/config.py` — What environment variables are used
3. `app/dependencies.py` — How API key auth works
4. `app/models/tables.py` — What's in the database
5. `app/models/schemas.py` — What requests and responses look like
6. `app/routers/slice.py` — The main endpoint, follow the logic
7. `app/services/slicer.py` — How PrusaSlicer is called
8. `app/services/gcode_parser.py` — How G-code output is parsed
9. `app/services/pricing.py` — How cost is calculated
10. `app/utils/security.py` — How API keys are generated and hashed

### Afternoon: Test Every Path

Run through TESTING.md checklist. For each test:

- Does it return the expected status code?
- Does the response match API-SPEC.md?
- Is the job saved in the database?

### Fix Issues

Use Claude Code to fix any bugs found. Update CHANGELOG.md after each fix.

### End of Day 2 Deliverable

You can explain how every file works. All tests pass. Code pushed to GitHub.

---

## Day 3 — Deploy on Coolify

**Goal:** API live on the internet with HTTPS.

### Tasks

1. **Push final code to GitHub** (if not already done)

2. **Create PostgreSQL in Coolify**
    - Coolify dashboard → New Resource → PostgreSQL
    - Copy the connection string

3. **Deploy the API in Coolify**
    - New Resource → choose GitHub repo
    - Coolify detects the Dockerfile and builds
    - Set environment variables (DATABASE_URL, PRUSASLICER_PATH, etc.)
    - Assign domain (e.g., api.yourdomain.com)
    - Coolify auto-configures HTTPS via Let's Encrypt

4. **Run database migrations**
    - Exec into the container via Coolify terminal
    - Run: `alembic upgrade head`

5. **Seed initial data**
    - Run: `python scripts/create_plan.py`
    - Run: `python scripts/seed_filaments.py`
    - Run: `python scripts/create_user.py "Test User" "test@email.com"`

6. **Verify deployment**
    - Hit `https://api.yourdomain.com/health` from browser
    - Test POST /slice with curl from your local machine

### Important Notes on Coolify + PrusaSlicer

PrusaSlicer must be installed inside the Docker container. The Dockerfile must include:

```dockerfile
RUN apt-get update && apt-get install -y prusa-slicer
```

If the package isn't available, you may need to download the AppImage and extract it. Claude Code should handle this in the Dockerfile.

### End of Day 3 Deliverable

API accessible at https://api.yourdomain.com. HTTPS working. Database connected. First test user created.

---

## Day 4 — Test Production + Prepare for Customers

**Goal:** Everything verified on production. Minimal docs ready. First real API key issued.

### Morning: Production Testing

1. Run full TESTING.md checklist against the live URL
2. Test with multiple STL files of different sizes and complexity
3. Verify rate limiting works on production
4. Check logs in Coolify dashboard
5. Verify database has all job records

### Afternoon: Customer Readiness

1. Create subscription plans in production database
2. Write a one-page API quick-start guide for customers
3. Create first real customer API key
4. Send a test request using their key
5. Set up daily database backup (pg_dump cron inside Coolify or via Coolify's backup feature)

### End of Day 4 Deliverable

Production system verified. First customer can start using the API.

---

## Post-Launch (Version 2 — No Deadline)

| Feature                                    | Priority                         |
| ------------------------------------------ | -------------------------------- |
| Redis + async queue for background slicing | When 5+ concurrent users         |
| Webhook notifications on job completion    | When customers request it        |
| Admin web dashboard                        | When CLI management gets tedious |
| Multi-printer profile support              | When customers need it           |
| G-code file download endpoint              | When customers request it        |
| Stripe payment integration                 | When ready to automate billing   |
| Docker Compose for local dev               | When team grows                  |
