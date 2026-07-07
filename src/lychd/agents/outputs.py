"""Typed agent outputs as a first-class module (A5 §2).

Outputs are *structures*, never prose to parse. `THE_FIRST_ONE` outputs
`BridgeReply | DeferredToolRequests`; every future agent spec goes through the
same typed-output gate. These types live here (not in `bridge_chat`) so
`the_first_one` can import `BridgeReply` without importing the workflow module —
that is what breaks the historical `the_first_one`<->`bridge_chat` cycle.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FragmentCall(BaseModel):
    """A generative-UI request: a registry key plus its params (never markup)."""

    fragment: str
    params: dict[str, Any] = Field(default_factory=dict)


class BridgeReply(BaseModel):
    """The First One's settled turn output."""

    answer: str
    fragments: list[FragmentCall] = Field(default_factory=list)


class Bottleneck(BaseModel):
    """A typed non-completion (ADR 20)."""

    kind: Literal["contradiction", "missing_input", "policy_block", "dependency_unavailable"]
    detail: str


class ConsentPointer(BaseModel):
    """What a parked turn projects while awaiting the Magus (A5 §2).

    The honest consent-resume path (a `ConsentPending` signal + `AwaitConsent`
    node) landed in Wave 4; this type keeps the projected shape stable.
    """

    consent_id: str
    tool_name: str
    summary: str


__all__ = ["Bottleneck", "BridgeReply", "ConsentPointer", "FragmentCall"]
