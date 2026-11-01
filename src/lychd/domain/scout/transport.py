"""Scout transport values and a mandatory synchronous network handoff port."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, Protocol

_MIN_HTTP_STATUS = 100
_MAX_HTTP_STATUS = 599


class FetchCode(StrEnum):
    """Closed acquisition outcomes without foreign diagnostics or locators."""

    CONFIG = "config"
    INPUT = "input"
    DNS = "dns"
    DESTINATION = "destination"
    EGRESS = "egress"
    CONNECT = "connect"
    PEER = "peer"
    TRANSPORT = "transport"
    TLS = "tls"
    TIMEOUT = "timeout"
    LIMIT = "limit"
    PROTOCOL = "protocol"
    MEDIA = "media"
    ENCODING = "encoding"
    REDIRECT = "redirect"


class FetchError(ValueError):
    """A content-free refusal with an optional observed HTTP status."""

    def __init__(self, code: FetchCode, *, http_status: int | None = None) -> None:
        """Keep only a closed outcome and a valid numeric status, never content."""
        if http_status is not None and (
            type(http_status) is not int or not _MIN_HTTP_STATUS <= http_status <= _MAX_HTTP_STATUS
        ):
            message = "Scout HTTP status is invalid."
            raise ValueError(message)
        self.code = code
        self.http_status = http_status
        super().__init__(f"Scout fetch refused: {code.value}.")


@dataclass(frozen=True, slots=True)
class NetworkTarget:
    """An exact contacted peer; this value confers no disclosure authority."""

    address: str = field(repr=False)
    port: int
    hostname: str = field(repr=False)
    role: Literal["resolver", "origin"]


@dataclass(frozen=True, slots=True)
class NetworkHandoff:
    """One nonblocking syscall's target and exact pending disclosure bytes."""

    target: NetworkTarget
    phase: Literal["connect", "dns", "tls", "http"]
    wire_bytes: bytes = field(repr=False)
    application_bytes: bytes | None = field(repr=False)


class NetworkGate(Protocol):
    """Authorize, debit and execute one syscall synchronously on the host loop.

    Implementations must call the action exactly once before returning. A gate
    is mandatory; neither a prior receipt nor these values authorize a contact.
    """

    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        """Check current authority and execute the same handoff without yielding."""
        ...
