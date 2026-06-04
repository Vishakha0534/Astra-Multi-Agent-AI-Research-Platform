from __future__ import annotations

from http import HTTPStatus
from typing import Any


class AstraBaseException(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.error_code = error_code or self.__class__.error_code
        self.details = details or {}
        super().__init__(self.message)


# ─── 400 Bad Request ─────────────────────────────────────────────────────────

class BadRequestError(AstraBaseException):
    status_code = 400
    error_code = "BAD_REQUEST"
    message = "Bad request"


class ValidationError(AstraBaseException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


# ─── 401 Unauthorized ────────────────────────────────────────────────────────

class AuthenticationError(AstraBaseException):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    message = "Authentication failed"


class InvalidTokenError(AstraBaseException):
    status_code = 401
    error_code = "INVALID_TOKEN"
    message = "Invalid or expired token"


class TokenExpiredError(AstraBaseException):
    status_code = 401
    error_code = "TOKEN_EXPIRED"
    message = "Token has expired"


# ─── 403 Forbidden ───────────────────────────────────────────────────────────

class PermissionDeniedError(AstraBaseException):
    status_code = 403
    error_code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"


# ─── 404 Not Found ───────────────────────────────────────────────────────────

class NotFoundError(AstraBaseException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class UserNotFoundError(NotFoundError):
    error_code = "USER_NOT_FOUND"
    message = "User not found"


class ProjectNotFoundError(NotFoundError):
    error_code = "PROJECT_NOT_FOUND"
    message = "Project not found"


class ResearchJobNotFoundError(NotFoundError):
    error_code = "JOB_NOT_FOUND"
    message = "Research job not found"


class ReportNotFoundError(NotFoundError):
    error_code = "REPORT_NOT_FOUND"
    message = "Report not found"


class SourceNotFoundError(NotFoundError):
    error_code = "SOURCE_NOT_FOUND"
    message = "Source not found"


# ─── 409 Conflict ────────────────────────────────────────────────────────────

class ConflictError(AstraBaseException):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource already exists"


class EmailAlreadyExistsError(ConflictError):
    error_code = "EMAIL_ALREADY_EXISTS"
    message = "A user with this email already exists"


# ─── 422 Unprocessable Entity ────────────────────────────────────────────────

class UnprocessableError(AstraBaseException):
    status_code = 422
    error_code = "UNPROCESSABLE"
    message = "Cannot process the request"


# ─── 429 Too Many Requests ───────────────────────────────────────────────────

class RateLimitError(AstraBaseException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please slow down."


# ─── 503 Service Unavailable ─────────────────────────────────────────────────

class ServiceUnavailableError(AstraBaseException):
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service temporarily unavailable"


class DatabaseError(AstraBaseException):
    status_code = 503
    error_code = "DATABASE_ERROR"
    message = "Database operation failed"


class CacheError(AstraBaseException):
    status_code = 503
    error_code = "CACHE_ERROR"
    message = "Cache operation failed"


# ─── Business Logic Errors ───────────────────────────────────────────────────

class JobAlreadyRunningError(AstraBaseException):
    status_code = 409
    error_code = "JOB_ALREADY_RUNNING"
    message = "A research job is already running for this project"


class JobNotCancellableError(AstraBaseException):
    status_code = 409
    error_code = "JOB_NOT_CANCELLABLE"
    message = "This job cannot be cancelled in its current state"


class BudgetExceededError(AstraBaseException):
    status_code = 402
    error_code = "BUDGET_EXCEEDED"
    message = "Token budget exceeded for this job"
