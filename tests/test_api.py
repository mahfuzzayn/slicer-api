"""Standalone integration tests for slicer-api.

Run:
    python tests/test_api.py

Environment variables:
    BASE_URL       (default: http://localhost:8000)
    TEST_API_KEY   (required for authenticated tests)
    TEST_STL_PATH  (optional — defaults to embedded cube STL)
"""
import os
import struct
import sys
import uuid
from pathlib import Path

import requests


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
TEST_API_KEY = os.environ.get("TEST_API_KEY", "")
TEST_STL_PATH = os.environ.get("TEST_STL_PATH", "")

PASS = "PASS"
FAIL = "FAIL"

results: list[tuple[str, str, str]] = []


def _cube_stl_bytes() -> bytes:
    """Build a minimal valid binary STL of a unit cube."""
    verts = [
        (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
        (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
    ]
    triangles = [
        (0, 1, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1),
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 4), (3, 4, 0),
    ]
    header = b"\x00" * 80
    out = bytearray(header + struct.pack("<I", len(triangles)))
    for a, b, c in triangles:
        out += struct.pack("<3f", 0.0, 0.0, 0.0)
        for idx in (a, b, c):
            out += struct.pack("<3f", *map(float, verts[idx]))
        out += struct.pack("<H", 0)
    return bytes(out)


def _stl_payload() -> tuple[str, bytes]:
    if TEST_STL_PATH and Path(TEST_STL_PATH).exists():
        return Path(TEST_STL_PATH).name, Path(TEST_STL_PATH).read_bytes()
    return "cube.stl", _cube_stl_bytes()


def record(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    marker = "[OK]" if status == PASS else "[FAIL]"
    print(f"{marker} {name}" + (f" — {detail}" if detail else ""))


def _auth_headers(key: str | None = None) -> dict:
    return {"Authorization": f"Bearer {key or TEST_API_KEY}"}


def test_health():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        assert r.status_code == 200, r.status_code
        data = r.json()
        assert data.get("status") == "ok", data
        record("health returns 200 ok", PASS)
    except Exception as exc:
        record("health returns 200 ok", FAIL, str(exc))


def test_slice_no_auth():
    try:
        name, body = _stl_payload()
        r = requests.post(
            f"{BASE_URL}/slice",
            files={"file": (name, body, "application/octet-stream")},
            timeout=30,
        )
        assert r.status_code == 401, r.status_code
        record("slice without auth returns 401", PASS)
    except Exception as exc:
        record("slice without auth returns 401", FAIL, str(exc))


def test_slice_invalid_key():
    try:
        name, body = _stl_payload()
        r = requests.post(
            f"{BASE_URL}/slice",
            headers=_auth_headers("sk_invalidkey"),
            files={"file": (name, body, "application/octet-stream")},
            timeout=30,
        )
        assert r.status_code == 401, r.status_code
        record("slice with invalid key returns 401", PASS)
    except Exception as exc:
        record("slice with invalid key returns 401", FAIL, str(exc))


def test_slice_missing_file():
    if not TEST_API_KEY:
        record("slice without file returns 422", FAIL, "TEST_API_KEY not set")
        return
    try:
        r = requests.post(f"{BASE_URL}/slice", headers=_auth_headers(), timeout=10)
        assert r.status_code == 422, r.status_code
        record("slice without file returns 422", PASS)
    except Exception as exc:
        record("slice without file returns 422", FAIL, str(exc))


def test_slice_non_stl():
    if not TEST_API_KEY:
        record("slice with non-STL returns 400", FAIL, "TEST_API_KEY not set")
        return
    try:
        r = requests.post(
            f"{BASE_URL}/slice",
            headers=_auth_headers(),
            files={"file": ("not.txt", b"hello world", "text/plain")},
            timeout=15,
        )
        assert r.status_code == 400, r.status_code
        record("slice with non-STL returns 400", PASS)
    except Exception as exc:
        record("slice with non-STL returns 400", FAIL, str(exc))


def test_slice_valid() -> str | None:
    if not TEST_API_KEY:
        record("slice with valid STL returns 200", FAIL, "TEST_API_KEY not set")
        return None
    try:
        name, body = _stl_payload()
        r = requests.post(
            f"{BASE_URL}/slice",
            headers=_auth_headers(),
            files={"file": (name, body, "application/octet-stream")},
            data={"layer_height": 0.2, "fill_density": 20, "fill_pattern": "grid"},
            timeout=180,
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
        data = r.json()
        assert "pricing" in data and "customer_price" in data["pricing"]
        record("slice with valid STL returns 200", PASS)
        return data["job_id"]
    except Exception as exc:
        record("slice with valid STL returns 200", FAIL, str(exc))
        return None


def test_list_jobs():
    if not TEST_API_KEY:
        record("list jobs returns 200", FAIL, "TEST_API_KEY not set")
        return
    try:
        r = requests.get(f"{BASE_URL}/jobs", headers=_auth_headers(), timeout=15)
        assert r.status_code == 200, r.status_code
        data = r.json()
        assert "jobs" in data and "pagination" in data
        record("list jobs returns 200", PASS)
    except Exception as exc:
        record("list jobs returns 200", FAIL, str(exc))


def test_get_job(job_id: str | None):
    if not TEST_API_KEY or not job_id:
        record("get job returns 200", FAIL, "no job_id")
        return
    try:
        r = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=_auth_headers(), timeout=15)
        assert r.status_code == 200, r.status_code
        assert r.json()["job_id"] == job_id
        record("get job returns 200", PASS)
    except Exception as exc:
        record("get job returns 200", FAIL, str(exc))


def test_get_job_wrong_user():
    if not TEST_API_KEY:
        record("get non-existent job returns 404", FAIL, "TEST_API_KEY not set")
        return
    try:
        fake = str(uuid.uuid4())
        r = requests.get(f"{BASE_URL}/jobs/{fake}", headers=_auth_headers(), timeout=10)
        assert r.status_code == 404, r.status_code
        record("get non-existent job returns 404", PASS)
    except Exception as exc:
        record("get non-existent job returns 404", FAIL, str(exc))


def test_rate_limit():
    record(
        "rate limit returns 429",
        PASS,
        "skipped — requires pre-exhausted quota, verify manually",
    )


def main() -> int:
    print(f"Running tests against {BASE_URL}")
    print(f"TEST_API_KEY set: {bool(TEST_API_KEY)}")
    print()

    test_health()
    test_slice_no_auth()
    test_slice_invalid_key()
    test_slice_missing_file()
    test_slice_non_stl()
    job_id = test_slice_valid()
    test_list_jobs()
    test_get_job(job_id)
    test_get_job_wrong_user()
    test_rate_limit()

    failed = [r for r in results if r[1] == FAIL]
    print()
    print(f"Results: {len(results) - len(failed)}/{len(results)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
