"""Bounded Intercom wire observations and mandatory current network handoff port.

These inert values grant no authority. Public source, current peer policy,
credential lifecycle, durable capacity and terminal adoption remain host duties.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

MAX_REQUEST_BYTES = 64 * 1024
MAX_REQUEST_BODY_BYTES = 48 * 1024
MAX_RESPONSE_BODY_BYTES = 64 * 1024
MAX_HEADER_BYTES = 8 * 1024
MAX_HEADER_FIELDS = 32
MAX_OPERATION_SECONDS = 30

type TaskMethod = Literal["SendMessage", "GetTask", "CancelTask"]


class IntercomCode(StrEnum):
    """Content-free outcomes; unknown remote effects require reconciliation."""

    CONFIG = "config"
    INPUT = "input"
    AUTHENTICATION = "authentication"
    PROTOCOL = "protocol"
    LIMIT = "limit"
    EGRESS = "egress"
    TRANSPORT = "transport"
    TIMEOUT = "timeout"
    REMOTE = "remote"


class IntercomError(ValueError):
    """A closed refusal that never includes foreign text or secret material."""

    def __init__(self, code: IntercomCode) -> None:
        """Retain only the closed failure classification."""
        self.code = code
        super().__init__(f"Intercom refused: {code.value}.")


class IntercomRemoteError(IntercomError):
    """An authenticated JSON-RPC error code, without foreign diagnostics."""

    def __init__(self, remote_code: int) -> None:
        """Preserve the bounded integer code for explicit local policy."""
        self.remote_code = remote_code
        super().__init__(IntercomCode.REMOTE)


@dataclass(frozen=True, slots=True)
class IntercomEndpoint:
    """One explicit numeric HTTPS target, path and trust-root selection."""

    address: str = field(repr=False)
    hostname: str = field(repr=False)
    port: int
    path: str = field(repr=False)
    ca_file: Path = field(repr=False)


@dataclass(frozen=True, slots=True)
class IntercomHandoff:
    """One syscall and the exact complete plaintext disclosure, when applicable."""

    target: IntercomEndpoint
    phase: Literal["connect", "tls", "http"]
    wire_bytes: bytes = field(repr=False)
    application_bytes: bytes | None = field(repr=False)


class IntercomGate(Protocol):
    """Check current authority, debit capacity and execute without yielding."""

    def handoff(self, handoff: IntercomHandoff, action: Callable[[], int]) -> int:
        """Execute action exactly once before returning its actual result."""
        ...


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    """Sealed complete application bytes and expected reply correlation."""

    method: TaskMethod
    local_task_id: str = field(repr=False)
    attempt_id: str = field(repr=False)
    peer_id: str = field(repr=False)
    workload_id: str = field(repr=False)
    task_schema: str = field(repr=False)
    request_uri: str = field(repr=False)
    body: bytes = field(repr=False)
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    wire: bytes = field(repr=False)
    digest: str = field(repr=False)
    nonce: str = field(repr=False)
    expected_task_id: str | None = field(repr=False)
    expected_context_id: str | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class RawResponse:
    """Bounded HTTP response bytes; neither authenticated nor authoritative."""

    status: int
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    body: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class TaskObservation:
    """Authenticated foreign task facts; all text remains quarantined data."""

    foreign_task_id: str = field(repr=False)
    context_id: str | None = field(repr=False)
    state: str
    text: tuple[str, ...] = field(repr=False)
    terminal: bool
    response_nonce: str = field(repr=False)
