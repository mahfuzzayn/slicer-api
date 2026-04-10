# API-SPEC.md — API Contract

## Base URL

```
Production: https://api.yourdomain.com
Local:      http://localhost:8000
```

## Authentication

All endpoints except `GET /health` require authentication.

```
Authorization: Bearer sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8
```

Keys are prefixed with `sk_` for identification.

---

## Endpoints

### GET /health

Health check. No authentication required.

**Response: 200 OK**

```json
{
    "status": "ok",
    "version": "1.0.0",
    "timestamp": "2026-07-04T12:00:00Z"
}
```

---

### POST /slice

Upload an STL file and get a cost estimate.

**Request:**

- Content-Type: `multipart/form-data`
- Auth: Required

| Field                 | Type       | Required | Default        | Constraints             |
| --------------------- | ---------- | -------- | -------------- | ----------------------- |
| file                  | file (STL) | yes      | —              | .stl only, max per plan |
| layer_height          | float      | no       | 0.2            | 0.05 – 0.6              |
| fill_density          | int        | no       | 20             | 0 – 100                 |
| fill_pattern          | string     | no       | "grid"         | See allowed values      |
| perimeters            | int        | no       | 3              | 1 – 10                  |
| support_material      | bool       | no       | false          | —                       |
| filament_type         | string     | no       | "PLA"          | See allowed values      |
| machine_rate_per_hour | float      | no       | server default | 0.0 – 100.0             |
| markup_multiplier     | float      | no       | server default | 1.0 – 10.0              |

**Allowed fill_pattern values:**
`grid`, `gyroid`, `honeycomb`, `rectilinear`, `triangles`, `cubic`, `line`, `concentric`

**Allowed filament_type values:**
`PLA`, `ABS`, `PETG`, `TPU`, `Nylon`, `ASA`, `PC`, `PVA`

**Response: 200 OK**

```json
{
    "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "job_id": "c3a42232-4f7c-478a-a616-561be0b703f4",
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

**Response Headers:**

```
X-Request-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 347
X-RateLimit-Reset: 2026-08-01T00:00:00Z
```

---

### GET /jobs

List the authenticated user's jobs.

**Request:**

- Auth: Required
- Query parameters:

| Param    | Type   | Default | Constraints                      |
| -------- | ------ | ------- | -------------------------------- |
| page     | int    | 1       | >= 1                             |
| per_page | int    | 20      | 1 – 100                          |
| status   | string | — (all) | "running", "succeeded", "failed" |

**Response: 200 OK**

```json
{
    "jobs": [
        {
            "job_id": "c3a42232-4f7c-478a-a616-561be0b703f4",
            "status": "succeeded",
            "file_name": "model.stl",
            "filament_type": "PLA",
            "customer_price": 4.7004,
            "created_at": "2026-07-04T12:00:00Z",
            "completed_at": "2026-07-04T12:01:48Z"
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

---

### GET /jobs/{job_id}

Get details for a specific job. Only returns jobs belonging to the authenticated user.

**Response: 200 OK**

```json
{
    "job_id": "c3a42232-4f7c-478a-a616-561be0b703f4",
    "status": "succeeded",
    "file_name": "model.stl",
    "created_at": "2026-07-04T12:00:00Z",
    "completed_at": "2026-07-04T12:01:48Z",
    "parameters": {
        "layer_height": 0.2,
        "fill_density": 20,
        "fill_pattern": "grid",
        "perimeters": 3,
        "support_material": false,
        "filament_type": "PLA"
    },
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
    }
}
```

---

## Error Responses

All errors follow this format:

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable explanation",
        "details": {}
    }
}
```

### Error Codes

| HTTP Status | Code                | When                                            |
| ----------- | ------------------- | ----------------------------------------------- |
| 400         | INVALID_FILE        | File is not a valid STL                         |
| 400         | INVALID_PARAMETER   | Parameter out of allowed range                  |
| 401         | MISSING_API_KEY     | No Authorization header                         |
| 401         | INVALID_API_KEY     | Key not found or inactive                       |
| 401         | EXPIRED_API_KEY     | Key past expiry date                            |
| 403         | ACCOUNT_INACTIVE    | User account deactivated                        |
| 404         | JOB_NOT_FOUND       | Job ID doesn't exist or belongs to another user |
| 413         | FILE_TOO_LARGE      | File exceeds plan's size limit                  |
| 422         | VALIDATION_ERROR    | Request body failed Pydantic validation         |
| 429         | RATE_LIMIT_EXCEEDED | Monthly request quota exceeded                  |
| 500         | SLICER_ERROR        | PrusaSlicer crashed or timed out                |
| 500         | INTERNAL_ERROR      | Unexpected server error                         |

### Error Examples

**401 — Invalid API Key:**

```json
{
    "error": {
        "code": "INVALID_API_KEY",
        "message": "The provided API key is not valid or has been deactivated",
        "details": {}
    }
}
```

**413 — File Too Large:**

```json
{
    "error": {
        "code": "FILE_TOO_LARGE",
        "message": "File size exceeds your plan's limit",
        "details": {
            "file_size_mb": 52.3,
            "max_allowed_mb": 25
        }
    }
}
```

**429 — Rate Limit Exceeded:**

```json
{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "You have exceeded your monthly request quota",
        "details": {
            "limit": 500,
            "used": 500,
            "resets_at": "2026-08-01T00:00:00Z"
        }
    }
}
```

---

## Data Types

All numeric values in responses are numbers (float or int), never strings.
All timestamps are ISO 8601 UTC format.
All UUIDs are standard v4 UUID strings.
Currency is always USD unless otherwise specified in future versions.
