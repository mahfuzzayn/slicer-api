# TESTING.md — Verification Checklist

Run these tests after every deployment or significant code change. Each test includes the exact curl command and expected result.

Replace `BASE_URL` and `API_KEY` with your actual values.

```bash
# Set these once per session
BASE_URL="http://localhost:8000"       # or https://api.yourdomain.com
API_KEY="sk_your_actual_key_here"
STL_FILE="path/to/test.stl"           # any valid STL file
```

---

## Test 1: Health Check

```bash
curl -s $BASE_URL/health | python3 -m json.tool
```

**Expected:** HTTP 200

```json
{
    "status": "ok",
    "version": "1.0.0",
    "timestamp": "2026-07-04T12:00:00Z"
}
```

**Pass criteria:** Status is "ok", response is valid JSON.

---

## Test 2: Slice Without Auth → 401

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST $BASE_URL/slice \
  -F "file=@$STL_FILE"
```

**Expected:** HTTP 401

```json
{
    "error": {
        "code": "MISSING_API_KEY",
        "message": "..."
    }
}
```

**Pass criteria:** Returns 401, not 500 or 200.

---

## Test 3: Slice With Invalid Key → 401

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST $BASE_URL/slice \
  -H "Authorization: Bearer sk_invalid_fake_key_12345" \
  -F "file=@$STL_FILE"
```

**Expected:** HTTP 401

```json
{
    "error": {
        "code": "INVALID_API_KEY",
        "message": "..."
    }
}
```

**Pass criteria:** Returns 401 with INVALID_API_KEY code.

---

## Test 4: Slice Without File → 422

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST $BASE_URL/slice \
  -H "Authorization: Bearer $API_KEY"
```

**Expected:** HTTP 422 (validation error — no file uploaded)

**Pass criteria:** Returns 422, not 500.

---

## Test 5: Slice With Non-STL File → 400

```bash
# Create a fake text file
echo "not an stl file" > /tmp/fake.txt

curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST $BASE_URL/slice \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@/tmp/fake.txt"
```

**Expected:** HTTP 400

```json
{
    "error": {
        "code": "INVALID_FILE",
        "message": "..."
    }
}
```

**Pass criteria:** Returns 400 with INVALID_FILE code. Does NOT attempt to slice.

---

## Test 6: Valid Slice Request → 200

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST $BASE_URL/slice \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@$STL_FILE" \
  -F "layer_height=0.2" \
  -F "fill_density=20" \
  -F "fill_pattern=grid" \
  -F "perimeters=3" \
  -F "support_material=false" \
  -F "filament_type=PLA" | python3 -m json.tool
```

**Expected:** HTTP 200

```json
{
  "request_id": "uuid-here",
  "job_id": "uuid-here",
  "status": "succeeded",
  "quote": {
    "filament_mm": 7068.30,
    "filament_cm3": 17.00,
    "filament_g": 21.08,
    "estimated_print_time": "1h 48m 29s",
    "estimated_print_time_hours": 1.8081,
    "first_layer_time": "56s"
  },
  "pricing": {
    "material_cost": 0.4216,
    "machine_cost": 2.7120,
    "total_cost": 3.1336,
    "customer_price": 4.7004,
    "currency": "USD"
  },
  "details": { "..." },
  "parameters": { "..." }
}
```

**Pass criteria:**

- [ ] HTTP 200
- [ ] `request_id` is a valid UUID
- [ ] `job_id` is a valid UUID
- [ ] `status` is "succeeded"
- [ ] `quote.filament_mm` is a number > 0
- [ ] `quote.filament_cm3` is a number > 0
- [ ] `quote.estimated_print_time` is a non-empty string
- [ ] `pricing.material_cost` is a number > 0
- [ ] `pricing.machine_cost` is a number > 0
- [ ] `pricing.customer_price` > `pricing.total_cost` (markup applied)
- [ ] All numeric values are numbers, NOT strings
- [ ] `X-Request-ID` header present in response
- [ ] `X-RateLimit-Remaining` header present

---

## Test 7: Slice With Custom Pricing → 200

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST $BASE_URL/slice \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@$STL_FILE" \
  -F "filament_type=PETG" \
  -F "machine_rate_per_hour=3.00" \
  -F "markup_multiplier=2.0" | python3 -m json.tool
```

**Pass criteria:**

- [ ] `details.filament_type` is "PETG"
- [ ] `details.machine_rate_per_hour` is 3.00
- [ ] `details.markup_multiplier` is 2.0
- [ ] `pricing.customer_price` = `pricing.total_cost` × 2.0

---

## Test 8: List Jobs → 200

```bash
curl -s \
  -H "Authorization: Bearer $API_KEY" \
  $BASE_URL/jobs | python3 -m json.tool
```

**Pass criteria:**

- [ ] HTTP 200
- [ ] `jobs` is an array with at least 1 entry (from Test 6)
- [ ] Each job has `job_id`, `status`, `created_at`
- [ ] `pagination` object present with `page`, `total`

---

## Test 9: Get Specific Job → 200

Use the `job_id` from Test 6:

```bash
JOB_ID="paste-job-id-from-test-6"

curl -s \
  -H "Authorization: Bearer $API_KEY" \
  $BASE_URL/jobs/$JOB_ID | python3 -m json.tool
```

**Pass criteria:**

- [ ] HTTP 200
- [ ] `job_id` matches what you requested
- [ ] `status` is "succeeded"
- [ ] `parameters`, `quote`, `pricing`, `details` all present
- [ ] Data matches what Test 6 returned

---

## Test 10: Invalid Parameter Range → 400 or 422

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST $BASE_URL/slice \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@$STL_FILE" \
  -F "layer_height=5.0" \
  -F "fill_density=200"
```

**Pass criteria:** Returns 400 or 422, NOT 200. Invalid values must be rejected.

---

## Test 11: Pagination

```bash
curl -s \
  -H "Authorization: Bearer $API_KEY" \
  "$BASE_URL/jobs?page=1&per_page=1" | python3 -m json.tool
```

**Pass criteria:**

- [ ] `jobs` array has exactly 1 item
- [ ] `pagination.per_page` is 1
- [ ] `pagination.total_pages` reflects correct count

---

## Test 12: Job Not Found → 404

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -H "Authorization: Bearer $API_KEY" \
  $BASE_URL/jobs/00000000-0000-0000-0000-000000000000
```

**Pass criteria:** HTTP 404 with `JOB_NOT_FOUND` error code.

---

## Production-Only Tests

Run these after deploying to Coolify:

### HTTPS Check

```bash
curl -s https://api.yourdomain.com/health | python3 -m json.tool
```

**Pass criteria:** Returns 200 over HTTPS. No certificate errors.

### HTTP Redirect

```bash
curl -s -o /dev/null -w "%{http_code}" http://api.yourdomain.com/health
```

**Pass criteria:** Returns 301 or 302 redirecting to HTTPS. (Coolify/Traefik handles this.)

### Large File Rejection

```bash
# Create a 60MB dummy file
dd if=/dev/zero of=/tmp/large.stl bs=1M count=60

curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST https://api.yourdomain.com/slice \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@/tmp/large.stl"
```

**Pass criteria:** Returns 413 FILE_TOO_LARGE (if plan limit is 50MB or less).

---

## Test Summary Checklist

| #   | Test                | Expected                | Status |
| --- | ------------------- | ----------------------- | ------ |
| 1   | Health check        | 200                     | ☐      |
| 2   | No auth             | 401                     | ☐      |
| 3   | Invalid key         | 401                     | ☐      |
| 4   | No file             | 422                     | ☐      |
| 5   | Non-STL file        | 400                     | ☐      |
| 6   | Valid slice         | 200 + full pricing      | ☐      |
| 7   | Custom pricing      | 200 + overrides applied | ☐      |
| 8   | List jobs           | 200 + array             | ☐      |
| 9   | Get job             | 200 + matching data     | ☐      |
| 10  | Invalid params      | 400/422                 | ☐      |
| 11  | Pagination          | Correct page size       | ☐      |
| 12  | Job not found       | 404                     | ☐      |
| P1  | HTTPS works         | 200                     | ☐      |
| P2  | HTTP redirects      | 301/302                 | ☐      |
| P3  | Large file rejected | 413                     | ☐      |
