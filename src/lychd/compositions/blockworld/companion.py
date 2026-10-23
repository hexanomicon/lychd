"""Finite companion authority and native Graph, with opt-in bounded interpretation."""

from __future__ import annotations

import asyncio
import json
import math
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Protocol, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.blockworld.companion_intent import CompanionInstruction
from lychd.domain.artifacts import ArtifactRef
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.graph import build_serial_graph

MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 65536
MAX_ACTIONS = 256
MAX_QUEUE = 8
MAX_CHAT = 200
MAX_INSTRUCTION_CHARS = 1000
COORDINATE_COUNT = 3
CONTROL_CHAR = 32
DELETE_CHAR = 127
CLOCK_HALF_PERIOD = 12_000


def canonical_uuid(value: str) -> str:
    if str(UUID(value)) != value:
        msg = "Identity must be a canonical UUID."
        raise ValueError(msg)
    return value


def strict_json(document: str | bytes, *, limit: int = MAX_REQUEST_BYTES) -> Any:
    """Decode bounded UTF-8 JSON, refusing duplicate keys and non-finite values."""
    raw = document.encode("utf-8") if isinstance(document, str) else document
    if len(raw) > limit:
        msg = "JSON body exceeds its byte limit."
        raise ValueError(msg)

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                msg = "Duplicate JSON key."
                raise ValueError(msg)
            result[key] = value
        return result

    def invalid(_: str) -> Any:
        msg = "Non-finite JSON number."
        raise ValueError(msg)

    def finite(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            return invalid(value)
        return number

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid, parse_float=finite)


class CompanionDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)

    @field_validator("protocol", mode="before", check_fields=False)
    @classmethod
    def exact_protocol(cls, value: Any) -> Any:
        if type(value) is not int or value != 1:
            msg = "Protocol must be original integer 1."
            raise ValueError(msg)
        return value


class SimpleAction(CompanionDocument):
    kind: Literal["state", "idle"]


class PointAction(CompanionDocument):
    kind: Literal["look", "goto"]
    x: float
    y: float
    z: float

    @field_validator("x", "y", "z", mode="before")
    @classmethod
    def original_number(cls, value: Any) -> Any:
        if type(value) not in (int, float) or not math.isfinite(value):
            msg = "Coordinates must be finite original numbers."
            raise ValueError(msg)
        return value


class FollowAction(CompanionDocument):
    kind: Literal["follow"]
    target_id: str
    _uuid = field_validator("target_id")(canonical_uuid)


CellCoordinate = Annotated[int, Field(ge=-30_000_000, le=30_000_000)]
RegistryName = Annotated[str, Field(max_length=160, pattern=r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")]
PropertyName = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")]


class CellAction(CompanionDocument):
    """One explicitly versioned read; coordinates are original integers, never rounded."""

    kind: Literal["inspect"]
    revision: Literal[1] = 1
    x: CellCoordinate
    y: CellCoordinate
    z: CellCoordinate

    @field_validator("revision", mode="before")
    @classmethod
    def exact_revision(cls, value: Any) -> Any:
        if type(value) is not int or value != 1:
            msg = "Inspection revision must be original integer 1."
            raise ValueError(msg)
        return value


class SayAction(CompanionDocument):
    kind: Literal["say"]
    text: str = Field(min_length=1, max_length=MAX_CHAT)

    @field_validator("text")
    @classmethod
    def ordinary_chat(cls, value: str) -> str:
        if value != value.strip() or value.startswith("/") or any(unicodedata.category(char) == "Cc" for char in value):
            msg = "Chat must be ordinary text without controls or a command prefix."
            raise ValueError(msg)
        return value


class WeatherAction(CompanionDocument):
    """A separately authorized, fixed server-weather timer programme."""

    kind: Literal["weather"]
    revision: Literal[1] = 1
    scope: Literal["server_weather"] = "server_weather"
    mode: Literal["clear", "rain"]
    duration_ticks: Literal[600] = 600

    @field_validator("revision", "duration_ticks", mode="before")
    @classmethod
    def original_integer(cls, value: Any) -> Any:
        if type(value) is not int:
            msg = "Weather revision and duration require original integers."
            raise ValueError(msg)
        return value


class TimeAction(CompanionDocument):
    """Place the supported clock at its next/equal marker, without numeric time authority."""

    kind: Literal["time"]
    revision: Literal[1] = 1
    scope: Literal["overworld_clock"] = "overworld_clock"
    mode: Literal["day", "night", "toggle"]

    @field_validator("revision", mode="before")
    @classmethod
    def original_revision(cls, value: Any) -> Any:
        if type(value) is not int:
            msg = "Time revision requires an original integer."
            raise ValueError(msg)
        return value


CompanionAction = Annotated[
    SimpleAction | PointAction | FollowAction | SayAction | CellAction | WeatherAction | TimeAction,
    Field(discriminator="kind"),
]
ACTION_ADAPTER = TypeAdapter(CompanionAction)


class CompanionRequest(CompanionDocument):
    request_id: str
    action: CompanionAction
    transcript: str = Field(default="", max_length=1000)
    source: Literal["text", "transcript"] = "text"
    generation: int = Field(default=0, ge=0)
    expires_at_ms: int | None = Field(default=None, gt=0)
    source_artifacts: tuple[ArtifactRef, ...] = Field(default=(), max_length=4)
    _uuid = field_validator("request_id")(canonical_uuid)

    @field_validator("source_artifacts", mode="before")
    @classmethod
    def artifact_sequence(cls, value: Any) -> Any:
        return tuple(cast("list[Any]", value)) if type(value) is list else value


def decode_request(document: str) -> CompanionRequest:
    return CompanionRequest.model_validate(strict_json(document))


def parse_text(text: str, *, target_id: str | None = None) -> CompanionAction:
    """Accept only the documented exact SK/CZ/EN forms; stop is out of band.

    Follow requires an explicitly supplied target UUID, either as its only
    argument or as target_id for the bare verb. No player is inferred.
    """
    if len(text) > MAX_INSTRUCTION_CHARS or any(unicodedata.category(char) == "Cc" for char in text):
        msg = "Instruction is too large or contains control characters."
        raise ValueError(msg)
    value = text.strip()
    word = value.casefold().rstrip(".!?")
    environment = _fixed_environment(word)
    if environment is not None:
        return environment
    if word in {"state", "stav"}:
        return SimpleAction(kind="state")
    if word in {"idle", "čakaj", "cakaj", "čekej", "cekej", "oddychuj", "odpočívej"}:
        return SimpleAction(kind="idle")
    if word in {"follow me", "nasleduj ma", "následuj mě", "nasleduj me"} and target_id is not None:
        return FollowAction(kind="follow", target_id=target_id)
    head, _, tail = value.partition(" ")
    if head.casefold() in {"time", "čas", "cas"}:
        return _parse_clock_mode(head.casefold(), tail)
    return _parse_arguments(head.casefold(), tail, target_id)


def _fixed_environment(word: str) -> WeatherAction | TimeAction | None:
    """Keep fixed environment phrases outside the optional NPC interpreter."""
    if word in {"daj jasno", "nastav jasno", "clear weather"}:
        return WeatherAction(kind="weather", mode="clear")
    if word in {"spusti dážď", "spusti dazd", "spusť déšť", "spust dest", "make it rain"}:
        return WeatherAction(kind="weather", mode="rain")
    if word in {
        "prepni deň noc",
        "prepni den noc",
        "prepni deň/noc",
        "prepni den/noc",
        "přepni den noc",
        "přepni den/noc",
        "toggle day night",
        "toggle day/night",
    }:
        return TimeAction(kind="time", mode="toggle")
    if word in {"nastav deň", "nastav den", "set day", "make it day"}:
        return TimeAction(kind="time", mode="day")
    if word in {"nastav noc", "set night", "make it night"}:
        return TimeAction(kind="time", mode="night")
    return None


def _parse_arguments(command: str, tail: str, target_id: str | None) -> CompanionAction:
    """Keep explicit argument grammars separate from the bare command vocabulary."""
    if command in {"weather", "počasie", "pocasie", "počasí", "pocasi"}:
        modes = (
            {"clear": "clear", "rain": "rain"}
            if command == "weather"
            else {"jasno": "clear", "dážď": "rain", "dazd": "rain", "déšť": "rain", "dest": "rain"}
        )
        mode = modes.get(tail.casefold().rstrip(".!?"))
        if mode is not None:
            return WeatherAction(kind="weather", mode=cast("Literal['clear', 'rain']", mode))
        msg = "Weather requires one explicit supported mode."
        raise ValueError(msg)
    if command in {"inspect", "blok", "block"}:
        coordinates = tail.split()
        if len(coordinates) != COORDINATE_COUNT or any(
            not axis.removeprefix("-").isascii() or not axis.removeprefix("-").isdecimal() for axis in coordinates
        ):
            msg = "Inspection requires exactly three integer coordinates."
            raise ValueError(msg)
        return CellAction(kind="inspect", x=int(coordinates[0]), y=int(coordinates[1]), z=int(coordinates[2]))
    if command in {"say", "povedz", "řekni"}:
        return SayAction(kind="say", text=tail)
    if command in {"follow", "nasleduj", "následuj"}:
        selected = tail or target_id
        if selected is not None:
            return FollowAction(kind="follow", target_id=selected)
    if command in {"look", "pozri", "podívej", "goto", "choď", "chod", "jdi"}:
        coordinates = tail.split()
        if len(coordinates) != 3:  # noqa: PLR2004 - the wire has exactly three axes
            msg = "Exactly three coordinates are required."
            raise ValueError(msg)
        return PointAction(
            kind="look" if command in {"look", "pozri", "podívej"} else "goto",
            x=float(coordinates[0]),
            y=float(coordinates[1]),
            z=float(coordinates[2]),
        )
    msg = "Unsupported or ambiguous instruction; stop uses the priority path."
    raise ValueError(msg)


def _parse_clock_mode(command: str, tail: str) -> TimeAction:
    modes = (
        {"day": "day", "night": "night", "toggle": "toggle"}
        if command == "time"
        else {"deň": "day", "den": "day", "noc": "night"}
    )
    mode = modes.get(tail.casefold().rstrip(".!?"))
    if mode is not None:
        return TimeAction(kind="time", mode=cast("Literal['day', 'night', 'toggle']", mode))
    msg = "Time requires one explicit supported mode."
    raise ValueError(msg)


class CompanionPolicy(CompanionDocument):
    session_id: str = Field(min_length=1, max_length=100)
    principal: str = Field(min_length=1, max_length=100)
    expires_at: datetime
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float
    max_distance: float = Field(default=16.0, gt=0, le=16)
    action_timeout_s: float = Field(default=3.0, ge=0.25, le=5)
    lease_s: float = Field(default=15.0, gt=0, le=60)
    max_actions: int = Field(default=128, ge=1, le=MAX_ACTIONS)
    allow_weather: bool = False
    allow_time: bool = False

    @model_validator(mode="after")
    def bounded(self) -> CompanionPolicy:
        if self.expires_at.tzinfo is None or any(
            low > high for low, high in ((self.min_x, self.max_x), (self.min_y, self.max_y), (self.min_z, self.max_z))
        ):
            msg = "Policy needs an aware expiry and ordered coordinate bounds."
            raise ValueError(msg)
        return self

    def contains(self, point: tuple[float, float, float]) -> bool:
        return all(
            low <= value <= high
            for value, low, high in zip(
                point, (self.min_x, self.min_y, self.min_z), (self.max_x, self.max_y, self.max_z), strict=True
            )
        )


class BridgePlayer(CompanionDocument):
    id: str
    name: str = Field(min_length=1, max_length=16)
    position: tuple[float, float, float]
    _uuid = field_validator("id")(canonical_uuid)

    @field_validator("position", mode="before")
    @classmethod
    def coordinates(cls, value: Any) -> Any:
        return _point(value)


def _point(value: Any) -> tuple[float, float, float]:
    if (
        type(value) not in (list, tuple)
        or len(value) != COORDINATE_COUNT
        or any(type(axis) not in (int, float) or not math.isfinite(axis) for axis in value)
    ):
        msg = "Position requires three finite original numbers."
        raise ValueError(msg)
    return float(value[0]), float(value[1]), float(value[2])


class BridgeState(CompanionDocument):
    protocol: Literal[1]
    boot_id: str
    generation: int = Field(ge=0)
    actor_id: str
    mode: Literal["idle", "look", "goto", "follow", "stopped", "unavailable"]
    position: tuple[float, float, float] | None
    yaw: float | None
    pitch: float | None
    queue_depth: int = Field(ge=0, le=MAX_QUEUE)
    active_action_id: str | None
    players: list[BridgePlayer] = Field(max_length=16)
    timestamp_ms: int = Field(ge=0)
    _ids = field_validator("boot_id", "actor_id")(canonical_uuid)

    @field_validator("active_action_id")
    @classmethod
    def optional_id(cls, value: str | None) -> str | None:
        return None if value is None else canonical_uuid(value)

    @field_validator("position", mode="before")
    @classmethod
    def position_value(cls, value: Any) -> Any:
        return None if value is None else _point(value)

    @field_validator("yaw", "pitch", mode="before")
    @classmethod
    def angle_value(cls, value: Any) -> Any:
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            msg = "Angles require finite original numbers."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def available_pose(self) -> BridgeState:
        if self.mode != "unavailable" and any(value is None for value in (self.position, self.yaw, self.pitch)):
            msg = "Available actor requires an observed pose."
            raise ValueError(msg)
        return self


class CellObservation(CompanionDocument):
    """One server cell read, without block-entity contents or placement authority."""

    profile: Literal["blockworld.cell@1"]
    boot_id: str
    generation: int = Field(ge=0)
    actor_id: str
    dimension: RegistryName
    position: tuple[CellCoordinate, CellCoordinate, CellCoordinate]
    available: bool
    block: RegistryName | None
    properties: dict[PropertyName, PropertyName] = Field(max_length=32)
    world_tick: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    _ids = field_validator("boot_id", "actor_id")(canonical_uuid)

    @field_validator("position", mode="before")
    @classmethod
    def integer_cell(cls, value: Any) -> Any:
        return tuple(cast("list[Any]", value)) if type(value) is list else value

    @model_validator(mode="after")
    def complete_cell(self) -> CellObservation:
        if self.available != (self.block is not None) or (not self.available and self.properties):
            msg = "Loaded cells require a block; unloaded cells cannot carry block properties."
            raise ValueError(msg)
        return self


class WeatherObservation(CompanionDocument):
    """Immediate shared server-weather readback; not a restoration or wall-clock guarantee."""

    profile: Literal["blockworld.weather@1"]
    boot_id: str
    generation: int = Field(ge=0)
    actor_id: str
    scope: Literal["server_weather"]
    anchor_dimension: Literal["minecraft:overworld"]
    mode: Literal["clear", "rain"]
    duration_ticks: Literal[600]
    clear_time: int = Field(ge=0)
    rain_time: int = Field(ge=0)
    thunder_time: int = Field(ge=0)
    raining: bool
    thundering: bool
    weather_advancing: bool
    world_tick: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    _ids = field_validator("boot_id", "actor_id")(canonical_uuid)

    @field_validator("duration_ticks", mode="before")
    @classmethod
    def original_duration(cls, value: Any) -> Any:
        if type(value) is not int:
            msg = "Weather duration requires an original integer."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def applied_programme(self) -> WeatherObservation:
        timers = (self.clear_time, self.rain_time, self.thunder_time)
        expected = (600, 0, 0) if self.mode == "clear" else (0, 600, 600)
        if timers != expected or self.raining != (self.mode == "rain") or self.thundering or not self.weather_advancing:
            msg = "Weather readback differs from the admitted timer programme."
            raise ValueError(msg)
        return self


ClockTicks = Annotated[int, Field(ge=0, le=9_223_372_036_854_775_807)]
ClockPhase = Annotated[int, Field(ge=0, lt=24_000)]


class ClockObservation(CompanionDocument):
    """Immediate forward placement and preserved settings, not a future cycling promise."""

    profile: Literal["blockworld.clock@1"]
    boot_id: str
    generation: int = Field(ge=0)
    actor_id: str
    scope: Literal["overworld_clock"]
    anchor_dimension: Literal["minecraft:overworld"]
    clock: Literal["minecraft:overworld"]
    requested_mode: Literal["day", "night", "toggle"]
    mode: Literal["day", "night"]
    before_ticks: ClockTicks
    after_ticks: ClockTicks
    delta_ticks: ClockPhase
    before_phase: ClockPhase
    after_phase: ClockPhase
    before_cycle: ClockTicks
    after_cycle: ClockTicks
    cycle_increment: Literal[0, 1]
    before_partial_tick: float
    partial_tick: float
    rate: float
    paused: bool
    time_advancing: bool
    world_tick: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    _ids = field_validator("boot_id", "actor_id")(canonical_uuid)

    @field_validator("cycle_increment", mode="before")
    @classmethod
    def original_increment(cls, value: Any) -> Any:
        if type(value) is not int:
            msg = "Clock increment requires an original integer."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def exact_placement(self) -> ClockObservation:
        phase = self.before_ticks % 24_000
        mode = (
            ("night" if phase < CLOCK_HALF_PERIOD else "day")
            if self.requested_mode == "toggle"
            else self.requested_mode
        )
        marker = 1000 if mode == "day" else 13_000
        delta = (marker - phase) % 24_000
        before_cycle, after_cycle = self.before_ticks // 24_000, self.after_ticks // 24_000
        if (
            self.mode != mode
            or self.after_ticks != self.before_ticks + delta
            or (self.delta_ticks, self.before_phase, self.after_phase) != (delta, phase, marker)
            or (self.before_cycle, self.after_cycle, self.cycle_increment)
            != (before_cycle, after_cycle, after_cycle - before_cycle)
            or self.partial_tick != (self.before_partial_tick if delta == 0 else 0.0)
        ):
            msg = "Clock readback differs from the admitted next/equal marker placement."
            raise ValueError(msg)
        return self


class ActionRecord(CompanionDocument):
    protocol: Literal[1]
    boot_id: str
    action_id: str
    run_id: str
    generation: int = Field(ge=0)
    status: Literal["accepted", "applied", "refused", "expired", "cancelled", "unknown"]
    detail: str = Field(max_length=300)
    observation: BridgeState | CellObservation | WeatherObservation | ClockObservation | None
    _ids = field_validator("boot_id", "action_id", "run_id")(canonical_uuid)


type CompanionReason = Literal[
    "time_not_authorized",
    "weather_not_authorized",
    "bounds",
    "actor_unavailable",
    "target_unavailable",
    "target_distant",
    "target_unbound",
    "interpretation_budget_exhausted",
    "interpretation_unavailable",
    "interpretation_response_refused",
    "cancelled_before_execution",
    "expired_before_execution",
]


class CompanionRefusalError(ValueError):
    """A closed host-known cause, never classified from foreign diagnostic prose."""

    def __init__(self, reason: CompanionReason) -> None:
        """Retain only a host-owned cause."""
        self.reason: CompanionReason = reason
        super().__init__(reason)


class CompanionResult(CompanionDocument):
    """A correlated disposition and optional host facts; not a wire receipt.

    controller_expires_at_ms retains the outgoing authorization upper bound,
    not an observed controller ending or proof that movement continues.
    """

    request_id: str
    kind: Literal["applied", "refused", "expired", "cancelled", "unknown", "no_action", "clarification"]
    detail: str = Field(max_length=300)
    observation: BridgeState | None = None
    reason: CompanionReason | None = None
    controller_expires_at_ms: int | None = Field(default=None, gt=0)
    cell: CellObservation | None = None
    weather: WeatherObservation | None = None
    clock: ClockObservation | None = None


class CompanionPort(Protocol):
    epoch: int
    paused: bool

    async def observe(self) -> BridgeState: ...
    async def invoke(
        self,
        request: CompanionRequest,
        run_id: str,
        *,
        expires_at_ms: int,
        authorize: Callable[[BridgeState], None] | None = None,
    ) -> CompanionResult: ...


class CompanionService:
    """Process-local intent authority and bounded result custody, without replay."""

    def __init__(self, policy: CompanionPolicy, bridge: CompanionPort) -> None:
        """Retain immutable local policy and the explicitly assembled effect port."""
        self.policy, self.bridge = policy, bridge
        self.used = 0
        self.requests: dict[str, bytes] = {}
        self.results: dict[str, CompanionResult] = {}
        self.run_results: dict[str, CompanionResult] = {}

    def validate_envelope(self, request: CompanionRequest | CompanionInstruction, principal: Sigil) -> None:
        """Recheck the original capture fence, deadline and session authority."""
        if principal.name != self.policy.principal or "blockworld:companion" not in principal.scopes:
            msg = "Principal has no companion session authority."
            raise ValueError(msg)
        if request.generation != self.bridge.epoch or self.bridge.paused:
            msg = "Captured command predates the stop fence or stop is unsettled."
            raise ValueError(msg)
        if datetime.now(UTC) >= self.policy.expires_at or self.used >= self.policy.max_actions:
            msg = "Session deadline or action budget exhausted."
            raise ValueError(msg)
        if request.expires_at_ms is not None and int(datetime.now(UTC).timestamp() * 1000) >= request.expires_at_ms:
            msg = "Original instruction deadline elapsed."
            raise ValueError(msg)

    def validate(self, request: CompanionRequest, principal: Sigil) -> None:
        self.validate_envelope(request, principal)
        self._authorize_weather(request.action, principal)
        self._authorize_time(request.action, principal)
        if isinstance(request.action, (PointAction, CellAction)):
            point = (request.action.x, request.action.y, request.action.z)
            if not self.policy.contains(point) or (
                isinstance(request.action, CellAction)
                and not self.policy.contains((point[0] + 1, point[1] + 1, point[2] + 1))
            ):
                raise CompanionRefusalError(reason="bounds")

    def _authorize(self, request: CompanionRequest, principal: Sigil, state: BridgeState) -> None:
        if request.expires_at_ms is not None and int(datetime.now(UTC).timestamp() * 1000) >= request.expires_at_ms:
            msg = "Original instruction expired before physical handoff."
            raise ValueError(msg)
        if request.generation != self.bridge.epoch or self.bridge.paused or datetime.now(UTC) >= self.policy.expires_at:
            msg = "Session was fenced before the physical handoff."
            raise ValueError(msg)
        if principal.name != self.policy.principal or "blockworld:companion" not in principal.scopes:
            msg = "Current principal refused."
            raise ValueError(msg)
        self._authorize_weather(request.action, principal)
        self._authorize_time(request.action, principal)
        if isinstance(request.action, (PointAction, FollowAction, CellAction)):
            self._authorize_spatial(request.action, state)

    def _authorize_weather(self, action: CompanionAction, principal: Sigil) -> None:
        if isinstance(action, WeatherAction) and (
            not self.policy.allow_weather or "blockworld:weather" not in principal.scopes
        ):
            raise CompanionRefusalError(reason="weather_not_authorized")

    def _authorize_time(self, action: CompanionAction, principal: Sigil) -> None:
        if isinstance(action, TimeAction) and (not self.policy.allow_time or "blockworld:time" not in principal.scopes):
            raise CompanionRefusalError(reason="time_not_authorized")

    def _authorize_spatial(self, action: PointAction | FollowAction | CellAction, state: BridgeState) -> None:
        if state.mode == "unavailable" or state.position is None:
            raise CompanionRefusalError(reason="actor_unavailable")
        if not self.policy.contains(state.position):
            raise CompanionRefusalError(reason="bounds")
        if isinstance(action, (PointAction, CellAction)):
            point = (action.x, action.y, action.z)
            if (
                not self.policy.contains(point)
                or math.dist(state.position, point) > self.policy.max_distance
                or (
                    isinstance(action, CellAction)
                    and not self.policy.contains((point[0] + 1, point[1] + 1, point[2] + 1))
                )
            ):
                raise CompanionRefusalError(reason="bounds")
            return
        targets = [player for player in state.players if player.id == action.target_id]
        if len(targets) != 1:
            raise CompanionRefusalError(reason="target_unavailable")
        if not self.policy.contains(targets[0].position):
            raise CompanionRefusalError(reason="bounds")
        if math.dist(state.position, targets[0].position) > self.policy.max_distance:
            raise CompanionRefusalError(reason="target_distant")

    async def execute(self, request: CompanionRequest, run_id: str, principal: Sigil) -> CompanionResult:
        document = request.model_dump_json().encode()
        if request.request_id in self.requests:
            if self.requests[request.request_id] != document:
                msg = "Request identity was reused with changed content."
                raise ValueError(msg)
            return self.results[request.request_id]
        self.validate(request, principal)
        self.used += 1
        self.requests[request.request_id] = document
        self.results[request.request_id] = CompanionResult(
            request_id=request.request_id, kind="unknown", detail="Attempt retained; no replay."
        )
        expires_at_ms = int(
            min(self.policy.expires_at.timestamp(), datetime.now(UTC).timestamp() + self.policy.lease_s) * 1000
        )
        if request.expires_at_ms is not None:
            expires_at_ms = min(expires_at_ms, request.expires_at_ms)
        try:
            async with asyncio.timeout(self.policy.action_timeout_s):
                result = await self.bridge.invoke(
                    request,
                    run_id,
                    expires_at_ms=expires_at_ms,
                    authorize=lambda state: self._authorize(request, principal, state),
                )
        except TimeoutError:
            result = CompanionResult(
                request_id=request.request_id,
                kind="unknown",
                detail="Finite native action deadline elapsed; no replay.",
            )
        controller_applied = (
            result.request_id == request.request_id
            and result.kind == "applied"
            and result.reason is None
            and request.action.kind in {"idle", "look", "goto", "follow"}
        )
        result = CompanionResult.model_validate(
            {
                **result.model_dump(mode="python"),
                "controller_expires_at_ms": expires_at_ms if controller_applied else None,
            }
        )
        self.results[request.request_id] = result
        return result


class CompanionState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    run_id: str
    session_id: str
    prompt: str
    profile_digest: str | None = None
    instruction: CompanionInstruction | None = None
    intent_decision: Literal["state", "idle", "follow_bound", "no_action", "clarification"] | None = None
    request: CompanionRequest | None = None
    result: CompanionResult | None = None


class CompanionInterpreter(Protocol):
    """A live local capability owner; never checkpointed in Graph state."""

    profile_digest: str

    async def interpret(self, instruction: CompanionInstruction, common: WorkflowServices, run_id: str) -> str: ...


def _resolved_instruction(instruction: CompanionInstruction, decision: str | None) -> CompanionRequest | None:
    """Pin every actionable proposal to the exact original envelope, never model arguments."""
    if decision in {"state", "idle"}:
        action: CompanionAction = SimpleAction(kind="state" if decision == "state" else "idle")
    elif decision == "follow_bound" and instruction.target_id is not None:
        action = FollowAction(kind="follow", target_id=instruction.target_id)
    else:
        return None
    return CompanionRequest(
        request_id=instruction.request_id,
        action=action,
        transcript=instruction.original_text,
        source=instruction.source,
        generation=instruction.generation,
        expires_at_ms=instruction.expires_at_ms,
        source_artifacts=instruction.source_artifacts,
    )


@dataclass(frozen=True)
class CompanionDeps:
    common: WorkflowServices
    companion: CompanionService
    interpreter: CompanionInterpreter | None = None


@dataclass
class ValidateCompanion(BaseNode[CompanionState, CompanionDeps]):
    async def run(
        self, ctx: GraphRunContext[CompanionState, CompanionDeps]
    ) -> InterpretCompanion | ExecuteCompanion | ReportCompanion:
        try:
            document = strict_json(ctx.state.prompt)
            if type(document) is dict and cast("dict[str, Any]", document).get("kind") == "raw_instruction":
                instruction = CompanionInstruction.model_validate(document)
                ctx.state.instruction = instruction
                interpreter = ctx.deps.interpreter
                if interpreter is None or instruction.profile_digest != ctx.state.profile_digest:
                    raise CompanionRefusalError(reason="interpretation_unavailable")
                ctx.deps.companion.validate_envelope(instruction, ctx.deps.common.sigil_provider())
                return InterpretCompanion()
            ctx.state.request = CompanionRequest.model_validate(document)
            ctx.deps.companion.validate(ctx.state.request, ctx.deps.common.sigil_provider())
        except ValueError as exc:
            ctx.state.result = CompanionResult(
                request_id=(
                    ctx.state.instruction.request_id
                    if ctx.state.instruction
                    else ctx.state.request.request_id
                    if ctx.state.request
                    else ctx.state.run_id
                ),
                kind="refused",
                detail="Instruction or session authority refused.",
                reason=exc.reason if isinstance(exc, CompanionRefusalError) else None,
            )
            return ReportCompanion()
        return ExecuteCompanion()


@dataclass
class InterpretCompanion(BaseNode[CompanionState, CompanionDeps]):
    async def run(self, ctx: GraphRunContext[CompanionState, CompanionDeps]) -> ExecuteCompanion | ReportCompanion:
        instruction, interpreter = ctx.state.instruction, ctx.deps.interpreter
        if instruction is None or interpreter is None:
            msg = "No bound interpretation input."
            raise ValueError(msg)
        try:
            ctx.deps.companion.validate_envelope(instruction, ctx.deps.common.sigil_provider())
            decision = await interpreter.interpret(instruction, ctx.deps.common, ctx.state.run_id)
            ctx.deps.companion.validate_envelope(instruction, ctx.deps.common.sigil_provider())
            if decision not in {"state", "idle", "follow_bound", "no_action", "clarification"}:
                raise CompanionRefusalError(reason="interpretation_response_refused")  # noqa: TRY301 - closed terminal decision
            ctx.state.intent_decision = cast(
                "Literal['state', 'idle', 'follow_bound', 'no_action', 'clarification']", decision
            )
            ctx.deps.common.events.emitter(ctx.state.run_id).log(json.dumps({"intent_decision": decision}))
            if decision in {"no_action", "clarification"}:
                ctx.state.result = CompanionResult(
                    request_id=instruction.request_id,
                    kind="no_action" if decision == "no_action" else "clarification",
                    detail="Interpretation ended without a game action.",
                )
                return ReportCompanion()
            if decision == "follow_bound" and instruction.target_id is None:
                ctx.state.result = CompanionResult(
                    request_id=instruction.request_id,
                    kind="clarification",
                    detail="No player was bound at capture.",
                    reason="target_unbound",
                )
                return ReportCompanion()
            ctx.state.request = _resolved_instruction(instruction, decision)
            if ctx.state.request is None:
                msg = "No actionable decision."
                raise ValueError(msg)  # noqa: TRY301 - closed decision guard
            ctx.deps.companion.validate(ctx.state.request, ctx.deps.common.sigil_provider())
        except Exception as exc:  # noqa: BLE001 - foreign diagnostics cannot become game effects or feedback
            expired = int(datetime.now(UTC).timestamp() * 1000) >= instruction.expires_at_ms
            ctx.state.result = CompanionResult(
                request_id=instruction.request_id,
                kind="expired" if expired else "refused",
                detail="Original instruction expired." if expired else "Local interpretation unavailable or refused.",
                reason=None if expired else exc.reason if isinstance(exc, CompanionRefusalError) else None,
            )
            return ReportCompanion()
        return ExecuteCompanion()


@dataclass
class ExecuteCompanion(BaseNode[CompanionState, CompanionDeps]):
    async def run(self, ctx: GraphRunContext[CompanionState, CompanionDeps]) -> ReportCompanion:
        request = ctx.state.request
        if request is None:
            msg = "No validated companion request."
            raise ValueError(msg)
        try:
            ctx.state.result = await ctx.deps.companion.execute(
                request, ctx.state.run_id, ctx.deps.common.sigil_provider()
            )
        except ValueError as exc:
            ctx.state.result = CompanionResult(
                request_id=request.request_id,
                kind="refused",
                detail="Current bounds or authority refused.",
                reason=exc.reason if isinstance(exc, CompanionRefusalError) else None,
            )
        return ReportCompanion()


@dataclass
class ReportCompanion(BaseNode[CompanionState, CompanionDeps, CompanionResult]):
    async def run(self, ctx: GraphRunContext[CompanionState, CompanionDeps]) -> End[CompanionResult]:
        result = ctx.state.result
        if result is None:
            msg = "No companion disposition retained."
            raise ValueError(msg)
        ctx.deps.companion.run_results[ctx.state.run_id] = result
        ctx.deps.common.events.emitter(ctx.state.run_id).log(result.model_dump_json())
        return End(result)


def companion_workflow(service: CompanionService, interpreter: CompanionInterpreter | None = None) -> Workflow:
    profile_digest = None if interpreter is None else interpreter.profile_digest
    graph = build_serial_graph(
        nodes=(ValidateCompanion, InterpretCompanion, ExecuteCompanion, ReportCompanion),
        state_type=CompanionState,
        deps_type=CompanionDeps,
        output_type=CompanionResult,
    )

    def make_state(intent: Intent) -> CompanionState:
        if (
            intent.run_id is None
            or intent.session_id != service.policy.session_id
            or intent.source != "blockworld.companion"
        ):
            msg = "Run identity or source differs from companion admission."
            raise ValueError(msg)
        return CompanionState(
            run_id=intent.run_id, session_id=intent.session_id, prompt=intent.prompt, profile_digest=profile_digest
        )

    def validate_state(intent: Intent, state: BaseModel) -> None:
        if isinstance(state, CompanionState):
            CompanionState.model_validate(state.model_dump(mode="python", warnings=False))
        if not isinstance(state, CompanionState) or (
            state.run_id,
            state.session_id,
            state.prompt,
            state.profile_digest,
        ) != (
            intent.run_id,
            intent.session_id,
            intent.prompt,
            profile_digest,
        ):
            msg = "Graph state differs from the admitted Run."
            raise ValueError(msg)
        _validate_instruction_state(state)

    return Workflow(
        name="blockworld.companion",
        title="Experimental local companion",
        description="One finite server action, with identity-correlated observation.",
        trigger=Trigger(
            hint="Explicit companion command", match=lambda intent: intent.source == "blockworld.companion"
        ),
        graph=graph,
        start_node=ValidateCompanion,
        make_state=make_state,
        validate_state=validate_state,
        bind_deps=lambda common: CompanionDeps(common, service, interpreter),
        manifest=PatternManifest(
            key="blockworld.companion",
            revision="4",
            implementation_revision="py.6",
            checkpoint_schema="companion-state-v6",
            entry_node="validate",
            nodes=(
                PatternNode(key="validate", label="Validate command", kind="step", implementation=ValidateCompanion),
                PatternNode(
                    key="interpret",
                    label="Interpret bounded instruction",
                    kind="step",
                    implementation=InterpretCompanion,
                ),
                PatternNode(key="execute", label="Attempt server action", kind="step", implementation=ExecuteCompanion),
                PatternNode(key="report", label="Report receipt", kind="step", implementation=ReportCompanion),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=tuple(
                PatternEdge(key=key, source=source, target=target)
                for key, source, target in (
                    ("validate-execute", "validate", "execute"),
                    ("validate-interpret", "validate", "interpret"),
                    ("validate-report", "validate", "report"),
                    ("interpret-execute", "interpret", "execute"),
                    ("interpret-report", "interpret", "report"),
                    ("execute-report", "execute", "report"),
                    ("report-end", "report", "end"),
                )
            ),
        ),
    )


def _validate_instruction_state(state: CompanionState) -> None:
    """Refuse substituted targets, deadlines, inputs or action kinds on restore."""
    try:
        document = strict_json(state.prompt)
        raw = type(document) is dict and cast("dict[str, Any]", document).get("kind") == "raw_instruction"
        admitted = CompanionInstruction.model_validate(document) if raw else CompanionRequest.model_validate(document)
    except ValueError:
        if state.request is not None or state.instruction is not None or state.intent_decision is not None:
            msg = "Invalid admission cannot carry derived continuation data."
            raise ValueError(msg) from None
        return
    if isinstance(admitted, CompanionInstruction):
        _validate_raw_state(admitted, state)
    elif (
        state.instruction is not None
        or state.intent_decision is not None
        or (state.request is not None and state.request.model_dump_json(warnings=False) != admitted.model_dump_json())
    ):
        msg = "Checkpoint typed request differs from original admission."
        raise ValueError(msg)
    if state.result is not None and state.result.request_id != admitted.request_id:
        msg = "Checkpoint result differs from original identity."
        raise ValueError(msg)


def _validate_raw_state(admitted: CompanionInstruction, state: CompanionState) -> None:
    if (
        state.instruction is not None
        and state.instruction.model_dump_json(warnings=False) != admitted.model_dump_json()
    ):
        msg = "Checkpoint instruction differs from original admission."
        raise ValueError(msg)
    if state.intent_decision is not None and state.instruction is None:
        msg = "Checkpoint decision lacks original input."
        raise ValueError(msg)
    if state.request is not None:
        resolved = _resolved_instruction(admitted, state.intent_decision)
        if resolved is None or state.request.model_dump_json(warnings=False) != resolved.model_dump_json():
            msg = "Checkpoint proposal differs from original bounds."
            raise ValueError(msg)
        if admitted.profile_digest != state.profile_digest:
            msg = "Checkpoint proposal has no trusted profile binding."
            raise ValueError(msg)
