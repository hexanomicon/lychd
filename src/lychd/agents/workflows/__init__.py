"""Workflow registry. Declaration order in `WORKFLOWS` is route precedence."""

from __future__ import annotations

from typing import Final

from lychd.agents.workflows.base import Trigger, Workflow
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT

WORKFLOWS: Final[tuple[Workflow, ...]] = (BRIDGE_CHAT,)

__all__ = ["BRIDGE_CHAT", "WORKFLOWS", "Trigger", "Workflow"]
