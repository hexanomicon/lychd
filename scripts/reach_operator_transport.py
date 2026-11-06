"""Bounded private-pipe routing and lifetime ownership of the paired operator children."""

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal, NoReturn, cast

from lychd.compositions.reach.operator_diagnostics import diagnostic_bytes, parse_diagnostic, write_diagnostic_line
from lychd.compositions.reach.operator_model_wire import OperatorModelRequest
from lychd.compositions.reach.operator_observation import ReachPatternObservation
from lychd.compositions.reach.operator_trace import ReachTraceEvent, error_code
from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES, ReachWorkerReady, ReachWorkerResult
from lychd.compositions.reach.research_wire import (
    OperatorResearchRequest,
    OperatorResearchResponse,
    ReachResearchProgress,
)
from lychd.interface.observation import OperationObservation

if __package__:
    from scripts.reach_model_broker import OperatorModelBroker
    from scripts.reach_research_broker import OperatorResearchBroker
    from scripts.reach_trace_capture import TraceCapture
else:
    from reach_model_broker import OperatorModelBroker
    from reach_research_broker import OperatorResearchBroker
    from reach_trace_capture import TraceCapture

WIRE_LIMIT = MAX_WIRE_BYTES
CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")


def _fail(code: str) -> NoReturn:
    raise ValueError(code)


def strict_object(raw: bytes) -> dict[str, Any]:
    """Do not let duplicate manifest keys or nonfinite JSON become operator authority."""

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                _fail("operator_duplicate_key")
            result[key] = value
        return result

    def constant(_value: str) -> Any:
        _fail("operator_json")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        _fail("operator_json")
    return cast("dict[str, Any]", value)


def safe_environment(engine: str) -> dict[str, str]:
    """Keep normal host engine discovery while excluding project and provider credentials."""
    permitted = (
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
        "XDG_RUNTIME_DIR",
        "XDG_CONFIG_HOME",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
        "DOCKER_BUILDKIT",
        "CONTAINER_HOST",
        "CONTAINERS_CONF",
        "REGISTRY_AUTH_FILE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    )
    result = {name: os.environ[name] for name in permitted if name in os.environ}
    result["LYCHD_TEST_ENGINE"] = engine
    result["LYCHD_TEST_PYTHON"] = "3.15.0"
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def capture_descriptors(value: dict[str, Any], raw: bytes, capture: TraceCapture | None) -> bool:
    """Consume only a bounded Core inspection frame without forwarding it to the edge."""
    if value.get("kind") != "reach_pattern_observation":
        return False
    with suppress(ValueError, TypeError):
        declaration = ReachPatternObservation.model_validate_json(raw)
        if capture is not None:
            capture.descriptors(declaration)
    return True


def capture_worker_frame(value: dict[str, Any], raw: bytes, capture: TraceCapture | None) -> None:
    """Record a native worker's typed control frame without changing forwarding."""
    if capture is None:
        return
    if value.get("kind") == "ready":
        capture.ready(ReachWorkerReady.model_validate_json(raw))
    elif value.get("kind") == "result":
        capture.result(ReachWorkerResult.model_validate_json(raw))


async def relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    requests_only: bool = False,
    capture: TraceCapture | None = None,
) -> None:
    """Forward bounded objects; the conversation edge may submit only typed worker requests."""
    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                _fail("operator_truncated_frame")
            return
        if len(raw) > WIRE_LIMIT:
            _fail("operator_frame_limit")
        value = strict_object(raw)
        if not requests_only and capture_descriptors(value, raw, capture):
            continue
        if requests_only:
            from lychd.compositions.reach.operator_wire import parse_request_line

            request = parse_request_line(raw)
            if capture is not None:
                capture.request(request)
        else:
            capture_worker_frame(value, raw, capture)
        writer.write(raw)
        await writer.drain()


def authorize_research_synthesis(payload: str, broker: OperatorResearchBroker) -> Callable[[], None] | None:
    """Bind the source envelope to one issued, currently authorized local consumption."""
    generation = strict_object(payload.encode())
    messages = generation.get("messages")
    prompt: dict[str, Any] = {}
    if isinstance(messages, list) and messages:
        last: Any = cast("list[Any]", messages)[-1]
        if isinstance(last, dict):
            content = cast("dict[str, Any]", last).get("content")
            if isinstance(content, str):
                with suppress(ValueError):
                    prompt = strict_object(content.encode())
    if prompt.get("research_phase") == "synthesis":
        return broker.authorize_consume(str(prompt.get("research_request_id", "")))
    if broker.material_pending:
        _fail("research_consume_binding")
    return None


async def model_relay(  # noqa: C901 - closed readiness/result/model/research wire branches
    reader: asyncio.StreamReader,
    edge_writer: asyncio.StreamWriter,
    core_writer: asyncio.StreamWriter,
    broker: OperatorModelBroker,
    research_broker: OperatorResearchBroker | None = None,
    capture: TraceCapture | None = None,
) -> None:
    """Keep model frames on the trusted host pipe and expose only public results."""

    async def progress(value: ReachResearchProgress) -> None:
        edge_writer.write(value.model_dump_json().encode() + b"\n")
        await edge_writer.drain()

    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                _fail("operator_truncated_frame")
            return
        if len(raw) > WIRE_LIMIT:
            _fail("operator_frame_limit")
        value = strict_object(raw)
        if capture_descriptors(value, raw, capture):
            continue
        if value.get("kind") in {"ready", "result"}:
            capture_worker_frame(value, raw, capture)
            if value.get("kind") == "result" and research_broker is not None:
                research_broker.settled(str(value.get("request_id", "")))
            edge_writer.write(raw)
            await edge_writer.drain()
        elif value.get("kind") == "model_request":
            request = OperatorModelRequest.model_validate_json(raw)
            response = await handle_model_request(broker, request, research_broker)
            await write_core_response(core_writer, response)
        elif value.get("kind") == "research_request" and research_broker is not None:
            research_request = OperatorResearchRequest.model_validate_json(raw)
            research_response = await handle_research_request(research_request, research_broker, progress, capture)
            await write_core_response(core_writer, research_response.model_dump_json())
        else:
            _fail("operator_core_frame")


async def handle_research_request(
    request: OperatorResearchRequest,
    broker: OperatorResearchBroker,
    progress: Callable[[ReachResearchProgress], Awaitable[None]],
    capture: TraceCapture | None,
) -> OperatorResearchResponse:
    """Observe the bounded acquisition handoff without retaining its material."""
    binding = request.correlation.model_dump(exclude_none=True) if request.correlation else {}
    started = time.monotonic()
    if capture is not None:
        capture.host.record("research_call", status="started", call_id=request.call_id, **binding)
    try:
        response = await broker.handle(request, progress)
    except (Exception, asyncio.CancelledError) as error:
        if capture is not None:
            capture.host.record(
                "research_call",
                status="cancelled" if isinstance(error, asyncio.CancelledError) else "error",
                code=error_code(error),
                call_id=request.call_id,
                duration_ms=min(86_400_000, int((time.monotonic() - started) * 1000)),
                **binding,
            )
        raise
    if capture is not None:
        capture.host.record(
            "research_call",
            status=response.status,
            call_id=request.call_id,
            duration_ms=min(86_400_000, int((time.monotonic() - started) * 1000)),
            **binding,
        )
        for source in response.sources:
            capture.host.record(
                "source_read",
                status=source.status,
                source_id=source.id,
                call_id=request.call_id,
                http_status=source.http_status,
                chars=len(source.text),
                truncated=source.truncated,
                code="fetch_protocol"
                if source.reason == "fetch_protocol"
                else "source_unavailable"
                if source.status != "ok"
                else None,
                **binding,
            )
    return response


async def handle_model_request(
    broker: OperatorModelBroker, request: OperatorModelRequest, research_broker: OperatorResearchBroker | None
) -> str:
    """Issue the local consumption guard only for the pending research synthesis."""
    authorize = None
    if research_broker is not None and request.operation == "generate":
        authorize = authorize_research_synthesis(request.payload_json, research_broker)
    response = (
        await broker.handle(request, authorize=authorize) if authorize is not None else await broker.handle(request)
    )
    return response.model_dump_json()


async def write_core_response(writer: asyncio.StreamWriter, response: str) -> None:
    """Keep every host response within the same bounded Core pipe dialect."""
    encoded = response.encode() + b"\n"
    if len(encoded) > WIRE_LIMIT:
        _fail("operator_frame_limit")
    writer.write(encoded)
    await writer.drain()


async def research_edge_relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    broker: OperatorResearchBroker,
    capture: TraceCapture | None = None,
) -> None:
    """Consume exact progress acknowledgements and forward only normalized requests."""
    from lychd.compositions.reach.operator_wire import parse_request_line
    from lychd.compositions.reach.research_wire import ReachResearchAcknowledgement

    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                _fail("operator_truncated_frame")
            return
        if len(raw) > WIRE_LIMIT:
            _fail("operator_frame_limit")
        value = strict_object(raw)
        if value.get("kind") == "progress_ack":
            broker.acknowledge(ReachResearchAcknowledgement.model_validate_json(raw))
        else:
            request = parse_request_line(raw)
            if capture is not None:
                capture.request(request)
            writer.write(raw)
            await writer.drain()


def capture_structured(raw: bytes, role: str, capture: TraceCapture) -> bool:
    """Validate one closed child record and pass its actual pipe role to custody checks."""
    try:
        value = strict_object(raw)
        if value.get("kind") == "operation_observation":
            capture.operation(OperationObservation.model_validate_json(raw), role)
            return True
        if value.get("kind") == "reach_trace":
            event = ReachTraceEvent.model_validate_json(raw)
            if event.producer == role:
                capture.child(event, role)
                return True
    except (ValueError, UnicodeError, RecursionError):
        return False
    return False


async def diagnostics(  # noqa: C901 - role custody, legacy diagnostics and closed readiness codes
    reader: asyncio.StreamReader,
    *,
    role: Literal["core", "edge"] = "edge",
    capture: TraceCapture | None = None,
) -> None:
    """Admit closed Core observations and fixed codes; reject foreign diagnostic bodies."""
    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.LimitOverrunError:
            write_diagnostic_line(b"reach_child_diagnostic_limit\n")
            _fail("operator_diagnostic_limit")
        except asyncio.IncompleteReadError:
            return
        if capture is not None and raw.startswith(b"{") and capture_structured(raw, role, capture):
            continue
        if role == "core" and raw.startswith(b"{"):
            try:
                record = parse_diagnostic(raw)
            except (ValueError, UnicodeError, RecursionError):
                pass
            else:
                write_diagnostic_line(diagnostic_bytes(record))
                continue
        try:
            code = raw.decode("ascii").strip()
        except UnicodeError:
            code = ""
        admitted = code if re.fullmatch(r"(?:reach_discord:)?[a-z][a-z0-9_]{0,63}", code) else "reach_child_diagnostic"
        if capture is not None:
            if role == "edge" and admitted in {
                "reach_discord:ready",
                "reach_discord:connecting",
                "reach_discord:disconnected",
            }:
                capture.host.record(
                    "gateway",
                    status="ok"
                    if admitted.endswith(":ready")
                    else "started"
                    if admitted.endswith(":connecting")
                    else "unavailable",
                    generation=capture.generation,
                )
            elif admitted == "reach_child_diagnostic" or admitted.endswith("_failed"):
                capture.host.record(
                    "child_diagnostic", status="error", code="protocol_error", generation=capture.generation
                )
        write_diagnostic_line((admitted + "\n").encode("ascii"))


async def retire(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 5)
        except TimeoutError:
            process.kill()
            await process.wait()


async def remove_owned(engine: str, cidfile: Path, *, read_identity: Callable[[Path, int], bytes]) -> None:
    """Remove only a validated exact identity emitted by this invocation's engine."""
    if not await asyncio.to_thread(cidfile.exists):
        return
    identity = (await asyncio.to_thread(read_identity, cidfile, 128)).decode("ascii").strip()
    if CONTAINER_ID.fullmatch(identity) is None:
        _fail("operator_container_identity")
    process = await asyncio.create_subprocess_exec(
        engine,
        "rm",
        "--force",
        identity,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        env=safe_environment(engine),
    )
    try:
        result = await asyncio.wait_for(process.wait(), 15)
    except TimeoutError:
        await retire(process)
        _fail("operator_cleanup_failed")
    if result:
        _fail("operator_cleanup_failed")


async def supervise(  # noqa: C901, PLR0912, PLR0915 - explicit two-child settlement and exact-ID cleanup
    engine: str,
    commands: tuple[list[str], list[str]],
    cidfiles: tuple[Path, Path],
    *,
    read_identity: Callable[[Path, int], bytes],
    broker: OperatorModelBroker | None = None,
    research_broker: OperatorResearchBroker | None = None,
    capture: TraceCapture | None = None,
) -> int:
    """First EOF, child failure or signal retires both processes and exact owned containers."""
    children: list[asyncio.subprocess.Process] = []
    control: dict[str, asyncio.Task[Any]] = {}
    drains: dict[str, asyncio.Task[None]] = {}
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stopped.set)
    status = 1
    heartbeat = asyncio.create_task(capture.heartbeat()) if capture is not None else None
    try:
        for arguments in commands:
            children.append(  # noqa: PERF401 - sequential spawn retains first child if the second fails
                await asyncio.create_subprocess_exec(
                    *arguments,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=WIRE_LIMIT,
                    env=safe_environment(engine),
                )
            )
        core, edge = children
        if (
            core.stdout is None
            or core.stdin is None
            or edge.stdout is None
            or edge.stdin is None
            or core.stderr is None
            or edge.stderr is None
        ):
            _fail("operator_child_pipe")
        control = {
            "core_output": asyncio.create_task(
                relay(core.stdout, edge.stdin, capture=capture)
                if broker is None
                else model_relay(core.stdout, edge.stdin, core.stdin, broker, research_broker, capture)
            ),
            "edge_output": asyncio.create_task(
                relay(edge.stdout, core.stdin, requests_only=True, capture=capture)
                if research_broker is None
                else research_edge_relay(edge.stdout, core.stdin, research_broker, capture)
            ),
            "core_exit": asyncio.create_task(core.wait()),
            "edge_exit": asyncio.create_task(edge.wait()),
            "signal": asyncio.create_task(stopped.wait()),
        }
        drains = {
            "core_diagnostics": asyncio.create_task(diagnostics(core.stderr, role="core", capture=capture)),
            "edge_diagnostics": asyncio.create_task(diagnostics(edge.stderr, role="edge", capture=capture)),
        }
        done, _ = await asyncio.wait((*control.values(), *drains.values()), return_when=asyncio.FIRST_COMPLETED)
        if stopped.is_set():
            status = 130
        else:
            # Every required reader failure is observed, even alongside child exit.
            for task in done:
                value = task.result()
                if type(value) is int:
                    status = value if value >= 0 else 128 - value
            if any(task in done for task in drains.values()) and not any(
                control[name] in done for name in ("core_exit", "edge_exit")
            ):
                write_diagnostic_line(b"reach_child_diagnostic_closed\n")
                status = 1
    finally:
        if heartbeat is not None:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
        for task in control.values():
            if not task.done():
                task.cancel()
        await asyncio.gather(*control.values(), return_exceptions=True)
        for child in children:
            await retire(child)
        try:
            async with asyncio.timeout(2):
                await asyncio.gather(*drains.values(), return_exceptions=True)
        except TimeoutError:
            for task in drains.values():
                task.cancel()
            await asyncio.gather(*drains.values(), return_exceptions=True)
        if capture is not None:
            capture.close(status)
        errors: list[OSError | ValueError] = []
        for cidfile in cidfiles:
            try:
                await remove_owned(engine, cidfile, read_identity=read_identity)
            except (OSError, ValueError) as error:
                errors.append(error)
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(signum)
        if errors:
            _fail("operator_cleanup_failed")
    return status
