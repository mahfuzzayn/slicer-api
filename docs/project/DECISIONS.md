# DECISIONS.md — Architecture Decision Records

Every technical decision and why it was made. When someone asks "why did we do it this way?" — the answer is here.

---

## ADR-001: Python + FastAPI over Node.js

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Team member Mahi built the MVP in Python + FastAPI. Question arose whether to switch to Node.js.

**Decision:** Stay with Python + FastAPI.

**Reasoning:**

- MVP already works in Python — switching wastes days
- PrusaSlicer is called via subprocess, which Python handles naturally
- FastAPI auto-generates OpenAPI docs (Swagger UI) — no extra work
- FastAPI has excellent validation via Pydantic
- Python is the dominant language for file processing and CLI tool orchestration
- Node.js has no advantage here — this isn't a real-time or frontend-heavy app

**Consequences:** Team needs Python knowledge. Mahi has this. Project lead is learning.

---

## ADR-002: No Docker Compose, Single Dockerfile Only

**Date:** 2026-07-04
**Status:** Accepted

**Context:** The 12-day roadmap originally planned Docker Compose with API + worker + Redis + PostgreSQL containers. Team has zero Docker experience.

**Decision:** Use a single Dockerfile for the API. PostgreSQL deployed separately via Coolify's one-click service.

**Reasoning:**

- Docker Compose multi-service adds significant complexity for a team that doesn't know Docker
- Coolify manages PostgreSQL as a separate service with its own backups and configuration
- Single Dockerfile is ~15 lines and easy to understand
- Coolify builds and deploys from Dockerfile automatically
- Multi-container orchestration adds zero value for a single-server setup

**Consequences:** If we need Redis or worker containers later, we'll add them as separate Coolify services, not Docker Compose.

---

## ADR-003: No Redis, Synchronous Slicing for v1

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Original roadmap included Redis + Celery for async job processing. Team has no Redis or message queue experience.

**Decision:** Process slicing synchronously in the request thread. No Redis in v1.

**Reasoning:**

- A typical PrusaSlicer run takes 10–30 seconds
- For B2B with fewer than 10 concurrent users, synchronous is fine
- FastAPI's thread pool handles some concurrency naturally
- Nginx (via Coolify/Traefik) proxy_read_timeout can be set to 120s
- Adding Redis + Celery introduces 3 new technologies the team doesn't know
- The 4-day deadline doesn't allow time to learn and debug queue systems

**Trade-offs:**

- Customer waits for the response (not ideal for large files)
- If 10+ users send requests simultaneously, some will timeout
- No job status polling needed since response is synchronous

**When to revisit:** When we see timeout errors in production or get 5+ concurrent users regularly.

---

## ADR-004: API Key Auth over OAuth/JWT

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Need authentication for B2B API access. Options: API keys, OAuth 2.0, JWT tokens.

**Decision:** Simple API key authentication with Bearer token.

**Reasoning:**

- B2B customers want a single key they can put in their code — not an OAuth dance
- API keys are the standard for B2B SaaS APIs (Stripe, OpenAI, SendGrid all use them)
- OAuth adds complexity (token refresh, scopes, consent flows) with no benefit for machine-to-machine communication
- JWT requires token issuance, expiry handling, and refresh logic
- API keys are simpler to implement, test, and support

**Security measures:**

- Keys are SHA-256 hashed before storage (never stored raw)
- Keys have optional expiry dates
- Keys can be deactivated instantly
- Only the 8-char prefix is logged
- Keys are shown once during creation

**Consequences:** No per-request token rotation. If a key is compromised, the customer must contact us to revoke and reissue. This is acceptable for v1.

---

## ADR-005: Coolify over Manual Nginx + systemd

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Originally planned manual Nginx configuration, Let's Encrypt setup, and systemd services. Team is new to VPS management.

**Decision:** Use Coolify for deployment, reverse proxy, and HTTPS.

**Reasoning:**

- Coolify handles Traefik (reverse proxy), Let's Encrypt (HTTPS), and container management via a web UI
- Already installed on the VPS (Hostinger KVM2)
- Eliminates need to learn Nginx configuration, certbot, and systemd service files
- One-click PostgreSQL deployment
- GitHub integration for auto-deploys
- Web-based log viewing
- Reduces "Day 5" from a full day of sysadmin work to ~1 hour

**Trade-offs:**

- Less control over Nginx tuning (timeout values, buffer sizes)
- Coolify itself uses RAM (~500MB) which is significant on a small VPS
- Dependency on Coolify project for updates and bug fixes

**Consequences:** Need a Dockerfile (Coolify deploys containers). This is the only Docker knowledge needed.

---

## ADR-006: Database-Based Rate Limiting over Redis

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Need per-user rate limiting. Redis is the traditional tool. We don't have Redis.

**Decision:** Count requests from the jobs table in PostgreSQL.

**Reasoning:**

- Every request already creates a job row — the data exists
- `SELECT COUNT(*) FROM jobs WHERE user_id = X AND created_at >= first_of_month` is fast with an index
- Monthly billing cycles align with simple date-range queries
- No new technology to learn or maintain

**Trade-offs:**

- Slightly slower than Redis (milliseconds, not microseconds) — irrelevant for our volume
- Under extreme concurrent load, race conditions could allow slight over-quota usage
- No sliding window — it's a monthly reset

**When to revisit:** When we need per-second rate limiting or sliding windows. That requires Redis.

---

## ADR-007: PrusaSlicer over Other Slicers

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Need an open-source slicer with CLI support for accurate filament/time estimation.

**Decision:** PrusaSlicer CLI.

**Alternatives considered:**

- **Cura (CuraEngine):** Also excellent but CLI integration is more complex. Config profiles are harder to manage headless.
- **Slic3r:** PrusaSlicer is a fork of Slic3r with more active development.
- **SuperSlicer:** Fork of PrusaSlicer. Less mainstream, smaller community.

**Reasoning:**

- Industry standard with active development
- Excellent CLI support with `--export-gcode` flag
- Accurate filament usage and time estimates (within 2-5% of actual)
- G-code comments are well-structured and easy to parse
- Free and open source (AGPLv3)
- Mahi already has working integration

**Consequences:** Accuracy depends on slicer profiles matching actual printers. May need to support multiple printer profiles in future versions.

---

## ADR-008: Monolithic API over Microservices

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Could separate slicing, pricing, and auth into different services.

**Decision:** Single FastAPI application with all logic.

**Reasoning:**

- Team of 2, building in 4 days — microservices would be insane
- All components share the same database
- No independent scaling needs (slicing is the only heavy operation)
- Deployment is one container, one service
- Debugging is straightforward — one set of logs

**When to revisit:** When (if ever) we need to scale slicing workers independently from the API. That's a v2+ concern.

---

## ADR-009: Store Pricing in Database, Not Config Files

**Date:** 2026-07-04
**Status:** Accepted

**Context:** Filament costs and machine rates need to be configurable. Could use env vars, config files, or database.

**Decision:** Store filament data in a `filaments` database table. Machine rate and markup as env vars with request-level overrides.

**Reasoning:**

- Filament prices change. Database lets you update without redeploying
- Admin CLI can add/update filaments
- Database is already there — no extra infrastructure
- Env vars for defaults (machine rate, markup) since these change rarely
- Per-request overrides let customers do self-service pricing

**Consequences:** Need seed scripts for initial filament data. Need admin CLI for price updates.
