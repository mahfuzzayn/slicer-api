from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AppError):
    status_code = 401
    code = "INVALID_API_KEY"
    message = "The provided API key is not valid or has been deactivated"


class AuthorizationError(AppError):
    status_code = 403
    code = "ACCOUNT_INACTIVE"
    message = "Your account has been deactivated"


class ValidationError(AppError):
    status_code = 400
    code = "INVALID_PARAMETER"
    message = "One or more parameters are invalid"


class NotFoundError(AppError):
    status_code = 404
    code = "JOB_NOT_FOUND"
    message = "Resource not found"


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    message = "You have exceeded your monthly request quota"


class SlicerError(AppError):
    status_code = 500
    code = "SLICER_ERROR"
    message = "PrusaSlicer failed to process the file"


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code_map = {
        400: "INVALID_PARAMETER",
        401: "MISSING_API_KEY",
        403: "ACCOUNT_INACTIVE",
        404: "JOB_NOT_FOUND",
        413: "FILE_TOO_LARGE",
        429: "RATE_LIMIT_EXCEEDED",
    }
    code = code_map.get(exc.status_code, "INTERNAL_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = exc.detail if isinstance(exc.detail, dict) else {}
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, message, details),
    )


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_body(
            "VALIDATION_ERROR",
            "Request body failed validation",
            {"errors": exc.errors()},
        ),
    )


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
