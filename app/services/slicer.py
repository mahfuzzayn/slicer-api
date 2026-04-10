import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings
from app.utils.errors import SlicerError


SLICE_TIMEOUT_SECONDS = 120


def slice_file(stl_path: Path, params: dict[str, Any]) -> Path:
    """Run PrusaSlicer on the given STL file and return the output gcode path.

    The STL path must be the LAST argument in the command list (MVP-tested).
    support_material is a boolean flag with no value — present means enabled.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="slicer_"))
    gcode_path = tmp_dir / f"{stl_path.stem}.gcode"

    fill_density_int = int(params["fill_density"])
    fill_density_str = f"{fill_density_int}%"

    cmd: list[str] = [
        settings.PRUSASLICER_PATH,
        "--export-gcode",
        "--output",
        str(gcode_path),
        "--layer-height",
        str(params["layer_height"]),
        "--fill-density",
        fill_density_str,
        "--fill-pattern",
        str(params["fill_pattern"]),
        "--perimeters",
        str(params["perimeters"]),
    ]

    if params.get("support_material"):
        cmd.append("--support-material")

    cmd.append(str(stl_path))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SLICE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise SlicerError(
            message="Slicing timed out after 120 seconds",
            details={"timeout_seconds": SLICE_TIMEOUT_SECONDS},
        ) from exc
    except FileNotFoundError as exc:
        raise SlicerError(
            message=f"PrusaSlicer binary not found at {settings.PRUSASLICER_PATH}",
        ) from exc

    if proc.returncode != 0:
        raise SlicerError(
            message="PrusaSlicer failed",
            details={"stderr": proc.stderr[-2000:]},
        )

    if not gcode_path.exists():
        raise SlicerError(
            message="PrusaSlicer did not produce a gcode file",
            details={"stderr": proc.stderr[-2000:]},
        )

    return gcode_path
