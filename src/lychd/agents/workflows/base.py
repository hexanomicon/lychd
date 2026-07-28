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
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel
    from pydantic_graph import BaseNode, Graph

    from lychd.agents.router import Intent

# The necro-green highlight used for the active node in Loom projections.
HIGHLIGHT_CSS = "fill:#39ff8a33,stroke:#39ff8a,stroke-width:2px"
_ROUTE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_HEX_LENGTH = 64
_PATTERN_SNAPSHOT_FIELDS = (
    "schema_version",
    "key",
    "revision",
    "checkpoint_schema",
    "nodes",
    "edges",
)


def pattern_snapshot_is_valid(snapshot: dict[str, Any]) -> bool:
    """Validate a persisted declarative score fingerprint and its checksum."""
    digest = snapshot.get("digest")
    if not isinstance(digest, str) or len(digest) != _SHA256_HEX_LENGTH:
        return False
    if any(field not in snapshot for field in _PATTERN_SNAPSHOT_FIELDS):
        return False
    key = snapshot.get("key")
    revision = snapshot.get("revision")
    if not isinstance(key, str) or not isinstance(revision, str):
        return False
    if not _ROUTE_IDENTIFIER.fullmatch(key) or not _ROUTE_IDENTIFIER.fullmatch(revision):
        return False
    nodes = snapshot.get("nodes")
    edges = snapshot.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return False
    unsigned = {field: snapshot[field] for field in _PATTERN_SNAPSHOT_FIELDS}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest() == digest


class Gate:
    """Marker mixin: a node that can park the run on an external verdict (consent/HitL).

    Any workflow whose graph contains a Gate node is assigned the Durable Stasis tier
    (`_workflow_parks` scans `graph.get_nodes()` for `issubclass(node, Gate)`).
    """


@dataclass(frozen=True, kw_only=True)
class PatternNode:
    """One stable semantic station in an immutable Weaver Pattern revision."""

    key: str
    label: str
    kind: Literal["step", "gate", "terminal"] = "step"
    implementation: type[Any] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Require renderer-independent identity and an implementation for executable stations."""
        if not self.key or not self.label:
            msg = "Pattern nodes require non-empty keys and labels."
            raise ValueError(msg)
        if self.kind != "terminal" and self.implementation is None:
            msg = f"Executable Pattern node '{self.key}' requires an implementation."
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
    checkpoint_schema: str
    nodes: tuple[PatternNode, ...]
    edges: tuple[PatternEdge, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        """Validate stable uniqueness and closed edge references."""
        if not self.key or not self.revision or not self.checkpoint_schema:
            msg = "Pattern key, revision, and checkpoint schema must be non-empty."
            raise ValueError(msg)
        if not _ROUTE_IDENTIFIER.fullmatch(self.key) or not _ROUTE_IDENTIFIER.fullmatch(self.revision):
            msg = "Pattern key and revision must be URL-safe identifiers."
            raise ValueError(msg)
        node_keys = [node.key for node in self.nodes]
        if len(node_keys) != len(set(node_keys)):
            msg = f"Pattern '{self.key}@{self.revision}' has duplicate node keys."
            raise ValueError(msg)
        edge_keys = [edge.key for edge in self.edges]
        if len(edge_keys) != len(set(edge_keys)):
            msg = f"Pattern '{self.key}@{self.revision}' has duplicate edge keys."
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
            "checkpoint_schema": self.checkpoint_schema,
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
        object.__setattr__(self, "durable", any(issubclass(node, Gate) for node in self.graph.get_nodes()))

    def mermaid(self, *, highlight: type[BaseNode[Any, Any, Any]] | None = None) -> str:
        """Return the stateDiagram-v2 source, optionally highlighting one node."""
        return self.graph.mermaid_code(
            title=self.title,
            direction="LR",
            highlighted_nodes=(highlight,) if highlight is not None else None,
            highlight_css=HIGHLIGHT_CSS,
        )
