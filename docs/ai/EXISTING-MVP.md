# EXISTING-MVP.md — Working MVP Code Reference

This is the existing working code built by team member Mahi. It runs on the VPS at `/opt/slicing-api/` and returns successful API responses.

**DO NOT throw this code away. Refactor it into the new project structure, preserving the working patterns.**

---

## What Works (Preserve These)

1. **PrusaSlicer CLI command construction** — The argument list pattern, flag ordering, and `--support-material` as boolean flag are all tested and working.

2. **G-code regex patterns** — These exact patterns match real PrusaSlicer output. Do not modify them.

3. **Filament cost fallback logic** — Uses `filament_g` when available, falls back to `filament_cm3 * density`. This handles the case where PrusaSlicer doesn't output gram data.

4. **File cleanup in finally block** — Temp files are always deleted, even on error.

## What Needs Improvement (Fix in v1)

1. **No subprocess timeout** — A huge STL can hang forever. Add 120s timeout.
2. **No auth** — Anyone can call the API. Add API key auth.
3. **No database** — Nothing is recorded. Add PostgreSQL.
4. **Hardcoded filament data** — Only PLA. Move to database.
5. **Quote values are strings** — `filament_mm: "7068.30"` should be `filament_mm: 7068.30`.
6. **No machine cost** — Only material cost is calculated. Add machine + markup.
7. **fill_density is a string** — Customer sends `"15%"`. API should accept integer `15` and format internally.
8. **No rate limiting** — Any user can make unlimited requests.
9. **Files saved to fixed paths** — Should use tempfile module for safety.
10. **PrusaSlicer path hardcoded** — Should come from environment variable.

---

## Current MVP Code (app/app.py — newer version)

```python
import re
import uuid
import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException

app = FastAPI(title="Slicing Quote API")

BASE_DIR = Path("/opt/slicing-api")
UPLOAD_DIR = BASE_DIR / "uploads"
OUT_DIR = BASE_DIR / "out"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PATTERNS = {
    "grid", "rectilinear", "gyroid", "honeycomb", "cubic", "line", "triangles"
}

FILAMENT_CATALOG = {
    "pla_basic": {
        "display_name": "PLA Basic",
        "cost_per_kg": 20.0,
        "density_g_cm3": 1.24,
        "diameter_mm": 1.75,
        "currency": "USD",
    }
}

DEFAULT_FILAMENT_TYPE = "pla_basic"


def _extract_first_number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None
    return float(match.group(0))


def calculate_printing_cost(summary: dict, filament_cfg: dict) -> dict:
    filament_g = _extract_first_number(summary.get("filament_g"))
    filament_cm3 = _extract_first_number(summary.get("filament_cm3"))

    if filament_g is None and filament_cm3 is not None:
        filament_g = filament_cm3 * filament_cfg["density_g_cm3"]

    if filament_g is None:
        return {
            "estimated_material_cost": None,
            "currency": filament_cfg["currency"],
            "cost_per_kg": filament_cfg["cost_per_kg"],
            "filament_type": filament_cfg["display_name"],
            "note": "Cost could not be computed because filament usage was missing.",
        }

    cost = (filament_g / 1000.0) * filament_cfg["cost_per_kg"]
    return {
        "estimated_material_cost": round(cost, 4),
        "currency": filament_cfg["currency"],
        "cost_per_kg": filament_cfg["cost_per_kg"],
        "filament_g_used": round(filament_g, 4),
        "filament_type": filament_cfg["display_name"],
    }


def parse_gcode_summary(gcode_path: Path):
    result = {
        "filament_mm": None,
        "filament_cm3": None,
        "filament_g": None,
        "total_filament_cost": None,
        "estimated_print_time": None,
        "estimated_first_layer_time": None,
    }

    patterns = {
        "filament_mm": r"^; filament used \[mm\] = (.+)$",
        "filament_cm3": r"^; filament used \[cm3\] = (.+)$",
        "filament_g": r"^; filament used \[g\] = (.+)$",
        "total_filament_cost": r"^; total filament cost = (.+)$",
        "estimated_print_time": r"^; estimated printing time \(normal mode\) = (.+)$",
        "estimated_first_layer_time": r"^; estimated first layer printing time \(normal mode\) = (.+)$",
    }

    with gcode_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            for key, pat in patterns.items():
                m = re.match(pat, line)
                if m:
                    result[key] = m.group(1).strip()

    return result


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/slice")
async def slice_quote(
    file: UploadFile = File(...),
    layer_height: float = Form(...),
    fill_density: str = Form(...),
    fill_pattern: str = Form(...),
    perimeters: int = Form(...),
    support_material: int = Form(...),
    filament_type: str = Form(DEFAULT_FILAMENT_TYPE),
):
    if not file.filename.lower().endswith(".stl"):
        raise HTTPException(status_code=400, detail="Only STL files are allowed")

    if not (0.05 <= layer_height <= 0.4):
        raise HTTPException(status_code=400, detail="layer_height must be 0.05 to 0.4")

    if not fill_density.endswith("%"):
        raise HTTPException(status_code=400, detail="fill_density must look like 15%")
    try:
        density_num = float(fill_density[:-1])
    except ValueError:
        raise HTTPException(status_code=400, detail="fill_density must be numeric percent")
    if not (0 <= density_num <= 100):
        raise HTTPException(status_code=400, detail="fill_density must be 0% to 100%")

    if fill_pattern not in ALLOWED_PATTERNS:
        raise HTTPException(
            status_code=400,
            detail=f"fill_pattern must be one of: {sorted(ALLOWED_PATTERNS)}",
        )

    if not (1 <= perimeters <= 10):
        raise HTTPException(status_code=400, detail="perimeters must be 1 to 10")

    if support_material not in (0, 1):
        raise HTTPException(status_code=400, detail="support_material must be 0 or 1")

    if filament_type not in FILAMENT_CATALOG:
        raise HTTPException(
            status_code=400,
            detail=f"filament_type must be one of: {sorted(FILAMENT_CATALOG.keys())}",
        )

    filament_cfg = FILAMENT_CATALOG[filament_type]

    job_id = str(uuid.uuid4())
    stl_path = UPLOAD_DIR / f"{job_id}.stl"
    gcode_path = OUT_DIR / f"{job_id}.gcode"

    try:
        with stl_path.open("wb") as out_f:
            shutil.copyfileobj(file.file, out_f)

        cmd = [
            "prusa-slicer",
            "--export-gcode",
            "--output", str(gcode_path),
            "--layer-height", str(layer_height),
            "--fill-density", fill_density,
            "--fill-pattern", fill_pattern,
            "--perimeters", str(perimeters),
        ]

        if support_material == 1:
            cmd.append("--support-material")

        cmd.append(str(stl_path))

        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Slicing failed",
                    "stderr": proc.stderr[-2000:],
                },
            )

        summary = parse_gcode_summary(gcode_path)
        pricing = calculate_printing_cost(summary, filament_cfg)

        return {
            "job_id": job_id,
            "inputs": {
                "layer_height": layer_height,
                "fill_density": fill_density,
                "fill_pattern": fill_pattern,
                "perimeters": perimeters,
                "support_material": support_material,
                "filament_type": filament_type,
            },
            "quote": summary,
            "pricing": pricing,
        }
    finally:
        if stl_path.exists():
            stl_path.unlink(missing_ok=True)
        if gcode_path.exists():
            gcode_path.unlink(missing_ok=True)
```

---

## Key Regex Patterns (TESTED — DO NOT MODIFY)

These patterns match actual PrusaSlicer 2.7+ G-code output:

```python
patterns = {
    "filament_mm": r"^; filament used \[mm\] = (.+)$",
    "filament_cm3": r"^; filament used \[cm3\] = (.+)$",
    "filament_g": r"^; filament used \[g\] = (.+)$",
    "total_filament_cost": r"^; total filament cost = (.+)$",
    "estimated_print_time": r"^; estimated printing time \(normal mode\) = (.+)$",
    "estimated_first_layer_time": r"^; estimated first layer printing time \(normal mode\) = (.+)$",
}
```

## PrusaSlicer CLI Pattern (TESTED — DO NOT MODIFY core structure)

```python
cmd = [
    "prusa-slicer",          # ← Change to PRUSASLICER_PATH from config
    "--export-gcode",
    "--output", str(gcode_path),
    "--layer-height", str(layer_height),
    "--fill-density", fill_density,   # ← Must include % sign: "15%"
    "--fill-pattern", fill_pattern,
    "--perimeters", str(perimeters),
]

# Boolean flag — NO value after it
if support_material:
    cmd.append("--support-material")

# STL path MUST be last
cmd.append(str(stl_path))
```
