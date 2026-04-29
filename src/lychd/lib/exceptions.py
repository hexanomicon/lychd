"""Lychd exception types.

Defines functions that translate service and repository exceptions into HTTP exceptions for the API.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, cast

from advanced_alchemy.exceptions import IntegrityError
from litestar.exceptions import (
    HTTPException,
    InternalServerException,
    NotFoundException,
    # REMOVED: PermissionDeniedException is no longer used
)
from litestar.exceptions.responses import (
    create_debug_response,  # type: ignore[reportUnknownVariableType]
    create_exception_response,  # type: ignore[reportUnknownVariableType]
)
from litestar.repository.exceptions import ConflictError, NotFoundError, RepositoryError
from litestar.status_codes import HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR
from structlog.contextvars import bind_contextvars

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.response import Response
    from litestar.types import Scope

# PRUNED: AuthorizationError removed from __all__
__all__ = (
    "ApplicationError",
    "HealthCheckConfigurationError",
    "after_exception_hook_handler",
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


async def after_exception_hook_handler(exc: Exception, _scope: Scope) -> None:
    """Essential for logging unexpected errors. KEEP."""
    if isinstance(exc, ApplicationError):
        return
    if isinstance(exc, HTTPException) and exc.status_code < HTTP_500_INTERNAL_SERVER_ERROR:
        return
    bind_contextvars(exc_info=sys.exc_info())


def exception_to_http_response(
    request: Request[Any, Any, Any],
    exc: ApplicationError | RepositoryError,
) -> Response[Any]:
    """Transform repository exceptions to HTTP exceptions."""
    http_exc: type[HTTPException]
    if isinstance(exc, NotFoundError):
        http_exc = NotFoundException
    elif isinstance(exc, ConflictError | RepositoryError | IntegrityError):
        http_exc = _HTTPConflictException
    else:
        http_exc = InternalServerException

    if request.app.debug and http_exc not in (NotFoundException,):
        return cast("Response[Any]", create_debug_response(request, exc))

    return cast("Response[Any]", create_exception_response(request, http_exc(detail=str(exc.__cause__))))
