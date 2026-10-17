"""Public inert fixtures; no model, host, Git or acquisition effects."""

# ruff: noqa: INP001 - existing tests/support namespace is intentional

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from lychd.compositions.creation.schemas import (
    OUTPUT_TOKENS,
    Candidate,
    ExternalAssessment,
    FeedbackTarget,
    InvestigationRequest,
    Verdict,
)
from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
)
from lychd.domain.cortex.leases import LeaseLedger


def request_document() -> InvestigationRequest:
    return InvestigationRequest.model_validate(
        {
            "request_id": str(uuid4()),
            "public_material": True,
            "repository": "public/example",
            "base_revision": "base-1",
            "tree_or_patch_digest": "a" * 40,
            "question": "Does a zero input refute the nonnegative predicate?",
            "non_goals": ["No source edits"],
            "omissions": [],
            "sources": [{"name": "check.py", "text": "def valid(x):\n    return x >= 0\n"}],
            "criteria": [{"id": "predicate", "predicate": "A counterexample must make valid(x) false."}],
        }
    )


def candidate_document() -> Candidate:
    return Candidate.model_validate(
        {
            "summary": "Zero is a counterexample.",
            "findings": [
                {
                    "criterion": "predicate",
                    "claim": "The zero case defeats the predicate.",
                    "citations": [{"source": "check.py", "first_line": 1, "last_line": 2}],
                    "unknown": "",
                }
            ],
        }
    )


def verdict_document() -> Verdict:
    return Verdict.model_validate(
        {
            "disposition": "rejected",
            "findings": [
                {
                    "criterion": "predicate",
                    "claim": "Zero satisfies x >= 0; a negative value refutes it.",
                    "citations": [{"source": "check.py", "first_line": 2, "last_line": 2}],
                    "unknown": "",
                }
            ],
            "contradictions": ["The proposed zero counterexample satisfies the actual predicate."],
        }
    )


def capability() -> CapabilitySpec:
    return CapabilitySpec.model_validate(
        {
            "key": "local:chat:Qwen3.8-27B",
            "animator_name": "local",
            "runtime": "vllm",
            "source_kind": "soulstone",
            "family": "chat",
            "model_id": "Qwen3.8-27B",
            "max_context": 4096,
            "concurrency": {"dedicated": False},
            "generation_profile": {
                "max_context": 4096,
                "max_tokens": OUTPUT_TOKENS,
                "temperature": 0,
                "thinking": "qwen3.8-non-thinking",
            },
        }
    )


class CreationRegistry:
    def get_capability(self, key: str) -> CapabilitySpec | None:
        return capability() if key == capability().key else None

    async def refresh_capability_state(self, key: str) -> CapabilityState:
        return CapabilityState(capability_key=key, phase=CapabilityPhase.WARM)


@dataclass(frozen=True, slots=True)
class InertCreationGrant(CapabilityGrant):
    """The inert model has no provider; its captured settings remain observable."""

    def model_settings(self) -> Any:
        return {
            "max_tokens": OUTPUT_TOKENS,
            "temperature": 0,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
        }


class CreationDispatcher:
    def __init__(self, model: Any, leases: LeaseLedger) -> None:
        self.model, self.leases = model, leases
        self.calls: list[dict[str, Any]] = []

    @asynccontextmanager
    async def lease_grant(self, **kwargs: Any) -> AsyncGenerator[CapabilityGrant]:
        self.calls.append(kwargs)
        spec = capability()
        assert kwargs["capability_key"] == spec.key
        assert kwargs["requires_tools"] is False
        grant = InertCreationGrant(
            spec=spec,
            state=CapabilityState(capability_key=spec.key, phase=CapabilityPhase.WARM),
            lease=GrantLease(grant_id=str(uuid4()), holder=f"run:{kwargs['run_id']}", issued_at=datetime.now(UTC)),
            model=self.model,
        )
        self.leases.acquire(
            grant, priority=50, admission_generation=self.leases.admission_generation(spec.animator_name)
        )
        try:
            yield grant
        finally:
            self.leases.release(grant.lease.grant_id)


def assessment_document(target: FeedbackTarget) -> ExternalAssessment:
    return ExternalAssessment(
        assessment_id=uuid4(),
        target=target,
        reviewer_label="external claimed reviewer",
        reviewer_revision="report-v1",
        report="PARTIAL: retained external report.\r\nExact č bytes.\n",
        disposition="partial",
        exposure=("Original request and native candidate",),
        limitations=("No authenticated external reviewer identity",),
    )
