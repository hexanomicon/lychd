"""Workflow = graph + metadata + deterministic trigger (§5.1).

A `Workflow` binds a BaseNode-style `pydantic_graph.Graph` to the metadata the
Loom renders and the pure predicate the router matches. Adding a workflow never
edits the router.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel
    from pydantic_graph import BaseNode, Graph

    from lychd.agents.router import Intent

# The necro-green highlight used for the active node in Loom projections.
HIGHLIGHT_CSS = "fill:#39ff8a33,stroke:#39ff8a,stroke-width:2px"
_ROUTE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_HEX_LENGTH = 64
_PATTERN_SCHEMA_VERSION = 2
_PATTERN_SNAPSHOT_FIELDS = (
    "schema_version",
    "key",
    "revision",
    "implementation_revision",
    "checkpoint_schema",
    "entry_node",
    "nodes",
    "edges",
)


def pattern_snapshot_is_valid(snapshot: dict[str, Any]) -> bool:
    """Validate a persisted declarative score fingerprint and its checksum."""
    digest = snapshot.get("digest")
    if (
        not isinstance(digest, str)
        or len(digest) != _SHA256_HEX_LENGTH
        or any(field not in snapshot for field in _PATTERN_SNAPSHOT_FIELDS)
    ):
        return False
    key = snapshot.get("key")
    revision = snapshot.get("revision")
    implementation_revision = snapshot.get("implementation_revision")
    checkpoint_schema = snapshot.get("checkpoint_schema")
    entry_node = snapshot.get("entry_node")
    if snapshot.get("schema_version") != _PATTERN_SCHEMA_VERSION or not all(
        isinstance(value, str) for value in (key, revision, implementation_revision, checkpoint_schema, entry_node)
    ):
        return False
    identifiers = (key, revision, implementation_revision, checkpoint_schema, entry_node)
    if any(not value or not _ROUTE_IDENTIFIER.fullmatch(value) for value in identifiers):
        return False
    nodes = snapshot.get("nodes")
    edges = snapshot.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return False
    entry_nodes: list[dict[str, object]] = []
    for candidate in cast("list[object]", nodes):
        if isinstance(candidate, dict):
            node = cast("dict[str, object]", candidate)
            if node.get("key") == entry_node:
                entry_nodes.append(node)
    if len(entry_nodes) != 1 or entry_nodes[0].get("kind") == "terminal":
        return False
    unsigned = {field: snapshot[field] for field in _PATTERN_SNAPSHOT_FIELDS}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest() == digest


class Gate:
    """Marker mixin: a node that can park the run on an external verdict (consent/HitL).

    Any workflow whose graph contains a Gate node is assigned the Durable Stasis tier
    (`_workflow_parks` scans `graph.get_nodes()` for `issubclass(node, Gate)`).
    """


class DelegatedAgentNode:
    """Marker mixin for a node that can enter Durable Stasis on delegated labor.

    The marker is execution policy, not decoration: any workflow containing one is
    assigned durable checkpoint persistence, and its Pattern station must declare
    ``kind="delegate"``.
    """


@dataclass(frozen=True, kw_only=True)
class PatternNode:
    """One stable semantic station in an immutable Weaver Pattern revision."""

    key: str
    label: str
    kind: Literal["step", "gate", "delegate", "terminal"] = "step"
    implementation: type[Any] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Require renderer-independent identity and an implementation for executable stations."""
        if not self.key or not self.label:
            msg = "Pattern nodes require non-empty keys and labels."
            raise ValueError(msg)
        if self.kind != "terminal" and self.implementation is None:
            msg = f"Executable Pattern node '{self.key}' requires an implementation."
            raise ValueError(msg)
        if self.kind == "delegate" and (
            self.implementation is None or not issubclass(self.implementation, DelegatedAgentNode)
        ):
            msg = f"Delegated Pattern node '{self.key}' must use a DelegatedAgentNode implementation."
            raise ValueError(msg)
        if (
            self.implementation is not None
            and issubclass(self.implementation, DelegatedAgentNode)
            and self.kind != "delegate"
        ):
            msg = f"DelegatedAgentNode implementation '{self.key}' must declare kind='delegate'."
            raise ValueError(msg)
        if self.kind == "gate" and (self.implementation is None or not issubclass(self.implementation, Gate)):
            msg = f"Gate Pattern node '{self.key}' must use a Gate implementation."
            raise ValueError(msg)
        if self.implementation is not None and issubclass(self.implementation, Gate) and self.kind != "gate":
            msg = f"Gate implementation '{self.key}' must declare kind='gate'."
            raise ValueError(msg)

    def snapshot(self) -> dict[str, str]:
        """Return the safe, renderer-neutral persisted projection."""
        return {"key": self.key, "label": self.label, "kind": self.kind}


@dataclass(frozen=True, kw_only=True)
class PatternEdge:
    """One stable permission edge in a Pattern score."""

    key: str
    source: str
    target: str
    relation: Literal["permits"] = "permits"

    def snapshot(self) -> dict[str, str]:
        """Return the safe persisted projection."""
        return {
            "key": self.key,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
        }


@dataclass(frozen=True, kw_only=True)
class PatternManifest:
    """Immutable Weaver-owned identity and score pinned to every admitted Run.

    The explicit revision is source-owned. The digest detects accidental drift inside
    that revision; it is not itself the revision and Mermaid is never an authority.
    """

    key: str
    revision: str
    implementation_revision: str
    checkpoint_schema: str
    entry_node: str
    nodes: tuple[PatternNode, ...]
    edges: tuple[PatternEdge, ...]
    schema_version: int = _PATTERN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate stable uniqueness and closed edge references."""
        if self.schema_version != _PATTERN_SCHEMA_VERSION:
            msg = f"Pattern schema version must be {_PATTERN_SCHEMA_VERSION}."
            raise ValueError(msg)
        identifiers = (
            self.key,
            self.revision,
            self.implementation_revision,
            self.checkpoint_schema,
            self.entry_node,
        )
        if any(not value or not _ROUTE_IDENTIFIER.fullmatch(value) for value in identifiers):
            msg = "Pattern identity fields and entry node must be URL-safe identifiers."
            raise ValueError(msg)
        node_keys = [node.key for node in self.nodes]
        if len(node_keys) != len(set(node_keys)):
            msg = f"Pattern '{self.key}@{self.revision}' has duplicate node keys."
            raise ValueError(msg)
        entry_nodes = [node for node in self.nodes if node.key == self.entry_node]
        if len(entry_nodes) != 1 or entry_nodes[0].kind == "terminal":
            msg = f"Pattern '{self.key}@{self.revision}' entry node must name one executable station."
            raise ValueError(msg)
        edge_keys = [edge.key for edge in self.edges]
        if len(edge_keys) != len(set(edge_keys)):
            msg = f"Pattern '{self.key}@{self.revision}' has duplicate edge keys."
            raise ValueError(msg)
        edge_pairs = [(edge.source, edge.target) for edge in self.edges]
        if len(edge_pairs) != len(set(edge_pairs)):
            msg = f"Pattern '{self.key}@{self.revision}' has duplicate semantic edges."
            raise ValueError(msg)
        unknown = {
            endpoint for edge in self.edges for endpoint in (edge.source, edge.target) if endpoint not in node_keys
        }
        if unknown:
            msg = f"Pattern '{self.key}@{self.revision}' edges reference unknown nodes: {sorted(unknown)}"
            raise ValueError(msg)

    @property
    def digest(self) -> str:
        """Return a deterministic digest of the semantic manifest."""
        encoded = json.dumps(self._unsigned_snapshot(), sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

    def node_key(self, implementation: type[Any]) -> str:
        """Resolve one executable node type to its stable Pattern key."""
        matches = [node.key for node in self.nodes if node.implementation is implementation]
        if len(matches) != 1:
            msg = (
                f"Pattern '{self.key}@{self.revision}' must map {implementation.__name__} "
                f"to exactly one semantic node; found {len(matches)}."
            )
            raise KeyError(msg)
        return matches[0]

    def snapshot(self) -> dict[str, Any]:
        """Return the exact safe manifest persisted with a Run."""
        return {**self._unsigned_snapshot(), "digest": self.digest}

    def _unsigned_snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "key": self.key,
            "revision": self.revision,
            "implementation_revision": self.implementation_revision,
            "checkpoint_schema": self.checkpoint_schema,
            "entry_node": self.entry_node,
            "nodes": [node.snapshot() for node in self.nodes],
            "edges": [edge.snapshot() for edge in self.edges],
        }


@dataclass(frozen=True, kw_only=True)
class Trigger:
    """Deterministic route predicate. Adding a workflow never edits the router."""

    hint: str
    match: Callable[[Intent], bool]


@dataclass(frozen=True, kw_only=True)
class Workflow:
    """A named workflow: its graph, its Loom metadata, and its route trigger."""

    name: str
    title: str
    description: str
    trigger: Trigger
    graph: Graph[Any, Any, Any]
    start_node: type[BaseNode[Any, Any, Any]]
    make_state: Callable[[Intent], BaseModel]
    manifest: PatternManifest
    # Computed once at construction: a workflow whose graph contains any `Gate` node
    # takes the Durable Stasis tier. Kept a derived property (not a hand-set flag) so it
    # can never drift from the graph — but resolved HERE, near `Gate`, not re-scanned by
    # the ghoul on every run.
    durable: bool = field(init=False)

    def __post_init__(self) -> None:
        """Validate the Pattern binding and derive the Durable-Stasis tier."""
        if self.manifest.key != self.name:
            msg = f"Workflow '{self.name}' must use a Pattern manifest with the same key."
            raise ValueError(msg)
        executable = {node.implementation for node in self.manifest.nodes if node.implementation is not None}
        graph_nodes = set(self.graph.get_nodes())
        if self.start_node not in graph_nodes:
            msg = f"Workflow '{self.name}' start node must belong to its graph."
            raise ValueError(msg)
        if self.manifest.node_key(self.start_node) != self.manifest.entry_node:
            msg = f"Workflow '{self.name}' start node must match Pattern entry node '{self.manifest.entry_node}'."
            raise ValueError(msg)
        if executable != graph_nodes:
            msg = (
                f"Pattern '{self.manifest.key}@{self.manifest.revision}' executable nodes must exactly match its graph."
            )
            raise ValueError(msg)
        for implementation in graph_nodes:
            try:
                self.manifest.node_key(implementation)
            except KeyError as exc:
                msg = f"Pattern '{self.manifest.key}@{self.manifest.revision}' must bind every graph node exactly once."
                raise ValueError(msg) from exc
        self._validate_manifest_topology()
        object.__setattr__(
            self,
            "durable",
            any(issubclass(node, (Gate, DelegatedAgentNode)) for node in self.graph.get_nodes()),
        )

    def _validate_manifest_topology(self) -> None:
        """Require the semantic score to match executable and durable re-entry edges."""
        terminal_nodes = [node for node in self.manifest.nodes if node.kind == "terminal"]
        if len(terminal_nodes) != 1:
            msg = f"Pattern '{self.manifest.key}@{self.manifest.revision}' must declare exactly one terminal node."
            raise ValueError(msg)
        terminal_key = terminal_nodes[0].key
        keys_by_implementation = {
            node.implementation: node.key for node in self.manifest.nodes if node.implementation is not None
        }
        executable_edges: set[tuple[str, str]] = set()
        for node_def in self.graph.node_defs.values():
            if node_def.returns_base_node:
                msg = (
                    f"Pattern '{self.manifest.key}@{self.manifest.revision}' cannot prove topology for "
                    f"dynamic BaseNode return from {node_def.node.__name__}."
                )
                raise ValueError(msg)
            source = keys_by_implementation[node_def.node]
            for target_id in node_def.next_node_edges:
                target = keys_by_implementation[self.graph.node_defs[target_id].node]
                executable_edges.add((source, target))
            if node_def.end_edge is not None:
                executable_edges.add((source, terminal_key))

        # A delegated station exits the in-process graph while parked and is later
        # re-entered at the same station. That lifecycle edge is executable policy
        # even when the Python return annotation only names the forward node. Gate
        # loops, by contrast, are ordinary graph return edges and remain explicit.
        executable_edges.update((node.key, node.key) for node in self.manifest.nodes if node.kind == "delegate")
        manifest_edges = {(edge.source, edge.target) for edge in self.manifest.edges}
        if manifest_edges != executable_edges:
            missing = sorted(executable_edges - manifest_edges)
            extra = sorted(manifest_edges - executable_edges)
            msg = (
                f"Pattern '{self.manifest.key}@{self.manifest.revision}' topology differs from its graph; "
                f"missing={missing}, extra={extra}."
            )
            raise ValueError(msg)

    def mermaid(self, *, highlight: type[BaseNode[Any, Any, Any]] | None = None) -> str:
        """Return the stateDiagram-v2 source, optionally highlighting one node."""
        return self.graph.mermaid_code(
            title=self.title,
            direction="LR",
            highlighted_nodes=(highlight,) if highlight is not None else None,
            highlight_css=HIGHLIGHT_CSS,
        )
