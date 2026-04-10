from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FillPattern(str, Enum):
    grid = "grid"
    gyroid = "gyroid"
    honeycomb = "honeycomb"
    rectilinear = "rectilinear"
    triangles = "triangles"
    cubic = "cubic"
    line = "line"
    concentric = "concentric"


class FilamentType(str, Enum):
    PLA = "PLA"
    ABS = "ABS"
    PETG = "PETG"
    TPU = "TPU"
    Nylon = "Nylon"
    ASA = "ASA"
    PC = "PC"
    PVA = "PVA"


class JobStatus(str, Enum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SliceRequest(BaseModel):
    layer_height: float = Field(
        0.2, ge=0.05, le=0.6, description="Layer height in mm", examples=[0.2]
    )
    fill_density: int = Field(
        20, ge=0, le=100, description="Infill density as a percent integer", examples=[20]
    )
    fill_pattern: FillPattern = Field(
        FillPattern.grid, description="Infill pattern", examples=["grid"]
    )
    perimeters: int = Field(
        3, ge=1, le=10, description="Number of perimeter shells", examples=[3]
    )
    support_material: bool = Field(
        False, description="Generate support material", examples=[False]
    )
    filament_type: FilamentType = Field(
        FilamentType.PLA, description="Filament material", examples=["PLA"]
    )
    machine_rate_per_hour: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Override machine rate in USD/hour"
    )
    markup_multiplier: Optional[float] = Field(
        None, ge=1.0, le=10.0, description="Override markup multiplier"
    )


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field("ok", description="Service status")
    version: str = Field(..., description="API version", examples=["1.0.0"])
    timestamp: datetime = Field(..., description="Current server time (UTC)")


class QuoteData(BaseModel):
    filament_mm: Optional[float] = None
    filament_cm3: Optional[float] = None
    filament_g: Optional[float] = None
    estimated_print_time: Optional[str] = None
    estimated_print_time_hours: Optional[float] = None
    first_layer_time: Optional[str] = None


class PricingData(BaseModel):
    material_cost: float
    machine_cost: float
    total_cost: float
    customer_price: float
    currency: str = "USD"


class PricingDetails(BaseModel):
    filament_type: str
    cost_per_kg: float
    density_g_per_cm3: float
    machine_rate_per_hour: float
    markup_multiplier: float


class ParametersData(BaseModel):
    layer_height: float
    fill_density: int
    fill_pattern: str
    perimeters: int
    support_material: bool
    filament_type: str


class SliceResponse(BaseModel):
    request_id: UUID
    job_id: UUID
    status: JobStatus
    quote: QuoteData
    pricing: PricingData
    details: PricingDetails
    parameters: ParametersData


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    status: JobStatus
    file_name: str
    filament_type: Optional[str] = None
    customer_price: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    pagination: PaginationMeta


class JobResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    file_name: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    parameters: ParametersData
    quote: Optional[QuoteData] = None
    pricing: Optional[PricingData] = None
    details: Optional[PricingDetails] = None
    error_message: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
