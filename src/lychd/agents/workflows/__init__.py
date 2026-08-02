"""Workflow registry (A5-U7): route by `Trigger`, look up by persisted name.

The engine routes an `Intent` to a `Workflow` ONCE via `WorkflowRegistry.route`
(explicit-precedence `Trigger` semantics, absorbing the former `agents.router.route`),
persists the choice, and thereafter `perform_run` looks the workflow up by name
and exact persisted revision — it never re-routes an in-flight run.

The full workflow packs are a later wave; here the registry wraps the built-in
`bridge_chat` and offline reference `delegated_rite` workflows. Production consumers
receive one registry from the application assembly root. ``WORKFLOW_REGISTRY`` remains
only as a compatibility value for direct library callers and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol, runtime_checkable

from lychd.agents.workflows.base import Trigger, Workflow
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT
from lychd.agents.workflows.delegated_rite import DELEGATED_RITE

if TYPE_CHECKING:
    from lychd.agents.router import Intent

__all__ = [
    "BRIDGE_CHAT",
    "DELEGATED_RITE",
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
        """Return every registered exact revision in declaration order."""
        ...

    def is_active(self, pattern_id: str, revision: str, /) -> bool:
        """Return whether an exact revision can receive new admissions."""
        ...

    def is_default(self, pattern_id: str, revision: str, /) -> bool:
        """Return whether an exact revision is the active route floor."""
        ...

    def route_rank(self, pattern_id: str, revision: str, /) -> int | None:
        """Return the one-based trigger precedence, excluding the default."""
        ...


@dataclass(frozen=True)
class BuiltinWorkflowRegistry:
    """Immutable revision catalogue with explicit active routing policy."""

    workflows: tuple[Workflow, ...]
    active_revisions: tuple[tuple[str, str], ...] = ()
    route_precedence: tuple[str, ...] = ()
    default_name: str | None = None

    def __post_init__(self) -> None:
        """Validate exact identities and freeze one unambiguous active route set."""
        if not self.workflows:
            msg = "WorkflowRegistry requires at least one workflow (the default)."
            raise ValueError(msg)
        names = [workflow.name for workflow in self.workflows]
        identities = [(workflow.manifest.key, workflow.manifest.revision) for workflow in self.workflows]
        if len(identities) != len(set(identities)):
            msg = "WorkflowRegistry contains duplicate Pattern revisions."
            raise ValueError(msg)

        registered_names = tuple(dict.fromkeys(names))
        active_revisions = self._normalize_active_revisions(registered_names, identities)
        default_name = self._normalize_default_name(active_revisions)
        self._normalize_route_precedence(active_revisions, default_name)

    def _normalize_active_revisions(
        self,
        registered_names: tuple[str, ...],
        identities: list[tuple[str, str]],
    ) -> tuple[tuple[str, str], ...]:
        """Validate or infer at most one active revision for each admitted name."""
        active_revisions = self.active_revisions
        if not active_revisions:
            if len(self.workflows) != len(registered_names):
                msg = "WorkflowRegistry with multiple revisions requires explicit active revisions."
                raise ValueError(msg)
            active_revisions = tuple((workflow.name, workflow.manifest.revision) for workflow in self.workflows)
            object.__setattr__(self, "active_revisions", active_revisions)

        active_names = [name for name, _revision in active_revisions]
        if len(active_names) != len(set(active_names)):
            msg = "WorkflowRegistry contains duplicate active workflow names."
            raise ValueError(msg)
        if not active_names:
            msg = "WorkflowRegistry requires at least one active workflow revision."
            raise ValueError(msg)
        for identity in active_revisions:
            if identity not in identities:
                msg = f"WorkflowRegistry active Pattern revision is not registered: {identity[0]}@{identity[1]}."
                raise ValueError(msg)
        return active_revisions

    def _normalize_default_name(
        self,
        active_revisions: tuple[tuple[str, str], ...],
    ) -> str:
        """Validate or infer the active route floor."""
        active_names = [name for name, _revision in active_revisions]
        default_name = self.default_name or active_names[0]
        if default_name not in active_names:
            msg = f"WorkflowRegistry default workflow is not active: {default_name}."
            raise ValueError(msg)
        object.__setattr__(self, "default_name", default_name)
        return default_name

    def _normalize_route_precedence(
        self,
        active_revisions: tuple[tuple[str, str], ...],
        default_name: str,
    ) -> None:
        """Validate or infer deterministic non-default trigger precedence."""
        active_names = [name for name, _revision in active_revisions]
        route_precedence = self.route_precedence
        if not route_precedence:
            if len(active_names) > 1:
                msg = "WorkflowRegistry with multiple workflow names requires explicit route precedence."
                raise ValueError(msg)
            route_precedence = tuple(name for name in active_names if name != default_name)
            object.__setattr__(self, "route_precedence", route_precedence)
        if len(route_precedence) != len(set(route_precedence)):
            msg = "WorkflowRegistry route precedence contains duplicate workflow names."
            raise ValueError(msg)
        expected_routes = set(active_names).difference({default_name})
        if set(route_precedence) != expected_routes:
            msg = "WorkflowRegistry route precedence must name every active non-default workflow exactly once."
            raise ValueError(msg)

    @property
    def default(self) -> Workflow:
        """Return the explicitly active route floor."""
        workflow = self.get(self.default_name or "")
        if workflow is None:  # pragma: no cover - constructor proves this invariant
            msg = "WorkflowRegistry default workflow disappeared after construction."
            raise RuntimeError(msg)
        return workflow

    def route(self, intent: Intent) -> Workflow:
        """Return the first workflow whose trigger matches, else the default."""
        for name in self.route_precedence:
            workflow = self.get(name)
            if workflow is None:  # pragma: no cover - constructor proves this invariant
                continue
            if workflow.trigger.match(intent):
                return workflow
        return self.default

    def get(self, name: str, /) -> Workflow | None:
        """Return the workflow registered under ``name``, or ``None``."""
        for active_name, revision in self.active_revisions:
            if active_name == name:
                return self.get_revision(name, revision)
        return None

    def get_revision(self, pattern_id: str, revision: str, /) -> Workflow | None:
        """Return one exact registered Pattern revision, or ``None``."""
        for workflow in self.workflows:
            if workflow.manifest.key == pattern_id and workflow.manifest.revision == revision:
                return workflow
        return None

    def all(self) -> tuple[Workflow, ...]:
        """Return every registered exact revision in declaration order."""
        return self.workflows

    def is_active(self, pattern_id: str, revision: str, /) -> bool:
        """Return whether an exact revision can receive new admissions."""
        return (pattern_id, revision) in self.active_revisions

    def is_default(self, pattern_id: str, revision: str, /) -> bool:
        """Return whether an exact revision is the active route floor."""
        workflow = self.get(self.default_name or "")
        return workflow is not None and (
            workflow.manifest.key,
            workflow.manifest.revision,
        ) == (pattern_id, revision)

    def route_rank(self, pattern_id: str, revision: str, /) -> int | None:
        """Return the one-based trigger precedence for an active non-default revision."""
        if not self.is_active(pattern_id, revision):
            return None
        try:
            return self.route_precedence.index(pattern_id) + 1
        except ValueError:
            return None


def builtin_workflow_registry() -> BuiltinWorkflowRegistry:
    """Build the built-in workflow registry (the sole construction site today)."""
    return BuiltinWorkflowRegistry(
        workflows=(BRIDGE_CHAT, DELEGATED_RITE),
        active_revisions=(
            (BRIDGE_CHAT.name, BRIDGE_CHAT.manifest.revision),
            (DELEGATED_RITE.name, DELEGATED_RITE.manifest.revision),
        ),
        route_precedence=(DELEGATED_RITE.name,),
        default_name=BRIDGE_CHAT.name,
    )


# Built once from frozen workflow config data (not mutable module state).
WORKFLOW_REGISTRY: Final[BuiltinWorkflowRegistry] = builtin_workflow_registry()
