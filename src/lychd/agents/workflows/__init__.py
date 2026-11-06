"""Immutable workflow revisions and routing for new admissions.

RunEngine routes each new Intent to an active revision and pins its full manifest.
Worker execution resolves that exact snapshot; inactive retained revisions remain
available for replay. Changing active routes never reroutes an admitted Run.

The application assembly root supplies one registry to all consumers. Private
legacy_inline locks keep exact local lookup bound to that immutable assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from lychd.agents.workflows._legacy_inline import LegacyInlineLock, legacy_inline_lock
from lychd.agents.workflows.archive_chat import BRIDGE_CHAT_ARCHIVE
from lychd.agents.workflows.base import PatternManifest, Trigger, Workflow, pattern_snapshot_is_valid
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT, BRIDGE_CHAT_BOUND
from lychd.agents.workflows.delegated_rite import DELEGATED_RITE, DELEGATED_RITE_BOUND
from lychd.agents.workflows.observe_market import OBSERVE_MARKET
from lychd.agents.workflows.scout_chat import BRIDGE_CHAT_SCOUT
from lychd.agents.workflows.semantic_chat import BRIDGE_CHAT_SEMANTIC
from lychd.domain.naming import NamingSnapshot

if TYPE_CHECKING:
    from pydantic import BaseModel

    from lychd.agents.router import Intent
    from lychd.config.settings import WeaverSettings

__all__ = [
    "BRIDGE_CHAT",
    "BRIDGE_CHAT_ARCHIVE",
    "BRIDGE_CHAT_BOUND",
    "BRIDGE_CHAT_SCOUT",
    "BRIDGE_CHAT_SEMANTIC",
    "DELEGATED_RITE",
    "DELEGATED_RITE_BOUND",
    "OBSERVE_MARKET",
    "BuiltinWorkflowRegistry",
    "Trigger",
    "Workflow",
    "WorkflowRegistry",
    "builtin_workflow_registry",
    "resolve_named_workflow",
    "resolve_pinned_workflow",
]


@runtime_checkable
class WorkflowRegistry(Protocol):
    """Route new admissions and resolve retained revisions for execution and Loom."""

    @property
    def default(self) -> Workflow:
        """The floor workflow returned when no trigger matches."""
        ...

    def route(self, intent: Intent) -> Workflow:
        """Return the first workflow whose trigger matches, else the default."""
        ...

    def get(self, name: str, /) -> Workflow | None:
        """Return the active revision for ``name``, or ``None`` if inactive or unknown."""
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


def resolve_pinned_workflow(
    registry: WorkflowRegistry,
    *,
    workflow_name: str,
    snapshot: dict[str, Any],
) -> Workflow | None:
    """Resolve only an exact valid snapshot owned by its persisted workflow name."""
    if not pattern_snapshot_is_valid(snapshot):
        return None
    pattern_id = cast("str", snapshot["key"])
    revision = cast("str", snapshot["revision"])
    if pattern_id != workflow_name:
        return None
    workflow = registry.get_revision(pattern_id, revision)
    if workflow is None or snapshot != workflow.manifest.snapshot():
        return None
    return workflow


@dataclass(frozen=True)
class BuiltinWorkflowRegistry:
    """Immutable local bindings with explicit active revision routing policy."""

    workflows: tuple[Workflow, ...]
    active_revisions: tuple[tuple[str, str], ...] = ()
    route_precedence: tuple[str, ...] = ()
    default_name: str | None = None
    _assemblies: tuple[tuple[Workflow, LegacyInlineLock], ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Freeze exact local bindings and one unambiguous active route set."""
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
        object.__setattr__(
            self, "_assemblies", tuple((workflow, legacy_inline_lock(workflow.manifest)) for workflow in self.workflows)
        )

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
        if not route_precedence and len(active_names) > 1:
            msg = "WorkflowRegistry with multiple workflow names requires explicit route precedence."
            raise ValueError(msg)
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
        if workflow is None:
            msg = "WorkflowRegistry default workflow binding is unavailable."
            raise RuntimeError(msg)
        return workflow

    def route(self, intent: Intent) -> Workflow:
        """Return the first workflow whose trigger matches, else the default."""
        for name in self.route_precedence:
            workflow = self.get(name)
            if workflow is None:
                msg = f"WorkflowRegistry active workflow binding is unavailable: {name}."
                raise RuntimeError(msg)
            if workflow.trigger.match(intent):
                return workflow
        return self.default

    def get(self, name: str, /) -> Workflow | None:
        """Return the active revision for ``name``, or ``None`` if inactive or unknown."""
        for active_name, revision in self.active_revisions:
            if active_name == name:
                return self.get_revision(name, revision)
        return None

    def get_revision(self, pattern_id: str, revision: str, /) -> Workflow | None:
        """Resolve an exact revision only while its frozen local binding agrees."""
        for workflow, lock in self._assemblies:
            manifest = workflow.manifest
            if manifest.key == pattern_id and manifest.revision == revision:
                return workflow if legacy_inline_lock(manifest).digest == lock.digest else None
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


def _naming_manifest(workflow: Workflow) -> PatternManifest:
    """Fence named execution from workers that only know legacy Bridge revisions."""
    return replace(
        workflow.manifest,
        revision=f"{workflow.manifest.revision}-naming1",
        implementation_revision=f"{workflow.manifest.implementation_revision}-naming1",
        checkpoint_schema=f"{workflow.manifest.checkpoint_schema}-naming1",
    )


def _named_bridge_workflow(workflow: Workflow) -> Workflow:
    """Reuse the exact profile behavior behind a mandatory retained naming binding."""

    def require_naming(intent: Intent) -> NamingSnapshot:
        if intent.admitted_naming is None:
            msg = "Named Bridge revision requires its admitted naming snapshot."
            raise ValueError(msg)
        return NamingSnapshot.model_validate(intent.admitted_naming.model_dump())

    def make_state(intent: Intent) -> BaseModel:
        naming = require_naming(intent)
        legacy_intent = intent.model_copy(update={"admitted_naming": None})
        return workflow.make_state(legacy_intent).model_copy(update={"naming": naming})

    def validate_state(intent: Intent, state: BaseModel) -> None:
        naming = require_naming(intent)
        if getattr(state, "naming", None) != naming:
            msg = "Named Bridge checkpoint does not match its admitted naming snapshot."
            raise ValueError(msg)
        legacy_intent = intent.model_copy(update={"admitted_naming": None})
        if workflow.validate_state is None:
            msg = "Named Bridge revision requires a profile checkpoint validator."
            raise ValueError(msg)
        workflow.validate_state(legacy_intent, state.model_copy(update={"naming": None}))

    return replace(
        workflow,
        trigger=Trigger(hint="selected from accepted naming at admission", match=lambda _intent: False),
        manifest=_naming_manifest(workflow),
        make_state=make_state,
        validate_state=validate_state,
    )


_NAMED_BRIDGE_WORKFLOWS = tuple(
    _named_bridge_workflow(workflow)
    for workflow in (BRIDGE_CHAT, BRIDGE_CHAT_BOUND, BRIDGE_CHAT_ARCHIVE, BRIDGE_CHAT_SCOUT, BRIDGE_CHAT_SEMANTIC)
)


def resolve_named_workflow(registry: WorkflowRegistry, workflow: Workflow) -> Workflow:
    """Select only the registered naming-aware equivalent of a routed base profile."""
    if workflow.name != "bridge_chat" or workflow.manifest.revision not in {"1", "2", "3", "4", "5"}:
        msg = "No naming-aware Bridge revision is registered for this profile."
        raise ValueError(msg)
    named = resolve_pinned_workflow(
        registry, workflow_name=workflow.name, snapshot=_naming_manifest(workflow).snapshot()
    )
    if named is None:
        msg = "The selected registry cannot execute retained Bridge naming."
        raise ValueError(msg)
    return named


def builtin_workflow_registry(*, weaver: WeaverSettings | None = None) -> BuiltinWorkflowRegistry:
    """Select active configured revisions while retaining prior executable revisions."""
    bridge = BRIDGE_CHAT_BOUND if weaver is not None and weaver.bridge is not None else BRIDGE_CHAT
    if weaver is not None and weaver.bridge is not None and weaver.bridge.revision == "3":
        bridge = BRIDGE_CHAT_ARCHIVE
    if weaver is not None and weaver.bridge is not None and weaver.bridge.revision == "4":
        bridge = BRIDGE_CHAT_SCOUT
    if weaver is not None and weaver.bridge is not None and weaver.bridge.revision == "5":
        bridge = BRIDGE_CHAT_SEMANTIC
    delegate = DELEGATED_RITE_BOUND if weaver is not None and weaver.delegation is not None else DELEGATED_RITE
    scavenger_active = weaver is not None and weaver.scavenger is not None
    return BuiltinWorkflowRegistry(
        workflows=(
            BRIDGE_CHAT,
            BRIDGE_CHAT_BOUND,
            BRIDGE_CHAT_ARCHIVE,
            BRIDGE_CHAT_SCOUT,
            BRIDGE_CHAT_SEMANTIC,
            *_NAMED_BRIDGE_WORKFLOWS,
            DELEGATED_RITE,
            DELEGATED_RITE_BOUND,
            OBSERVE_MARKET,
        ),
        active_revisions=(
            (bridge.name, bridge.manifest.revision),
            (delegate.name, delegate.manifest.revision),
            *(((OBSERVE_MARKET.name, OBSERVE_MARKET.manifest.revision),) if scavenger_active else ()),
        ),
        route_precedence=(*((OBSERVE_MARKET.name,) if scavenger_active else ()), DELEGATED_RITE.name),
        default_name=BRIDGE_CHAT.name,
    )
