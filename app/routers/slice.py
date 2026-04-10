import shutil
import tempfile
import time
import uuid
from calendar import monthrange
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.schemas import (
    FilamentType,
    FillPattern,
    JobStatus,
    ParametersData,
    PricingData,
    PricingDetails,
    QuoteData,
    SliceRequest,
    SliceResponse,
)
from app.models.tables import Filament, Job, User
from app.services.gcode_parser import parse_gcode
from app.services.pricing import calculate_cost
from app.services.slicer import slice_file
from app.utils.errors import (
    AppError,
    NotFoundError,
    RateLimitError,
    SlicerError,
    ValidationError,
)


router = APIRouter(tags=["slice"])

STL_MAGIC_BINARY_HEADER_LEN = 80


def _month_window() -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    last_day = monthrange(now.year, now.month)[1]
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1)
    else:
        end = datetime(now.year, now.month + 1, 1)
    return start, end


def _validate_stl(file_bytes: bytes, filename: str) -> None:
    if not filename.lower().endswith(".stl"):
        raise ValidationError(
            message="Only .stl files are accepted",
            code="INVALID_FILE",
        )
    if len(file_bytes) == 0:
        raise ValidationError(message="Uploaded file is empty", code="INVALID_FILE")
    head = file_bytes[:5].lower()
    if head.startswith(b"solid"):
        return
    if len(file_bytes) >= STL_MAGIC_BINARY_HEADER_LEN + 4:
        return
    raise ValidationError(
        message="File does not look like a valid STL",
        code="INVALID_FILE",
    )


@router.post("/slice", response_model=SliceResponse)
async def slice_endpoint(
    response: Response,
    file: UploadFile = File(...),
    layer_height: float = Form(0.2),
    fill_density: int = Form(20),
    fill_pattern: FillPattern = Form(FillPattern.grid),
    perimeters: int = Form(3),
    support_material: bool = Form(False),
    filament_type: FilamentType = Form(FilamentType.PLA),
    machine_rate_per_hour: float | None = Form(None),
    markup_multiplier: float | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SliceResponse:
    params = SliceRequest(
        layer_height=layer_height,
        fill_density=fill_density,
        fill_pattern=fill_pattern,
        perimeters=perimeters,
        support_material=support_material,
        filament_type=filament_type,
        machine_rate_per_hour=machine_rate_per_hour,
        markup_multiplier=markup_multiplier,
    )

    plan = current_user.plan
    max_file_size_mb = plan.max_file_size_mb if plan else settings.MAX_FILE_SIZE_MB
    requests_per_month = plan.requests_per_month if plan else 10_000

    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > max_file_size_mb:
        raise AppError(
            message="File size exceeds your plan's limit",
            code="FILE_TOO_LARGE",
            status_code=413,
            details={
                "file_size_mb": round(file_size_mb, 4),
                "max_allowed_mb": max_file_size_mb,
            },
        )

    _validate_stl(file_bytes, file.filename or "")

    month_start, month_end = _month_window()
    used_this_month = (
        db.query(Job)
        .filter(Job.user_id == current_user.id)
        .filter(Job.created_at >= month_start)
        .filter(Job.created_at < month_end)
        .count()
    )
    if used_this_month >= requests_per_month:
        raise RateLimitError(
            details={
                "limit": requests_per_month,
                "used": used_this_month,
                "resets_at": month_end.isoformat() + "Z",
            }
        )

    request_id = uuid.uuid4()

    filament: Filament | None = (
        db.query(Filament).filter(Filament.type == params.filament_type.value).one_or_none()
    )
    if filament is None:
        raise NotFoundError(
            message=f"Filament '{params.filament_type.value}' not found",
            code="INVALID_PARAMETER",
            status_code=400,
        )

    job = Job(
        user_id=current_user.id,
        request_id=request_id,
        status="running",
        file_name=file.filename or "upload.stl",
        file_size_bytes=len(file_bytes),
        parameters_json=params.model_dump(mode="json"),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    tmp_dir = Path(tempfile.mkdtemp(prefix="slice_in_"))
    stl_path = tmp_dir / (file.filename or f"{job.id}.stl")
    gcode_path: Path | None = None
    start_time = time.monotonic()

    try:
        stl_path.write_bytes(file_bytes)

        slice_params = params.model_dump()
        slice_params["fill_pattern"] = params.fill_pattern.value

        gcode_path = slice_file(stl_path, slice_params)
        parsed = parse_gcode(gcode_path)
        pricing = calculate_cost(
            parsed,
            filament,
            machine_rate=params.machine_rate_per_hour,
            markup=params.markup_multiplier,
        )

        quote = QuoteData(
            filament_mm=parsed.get("filament_mm"),
            filament_cm3=parsed.get("filament_cm3"),
            filament_g=round(pricing["filament_grams"], 4),
            estimated_print_time=parsed.get("estimated_print_time"),
            estimated_print_time_hours=parsed.get("estimated_print_time_hours"),
            first_layer_time=parsed.get("first_layer_time"),
        )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        result_payload = {
            "quote": quote.model_dump(mode="json"),
            "pricing": pricing["pricing"],
            "details": pricing["details"],
            "parameters": params.model_dump(mode="json"),
        }

        job.status = "succeeded"
        job.result_json = result_payload
        job.completed_at = datetime.utcnow()
        job.processing_time_ms = elapsed_ms
        db.commit()

        response.headers["X-Request-ID"] = str(request_id)
        response.headers["X-RateLimit-Limit"] = str(requests_per_month)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, requests_per_month - used_this_month - 1)
        )
        response.headers["X-RateLimit-Reset"] = month_end.isoformat() + "Z"

        return SliceResponse(
            request_id=request_id,
            job_id=job.id,
            status=JobStatus.succeeded,
            quote=quote,
            pricing=PricingData(**pricing["pricing"]),
            details=PricingDetails(**pricing["details"]),
            parameters=ParametersData(
                layer_height=params.layer_height,
                fill_density=params.fill_density,
                fill_pattern=params.fill_pattern.value,
                perimeters=params.perimeters,
                support_material=params.support_material,
                filament_type=params.filament_type.value,
            ),
        )
    except AppError as exc:
        job.status = "failed"
        job.error_message = exc.message
        job.completed_at = datetime.utcnow()
        db.commit()
        raise
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise SlicerError(message=str(exc)) from exc
    finally:
        try:
            if stl_path.exists():
                stl_path.unlink(missing_ok=True)
        except OSError:
            pass
        if gcode_path is not None:
            try:
                shutil.rmtree(gcode_path.parent, ignore_errors=True)
            except OSError:
                pass
        shutil.rmtree(tmp_dir, ignore_errors=True)
