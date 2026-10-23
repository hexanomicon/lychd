"""Inert machine admission for the host-owned installation stop operation.

The HTTP boundary verifies the signed exchange and current application admission.
It neither inspects host binding generations nor acquires lifecycle locks or
performs the eventual stop; those remain the host caller's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from litestar import Request, post
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.response import Response

from lychd.config.constants import STOP_ADMISSION_LAUNCHER_PROFILE, STOP_ADMISSION_PATH
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.system.operator.admission import (
    MAX_ADMISSION_BODY_BYTES,
    StopAdmissionError,
    StopAdmissionProtocol,
)


@dataclass(slots=True)
class StopAdmissionState:
    """Independent production-publication and owned-native launcher admission gates."""

    protocol: StopAdmissionProtocol
    access: LocalOperatorAccess
    authentication: LocalOperatorAuthentication
    production: bool
    published: bool = False
    _launcher_profile: str | None = field(default=None, init=False, repr=False)

    @property
    def launcher_profile(self) -> str | None:
        """Expose the armed mechanism without deriving it from environment or publication."""
        return self._launcher_profile

    def arm_native_launcher(self) -> None:
        """Arm the production app captured by the owned native entrypoint."""
        if self.production:
            self._launcher_profile = STOP_ADMISSION_LAUNCHER_PROFILE

    def publish(self) -> None:
        """Open admission only for the production service publication."""
        self.published = self.production

    def withdraw(self) -> None:
        """Withdraw publication and launcher authority before any retirement await."""
        self.published = False
        self._launcher_profile = None

    def admit(self, request: httpx.Request) -> httpx.Response:
        """Verify possession before consulting the live credential owner."""
        reply = self.protocol.admit(request)
        if (
            not self.production
            or not self.published
            or self._launcher_profile != STOP_ADMISSION_LAUNCHER_PROFILE
            or not self.access.current(self.authentication)
        ):
            raise PermissionDeniedException(detail="Local stop admission is unavailable.")
        return reply


@post(
    STOP_ADMISSION_PATH,
    include_in_schema=False,
    request_max_body_size=MAX_ADMISSION_BODY_BYTES,
)
async def stop_admission(request: Request[Any, Any, Any]) -> Response[bytes]:
    """Return a signed admission reply without granting request identity or effects."""
    body = await request.body()
    scope = request.scope
    if "raw_path" not in scope or scope["raw_path"] != STOP_ADMISSION_PATH.encode("ascii"):
        raise NotAuthorizedException(detail="Local stop admission is refused.")
    try:
        query = scope["query_string"]
        target = f"{scope['scheme']}://{request.headers.get('host', '')}{STOP_ADMISSION_PATH}"
        if query:
            target += "?" + query.decode("ascii")
        message = httpx.Request(scope["method"], target, headers=list(scope["headers"]), content=body)
        admission: StopAdmissionState = request.app.state.stop_admission
        reply = admission.admit(message)
    except (StopAdmissionError, UnicodeDecodeError, httpx.InvalidURL):
        raise NotAuthorizedException(detail="Local stop admission is refused.") from None
    return Response(content=reply.content, status_code=reply.status_code, headers=dict(reply.headers))
