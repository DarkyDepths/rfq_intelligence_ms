"""
exceptions.py — Custom Exception Classes

BACAB Layer: Utils (cross-cutting)

Responsibility:
    Defines the exception hierarchy used across the service.
    The global exception handler in app.py catches AppError and its
    subclasses and converts them to clean JSON responses.

Current status: COMPLETE for skeleton.
"""


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)


class BadRequestError(AppError):
    """Raised when the request is malformed or invalid."""

    def __init__(self, message: str = "Bad request"):
        super().__init__(message=message, status_code=400)
