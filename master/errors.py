"""Error/exception classes for Master API."""

from __future__ import annotations


class MasterAPIError(Exception):
    """Base exception for Master API."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ExperimentNotFoundError(MasterAPIError):
    """Experiment not found in database."""

    def __init__(self, exp_id: str):
        super().__init__(f"Experiment not found: {exp_id}", status_code=404)


class CircularDependencyError(MasterAPIError):
    """Circular dependency detected in lineage."""

    def __init__(self, details: str = ""):
        msg = "Circular dependency in checkpoint merge" + (f": {details}" if details else "")
        super().__init__(msg, status_code=409)


class ConflictError(MasterAPIError):
    """Resource conflict."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class ValidationError(MasterAPIError):
    """Validation failed."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class InternalServerError(MasterAPIError):
    """Internal server error."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)
