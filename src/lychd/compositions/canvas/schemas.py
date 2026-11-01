"""Closed, bounded portable records for the Canvas board authoring profile.

These records prove portable structure and proposal scope, not model transmission
or native media custody. Workspace retention belongs to Atlas. Revalidation is required at every
public operation because Python callers can still mutate a model's lists.
"""

from __future__ import annotations

import base64
import binascii
import json
import zlib
from dataclasses import dataclass
from typing import Annotated, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

MAX_PNG_BYTES = 512 * 1024
MAX_SCENE_BYTES = 2 * 1024 * 1024
MAX_PACKET_BYTES = 3 * 1024 * 1024
MAX_DOCUMENT_BYTES = 12 * 1024 * 1024
MAX_REVIEW_BYTES = 6 * 1024 * 1024
MAX_POINTS = 30_000
MAX_REVISION = 9_007_199_254_740_991
_PORTABLE_NUMBER_BUDGET = "0" * 24
_PNG_PREFIX = "data:image/png;base64,"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_MAX_DIMENSION = 1024
_PNG_IHDR_LENGTH = 13
_PNG_CHUNK_OVERHEAD = 12
_PNG_INDEXED_COLOR = 3
_PNG_GRAYSCALE_COLORS = frozenset({0, 4})
_PNG_PALETTE_CHANNELS = 3
_PNG_MAX_PALETTE_BYTES = 768
_PNG_ALLOWED_DEPTHS = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
_PNG_ANIMATION_CHUNKS = frozenset({b"acTL", b"fcTL", b"fdAT"})
_PNG_ENCODED_LIMIT = len(_PNG_PREFIX) + 4 * ((MAX_PNG_BYTES + 2) // 3)
_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

UUIDString = Annotated[str, Field(pattern=_UUID_PATTERN, min_length=36, max_length=36)]
Coordinate = Annotated[float, Field(ge=-100_000, le=100_000, allow_inf_nan=False)]
BoundCoordinate = Annotated[float, Field(ge=-102_000, le=102_000, allow_inf_nan=False)]
Dimension = Annotated[float, Field(gt=0, le=400_000, allow_inf_nan=False)]
Revision = Annotated[int, Field(ge=1, le=MAX_REVISION)]
Label = Annotated[str, Field(max_length=240)]
PNGDataURL = Annotated[str, Field(max_length=_PNG_ENCODED_LIMIT)]


class CanvasValidationError(ValueError):
    """A local record or proposed transaction violates the Canvas contract."""


def refuse(message: str) -> Never:
    """Raise a bounded contract failure without exposing imported document content."""
    raise CanvasValidationError(message)


def _png_bytes(data_url: str) -> bytes:
    """Admit only bounded canonical base64 with a PNG signature."""
    if type(data_url) is not str or len(data_url) > _PNG_ENCODED_LIMIT or not data_url.startswith(_PNG_PREFIX):
        refuse("Artwork must be a bounded local PNG data URL.")
    encoded = data_url[len(_PNG_PREFIX) :]
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        refuse("PNG base64 is invalid.")
    if len(raw) > MAX_PNG_BYTES or not raw.startswith(_PNG_SIGNATURE):
        refuse("PNG signature or byte limit is invalid.")
    if base64.b64encode(raw).decode("ascii") != encoded:
        refuse("PNG base64 must use canonical encoding.")
    return raw


def _png_chunk(raw: bytes, offset: int) -> tuple[bytes, bytes, int]:
    """Read one bounded alphabetic chunk and verify its CRC before dispatch."""
    if len(raw) - offset < _PNG_CHUNK_OVERHEAD:
        refuse("PNG chunk is truncated.")
    length = int.from_bytes(raw[offset : offset + 4], "big")
    kind = raw[offset + 4 : offset + 8]
    end = offset + _PNG_CHUNK_OVERHEAD + length
    if end > len(raw) or not kind.isalpha():
        refuse("PNG chunk envelope is invalid.")
    payload = raw[offset + 8 : end - 4]
    expected_crc = int.from_bytes(raw[end - 4 : end], "big")
    if zlib.crc32(kind + payload) != expected_crc:
        refuse("PNG chunk CRC is invalid.")
    return kind, payload, end


@dataclass(frozen=True, slots=True)
class _PNGHeader:
    width: int
    height: int
    bit_depth: int
    color_type: int


def _png_header(kind: bytes, payload: bytes) -> _PNGHeader:
    """Admit exactly one bounded IHDR and the supported PNG pixel modes."""
    if kind != b"IHDR" or len(payload) != _PNG_IHDR_LENGTH:
        refuse("PNG must begin with one IHDR chunk.")
    width = int.from_bytes(payload[:4], "big")
    height = int.from_bytes(payload[4:8], "big")
    bit_depth, color_type, compression, filtering, interlace = payload[8:]
    if (
        not 1 <= width <= _PNG_MAX_DIMENSION
        or not 1 <= height <= _PNG_MAX_DIMENSION
        or bit_depth not in _PNG_ALLOWED_DEPTHS.get(color_type, set())
        or compression != 0
        or filtering != 0
        or interlace not in {0, 1}
    ):
        refuse("PNG IHDR dimensions or modes are invalid.")
    return _PNGHeader(width=width, height=height, bit_depth=bit_depth, color_type=color_type)


@dataclass(slots=True)
class _PNGEnvelope:
    """Transient state for palette ordering, contiguous data and terminal IEND."""

    header: _PNGHeader
    palette: bool = False
    image_data: bool = False
    image_data_ended: bool = False
    image_data_bytes: int = 0

    def _accept_palette(self, length: int) -> None:
        if (
            self.palette
            or self.image_data
            or self.header.color_type in _PNG_GRAYSCALE_COLORS
            or not length
            or length % _PNG_PALETTE_CHANNELS
            or length > _PNG_MAX_PALETTE_BYTES
        ):
            refuse("PNG palette is invalid.")
        if self.header.color_type == _PNG_INDEXED_COLOR and length // _PNG_PALETTE_CHANNELS > 2**self.header.bit_depth:
            refuse("PNG palette exceeds its indexed depth.")
        self.palette = True

    def _accept_image_data(self, length: int) -> None:
        if self.image_data_ended or (self.header.color_type == _PNG_INDEXED_COLOR and not self.palette):
            refuse("PNG image data ordering is invalid.")
        self.image_data = True
        self.image_data_bytes += length

    def _accept_end(self, length: int, end: int, total: int) -> None:
        if length or not self.image_data or not self.image_data_bytes or end != total:
            refuse("PNG terminal chunk is invalid.")

    def accept(self, kind: bytes, length: int, end: int, total: int) -> bool:
        """Accept one verified post-header chunk; return whether it closes the PNG."""
        if kind == b"IHDR" or kind in _PNG_ANIMATION_CHUNKS:
            refuse("PNG must contain one static image.")
        if kind == b"PLTE":
            self._accept_palette(length)
        elif kind == b"IDAT":
            self._accept_image_data(length)
        elif kind == b"IEND":
            self._accept_end(length, end, total)
            return True
        elif kind[:1].isupper():
            refuse("PNG contains an unsupported critical chunk.")
        if self.image_data and kind != b"IDAT":
            self.image_data_ended = True
        return False


def png_dimensions(data_url: str) -> tuple[int, int]:
    """Validate a bounded PNG chunk envelope without decoding image pixels.

    No URL is fetched. CRCs, single-image structure, IHDR modes and image bounds
    are checked. This does not assert that compressed pixels render correctly.
    """
    raw = _png_bytes(data_url)
    kind, payload, offset = _png_chunk(raw, len(_PNG_SIGNATURE))
    header = _png_header(kind, payload)
    envelope = _PNGEnvelope(header)
    while offset < len(raw):
        kind, payload, end = _png_chunk(raw, offset)
        if envelope.accept(kind, len(payload), end, len(raw)):
            return header.width, header.height
        offset = end
    refuse("PNG has no terminal IEND chunk.")


class _CanvasRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, allow_inf_nan=False, revalidate_instances="always"
    )

    @field_validator("*", mode="before")
    @classmethod
    def valid_unicode(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                value.encode("utf-8", errors="strict")
            except UnicodeEncodeError:
                refuse("Canvas strings must contain valid Unicode scalar values.")
        return value


def _budget_value(value: JsonValue) -> JsonValue:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return _PORTABLE_NUMBER_BUDGET
    if isinstance(value, list):
        return [_budget_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _budget_value(item) for key, item in value.items()}
    return value


def portable_json_size(value: JsonValue) -> int:
    """Budget 26 ASCII bytes per number without changing the portable payload.

    Python and JavaScript spell some equal numbers differently. Their shared
    conservative admission budget replaces every number, excluding booleans,
    with one fixed 24-character string before compact UTF-8 JSON encoding.
    """
    budgeted = _budget_value(value)
    return len(json.dumps(budgeted, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def _bounded_json(record: BaseModel, maximum: int) -> None:
    if portable_json_size(record.model_dump(mode="json")) > maximum:
        refuse("Canvas record exceeds its portable size budget.")


def _unique(values: list[str], what: str) -> None:
    if len(values) != len(set(values)):
        refuse(f"Canvas {what} identities must be unique.")


class CanvasPoint(_CanvasRecord):
    x: Coordinate
    y: Coordinate


class CanvasBounds(_CanvasRecord):
    x: BoundCoordinate
    y: BoundCoordinate
    width: Dimension
    height: Dimension


class CanvasStroke(_CanvasRecord):
    id: UUIDString
    points: Annotated[list[CanvasPoint], Field(min_length=1, max_length=2048)]
    color: Annotated[str, Field(pattern=r"^#[0-9a-f]{6}$")]
    width: Annotated[float, Field(ge=1, le=16)]
    archived: bool


class CanvasArtwork(_CanvasRecord):
    png_data_url: PNGDataURL
    alt: Label
    provenance: Label

    @field_validator("png_data_url")
    @classmethod
    def valid_png(cls, value: str) -> str:
        png_dimensions(value)
        return value


class CanvasNode(_CanvasRecord):
    id: UUIDString
    x: Coordinate
    y: Coordinate
    width: Annotated[float, Field(ge=32, le=1600)]
    height: Annotated[float, Field(ge=32, le=1600)]
    label: Label
    kind: Literal["box", "database", "service", "person", "note"]
    pinned: bool
    source_stroke_ids: Annotated[list[UUIDString], Field(max_length=300)]
    artwork: CanvasArtwork | None

    @field_validator("source_stroke_ids")
    @classmethod
    def unique_source_ids(cls, values: list[str]) -> list[str]:
        _unique(values, "source stroke")
        return values


class CanvasEdge(_CanvasRecord):
    id: UUIDString
    source: UUIDString
    target: UUIDString
    label: Label
    source_stroke_ids: Annotated[list[UUIDString], Field(max_length=300)]

    @field_validator("source_stroke_ids")
    @classmethod
    def unique_source_ids(cls, values: list[str]) -> list[str]:
        _unique(values, "source stroke")
        return values


class CanvasScene(_CanvasRecord):
    format: Literal["lychd.canvas/1"]
    id: UUIDString
    revision: Revision
    title: Annotated[str, Field(min_length=1, max_length=120)]
    strokes: Annotated[list[CanvasStroke], Field(max_length=300)]
    nodes: Annotated[list[CanvasNode], Field(max_length=128)]
    edges: Annotated[list[CanvasEdge], Field(max_length=256)]

    @model_validator(mode="after")
    def valid_scene(self) -> Self:
        _unique([item.id for item in [*self.strokes, *self.nodes, *self.edges]], "object")
        if sum(len(stroke.points) for stroke in self.strokes) > MAX_POINTS:
            refuse("Canvas scene exceeds its total point limit.")
        strokes = {stroke.id for stroke in self.strokes}
        nodes = {node.id for node in self.nodes}
        for item in [*self.nodes, *self.edges]:
            if not set(item.source_stroke_ids) <= strokes:
                refuse("Canvas source references must name retained strokes.")
        for edge in self.edges:
            if edge.source not in nodes or edge.target not in nodes:
                refuse("Canvas edge endpoints must name existing nodes.")
        _bounded_json(self, MAX_SCENE_BYTES)
        return self


class CanvasDocument(_CanvasRecord):
    format: Literal["lychd.canvas.document/1"]
    scene: CanvasScene
    past: Annotated[list[CanvasScene], Field(max_length=20)]
    future: Annotated[list[CanvasScene], Field(max_length=20)]

    @model_validator(mode="after")
    def valid_document(self) -> Self:
        if any(scene.id != self.scene.id for scene in [*self.past, *self.future]):
            refuse("Canvas history must retain one scene identity.")
        _bounded_json(self, MAX_DOCUMENT_BYTES)
        return self


class CanvasSelection(_CanvasRecord):
    scene_id: UUIDString
    revision: Revision
    object_ids: Annotated[list[UUIDString], Field(min_length=1, max_length=128)]
    bounds: CanvasBounds

    @field_validator("object_ids")
    @classmethod
    def unique_ids(cls, values: list[str]) -> list[str]:
        _unique(values, "selection")
        return values


class CanvasCrop(_CanvasRecord):
    png_data_url: PNGDataURL
    width: Annotated[int, Field(ge=1, le=1024)]
    height: Annotated[int, Field(ge=1, le=1024)]
    bounds: CanvasBounds

    @model_validator(mode="after")
    def valid_crop(self) -> Self:
        if png_dimensions(self.png_data_url) != (self.width, self.height):
            refuse("Canvas crop dimensions must equal its PNG IHDR.")
        return self


class CanvasPacket(_CanvasRecord):
    format: Literal["lychd.canvas.selection/1"]
    scene: CanvasScene
    selection: CanvasSelection
    instruction: Annotated[str, Field(min_length=1, max_length=4000)]
    crop: CanvasCrop | None

    @model_validator(mode="after")
    def valid_packet(self) -> Self:
        if self.selection.scene_id != self.scene.id or self.selection.revision != self.scene.revision:
            refuse("Canvas selection must bind the captured scene revision.")
        visible = {item.id for item in [*self.scene.nodes, *self.scene.edges]}
        visible.update(stroke.id for stroke in self.scene.strokes if not stroke.archived)
        if not set(self.selection.object_ids) <= visible:
            refuse("Canvas selection must name visible captured objects.")
        if self.crop is not None and self.crop.bounds != self.selection.bounds:
            refuse("Canvas crop bounds must equal the captured selection bounds.")
        _bounded_json(self, MAX_PACKET_BYTES)
        return self


class CanvasProposal(_CanvasRecord):
    format: Literal["lychd.canvas.proposal/1"]
    id: UUIDString
    scene_id: UUIDString
    base_revision: Revision
    selection_ids: Annotated[list[UUIDString], Field(min_length=1, max_length=128)]
    author: Annotated[str, Field(min_length=1, max_length=120)]
    summary: Annotated[str, Field(min_length=1, max_length=1000)]
    nodes: Annotated[list[CanvasNode], Field(max_length=128)]
    edges: Annotated[list[CanvasEdge], Field(max_length=256)]
    archive_stroke_ids: Annotated[list[UUIDString], Field(max_length=128)]

    @model_validator(mode="after")
    def valid_proposal(self) -> Self:
        _unique(self.selection_ids, "proposal selection")
        _unique(self.archive_stroke_ids, "archive")
        _unique([item.id for item in [*self.nodes, *self.edges]], "proposal object")
        _bounded_json(self, MAX_SCENE_BYTES)
        return self


class CanvasReviewRequest(_CanvasRecord):
    packet: CanvasPacket
    proposal: CanvasProposal


class CanvasReviewResult(_CanvasRecord):
    scene: CanvasScene
    summary: Annotated[str, Field(min_length=1, max_length=1000)]


class CanvasContracts(_CanvasRecord):
    composition: Literal["canvas.board"] = "canvas.board"
    revision: Literal[2] = 2
    scene_format: Literal["lychd.canvas/1"] = "lychd.canvas/1"
    document_format: Literal["lychd.canvas.document/1"] = "lychd.canvas.document/1"
    packet_format: Literal["lychd.canvas.selection/1"] = "lychd.canvas.selection/1"
    proposal_format: Literal["lychd.canvas.proposal/1"] = "lychd.canvas.proposal/1"
    server_retention: Literal[True] = True
    model_transmission: Literal[False] = False
    image_generation: Literal[False] = False
