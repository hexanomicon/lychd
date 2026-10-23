"""Finite experimental Horizon client assistance, separate from placement receipts.

The parser and Graph perform no filesystem, socket, model, or process effects.
One request is one action; a later bounded supervisor may submit new requests.
"""

from __future__ import annotations

import json
import math
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
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.graph import build_serial_graph

FIRST_PRINTABLE = 32
DELETE_CHARACTER = 127
MAX_INSTRUCTION_CHARS = 1000
COORDINATE_COUNT = 3
MAX_REQUEST_BYTES = 4096


class AssistDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class ReadAction(AssistDocument):
    kind: Literal["state", "status"]


class PointAction(AssistDocument):
    kind: Literal["goto", "look_at"]
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


class SayAction(AssistDocument):
    kind: Literal["say"]
    text: str = Field(min_length=1, max_length=200)

    @field_validator("text")
    @classmethod
    def ordinary_chat(cls, value: str) -> str:
        if (
            value != value.strip()
            or value.startswith("/")
            or any(ord(char) < FIRST_PRINTABLE or ord(char) == DELETE_CHARACTER for char in value)
        ):
            msg = "Chat must be ordinary text without control characters or a command prefix."
            raise ValueError(msg)
        return value


AssistAction = Annotated[ReadAction | PointAction | SayAction, Field(discriminator="kind")]
ACTION_ADAPTER = TypeAdapter(AssistAction)


class AssistRequest(AssistDocument):
    request_id: str
    action: AssistAction
    transcript: str = Field(default="", max_length=1000)
    source: Literal["text", "transcript"] = "text"

    @field_validator("request_id")
    @classmethod
    def canonical_id(cls, value: str) -> str:
        if str(UUID(value)) != value:
            msg = "Request identity must be a canonical UUID."
            raise ValueError(msg)
        return value


def decode_request(document: str) -> AssistRequest:
    """Refuse duplicate keys and non-finite values before typed wire validation."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                msg = "Duplicate request key."
                raise ValueError(msg)
            result[key] = value
        return result

    def invalid(_: str) -> Any:
        msg = "Non-finite request number."
        raise ValueError(msg)

    if len(document.encode()) > MAX_REQUEST_BYTES:
        msg = "Request exceeds the wire byte limit."
        raise ValueError(msg)
    return AssistRequest.model_validate(json.loads(document, object_pairs_hook=unique, parse_constant=invalid))


class AssistPolicy(AssistDocument):
    """One session's finite local policy; coordinates are client-side checks only."""

    session_id: str = Field(min_length=1, max_length=100)
    principal: str = Field(min_length=1, max_length=100)
    expires_at: datetime
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float
    max_distance: float = Field(default=8.0, gt=0, le=16)
    action_timeout_s: float = Field(default=3.0, ge=0.25, le=5)
    max_actions: int = Field(default=20, ge=1, le=100)
    permitted: tuple[Literal["state", "status", "goto", "look_at", "say", "place"], ...] = ("state", "status")

    @model_validator(mode="after")
    def bounded(self) -> AssistPolicy:
        if self.expires_at.tzinfo is None or any(
            low > high or not math.isfinite(low) or not math.isfinite(high)
            for low, high in ((self.min_x, self.max_x), (self.min_y, self.max_y), (self.min_z, self.max_z))
        ):
            msg = "Policy requires timezone-aware expiry and ordered finite coordinates."
            raise ValueError(msg)
        return self

    def contains(self, point: tuple[float, float, float]) -> bool:
        return all(
            low <= value <= high
            for value, low, high in zip(
                point, (self.min_x, self.min_y, self.min_z), (self.max_x, self.max_y, self.max_z), strict=True
            )
        )


class AssistResult(AssistDocument):
    request_id: str
    kind: Literal["client_observed", "refused", "client_error", "outcome_unknown"]
    detail: str
    observation: dict[str, Any] | None = None


class ControlPort(Protocol):
    async def observe(self) -> dict[str, Any]: ...
    async def invoke(
        self, run_id: str, line: str, *, query: bool = False, authorize: Callable[[dict[str, Any]], None] | None = None
    ) -> Any: ...


def encode_action(action: AssistAction, policy: AssistPolicy) -> str:
    """Translate only admitted structured commands; this is not a shell grammar."""
    if isinstance(action, ReadAction):
        return action.kind
    if isinstance(action, SayAction):
        return f"chat {action.text}"
    coordinates = f"{action.x:.9g} {action.y:.9g} {action.z:.9g}"
    if action.kind == "look_at":
        return f"look-at {coordinates}"
    return f"goto {coordinates} --near 1.5 --timeout {policy.action_timeout_s:.9g}"


def parse_text(text: str) -> AssistAction:
    """Recognize a small English/Slovak grammar; ambiguity refuses without a model."""
    if len(text) > MAX_INSTRUCTION_CHARS or any(ord(char) < FIRST_PRINTABLE for char in text):
        msg = "Instruction is too large or contains control characters."
        raise ValueError(msg)
    value = text.strip()
    read_word = value.casefold().rstrip(".!?")
    if read_word in {"state", "stav"}:
        return ReadAction(kind="state")
    if read_word == "status":
        return ReadAction(kind="status")
    head, _, tail = value.partition(" ")
    command = head.casefold()
    if command in {"say", "povedz"}:
        return SayAction(kind="say", text=tail)
    if command in {"goto", "chod", "choď", "look-at", "pozri"}:
        coordinates = tail.split()
        if len(coordinates) != COORDINATE_COUNT:
            msg = "An exact three-coordinate target is required."
            raise ValueError(msg)
        return PointAction(
            kind="look_at" if command in {"look-at", "pozri"} else "goto",
            x=float(coordinates[0]),
            y=float(coordinates[1]),
            z=float(coordinates[2]),
        )
    msg = "Unsupported or ambiguous instruction; stop uses the cancellation path."
    raise ValueError(msg)


def _observed_point(state: dict[str, Any]) -> tuple[float, float, float]:
    player = state.get("player")
    if type(player) is not dict:
        msg = "Observed player is unavailable."
        raise ValueError(msg)
    raw = cast("dict[str, Any]", player).get("position")
    if type(raw) is not list:
        msg = "Observed position is unavailable."
        raise ValueError(msg)
    values = cast("list[Any]", raw)
    if len(values) != COORDINATE_COUNT or any(
        type(value) not in (int, float) or not math.isfinite(value) for value in values
    ):
        msg = "Observed position must contain three finite numbers."
        raise ValueError(msg)
    return float(values[0]), float(values[1]), float(values[2])


class HorizonAssistService:
    """Process-local admission and results, never a durable placement ledger."""

    def __init__(self, policy: AssistPolicy, control: ControlPort) -> None:
        """Bind one immutable policy and local outcome custody."""
        self.policy = policy
        self.control = control
        self.used = 0
        self.results: dict[str, AssistResult] = {}
        self.run_results: dict[str, AssistResult] = {}
        self.requests: dict[str, bytes] = {}

    def validate(self, request: AssistRequest, principal: Sigil) -> None:
        if principal.name != self.policy.principal or "horizon:assist" not in principal.scopes:
            msg = "Principal has no session authority."
            raise ValueError(msg)
        if datetime.now(UTC) >= self.policy.expires_at or self.used >= self.policy.max_actions:
            msg = "Session deadline or action budget exhausted."
            raise ValueError(msg)
        if request.action.kind not in self.policy.permitted:
            msg = "Action is not permitted by this session."
            raise ValueError(msg)
        if isinstance(request.action, PointAction) and not self.policy.contains(
            (request.action.x, request.action.y, request.action.z)
        ):
            msg = "Target is outside session coordinate bounds."
            raise ValueError(msg)

    async def execute(  # noqa: C901 - retain the existing admission boundary plus the optional final behavior guard
        self,
        request: AssistRequest,
        run_id: str,
        principal: Sigil,
        *,
        pre_write_guard: Callable[[dict[str, Any]], None] | None = None,
    ) -> AssistResult:
        document = request.model_dump_json().encode()
        if request.request_id in self.requests:
            if self.requests[request.request_id] != document:
                msg = "Request identity was reused with changed content."
                raise ValueError(msg)
            return self.results[request.request_id]
        self.validate(request, principal)
        if isinstance(request.action, PointAction):
            try:
                state = await self.control.observe()
            except (OSError, RuntimeError, ValueError) as exc:
                msg = "Current client position is unavailable."
                raise ValueError(msg) from exc
            position = _observed_point(state)
            if (
                not self.policy.contains(position)
                or math.dist(position, (request.action.x, request.action.y, request.action.z))
                > self.policy.max_distance
            ):
                msg = "Current position or target distance exceeds session bounds."
                raise ValueError(msg)
        # Fresh authority check after observation, before committing this local attempt.
        self.validate(request, principal)
        self.used += 1
        self.requests[request.request_id] = document
        self.results[request.request_id] = AssistResult(
            request_id=request.request_id, kind="outcome_unknown", detail="Local attempt retained; no replay."
        )
        pinned_policy = self.policy

        def authorize(latest: dict[str, Any]) -> None:
            if (
                self.policy != pinned_policy
                or datetime.now(UTC) >= self.policy.expires_at
                or self.used > self.policy.max_actions
            ):
                msg = "Session policy or deadline changed before handoff."
                raise ValueError(msg)
            if isinstance(request.action, PointAction):
                pose = _observed_point(latest)
                if (
                    not self.policy.contains(pose)
                    or math.dist(pose, (request.action.x, request.action.y, request.action.z))
                    > self.policy.max_distance
                ):
                    msg = "Latest observed pose exceeds current bounds."
                    raise ValueError(msg)

            if pre_write_guard is not None:
                pre_write_guard(latest)

        outcome = await self.control.invoke(
            run_id,
            encode_action(request.action, self.policy),
            query=isinstance(request.action, ReadAction),
            authorize=authorize,
        )
        result = AssistResult(
            request_id=request.request_id, kind=outcome.kind, detail=outcome.detail, observation=outcome.observation
        )
        self.results[request.request_id] = result
        return result


class AssistState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    run_id: str
    session_id: str
    prompt: str
    request: AssistRequest | None = None
    result: AssistResult | None = None


@dataclass(frozen=True)
class AssistDeps:
    common: WorkflowServices
    assist: HorizonAssistService


@dataclass
class ValidateAssist(BaseNode[AssistState, AssistDeps]):
    async def run(self, ctx: GraphRunContext[AssistState, AssistDeps]) -> ExecuteAssist | ReportAssist:
        try:
            request = decode_request(ctx.state.prompt)
            ctx.state.request = request
            ctx.deps.assist.validate(request, ctx.deps.common.sigil_provider())
        except ValueError:
            ctx.state.result = AssistResult(
                request_id=ctx.state.request.request_id if ctx.state.request is not None else ctx.state.run_id,
                kind="refused",
                detail="Instruction or current session authority refused.",
            )
            return ReportAssist()
        return ExecuteAssist()


@dataclass
class ExecuteAssist(BaseNode[AssistState, AssistDeps]):
    async def run(self, ctx: GraphRunContext[AssistState, AssistDeps]) -> ReportAssist:
        if ctx.state.request is None:
            msg = "No validated action is retained."
            raise ValueError(msg)
        try:
            ctx.state.result = await ctx.deps.assist.execute(
                ctx.state.request, ctx.state.run_id, ctx.deps.common.sigil_provider()
            )
        except ValueError:
            ctx.state.result = AssistResult(
                request_id=ctx.state.request.request_id, kind="refused", detail="Current bounds or authority refused."
            )
        return ReportAssist()


@dataclass
class ReportAssist(BaseNode[AssistState, AssistDeps, AssistResult]):
    async def run(self, ctx: GraphRunContext[AssistState, AssistDeps]) -> End[AssistResult]:
        result = ctx.state.result
        if result is None:
            msg = "No action disposition was retained."
            raise ValueError(msg)
        ctx.deps.assist.run_results[ctx.state.run_id] = result
        ctx.deps.common.events.emitter(ctx.state.run_id).log(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        )
        return End(result)


def horizon_assist_workflow(service: HorizonAssistService) -> Workflow:
    """Assemble explicitly; importing this module registers nothing."""
    graph = build_serial_graph(
        nodes=(ValidateAssist, ExecuteAssist, ReportAssist),
        state_type=AssistState,
        deps_type=AssistDeps,
        output_type=AssistResult,
    )

    def make_state(intent: Intent) -> AssistState:
        if intent.run_id is None or intent.session_id != service.policy.session_id or intent.source != "horizon.assist":
            msg = "Run identity or session differs from admission."
            raise ValueError(msg)
        return AssistState(run_id=intent.run_id, session_id=intent.session_id, prompt=intent.prompt)

    def validate_state(intent: Intent, state: BaseModel) -> None:
        if not isinstance(state, AssistState) or (state.run_id, state.session_id, state.prompt) != (
            intent.run_id,
            intent.session_id,
            intent.prompt,
        ):
            msg = "Graph state differs from its admitted Run."
            raise ValueError(msg)

    return Workflow(
        name="blockworld.horizon_assist",
        title="Experimental Horizon client assistance",
        description="One finite client action; observations are not world receipts.",
        trigger=Trigger(hint="Explicit Horizon assist input", match=lambda intent: intent.source == "horizon.assist"),
        graph=graph,
        start_node=ValidateAssist,
        make_state=make_state,
        validate_state=validate_state,
        bind_deps=lambda common: AssistDeps(common, service),
        manifest=PatternManifest(
            key="blockworld.horizon_assist",
            revision="1",
            implementation_revision="py.1",
            checkpoint_schema="horizon-assist-state-v1",
            entry_node="validate",
            nodes=(
                PatternNode(key="validate", label="Validate action", kind="step", implementation=ValidateAssist),
                PatternNode(key="execute", label="Attempt client action", kind="step", implementation=ExecuteAssist),
                PatternNode(key="report", label="Report observation", kind="step", implementation=ReportAssist),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=tuple(
                PatternEdge(key=key, source=source, target=target)
                for key, source, target in (
                    ("validate-execute", "validate", "execute"),
                    ("validate-report", "validate", "report"),
                    ("execute-report", "execute", "report"),
                    ("report-end", "report", "end"),
                )
            ),
        ),
    )
