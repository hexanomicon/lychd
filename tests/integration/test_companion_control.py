"""Real local control sockets through console capture and actual native Graph ownership."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from lychd.compositions.blockworld.companion import CompanionService
from lychd.system.services.companion_control import CompanionControl, CompanionControlError, ControlProfile
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner
from tests.integration.test_companion import FakeBridge, policy
from tests.unit.cli.test_companion_lab import ConsolePipe, speech, wav
from tests.unit.cli.test_companion_lab import console_pipe as console_pipe  # noqa: PLC0414 - shared actual pipe fixture
from tests.unit.cli.test_companion_lab import files as files  # noqa: PLC0414 - shared private fixture


@asynccontextmanager
async def connected(
    files: PrivateWorkspace,
    port: int,
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response]
    | Callable[[httpx.Request], Coroutine[None, None, httpx.Response]],
    *,
    hold_seconds: int | None = None,
) -> AsyncGenerator[tuple[CompanionControl, companion_lab.CompanionConsole, FakeBridge, httpx.AsyncClient, list[int]]]:
    fake = FakeBridge()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    console = companion_lab.CompanionConsole(files, session, speech=speech(httpx.MockTransport(handler)), language="en")
    session.record = console.record
    captures: list[int] = []

    async def capture(*, seconds: int) -> bytes:
        captures.append(seconds)
        return wav()

    monkeypatch.setattr(companion_lab, "capture_utterance", capture)
    profile = ControlProfile(1, f"http://127.0.0.1:{port}", "b" * 64, "127.0.0.1:25572", fake.player, 3)
    control = CompanionControl(
        profile,
        expires_at_ms=int((time.time() + 60) * 1000),
        context=console.control_context,
        record=console.record_gesture,
        stop=console.begin_stop,
        hold_seconds=hold_seconds,
    )
    console.control = control
    await session.open()
    try:
        await control.open()
        async with httpx.AsyncClient(
            base_url=profile.endpoint,
            headers={"Authorization": "Bearer " + profile.token, "Accept-Encoding": "identity"},
            trust_env=False,
            follow_redirects=False,
            timeout=3,
        ) as client:
            yield control, console, fake, client, captures
    finally:
        await control.aclose()
        await console.stop()
        await session.aclose()


def gesture(control: CompanionControl, operation: str = "record") -> tuple[str, bytes]:
    state = control.state()
    created = int(time.time() * 1000)
    identity = str(uuid4())
    body = {
        "protocol": 1,
        "session_id": state["session_id"],
        "request_id": identity,
        "created_at_ms": created,
        "admit_before_ms": created + 3000,
    }
    if operation == "record":
        body.update(
            context_id=state["context_id"],
            generation=state["generation"],
            expires_at_ms=created + state["instruction_timeout_ms"],
        )
    return identity, json.dumps(body, separators=(",", ":")).encode()


async def known(client: httpx.AsyncClient, identity: str) -> dict[str, Any]:
    for _ in range(30):
        response = await client.get("/v1/operations/" + identity)
        assert response.status_code == 200
        operation = response.json()
        if operation["status"] != "pending":
            return operation
        await asyncio.sleep(0.01)
    pytest.fail("Owned operation did not become observable")


@pytest.mark.asyncio
async def test_real_control_turn_preserves_original_identity_deadline_native_evidence_and_no_replay(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": "state"})
    ) as (control, console, fake, client, captures):
        before = fake.reads, len(fake.requests), len(console.session.run_ids)
        initial = await client.get("/v1/state")
        assert initial.status_code == 200
        assert before == (fake.reads, len(fake.requests), len(console.session.run_ids))
        identity, raw = gesture(control)
        response = await client.post("/v1/record", content=raw, headers={"Content-Type": "application/json"})
        assert response.status_code == 202
        assert response.json()["request_id"] == identity
        await asyncio.wait_for(fake.action_started.wait(), 2)
        await asyncio.gather(*console.replies)
        outcome = await known(client, identity)
        assert outcome["game_kind"] == "applied"
        assert outcome["feedback"]["language"] == "en"
        assert outcome["native_evidence_status"] == "recorded"
        assert captures == [3]
        (native_file,) = files.root.glob("*-native.json")
        native = json.loads(native_file.read_bytes())
        voice = json.loads((files.root / f"{identity}-voice.json").read_bytes())
        assert native["request_id"] == voice["request_id"] == identity
        assert native["run_id"] == fake.requests[0]["run_id"]
        assert native["events"]
        assert voice["expires_at_ms"] == json.loads(raw)["expires_at_ms"]
        assert "transcript" not in outcome
        monkeypatch.setattr(control, "clock", lambda: time.time() + 10)
        duplicate = await client.post("/v1/record", content=raw, headers={"Content-Type": "application/json"})
        assert duplicate.status_code == 200
        changed = json.loads(raw)
        changed["created_at_ms"] += 1
        conflict = await client.post("/v1/record", json=changed)
        assert conflict.status_code == 409
        assert captures == [3]
        assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_first_control_bytes_during_full_stop_cannot_capture_after_retirement(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": "state"})
    ) as (control, console, fake, _client, captures):
        entered, release, observed = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_settle = console._settle_stop  # pyright: ignore[reportPrivateUsage]

        async def held(*args: Any, **kwargs: Any) -> Any:
            result = await original_settle(*args, **kwargs)
            entered.set()
            await release.wait()
            return result

        monkeypatch.setattr(console, "_settle_stop", held)
        stopping = console.begin_stop()
        reader: asyncio.StreamReader | None = None
        writer: asyncio.StreamWriter | None = None
        try:
            await asyncio.wait_for(entered.wait(), 2)
            assert console.session.bridge.paused is False
            assert console.control_context().stopping
            identity, raw = gesture(control)
            original_context = control.context

            def capture_context() -> Any:
                context = original_context()
                observed.set()
                return context

            monkeypatch.setattr(control, "context", capture_context)
            reader, writer = await asyncio.open_connection("127.0.0.1", unused_tcp_port)
            writer.write(b"P")
            await writer.drain()
            await asyncio.wait_for(observed.wait(), 2)
            release.set()
            await asyncio.wait_for(stopping, 2)
            assert console.control_context().can_record
            header = (
                f"OST /v1/record HTTP/1.1\r\nHost: 127.0.0.1:{unused_tcp_port}\r\n"
                f"Authorization: Bearer {'b' * 64}\r\nContent-Type: application/json\r\nContent-Length: {len(raw)}\r\n\r\n"
            ).encode()
            writer.write(header + raw)
            await writer.drain()
            response = await asyncio.wait_for(reader.read(), 2)
            assert response.startswith(b"HTTP/1.1 409 ")
            operation = control.operation(identity)
            assert operation is not None
            assert operation["status"] == "refused"
            assert not captures
            assert not fake.requests
            assert not console.session.run_ids
        finally:
            release.set()
            await stopping
            if writer is not None:
                writer.close()
                await writer.wait_closed()


@pytest.mark.asyncio
async def test_priority_control_stop_joins_held_transcription_and_duplicate_does_not_refence(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = asyncio.Event()

    async def transcription(_request: httpx.Request) -> httpx.Response:
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError

    async with connected(files, unused_tcp_port, monkeypatch, transcription) as (
        control,
        console,
        fake,
        client,
        captures,
    ):
        record_id, raw = gesture(control)
        assert (
            await client.post("/v1/record", content=raw, headers={"Content-Type": "application/json"})
        ).status_code == 202
        await asyncio.wait_for(entered.wait(), 2)
        assert control.state()["voice"]["phase"] == "transcribing"
        stop_id, stop = gesture(control, "stop")
        generation = console.session.capture_generation()
        response = await client.post("/v1/stop", content=stop, headers={"Content-Type": "application/json"})
        assert response.status_code == 202
        assert console.session.capture_generation() > generation
        stopped = await known(client, stop_id)
        assert stopped["game_kind"] == "applied"
        assert stopped["server_stop_id"] != stop_id
        assert console.voice_task is not None
        assert console.voice_task.done()
        operation = control.operation(record_id)
        assert operation is not None
        assert operation["status"] == "unknown"
        before = len(fake.stop_ids)
        duplicate = await client.post("/v1/stop", content=stop, headers={"Content-Type": "application/json"})
        assert duplicate.status_code == 200
        assert len(fake.stop_ids) == before
        assert captures == [3]
        assert not fake.requests
        assert control.state()["can_record"]


@pytest.mark.asyncio
async def test_control_close_retires_partial_http_without_admitting_capture(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": "state"})
    ) as (control, _console, fake, _client, captures):
        observed = asyncio.Event()
        original = control.context

        def context() -> Any:
            observed.set()
            return original()

        monkeypatch.setattr(control, "context", context)
        reader, writer = await asyncio.open_connection("127.0.0.1", unused_tcp_port)
        try:
            writer.write(b"P")
            await writer.drain()
            await asyncio.wait_for(observed.wait(), 2)
            await asyncio.wait_for(control.aclose(), 2)
            assert await asyncio.wait_for(reader.read(), 2) == b""
            assert not control.state()["can_record"]
            assert not captures
            assert not fake.requests
        finally:
            writer.close()
            await writer.wait_closed()


@pytest.mark.parametrize(
    ("violation", "expected"),
    [
        ("missing_auth", 401),
        ("wrong_auth", 401),
        ("duplicate_auth", 400),
        ("origin", 400),
        ("wrong_host", 400),
        ("transfer", 400),
        ("duplicate_length", 400),
        ("duplicate_json", 400),
        ("query", 400),
        ("oversize_header", 400),
        ("oversize_body", 400),
    ],
)
@pytest.mark.asyncio
async def test_control_http_refuses_foreign_or_ambiguous_ingress_before_capture(
    files: PrivateWorkspace,
    unused_tcp_port: int,
    monkeypatch: pytest.MonkeyPatch,
    violation: str,
    expected: int,
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": "state"})
    ) as (control, console, fake, _client, captures):
        _identity, raw = gesture(control)
        path = "/v1/record?x=1" if violation == "query" else "/v1/record"
        if violation == "duplicate_json":
            raw = raw[:-1] + b',"protocol":1}'
        auth = f"Authorization: Bearer {'b' * 64}\r\n"
        if violation == "missing_auth":
            auth = ""
        elif violation == "wrong_auth":
            auth = f"Authorization: Bearer {'c' * 64}\r\n"
        elif violation == "duplicate_auth":
            auth += auth
        extra = {
            "origin": "Origin: http://127.0.0.1\r\n",
            "transfer": "Transfer-Encoding: chunked\r\n",
            "duplicate_length": f"Content-Length: {len(raw)}\r\n",
            "oversize_header": f"X-Padding: {'x' * 4100}\r\n",
        }.get(violation, "")
        host = "localhost" if violation == "wrong_host" else "127.0.0.1"
        length = 2049 if violation == "oversize_body" else len(raw)
        request = (
            f"POST {path} HTTP/1.1\r\nHost: {host}:{unused_tcp_port}\r\n"
            f"{auth}{extra}Content-Type: application/json\r\nContent-Length: {length}\r\n\r\n"
        ).encode() + raw
        reader, writer = await asyncio.open_connection("127.0.0.1", unused_tcp_port)
        try:
            writer.write(request)
            await writer.drain()
            response = await asyncio.wait_for(reader.read(), 3)
            assert response.startswith(f"HTTP/1.1 {expected} ".encode())
            assert json.loads(response.split(b"\r\n\r\n", 1)[1]) == {"protocol": 1, "status": "refused"}
            assert not captures
            assert not fake.requests
            assert not console.session.run_ids
        finally:
            writer.close()
            await writer.wait_closed()


@pytest.mark.asyncio
async def test_lost_control_acknowledgement_queries_original_operation_without_repeating_capture(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": "state"})
    ) as (control, console, fake, client, captures):
        identity, raw = gesture(control)
        _reader, writer = await asyncio.open_connection("127.0.0.1", unused_tcp_port)
        try:
            writer.write(
                (
                    f"POST /v1/record HTTP/1.1\r\nHost: 127.0.0.1:{unused_tcp_port}\r\n"
                    f"Authorization: Bearer {'b' * 64}\r\nContent-Type: application/json\r\n"
                    f"Content-Length: {len(raw)}\r\n\r\n"
                ).encode()
                + raw
            )
            await writer.drain()
            await asyncio.wait_for(fake.action_started.wait(), 2)
        finally:
            # Deliberately discard the mutation response. Only query the original ID next.
            writer.close()
            await writer.wait_closed()
        await asyncio.gather(*console.replies)
        outcome = await known(client, identity)
        assert outcome["request_id"] == identity
        assert outcome["game_kind"] == "applied"
        assert captures == [3]
        assert len(fake.requests) == 1
        assert len(console.session.run_ids) == 1


@pytest.mark.asyncio
async def test_record_instruction_must_fit_session_before_waiting_for_capture_lock(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": "state"})
    ) as (control, console, fake, client, captures):
        identity, raw = gesture(control)
        document = json.loads(raw)
        # The original instruction is fresh, but outlives its capture authority.
        control.expires_at_ms = document["expires_at_ms"] - 1
        now_ms = document["created_at_ms"]
        monkeypatch.setattr(control, "clock", lambda: now_ms / 1000)
        lock = console._capture_lock  # pyright: ignore[reportPrivateUsage]
        await lock.acquire()
        try:
            assert not control.state()["can_record"]
            response = await client.post("/v1/record", content=raw, headers={"Content-Type": "application/json"})
            assert response.status_code == 408
            assert control.operation(identity) is None
            assert console.voice_task is None
            now_ms = control.expires_at_ms + 1
        finally:
            stopping = console.begin_stop()
            lock.release()
            await asyncio.wait_for(stopping, 2)
        assert not captures
        assert not fake.requests
        assert not console.session.run_ids
        assert not list(files.root.glob("*-voice.json"))


@pytest.mark.parametrize("exit_mode", ["quit", "eof"])
@pytest.mark.asyncio
async def test_final_console_stop_seals_admission_before_its_waiter_resumes(  # noqa: PLR0915 - one deterministic shutdown interleaving
    files: PrivateWorkspace,
    unused_tcp_port: int,
    monkeypatch: pytest.MonkeyPatch,
    console_pipe: ConsolePipe,
    exit_mode: str,
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": "state"})
    ) as (control, console, fake, client, captures):
        settled, release, attempted, returned, release_capture = (asyncio.Event() for _ in range(5))
        observations: dict[str, Any] = {}
        original_settle = console._settle_stop  # pyright: ignore[reportPrivateUsage]
        original_begin = console.begin_stop
        stop_tasks: list[asyncio.Task[Any]] = []

        async def held_settlement(*args: Any, **kwargs: Any) -> Any:
            result = await original_settle(*args, **kwargs)
            settled.set()
            await release.wait()
            return result

        async def held_capture(*, seconds: int) -> bytes:
            captures.append(seconds)
            await release_capture.wait()
            return wav()

        def after_final_stop(task: asyncio.Task[Any]) -> None:
            observations["stop_done"] = task.done() and not task.cancelled() and task.exception() is None
            observations["outer_returned"] = returned.is_set()
            context = console.control_context()
            observations["owner_can_record"] = context.can_record
            observations["stopping"] = context.stopping
            observations["control_can_record"] = control.state()["can_record"]
            identity, raw = gesture(control)
            observations["identity"] = identity
            # This existing synchronous dispatch seam fixes the interleaving at
            # task completion, before console.stop's outer waiter can resume.
            try:
                status, _operation = control._dispatch(  # pyright: ignore[reportPrivateUsage]
                    "POST", "/v1/record", raw, context
                )
            except CompanionControlError as error:
                status = error.status
            observations["status"] = status
            attempted.set()

        def begin_stop() -> asyncio.Task[Any]:
            task = original_begin()
            if not stop_tasks:
                stop_tasks.append(task)
                task.add_done_callback(after_final_stop)
            return task

        async def run_console() -> None:
            await console.run()
            returned.set()

        monkeypatch.setattr(console, "_settle_stop", held_settlement)
        monkeypatch.setattr(console, "begin_stop", begin_stop)
        monkeypatch.setattr(companion_lab, "capture_utterance", held_capture)
        running = asyncio.create_task(run_console())
        try:
            if exit_mode == "quit":
                console_pipe.send(b":quit\n")
            else:
                console_pipe.eof()
            await asyncio.wait_for(settled.wait(), 2)
            assert not running.done()
            assert (await client.get("/v1/state")).status_code == 200
            release.set()
            await asyncio.wait_for(attempted.wait(), 2)
            await asyncio.wait_for(running, 2)
            assert observations["stop_done"]
            assert not observations["outer_returned"]
            assert observations["owner_can_record"]
            assert not observations["stopping"]
            assert not observations["control_can_record"]
            assert observations["status"] == 429
            assert control.operation(observations["identity"]) is None
            assert console.voice_task is None or console.voice_task.done()
            assert not captures
            assert not fake.requests
            assert not console.session.run_ids
            assert (await client.get("/v1/state")).json()["can_record"] is False
        finally:
            cleanup = original_begin()
            release.set()
            release_capture.set()
            if not running.done():
                running.cancel()
            await asyncio.wait_for(asyncio.gather(running, cleanup, return_exceptions=True), 2)


@pytest.mark.parametrize("fail_native_write", [False, True])
@pytest.mark.asyncio
async def test_control_queue_cancellation_keeps_terminal_native_custody_after_older_pending_reply(  # noqa: PLR0915 - actual two-command queue and receipt ordering
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch, *, fail_native_write: bool
) -> None:
    transcripts = iter(("say active", "say queued"))
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": next(transcripts)})
    ) as (control, console, fake, client, captures):
        fake.delay = True
        queued_id: str | None = None
        events: list[dict[str, Any]] = []
        original_write, original_observe = files.write_new, control.observe

        def write(path: Path, content: bytes) -> None:
            if (
                fail_native_write
                and path.name.endswith("-native.json")
                and json.loads(content)["request_id"] == queued_id
            ):
                msg = "private queued native receipt failure"
                raise OSError(msg)
            original_write(path, content)

        def observe(event: dict[str, Any]) -> None:
            if event.get("request_id") == queued_id:
                events.append(dict(event))
            original_observe(event)

        monkeypatch.setattr(files, "write_new", write)
        monkeypatch.setattr(control, "observe", observe)
        try:
            active_id, active_raw = gesture(control)
            assert (
                await client.post("/v1/record", content=active_raw, headers={"Content-Type": "application/json"})
            ).status_code == 202
            await asyncio.wait_for(fake.action_started.wait(), 2)
            assert console.voice_task is not None
            await asyncio.wait_for(console.voice_task, 2)
            queued_id, queued_raw = gesture(control)
            assert (
                await client.post("/v1/record", content=queued_raw, headers={"Content-Type": "application/json"})
            ).status_code == 202
            assert console.voice_task is not None
            await asyncio.wait_for(console.voice_task, 2)
            snapshot = console.session.snapshot()
            assert snapshot.current is not None
            assert snapshot.current.request_id == active_id
            assert [item.request_id for item in snapshot.pending] == [queued_id]
            assert len(fake.requests) == 1
            assert captures == [3, 3]
            stop_id, stop_raw = gesture(control, "stop")
            assert (
                await client.post("/v1/stop", content=stop_raw, headers={"Content-Type": "application/json"})
            ).status_code == 202
            stopped = await known(client, stop_id)
            assert stopped["game_kind"] == "applied"
            await asyncio.wait_for(asyncio.gather(*console.replies), 2)
            settled = console.session.outcomes[queued_id]
            assert settled.kind == "cancelled"
            assert settled.reason == "cancelled_before_execution"
            assert settled.run_id is None
            expected = "failed" if fail_native_write else "recorded"
            assert settled.evidence_status == expected
            operation = (await client.get("/v1/operations/" + queued_id)).json()
            assert operation["status"] == "known"
            assert operation["game_kind"] == "cancelled"
            assert operation["native_evidence_status"] == expected
            terminal_index = next(
                index
                for index, event in enumerate(events)
                if event.get("kind") == "native_evidence_failed" or "evidence" in event
            )
            result_index = next(index for index, event in enumerate(events) if "feedback" in event)
            assert terminal_index < result_index
            assert events[result_index]["evidence_status"] == "pending"
            assert len(fake.requests) == 1
            assert queued_id not in console.session.run_ids
            assert not console.replies
        finally:
            cleanup = console.begin_stop()
            fake.release_action.set()
            await asyncio.wait_for(cleanup, 2)


@pytest.mark.asyncio
async def test_fresh_same_session_stop_after_control_expiry_fences_and_joins_transcription(  # noqa: PLR0915 - separate capture expiry from owned revocation settlement
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, retiring, release = (asyncio.Event() for _ in range(3))

    async def transcription(_request: httpx.Request) -> httpx.Response:
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            retiring.set()
            await release.wait()
        raise AssertionError

    async with connected(files, unused_tcp_port, monkeypatch, transcription) as (
        control,
        console,
        fake,
        client,
        captures,
    ):
        try:
            record_id, raw = gesture(control)
            assert (
                await client.post("/v1/record", content=raw, headers={"Content-Type": "application/json"})
            ).status_code == 202
            await asyncio.wait_for(entered.wait(), 2)
            recording = console.voice_task
            assert recording is not None
            assert not recording.done()
            generation = console.session.capture_generation()
            expired_now_ms = control.expires_at_ms + 1
            monkeypatch.setattr(control, "clock", lambda: expired_now_ms / 1000)
            assert not control.state()["can_record"]
            synchronous_fences: list[tuple[bool, bool, bool]] = []
            original_stop = control.stop

            def stop() -> asyncio.Task[Any]:
                task = original_stop()
                # No await separates admission from these owner observations.
                synchronous_fences.append(
                    (
                        console.session.capture_generation() > generation,
                        recording.cancelling() > 0,
                        console.control_context().stopping,
                    )
                )
                return task

            monkeypatch.setattr(control, "stop", stop)
            stop_id, stop_raw = gesture(control, "stop")
            fresh_stop = json.loads(stop_raw)
            fresh_stop.update(created_at_ms=expired_now_ms, admit_before_ms=expired_now_ms + 3000)
            response = await client.post("/v1/stop", json=fresh_stop)
            assert response.status_code == 202
            assert synchronous_fences == [(True, True, True)]
            await asyncio.wait_for(retiring.wait(), 2)
            assert not recording.done()
            pending = control.operation(stop_id)
            assert pending is not None
            assert pending["status"] == "pending"
            release.set()
            stopped = await known(client, stop_id)
            assert stopped["game_kind"] == "applied"
            assert stopped["server_stop_id"] != stop_id
            await asyncio.wait_for(asyncio.gather(recording, return_exceptions=True), 2)
            assert recording.done()
            operation = control.operation(record_id)
            assert operation is not None
            assert operation["status"] == "unknown"
            assert not control.state()["can_record"]
            _fresh_id, fresh_raw = gesture(control)
            fresh_record = json.loads(fresh_raw)
            fresh_record.update(
                created_at_ms=expired_now_ms,
                admit_before_ms=expired_now_ms + 3000,
                expires_at_ms=expired_now_ms + control.state()["instruction_timeout_ms"],
            )
            assert (await client.post("/v1/record", json=fresh_record)).status_code == 408
            assert captures == [3]
            assert not fake.requests
            assert not console.session.run_ids
        finally:
            cleanup = console.begin_stop()
            release.set()
            await asyncio.wait_for(cleanup, 2)
