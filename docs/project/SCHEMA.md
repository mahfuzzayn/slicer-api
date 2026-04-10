# SCHEMA.md — Database Design

## Database

- **Engine:** PostgreSQL 15+
- **Name:** slicer_api
- **ORM:** SQLAlchemy 2.0 (synchronous)
- **Migrations:** Alembic

---

## Tables

### plans

Subscription tiers that control rate limits and file size limits.

| Column             | Type          | Constraints              | Example                |
| ------------------ | ------------- | ------------------------ | ---------------------- |
| id                 | UUID          | PK, default uuid4        | `a1b2c3d4-...`         |
| name               | VARCHAR(50)   | UNIQUE, NOT NULL         | `"starter"`            |
| display_name       | VARCHAR(100)  | NOT NULL                 | `"Starter Plan"`       |
| monthly_price      | DECIMAL(10,2) | NOT NULL                 | `29.00`                |
| requests_per_month | INTEGER       | NOT NULL                 | `500`                  |
| max_file_size_mb   | INTEGER       | NOT NULL                 | `25`                   |
| is_active          | BOOLEAN       | NOT NULL, DEFAULT true   | `true`                 |
| created_at         | TIMESTAMP     | NOT NULL, DEFAULT utcnow | `2026-07-04T12:00:00Z` |

**Default seed data:**

| name         | monthly_price | requests_per_month | max_file_size_mb |
| ------------ | ------------- | ------------------ | ---------------- |
| starter      | 29.00         | 500                | 25               |
| professional | 99.00         | 2000               | 50               |
| enterprise   | 299.00        | 10000              | 100              |

---

### users

Customer accounts.

| Column     | Type         | Constraints                                | Example                |
| ---------- | ------------ | ------------------------------------------ | ---------------------- |
| id         | UUID         | PK, default uuid4                          | `b2c3d4e5-...`         |
| name       | VARCHAR(200) | NOT NULL                                   | `"Acme Corp"`          |
| email      | VARCHAR(200) | UNIQUE, NOT NULL                           | `"api@acme.com"`       |
| plan_id    | UUID         | FK → plans.id, ON DELETE SET NULL          | `a1b2c3d4-...`         |
| is_active  | BOOLEAN      | NOT NULL, DEFAULT true                     | `true`                 |
| created_at | TIMESTAMP    | NOT NULL, DEFAULT utcnow                   | `2026-07-04T12:00:00Z` |
| updated_at | TIMESTAMP    | NOT NULL, DEFAULT utcnow, ON UPDATE utcnow | `2026-07-04T12:00:00Z` |

**Indexes:**

- UNIQUE on `email`

---

### api_keys

Hashed API keys for authentication. One user can have multiple keys (for rotation).

| Column       | Type         | Constraints                                | Example                |
| ------------ | ------------ | ------------------------------------------ | ---------------------- |
| id           | UUID         | PK, default uuid4                          | `c3d4e5f6-...`         |
| user_id      | UUID         | FK → users.id, ON DELETE CASCADE, NOT NULL | `b2c3d4e5-...`         |
| key_hash     | VARCHAR(64)  | UNIQUE, NOT NULL                           | `sha256 hex digest`    |
| key_prefix   | VARCHAR(12)  | NOT NULL                                   | `"sk_a1b2c3d4"`        |
| label        | VARCHAR(100) | NULLABLE                                   | `"Production key"`     |
| is_active    | BOOLEAN      | NOT NULL, DEFAULT true                     | `true`                 |
| expires_at   | TIMESTAMP    | NULLABLE                                   | `2027-07-04T12:00:00Z` |
| last_used_at | TIMESTAMP    | NULLABLE                                   | `2026-07-04T12:00:00Z` |
| created_at   | TIMESTAMP    | NOT NULL, DEFAULT utcnow                   | `2026-07-04T12:00:00Z` |

**Indexes:**

- UNIQUE on `key_hash` (this is the lookup column for auth)
- INDEX on `user_id`

**Important:**

- `key_hash` stores the SHA-256 hex digest of the raw API key
- `key_prefix` stores the first 12 characters (e.g., `sk_a1b2c3d4`) for identification in logs
- The raw key is NEVER stored. It's shown once during creation.
- `last_used_at` is updated on every successful authentication

---

### jobs

Every slice request creates a job record.

| Column             | Type         | Constraints                                | Example                              |
| ------------------ | ------------ | ------------------------------------------ | ------------------------------------ |
| id                 | UUID         | PK, default uuid4                          | `d4e5f6g7-...`                       |
| user_id            | UUID         | FK → users.id, ON DELETE CASCADE, NOT NULL | `b2c3d4e5-...`                       |
| request_id         | UUID         | NOT NULL                                   | `e5f6g7h8-...`                       |
| status             | VARCHAR(20)  | NOT NULL, DEFAULT "running"                | `"succeeded"`                        |
| file_name          | VARCHAR(255) | NOT NULL                                   | `"bracket.stl"`                      |
| file_size_bytes    | BIGINT       | NOT NULL                                   | `1048576`                            |
| parameters_json    | JSONB        | NOT NULL                                   | `{"layer_height": 0.2, ...}`         |
| result_json        | JSONB        | NULLABLE                                   | `{"quote": {...}, "pricing": {...}}` |
| error_message      | TEXT         | NULLABLE                                   | `"PrusaSlicer timed out"`            |
| processing_time_ms | INTEGER      | NULLABLE                                   | `28500`                              |
| created_at         | TIMESTAMP    | NOT NULL, DEFAULT utcnow                   | `2026-07-04T12:00:00Z`               |
| completed_at       | TIMESTAMP    | NULLABLE                                   | `2026-07-04T12:01:48Z`               |

**Indexes:**

- INDEX on `user_id`
- INDEX on `user_id, created_at` (for paginated job listing)
- INDEX on `user_id, status` (for filtered queries)
- INDEX on `created_at` (for rate limit counting)

**Status values:**

- `running` — PrusaSlicer is processing
- `succeeded` — Complete with results
- `failed` — Error occurred

**Notes:**

- `parameters_json` stores the exact request parameters for audit trail
- `result_json` stores the complete pricing response (quote + pricing + details)
- `processing_time_ms` tracks how long PrusaSlicer took (useful for monitoring)
- `request_id` is the correlation ID returned to the customer

---

### filaments

Reference data for filament materials and pricing.

| Column            | Type          | Constraints                                | Example                |
| ----------------- | ------------- | ------------------------------------------ | ---------------------- |
| id                | UUID          | PK, default uuid4                          | `e5f6g7h8-...`         |
| type              | VARCHAR(20)   | UNIQUE, NOT NULL                           | `"PLA"`                |
| display_name      | VARCHAR(50)   | NOT NULL                                   | `"PLA Basic"`          |
| density_g_per_cm3 | DECIMAL(6,4)  | NOT NULL                                   | `1.2400`               |
| cost_per_kg       | DECIMAL(10,2) | NOT NULL                                   | `20.00`                |
| is_active         | BOOLEAN       | NOT NULL, DEFAULT true                     | `true`                 |
| created_at        | TIMESTAMP     | NOT NULL, DEFAULT utcnow                   | `2026-07-04T12:00:00Z` |
| updated_at        | TIMESTAMP     | NOT NULL, DEFAULT utcnow, ON UPDATE utcnow | `2026-07-04T12:00:00Z` |

**Indexes:**

- UNIQUE on `type`

**Default seed data:**

| type  | display_name     | density_g_per_cm3 | cost_per_kg |
| ----- | ---------------- | ----------------- | ----------- |
| PLA   | PLA Basic        | 1.2400            | 20.00       |
| ABS   | ABS Standard     | 1.0400            | 22.00       |
| PETG  | PETG Standard    | 1.2700            | 25.00       |
| TPU   | TPU Flexible     | 1.2100            | 35.00       |
| Nylon | Nylon PA12       | 1.1400            | 40.00       |
| ASA   | ASA UV-Resistant | 1.0700            | 28.00       |
| PC    | Polycarbonate    | 1.2000            | 45.00       |
| PVA   | PVA Soluble      | 1.2300            | 50.00       |

---

## Entity Relationship Diagram

```
┌──────────┐       ┌──────────┐
│  plans    │       │filaments │
│──────────│       │──────────│
│ id (PK)  │       │ id (PK)  │
│ name     │       │ type     │
│ price    │       │ density  │
│ limits   │       │ cost/kg  │
└────┬─────┘       └──────────┘
     │ 1                 ▲
     │                   │ looked up by type
     │ many              │ (no FK — soft reference)
     ▼                   │
┌──────────┐       ┌──────────┐
│  users   │       │  jobs    │
│──────────│       │──────────│
│ id (PK)  │──1:N──▶│ id (PK)  │
│ name     │       │ user_id  │
│ email    │       │ status   │
│ plan_id  │       │ params   │
└────┬─────┘       │ result   │
     │             └──────────┘
     │ 1
     │
     │ many
     ▼
┌──────────┐
│ api_keys │
│──────────│
│ id (PK)  │
│ user_id  │
│ key_hash │
│ prefix   │
└──────────┘
```

---

## Migration Strategy

- Use Alembic for ALL schema changes
- Never modify tables manually via SQL
- Migration naming: `YYYYMMDD_description` (e.g., `20260704_initial_schema`)
- Always test migrations locally before running on production
- Keep `alembic upgrade head` in the container startup script for automatic migration on deploy
