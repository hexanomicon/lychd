"""Workflow registry (A5-U7): route by `Trigger`, look up by persisted name.

The engine routes an `Intent` to a `Workflow` ONCE via `WorkflowRegistry.route`
(first-match `Trigger` semantics, absorbing the former `agents.router.route`),
persists the choice, and thereafter `perform_run` looks the workflow up by name
via `WorkflowRegistry.get` — it never re-routes an in-flight run.

The full workflow packs are a later wave; here the registry wraps the single
built-in `bridge_chat` workflow. Consumers (engine, Loom) read the registry
directly via `WORKFLOW_REGISTRY`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol, runtime_checkable

from lychd.agents.workflows.base import Trigger, Workflow
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT

if TYPE_CHECKING:
    from lychd.agents.router import Intent

__all__ = [
    "BRIDGE_CHAT",
    "WORKFLOW_REGISTRY",
    "BuiltinWorkflowRegistry",
    "Trigger",
    "Workflow",
    "WorkflowRegistry",
    "builtin_workflow_registry",
]


@runtime_checkable
class WorkflowRegistry(Protocol):
    """The route-once / look-up-by-name surface the engine and Loom consume."""

    @property
    def default(self) -> Workflow:
        """The floor workflow returned when no trigger matches."""
        ...

    def route(self, intent: Intent) -> Workflow:
        """Return the first workflow whose trigger matches, else the default."""
        ...

    def get(self, name: str, /) -> Workflow | None:
        """Return the workflow persisted under ``name``, or ``None``."""
        ...

    def get_revision(self, pattern_id: str, revision: str, /) -> Workflow | None:
        """Return one exact registered Pattern revision, or ``None``."""
        ...

    def all(self) -> tuple[Workflow, ...]:
        """Return every registered workflow in route-precedence order."""
        ...


@dataclass(frozen=True)
class BuiltinWorkflowRegistry:
    """Immutable, ordered workflow registry. Declaration order is route precedence."""

    workflows: tuple[Workflow, ...]

    def __post_init__(self) -> None:
        """Validate the registry is non-empty and has unambiguous immutable identities."""
        if not self.workflows:
            msg = "WorkflowRegistry requires at least one workflow (the default)."
            raise ValueError(msg)
        names = [workflow.name for workflow in self.workflows]
        if len(names) != len(set(names)):
            msg = "WorkflowRegistry contains duplicate workflow names."
            raise ValueError(msg)
        identities = [(workflow.manifest.key, workflow.manifest.revision) for workflow in self.workflows]
        if len(identities) != len(set(identities)):
            msg = "WorkflowRegistry contains duplicate Pattern revisions."
            raise ValueError(msg)

    @property
    def default(self) -> Workflow:
        """The first-registered workflow: the route floor."""
        return self.workflows[0]

    def route(self, intent: Intent) -> Workflow:
        """Return the first workflow whose trigger matches, else the default."""
        for workflow in self.workflows:
            if workflow.trigger.match(intent):
                return workflow
        return self.default

    def get(self, name: str, /) -> Workflow | None:
        """Return the workflow registered under ``name``, or ``None``."""
        for workflow in self.workflows:
            if workflow.name == name:
                return workflow
        return None

    def get_revision(self, pattern_id: str, revision: str, /) -> Workflow | None:
        """Return one exact registered Pattern revision, or ``None``."""
        for workflow in self.workflows:
            if workflow.manifest.key == pattern_id and workflow.manifest.revision == revision:
                return workflow
        return None

    def all(self) -> tuple[Workflow, ...]:
        """Return every registered workflow in route-precedence order."""
        return self.workflows


def builtin_workflow_registry() -> BuiltinWorkflowRegistry:
    """Build the built-in workflow registry (the sole construction site today)."""
    return BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT,))


# Built once from frozen workflow config data (not mutable module state).
WORKFLOW_REGISTRY: Final[BuiltinWorkflowRegistry] = builtin_workflow_registry()
