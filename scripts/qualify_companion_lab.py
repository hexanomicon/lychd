"""Opt-in CPU/headless functional proof against an already prepared empty test server.

No server provisioning, restart, client rendering, speech or microphone work occurs.
Every game effect is bounded, and every run writes a private receipt, including failure.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from lychd.compositions.blockworld.companion import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    ActionRecord,
    BridgeState,
    CompanionPolicy,
    CompanionRequest,
    CompanionService,
    parse_text,
    strict_json,
)
from lychd.domain.speech_probe import MAX_PROFILE_BYTES
from lychd.lib.asyncio import complete_under_cancellation
from lychd.system.services.companion_bridge import BridgeBinding, CompanionBridge
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner, SessionResult
from scripts.voice_probe import CHECKOUT_ROOT, PrivateWorkspace

LEASE_SECONDS = 3.0
MAX_PROOF_SECONDS = 90
DIRECTION_EPSILON = 1e-9
MAX_NATIVE_BYTES = 2_097_152
CHUNK_SIZE = 16
GOTO_BLOCKS = 3.0
LOOK_BLOCKS = 4.0
POLL_SECONDS = 0.1
MIN_LOOK_DEGREES = 10.0
MIN_MOVE_BLOCKS = 0.2
MIN_RETIRE_SECONDS = 4.0
MAX_RETIRE_SECONDS = 10.0


class QualificationError(RuntimeError):
    """A bounded proof check failed; its message contains no remote material."""


def require(condition: bool, label: str) -> None:  # noqa: FBT001 - an assertion predicate, not a mode flag
    if not condition:
        raise QualificationError(label)


def position(state: BridgeState) -> tuple[float, float, float]:
    require(state.position is not None and state.mode != "unavailable", "actor_unavailable")
    return cast("tuple[float, float, float]", state.position)


def in_home(point: tuple[float, float, float], home: tuple[int, int]) -> bool:
    return (math.floor(point[0] / CHUNK_SIZE), math.floor(point[2] / CHUNK_SIZE)) == home


def look_target(state: BridgeState, policy: CompanionPolicy) -> tuple[float, float, float]:
    """Aim opposite the settled head yaw, avoiding an already-facing false negative."""
    x, y, z = position(state)
    require(state.yaw is not None, "head_gaze_unavailable")
    angle = math.radians(cast("float", state.yaw) + 180.0)
    dx, dz = -math.sin(angle), math.cos(angle)
    length = LOOK_BLOCKS
    for current, direction, low, high in ((x, dx, policy.min_x, policy.max_x), (z, dz, policy.min_z, policy.max_z)):
        if abs(direction) > DIRECTION_EPSILON:
            length = min(length, ((high - current) if direction > 0 else (current - low)) / abs(direction) - 0.1)
    require(length >= 1.0, "bounds_cannot_admit_opposite_gaze")
    target = (x + dx * length, min(policy.max_y, y + 1.0), z + dz * length)
    require(policy.contains(target), "look_target_exceeds_policy")
    return target


def goto_target(state: BridgeState, policy: CompanionPolicy, home: tuple[int, int]) -> tuple[float, float, float]:
    """Choose one short target away from the fixed home chunk's boundary."""
    x, y, z = position(state)
    origin_x, origin_z = home[0] * CHUNK_SIZE, home[1] * CHUNK_SIZE
    options = [
        (x + dx, y, z + dz) for dx, dz in ((GOTO_BLOCKS, 0), (-GOTO_BLOCKS, 0), (0, GOTO_BLOCKS), (0, -GOTO_BLOCKS))
    ]
    toward_center = (origin_x + CHUNK_SIZE / 2 - x, origin_z + CHUNK_SIZE / 2 - z)
    center_distance = math.hypot(*toward_center)
    if center_distance > DIRECTION_EPSILON:
        options.insert(
            0,
            (
                x + GOTO_BLOCKS * toward_center[0] / center_distance,
                y,
                z + GOTO_BLOCKS * toward_center[1] / center_distance,
            ),
        )
    candidates = [point for point in options if policy.contains(point) and in_home(point, home)]
    require(bool(candidates), "no_bounded_home_chunk_goto")
    return max(
        candidates,
        key=lambda point: min(
            point[0] - origin_x, origin_x + CHUNK_SIZE - point[0], point[2] - origin_z, origin_z + CHUNK_SIZE - point[2]
        ),
    )


class DropAcknowledgement(httpx.AsyncBaseTransport):
    """Dispatch once, then lose exactly one complete real action response locally."""

    def __init__(self) -> None:
        """Own one no-retry HTTP transport and finite proof counters."""
        self.inner = httpx.AsyncHTTPTransport(retries=0)
        self.drop = False
        self.action_sends = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        action = request.method == "POST" and request.url.path == "/v1/actions"
        self.action_sends += int(action)
        response = await self.inner.handle_async_request(request)
        if action and self.drop:
            self.drop = False
            await response.aclose()
            msg = "Qualification injected acknowledgement loss after dispatch."
            raise httpx.ReadError(msg, request=request)
        return response

    async def aclose(self) -> None:
        await self.inner.aclose()


async def exchange(
    client: httpx.AsyncClient, method: Literal["GET", "POST"], path: str, *, content: bytes | None = None
) -> tuple[int, bytes]:
    async with client.stream(method, path, content=content) as response:
        body = bytearray()
        async for chunk in response.aiter_bytes():
            require(len(body) + len(chunk) <= MAX_RESPONSE_BYTES, "raw_probe_response_too_large")
            body.extend(chunk)
        return response.status_code, bytes(body)


def action_record(raw: bytes, state: BridgeState, action_id: str, run_id: str) -> ActionRecord:
    record = ActionRecord.model_validate(strict_json(raw, limit=MAX_RESPONSE_BYTES))
    require(
        (record.boot_id, record.action_id, record.run_id, record.generation)
        == (state.boot_id, action_id, run_id, state.generation),
        "raw_action_identity_mismatch",
    )
    return record


async def settled_record(
    client: httpx.AsyncClient, raw: bytes, state: BridgeState, action_id: str, run_id: str
) -> ActionRecord:
    record = action_record(raw, state, action_id, run_id)
    async with asyncio.timeout(3):
        while record.status == "accepted":
            await asyncio.sleep(POLL_SECONDS)
            status, raw = await exchange(client, "GET", f"/v1/actions/{action_id}")
            require(status == HTTPStatus.OK, "raw_action_record_missing")
            record = action_record(raw, state, action_id, run_id)
    require(record.status == "applied", "raw_action_not_applied")
    return record


async def stop_replay_checks(client: httpx.AsyncClient, bridge: CompanionBridge) -> None:
    """Require historical stop replay to preserve freshly admitted work and retained identity."""
    state = await bridge.observe()
    stops: list[tuple[bytes, ActionRecord]] = []
    for _ in range(2):
        action_id, run_id = str(uuid4()), str(uuid4())
        content = json.dumps(
            {
                "protocol": 1,
                "boot_id": state.boot_id,
                "actor_id": state.actor_id,
                "run_id": run_id,
                "action_id": action_id,
            },
            separators=(",", ":"),
        ).encode()
        status, raw = await exchange(client, "POST", "/v1/stop", content=content)
        require(status == HTTPStatus.ACCEPTED, "stop_history_probe_not_accepted")
        expected = state.model_copy(update={"generation": state.generation + 1})
        stops.append((content, await settled_record(client, raw, expected, action_id, run_id)))
        state = await bridge.observe(allow_new_generation=True)
        require(not state.players and state.generation == expected.generation, "stop_history_probe_generation_changed")
    action_id, run_id = str(uuid4()), str(uuid4())
    document: dict[str, Any] = {
        "protocol": 1,
        "boot_id": state.boot_id,
        "generation": state.generation,
        "actor_id": state.actor_id,
        "run_id": run_id,
        "action_id": action_id,
        "expires_at_ms": int(time.time() * 1000) + 10000,
        "kind": "idle",
        "args": {},
    }
    status, raw = await exchange(client, "POST", "/v1/actions", content=json.dumps(document).encode())
    require(status == HTTPStatus.ACCEPTED, "post_stop_work_not_accepted")
    await settled_record(client, raw, state, action_id, run_id)
    content, historical = stops[0]
    status, raw = await exchange(client, "POST", "/v1/stop", content=content)
    require(
        status == HTTPStatus.ACCEPTED and ActionRecord.model_validate(strict_json(raw)) == historical,
        "historical_stop_replay_changed_receipt",
    )
    observed = await bridge.observe()
    require(
        observed.generation == state.generation and observed.active_action_id == action_id,
        "historical_stop_replay_fenced_fresh_work",
    )
    changed = strict_json(content)
    changed["run_id"] = str(uuid4())
    status, _ = await exchange(client, "POST", "/v1/stop", content=json.dumps(changed).encode())
    require(status == HTTPStatus.CONFLICT, "historical_stop_changed_content_not_refused")
    document["action_id"] = historical.action_id
    status, _ = await exchange(client, "POST", "/v1/actions", content=json.dumps(document).encode())
    require(status == HTTPStatus.CONFLICT, "historical_stop_action_collision_not_refused")


async def protocol_checks(binding: BridgeBinding, bridge: CompanionBridge) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {binding.token}",
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
    }
    async with httpx.AsyncClient(
        base_url=binding.endpoint.rstrip("/"),
        trust_env=False,
        follow_redirects=False,
        timeout=3,
        transport=httpx.AsyncHTTPTransport(retries=0),
    ) as client:
        status, _ = await exchange(client, "GET", "/v1/state")
        require(status == HTTPStatus.UNAUTHORIZED, "unauthenticated_state_not_refused")
        client.headers.update(headers)
        status, _ = await exchange(client, "POST", "/v1/actions", content=b'{"protocol":1,"protocol":1}')
        require(status == HTTPStatus.BAD_REQUEST, "duplicate_json_key_not_refused")
        status, _ = await exchange(client, "POST", "/v1/actions", content=b"x" * (MAX_REQUEST_BYTES + 1))
        require(status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "oversized_body_not_refused")
        state = await bridge.observe()
        require(not state.players, "server_no_longer_empty")
        action_id, run_id = str(uuid4()), str(uuid4())
        document = {
            "protocol": 1,
            "boot_id": state.boot_id,
            "generation": state.generation,
            "actor_id": state.actor_id,
            "run_id": run_id,
            "action_id": action_id,
            "expires_at_ms": int(time.time() * 1000) + 10000,
            "kind": "say",
            "args": {"text": "companion qualification duplicate probe"},
        }
        content = json.dumps(document, separators=(",", ":")).encode()
        status, raw = await exchange(client, "POST", "/v1/actions", content=content)
        require(status == HTTPStatus.ACCEPTED, "raw_action_not_accepted")
        retained = await settled_record(client, raw, state, action_id, run_id)
        status, raw = await exchange(client, "POST", "/v1/actions", content=content)
        require(
            status == HTTPStatus.ACCEPTED and action_record(raw, state, action_id, run_id) == retained,
            "identical_duplicate_changed_receipt",
        )
        document["args"] = {"text": "changed duplicate content"}
        status, _ = await exchange(client, "POST", "/v1/actions", content=json.dumps(document).encode())
        require(status == HTTPStatus.CONFLICT, "changed_duplicate_not_conflicted")
        await stop_replay_checks(client, bridge)
    return {
        "auth_duplicate_keys_oversize_identity_dedupe_conflict": True,
        "historical_stop_replay_and_collision": True,
        "action_id": action_id,
        "run_id": run_id,
    }


async def incomplete_request(binding: BridgeBinding) -> dict[str, Any]:
    endpoint = urlsplit(binding.endpoint)
    reader, writer = await asyncio.open_connection(endpoint.hostname, endpoint.port)
    started = time.monotonic()
    try:
        request = f"POST /v1/actions HTTP/1.1\r\nHost: {endpoint.hostname}:{endpoint.port}\r\nAuthorization: Bearer {binding.token}\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\nx"
        async with asyncio.timeout(MAX_RETIRE_SECONDS):
            writer.write(request.encode())
            await writer.drain()
            response = await reader.read(MAX_RESPONSE_BYTES + 1)
            require(len(response) <= MAX_RESPONSE_BYTES, "incomplete_request_response_too_large")
            require(await reader.read(1) == b"", "incomplete_request_connection_not_retired")
        elapsed = time.monotonic() - started
        require(MIN_RETIRE_SECONDS <= elapsed < MAX_RETIRE_SECONDS, "incomplete_request_retirement_outside_window")
        return {"retired_seconds": elapsed, "response_bytes": len(response)}
    finally:
        writer.close()
        with suppress(OSError):
            await writer.wait_closed()


def source_references() -> list[dict[str, str]]:
    paths = [
        Path(__file__),
        *(
            CHECKOUT_ROOT / name
            for name in (
                "scripts/voice_probe.py",
                "scripts/companion_lab.py",
                "src/lychd/compositions/blockworld/companion.py",
                "src/lychd/compositions/blockworld/companion_feedback.py",
                "src/lychd/compositions/blockworld/local_runtime.py",
                "src/lychd/system/services/companion_bridge.py",
                "src/lychd/system/services/companion_session.py",
                "clients/minecraft/src/main/java/org/lychd/companion/WolfController.java",
                "clients/minecraft/src/main/java/org/lychd/companion/protocol/BridgeHttpServer.java",
                "clients/minecraft/src/main/java/org/lychd/companion/protocol/ActionInbox.java",
                "clients/minecraft/src/main/java/org/lychd/companion/protocol/StrictJson.java",
            )
        ),
    ]
    return [{"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths]


def matching_report(event: dict[str, Any], result: Any) -> bool:
    if event.get("kind") != "log":
        return False
    try:
        return strict_json(event["data"], limit=MAX_NATIVE_BYTES) == result
    except (ValueError, UnicodeError, TypeError):
        return False


async def functional_checks(  # noqa: PLR0915 - one explicit finite end-to-end proof sequence
    session: CompanionSession,
    transport: DropAcknowledgement,
    policy: CompanionPolicy,
    home: tuple[int, int],
    summary: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    bridge = session.bridge
    checks: dict[str, Any] = summary["checks"]

    async def observe() -> BridgeState:
        state = await bridge.observe()
        require(not state.players, "server_no_longer_empty")
        require(in_home(position(state), home), "actor_left_declared_home_chunk")
        return state

    async def issue(text: str) -> SessionResult:
        await observe()
        generation = session.capture_generation()
        request = CompanionRequest(
            request_id=str(uuid4()), action=parse_text(text), generation=generation, transcript=text
        )
        result = await session.enqueue(request, captured_generation=generation)
        require(result.kind == "applied", "native_action_not_applied")
        return result

    require((await session.stop()).kind == "applied", "initial_stop_not_applied")
    await issue("idle")
    await asyncio.sleep(LEASE_SECONDS + 0.4)
    settled = await observe()
    require(settled.mode == "idle" and settled.active_action_id is None, "initial_idle_not_settled")
    summary["settled"] = settled.model_dump(mode="json")
    await issue("stav")
    await issue("povedz companion qualification")
    checks["native_state_and_chat"] = True
    target = look_target(settled, policy)
    await issue("pozri " + " ".join(map(str, target)))
    await asyncio.sleep(0.8)
    looked = await observe()
    require(looked.yaw is not None and settled.yaw is not None, "head_gaze_unavailable")
    degrees = abs((cast("float", looked.yaw) - cast("float", settled.yaw) + 180) % 360 - 180)
    require(degrees > MIN_LOOK_DEGREES, "actual_head_gaze_did_not_change")
    checks["look"] = {
        "before": settled.model_dump(mode="json"),
        "after": looked.model_dump(mode="json"),
        "target": target,
        "observed_degrees": degrees,
    }
    before = await observe()
    target = goto_target(before, policy, home)
    await issue("choď " + " ".join(map(str, target)))
    samples: list[BridgeState] = []
    for _ in range(14):
        await asyncio.sleep(POLL_SECONDS)
        samples.append(await observe())
    distance = max(math.dist(position(before), position(sample)) for sample in samples)
    require(distance > MIN_MOVE_BLOCKS, "actual_goto_displacement_not_observed")
    checks["goto"] = {
        "target": target,
        "before": before.model_dump(mode="json"),
        "samples": [sample.model_dump(mode="json") for sample in samples],
        "max_observed_displacement": distance,
        "destination_completion_claimed": False,
    }
    captured = session.capture_generation()
    queued_requests = [
        CompanionRequest(request_id=str(uuid4()), action=parse_text(f"say queued {index}"), generation=captured)
        for index in range(3)
    ]
    pending = [session.enqueue(request) for request in queued_requests]
    stopping = session.stop()
    require(session.capture_generation() == captured + 1, "stop_did_not_fence_synchronously")
    require((await stopping).kind == "applied", "priority_stop_not_applied")
    require(
        all(result.kind == "cancelled" for result in await asyncio.gather(*pending)), "queued_commands_survived_stop"
    )
    stopped = await observe()
    await asyncio.sleep(0.3)
    still = await observe()
    require(
        all(state.mode == "stopped" and state.active_action_id is None for state in (stopped, still)),
        "stopped_controller_resumed",
    )
    checks["priority_stop"] = {
        "queued_cancelled": len(pending),
        "post_stop_physics_displacement": math.dist(position(stopped), position(still)),
    }
    await issue("state")
    checks["fresh_command_after_stop"] = True
    await issue("idle")
    used = session.runner.service.used
    await asyncio.sleep(LEASE_SECONDS + 0.4)
    idle = await observe()
    require(
        idle.mode == "idle" and idle.active_action_id is None and session.runner.service.used == used,
        "idle_expiry_or_native_budget_changed",
    )
    checks["finite_idle_without_extra_runs"] = True
    transport.drop = True
    sent = transport.action_sends
    request = CompanionRequest(
        request_id=str(uuid4()), action=parse_text("state"), generation=session.capture_generation()
    )
    unknown = await session.enqueue(request)
    require(
        unknown.kind == "unknown" and transport.action_sends == sent + 1, "lost_ack_was_reposted_or_false_completion"
    )
    require(
        (await session.enqueue(request)).kind == "unknown" and transport.action_sends == sent + 1,
        "identical_unknown_request_reposted",
    )
    require((await session.stop()).kind == "applied", "lost_ack_stop_not_applied")
    checks["lost_real_ack_unknown_without_repost"] = True
    require(bool(records), "native_evidence_missing")
    queued_ids = {request.request_id for request in queued_requests}
    queued_records = [record for record in records if record.get("request_id") in queued_ids]
    require(
        len(queued_records) == len(queued_ids)
        and {record["request_id"] for record in queued_records} == queued_ids
        and all(record["kind"] == "cancelled" and record.get("run_id") is None for record in queued_records),
        "queued_cancellation_identity_evidence_missing",
    )
    checks["pre_run_cancellation_records"] = len(queued_records)
    for record in records:
        require(bool(record.get("request_id")), "operator_request_identity_missing")
        if record.get("run_id") is None:
            require(
                record["kind"] in {"cancelled", "expired"} and not record.get("events"),
                "pre_run_result_invented_native_events",
            )
            continue
        require(
            all(event["run_id"] == record["run_id"] for event in record.get("events", [])),
            "native_event_run_identity_mismatch",
        )
        if record["kind"] == "applied":
            require(
                [
                    event["data"]
                    for event in record.get("events", [])
                    if event["kind"] == "node" and event.get("meta", {}).get("phase") == "entered"
                ]
                == ["validate", "execute", "report"],
                "native_station_evidence_mismatch",
            )
            require(
                any(matching_report(event, record["result"]) for event in record.get("events", [])),
                "native_report_result_mismatch",
            )
    checks["native_graph_stations_correlated"] = sum(record.get("run_id") is not None for record in records)
    checks["protocol"] = await protocol_checks(bridge.binding, bridge)
    checks["incomplete_request"] = await incomplete_request(bridge.binding)
    summary["final"] = (await observe()).model_dump(mode="json")


async def run(args: argparse.Namespace) -> tuple[bool, Path]:  # noqa: PLR0915 - retain primary and cleanup evidence in one receipt owner
    files = PrivateWorkspace(args.workspace, tuple(args.checkout_root))
    receipt = files.root / f"{uuid4()}-companion-qualification.json"
    summary: dict[str, Any] = {
        "profile": "experimental_companion_cpu_headless",
        "success": False,
        "checks": {},
        "started_at": datetime.now(UTC).isoformat(),
        "gpu_client_started": False,
        "speech_attempted": False,
        "provisioning_or_restart_attempted": False,
        "deployed_artifact_verified": False,
        "home_chunk": args.home_chunk,
        "bounds": args.bounds,
        "native_records": [],
    }
    bridge: CompanionBridge | None = None
    session: CompanionSession | None = None
    stage = "private_inputs"
    try:
        content = files.read(args.bridge_profile, MAX_PROFILE_BYTES)
        document = strict_json(content)
        require(
            type(document) is dict
            and set(document) == {"endpoint", "token", "actor_id"}
            and all(type(value) is str for value in document.values()),
            "bridge_profile_fields_invalid",
        )
        binding_document = cast("dict[str, str]", document)
        binding = BridgeBinding(
            endpoint=binding_document["endpoint"],
            token=binding_document["token"],
            actor_id=binding_document["actor_id"],
        )
        summary["bridge_profile"] = {
            "path": str(args.bridge_profile),
            "sha256": hashlib.sha256(content).hexdigest(),
            "endpoint": binding.endpoint,
            "actor_id": binding.actor_id,
        }
        summary["sources"] = source_references()
        low, high = args.bounds[:3], args.bounds[3:]
        policy = CompanionPolicy(
            session_id=str(uuid4()),
            principal="companion-qualification",
            expires_at=datetime.now(UTC) + timedelta(seconds=MAX_PROOF_SECONDS),
            min_x=low[0],
            min_y=low[1],
            min_z=low[2],
            max_x=high[0],
            max_y=high[1],
            max_z=high[2],
            lease_s=LEASE_SECONDS,
            max_actions=24,
        )
        summary["policy"] = policy.model_dump(mode="json")
        transport = DropAcknowledgement()
        bridge = CompanionBridge(binding, transport=transport)
        stage = "empty_prepared_server"
        initial = await bridge.open()
        summary["initial"] = initial.model_dump(mode="json")
        require(not initial.players, "prepared_server_has_online_players")
        require(
            in_home(position(initial), tuple(args.home_chunk)) and policy.contains(position(initial)),
            "actor_outside_home_chunk_or_policy",
        )
        records: list[dict[str, Any]] = []

        async def record(document: dict[str, Any]) -> None:
            raw = json.dumps(document, ensure_ascii=False, allow_nan=False).encode()
            require(len(raw) <= MAX_NATIVE_BYTES, "native_evidence_exceeds_bound")
            path = files.root / f"{uuid4()}-qualification-native.json"
            files.write_new(path, raw)
            records.append(document)
            summary["native_records"].append(
                {
                    "path": str(path),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "run_id": document.get("run_id"),
                    "kind": document.get("kind"),
                }
            )

        session = CompanionSession(
            LocalCompanionRunner(CompanionService(policy, bridge), bridge), bridge, record=record
        )
        await session.open()
        stage = "functional_checks"
        async with asyncio.timeout(MAX_PROOF_SECONDS):
            await functional_checks(session, transport, policy, tuple(args.home_chunk), summary, records)
        require(source_references() == summary["sources"], "qualification_sources_changed_during_run")
        require(files.read(args.bridge_profile, MAX_PROFILE_BYTES) == content, "bridge_profile_changed_during_run")
        summary["success"] = True
    except BaseException as exc:  # noqa: BLE001 - preserve private failure evidence, including cancellation
        summary["failure"] = {
            "stage": stage,
            "type": type(exc).__name__,
            "check": str(exc) if isinstance(exc, QualificationError) else "details_withheld",
        }
    finally:
        try:
            if session is not None:
                await complete_under_cancellation(session.aclose())
            elif bridge is not None:
                await complete_under_cancellation(bridge.aclose())
            summary["cleanup"] = "settled"
        except BaseException as exc:  # noqa: BLE001 - a cleanup failure must not erase the primary receipt
            summary["success"] = False
            summary["cleanup"] = {"type": type(exc).__name__, "disposition": "unknown"}
        summary["finished_at"] = datetime.now(UTC).isoformat()
        files.write_new(receipt, json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2).encode())
    return bool(summary["success"]), receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--run",
        action="store_true",
        required=True,
        help="Explicitly run effects against the prepared empty test server.",
    )
    result.add_argument("--workspace", type=Path, required=True)
    result.add_argument("--checkout-root", type=Path, action="append", required=True)
    result.add_argument("--bridge-profile", type=Path, required=True)
    result.add_argument("--home-chunk", type=int, nargs=2, required=True, metavar=("CHUNK_X", "CHUNK_Z"))
    result.add_argument(
        "--bounds", type=float, nargs=6, required=True, metavar=("MIN_X", "MIN_Y", "MIN_Z", "MAX_X", "MAX_Y", "MAX_Z")
    )
    return result


def main() -> int:
    try:
        success, receipt = asyncio.run(run(parser().parse_args()))
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - print no private profile, token, remote response or traceback
        sys.stderr.write(
            "Qualification failed before a private receipt could be retained. Inspect the explicit private workspace.\n"
        )
        return 1
    sys.stdout.write(json.dumps({"success": success, "receipt": str(receipt)}) + "\n")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
