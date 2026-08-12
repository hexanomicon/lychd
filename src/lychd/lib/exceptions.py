"""Lychd exception types.

Defines functions that translate service and repository exceptions into HTTP exceptions for the API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from advanced_alchemy.exceptions import NotFoundError, RepositoryError
from litestar.exceptions import (
    InternalServerException,
    NotFoundException,
)
from litestar.exceptions.responses import (
    create_exception_response,  # type: ignore[reportUnknownVariableType]
)

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.response import Response

__all__ = (
    "ApplicationError",
    "HealthCheckConfigurationError",
)


class ApplicationError(Exception):
    """Base exception type for the lib's custom exception types."""

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


class MissingDependencyError(ApplicationError, ImportError): ...


class HealthCheckConfigurationError(ApplicationError): ...


def exception_to_http_response(
    request: Request[Any, Any, Any],
    exc: ApplicationError | RepositoryError,
) -> Response[Any]:
    """Return the stable JSON error shape without exposing internal failure text.

    ``NotFoundError`` is the one repository condition with an explicit public
    meaning. Every other repository failure is ambiguous infrastructure or
    persistence truth, so it remains a generic server error rather than a false
    client conflict. ``ApplicationError`` retains its existing generic 500
    contract.
    """
    http_exc = NotFoundException(detail=exc.detail) if isinstance(exc, NotFoundError) else InternalServerException()

    return cast("Response[Any]", create_exception_response(request, http_exc))
