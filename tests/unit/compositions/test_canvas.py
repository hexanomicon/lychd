"""Failure-oriented tests for local Canvas custody and pure review."""

from __future__ import annotations

import base64
import json
import struct
import zlib
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import JsonValue, ValidationError

from lychd.compositions.canvas.operations import (
    apply_proposal,
    bounds_of_selection,
    make_packet,
    object_bounds,
    select_in_bounds,
    validate_document,
    validate_proposal,
)
from lychd.compositions.canvas.schemas import (
    MAX_DOCUMENT_BYTES,
    MAX_REVISION,
    MAX_SCENE_BYTES,
    CanvasArtwork,
    CanvasBounds,
    CanvasCrop,
    CanvasDocument,
    CanvasEdge,
    CanvasNode,
    CanvasPacket,
    CanvasPoint,
    CanvasProposal,
    CanvasScene,
    CanvasStroke,
    CanvasValidationError,
    png_dimensions,
    portable_json_size,
)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def _png(*, width: int = 1, height: int = 1, extra: bytes = b"", scanline: bytes = b"\x00\x00\x00\x00\xff") -> str:
    raw = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + extra
        + _chunk(b"IDAT", zlib.compress(scanline))
        + _chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _node(*, identity: str | None = None, x: float = 0, label: str = "Draft") -> CanvasNode:
    return CanvasNode(
        id=identity or str(uuid4()),
        x=x,
        y=0,
        width=120,
        height=60,
        label=label,
        kind="box",
        pinned=False,
        source_stroke_ids=[],
        artwork=None,
    )


def _scene() -> CanvasScene:
    inside, outside = _node(), _node(x=500, label="Untouched")
    stroke = CanvasStroke(
        id=str(uuid4()),
        points=[CanvasPoint(x=-5, y=-5), CanvasPoint(x=100, y=50)],
        color="#abcdef",
        width=2,
        archived=False,
    )
    return CanvasScene(
        format="lychd.canvas/1",
        id=str(uuid4()),
        revision=1,
        title="Illustrative fixture",
        strokes=[stroke],
        nodes=[inside, outside],
        edges=[
            CanvasEdge(id=str(uuid4()), source=inside.id, target=outside.id, label="Existing", source_stroke_ids=[])
        ],
    )


def _packet(scene: CanvasScene) -> CanvasPacket:
    return make_packet(
        scene,
        [scene.strokes[0].id, scene.nodes[0].id],
        CanvasBounds(x=-10, y=-10, width=150, height=100),
        "Turn the selected ink into an editable step.",
    )


def _proposal(packet: CanvasPacket, **changes: Any) -> CanvasProposal:
    values: dict[str, Any] = {
        "format": "lychd.canvas.proposal/1",
        "id": str(uuid4()),
        "scene_id": packet.scene.id,
        "base_revision": packet.scene.revision,
        "selection_ids": packet.selection.object_ids,
        "author": "Explicit test fixture",
        "summary": "Create one editable step.",
        "nodes": [_node(label="Editable")],
        "edges": [],
        "archive_stroke_ids": [packet.scene.strokes[0].id],
    }
    values.update(changes)
    return CanvasProposal.model_validate(values)


def _document(scene: CanvasScene) -> CanvasDocument:
    return CanvasDocument(format="lychd.canvas.document/1", scene=scene, past=[], future=[])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -100001, 100001, True, "12"])
def test_coordinates_reject_nonfinite_outside_and_coerced_values(value: object) -> None:
    with pytest.raises(ValidationError):
        CanvasPoint.model_validate({"x": value, "y": 0})


def test_closed_records_reject_unknown_fields_and_noncanonical_identity() -> None:
    with pytest.raises(ValidationError):
        CanvasPoint.model_validate({"x": 0, "y": 0, "script": "inert text"})
    node = _node().model_dump()
    node["id"] = "ABCDEFAB-0000-0000-0000-000000000000"
    with pytest.raises(ValidationError):
        CanvasNode.model_validate(node)


def test_selection_dimensions_are_positive_finite_and_arithmetically_bounded() -> None:
    assert CanvasBounds(x=-100000, y=-100000, width=400000, height=200000).width == 400000
    for width in (0, -1, 400001, 1e308, float("inf")):
        with pytest.raises(ValidationError):
            CanvasBounds(x=0, y=0, width=width, height=1)


def test_portable_strings_reject_surrogates_but_preserve_valid_unicode() -> None:
    node = _node(label="Database 😀")
    assert CanvasNode.model_validate_json(node.model_dump_json()).label == "Database 😀"
    for label in ("\ud800", "bad\udfff", "\ud83d\ude00"):
        with pytest.raises(ValidationError, match="Unicode"):
            CanvasNode.model_validate(node.model_copy(update={"label": label}))


def test_revision_is_exactly_representable_and_successor_cannot_overflow() -> None:
    scene = CanvasScene.model_validate(_scene().model_copy(update={"revision": MAX_REVISION}))
    packet = _packet(scene)
    proposal = _proposal(packet)
    before = scene.model_dump_json()
    with pytest.raises(ValidationError):
        apply_proposal(scene, proposal, packet)
    assert scene.model_dump_json() == before
    with pytest.raises(ValidationError):
        CanvasScene.model_validate(scene.model_copy(update={"revision": MAX_REVISION + 1}))


def test_scene_rejects_cross_category_identity_and_dangling_references() -> None:
    scene = _scene()
    node = scene.nodes[0].model_copy(update={"id": scene.strokes[0].id})
    with pytest.raises(ValidationError, match="unique"):
        CanvasScene.model_validate(scene.model_copy(update={"nodes": [node, scene.nodes[1]]}))
    node = scene.nodes[0].model_copy(update={"source_stroke_ids": [str(uuid4())]})
    with pytest.raises(ValidationError, match="source references"):
        CanvasScene.model_validate(scene.model_copy(update={"nodes": [node, scene.nodes[1]]}))
    edge = scene.edges[0].model_copy(update={"target": str(uuid4())})
    with pytest.raises(ValidationError, match="endpoints"):
        CanvasScene.model_validate(scene.model_copy(update={"edges": [edge]}))


def test_source_references_are_unique_for_nodes_and_edges() -> None:
    scene = _scene()
    repeated = [scene.strokes[0].id, scene.strokes[0].id]
    for item in (scene.nodes[0], scene.edges[0]):
        values = item.model_dump()
        values["source_stroke_ids"] = repeated
        with pytest.raises(ValidationError, match=r"source stroke.*unique"):
            type(item).model_validate(values)


def test_scene_rejects_total_point_limit_even_when_each_stroke_is_bounded() -> None:
    scene = _scene()
    strokes = [
        CanvasStroke(
            id=str(uuid4()),
            points=[CanvasPoint(x=0, y=0)] * 2048,
            color="#ffffff",
            width=1,
            archived=False,
        )
        for _ in range(15)
    ]
    with pytest.raises(ValidationError, match="total point"):
        CanvasScene.model_validate(scene.model_copy(update={"strokes": strokes}))


def test_document_roundtrip_keeps_exact_source_geometry_and_history() -> None:
    scene = _scene()
    current = scene.model_copy(update={"revision": 2})
    document = CanvasDocument(format="lychd.canvas.document/1", scene=current, past=[scene], future=[])
    restored = validate_document(document.model_dump_json())
    assert restored == document
    assert restored.past[0].strokes[0].points == scene.strokes[0].points


def test_document_rejects_foreign_history_excess_history_and_raw_bytes() -> None:
    document = _document(_scene())
    values = document.model_dump()
    values["past"] = [_scene().model_dump()]
    with pytest.raises(ValidationError, match="one scene identity"):
        validate_document(values)
    values["past"] = [document.scene.model_dump()] * 21
    with pytest.raises(ValidationError):
        validate_document(values)
    with pytest.raises(CanvasValidationError, match="byte limit"):
        validate_document(b" " * (MAX_DOCUMENT_BYTES + 1))


def test_mutated_model_lists_are_revalidated_at_public_boundaries() -> None:
    document = _document(_scene())
    document.scene.strokes[0].points.append(CanvasPoint.model_construct(x=float("nan"), y=0))
    with pytest.raises(ValidationError):
        validate_document(document)


def test_marquee_selects_intersecting_whole_objects_and_excludes_archived_ink() -> None:
    scene = _scene()
    area = CanvasBounds(x=-10, y=-10, width=20, height=20)
    selected = select_in_bounds(scene, area)
    assert scene.strokes[0].id in selected
    assert scene.nodes[0].id in selected
    assert scene.nodes[1].id not in selected
    assert bounds_of_selection(scene, [scene.strokes[0].id]) == CanvasBounds(x=-6, y=-6, width=107, height=57)
    archived = scene.strokes[0].model_copy(update={"archived": True})
    changed = CanvasScene.model_validate(scene.model_copy(update={"strokes": [archived]}))
    assert archived.id not in select_in_bounds(changed, area)
    with pytest.raises(ValidationError, match="visible"):
        _packet(changed)


@pytest.mark.parametrize(
    ("points", "marquee", "expected"),
    [
        (
            [(0, 0), (100, 0)],
            CanvasBounds(x=50, y=-6, width=10, height=2),
            CanvasBounds(x=-8, y=-8, width=116, height=16),
        ),
        (
            [(0, 0), (0, 100)],
            CanvasBounds(x=-6, y=50, width=2, height=10),
            CanvasBounds(x=-8, y=-8, width=16, height=116),
        ),
        (
            [(0, 0)],
            CanvasBounds(x=-6, y=-1, width=2, height=2),
            CanvasBounds(x=-8, y=-8, width=16, height=16),
        ),
        (
            [(-100000, -100000), (100000, 100000)],
            CanvasBounds(x=-100007, y=-100001, width=2, height=2),
            CanvasBounds(x=-100008, y=-100008, width=200016, height=200016),
        ),
    ],
)
def test_stroke_selection_and_capture_bounds_include_painted_width(
    points: list[tuple[int, int]], marquee: CanvasBounds, expected: CanvasBounds
) -> None:
    scene = _scene()
    stroke = scene.strokes[0].model_copy(update={"points": [CanvasPoint(x=x, y=y) for x, y in points], "width": 16})
    scene = CanvasScene.model_validate(scene.model_copy(update={"strokes": [stroke]}))
    assert object_bounds(scene, stroke.id) == expected
    assert bounds_of_selection(scene, [stroke.id]) == expected
    assert stroke.id in select_in_bounds(scene, marquee)


def test_derived_bound_origins_have_separate_finite_limits() -> None:
    assert CanvasBounds(x=-102000, y=102000, width=1, height=1).x == -102000
    for x in (-102001, 102001):
        with pytest.raises(ValidationError):
            CanvasBounds(x=x, y=0, width=1, height=1)
    with pytest.raises(ValidationError):
        CanvasPoint(x=-100008, y=0)


def test_canonical_frontend_fixture_matches_python_review_and_object_bounds() -> None:
    path = Path(__file__).resolve().parents[3] / "clients/web/src/lib/pages/canvas/state/parity.json"
    fixture = cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
    document = validate_document(fixture["document"])
    packet = CanvasPacket.model_validate(fixture["packet"])
    proposal = validate_proposal(fixture["proposal"], packet)
    assert document.scene == packet.scene
    assert apply_proposal(document.scene, proposal, packet).model_dump(mode="json") == fixture["expected_scene"]
    for expected in fixture["expected_bounds"]:
        assert object_bounds(document.scene, expected["id"]) == CanvasBounds.model_validate(expected["bounds"])


def test_canonical_self_loop_fixture_includes_rendered_curve_and_marquee_hit() -> None:
    path = Path(__file__).resolve().parents[3] / "clients/web/src/lib/pages/canvas/state/parity.json"
    fixture = cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))["self_loop_case"]
    scene = CanvasScene.model_validate(fixture["scene"])
    expected = CanvasBounds.model_validate(fixture["expected_bounds"])
    assert object_bounds(scene, fixture["edge_id"]) == expected
    assert bounds_of_selection(scene, [fixture["edge_id"]]) == expected
    assert fixture["edge_id"] in select_in_bounds(scene, CanvasBounds(x=expected.x, y=expected.y, width=10, height=10))


def test_portable_size_budget_treats_numeric_spellings_equally_without_changing_flags() -> None:
    values: dict[str, JsonValue] = {"integer": 1, "real": 1.0, "enabled": True, "title": "😀"}
    expected = {"integer": "0" * 24, "real": "0" * 24, "enabled": True, "title": "😀"}
    size = len(json.dumps(expected, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    assert portable_json_size(values) == size
    assert portable_json_size({"n": 1}) == portable_json_size({"n": 1.0})
    assert values == {"integer": 1, "real": 1.0, "enabled": True, "title": "😀"}


def _size_recipe_scene(recipe: dict[str, Any]) -> dict[str, Any]:
    point_count = cast("int", recipe["point_count"])
    node_count = cast("int", recipe["node_count"])
    png_padding = cast("int", recipe["png_padding"])
    strokes = [
        {
            "id": f"20000000-0000-0000-0000-{index:012x}",
            "points": [{"x": 1, "y": 1} for _ in range(min(2048, point_count - start))],
            "color": "#ffffff",
            "width": 2,
            "archived": False,
        }
        for index, start in enumerate(range(0, point_count, 2048))
    ]
    artwork = {
        "png_data_url": _png(extra=_chunk(b"tEXt", b"A" * png_padding), scanline=b"\x00" * 5),
        "alt": "Budget fixture",
        "provenance": "Synthetic local PNG",
    }
    nodes = [
        {
            **_node(identity=f"30000000-0000-0000-0000-{index:012x}").model_dump(mode="json"),
            "artwork": artwork,
        }
        for index in range(node_count)
    ]
    return {
        "format": "lychd.canvas/1",
        "id": "10000000-0000-0000-0000-000000000000",
        "revision": 1,
        "title": recipe["name"],
        "strokes": strokes,
        "nodes": nodes,
        "edges": [],
    }


def test_shared_size_recipes_have_identical_portable_admission() -> None:
    path = Path(__file__).resolve().parents[3] / "clients/web/src/lib/pages/canvas/state/parity.json"
    fixture = cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
    for recipe in fixture["size_recipes"]:
        values = _size_recipe_scene(recipe)
        raw_bytes = len(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        assert raw_bytes < MAX_SCENE_BYTES
        if recipe["expected_valid"]:
            scene = CanvasScene.model_validate(values)
            assert sum(len(stroke.points) for stroke in scene.strokes) == recipe["point_count"]
        else:
            with pytest.raises(ValidationError, match="portable size budget"):
                CanvasScene.model_validate(values)
        assert values["strokes"][0]["points"][0] == {"x": 1, "y": 1}


def test_crop_binds_actual_png_dimensions_and_exact_selection_bounds() -> None:
    scene = _scene()
    packet = _packet(scene)
    crop = CanvasCrop(png_data_url=_png(), width=1, height=1, bounds=packet.selection.bounds)
    captured = make_packet(scene, packet.selection.object_ids, packet.selection.bounds, "Review", crop)
    assert captured.crop == crop
    with pytest.raises(ValidationError, match="IHDR"):
        CanvasCrop(png_data_url=_png(), width=2, height=1, bounds=packet.selection.bounds)
    wrong = crop.model_copy(update={"bounds": CanvasBounds(x=0, y=0, width=1, height=1)})
    with pytest.raises(ValidationError, match="crop bounds"):
        make_packet(scene, packet.selection.object_ids, packet.selection.bounds, "Review", wrong)


def test_packet_rejects_duplicate_selection_and_mixed_revision() -> None:
    packet = _packet(_scene())
    values = packet.model_dump()
    values["selection"]["revision"] += 1
    with pytest.raises(ValidationError, match="captured scene revision"):
        CanvasPacket.model_validate(values)
    values = packet.model_dump()
    values["selection"]["object_ids"] *= 2
    with pytest.raises(ValidationError, match="unique"):
        CanvasPacket.model_validate(values)


def test_apply_preserves_external_edges_and_original_ink_atomically() -> None:
    scene = _scene()
    packet = _packet(scene)
    added = _node(label="New step")
    proposal = _proposal(
        packet,
        nodes=[scene.nodes[0].model_copy(update={"label": "Reviewed"}), added],
        edges=[
            CanvasEdge(
                id=str(uuid4()),
                source=added.id,
                target=scene.nodes[1].id,
                label="Read-only context",
                source_stroke_ids=[],
            )
        ],
    )
    before = scene.model_dump_json()
    result = apply_proposal(scene, proposal, packet)
    assert result.revision == scene.revision + 1
    assert result.nodes[1] == scene.nodes[1]
    assert result.edges[0] == scene.edges[0]
    assert result.edges[1].target == scene.nodes[1].id
    assert result.strokes[0].archived is True
    assert result.strokes[0].model_dump(exclude={"archived"}) == scene.strokes[0].model_dump(exclude={"archived"})
    assert scene.model_dump_json() == before


def test_apply_rejects_outside_selection_change_and_category_replacement() -> None:
    scene = _scene()
    packet = _packet(scene)
    proposal = _proposal(packet, nodes=[scene.nodes[1].model_copy(update={"label": "Unauthorized"})])
    with pytest.raises(CanvasValidationError, match="unselected"):
        apply_proposal(scene, proposal, packet)
    proposal = _proposal(packet, nodes=[_node(identity=scene.strokes[0].id)])
    with pytest.raises(CanvasValidationError, match="category"):
        apply_proposal(scene, proposal, packet)


def test_apply_rejects_stale_scene_and_same_revision_substitution() -> None:
    scene = _scene()
    packet = _packet(scene)
    proposal = _proposal(packet)
    for changed in (scene.model_copy(update={"revision": 2}), scene.model_copy(update={"title": "Changed"})):
        with pytest.raises(CanvasValidationError, match="stale"):
            apply_proposal(changed, proposal, packet)
    stale = proposal.model_copy(update={"base_revision": 2})
    with pytest.raises(CanvasValidationError, match="stale"):
        apply_proposal(scene, stale, packet)
    successor = apply_proposal(scene, proposal, packet)
    with pytest.raises(CanvasValidationError, match="stale"):
        apply_proposal(successor, proposal, packet)


def test_apply_late_reference_failure_leaves_every_input_unchanged() -> None:
    scene = _scene()
    packet = _packet(scene)
    proposal = _proposal(
        packet,
        edges=[
            CanvasEdge(
                id=str(uuid4()), source=scene.nodes[0].id, target=str(uuid4()), label="Invalid", source_stroke_ids=[]
            )
        ],
    )
    before = (scene.model_dump_json(), packet.model_dump_json(), proposal.model_dump_json())
    with pytest.raises(ValidationError, match="endpoints"):
        apply_proposal(scene, proposal, packet)
    assert (scene.model_dump_json(), packet.model_dump_json(), proposal.model_dump_json()) == before


def test_proposal_import_cannot_expand_selection_or_archive_context() -> None:
    scene = _scene()
    packet = _packet(scene)
    changed = _proposal(packet, selection_ids=[scene.nodes[1].id])
    with pytest.raises(CanvasValidationError, match="selection"):
        validate_proposal(changed.model_dump_json(), packet)
    changed = _proposal(packet, archive_stroke_ids=[scene.nodes[0].id])
    with pytest.raises(CanvasValidationError, match="archive"):
        validate_proposal(changed, packet)


def test_proposal_source_claims_are_limited_to_selected_visible_ink() -> None:
    scene = _scene()
    context = scene.strokes[0].model_copy(update={"id": str(uuid4())})
    scene = CanvasScene.model_validate(scene.model_copy(update={"strokes": [*scene.strokes, context]}))
    packet = _packet(scene)
    node = _node().model_copy(update={"source_stroke_ids": [context.id]})
    with pytest.raises(CanvasValidationError, match="source references only to selected"):
        apply_proposal(scene, _proposal(packet, nodes=[node]), packet)
    edge = scene.edges[0].model_copy(update={"id": str(uuid4()), "source_stroke_ids": [context.id]})
    with pytest.raises(CanvasValidationError, match="source references only to selected"):
        apply_proposal(scene, _proposal(packet, edges=[edge]), packet)
    selected_node = scene.nodes[0].model_copy(update={"source_stroke_ids": [context.id]})
    retained = CanvasScene.model_validate(scene.model_copy(update={"nodes": [selected_node, scene.nodes[1]]}))
    packet = _packet(retained)
    updated = selected_node.model_copy(
        update={"label": "Preserved provenance", "source_stroke_ids": [context.id, scene.strokes[0].id]}
    )
    result = apply_proposal(retained, _proposal(packet, nodes=[updated]), packet)
    assert result.nodes[0].source_stroke_ids == [context.id, scene.strokes[0].id]


def test_self_loop_is_valid_and_labels_remain_separate_from_artwork() -> None:
    scene = _scene()
    packet = _packet(scene)
    node = _node(label="DB")
    artwork = CanvasArtwork(png_data_url=_png(), alt="Symbolic database", provenance="Local test PNG")
    node = node.model_copy(update={"artwork": artwork})
    edge = CanvasEdge(id=str(uuid4()), source=node.id, target=node.id, label="Retry", source_stroke_ids=[])
    result = apply_proposal(scene, _proposal(packet, nodes=[node], edges=[edge]), packet)
    assert result.nodes[-1].label == "DB"
    assert result.nodes[-1].artwork == artwork
    assert result.edges[-1].source == result.edges[-1].target


@pytest.mark.parametrize(
    "value", ["https://example.invalid/art.png", "data:image/svg+xml;base64,AAAA", "data:image/png;base64,%%%%"]
)
def test_artwork_refuses_remote_or_non_png_imports(value: str) -> None:
    with pytest.raises(CanvasValidationError):
        png_dimensions(value)


def test_png_envelope_refuses_crc_truncation_dimensions_critical_chunks_and_animation() -> None:
    assert png_dimensions(_png()) == (1, 1)
    raw = base64.b64decode(_png().partition(",")[2])
    malformed = [
        raw[:-1],
        raw[:29] + bytes([raw[29] ^ 1]) + raw[30:],
        base64.b64decode(_png(width=1025).partition(",")[2]),
        base64.b64decode(_png(extra=_chunk(b"EXEC", b"inert")).partition(",")[2]),
        base64.b64decode(_png(extra=_chunk(b"acTL", b"inert")).partition(",")[2]),
        raw + b"trailing",
    ]
    for payload in malformed:
        with pytest.raises(CanvasValidationError):
            png_dimensions("data:image/png;base64," + base64.b64encode(payload).decode("ascii"))


def test_import_rejects_hidden_extra_fields_without_interpreting_text() -> None:
    document = _document(_scene()).model_dump()
    document["scene"]["nodes"][0]["label"] = '<script>alert("inert")</script>'
    assert validate_document(document).scene.nodes[0].label == '<script>alert("inert")</script>'
    document["scene"]["nodes"][0]["html"] = "not admitted"
    with pytest.raises(ValidationError):
        validate_document(json.dumps(document))
