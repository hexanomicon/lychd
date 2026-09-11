"""Authenticate the local operator before assigning the fixed local Sigil.

This narrow possession check is not remote Ward identity or object authorization.
Static assets and schema documents remain public; protected requests have no
cookie, network-location, or browser-header fallback.
"""

from __future__ import annotations

import base64
import binascii
import hmac
from typing import TYPE_CHECKING, Any

from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import AbstractAuthenticationMiddleware, AuthenticationResult

from lychd.domain.codex.sigil import default_local_sigil

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.connection import ASGIConnection
    from litestar.types import ASGIApp

__all__ = ["SigilAuthMiddleware", "sigil_auth_middleware"]
_MAX_AUTHORIZATION_BYTES = 2048


class SigilAuthMiddleware(AbstractAuthenticationMiddleware):
    """Require the dedicated local password on every protected request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        access_password: str,
        allowed_origins: Sequence[str] = (),
    ) -> None:
        """Bind one startup credential generation and exact development origins."""
        if not access_password:
            msg = "Required local access password is unavailable."
            raise ValueError(msg)
        super().__init__(app, exclude=[r"^/_app(?:/|$)", r"^/schema(?:/|$)"])
        self._password = access_password.encode("utf-8")
        self._allowed_origins = frozenset(allowed_origins)

    async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
        """Authenticate possession, then refuse foreign-origin mutations."""
        values = [value for name, value in connection.scope["headers"] if name.lower() == b"authorization"]
        valid = False
        if len(values) == 1 and len(values[0]) <= _MAX_AUTHORIZATION_BYTES:
            scheme, separator, encoded = values[0].partition(b" ")
            if separator and scheme.lower() == b"basic":
                try:
                    username, colon, password = base64.b64decode(encoded, validate=True).partition(b":")
                except (ValueError, binascii.Error):
                    pass
                else:
                    valid = username == b"magus" and bool(colon) and hmac.compare_digest(password, self._password)
        if not valid:
            raise NotAuthorizedException(
                detail="Local operator authentication is required.",
                headers={"WWW-Authenticate": 'Basic realm="LychD local operator", charset="UTF-8"'},
            )
        if connection.scope["type"] == ScopeType.HTTP and connection.scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            origins = [value for name, value in connection.scope["headers"] if name.lower() == b"origin"]
            expected = f"{connection.scope['scheme']}://{connection.headers.get('host', '')}"
            if origins and (
                len(origins) != 1 or origins[0].decode("latin-1") not in {expected, *self._allowed_origins}
            ):
                raise PermissionDeniedException(detail="This request Origin is not admitted.")
        return AuthenticationResult(user=default_local_sigil(), auth=None)


def sigil_auth_middleware(*, access_password: str, allowed_origins: Sequence[str] = ()) -> DefineMiddleware:
    """Build local operator admission without reading ambient secrets."""
    if not access_password:
        msg = "Required local access password is unavailable."
        raise ValueError(msg)
    return DefineMiddleware(SigilAuthMiddleware, access_password=access_password, allowed_origins=allowed_origins)
