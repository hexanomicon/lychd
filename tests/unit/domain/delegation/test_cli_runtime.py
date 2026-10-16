"""Official CLI transcript interpretation and fail-closed host-boundary tests."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Literal, cast

import pytest

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.delegation import DelegatedAgentCoordinator, InMemoryDelegatedAgentJobStore
from lychd.domain.delegation.cli_protocol import (
    CliLaunchSpec,
    CliLimits,
    CliRuntimeKind,
    CliWorkspace,
    build_cli_launch_spec,
    parse_cli_output,
    reviewed_cli_version,
)
from lychd.domain.delegation.cli_runtime import (
    ClaudeCliRuntime,
    CliCancellationObservation,
    CliContainmentReceipt,
    CliContainmentUncertainError,
    CliExitObservation,
    CliLaunchRefusedError,
    CodexCliRuntime,
)
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentRequest,
)
from tests.support.delegated_cli import InertOwnerAdmission, cli_request


def _identity(kind: CliRuntimeKind) -> tuple[DelegatedAgentRequest, DelegatedAgentJobRef]:
    request = DelegatedAgentRequest(
        request_id="request", run_id="run", step_id="step", runtime=kind, prompt="--resume $(false)\nUnicode: λ"
    )
    return request, DelegatedAgentJobRef(job_id="job", request_id="request", run_id="run", runtime=kind)


def _jsonl(*records: dict[str, object]) -> bytes:
    return ("\n".join(json.dumps(record) for record in records) + "\n").encode()


def _claude_stream(*records: dict[str, object]) -> bytes:
    return _jsonl(
        {"type": "system", "subtype": "init", "session_id": "provider-session"},
        *({**record, "session_id": "provider-session"} for record in records),
    )


def _codex_success() -> bytes:
    return _jsonl(
        {"type": "thread.started", "thread_id": "provider-thread"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "candidate only"}},
        {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 2}},
    )


@pytest.mark.parametrize("kind", list(CliRuntimeKind))
def test_launch_is_literal_and_has_no_ambient_auth(kind: CliRuntimeKind) -> None:
    request, job = _identity(kind)
    spec = build_cli_launch_spec(
        kind,
        executable=f"/opt/agents/{kind}",
        model="explicit-model",
        request=request,
        job=job,
        workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
        limits=CliLimits(),
    )
    assert spec.stdin == request.prompt.encode()
    assert request.prompt not in spec.argv
    assert spec.argv[0] == f"/opt/agents/{kind}"
    assert not {"PATH", "OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY"}.intersection(dict(spec.environment))
    assert dict(spec.environment)["HOME"] == "/jobs/one/scratch/home"
    assert not {"--resume", "--continue", "--fallback-model", "--dangerously-skip-permissions"}.intersection(spec.argv)
    if kind is CliRuntimeKind.CODEX:
        assert spec.argv[1:3] == ("exec", "--json")
        assert "--ignore-user-config" in spec.argv
        assert spec.argv[-1] == "-"
    else:
        assert spec.argv[1:3] == ("--bare", "--print")
        assert "--no-session-persistence" in spec.argv


@pytest.mark.parametrize(
    ("kind", "expected_digest"),
    [
        (CliRuntimeKind.CODEX, "d6f39a08eecd609ace5159eef699d2b8672d9c700a2ac62ce383a95687f1c75d"),
        (CliRuntimeKind.CLAUDE, "9fee704d545ad0600c8ff0cd76265bd90b9d8a64ba856cc2ef4ea7915cf90ce8"),
    ],
)
def test_legacy_request_and_launch_identities_remain_literal(kind: CliRuntimeKind, expected_digest: str) -> None:
    literal = (
        '{"request_id":"legacy-request","run_id":"legacy-run","step_id":"delegate",'
        f'"runtime":"{kind.value}","profile":"read","prompt":"Keep λ literal.",'
        '"input_artifacts":[{"artifact_id":"input-1",'
        '"digest":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        '"media_type":"text/plain","size":12,"classification":"internal"}]}'
    )
    request = DelegatedAgentRequest.model_validate_json(literal)
    job = DelegatedAgentJobRef(job_id="legacy-job", request_id=request.request_id, run_id=request.run_id, runtime=kind)
    spec = build_cli_launch_spec(
        kind,
        executable=f"/opt/agents/{kind}",
        model="explicit-model",
        request=request,
        job=job,
        workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
        limits=CliLimits(),
    )

    assert request.model_dump_json() == literal
    assert spec.digest == expected_digest


@pytest.mark.parametrize("path", ["codex", "/opt/../codex", "/opt//codex", "/opt/codex\n", "//opt/codex"])
def test_unsafe_executable_refused(path: str) -> None:
    with pytest.raises(ValueError, match="canonical absolute"):
        CodexCliRuntime(executable=path, model="model", job_roots="/jobs")


def test_overlapping_roots_refused() -> None:
    with pytest.raises(ValueError, match="disjoint"):
        CliWorkspace("/job", "/job/work", "/job/work/tmp", "/job/artifacts")


@pytest.mark.parametrize(
    ("kind", "stdout"),
    [
        (CliRuntimeKind.CODEX, _codex_success()),
        (
            CliRuntimeKind.CLAUDE,
            _claude_stream(
                {"type": "result", "subtype": "success", "is_error": False, "result": "candidate only"},
            ),
        ),
    ],
)
def test_official_terminal_transcript(kind: CliRuntimeKind, stdout: bytes) -> None:
    result = parse_cli_output(kind, stdout, job_id="job", exit_code=0, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.SUCCEEDED
    assert result.output == "candidate only"


@pytest.mark.parametrize(
    "stdout",
    [
        b"",
        b"not json",
        b'{"type":"result","type":"result"}',
        b"\xff",
        _jsonl({"type": "result", "subtype": "success", "is_error": False}),
        _jsonl({"type": "result", "subtype": "success", "is_error": True, "result": "bad"}),
        _jsonl(
            {"type": "result", "subtype": "success", "is_error": False, "result": "ok"},
            {"type": "result", "subtype": "success", "is_error": False, "result": "late"},
        ),
    ],
)
def test_malformed_claude_evidence_is_lost(stdout: bytes) -> None:
    assert (
        parse_cli_output(CliRuntimeKind.CLAUDE, stdout, job_id="job", exit_code=0, limits=CliLimits()).status
        is DelegatedAgentJobStatus.LOST
    )


@pytest.mark.parametrize(
    "stdout",
    [
        _codex_success().rsplit(b"\n", 2)[0],
        _codex_success() + _jsonl({"type": "turn.completed"}),
        _jsonl({"type": "turn.completed"}),
    ],
)
def test_missing_or_duplicate_codex_terminal_is_lost(stdout: bytes) -> None:
    assert (
        parse_cli_output(CliRuntimeKind.CODEX, stdout, job_id="job", exit_code=0, limits=CliLimits()).status
        is DelegatedAgentJobStatus.LOST
    )


def test_success_requires_zero_exit_and_bounded_capture() -> None:
    for exit_code, limits in [
        (1, CliLimits()),
        (0, CliLimits(max_stdout_bytes=10, max_record_bytes=10)),
        (0, CliLimits(max_record_bytes=10)),
    ]:
        assert (
            parse_cli_output(
                CliRuntimeKind.CODEX, _codex_success(), job_id="job", exit_code=exit_code, limits=limits
            ).status
            is DelegatedAgentJobStatus.LOST
        )


@pytest.mark.parametrize(
    ("kind", "stdout"),
    [
        (
            CliRuntimeKind.CODEX,
            _jsonl(
                {"type": "thread.started", "thread_id": "id"},
                {"type": "turn.started"},
                {"type": "turn.failed", "error": {"message": "secret"}},
            ),
        ),
        (
            CliRuntimeKind.CLAUDE,
            _claude_stream(
                {"type": "result", "subtype": "error_during_execution", "is_error": True, "errors": ["secret"]}
            ),
        ),
    ],
)
def test_failed_turn_is_generic_and_secret_free(kind: CliRuntimeKind, stdout: bytes) -> None:
    result = parse_cli_output(kind, stdout, job_id="job", exit_code=1, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.FAILED
    assert "secret" not in result.model_dump_json()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(CliRuntimeKind))
async def test_default_runtime_refuses_launch_lookup_and_cancellation(kind: CliRuntimeKind) -> None:
    request, job = _identity(kind)
    runtime_type = CodexCliRuntime if kind is CliRuntimeKind.CODEX else ClaudeCliRuntime
    runtime = runtime_type(executable=f"/opt/agents/{kind}", model="model", job_roots="/jobs")
    with pytest.raises(CliLaunchRefusedError):
        await runtime.start(request, job)
    result = await runtime.poll(job, request=request)
    assert result is not None
    assert result.status is DelegatedAgentJobStatus.LOST
    with pytest.raises(CliContainmentUncertainError):
        await runtime.cancel(job, request=request)


@pytest.mark.asyncio
async def test_poll_after_reconstruction_never_launches_and_cancel_requires_exact_receipt() -> None:
    request, job = _identity(CliRuntimeKind.CODEX)
    spec = build_cli_launch_spec(
        CliRuntimeKind.CODEX,
        executable="/opt/codex",
        model="model",
        request=request,
        job=job,
        workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
        limits=CliLimits(),
    )
    receipt = CliContainmentReceipt(job, "host-test-evidence", spec.digest)

    expected_job = job

    class Host:
        async def launch(self, spec: object) -> None:
            del spec
            pytest.fail("Observation must never launch or resume.")

        async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation:
            assert job == expected_job
            return CliExitObservation(spec, receipt, 0, _codex_success())

        async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
            return CliCancellationObservation(
                spec, replace(receipt, job=job.model_copy(update={"request_id": "other"}))
            )

    runtime = CodexCliRuntime(executable="/opt/codex", model="model", job_roots="/jobs", host=Host())
    result = await runtime.poll(job, request=request)
    assert result is not None
    assert result.status is DelegatedAgentJobStatus.SUCCEEDED
    with pytest.raises(CliContainmentUncertainError):
        await runtime.cancel(job, request=request)


@pytest.mark.parametrize(
    "stdout",
    [
        b'{"type":"result","subtype":"success","is_error":false,"result":"ok","usage":NaN}\n',
        b'{"type":"result","subtype":"success","is_error":false,"result":"ok"}',
    ],
)
def test_non_json_or_incomplete_final_record_is_lost(stdout: bytes) -> None:
    result = parse_cli_output(CliRuntimeKind.CLAUDE, stdout, job_id="job", exit_code=0, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.LOST


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", [False, True])
async def test_restart_uses_durable_limits_and_rejects_stale_launch_evidence(*, mismatch: bool) -> None:
    request, job = _identity(CliRuntimeKind.CODEX)
    limits = CliLimits(max_stdout_bytes=64, max_record_bytes=64)
    spec = build_cli_launch_spec(
        CliRuntimeKind.CODEX,
        executable="/opt/codex",
        model="model",
        request=request,
        job=job,
        workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
        limits=limits,
    )
    receipt = CliContainmentReceipt(job, "test-evidence", "0" * 64 if mismatch else spec.digest)

    expected_job = job

    class Host:
        async def launch(self, spec: object) -> None:
            del spec
            pytest.fail("Restart observation must not launch.")

        async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation:
            assert job == expected_job
            return CliExitObservation(spec, receipt, 0, _codex_success())

        async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
            assert job == expected_job
            return CliCancellationObservation(spec, receipt)

    runtime = CodexCliRuntime(
        executable="/opt/codex", model="different-model", job_roots="/different", limits=CliLimits(), host=Host()
    )
    result = await runtime.poll(job, request=request)
    assert result is not None
    assert result.status is DelegatedAgentJobStatus.LOST


def test_launch_digest_binds_prompt_limits_and_cli_version() -> None:
    request, job = _identity(CliRuntimeKind.CODEX)
    spec = build_cli_launch_spec(
        CliRuntimeKind.CODEX,
        executable="/opt/codex",
        model="model",
        request=request,
        job=job,
        workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
        limits=CliLimits(),
    )
    assert spec.digest != replace(spec, stdin=b"changed").digest
    assert spec.digest != replace(spec, limits=CliLimits(wall_seconds=1)).digest
    assert spec.digest != replace(spec, cli_version="unreviewed").digest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("termination", "stderr", "expected"),
    [
        ("timed_out", b"", DelegatedAgentJobStatus.TIMED_OUT),
        ("output_limit", b"", DelegatedAgentJobStatus.LOST),
        ("exited", b"x" * 16_385, DelegatedAgentJobStatus.LOST),
    ],
)
async def test_host_termination_and_both_capture_limits_are_preserved(
    termination: Literal["exited", "timed_out", "output_limit"],
    stderr: bytes,
    expected: DelegatedAgentJobStatus,
) -> None:
    request, job = _identity(CliRuntimeKind.CODEX)
    spec = build_cli_launch_spec(
        CliRuntimeKind.CODEX,
        executable="/opt/codex",
        model="model",
        request=request,
        job=job,
        workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
        limits=CliLimits(),
    )
    receipt = CliContainmentReceipt(job, "test-evidence", spec.digest)

    expected_job = job

    class Host:
        async def launch(self, spec: object) -> None:
            del spec
            pytest.fail("Observation must not launch.")

        async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation:
            assert job == expected_job
            return CliExitObservation(spec, receipt, 0, _codex_success(), stderr, termination)

        async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
            assert job == expected_job
            return CliCancellationObservation(spec, receipt)

    runtime = CodexCliRuntime(executable="/opt/codex", model="model", job_roots="/jobs", host=Host())
    result = await runtime.poll(job, request=request)
    assert result is not None
    assert result.status is expected


@pytest.mark.parametrize("kind", ["codex", "claude", "other", "", None])
def test_runtime_kind_cannot_fall_through_to_another_protocol(kind: object) -> None:
    invalid_kind = cast("CliRuntimeKind", kind)
    output = _claude_stream({"type": "result", "subtype": "success", "is_error": False, "result": "ok"})
    result = parse_cli_output(invalid_kind, output, job_id="job", exit_code=0, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.LOST
    with pytest.raises(ValueError, match="exact supported"):
        reviewed_cli_version(invalid_kind)
    request, job = _identity(CliRuntimeKind.CODEX)
    with pytest.raises(ValueError, match="exact supported"):
        build_cli_launch_spec(
            invalid_kind,
            executable="/opt/codex",
            model="model",
            request=request,
            job=job,
            workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
            limits=CliLimits(),
        )


@pytest.mark.parametrize(
    "record",
    [
        {"type": "turn.failed"},
        {"type": "error"},
        {"type": "unknown"},
        {"type": "system", "subtype": "init"},
        {"type": "result", "subtype": "error_during_execution", "is_error": True},
        {"type": "assistant", "error": "foreign-secret", "message": {"role": "assistant", "content": []}},
        {"type": "assistant", "message": {"role": "user", "content": []}},
    ],
)
def test_claude_conflicting_or_unknown_events_cannot_precede_success(record: dict[str, object]) -> None:
    output = _claude_stream(record, {"type": "result", "subtype": "success", "is_error": False, "result": "ok"})
    result = parse_cli_output(CliRuntimeKind.CLAUDE, output, job_id="job", exit_code=0, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.LOST
    assert "foreign-secret" not in result.model_dump_json()


@pytest.mark.parametrize("session", [None, "", "different", "x" * 129, "\ud800"])
def test_claude_terminal_requires_the_bounded_initialized_session(session: object) -> None:
    output = _jsonl(
        {"type": "system", "subtype": "init", "session_id": "session"},
        {"type": "result", "subtype": "success", "is_error": False, "result": "ok", "session_id": session},
    )
    result = parse_cli_output(CliRuntimeKind.CLAUDE, output, job_id="job", exit_code=0, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.LOST


@pytest.mark.parametrize("kind", list(CliRuntimeKind))
def test_lone_surrogate_result_stays_generic_lost(kind: CliRuntimeKind) -> None:
    if kind is CliRuntimeKind.CLAUDE:
        output = _claude_stream(
            {"type": "result", "subtype": "success", "is_error": False, "result": "foreign-secret\ud800"}
        )
    else:
        output = _codex_success().replace(b"candidate only", b"foreign-secret\\ud800")
    result = parse_cli_output(kind, output, job_id="job", exit_code=0, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.LOST
    assert "foreign-secret" not in result.model_dump_json()


def test_claude_supported_core_messages_preserve_success() -> None:
    output = _claude_stream(
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "working"}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": "done"},
    )
    result = parse_cli_output(CliRuntimeKind.CLAUDE, output, job_id="job", exit_code=0, limits=CliLimits())
    assert result.status is DelegatedAgentJobStatus.SUCCEEDED


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["none", "digest", "kind", "version", "job", "receipt-only"])
async def test_cancellation_before_observation_requires_exact_retained_launch(mismatch: str) -> None:
    request, job = _identity(CliRuntimeKind.CODEX)
    spec = build_cli_launch_spec(
        CliRuntimeKind.CODEX,
        executable="/opt/codex",
        model="model",
        request=request,
        job=job,
        workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
        limits=CliLimits(),
    )
    if mismatch == "kind":
        spec = replace(spec, kind=CliRuntimeKind.CLAUDE)
    elif mismatch == "version":
        spec = replace(spec, cli_version="unreviewed")
    elif mismatch == "job":
        spec = replace(spec, job=job.model_copy(update={"request_id": "other"}))
    receipt = CliContainmentReceipt(job, "test-only-evidence", "0" * 64 if mismatch == "digest" else spec.digest)
    expected_job = job

    class Host:
        async def launch(self, spec: object) -> None:
            del spec
            pytest.fail("Cancellation must not launch.")

        async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation | None:
            del job
            pytest.fail("Cancellation must retain its own exact admission evidence.")

        async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
            assert job == expected_job
            if mismatch == "receipt-only":
                return cast("CliCancellationObservation", cast("object", receipt))
            return CliCancellationObservation(spec, receipt)

    runtime = CodexCliRuntime(executable="/opt/codex", model="changed", job_roots="/changed", host=Host())
    if mismatch == "none":
        await runtime.cancel(job, request=request)
    else:
        with pytest.raises(CliContainmentUncertainError):
            await runtime.cancel(job, request=request)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(CliRuntimeKind))
@pytest.mark.parametrize("operation", ["poll", "cancel"])
@pytest.mark.parametrize(
    "substitution", ["none", "prompt", "stdin", "artifact_id", "digest", "media_type", "size", "classification"]
)
async def test_reconstructed_coordinator_correlates_original_request(
    kind: CliRuntimeKind, operation: str, substitution: str
) -> None:
    request = cli_request(kind)
    artifact = ArtifactRef(
        artifact_id="original-input",
        digest="sha256:" + "a" * 64,
        media_type="text/plain",
        size=12,
        classification="internal",
    )
    request = request.model_copy(update={"input_artifacts": (artifact,)})
    launches: list[CliLaunchSpec] = []
    polls: list[DelegatedAgentJobRef] = []
    cancellations: list[DelegatedAgentJobRef] = []
    observed_spec: CliLaunchSpec | None = None
    stdout = (
        _codex_success()
        if kind is CliRuntimeKind.CODEX
        else _claude_stream({"type": "result", "subtype": "success", "is_error": False, "result": "candidate only"})
    )

    class Host:
        async def launch(self, spec: CliLaunchSpec) -> None:
            launches.append(spec)
            assert len(launches) == 1, "Recovery must never launch."

        async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation:
            polls.append(job)
            assert observed_spec is not None
            assert observed_spec.job == job
            receipt = CliContainmentReceipt(job, "test-retained-evidence", observed_spec.digest)
            return CliExitObservation(observed_spec, receipt, 0, stdout)

        async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
            cancellations.append(job)
            assert observed_spec is not None
            assert observed_spec.job == job
            receipt = CliContainmentReceipt(job, "test-retained-evidence", observed_spec.digest)
            return CliCancellationObservation(observed_spec, receipt)

    host = Host()
    runtime_type = CodexCliRuntime if kind is CliRuntimeKind.CODEX else ClaudeCliRuntime
    original = runtime_type(
        executable=f"/opt/agents/{kind}",
        model="original",
        job_roots="/jobs",
        host=host,
        owner_admission=InertOwnerAdmission(),
    )
    store = InMemoryDelegatedAgentJobStore()
    first = DelegatedAgentCoordinator(runtimes={original.name: original}, store=store)
    job = await first.submit(request)
    observed_request = request
    if substitution == "prompt":
        observed_request = request.model_copy(update={"prompt": "consistently substituted prompt"})
    elif substitution not in {"none", "stdin"}:
        replacements: dict[str, str | int] = {
            "artifact_id": "substituted-input",
            "digest": "sha256:" + "b" * 64,
            "media_type": "application/json",
            "size": 13,
            "classification": "public",
        }
        observed_request = request.model_copy(
            update={"input_artifacts": (artifact.model_copy(update={substitution: replacements[substitution]}),)}
        )
    observed_stdin = (
        b"consistently substituted stdin" if substitution == "stdin" else observed_request.prompt.encode("utf-8")
    )
    observed_spec = replace(launches[0], request=observed_request, stdin=observed_stdin)
    restarted = runtime_type(
        executable=f"/changed/{kind}",
        model="current-default",
        job_roots="/changed",
        limits=CliLimits(max_stdout_bytes=1, max_record_bytes=1, wall_seconds=1),
        host=host,
    )
    recovered = DelegatedAgentCoordinator(runtimes={restarted.name: restarted}, store=store)

    if operation == "poll":
        result = await recovered.refresh(job.job_id)
        assert result.status is (
            DelegatedAgentJobStatus.SUCCEEDED if substitution == "none" else DelegatedAgentJobStatus.LOST
        )
        assert polls == [job]
    else:
        assert polls == []
    if substitution != "none":
        before = await store.get(job.job_id)
        with pytest.raises(CliContainmentUncertainError):
            await recovered.cancel(job.job_id)
        assert await store.get(job.job_id) == before
        assert cancellations == [job]
    elif operation == "cancel":
        assert await recovered.cancel(job.job_id)
        settled = await store.get(job.job_id)
        assert settled is not None
        assert settled.status is DelegatedAgentJobStatus.CANCELLED
        assert cancellations == [job]
    assert polls == ([job] if operation == "poll" else [])
    assert launches[0].request == request
    assert len(launches) == 1
