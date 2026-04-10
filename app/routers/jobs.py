import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.schemas import (
    JobListItem,
    JobListResponse,
    JobResponse,
    JobStatus,
    PaginationMeta,
    ParametersData,
    PricingData,
    PricingDetails,
    QuoteData,
)
from app.models.tables import Job, User
from app.utils.errors import NotFoundError


router = APIRouter(tags=["jobs"])


def _list_item(job: Job) -> JobListItem:
    result = job.result_json or {}
    pricing = result.get("pricing") or {}
    details = result.get("details") or {}
    return JobListItem(
        job_id=job.id,
        status=JobStatus(job.status),
        file_name=job.file_name,
        filament_type=details.get("filament_type"),
        customer_price=pricing.get("customer_price"),
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


def _full_response(job: Job) -> JobResponse:
    params = job.parameters_json or {}
    result = job.result_json or {}

    parameters = ParametersData(
        layer_height=params.get("layer_height", 0.2),
        fill_density=params.get("fill_density", 20),
        fill_pattern=str(params.get("fill_pattern", "grid")),
        perimeters=params.get("perimeters", 3),
        support_material=params.get("support_material", False),
        filament_type=str(params.get("filament_type", "PLA")),
    )

    quote = QuoteData(**result["quote"]) if result.get("quote") else None
    pricing = PricingData(**result["pricing"]) if result.get("pricing") else None
    details = PricingDetails(**result["details"]) if result.get("details") else None

    return JobResponse(
        job_id=job.id,
        status=JobStatus(job.status),
        file_name=job.file_name,
        created_at=job.created_at,
        completed_at=job.completed_at,
        parameters=parameters,
        quote=quote,
        pricing=pricing,
        details=details,
        error_message=job.error_message,
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: JobStatus | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobListResponse:
    query = db.query(Job).filter(Job.user_id == current_user.id)
    if status is not None:
        query = query.filter(Job.status == status.value)

    total = query.count()
    rows = (
        query.order_by(Job.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return JobListResponse(
        jobs=[_list_item(job) for job in rows],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=max(1, math.ceil(total / per_page)) if total else 0,
        ),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .filter(Job.user_id == current_user.id)
        .one_or_none()
    )
    if job is None:
        raise NotFoundError(message="Job not found")
    return _full_response(job)
