"""Workflow = graph + metadata + deterministic trigger.

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

from lychd.domain.cortex.graph import serial_graph_topology

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel
    from pydantic_graph import BaseNode, Graph

    from lychd.agents.router import Intent
    from lychd.agents.services import WorkflowServices

# Optional caller-owned emphasis; the static Loom does not infer active stations.
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


def _snapshot_string_fields(candidate: object, fields: tuple[str, ...]) -> dict[str, str]:
    """Read required semantic strings before any hashing or set construction."""
    if isinstance(candidate, dict):
        record = cast("dict[str, object]", candidate)
        if all(isinstance(record.get(field), str) for field in fields):
            return {field: cast("str", record[field]) for field in fields}
    msg = "Pattern snapshot records require string semantic fields."
    raise ValueError(msg)


def pattern_snapshot_is_valid(snapshot: dict[str, Any]) -> bool:
    """Validate persisted v2 score shape and checksum without resolving executable code."""
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
    stations: list[tuple[str, str]] = []
    permissions: list[PatternEdge] = []
    try:
        for candidate in cast("list[object]", nodes):
            node_fields = _snapshot_string_fields(candidate, ("key", "label", "kind"))
            _validate_pattern_node_fields(node_fields["key"], node_fields["label"], node_fields["kind"])
            stations.append((node_fields["key"], node_fields["kind"]))
        for candidate in cast("list[object]", edges):
            edge_fields = _snapshot_string_fields(candidate, ("key", "source", "target", "relation"))
            permissions.append(
                PatternEdge(
                    key=edge_fields["key"],
                    source=edge_fields["source"],
                    target=edge_fields["target"],
                    relation=cast("Literal['permits']", edge_fields["relation"]),
                )
            )
        _validate_pattern_score(
            cast("str", key), cast("str", revision), cast("str", entry_node), tuple(stations), tuple(permissions)
        )
    except ValueError:
        return False
    unsigned = {field: snapshot[field] for field in _PATTERN_SNAPSHOT_FIELDS}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest() == digest


class Gate:
    """Marker for a consent/HitL station requiring durable checkpoint persistence."""


class DelegatedAgentNode:
    """Marker mixin for a node that can enter Durable Stasis on delegated labor.

    The marker is execution policy, not decoration: any workflow containing one is
    assigned durable checkpoint persistence, and its Pattern station must declare
    ``kind="delegate"``.
    """


class PeerTaskNode:
    """Marker for a sovereign peer station requiring exact durable task ownership."""


type PatternNodeKind = Literal["step", "gate", "delegate", "peer", "terminal"]


def _validate_pattern_node_fields(key: str, label: str, kind: str) -> None:
    """Check declarative station meaning independently of executable bindings."""
    if kind not in {"step", "gate", "delegate", "peer", "terminal"}:
        msg = f"Unknown Pattern node kind: {kind!r}."
        raise ValueError(msg)
    if not key or not label:
        msg = "Pattern nodes require non-empty keys and labels."
        raise ValueError(msg)


@dataclass(frozen=True, kw_only=True)
class PatternNode:
    """One stable semantic station in an immutable Weaver Pattern revision."""

    key: str
    label: str
    kind: PatternNodeKind = "step"
    implementation: type[Any] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Require a known station kind, stable identity, and its declared implementation."""
        _validate_pattern_node_fields(self.key, self.label, self.kind)
        if self.kind == "terminal" and self.implementation is not None:
            msg = f"Terminal Pattern node '{self.key}' must remain declarative."
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
        if self.kind == "peer" and (self.implementation is None or not issubclass(self.implementation, PeerTaskNode)):
            msg = f"Peer Pattern node '{self.key}' must use a PeerTaskNode implementation."
            raise ValueError(msg)
        if self.implementation is not None and issubclass(self.implementation, PeerTaskNode) and self.kind != "peer":
            msg = f"PeerTaskNode implementation '{self.key}' must declare kind='peer'."
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

    def __post_init__(self) -> None:
        """Keep every declared edge a permission to traverse the score."""
        if self.relation != "permits":
            msg = "Pattern edges must declare relation='permits'."
            raise ValueError(msg)

    def snapshot(self) -> dict[str, str]:
        """Return the safe persisted projection."""
        return {
            "key": self.key,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
        }


def _validate_pattern_score(
    key: str,
    revision: str,
    entry_node: str,
    stations: tuple[tuple[str, str], ...],
    edges: tuple[PatternEdge, ...],
) -> None:
    """Require unique semantic stations and permissions with closed references."""
    node_keys = [node_key for node_key, _kind in stations]
    if len(node_keys) != len(set(node_keys)):
        msg = f"Pattern '{key}@{revision}' has duplicate node keys."
        raise ValueError(msg)
    entry_nodes = [kind for node_key, kind in stations if node_key == entry_node]
    if len(entry_nodes) != 1 or entry_nodes[0] == "terminal":
        msg = f"Pattern '{key}@{revision}' entry node must name one executable station."
        raise ValueError(msg)
    edge_keys = [edge.key for edge in edges]
    if len(edge_keys) != len(set(edge_keys)):
        msg = f"Pattern '{key}@{revision}' has duplicate edge keys."
        raise ValueError(msg)
    edge_pairs = [(edge.source, edge.target) for edge in edges]
    if len(edge_pairs) != len(set(edge_pairs)):
        msg = f"Pattern '{key}@{revision}' has duplicate semantic edges."
        raise ValueError(msg)
    unknown = {endpoint for edge in edges for endpoint in (edge.source, edge.target) if endpoint not in node_keys}
    if unknown:
        msg = f"Pattern '{key}@{revision}' edges reference unknown nodes: {sorted(unknown)}"
        raise ValueError(msg)


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
        _validate_pattern_score(
            self.key,
            self.revision,
            self.entry_node,
            tuple((node.key, node.kind) for node in self.nodes),
            self.edges,
        )

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
    graph: Graph[Any, Any, Any, Any]
    start_node: type[BaseNode[Any, Any, Any]]
    make_state: Callable[[Intent], BaseModel]
    manifest: PatternManifest
    # An executable revision may require checkpoint values to match its durable
    # admission. The worker binds the Intent; the runner checks each loaded state.
    validate_state: Callable[[Intent, BaseModel], None] | None = None
    bind_deps: Callable[[WorkflowServices], Any] | None = None
    # Derive checkpoint policy once from the graph's Gate and delegated stations.
    durable: bool = field(init=False)

    def __post_init__(self) -> None:
        """Validate the Pattern binding and derive the Durable-Stasis tier."""
        if self.manifest.key != self.name:
            msg = f"Workflow '{self.name}' must use a Pattern manifest with the same key."
            raise ValueError(msg)
        executable = {node.implementation for node in self.manifest.nodes if node.implementation is not None}
        graph_nodes = set(serial_graph_topology(self.graph)[0].values())
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
            any(issubclass(node, (Gate, DelegatedAgentNode, PeerTaskNode)) for node in graph_nodes),
        )

    def _validate_manifest_topology(self) -> None:
        """Require the semantic score to match executable and durable re-entry edges."""
        from pydantic_graph import EndNode, StartNode

        terminal_nodes = [node for node in self.manifest.nodes if node.kind == "terminal"]
        if len(terminal_nodes) != 1:
            msg = f"Pattern '{self.manifest.key}@{self.manifest.revision}' must declare exactly one terminal node."
            raise ValueError(msg)
        terminal_key = terminal_nodes[0].key
        keys_by_implementation = {
            node.implementation: node.key for node in self.manifest.nodes if node.implementation is not None
        }
        stations, routes = serial_graph_topology(self.graph)
        if {target for source, target in routes if source == StartNode.id} != {self.start_node.get_node_id()}:
            msg = f"Workflow '{self.name}' graph entry must match its Pattern entry station."
            raise ValueError(msg)
        executable_edges = {
            (
                keys_by_implementation[stations[source]],
                terminal_key if target == EndNode.id else keys_by_implementation[stations[target]],
            )
            for source, target in routes
            if source != StartNode.id
        }

        # A delegated station exits the in-process graph while parked and is later
        # re-entered at the same station. That lifecycle edge is executable policy
        # even when the Python return annotation only names the forward node. Gate
        # loops, by contrast, are ordinary graph return edges and remain explicit.
        executable_edges.update(
            (node.key, node.key) for node in self.manifest.nodes if node.kind in {"delegate", "peer"}
        )
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
        """Draw only admitted stations and permissions, including durable re-entry.

        Renderer aliases encode semantic keys, independent of Python class names or
        declaration order. Labels cannot introduce Mermaid syntax or directives.
        Revision and digest retain export provenance without granting execution authority.
        """
        aliases = {node.key: f"station_{node.key.encode().hex()}" for node in self.manifest.nodes}
        title = f"{self.title} ({self.manifest.key}@{self.manifest.revision})"
        lines = [
            "---",
            f"title: {json.dumps(title)}",
            "---",
            f"%% Pattern digest: {self.manifest.digest}",
            "stateDiagram-v2",
            "  direction LR",
        ]
        for node in self.manifest.nodes:
            label = f"{node.label} ({node.kind}) · {node.key}"
            escaped = "".join(char if char.isalnum() or char in " _-." else f"#{ord(char)};" for char in label)
            lines.append(f'  state "{escaped}" as {aliases[node.key]}')
        lines.extend(f"  {aliases[edge.source]} --> {aliases[edge.target]}" for edge in self.manifest.edges)
        if highlight is not None:
            lines.extend(
                (
                    f"  classDef highlighted {HIGHLIGHT_CSS}",
                    f"  class {aliases[self.manifest.node_key(highlight)]} highlighted",
                )
            )
        return "\n".join(lines)
