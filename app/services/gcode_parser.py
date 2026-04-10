import re
from collections import deque
from pathlib import Path
from typing import Any


GCODE_PATTERNS = {
    "filament_mm": r"^; filament used \[mm\] = (.+)$",
    "filament_cm3": r"^; filament used \[cm3\] = (.+)$",
    "filament_g": r"^; filament used \[g\] = (.+)$",
    "total_filament_cost": r"^; total filament cost = (.+)$",
    "estimated_print_time": r"^; estimated printing time \(normal mode\) = (.+)$",
    "estimated_first_layer_time": r"^; estimated first layer printing time \(normal mode\) = (.+)$",
}

TAIL_LINES = 200


def _extract_first_number(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if match is None:
        return None
    return float(match.group(0))


def parse_time_to_hours(time_str: str | None) -> float | None:
    """Parse PrusaSlicer time strings like '1h 48m 29s', '1d 2h 30m', '56s' to hours."""
    if not time_str:
        return None
    total_seconds = 0.0
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*([dhms])", time_str):
        value = float(match.group(1))
        unit = match.group(2)
        total_seconds += value * units[unit]
    if total_seconds == 0:
        return None
    return round(total_seconds / 3600.0, 4)


def parse_gcode(gcode_path: Path) -> dict[str, Any]:
    """Parse a PrusaSlicer-produced gcode file for stats.

    Returns numeric filament values as floats, times as strings plus an
    ``estimated_print_time_hours`` float. Missing fields are returned as None.
    """
    raw: dict[str, str | None] = {key: None for key in GCODE_PATTERNS}

    with gcode_path.open("r", encoding="utf-8", errors="ignore") as f:
        tail = deque(f, maxlen=TAIL_LINES)

    for line in tail:
        line = line.rstrip("\n")
        for key, pattern in GCODE_PATTERNS.items():
            if raw[key] is not None:
                continue
            match = re.match(pattern, line)
            if match:
                raw[key] = match.group(1).strip()

    result: dict[str, Any] = {
        "filament_mm": _extract_first_number(raw["filament_mm"]),
        "filament_cm3": _extract_first_number(raw["filament_cm3"]),
        "filament_g": _extract_first_number(raw["filament_g"]),
        "total_filament_cost": _extract_first_number(raw["total_filament_cost"]),
        "estimated_print_time": raw["estimated_print_time"],
        "estimated_print_time_hours": parse_time_to_hours(raw["estimated_print_time"]),
        "first_layer_time": raw["estimated_first_layer_time"],
    }
    return result
