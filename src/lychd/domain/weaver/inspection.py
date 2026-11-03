"""Immutable, non-executable inspection of an exact v2 Pattern declaration."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

if TYPE_CHECKING:
    from lychd.agents.workflows.base import Workflow

type PatternIdentifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$", max_length=128)]
type InspectionIdentifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$", max_length=128)]


class InspectionValue(BaseModel):
    """Closed immutable values; no callables, Graph objects or arbitrary metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class InspectionNode(InspectionValue):
    key: PatternIdentifier
    label: str = Field(min_length=1, max_length=160)
    kind: Literal["step", "gate", "delegate", "peer", "terminal"]


class InspectionEdge(InspectionValue):
    key: PatternIdentifier
    source: PatternIdentifier
    target: PatternIdentifier
    relation: Literal["permits"] = "permits"


class PatternInspectionDescriptor(InspectionValue):
    """Safe score derived from the same manifest as its executable profile.

    The checksum is exactly the existing v2 semantic checksum. Source generation,
    publication and local executability belong to the separate host envelope.
    """

    schema_version: Literal[2] = 2
    pattern_id: PatternIdentifier
    revision: PatternIdentifier
    implementation_revision: PatternIdentifier
    checkpoint_schema: PatternIdentifier
    entry_node: PatternIdentifier
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=4096)
    trigger_hint: str = Field(max_length=512)
    nodes: tuple[InspectionNode, ...] = Field(min_length=1, max_length=128)
    edges: tuple[InspectionEdge, ...] = Field(max_length=256)

    def manifest_snapshot(self) -> dict[str, Any]:
        """Reconstruct the existing persisted declaration, with no envelope fields."""
        return {
            "schema_version": self.schema_version,
            "key": self.pattern_id,
            "revision": self.revision,
            "implementation_revision": self.implementation_revision,
            "checkpoint_schema": self.checkpoint_schema,
            "entry_node": self.entry_node,
            "nodes": [node.model_dump() for node in self.nodes],
            "edges": [edge.model_dump() for edge in self.edges],
            "digest": self.digest,
        }

    @model_validator(mode="after")
    def exact_score(self) -> PatternInspectionDescriptor:
        keys = {node.key for node in self.nodes}
        entry = next((node for node in self.nodes if node.key == self.entry_node), None)
        if len(keys) != len(self.nodes) or entry is None or entry.kind == "terminal":
            msg = "Inspection requires unique stations and an exact nonterminal entry."
            raise ValueError(msg)
        if len({edge.key for edge in self.edges}) != len(self.edges) or len(
            {(edge.source, edge.target) for edge in self.edges}
        ) != len(self.edges):
            msg = "Inspection permission identities must be unique."
            raise ValueError(msg)
        if any(edge.source not in keys or edge.target not in keys for edge in self.edges):
            msg = "Inspection permissions must reference declared stations."
            raise ValueError(msg)
        unsigned = self.manifest_snapshot()
        unsigned.pop("digest")
        encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        if sha256(encoded).hexdigest() != self.digest:
            msg = "Inspection does not match its exact v2 semantic digest."
            raise ValueError(msg)
        return self

    @classmethod
    def from_workflow(cls, workflow: Workflow) -> PatternInspectionDescriptor:
        """Copy declaration data only, never retain an executable closure."""
        snapshot = workflow.manifest.snapshot()
        return cls(
            schema_version=snapshot["schema_version"],
            pattern_id=snapshot["key"],
            revision=snapshot["revision"],
            implementation_revision=snapshot["implementation_revision"],
            checkpoint_schema=snapshot["checkpoint_schema"],
            entry_node=snapshot["entry_node"],
            digest=snapshot["digest"],
            title=workflow.title,
            description=workflow.description,
            trigger_hint=workflow.trigger.hint,
            nodes=tuple(InspectionNode(**node) for node in snapshot["nodes"]),
            edges=tuple(InspectionEdge(**edge) for edge in snapshot["edges"]),
        )

    def mermaid(self) -> str:
        """Render inert, escaped declaration text without invoking workflow code."""
        aliases = {node.key: f"station_{node.key.encode().hex()}" for node in self.nodes}
        title = f"{self.title} ({self.pattern_id}@{self.revision})"
        lines = [
            "---",
            f"title: {json.dumps(title)}",
            "---",
            f"%% Pattern digest: {self.digest}",
            "stateDiagram-v2",
            "  direction LR",
        ]
        for node in self.nodes:
            label = f"{node.label} ({node.kind}) · {node.key}"
            escaped = "".join(char if char.isalnum() or char in " _-." else f"#{ord(char)};" for char in label)
            lines.append(f'  state "{escaped}" as {aliases[node.key]}')
        lines.extend(f"  {aliases[edge.source]} --> {aliases[edge.target]}" for edge in self.edges)
        return "\n".join(lines)


class InspectionBinding(InspectionValue):
    """Host attribution and selection, deliberately outside the v2 checksum."""

    source_id: InspectionIdentifier
    registrant_id: str = Field(min_length=1, max_length=160)
    source_generation: InspectionIdentifier
    profile_id: InspectionIdentifier
    profile_revision: InspectionIdentifier
    publication: Literal["published", "observed"]
    executable: bool = False


class PatternInspectionEntry(InspectionValue):
    descriptor: PatternInspectionDescriptor
    binding: InspectionBinding
    detail_path: str


class InspectionContribution(InspectionValue):
    """One selected profile's pure declaration, before host provenance is bound."""

    source_id: InspectionIdentifier
    profile_id: InspectionIdentifier
    profile_revision: InspectionIdentifier
    descriptor: PatternInspectionDescriptor
