"""Ports separating Intercom core from transport, authentication, policy, and storage."""

from __future__ import annotations

from typing import Protocol

from lychd.domain.intercom.models import (
    PeerAdmissionDecision,
    PeerTaskRecord,
    PeerTaskResult,
    PeerTaskStatus,
    VerifiedPeerEnvelope,
)

__all__ = ["PeerAdmissionPolicy", "PeerEnvelopeVerifier", "PeerTaskStore"]


class PeerEnvelopeVerifier(Protocol):
    """Pinned adapter boundary for decoding and cryptographically verifying one message."""

    async def verify(self, message: bytes) -> VerifiedPeerEnvelope:
        """Return exact authenticated evidence or raise without admitting work."""
        ...


class PeerAdmissionPolicy(Protocol):
    """Local authority deciding whether one authenticated peer task is admissible."""

    async def decide(self, verified: VerifiedPeerEnvelope) -> PeerAdmissionDecision:
        """Evaluate current peer, task, content, resource, artifact, and egress policy."""
        ...


class PeerTaskStore(Protocol):
    """Persistence seam for replay-safe incoming peer-task state."""

    async def receive(self, verified: VerifiedPeerEnvelope) -> tuple[PeerTaskRecord, bool]:
        """Record one verified envelope once and reject conflicting identity reuse."""
        ...

    async def get(self, task_id: str) -> PeerTaskRecord | None: ...

    async def transition(
        self,
        task_id: str,
        status: PeerTaskStatus,
        *,
        admission: PeerAdmissionDecision | None = None,
    ) -> tuple[PeerTaskRecord, bool]:
        """Advance one legal nonterminal edge."""
        ...

    async def adopt(
        self,
        task_id: str,
        result: PeerTaskResult,
        *,
        admission: PeerAdmissionDecision | None = None,
    ) -> tuple[PeerTaskRecord, bool]:
        """Adopt one exact terminal result; later results remain inert."""
        ...
