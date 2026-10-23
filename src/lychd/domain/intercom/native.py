"""Typed native peer ownership; retained values never authenticate an operator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.domain.cortex.ledger import PeerAdmissionEvidence


class PeerRunBinding(BaseModel):
    """Immutable admission of one original public source and exact sovereign target."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    profile: Literal["native-public-peer@1"] = "native-public-peer@1"
    request_id: UUID
    declaration_id: UUID
    operation_id: UUID
    peer_id: UUID
    purpose: str = Field(min_length=1, max_length=200)
    task_schema: str = Field(min_length=1, max_length=300)
    endpoint: str = Field(min_length=1, max_length=2048)
    category: Literal["public-task"] = "public-task"
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)
    text_digest: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)
    expires_at: datetime

    @property
    def digest(self) -> str:
        """Bind all source, target, occurrence and original lifetime facts."""
        value = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True, kw_only=True)
class PeerDeclarationProof:
    """Ephemeral host handoff checked by object identity and the actual marker."""

    authentication: object = field(repr=False)
    binding: PeerRunBinding


class PeerAdmission(Protocol):
    """Current synchronous admission check repeated after protected awaits."""

    def __call__(self, intent: Intent, proof: PeerDeclarationProof) -> PeerRunBinding: ...


class PeerTaskRef(BaseModel):
    """The only peer custody reference admitted into a native checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    task_id: UUID
    run_id: str = Field(min_length=1)
    station: str = Field(min_length=1, max_length=100)
    request_id: UUID
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PeerTaskPending(Exception):  # noqa: N818 - native suspension control flow
    """Checkpoint this exact peer task and exit the Graph worker."""

    def __init__(self, ref: PeerTaskRef) -> None:
        """Retain the exact local task owner for checkpointing."""
        self.ref = ref
        super().__init__("Native peer task awaits its sovereign result.")


class PeerTaskOutcomeError(RuntimeError):
    """An explicit local non-completion; remote execution may remain unknown."""

    def __init__(self, outcome: str) -> None:
        """Expose only a closed local disposition, without foreign diagnostics."""
        self.outcome = outcome
        super().__init__(f"Native public peer task settled locally: {outcome}.")


@dataclass(frozen=True, kw_only=True)
class PeerTaskParked:
    """The worker must atomically bind this owner before any peer contact."""

    ref: PeerTaskRef


class PeerWorkflowPort(Protocol):
    """Live process-owned authority and custody outside serializable Graph state."""

    async def prepare(self, *, run_id: str, binding: PeerRunBinding, station: str) -> PeerTaskRef: ...

    async def result(self, *, run_id: str, binding: PeerRunBinding, ref: PeerTaskRef) -> str: ...

    async def drive_wait(self, run_id: str) -> bool: ...

    async def evidence(self, *, run_id: str, task_id: str) -> PeerAdmissionEvidence: ...

    def require_resume(self, run_id: str, task_id: str, *, enqueue_seq: int) -> None: ...

    async def close_run(self, run_id: str) -> None: ...
