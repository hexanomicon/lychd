"""Typed agent outputs shared without coupling agents to workflow modules.

Outputs are *structures*, never prose to parse. `THE_FIRST_ONE` outputs
`BridgeReply | DeferredToolRequests`; agent specs pass through the same
typed-output gate. These types live here (not in `bridge_chat`) so
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


__all__ = ["Bottleneck", "BridgeReply", "FragmentCall"]
