"""Finite client-observed plank placement; no server receipt or atomic world guard.

One admitted cell is one native Run and at most one placement attempt. Queries
and Horizon's later click are separate operations: concurrent changes can remain
unobserved. Unknown effects stop a plan and are never automatically replayed.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, cast
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.blockworld.horizon_assist import (
    AssistDocument,
    AssistRequest,
    HorizonAssistService,
    ReadAction,
)
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.graph import build_serial_graph

Cell = tuple[int, int, int]
I32_MIN, I32_MAX = -(2**31), 2**31 - 1
MATERIAL = "minecraft:oak_planks"
MAX_CELLS = 3
HOTBAR_SIZE = 9
MAX_STACK = 64
MAX_BUILD_BYTES = 8192
READS_PER_CELL = 8
REACH = 4.0
FRESHNESS_S = 1.0


def _uuid(value: str) -> str:
    if str(UUID(value)) != value:
        msg = "Identity must be a canonical UUID."
        raise ValueError(msg)
    return value


def _cell(value: Cell) -> Cell:
    if any(type(item) is not int or not I32_MIN <= item <= I32_MAX for item in value):
        msg = "Cells require exact signed 32-bit integers."
        raise ValueError(msg)
    return value


class BuildPlan(AssistDocument):
    """An immutable declaration; only the shared session can authorize its effect."""

    plan_id: str
    session_id: str = Field(min_length=1, max_length=100)
    world: str = Field(max_length=200)
    dimension: str = Field(min_length=1, max_length=200)
    mode: Literal["survival", "creative"]
    cells: tuple[Cell, ...]
    plot_min: Cell
    plot_max: Cell
    expires_at: datetime
    max_placements: int = Field(ge=1, le=MAX_CELLS)
    max_reads: int = Field(ge=READS_PER_CELL, le=24)
    duration_s: float = Field(default=60.0, gt=0, le=60)
    material: Literal["minecraft:oak_planks"] = MATERIAL
    expected_target: Literal["minecraft:air"] = "minecraft:air"
    expected_support: Literal["minecraft:stone"] = "minecraft:stone"

    _plan_uuid = field_validator("plan_id")(_uuid)
    _bounds = field_validator("plot_min", "plot_max")(_cell)

    @model_validator(mode="after")
    def finite_plot(self) -> BuildPlan:
        if (
            len(self.cells) not in (1, MAX_CELLS)
            or len(set(self.cells)) != len(self.cells)
            or self.max_placements != len(self.cells)
            or self.max_reads < READS_PER_CELL * len(self.cells)
            or self.expires_at.tzinfo is None
            or any(low > high for low, high in zip(self.plot_min, self.plot_max, strict=True))
        ):
            msg = "Plan requires one or three unique cells and sufficient finite budgets."
            raise ValueError(msg)
        for cell in self.cells:
            _cell(cell)
            support = _cell((cell[0], cell[1] - 1, cell[2]))
            if not self.contains(cell) or not self.contains(support):
                msg = "Target and support must be within the admitted plot."
                raise ValueError(msg)
        return self

    def contains(self, point: tuple[float, float, float] | Cell) -> bool:
        return all(low <= value <= high for value, low, high in zip(point, self.plot_min, self.plot_max, strict=True))

    @property
    def canonical_bytes(self) -> bytes:
        """Local v1 content encoding, without claiming portable Scroll identity."""
        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


class BuildStep(AssistDocument):
    request_id: str
    plan_id: str
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation: int = Field(ge=1)
    cursor: int = Field(ge=0, lt=MAX_CELLS)
    cell: Cell
    created_at: float
    deadline: float

    _request_uuid = field_validator("request_id")(_uuid)
    _plan_uuid = field_validator("plan_id")(_uuid)
    _coordinates = field_validator("cell")(_cell)


class BuildResult(AssistDocument):
    request_id: str
    plan_id: str
    plan_digest: str
    generation: int
    cursor: int
    cell: Cell | None
    kind: Literal["placed", "refused", "client_error", "outcome_unknown"]
    detail: str
    stop_required: bool
    read_count: int
    action_count: int
    started_at: float
    finished_at: float
    observation: dict[str, Any] | None = None


def _decode(document: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                msg = "Duplicate build document key."
                raise ValueError(msg)
            result[key] = value
        return result

    def invalid(_: str) -> Any:
        msg = "Non-finite build document number."
        raise ValueError(msg)

    if len(document.encode()) > MAX_BUILD_BYTES:
        msg = "Build document exceeds its byte budget."
        raise ValueError(msg)
    return _object(json.loads(document, object_pairs_hook=unique, parse_constant=invalid))


def decode_plan(document: str) -> BuildPlan:
    """Refuse duplicate keys before strict JSON plan validation."""
    _decode(document)
    return BuildPlan.model_validate_json(document)


def decode_step(document: str) -> BuildStep:
    """Refuse duplicate keys before strict checkpoint input validation."""
    _decode(document)
    return BuildStep.model_validate_json(document)


class BuildControl(Protocol):
    async def observe(self) -> dict[str, Any]: ...
    async def inspect_inventory(self) -> dict[str, Any]: ...
    async def inspect_cell(self, x: int, y: int, z: int) -> dict[str, Any]: ...
    async def invoke(
        self, run_id: str, line: str, *, query: bool = False, authorize: Callable[[dict[str, Any]], None] | None = None
    ) -> Any: ...


class BuildState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    run_id: str
    session_id: str
    prompt: str
    step: BuildStep | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    sample_time: float | None = None
    read_count: int = 0
    action_count: int = 0
    result: BuildResult | None = None


def _object(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        msg = "Expected an observed object."
        raise ValueError(msg)
    return cast("dict[str, Any]", value)


def _vector(value: Any) -> tuple[float, float, float]:
    if type(value) is not list or len(cast("list[Any]", value)) != MAX_CELLS:
        msg = "Expected an observed three-coordinate vector."
        raise ValueError(msg)
    items = cast("list[Any]", value)
    if any(type(item) not in (int, float) or not math.isfinite(item) for item in items):
        msg = "Observed vector must be finite."
        raise ValueError(msg)
    return float(items[0]), float(items[1]), float(items[2])


def _exact_block(raw: Any, cell: Cell, block: str) -> None:
    value = _object(raw)
    if (
        value.get("loaded") is not True
        or value.get("pos") != list(cell)
        or any(type(item) is not int for item in cast("list[Any]", value.get("pos", [])))
        or value.get("block") != block
        or value.get("state") != block
    ):
        msg = "Cell is unloaded, changed or not the exact expected plain block."
        raise ValueError(msg)


def _inventory(raw: Any, needed: int) -> dict[str, Any]:  # noqa: C901 - validate one complete source-derived inventory observation
    value = _object(raw)
    if set(value) != {"selected", "held", "hotbar", "main", "armor", "offhand", "carried", "counts"}:
        msg = "Incomplete inventory observation."
        raise ValueError(msg)
    selected = value["selected"]
    held = _object(value["held"])
    if (
        type(selected) is not int
        or not 1 <= selected <= HOTBAR_SIZE
        or set(held) != {"item", "count"}
        or held.get("item") != MATERIAL
        or type(held.get("count")) is not int
        or not needed <= held["count"] <= MAX_STACK
        or value["offhand"] != {"slot": 504, "item": None}
        or value["carried"] is not None
    ):
        msg = "Already selected ordinary planks and empty offhand/carried stacks are required."
        raise ValueError(msg)
    totals: dict[str, int] = {}
    for key, slots in (("hotbar", tuple(range(9))), ("main", tuple(range(9, 36))), ("armor", tuple(range(500, 504)))):
        array = value[key]
        if type(array) is not list or len(cast("list[Any]", array)) != len(slots):
            msg = "Inventory slots are incomplete."
            raise ValueError(msg)
        for raw_slot, number in zip(cast("list[Any]", array), slots, strict=True):
            slot = _object(raw_slot)
            if type(slot.get("slot")) is not int or slot["slot"] != number:
                msg = "Inventory slot identity changed."
                raise ValueError(msg)
            item = slot.get("item")
            if item is not None:
                count = slot.get("count")
                if type(item) is not str or type(count) is not int or not 1 <= count <= MAX_STACK:
                    msg = "Malformed observed inventory stack."
                    raise ValueError(msg)
                totals[item] = totals.get(item, 0) + count
    hotbar = cast("list[dict[str, Any]]", value["hotbar"])
    if hotbar[selected - 1] != {"slot": selected - 1, **held} or value["counts"] != totals:
        msg = "Held stack, selected slot or inventory totals disagree."
        raise ValueError(msg)
    observed_counts = _object(value["counts"])
    if any(type(key) is not str or type(count) is not int or count <= 0 for key, count in observed_counts.items()):
        msg = "Inventory totals require exact positive integers."
        raise ValueError(msg)
    return value


class HorizonBuildService:
    """Process-local plan custody sharing the existing assist authority and budget."""

    def __init__(
        self,
        assist: HorizonAssistService,
        control: BuildControl | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Bind existing collaborators without opening a client or starting work."""
        self.assist = assist
        self._assist = assist
        self.control = control if control is not None else cast("BuildControl", assist.control)
        if self.control is not assist.control:
            msg = "Build and assist must use the same control session."
            raise ValueError(msg)
        self._control = self.control
        self.clock = clock
        self.plan: BuildPlan | None = None
        self.cursor = 0
        self.generation = 0
        self.deadline = 0.0
        self.read_count = 0
        self.action_count = 0
        self.fence_reason: str | None = None
        self.results: dict[str, BuildResult] = {}
        self.run_results: dict[str, BuildResult] = {}
        self.records: list[dict[str, Any]] = []
        self._plans: dict[str, bytes] = {}
        self._steps: dict[str, BuildStep] = {}
        self._runs: dict[str, str] = {}
        self._attempted: set[str] = set()
        self._reported: set[str] = set()
        self._plan_bytes = b""
        self._assist_policy = assist.policy

    def fence(self, reason: str) -> int:
        """Retire the active generation synchronously; no world undo is implied."""
        self.generation += 1
        self.plan = None
        self.deadline = 0.0
        self.fence_reason = reason
        return self.generation

    def begin(self, plan: BuildPlan) -> int:
        """Admit detached plan bytes once; shape does not grant session authority."""
        plan = BuildPlan.model_validate_json(plan.model_dump_json())
        policy = self.assist.policy
        now = self.clock()
        if (
            plan.plan_id in self._plans
            or plan.session_id != policy.session_id
            or plan.expires_at > policy.expires_at
            or datetime.now(UTC) >= plan.expires_at
            or not math.isfinite(now)
            or not policy.contains(plan.plot_min)
            or not policy.contains(plan.plot_max)
            or not {"state", "place"}.issubset(policy.permitted)
            or plan.max_placements > policy.max_actions - self.assist.used
        ):
            msg = "Plan identity, bounds, expiry or shared session budget refused."
            raise ValueError(msg)
        self.fence("replaced")
        self.plan = plan
        self._plan_bytes = plan.canonical_bytes
        self._plans[plan.plan_id] = self._plan_bytes
        self._assist_policy = policy
        self.deadline = now + min(plan.duration_s, (plan.expires_at - datetime.now(UTC)).total_seconds())
        self.cursor = self.read_count = self.action_count = 0
        self.fence_reason = None
        return self.generation

    def new_step(self) -> BuildStep:
        """Pin only the next cell; a pending step cannot be replaced or queued twice."""
        plan = self.plan
        if plan is None or self.cursor >= len(plan.cells) or self.clock() >= self.deadline:
            msg = "No active finite build cell."
            raise ValueError(msg)
        request_id = str(uuid5(UUID(plan.plan_id), f"{self.generation}:{self.cursor}"))
        if request_id in self._steps:
            msg = "This cell already has a retained step identity."
            raise ValueError(msg)
        step = BuildStep(
            request_id=request_id,
            plan_id=plan.plan_id,
            plan_digest=plan.digest,
            generation=self.generation,
            cursor=self.cursor,
            cell=plan.cells[self.cursor],
            created_at=self.clock(),
            deadline=self.deadline,
        )
        self._steps[request_id] = step
        return step

    def check(self, step: BuildStep, sample_time: float | None = None) -> BuildPlan:
        plan, now = self.plan, self.clock()
        if (
            plan is None
            or self.assist is not self._assist
            or self.control is not self._control
            or self.assist.control is not self._control
            or plan.canonical_bytes != self._plan_bytes
            or self.assist.policy != self._assist_policy
            or self._plans.get(step.plan_id) != self._plan_bytes
            or self._steps.get(step.request_id) != step
            or (step.plan_id, step.plan_digest, step.generation, step.cursor)
            != (plan.plan_id, plan.digest, self.generation, self.cursor)
            or step.cell != plan.cells[self.cursor]
            or step.deadline != self.deadline
            or not math.isfinite(now)
            or now < step.created_at
            or now >= self.deadline
            or datetime.now(UTC) >= plan.expires_at
            or (sample_time is not None and (now < sample_time or now - sample_time >= FRESHNESS_S))
        ):
            msg = "Plan bytes, step, generation, deadline or read freshness changed."
            raise ValueError(msg)
        return plan

    def validate(self, step: BuildStep, principal: Sigil, run_id: str | None = None) -> None:
        self.check(step)
        self.assist.validate(AssistRequest(request_id=step.request_id, action=ReadAction(kind="state")), principal)
        if (
            "place" not in cast("tuple[str, ...]", self.assist.policy.permitted)
            or self.assist.used > self.assist.policy.max_actions
        ):
            msg = "Shared session does not permit placement."
            raise ValueError(msg)
        if run_id is not None:
            if self._runs.get(step.request_id, run_id) != run_id:
                msg = "Step belongs to another native Run."
                raise ValueError(msg)
            self._runs[step.request_id] = run_id

    def disposition(
        self, state: BuildState, kind: Literal["placed", "refused", "client_error", "outcome_unknown"], detail: str
    ) -> BuildResult:
        step = state.step
        return BuildResult(
            request_id=step.request_id if step else state.run_id,
            plan_id=step.plan_id if step else "",
            plan_digest=step.plan_digest if step else "",
            generation=step.generation if step else self.generation,
            cursor=step.cursor if step else 0,
            cell=step.cell if step else None,
            kind=kind,
            detail=detail,
            stop_required=kind != "placed",
            read_count=state.read_count,
            action_count=state.action_count,
            started_at=step.created_at if step else self.clock(),
            finished_at=self.clock(),
            observation=state.after,
        )

    def pose(self, step: BuildStep, raw: Any) -> dict[str, Any]:
        plan = self.check(step)
        value = _object(raw)
        player = _object(value.get("player"))
        health = player.get("health")
        support_top = (step.cell[0] + 0.5, float(step.cell[1]), step.cell[2] + 0.5)
        if (
            value.get("world") != plan.world
            or value.get("dimension") != plan.dimension
            or value.get("gamemode") != plan.mode
            or value.get("screen") != "playing"
            or value.get("paused") is not False
            or value.get("busy") is not None
            or type(value.get("selected")) is not int
            or value.get("sleeping") is not None
            or value.get("using") is not None
            or type(health) not in (int, float)
            or not math.isfinite(cast("float", health))
            or cast("float", health) <= 0
            or not self.assist.policy.contains(_vector(player.get("position")))
            or math.dist(_vector(player.get("position")), tuple(value + 0.5 for value in step.cell))
            > self.assist.policy.max_distance
            or math.dist(_vector(player.get("eye")), support_top) > REACH
        ):
            msg = "Healthy idle Playing state, exact mode/labels or conservative reach refused."
            raise ValueError(msg)
        return value

    async def read(self, state: BuildState) -> dict[str, Any]:
        """Count four composition calls, not control-session wire queries."""
        step = state.step
        if step is None:
            msg = "No admitted build step."
            raise ValueError(msg)
        plan = self.check(step)
        sample_time = self.clock()
        result: dict[str, Any] = {}
        for name, call in (
            ("state", self.control.observe),
            ("inventory", self.control.inspect_inventory),
            ("target", lambda: self.control.inspect_cell(*step.cell)),
            ("support", lambda: self.control.inspect_cell(step.cell[0], step.cell[1] - 1, step.cell[2])),
        ):
            if self.read_count >= plan.max_reads:
                msg = "Finite composition read budget exhausted."
                raise ValueError(msg)
            self.check(step, sample_time)
            self.read_count += 1
            state.read_count += 1
            try:
                result[name] = await call()
            except asyncio.CancelledError:
                state.result = self.disposition(
                    state,
                    "outcome_unknown" if state.action_count else "refused",
                    "Read cancelled; prior effects may remain.",
                )
                self.results[step.request_id] = self.run_results[state.run_id] = state.result
                if step.generation == self.generation:
                    self.fence("cancelled")
                raise
            self.check(step, sample_time)
        state.sample_time = sample_time
        # Detach mutable port data before retaining a checkpoint or comparing later.
        return cast("dict[str, Any]", json.loads(json.dumps(result, allow_nan=False)))

    def decide(self, state: BuildState) -> None:
        step, before = state.step, state.before
        if step is None or before is None:
            msg = "No preflight observation."
            raise ValueError(msg)
        plan = self.check(step, state.sample_time)
        pose = self.pose(step, before["state"])
        inventory = _inventory(before["inventory"], len(plan.cells) - self.cursor if plan.mode == "survival" else 1)
        if pose.get("selected") != inventory["selected"] or pose.get("held") != inventory["held"]:
            msg = "State and inventory disagree about selected planks."
            raise ValueError(msg)
        _exact_block(before["target"], step.cell, plan.expected_target)
        _exact_block(before["support"], (step.cell[0], step.cell[1] - 1, step.cell[2]), plan.expected_support)

    async def place(self, state: BuildState, principal: Sigil) -> None:
        step, before = state.step, state.before
        if step is None or before is None:
            msg = "No decided build cell."
            raise ValueError(msg)
        self.validate(step, principal, state.run_id)
        self.decide(state)
        if step.request_id in self._attempted:
            msg = "Retained placement identity cannot be attempted again."
            raise ValueError(msg)
        self._attempted.add(step.request_id)
        state.result = self.disposition(
            state, "outcome_unknown", "Placement attempt retained; no replay or undo claim."
        )
        self.results[step.request_id] = self.run_results[state.run_id] = state.result

        def authorize(latest: dict[str, Any]) -> None:
            self.validate(step, principal, state.run_id)
            self.check(step, state.sample_time)
            pose = self.pose(step, latest)
            inventory = _object(before["inventory"])
            if pose.get("selected") != inventory["selected"] or pose.get("held") != inventory["held"]:
                msg = "Latest selected stack changed before placement handoff."
                raise ValueError(msg)
            if state.action_count:
                msg = "Placement authorization callback cannot reserve twice."
                raise ValueError(msg)
            self.assist.used += 1
            self.action_count += 1
            state.action_count = 1
            state.result = self.disposition(
                state, "outcome_unknown", "Placement reserved immediately before handoff; no replay."
            )
            self.results[step.request_id] = self.run_results[state.run_id] = state.result

        try:
            outcome = await self.control.invoke(
                state.run_id, f"place {step.cell[0]} {step.cell[1]} {step.cell[2]}", query=False, authorize=authorize
            )
        except BaseException:
            self.results[step.request_id] = self.run_results[state.run_id] = state.result
            if step.generation == self.generation:
                self.fence("outcome_unknown")
            raise
        if outcome.kind != "client_observed":
            state.result = self.disposition(state, outcome.kind, outcome.detail)
        else:
            # A stock ok only says some target state changed. Postflight decides.
            state.result = None

    def confirm(self, state: BuildState) -> None:
        step, before, after = state.step, state.before, state.after
        if step is None or before is None or after is None:
            msg = "No postflight observation."
            raise ValueError(msg)
        plan = self.check(step, state.sample_time)
        pose = self.pose(step, after["state"])
        _exact_block(after["target"], step.cell, MATERIAL)
        _exact_block(after["support"], (step.cell[0], step.cell[1] - 1, step.cell[2]), plan.expected_support)
        expected = cast("dict[str, Any]", json.loads(json.dumps(before["inventory"])))
        delta = 1 if plan.mode == "survival" else 0
        held = _object(expected["held"])
        held["count"] -= delta
        selected = cast("int", expected["selected"])
        hotbar = cast("list[dict[str, Any]]", expected["hotbar"])
        counts = _object(expected["counts"])
        if held["count"] == 0:
            expected["held"] = None
            hotbar[selected - 1] = {"slot": selected - 1, "item": None}
        else:
            hotbar[selected - 1]["count"] -= delta
        counts[MATERIAL] -= delta
        if counts[MATERIAL] == 0:
            del counts[MATERIAL]
        observed_inventory = _object(after["inventory"])
        # JSON bytes distinguish booleans/fractions from exact integer counts.
        if (
            json.dumps(observed_inventory, sort_keys=True, separators=(",", ":"), allow_nan=False)
            != json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False)
            or pose.get("selected") != selected
            or json.dumps(pose.get("held"), sort_keys=True, allow_nan=False)
            != json.dumps(expected["held"], sort_keys=True, allow_nan=False)
        ):
            msg = "Unexpected held, inventory, selection or consumption change."
            raise ValueError(msg)
        state.result = self.disposition(
            state, "placed", "Exact cell and expected inventory delta observed by this client only."
        )

    def report(self, state: BuildState) -> BuildResult:
        if state.run_id in self._reported:
            return self.run_results[state.run_id]
        result, step = state.result, state.step
        if result is None:
            msg = "No build disposition retained."
            raise ValueError(msg)
        owns_step = (
            step is not None
            and self._runs.get(step.request_id) == state.run_id
            and self._steps.get(step.request_id) == step
        )
        owns_cursor = (
            owns_step and step is not None and step.generation == self.generation and step.cursor == self.cursor
        )
        if result.kind == "placed":
            if not owns_cursor or step is None:
                result = self.disposition(
                    state, "outcome_unknown", "Report does not own the exact current step and Run."
                )
            else:
                try:
                    self.check(step, state.sample_time)
                except ValueError:
                    result = self.disposition(
                        state, "outcome_unknown", "Build authority changed before report; prior effects may remain."
                    )
                else:
                    self.cursor += 1
        if owns_step:
            self.results[result.request_id] = result
        self.run_results[state.run_id] = result
        self._reported.add(state.run_id)
        self.records.append(result.model_dump(mode="json"))
        if result.stop_required and owns_cursor:
            self.fence(result.kind)
        return result


@dataclass(frozen=True)
class BuildDeps:
    common: WorkflowServices
    builds: HorizonBuildService


@dataclass
class ValidateBuild(BaseNode[BuildState, BuildDeps]):
    async def run(self, ctx: GraphRunContext[BuildState, BuildDeps]) -> ReadBuildPreflight | ReportBuild:
        try:
            ctx.state.step = decode_step(ctx.state.prompt)
            ctx.deps.builds.validate(ctx.state.step, ctx.deps.common.sigil_provider(), ctx.state.run_id)
        except ValueError:
            ctx.state.result = ctx.deps.builds.disposition(
                ctx.state, "refused", "Build plan or shared session authority refused."
            )
            return ReportBuild()
        return ReadBuildPreflight()


@dataclass
class ReadBuildPreflight(BaseNode[BuildState, BuildDeps]):
    async def run(self, ctx: GraphRunContext[BuildState, BuildDeps]) -> DecideBuild | ReportBuild:
        try:
            ctx.state.before = await ctx.deps.builds.read(ctx.state)
        except (OSError, RuntimeError, ValueError):
            ctx.state.result = ctx.deps.builds.disposition(
                ctx.state, "refused", "Preflight unavailable, stale or changed."
            )
            return ReportBuild()
        return DecideBuild()


@dataclass
class DecideBuild(BaseNode[BuildState, BuildDeps]):
    async def run(self, ctx: GraphRunContext[BuildState, BuildDeps]) -> PlaceBuild | ReportBuild:
        try:
            ctx.deps.builds.decide(ctx.state)
        except ValueError:
            ctx.state.result = ctx.deps.builds.disposition(
                ctx.state, "refused", "Observed target, support, reach, mode or inventory refused."
            )
            return ReportBuild()
        return PlaceBuild()


@dataclass
class PlaceBuild(BaseNode[BuildState, BuildDeps]):
    async def run(self, ctx: GraphRunContext[BuildState, BuildDeps]) -> ReadBuildPostflight | ReportBuild:
        try:
            await ctx.deps.builds.place(ctx.state, ctx.deps.common.sigil_provider())
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError, ValueError):
            ctx.state.result = ctx.deps.builds.disposition(
                ctx.state,
                "outcome_unknown" if ctx.state.action_count else "refused",
                "Placement has no safe disposition; effects may remain.",
            )
        return ReadBuildPostflight() if ctx.state.result is None else ReportBuild()


@dataclass
class ReadBuildPostflight(BaseNode[BuildState, BuildDeps]):
    async def run(self, ctx: GraphRunContext[BuildState, BuildDeps]) -> ReportBuild:
        try:
            ctx.state.after = await ctx.deps.builds.read(ctx.state)
            ctx.deps.builds.confirm(ctx.state)
        except (OSError, RuntimeError, ValueError):
            ctx.state.result = ctx.deps.builds.disposition(
                ctx.state,
                "outcome_unknown",
                "Postflight did not prove the exact cell and expected inventory delta; effects may remain.",
            )
        return ReportBuild()


@dataclass
class ReportBuild(BaseNode[BuildState, BuildDeps, BuildResult]):
    async def run(self, ctx: GraphRunContext[BuildState, BuildDeps]) -> End[BuildResult]:
        result = ctx.deps.builds.report(ctx.state)
        ctx.deps.common.events.emitter(ctx.state.run_id).log(json.dumps(result.model_dump(mode="json")))
        return End(result)


def horizon_build_workflow(service: HorizonBuildService) -> Workflow:
    """Register only in the explicit local assembly supplied this exact service."""
    nodes = (ValidateBuild, ReadBuildPreflight, DecideBuild, PlaceBuild, ReadBuildPostflight, ReportBuild)
    keys = ("validate", "read_preflight", "decide", "place", "read_postflight", "report")
    graph = build_serial_graph(nodes=nodes, state_type=BuildState, deps_type=BuildDeps, output_type=BuildResult)

    def make_state(intent: Intent) -> BuildState:
        if (
            intent.run_id is None
            or intent.session_id != service.assist.policy.session_id
            or intent.source != "horizon.build_step"
        ):
            msg = "Build Run identity or session differs from admission."
            raise ValueError(msg)
        return BuildState(run_id=intent.run_id, session_id=intent.session_id, prompt=intent.prompt)

    def validate_state(intent: Intent, state: BaseModel) -> None:
        if not isinstance(state, BuildState) or (state.run_id, state.session_id, state.prompt) != (
            intent.run_id,
            intent.session_id,
            intent.prompt,
        ):
            msg = "Build Graph state differs from its admitted Run."
            raise ValueError(msg)

    return Workflow(
        name="blockworld.horizon_build_step",
        title="Finite Horizon build cell",
        description="One admitted plank cell and client observations; no placement receipt.",
        trigger=Trigger(
            hint="Explicit admitted Horizon build cell", match=lambda intent: intent.source == "horizon.build_step"
        ),
        graph=graph,
        start_node=ValidateBuild,
        make_state=make_state,
        validate_state=validate_state,
        bind_deps=lambda common: BuildDeps(common, service),
        manifest=PatternManifest(
            key="blockworld.horizon_build_step",
            revision="1",
            implementation_revision="py.1",
            checkpoint_schema="horizon-build-step-state-v1",
            entry_node="validate",
            nodes=(
                *(
                    PatternNode(key=key, label=key.replace("_", " ").capitalize(), kind="step", implementation=node)
                    for key, node in zip(keys, nodes, strict=True)
                ),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=tuple(
                PatternEdge(key=f"{a}-{b}", source=a, target=b)
                for a, b in (
                    ("validate", "read_preflight"),
                    ("validate", "report"),
                    ("read_preflight", "decide"),
                    ("read_preflight", "report"),
                    ("decide", "place"),
                    ("decide", "report"),
                    ("place", "read_postflight"),
                    ("place", "report"),
                    ("read_postflight", "report"),
                    ("report", "end"),
                )
            ),
        ),
    )
