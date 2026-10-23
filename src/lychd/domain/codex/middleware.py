"""Authenticate the local operator before assigning the fixed local Sigil.

This narrow possession check is not remote Ward identity or object authorization.
Static assets and schema documents remain public; protected requests have no
cookie, network-location, or browser-header fallback.
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import TYPE_CHECKING, Any

from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import AbstractAuthenticationMiddleware, AuthenticationResult

from lychd.config.constants import STOP_ADMISSION_PATH
from lychd.domain.codex.local_access import LocalOperatorAccess
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
        access_password: str | None = None,
        operator_access: LocalOperatorAccess | None = None,
        allowed_origins: Sequence[str] = (),
    ) -> None:
        """Bind one startup credential generation and exact development origins."""
        super().__init__(
            app,
            exclude=[r"^/_app(?:/|$)", r"^/schema(?:/|$)", rf"^{re.escape(STOP_ADMISSION_PATH)}$"],
        )
        self._operator_access = _operator_access(access_password, operator_access)
        self._allowed_origins = frozenset(allowed_origins)

    async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
        """Authenticate possession, then refuse foreign-origin mutations."""
        values = [value for name, value in connection.scope["headers"] if name.lower() == b"authorization"]
        authentication = None
        if len(values) == 1 and len(values[0]) <= _MAX_AUTHORIZATION_BYTES:
            scheme, separator, encoded = values[0].partition(b" ")
            if separator and scheme.lower() == b"basic":
                try:
                    username, colon, password = base64.b64decode(encoded, validate=True).partition(b":")
                except (ValueError, binascii.Error):
                    pass
                else:
                    if colon:
                        authentication = self._operator_access.authenticate(username=username, password=password)
        if authentication is None:
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
        return AuthenticationResult(user=default_local_sigil(), auth=authentication)


def _operator_access(password: str | None, access: LocalOperatorAccess | None) -> LocalOperatorAccess:
    if access is not None:
        if password is not None:
            msg = "Local access accepts one credential owner."
            raise ValueError(msg)
        return access
    return LocalOperatorAccess(access_password=password or "")


def sigil_auth_middleware(
    *,
    access_password: str | None = None,
    operator_access: LocalOperatorAccess | None = None,
    allowed_origins: Sequence[str] = (),
) -> DefineMiddleware:
    """Build local operator admission without reading ambient secrets."""
    access = _operator_access(access_password, operator_access)
    return DefineMiddleware(SigilAuthMiddleware, operator_access=access, allowed_origins=allowed_origins)
