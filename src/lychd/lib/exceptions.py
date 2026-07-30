"""Lychd exception types.

Defines functions that translate service and repository exceptions into HTTP exceptions for the API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from advanced_alchemy.exceptions import NotFoundError, RepositoryError
from litestar.exceptions import (
    HTTPException,
    InternalServerException,
    NotFoundException,
    # REMOVED: PermissionDeniedException is no longer used
)
from litestar.exceptions.responses import (
    create_exception_response,  # type: ignore[reportUnknownVariableType]
)
from litestar.status_codes import HTTP_409_CONFLICT

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.response import Response

# PRUNED: AuthorizationError removed from __all__
__all__ = (
    "ApplicationError",
    "HealthCheckConfigurationError",
)


class ApplicationError(Exception):
    """Base exception type for the lib's custom exception types."""

    # ... (this class remains the same)
    detail: str

    def __init__(self, *args: Any, detail: str = "") -> None:
        """Initialize ApplicationError."""
        str_args = [str(arg) for arg in args if arg]
        if not detail:
            if str_args:
                detail, *str_args = str_args
            elif hasattr(self, "detail"):
                detail = self.detail
        self.detail = detail
        super().__init__(*str_args)

    def __repr__(self) -> str:
        """Return a string representation of the exception."""
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__

    def __str__(self) -> str:
        """Return the string representation of the exception."""
        return " ".join((*self.args, self.detail)).strip()


# NOTE: These smaller exception classes are still useful for organization.
class MissingDependencyError(ApplicationError, ImportError): ...


class HealthCheckConfigurationError(ApplicationError): ...


class _HTTPConflictException(HTTPException):
    """Request conflict with the current state of the target resource."""

    status_code = HTTP_409_CONFLICT


def exception_to_http_response(
    request: Request[Any, Any, Any],
    exc: ApplicationError | RepositoryError,
) -> Response[Any]:
    """Transform repository exceptions to HTTP exceptions."""
    http_exc: type[HTTPException]
    if isinstance(exc, NotFoundError):
        http_exc = NotFoundException
    elif isinstance(exc, RepositoryError):
        http_exc = _HTTPConflictException
    else:
        http_exc = InternalServerException

    detail = str(exc.__cause__) if exc.__cause__ is not None else str(exc)
    return cast("Response[Any]", create_exception_response(request, http_exc(detail=detail)))
