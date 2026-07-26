"""`SigilAuthMiddleware` — stamp requests with the loopback bootstrap Sigil.

This is not caller authentication. IAM replaces ``default_local_sigil()`` with
credential-backed resolution before LychD accepts remote traffic. Compiled client assets and
OpenAPI schema paths are excluded from the bootstrap middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import AbstractAuthenticationMiddleware, AuthenticationResult

from lychd.domain.codex.sigil import Sigil, default_local_sigil

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["SigilAuthMiddleware", "local_sigil", "sigil_auth_middleware"]


def local_sigil() -> Sigil:
    """Return the bootstrap Sigil; a narrow seam for focused tests and future IAM."""
    return default_local_sigil()


class SigilAuthMiddleware(AbstractAuthenticationMiddleware):
    """Set `connection.user` to the fixed loopback bootstrap Sigil."""

    async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
        """Return the bootstrap Sigil as the connection user (no secret read)."""
        _ = connection
        return AuthenticationResult(user=local_sigil(), auth=None)


def sigil_auth_middleware() -> DefineMiddleware:
    """Return the sigil auth middleware, excluding client assets and schema paths."""
    return DefineMiddleware(SigilAuthMiddleware, exclude=["^/_app", "^/schema"])
