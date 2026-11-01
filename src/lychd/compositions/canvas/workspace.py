"""Deterministic, editable LychD reference board grounded in ``docs/map.md``.

This seed describes named architectural relationships. It is not a discovery
result, capability declaration, health projection, or execution receipt.
"""

from __future__ import annotations

from uuid import UUID, uuid5

from lychd.compositions.canvas.schemas import CanvasDocument, CanvasEdge, CanvasNode, CanvasScene

_WORKSPACE_NAMESPACE = UUID("d1ec7705-a329-5417-a064-9ca43737ec43")
# All newly created Project UUIDs beginning 1ec4d000 belong to system bootstrap.
# Replacing only these 32 bits preserves the derived UUID's version and variant.
_SYSTEM_PROJECT_PREFIX = bytes.fromhex("1ec4d000")


def is_reserved_system_project_id(project_id: UUID) -> bool:
    """Recognize the system range without rejecting unrelated caller UUID5 identities."""
    return project_id.bytes[:4] == _SYSTEM_PROJECT_PREFIX


def lychd_project_id(owner: str) -> UUID:
    """Reserve one stable system Project identity inside each Sigil boundary."""
    derived = uuid5(_WORKSPACE_NAMESPACE, owner)
    return UUID(bytes=_SYSTEM_PROJECT_PREFIX + derived.bytes[4:])


def lychd_workspace_document(owner: str) -> CanvasDocument:
    """Build native text and connections; every owner gets distinct stable identities."""
    scene_id = uuid5(lychd_project_id(owner), "primary-scene")
    positions = {
        "Canvas": (0, 0),
        "Atlas": (0, -180),
        "Bridge": (560, -180),
        "Orb": (840, -180),
        "Loom": (280, -180),
        "Nexus": (1120, 540),
        "Composition": (0, 180),
        "Weaver": (280, 180),
        "Run": (560, 180),
        "Graph": (840, 180),
        "Dispatcher": (840, 360),
        "Orchestrator": (840, 540),
        "Animator": (1120, 360),
        "Phylactery": (560, 540),
    }
    identities = {label: str(uuid5(scene_id, label)) for label in positions}
    nodes = [
        CanvasNode(
            id=identities[label],
            x=x,
            y=y,
            width=210,
            height=80,
            label=label,
            kind="database" if label == "Phylactery" else "box",
            pinned=False,
            source_stroke_ids=[],
            artwork=None,
        )
        for label, (x, y) in positions.items()
    ]
    relationships = [
        ("Atlas", "Canvas", "Catalogues Canvas Projects"),
        ("Canvas", "Composition", "Is an application"),
        ("Composition", "Weaver", "Owns the Pattern to resolve"),
        ("Weaver", "Run", "Resolves the exact Scroll pinned at admission"),
        ("Bridge", "Run", "Admits Intent and presents replies"),
        ("Orb", "Run", "Projects recorded evidence"),
        ("Loom", "Weaver", "Inspects the declared score"),
        ("Run", "Graph", "Casting carries Spell placements"),
        ("Run", "Phylactery", "Retained Run and checkpoints"),
        ("Graph", "Dispatcher", "Requests a faculty"),
        ("Dispatcher", "Animator", "Grants scoped use"),
        ("Dispatcher", "Orchestrator", "Requests managed readiness"),
        ("Nexus", "Orchestrator", "Projects physical readiness"),
    ]
    edges = [
        CanvasEdge(
            id=str(uuid5(scene_id, f"{source}:{target}")),
            source=identities[source],
            target=identities[target],
            label=label,
            source_stroke_ids=[],
        )
        for source, target, label in relationships
    ]
    return CanvasDocument(
        format="lychd.canvas.document/1",
        scene=CanvasScene(
            format="lychd.canvas/1",
            id=str(scene_id),
            revision=1,
            title="LychD — static architecture reference",
            strokes=[],
            nodes=nodes,
            edges=edges,
        ),
        past=[],
        future=[],
    )
