"""Mocked scout custody proves acknowledgement, admission, bounded output and exact cleanup."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from scripts import reach_research_broker as module

from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile
from lychd.compositions.reach.research_wire import (
    OperatorResearchRequest,
    ReachResearchAcknowledgement,
    ReachResearchProgress,
    ResearchJob,
    ResearchOptions,
    ResearchRuntimeProfile,
    ResearchSource,
    SourceReadResult,
)
from lychd.compositions.reach.schemas import ReachRule
from tests.unit.compositions.test_reach_documents import NOW, make_policy, make_request

IMAGE = "sha256:" + "a" * 64
CONTAINER_ID = "b" * 64
type BrokerCase = tuple[module.OperatorResearchBroker, OperatorResearchRequest, Path, ResearchRuntimeProfile]


def write_profile(path: Path, profile: ResearchRuntimeProfile) -> None:
    path.write_text(profile.model_dump_json(), encoding="utf-8")
    path.chmod(0o600)


@pytest.fixture
def broker_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BrokerCase:
    monkeypatch.setattr(module, "_now", lambda: NOW)
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    authority = tmp_path / "authority"
    authority.mkdir(mode=0o700)
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    research = ResearchOptions(
        enabled=True,
        sources=(ResearchSource(id="jjk", title="Domain Expansion", url="https://public.example/domain/"),),
    )
    profile = OperatorConversationProfile(
        persona_name="Nadir", persona_instructions="Be helpful.", adaptive_context=True, research=research
    )
    policy = make_policy(
        rules=(ReachRule(name="operator", subject_ids=("person:one",), actions=("converse",)),),
        allowed_direct_subject_ids=("person:one",),
    )
    runtime = ResearchRuntimeProfile(
        source_kind="operator_public_catalogue",
        public_catalogue_authorized=True,
        policy_revision=1,
        revocation_generation=0,
        expires_at=NOW + timedelta(minutes=10),
        catalogue=research,
        allowed_subject_ids=("person:one",),
        allowed_channel_ids=("channel:one",),
        allowed_dm_user_ids=("person:one",),
        resolver_address="1.1.1.1",
        resolver_custody_statement="The operator selects the fixed public resolver.",
    )
    path = authority / "profile.json"
    write_profile(path, runtime)
    broker = module.OperatorResearchBroker(profile, policy, runtime_profile_path=path, state_dir=state, image=IMAGE)
    request = OperatorResearchRequest(
        call_id=str(uuid4()),
        request_id="request:research",
        binding_digest=profile.digest,
        event=make_request(action="converse").event,
        plan="I will compare the source with the Lich documentation.",
        source_ids=("jjk",),
    )
    return broker, request, path, runtime


def source() -> SourceReadResult:
    text = "A bounded attributed source excerpt."
    return SourceReadResult(
        id="web:jjk",
        title="Domain Expansion",
        url="https://public.example/domain/",
        status="ok",
        text=text,
        source_digest="c" * 64,
        text_digest=sha256(text.encode()).hexdigest(),
        source_chars=100,
        excerpt_start=2,
        truncated=True,
        receipt_id="d" * 64,
    )


def encoded_source() -> bytes:
    return json.dumps([source().model_dump(mode="json")]).encode()


def ack(broker: module.OperatorResearchBroker) -> Callable[[ReachResearchProgress], Awaitable[None]]:
    async def deliver(progress: ReachResearchProgress) -> None:
        broker.acknowledge(
            ReachResearchAcknowledgement(
                call_id=progress.call_id,
                request_id=progress.request_id,
                binding_digest=progress.binding_digest,
                accepted=True,
            )
        )

    return deliver


def assert_no_pending_acknowledgements(broker: module.OperatorResearchBroker) -> None:
    # Late ACKs are inert publicly; this custody oracle also proves no pending Future survives.
    assert broker._pending == {}  # pyright: ignore[reportPrivateUsage]


def next_local_request(request: OperatorResearchRequest) -> OperatorResearchRequest:
    return request.model_copy(
        update={
            "call_id": str(uuid4()),
            "request_id": "request:following-local",
            "event": request.event.model_copy(update={"event_id": f"event:{uuid4()}"}),
            "source_ids": (),
        }
    )


async def assert_available_for_local_turn(
    broker: module.OperatorResearchBroker, request: OperatorResearchRequest
) -> None:
    result = await broker.handle(next_local_request(request), ack(broker))
    assert result.status == "ok"
    assert result.sources == ()


class InputPipe:
    def __init__(self) -> None:
        self.content = bytearray()
        self.closed = False

    def write(self, value: bytes) -> None:
        self.content.extend(value)

    async def drain(self) -> None:
        return

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return


class Process:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", *, running: bool = False, code: int = 0) -> None:
        self.stdin = InputPipe()
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.stderr.feed_data(stderr)
        self.returncode = None if running else code
        self.finished = asyncio.Event()
        self.terminated = False
        if not running:
            self.stdout.feed_eof()
            self.stderr.feed_eof()
            self.finished.set()

    async def wait(self) -> int:
        await self.finished.wait()
        assert self.returncode is not None
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15
        self.stdout.feed_eof()
        self.stderr.feed_eof()
        self.finished.set()

    def kill(self) -> None:
        self.terminate()
        self.returncode = -9


class Engine:
    def __init__(self, process: Process, *, cleanup_code: int = 0, identity: str = CONTAINER_ID) -> None:
        self.process = process
        self.cleanup_code = cleanup_code
        self.identity = identity
        self.calls: list[tuple[str, ...]] = []
        self.environments: list[dict[str, str]] = []
        self.started = asyncio.Event()

    async def spawn(self, *args: str, **kwargs: Any) -> asyncio.subprocess.Process:
        self.calls.append(args)
        self.environments.append(kwargs["env"])
        if "run" in args:
            cidfile = Path(args[args.index("--cidfile") + 1])
            await asyncio.to_thread(cidfile.write_text, self.identity, encoding="ascii")
            self.started.set()
            return cast("asyncio.subprocess.Process", self.process)
        assert args[-3:] == ("rm", "--force", CONTAINER_ID)
        return cast("asyncio.subprocess.Process", Process(code=self.cleanup_code))


@pytest.mark.asyncio
async def test_acknowledgement_precedes_scout_and_job_discloses_only_local_metadata(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, path, _ = broker_case
    engine = Engine(Process(encoded_source()))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    progress_sent = asyncio.Event()

    async def progress(message: ReachResearchProgress) -> None:
        assert message.text == request.plan
        assert message.request_id == request.request_id
        progress_sent.set()

    task = asyncio.create_task(broker.handle(request, progress))
    await progress_sent.wait()
    assert engine.calls == []
    await ack(broker)(
        ReachResearchProgress(
            call_id=request.call_id,
            request_id=request.request_id,
            binding_digest=request.binding_digest,
            text=request.plan,
        )
    )
    result = await task
    assert result.status == "ok"
    assert result.sources == (source(),)
    job = ResearchJob.model_validate_json(bytes(engine.process.stdin.content))
    assert job.source_ids == request.source_ids
    assert job.event_id == request.event.event_id
    assert not job.direct
    assert request.plan.encode() not in engine.process.stdin.content
    assert request.event.question.encode() not in engine.process.stdin.content
    command = engine.calls[0]
    assert command[0] == "docker"
    assert "--network=host" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--security-opt=seccomp=unconfined" in command
    assert "--security-opt=systempaths=unconfined" in command
    assert "--security-opt=label=disable" in command
    assert command.count("--mount") == 2
    assert f"type=bind,src={path.parent},dst=/run/research-authority,readonly" in command
    assert f"type=bind,src={broker.state_dir / 'scout'},dst=/state/research" in command
    assert IMAGE in command
    assert "/work/scripts/reach_scout_worker.py" in command
    assert engine.calls[-1][-1] == CONTAINER_ID
    assert set(engine.environments[0]) == {"PATH", "LANG"}
    assert not list(broker.state_dir.glob("scout-*"))


@pytest.mark.asyncio
async def test_doc_only_plan_requires_ack_but_never_starts_a_scout(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case

    async def forbidden(*_args: str, **_kwargs: Any) -> asyncio.subprocess.Process:
        pytest.fail("A local-only plan must not launch an acquisition process")

    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", forbidden)
    request = request.model_copy(update={"source_ids": ()})
    result = await broker.handle(request, ack(broker))
    assert (result.status, result.sources) == ("ok", ())
    duplicate = await broker.handle(request.model_copy(update={"call_id": str(uuid4())}), ack(broker))
    assert duplicate.reason == "research_duplicate"


@pytest.mark.parametrize("change", ["binding", "unknown", "repeated", "event", "subject", "target", "expired"])
@pytest.mark.asyncio
async def test_refused_admission_performs_no_progress_or_process_work(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    broker, request, path, runtime = broker_case
    if change == "binding":
        request = request.model_copy(update={"binding_digest": "0" * 64})
    elif change == "unknown":
        request = request.model_copy(update={"source_ids": ("invented",)})
    elif change == "repeated":
        request = request.model_copy(update={"source_ids": ("jjk", "jjk")})
    elif change == "event":
        request = request.model_copy(
            update={"event": request.event.model_copy(update={"occurred_at": NOW + timedelta(seconds=1)})}
        )
    elif change == "subject":
        write_profile(path, runtime.model_copy(update={"allowed_subject_ids": ("person:other",)}))
    elif change == "target":
        write_profile(path, runtime.model_copy(update={"allowed_channel_ids": ("channel:other",)}))
    else:
        monkeypatch.setattr(module, "_now", lambda: NOW + timedelta(minutes=11))

    async def progress(_message: ReachResearchProgress) -> None:
        pytest.fail("Refused admission must not acknowledge or start acquisition")

    result = await broker.handle(request, progress)
    assert result.status == "refused"
    assert result.sources == ()


@pytest.mark.asyncio
async def test_atomic_revocation_after_ack_prevents_source_acquisition(broker_case: BrokerCase) -> None:
    broker, request, path, runtime = broker_case

    async def progress(message: ReachResearchProgress) -> None:
        replacement = path.parent / "replacement.json"
        write_profile(replacement, runtime.model_copy(update={"revocation_generation": 1}))
        replacement.replace(path)
        await ack(broker)(message)

    result = await broker.handle(request, progress)
    assert result.reason == "research_authority"
    assert result.sources == ()
    assert not list(broker.state_dir.iterdir())


@pytest.mark.asyncio
async def test_failed_or_timed_out_ack_has_no_process_and_fences_event(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    monkeypatch.setattr(module, "ACK_TIMEOUT_SECONDS", 0)

    async def progress(_message: ReachResearchProgress) -> None:
        return

    result = await broker.handle(request, progress)
    assert result.reason == "research_timeout"
    assert not list(broker.state_dir.iterdir())
    duplicate = await broker.handle(request, progress)
    assert duplicate.reason == "research_duplicate"
    await ack(broker)(
        ReachResearchProgress(
            call_id=request.call_id,
            request_id=request.request_id,
            binding_digest=request.binding_digest,
            text=request.plan,
        )
    )
    assert not list(broker.state_dir.iterdir())
    assert (await broker.handle(request, progress)).reason == "research_duplicate"


@pytest.mark.asyncio
async def test_ack_must_match_all_pending_bindings_and_cannot_be_replayed(broker_case: BrokerCase) -> None:
    broker, request, _, _ = broker_case
    request = request.model_copy(update={"source_ids": ()})

    async def progress(message: ReachResearchProgress) -> None:
        wrong = ReachResearchAcknowledgement(
            call_id=message.call_id,
            request_id="request:other",
            binding_digest=message.binding_digest,
            accepted=True,
        )
        with pytest.raises(ValueError, match="research_acknowledgement"):
            broker.acknowledge(wrong)
        right = wrong.model_copy(update={"request_id": message.request_id})
        broker.acknowledge(right)
        with pytest.raises(ValueError, match="research_acknowledgement"):
            broker.acknowledge(right)

    assert (await broker.handle(request, progress)).status == "ok"


@pytest.mark.asyncio
async def test_negative_acknowledgement_performs_no_acquisition(broker_case: BrokerCase) -> None:
    broker, request, _, _ = broker_case

    async def decline(message: ReachResearchProgress) -> None:
        broker.acknowledge(
            ReachResearchAcknowledgement(
                call_id=message.call_id,
                request_id=message.request_id,
                binding_digest=message.binding_digest,
                accepted=False,
            )
        )

    result = await broker.handle(request, decline)
    assert result.reason == "research_acknowledgement"
    assert not list(broker.state_dir.iterdir())


@pytest.mark.asyncio
async def test_generation_budget_rejects_new_events_before_progress(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    monkeypatch.setattr(module, "MAX_SEEN_EVENTS", 0)
    result = await broker.handle(request, ack(broker))
    assert result.reason == "research_generation_budget"
    assert_no_pending_acknowledgements(broker)


@pytest.mark.asyncio
async def test_cancellation_during_ack_closes_pending_slot_without_acquisition(broker_case: BrokerCase) -> None:
    broker, request, _, _ = broker_case
    waiting = asyncio.Event()

    async def progress(_message: ReachResearchProgress) -> None:
        waiting.set()

    task = asyncio.create_task(broker.handle(request, progress))
    await waiting.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert_no_pending_acknowledgements(broker)
    assert not list(broker.state_dir.iterdir())
    await assert_available_for_local_turn(broker, request)


@pytest.mark.parametrize("failure", ["id", "url", "title", "digest", "extra", "stdout", "stderr", "exit"])
@pytest.mark.asyncio
async def test_foreign_protocol_or_size_failures_are_content_free_and_cleanup_exactly_once(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    broker, request, _, _ = broker_case
    value = source().model_dump(mode="json")
    if failure in {"id", "url", "title"}:
        value[failure] = {"id": "web:invented", "url": "https://other.example/", "title": "Foreign title"}[failure]
    elif failure == "digest":
        value["text_digest"] = "0" * 64
    output = json.dumps([value, value] if failure == "extra" else [value]).encode()
    if failure == "stdout":
        output = b"secret-source" * module.MAX_SCOUT_OUTPUT_BYTES
    error = b"secret-diagnostic" * module.MAX_SCOUT_ERROR_BYTES if failure == "stderr" else b""
    engine = Engine(Process(output, error, code=1 if failure == "exit" else 0))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    result = await broker.handle(request, ack(broker))
    assert result.status == "refused"
    assert result.reason == "research_protocol"
    assert result.sources == ()
    assert "secret" not in result.model_dump_json()
    assert len(engine.calls) == 2
    assert engine.calls[-1][-3:] == ("rm", "--force", CONTAINER_ID)


@pytest.mark.asyncio
async def test_cancellation_retires_scout_then_removes_its_exact_container(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    process = Process(running=True)
    engine = Engine(process)
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    task = asyncio.create_task(broker.handle(request, ack(broker)))
    await engine.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.terminated
    assert len(engine.calls) == 2
    assert engine.calls[-1][-1] == CONTAINER_ID
    assert_no_pending_acknowledgements(broker)
    await assert_available_for_local_turn(broker, request)


@pytest.mark.asyncio
async def test_cancellation_during_spawn_still_joins_client_and_exact_cleanup(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    process = Process(running=True)
    engine = Engine(process)
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(*args: str, **kwargs: Any) -> asyncio.subprocess.Process:
        if "run" in args:
            started.set()
            await release.wait()
        return await engine.spawn(*args, **kwargs)

    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", delayed)
    task = asyncio.create_task(broker.handle(request, ack(broker)))
    await started.wait()
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.terminated
    assert engine.calls[-1][-1] == CONTAINER_ID


@pytest.mark.asyncio
async def test_repeated_cancellation_cannot_cancel_the_owned_spawn_capture(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    process = Process(running=True)
    engine = Engine(process)
    started, release, interrupted = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def delayed(*args: str, **kwargs: Any) -> asyncio.subprocess.Process:
        if "run" in args:
            started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                interrupted.set()
                raise
        return await engine.spawn(*args, **kwargs)

    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", delayed)
    task = asyncio.create_task(broker.handle(request, ack(broker)))
    await started.wait()
    for _ in range(3):
        task.cancel()
        await asyncio.sleep(0)
    was_waiting = not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert was_waiting
    assert not interrupted.is_set()
    assert process.terminated
    assert engine.calls[-1][-3:] == ("rm", "--force", CONTAINER_ID)
    assert not list(broker.state_dir.glob("scout-*"))
    await assert_available_for_local_turn(broker, request)


@pytest.mark.asyncio
async def test_repeated_cancellation_waits_for_proved_cleanup_before_removing_cid_scratch(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    engine = Engine(Process(encoded_source()))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    started, release, interrupted = asyncio.Event(), asyncio.Event(), asyncio.Event()
    # Pause the real custody boundary to inject repeated caller cancellation.
    original_cleanup = broker._cleanup  # pyright: ignore[reportPrivateUsage]

    async def delayed(process: asyncio.subprocess.Process | None, scratch: Path) -> None:
        started.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            interrupted.set()
            raise
        await original_cleanup(process, scratch)

    monkeypatch.setattr(broker, "_cleanup", delayed)
    task = asyncio.create_task(broker.handle(request, ack(broker)))
    await started.wait()
    scratch = next(broker.state_dir.glob("scout-*"))
    for _ in range(3):
        task.cancel()
        await asyncio.sleep(0)
    was_waiting = not task.done()
    retained_before_proof = (scratch / "container.id").is_file()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert was_waiting
    assert retained_before_proof
    assert not interrupted.is_set()
    assert engine.calls[-1][-3:] == ("rm", "--force", CONTAINER_ID)
    assert not scratch.exists()
    await assert_available_for_local_turn(broker, request)


@pytest.mark.asyncio
async def test_cancelled_owned_cleanup_retains_cid_and_fences_later_work(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    engine = Engine(Process(encoded_source()))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)

    async def interrupted(_process: asyncio.subprocess.Process | None, _scratch: Path) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(broker, "_cleanup", interrupted)
    with pytest.raises(asyncio.CancelledError):
        await broker.handle(request, ack(broker))
    scratch = next(broker.state_dir.glob("scout-*"))
    assert (scratch / "container.id").read_text(encoding="ascii") == CONTAINER_ID
    assert len(engine.calls) == 1
    later = request.model_copy(
        update={"call_id": str(uuid4()), "event": request.event.model_copy(update={"event_id": "event:later"})}
    )
    assert (await broker.handle(later, ack(broker))).reason == "research_unavailable"
    assert len(engine.calls) == 1


@pytest.mark.asyncio
async def test_timeout_settles_started_scout_and_does_not_retry(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    process = Process(running=True)
    engine = Engine(process)
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    monkeypatch.setattr(module, "SCOUT_TIMEOUT_SECONDS", 0)
    result = await broker.handle(request, ack(broker))
    assert result.reason == "research_timeout"
    assert process.terminated
    assert len(engine.calls) == 2
    assert engine.calls[-1][-1] == CONTAINER_ID


@pytest.mark.asyncio
async def test_client_retirement_failure_still_attempts_exact_container_removal(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, _, _ = broker_case
    engine = Engine(Process(encoded_source()))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    # Force an actual client-retirement failure while retaining real container cleanup.
    original_retire = module._retire  # pyright: ignore[reportPrivateUsage]

    async def failed_client(process: asyncio.subprocess.Process) -> None:
        if process is cast("asyncio.subprocess.Process", engine.process):
            raise TimeoutError
        await original_retire(process)

    monkeypatch.setattr(module, "_retire", failed_client)
    result = await broker.handle(request, ack(broker))
    assert result.reason == "research_cleanup"
    scratch = next(broker.state_dir.glob("scout-*"))
    assert (scratch / "container.id").read_text(encoding="ascii") == CONTAINER_ID
    assert engine.calls[-1][-3:] == ("rm", "--force", CONTAINER_ID)
    assert (await broker.handle(next_local_request(request), ack(broker))).reason == "research_unavailable"
    assert len(engine.calls) == 2


@pytest.mark.asyncio
async def test_revocation_after_acquisition_does_not_promote_source_body(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, path, runtime = broker_case
    engine = Engine(Process(encoded_source()))

    async def revoke_at_settlement(*args: str, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await engine.spawn(*args, **kwargs)
        if "rm" in args:
            write_profile(path, runtime.model_copy(update={"revocation_generation": 1}))
        return process

    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", revoke_at_settlement)
    result = await broker.handle(request, ack(broker))
    assert result.reason == "research_authority"
    assert result.sources == ()


@pytest.mark.parametrize("identity", [CONTAINER_ID, "untrusted-container-name"])
@pytest.mark.asyncio
async def test_uncertain_cleanup_fences_later_source_work(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch, identity: str
) -> None:
    broker, request, _, _ = broker_case
    engine = Engine(Process(encoded_source()), cleanup_code=1, identity=identity)
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    result = await broker.handle(request, ack(broker))
    assert result.reason == "research_cleanup"
    scratch = next(broker.state_dir.glob("scout-*"))
    assert (scratch / "container.id").read_text(encoding="ascii") == identity
    count = len(engine.calls)
    later = request.model_copy(
        update={"call_id": str(uuid4()), "event": request.event.model_copy(update={"event_id": "event:later"})}
    )
    refused = await broker.handle(later, ack(broker))
    assert refused.reason == "research_unavailable"
    assert len(engine.calls) == count


@pytest.mark.parametrize("change", ["image", "authority_extra", "mode", "symlink", "overlap"])
def test_constructor_rejects_broad_or_unbound_local_custody(broker_case: BrokerCase, change: str) -> None:
    broker, _, path, _ = broker_case
    image, state = IMAGE, broker.state_dir
    if change == "image":
        image = "mutable:latest"
    elif change == "authority_extra":
        (path.parent / "unrelated.txt").write_text("not admitted", encoding="utf-8")
    elif change == "mode":
        path.chmod(0o644)
    elif change == "symlink":
        target = path.parent.parent / "profile-target.json"
        path.replace(target)
        path.symlink_to(target)
    else:
        state = path.parent
    with pytest.raises(ValueError, match="research_"):
        module.OperatorResearchBroker(
            broker.profile, broker.policy, runtime_profile_path=path, state_dir=state, image=image
        )


@pytest.mark.asyncio
async def test_only_local_engine_socket_environment_can_be_selected(
    broker_case: BrokerCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    broker, request, path, _ = broker_case
    monkeypatch.setenv("DOCKER_HOST", "tcp://foreign.example:2376")
    with pytest.raises(ValueError, match="research_engine_host"):
        module.OperatorResearchBroker(
            broker.profile, broker.policy, runtime_profile_path=path, state_dir=broker.state_dir, image=IMAGE
        )
    monkeypatch.setenv("DOCKER_HOST", "unix:///run/user/1000/docker.sock")
    local = module.OperatorResearchBroker(
        broker.profile, broker.policy, runtime_profile_path=path, state_dir=broker.state_dir, image=IMAGE
    )
    engine = Engine(Process(encoded_source()))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", engine.spawn)
    result = await local.handle(request, ack(local))
    assert result.status == "ok"
    environment = engine.environments[0]
    assert environment["DOCKER_HOST"] == os.environ["DOCKER_HOST"]
    assert "HOME" not in environment
    assert "DOCKER_CONFIG" not in environment
