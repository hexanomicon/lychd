"""`SigilAuthMiddleware` — stamp the request's `connection.user` with the Sigil (§3.3).

v1 single-identity Ward: every request carries the settings sigil
(`get_settings().sigil`). The guards (`guards.py`) then rule on its scopes. Static
and OpenAPI schema paths are excluded so unauthenticated asset serving still works.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import AbstractAuthenticationMiddleware, AuthenticationResult

from lychd.config.settings import get_settings
from lychd.domain.codex.sigil import Sigil

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["SigilAuthMiddleware", "sigil_auth_middleware"]


class SigilAuthMiddleware(AbstractAuthenticationMiddleware):
    """Set `connection.user` to the process Sigil built from settings (v1 Ward)."""

    async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
        """Return the settings-derived Sigil as the connection user (no secret read)."""
        _ = connection
        sigil_settings = get_settings().sigil
        sigil = Sigil(name=sigil_settings.name, scopes=frozenset(sigil_settings.scopes))
        return AuthenticationResult(user=sigil, auth=None)


def sigil_auth_middleware() -> DefineMiddleware:
    """Return the sigil auth middleware, excluding static + schema paths."""
    return DefineMiddleware(SigilAuthMiddleware, exclude=["^/static", "^/schema"])
