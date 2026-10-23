"""Authenticated literal-loopback companion HTTP, with strict bounded no-retry I/O."""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from lychd.compositions.blockworld.companion import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    ActionRecord,
    BridgeState,
    CellObservation,
    ClockObservation,
    CompanionRefusalError,
    CompanionRequest,
    CompanionResult,
    WeatherObservation,
    canonical_uuid,
    strict_json,
)
from lychd.lib.asyncio import complete_under_cancellation

MAX_TCP_PORT = 65535
MIN_TIMEOUT_S = 0.25
MAX_TIMEOUT_S = 5
MIN_POLL_S = 0.01
MAX_POLL_S = 0.5
MAX_FRESHNESS_MS = 5000
MAX_LEASE_MS = 60000
TERMINAL = frozenset({"applied", "refused", "expired", "cancelled", "unknown"})


class CompanionBridgeError(RuntimeError):
    """A transport or binding failure; never an action completion receipt."""


@dataclass(frozen=True)
class BridgeBinding:
    endpoint: str
    token: str = field(repr=False)
    actor_id: str
    timeout_s: float = 2.0
    poll_interval_s: float = 0.05

    def __post_init__(self) -> None:
        """Validate the narrow local transport profile without opening sockets."""
        parsed = urlsplit(self.endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.port is None
            or not 1 <= parsed.port <= MAX_TCP_PORT
        ):
            msg = "Endpoint must be literal http://127.0.0.1:<port> without credentials or path."
            raise ValueError(msg)
        if (
            re.fullmatch(r"[0-9a-f]{64}", self.token) is None
            or not MIN_TIMEOUT_S <= self.timeout_s <= MAX_TIMEOUT_S
            or not MIN_POLL_S <= self.poll_interval_s <= MAX_POLL_S
        ):
            msg = "Bridge token or finite timeout profile is invalid."
            raise ValueError(msg)
        canonical_uuid(self.actor_id)


class CompanionBridge:
    """One boot/actor binding, process-local fences and one priority stop attempt."""

    def __init__(self, binding: BridgeBinding, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Bind one endpoint and finite client; start no network request."""
        self.binding = binding
        self.epoch = 0
        self.paused = True
        self.state: BridgeState | None = None
        self._closed = False
        self._all_fenced = False
        self._fenced: set[str] = set()
        self._issued: dict[str, int] = {}
        self._stop_task: asyncio.Task[CompanionResult] | None = None
        self._client = httpx.AsyncClient(
            base_url=binding.endpoint.rstrip("/"),
            headers={
                "Authorization": f"Bearer {binding.token}",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
            timeout=httpx.Timeout(binding.timeout_s),
            follow_redirects=False,
            trust_env=False,
            transport=transport or httpx.AsyncHTTPTransport(retries=0),
        )

    async def _http(
        self, method: Literal["GET", "POST"], path: str, document: dict[str, Any] | None = None, *, expected: int = 200
    ) -> Any:
        raw = (
            None
            if document is None
            else json.dumps(document, allow_nan=False, ensure_ascii=False, separators=(",", ":")).encode()
        )
        if raw is not None and len(raw) > MAX_REQUEST_BYTES:
            msg = "Outgoing request exceeds protocol body limit."
            raise CompanionBridgeError(msg)
        try:
            async with self._client.stream(
                method, path, content=raw, headers={"Content-Type": "application/json; charset=utf-8"}
            ) as response:
                if response.status_code != expected:
                    msg = f"HTTP admission returned {response.status_code}; no completion receipt."
                    raise CompanionBridgeError(msg)
                media = response.headers.get("content-type", "").lower().replace(" ", "")
                if (
                    media not in {"application/json", "application/json;charset=utf-8"}
                    or response.headers.get("content-encoding", "identity").lower() != "identity"
                ):
                    msg = "Unexpected response media or compression."
                    raise CompanionBridgeError(msg)
                length = response.headers.get("content-length")
                if length is not None and (
                    not length.isascii() or not length.isdecimal() or int(length) > MAX_RESPONSE_BYTES
                ):
                    msg = "Invalid or oversized response length."
                    raise CompanionBridgeError(msg)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        msg = "Response exceeds bounded byte limit."
                        raise CompanionBridgeError(msg)
                    body.extend(chunk)
                if length is not None and int(length) != len(body):
                    msg = "Response body length differs from its framing."
                    raise CompanionBridgeError(msg)
                return strict_json(bytes(body), limit=MAX_RESPONSE_BYTES)
        except (httpx.HTTPError, ValueError, UnicodeError) as exc:
            msg = "Bridge transport or strict JSON failed; no completion receipt."
            raise CompanionBridgeError(msg) from exc

    def _check_state(self, state: BridgeState, *, allow_new_generation: bool = False) -> None:
        if state.actor_id != self.binding.actor_id or (self.state is not None and state.boot_id != self.state.boot_id):
            self.paused = True
            msg = "Server boot or actor identity changed; bind a fresh session."
            raise CompanionBridgeError(msg)
        if not -MAX_FRESHNESS_MS <= int(time.time() * 1000) - state.timestamp_ms <= MAX_FRESHNESS_MS:
            msg = "Server snapshot is not fresh."
            raise CompanionBridgeError(msg)
        if self.state is not None and state.generation != self.state.generation and not allow_new_generation:
            self.paused = True
            msg = "Server stop generation changed outside this session."
            raise CompanionBridgeError(msg)

    async def open(self) -> BridgeState:
        if self._closed or self.state is not None:
            msg = "Bridge is closed or already bound."
            raise CompanionBridgeError(msg)
        state = await self.observe()
        self.paused = False
        return state

    async def observe(self, *, allow_new_generation: bool = False) -> BridgeState:
        try:
            state = BridgeState.model_validate(await self._http("GET", "/v1/state"))
        except ValueError as exc:
            msg = "Server state failed strict schema validation."
            raise CompanionBridgeError(msg) from exc
        self._check_state(state, allow_new_generation=allow_new_generation)
        self.state = state
        return state

    def _record(self, raw: Any, *, action_id: str, run_id: str, generation: int, stop: bool = False) -> ActionRecord:
        try:
            record = ActionRecord.model_validate(raw)
        except ValueError as exc:
            msg = "Action receipt failed strict schema validation."
            raise CompanionBridgeError(msg) from exc
        state = self.state
        if (
            state is None
            or (record.boot_id, record.action_id, record.run_id) != (state.boot_id, action_id, run_id)
            or (record.generation < generation + 1 if stop else record.generation != generation)
        ):
            msg = "Action receipt identities or generation differ."
            raise CompanionBridgeError(msg)
        if isinstance(record.observation, BridgeState):
            if record.observation.generation != record.generation:
                msg = "Observation generation differs from its action receipt."
                raise CompanionBridgeError(msg)
            self._check_state(record.observation, allow_new_generation=stop)
        elif isinstance(record.observation, (CellObservation, WeatherObservation, ClockObservation)) and (
            (record.observation.boot_id, record.observation.actor_id, record.observation.generation)
            != (record.boot_id, self.binding.actor_id, record.generation)
            or not -MAX_FRESHNESS_MS <= int(time.time() * 1000) - record.observation.timestamp_ms <= MAX_FRESHNESS_MS
        ):
            msg = "Typed observation binding or freshness differs."
            raise CompanionBridgeError(msg)
        return record

    @staticmethod
    def _check_observation(record: ActionRecord, document: dict[str, Any]) -> None:
        """Require the operation's own correlated result, without cross-kind substitution."""
        observation = record.observation
        if document.get("kind") == "time":
            CompanionBridge._check_clock_observation(record, document["args"])
            return
        if isinstance(observation, ClockObservation):
            msg = "Clock observation cannot confirm another operation."
            raise CompanionBridgeError(msg)
        if document.get("kind") == "weather":
            CompanionBridge._check_weather_observation(record, document["args"])
            return
        if isinstance(observation, WeatherObservation):
            msg = "Weather observation cannot confirm another operation."
            raise CompanionBridgeError(msg)
        if document.get("kind") == "inspect":
            if record.status in {"applied", "refused"} and isinstance(observation, CellObservation):
                args = document["args"]
                if observation.available == (record.status == "applied") and observation.position == (
                    args["x"],
                    args["y"],
                    args["z"],
                ):
                    return
            if record.status != "applied" and observation is None:
                return
        elif not isinstance(observation, CellObservation):
            return
        msg = "Operation and observation variant or cell differ."
        raise CompanionBridgeError(msg)

    @staticmethod
    def _check_clock_observation(record: ActionRecord, args: dict[str, Any]) -> None:
        observation = record.observation
        if record.status == "applied" and isinstance(observation, ClockObservation):
            if (observation.scope, observation.requested_mode) == (args["scope"], args["mode"]):
                return
        elif record.status != "applied" and observation is None:
            return
        msg = "Clock receipt lacks the exact requested placement."
        raise CompanionBridgeError(msg)

    @staticmethod
    def _check_weather_observation(record: ActionRecord, args: dict[str, Any]) -> None:
        observation = record.observation
        if record.status == "applied" and isinstance(observation, WeatherObservation):
            if (observation.scope, observation.mode, observation.duration_ticks) == (
                args["scope"],
                args["mode"],
                args["duration_ticks"],
            ):
                return
        elif record.status != "applied" and observation is None:
            return
        msg = "Weather receipt lacks the exact requested programme."
        raise CompanionBridgeError(msg)

    async def _action(self, path: str, document: dict[str, Any], *, stop: bool = False) -> CompanionResult:
        action_id, run_id = str(document["action_id"]), str(document["run_id"])
        generation = self.state.generation if self.state is not None else 0
        try:
            async with asyncio.timeout(self.binding.timeout_s):
                record = self._record(
                    await self._http("POST", path, document, expected=202),
                    action_id=action_id,
                    run_id=run_id,
                    generation=generation,
                    stop=stop,
                )
                self._check_observation(record, document)
                while record.status == "accepted":
                    await asyncio.sleep(self.binding.poll_interval_s)
                    record = self._record(
                        await self._http("GET", f"/v1/actions/{action_id}"),
                        action_id=action_id,
                        run_id=run_id,
                        generation=generation,
                        stop=stop,
                    )
                    self._check_observation(record, document)
                return CompanionResult(
                    request_id=action_id,
                    kind=record.status,
                    detail=record.detail,
                    observation=record.observation if isinstance(record.observation, BridgeState) else None,
                    cell=record.observation if isinstance(record.observation, CellObservation) else None,
                    weather=record.observation if isinstance(record.observation, WeatherObservation) else None,
                    clock=record.observation if isinstance(record.observation, ClockObservation) else None,
                )
        except (CompanionBridgeError, TimeoutError) as exc:
            return CompanionResult(request_id=action_id, kind="unknown", detail=str(exc)[:300])

    async def invoke(  # noqa: PLR0911 - retain each distinct pre-handoff and receipt refusal
        self,
        request: CompanionRequest,
        run_id: str,
        *,
        expires_at_ms: int,
        authorize: Callable[[BridgeState], None] | None = None,
    ) -> CompanionResult:
        canonical_uuid(run_id)
        if (
            self._closed
            or self._all_fenced
            or run_id in self._fenced
            or self.paused
            or request.generation != self.epoch
        ):
            return CompanionResult(
                request_id=request.request_id, kind="refused", detail="Local stop or Run fence refused handoff."
            )
        try:
            state = await self.observe()
            if authorize is not None:
                authorize(state)
        except ValueError as exc:
            return CompanionResult(
                request_id=request.request_id,
                kind="refused",
                detail="Current session bounds or authority refused.",
                reason=exc.reason if isinstance(exc, CompanionRefusalError) else None,
            )
        except CompanionBridgeError as exc:
            return CompanionResult(request_id=request.request_id, kind="unknown", detail=str(exc)[:300])
        if (
            self._closed
            or self._all_fenced
            or run_id in self._fenced
            or self.paused
            or request.generation != self.epoch
        ):
            return CompanionResult(
                request_id=request.request_id, kind="refused", detail="Stop overtook observation; handoff refused."
            )
        remaining = expires_at_ms - int(time.time() * 1000)
        if not 0 < remaining <= MAX_LEASE_MS:
            return CompanionResult(
                request_id=request.request_id, kind="expired", detail="Action deadline is outside the finite lease."
            )
        args = request.action.model_dump(exclude={"kind"})
        self._issued[run_id] = self.epoch
        document = {
            "protocol": 1,
            "boot_id": state.boot_id,
            "generation": state.generation,
            "actor_id": state.actor_id,
            "run_id": run_id,
            "action_id": request.request_id,
            "expires_at_ms": expires_at_ms,
            "kind": request.action.kind,
            "args": args,
        }
        result = await self._action("/v1/actions", document)
        if request.action.kind == "state" and result.kind == "applied" and result.observation is None:
            return CompanionResult(
                request_id=request.request_id, kind="unknown", detail="Applied state receipt has no observation."
            )
        return result

    def begin_stop(self, *, run_id: str | None = None, action_id: str | None = None) -> asyncio.Task[CompanionResult]:
        """Fence immediately, before the caller can await cancellation or HTTP."""
        if self._stop_task is not None and not self._stop_task.done():
            return self._stop_task
        self.epoch += 1
        self.paused = True
        self._fenced.update(self._issued)
        self._stop_task = asyncio.create_task(
            self._stop(run_id or str(uuid4()), action_id or str(uuid4())), name="companion-priority-stop"
        )
        return self._stop_task

    async def _stop(self, run_id: str, action_id: str) -> CompanionResult:
        canonical_uuid(run_id)
        canonical_uuid(action_id)
        state = self.state
        if state is None:
            return CompanionResult(
                request_id=action_id, kind="unknown", detail="No bound server identity for priority stop."
            )
        result = await self._action(
            "/v1/stop",
            {
                "protocol": 1,
                "boot_id": state.boot_id,
                "actor_id": state.actor_id,
                "run_id": run_id,
                "action_id": action_id,
            },
            stop=True,
        )
        if result.kind == "applied":
            try:
                latest = await self.observe(allow_new_generation=True)
                if latest.generation <= state.generation:
                    msg = "Fresh state has not crossed the stop generation."
                    return CompanionResult(request_id=action_id, kind="unknown", detail=msg)
            except CompanionBridgeError as exc:
                return CompanionResult(request_id=action_id, kind="unknown", detail=str(exc)[:300])
            self.paused = self._all_fenced
        return result

    async def stop(self, run_id: str | None = None, action_id: str | None = None) -> CompanionResult:
        return await complete_under_cancellation(self.begin_stop(run_id=run_id, action_id=action_id))

    def fence(self, run_id: str, reason: str) -> None:
        del reason
        self._fenced.add(run_id)

    def fence_claim(self, run_id: str, enqueue_seq: int, reason: str) -> None:
        del enqueue_seq
        self.fence(run_id, reason)

    def fence_all(self, reason: str) -> None:
        del reason
        self._all_fenced = True
        self.paused = True
        self._fenced.update(self._issued)

    async def contain(self, run_id: str) -> None:
        if run_id in self._issued or (self._stop_task is not None and not self._stop_task.done()):
            result = (
                await complete_under_cancellation(self._stop_task)
                if self._stop_task is not None and self._issued.get(run_id, self.epoch) < self.epoch
                else await self.stop(run_id=run_id)
            )
            if result.kind != "applied":
                msg = "Priority server stop was not acknowledged; containment unknown."
                raise CompanionBridgeError(msg)

    async def contain_all(self) -> None:
        if self._issued:
            result = (
                await complete_under_cancellation(self._stop_task)
                if self._stop_task is not None and all(epoch < self.epoch for epoch in self._issued.values())
                else await self.stop()
            )
            if result.kind != "applied":
                msg = "Priority server stop was not acknowledged; containment unknown."
                raise CompanionBridgeError(msg)

    async def aclose(self) -> None:
        self.fence_all("bridge_closed")
        try:
            await self.contain_all()
        finally:
            self._closed = True
            await self._client.aclose()
