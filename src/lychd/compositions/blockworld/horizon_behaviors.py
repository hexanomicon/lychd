"""Finite native observation/follow ticks; cadence and containment belong to the caller.

These process-local scores read exact already-bound clients. They neither discover
players nor schedule work, and client observations never become world receipts.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.blockworld.horizon_assist import (
    COORDINATE_COUNT,
    AssistDocument,
    AssistRequest,
    AssistResult,
    HorizonAssistService,
    PointAction,
    ReadAction,
)
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.graph import build_serial_graph

MIN_FOLLOW_PROGRESS = 0.05
BehaviorKind = Literal[
    "changed", "unchanged", "moved", "no_progress", "movement_unverified", "refused", "client_error", "outcome_unknown"
]


class ObservationPort(Protocol):
    """An exact own-client pose feed; no command or stop authority is exposed."""

    async def observe(self) -> dict[str, Any]: ...


class BehaviorDirective(AssistDocument):
    kind: Literal["idle", "follow"]
    task_id: str
    duration_s: float = Field(gt=0, le=60)

    @field_validator("task_id")
    @classmethod
    def canonical_identity(cls, value: str) -> str:
        if str(UUID(value)) != value:
            msg = "Task identity must be a canonical UUID."
            raise ValueError(msg)
        return value


class BehaviorPolicy(AssistDocument):
    max_tasks: int = Field(default=20, ge=1, le=100)
    max_ticks: int = Field(default=60, ge=1, le=60)
    cadence_s: float = Field(default=1.0, ge=1, le=60)
    freshness_s: float = Field(default=3.0, gt=0, le=3)
    deadband: float = Field(default=1.5, ge=1.5, le=16)
    max_segment: float = Field(default=4.0, gt=1.5, le=4)
    max_separation: float = Field(default=16.0, ge=1.5, le=32)


class BehaviorTick(AssistDocument):
    request_id: str
    task_id: str
    kind: Literal["idle", "follow"]
    generation: int = Field(ge=1)
    sequence: int = Field(ge=1, le=60)
    created_at: float
    deadline: float


class BehaviorResult(AssistDocument):
    request_id: str
    task_id: str
    generation: int
    sequence: int
    kind: BehaviorKind
    detail: str
    stop_required: bool
    observation_count: int = 0
    action_count: int = 0
    started_at: float
    finished_at: float
    sample_time: float | None = None
    distance: float | None = None
    action_result: AssistResult | None = None
    start_position: tuple[float, float, float] | None = None
    end_position: tuple[float, float, float] | None = None
    displacement: float | None = Field(default=None, ge=0)
    progress: float | None = None
    distance_after: float | None = Field(default=None, ge=0)


class _Pose(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, strict=True, allow_inf_nan=False)
    position: tuple[float, float, float]
    health: float = Field(gt=0)

    @field_validator("position", mode="before")
    @classmethod
    def finite_position(cls, value: Any) -> tuple[float, float, float]:
        values = cast("list[Any]", value) if type(value) is list else []
        if len(values) != COORDINATE_COUNT or any(
            type(item) not in (int, float) or not math.isfinite(item) for item in values
        ):
            msg = "Own-client pose requires exactly three finite original numbers."
            raise ValueError(msg)
        return float(values[0]), float(values[1]), float(values[2])


class _Observation(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, strict=True, allow_inf_nan=False)
    world: str  # Remote clients may report an empty cosmetic label; never invent a world identity.
    dimension: str = Field(min_length=1)
    screen: Literal["playing"]
    paused: Literal[False]
    player: _Pose
    busy: str | None = None

    @field_validator("paused", mode="before")
    @classmethod
    def original_false(cls, value: Any) -> Any:
        if value is not False:
            msg = "Client must explicitly report an unpaused state."
            raise ValueError(msg)
        return value


class BehaviorState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    run_id: str
    session_id: str
    prompt: str
    tick: BehaviorTick | None = None
    sample_time: float | None = None
    bot: _Observation | None = None
    target: _Observation | None = None
    pre_command_bot: _Observation | None = None
    post_command_bot: _Observation | None = None
    action_result: AssistResult | None = None
    action: PointAction | None = None
    result: BehaviorResult | None = None
    observation_count: int = 0
    action_count: int = 0
    distance: float | None = None


class HorizonBehaviorService:
    """Loop-owned finite authority, immutable tick identities and local decision records.

    Begin/fence never yield. A supervisor must settle any previous owned effect
    before admitting another Run. Counters count this composition's observe calls
    and shared assist command attempts, not hidden reads inside a control adapter.
    """

    def __init__(
        self,
        assist: HorizonAssistService,
        target: ObservationPort | None = None,
        policy: BehaviorPolicy | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Bind supplied collaborators without starting a task or reading a client."""
        self.assist = assist
        self.target = target
        self.policy = policy or BehaviorPolicy()
        self.clock = clock
        self.generation = 0
        self.directive: BehaviorDirective | None = None
        self.deadline = 0.0
        self.results: dict[str, BehaviorResult] = {}
        self.records: list[dict[str, Any]] = []
        self.observation_count = 0
        self.action_count = 0
        self.fence_reason: str | None = None
        self._sequence = 0
        self._ticks: dict[str, BehaviorTick] = {}
        self._runs: dict[str, str] = {}
        self._tasks: set[str] = set()
        self._last: _Observation | None = None
        self._task_policy = self.policy
        self._assist_policy = self.assist.policy
        self._task_target = self.target

    def fence(self, reason: str) -> None:
        """Invalidate all prior tick/sample generations before the caller can yield."""
        self.generation += 1
        self.directive = None
        self.deadline = 0.0
        self.fence_reason = reason
        self._last = None

    def begin(self, directive: BehaviorDirective) -> int:
        """Replace authority synchronously; task identities cannot be reused."""
        self.fence("replaced")
        if len(self._tasks) >= self.policy.max_tasks:
            msg = "Behavior session task budget is exhausted."
            raise ValueError(msg)
        if directive.task_id in self._tasks:
            msg = "Task identity has already been used."
            raise ValueError(msg)
        if directive.kind == "follow" and (self.target is None or self.assist.policy.action_timeout_s > 1):
            msg = "Follow requires a bound target and an assist action timeout of at most one second."
            raise ValueError(msg)
        now = self.clock()
        if not math.isfinite(now):
            msg = "Behavior clock is unavailable."
            raise ValueError(msg)
        self._tasks.add(directive.task_id)
        self.directive = directive
        self._task_policy = self.policy
        self._assist_policy = self.assist.policy
        self._task_target = self.target
        self.deadline = now + directive.duration_s
        self._sequence = 0
        self.fence_reason = None
        return self.generation

    def new_tick(self) -> BehaviorTick:
        """Pin one finite tick; callers coalesce requests and own cadence."""
        directive = self.directive
        now = self.clock()
        if (
            directive is None
            or not math.isfinite(now)
            or now >= self.deadline
            or self._sequence >= self.policy.max_ticks
        ):
            msg = "Behavior deadline, authority or tick budget is exhausted."
            raise ValueError(msg)
        self._sequence += 1
        tick = BehaviorTick(
            request_id=str(uuid5(UUID(directive.task_id), f"{self.generation}:{self._sequence}")),
            task_id=directive.task_id,
            kind=directive.kind,
            generation=self.generation,
            sequence=self._sequence,
            created_at=now,
            deadline=self.deadline,
        )
        self._ticks[tick.request_id] = tick
        return tick

    def check(self, tick: BehaviorTick, sample_time: float | None = None) -> None:
        """Refuse substituted identity, expired authority and reads that aged while awaited."""
        directive = self.directive
        now = self.clock()
        if (
            directive is None
            or self.policy != self._task_policy
            or self.assist.policy != self._assist_policy
            or self.target is not self._task_target
            or self._ticks.get(tick.request_id) != tick
            or tick.generation != self.generation
            or (tick.task_id, tick.kind) != (directive.task_id, directive.kind)
            or tick.deadline != self.deadline
            or not math.isfinite(now)
            or now < tick.created_at
            or now >= tick.deadline
            or (sample_time is not None and (now < sample_time or now - sample_time >= self.policy.freshness_s))
        ):
            msg = "Behavior identity, generation, deadline or observation freshness refused."
            raise ValueError(msg)

    def validate(
        self,
        tick: BehaviorTick,
        principal: Sigil,
        run_id: str | None = None,
        kind: Literal["idle", "follow"] | None = None,
    ) -> None:
        self.check(tick)
        if kind is not None and tick.kind != kind:
            msg = "Tick kind differs from the admitted score."
            raise ValueError(msg)
        self.assist.validate(AssistRequest(request_id=tick.request_id, action=ReadAction(kind="state")), principal)
        if run_id is not None:
            if self._runs.get(tick.request_id, run_id) != run_id:
                msg = "Tick identity belongs to another Run."
                raise ValueError(msg)
            self._runs[tick.request_id] = run_id

    def disposition(
        self,
        state: BehaviorState,
        kind: BehaviorKind,
        detail: str,
    ) -> BehaviorResult:
        tick = state.tick
        start = state.pre_command_bot.player.position if state.pre_command_bot is not None else None
        end = state.post_command_bot.player.position if state.post_command_bot is not None else None
        distance_after = math.dist(end, state.target.player.position) if end is not None and state.target else None
        return BehaviorResult(
            request_id=tick.request_id if tick else state.run_id,
            task_id=tick.task_id if tick else "",
            generation=tick.generation if tick else self.generation,
            sequence=tick.sequence if tick else 0,
            kind=kind,
            detail=detail,
            stop_required=kind in {"no_progress", "movement_unverified", "refused", "client_error", "outcome_unknown"},
            observation_count=state.observation_count,
            action_count=state.action_count,
            started_at=tick.created_at if tick else self.clock(),
            finished_at=self.clock(),
            sample_time=state.sample_time,
            distance=state.distance,
            action_result=state.action_result,
            start_position=start,
            end_position=end,
            displacement=math.dist(start, end) if start is not None and end is not None else None,
            progress=(
                math.dist(start, state.target.player.position) - distance_after
                if start is not None and state.target is not None and distance_after is not None
                else None
            ),
            distance_after=distance_after,
        )

    async def observe(self, state: BehaviorState) -> None:
        tick = state.tick
        if tick is None:
            msg = "No admitted behavior tick."
            raise ValueError(msg)
        self.check(tick)
        # Capture BEFORE any awaited read, including the bot read before target.
        state.sample_time = self.clock()
        state.observation_count += 1
        self.observation_count += 1
        bot = _Observation.model_validate(await self.assist.control.observe())
        self.check(tick, state.sample_time)
        if not self.assist.policy.contains(bot.player.position):
            msg = "Observed bot is outside session bounds."
            raise ValueError(msg)
        if self._last is not None and (bot.world, bot.dimension) != (self._last.world, self._last.dimension):
            msg = "Observed world or dimension changed."
            raise ValueError(msg)
        state.bot = bot
        if tick.kind == "follow":
            target = self.target
            if (
                target is None
                or bot.busy is not None
                or (self._last is not None and bot.player.health < self._last.player.health)
            ):
                msg = "Target is unavailable, bot is busy or bot health decreased."
                raise ValueError(msg)
            state.observation_count += 1
            self.observation_count += 1
            sample = _Observation.model_validate(await target.observe())
            self.check(tick, state.sample_time)
            if (sample.world, sample.dimension) != (bot.world, bot.dimension) or not self.assist.policy.contains(
                sample.player.position
            ):
                msg = "Target world, dimension or coordinate bounds differ."
                raise ValueError(msg)
            state.target = sample

    def decide_idle(self, state: BehaviorState) -> None:
        if state.tick is None or state.bot is None:
            msg = "Idle decision lacks a validated observation."
            raise ValueError(msg)
        self.check(state.tick, state.sample_time)
        kind = "unchanged" if state.bot == self._last else "changed"
        state.result = self.disposition(state, kind, "Client observation only; idle performs no command.")

    def decide_follow(self, state: BehaviorState) -> None:
        if state.tick is None or state.bot is None or state.target is None:
            msg = "Follow decision lacks exact client observations."
            raise ValueError(msg)
        self.check(state.tick, state.sample_time)
        origin, target = state.bot.player.position, state.target.player.position
        distance = math.dist(origin, target)
        state.distance = distance
        if distance > self.policy.max_separation:
            msg = "Target separation exceeds the finite follow policy."
            raise ValueError(msg)
        if distance <= self.policy.deadband:
            state.result = self.disposition(state, "unchanged", "Target is within the stop-distance deadband.")
            return
        # Horizon finishes within its fixed --near 1.5 radius of this waypoint.
        # Place that radius at the requested deadband instead of inside it.
        length = min(self.policy.max_segment, distance - max(0.0, self.policy.deadband - 1.5))
        factor = length / distance
        state.action = PointAction(
            kind="goto",
            x=origin[0] + (target[0] - origin[0]) * factor,
            y=origin[1] + (target[1] - origin[1]) * factor,
            z=origin[2] + (target[2] - origin[2]) * factor,
        )

    async def act(self, state: BehaviorState, principal: Sigil) -> None:
        tick, bot, target, action = state.tick, state.bot, state.target, state.action
        if tick is None or bot is None or target is None or action is None or tick.kind != "follow":
            msg = "No finite admitted follow segment."
            raise ValueError(msg)
        self.check(tick, state.sample_time)
        pinned_policy = self.policy

        def pre_write(latest: dict[str, Any]) -> None:
            self.check(tick, state.sample_time)
            pose = _Observation.model_validate(latest)
            if (
                self.policy != pinned_policy
                or self.assist.policy.action_timeout_s > 1
                or pose.busy is not None
                or pose.player.health < bot.player.health
                or (pose.world, pose.dimension) != (bot.world, bot.dimension)
                or math.dist(pose.player.position, (action.x, action.y, action.z)) > self.policy.max_segment
                or math.dist(pose.player.position, target.player.position) > self.policy.max_separation
            ):
                msg = "Latest client pose or behavior policy refused final handoff."
                raise ValueError(msg)
            state.pre_command_bot = pose

        request = AssistRequest(request_id=tick.request_id, action=action)
        before = self.assist.used
        state.result = self.disposition(state, "outcome_unknown", "Follow attempt awaiting a client disposition.")
        self.results[tick.request_id] = state.result
        try:
            result = await self.assist.execute(request, state.run_id, principal, pre_write_guard=pre_write)
        finally:
            state.action_count = self.assist.used - before
            self.action_count += state.action_count
            self.results[tick.request_id] = self.disposition(
                state, "outcome_unknown", "Follow attempt has no settled client disposition."
            )
        state.action_result = result
        if result.kind != "client_observed":
            state.result = self.disposition(state, result.kind, result.detail)
            return
        # Retain the known reply before the next await, including cancellation of
        # the postflight read. A missing observation cannot make that reply unknown.
        state.result = self.disposition(state, "movement_unverified", "Client replied; movement is unverified.")
        self.results[tick.request_id] = state.result
        try:
            await self.verify_follow(state)
        except (OSError, RuntimeError, ValueError):
            state.result = self.disposition(
                state, "movement_unverified", "Client replied; post-command observation unavailable, stale or unsafe."
            )

    async def verify_follow(self, state: BehaviorState) -> None:
        """Measure progress from the final handoff pose toward the original target sample."""
        tick, start, target = state.tick, state.pre_command_bot, state.target
        if tick is None or start is None or target is None:
            msg = "Final authorized pre-command pose is unavailable."
            raise ValueError(msg)
        self.check(tick, state.sample_time)
        state.observation_count += 1
        self.observation_count += 1
        state.result = self.disposition(state, "movement_unverified", "Client replied; post-command read pending.")
        self.results[tick.request_id] = state.result
        post = _Observation.model_validate(await self.assist.control.observe())
        self.check(tick, state.sample_time)
        if (
            (post.world, post.dimension) != (start.world, start.dimension)
            or not self.assist.policy.contains(post.player.position)
            or post.busy is not None
            or post.player.health < start.player.health
        ):
            msg = "Post-command client identity, bounds, health or idle state changed."
            raise ValueError(msg)
        distance_after = math.dist(post.player.position, target.player.position)
        progress = math.dist(start.player.position, target.player.position) - distance_after
        if not all(
            math.isfinite(value)
            for value in (distance_after, progress, math.dist(start.player.position, post.player.position))
        ):
            msg = "Post-command movement metrics are not finite."
            raise ValueError(msg)
        state.post_command_bot = state.bot = post
        state.result = self.disposition(
            state,
            "moved" if progress >= MIN_FOLLOW_PROGRESS else "no_progress",
            "Observed progress toward the original target sample."
            if progress >= MIN_FOLLOW_PROGRESS
            else "No sufficient observed progress; finite follow task stopped.",
        )

    def report(self, state: BehaviorState) -> BehaviorResult:
        result = state.result
        if result is None:
            msg = "Behavior has no disposition."
            raise ValueError(msg)
        tick = state.tick
        if not result.stop_required and tick is not None:
            try:
                self.check(tick, state.sample_time)
            except ValueError:
                result = BehaviorResult.model_validate(
                    {
                        **result.model_dump(),
                        "stop_required": True,
                        "detail": f"{result.detail} Behavior authority expired before report.",
                    }
                )
            else:
                self._last = state.bot
        self.results[result.request_id] = result
        self.records.append(result.model_dump(mode="json"))
        # A stale Run can record its own outcome, but cannot fence its successor.
        if result.stop_required and tick is not None and tick.generation == self.generation:
            self.fence(result.kind)
        return result


@dataclass(frozen=True)
class BehaviorDeps:
    common: WorkflowServices
    behaviors: HorizonBehaviorService


def _validate(ctx: GraphRunContext[BehaviorState, BehaviorDeps], kind: Literal["idle", "follow"]) -> bool:
    try:
        tick = BehaviorTick.model_validate_json(ctx.state.prompt)
        ctx.state.tick = tick
        ctx.deps.behaviors.validate(tick, ctx.deps.common.sigil_provider(), ctx.state.run_id, kind)
    except ValueError:
        ctx.state.result = ctx.deps.behaviors.disposition(ctx.state, "refused", "Behavior authority refused.")
        return False
    return True


async def _observe(ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> bool:
    try:
        await ctx.deps.behaviors.observe(ctx.state)
    except (OSError, RuntimeError, ValueError):
        ctx.state.result = ctx.deps.behaviors.disposition(
            ctx.state, "refused", "Client observation unavailable or stale."
        )
        return False
    return True


@dataclass
class ValidateIdle(BaseNode[BehaviorState, BehaviorDeps]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> ObserveIdle | ReportBehavior:
        return ObserveIdle() if _validate(ctx, "idle") else ReportBehavior()


@dataclass
class ObserveIdle(BaseNode[BehaviorState, BehaviorDeps]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> DecideIdle | ReportBehavior:
        return DecideIdle() if await _observe(ctx) else ReportBehavior()


@dataclass
class DecideIdle(BaseNode[BehaviorState, BehaviorDeps]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> ReportBehavior:
        try:
            ctx.deps.behaviors.decide_idle(ctx.state)
        except ValueError:
            ctx.state.result = ctx.deps.behaviors.disposition(ctx.state, "refused", "Idle decision refused.")
        return ReportBehavior()


@dataclass
class ValidateFollow(BaseNode[BehaviorState, BehaviorDeps]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> ObserveFollow | ReportBehavior:
        return ObserveFollow() if _validate(ctx, "follow") else ReportBehavior()


@dataclass
class ObserveFollow(BaseNode[BehaviorState, BehaviorDeps]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> DecideFollow | ReportBehavior:
        return DecideFollow() if await _observe(ctx) else ReportBehavior()


@dataclass
class DecideFollow(BaseNode[BehaviorState, BehaviorDeps]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> ActFollow | ReportBehavior:
        try:
            ctx.deps.behaviors.decide_follow(ctx.state)
        except ValueError:
            ctx.state.result = ctx.deps.behaviors.disposition(ctx.state, "refused", "Follow decision refused.")
        return ActFollow() if ctx.state.action is not None else ReportBehavior()


@dataclass
class ActFollow(BaseNode[BehaviorState, BehaviorDeps]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> ReportBehavior:
        try:
            await ctx.deps.behaviors.act(ctx.state, ctx.deps.common.sigil_provider())
        except (OSError, RuntimeError, ValueError):
            kind = "outcome_unknown" if ctx.state.action_count else "refused"
            ctx.state.result = ctx.deps.behaviors.disposition(
                ctx.state, kind, "Follow did not obtain a safe disposition."
            )
        return ReportBehavior()


@dataclass
class ReportBehavior(BaseNode[BehaviorState, BehaviorDeps, BehaviorResult]):
    async def run(self, ctx: GraphRunContext[BehaviorState, BehaviorDeps]) -> End[BehaviorResult]:
        result = ctx.deps.behaviors.report(ctx.state)
        ctx.deps.common.events.emitter(ctx.state.run_id).log(json.dumps(result.model_dump(mode="json")))
        return End(result)


def horizon_behavior_workflows(service: HorizonBehaviorService) -> tuple[Workflow, Workflow]:
    """Assemble two explicit native scores; normal boot registers neither."""
    return _workflow(service, "idle"), _workflow(service, "follow")


def _workflow(service: HorizonBehaviorService, kind: Literal["idle", "follow"]) -> Workflow:
    idle = kind == "idle"
    nodes = (
        (ValidateIdle, ObserveIdle, DecideIdle, ReportBehavior)
        if idle
        else (ValidateFollow, ObserveFollow, DecideFollow, ActFollow, ReportBehavior)
    )
    keys = (
        ("validate", "observe", "decide", "report") if idle else ("validate", "observe", "decide", "action", "report")
    )
    edges = [
        ("validate", "observe"),
        ("validate", "report"),
        ("observe", "decide"),
        ("observe", "report"),
        ("decide", "report"),
        ("report", "end"),
    ]
    if not idle:
        edges.extend((("decide", "action"), ("action", "report")))
    graph = build_serial_graph(
        nodes=nodes, state_type=BehaviorState, deps_type=BehaviorDeps, output_type=BehaviorResult
    )
    name = f"blockworld.horizon_{kind}_tick"
    source = f"horizon.{kind}_tick"

    def make_state(intent: Intent) -> BehaviorState:
        if intent.run_id is None or intent.session_id != service.assist.policy.session_id or intent.source != source:
            msg = "Behavior Run identity or session differs from admission."
            raise ValueError(msg)
        return BehaviorState(run_id=intent.run_id, session_id=intent.session_id, prompt=intent.prompt)

    def validate_state(intent: Intent, state: BaseModel) -> None:
        if not isinstance(state, BehaviorState) or (state.run_id, state.session_id, state.prompt) != (
            intent.run_id,
            intent.session_id,
            intent.prompt,
        ):
            msg = "Behavior Graph state differs from its admitted Run."
            raise ValueError(msg)

    return Workflow(
        name=name,
        title=f"Finite Horizon {kind} tick",
        description="One bounded own-client observation/follow tick; no world receipt.",
        trigger=Trigger(hint=f"Explicit Horizon {kind} tick", match=lambda intent: intent.source == source),
        graph=graph,
        start_node=nodes[0],
        make_state=make_state,
        validate_state=validate_state,
        bind_deps=lambda common: BehaviorDeps(common, service),
        manifest=PatternManifest(
            key=name,
            revision="1",
            implementation_revision="py.1",
            checkpoint_schema=f"horizon-{kind}-tick-state-v1",
            entry_node="validate",
            nodes=(
                *(
                    PatternNode(key=key, label=key.capitalize(), kind="step", implementation=node)
                    for key, node in zip(keys, nodes, strict=True)
                ),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=tuple(PatternEdge(key=f"{a}-{b}", source=a, target=b) for a, b in edges),
        ),
    )
