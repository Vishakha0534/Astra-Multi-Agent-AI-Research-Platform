from __future__ import annotations

from http import HTTPStatus


class AstraBaseException(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class AuthenticationError(AstraBaseException):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    message = "Authentication failed"


class AuthorizationError(AstraBaseException):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action"


class NotFoundError(AstraBaseException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(AstraBaseException):
    status_code = 409

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(message)


class ValidationError(AstraBaseException):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class InvalidTokenError(AstraBaseException):
    status_code = 401
    error_code = "INVALID_TOKEN"
    message = "Token is invalid"


class TokenExpiredError(AstraBaseException):
    status_code = 401
    error_code = "TOKEN_EXPIRED"
    message = "Token has expired"


class RateLimitError(AstraBaseException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests"
