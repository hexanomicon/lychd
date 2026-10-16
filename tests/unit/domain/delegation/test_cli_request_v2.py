"""Versioned request transport and inert owner-admission consumer conformance."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.delegation.cli_protocol import CliLimits, CliRuntimeKind, compile_cli_request
from lychd.domain.delegation.cli_runtime import (
    CliContainmentUncertainError,
    CliLaunchRefusedError,
    CodexCliRuntime,
)
from lychd.domain.delegation.models import (
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentRequest,
    DelegatedCliRequestV2,
    DelegatedRequest,
    decode_delegated_request,
    encode_delegated_request,
)
from lychd.domain.delegation.owner_admission import (
    OwnerAdmissionDenied,
    OwnerAdmissionGranted,
    OwnerAdmissionReason,
)
from lychd.domain.delegation.services import (
    DelegatedAgentCoordinator,
    DelegatedAgentIdempotencyConflictError,
    InMemoryDelegatedAgentJobStore,
)
from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime
from tests.support.delegated_cli import InertCliHost, InertOwnerAdmission, cli_request, substitute_spec


def _job(request: DelegatedCliRequestV2) -> DelegatedAgentJobRef:
    return DelegatedAgentJobRef(
        job_id="job",
        request_id=request.request_id,
        run_id=request.run_id,
        runtime=request.runtime,
        profile=request.profile,
    )


@pytest.mark.parametrize("kind", list(CliRuntimeKind))
def test_full_and_nested_request_roundtrip(kind: CliRuntimeKind) -> None:
    request = cli_request(kind)
    encoded = encode_delegated_request(request)
    assert decode_delegated_request(json.loads(json.dumps(encoded))) == request
    job = DelegatedAgentJob(request=request, ref=_job(request), status=DelegatedAgentJobStatus.RUNNING)
    assert DelegatedAgentJob.model_validate_json(job.model_dump_json()) == job
    assert json.loads(job.model_dump_json())["request"] == encoded
    assert compile_cli_request(request, job.ref).request == request
    with pytest.raises(ValidationError):
        request.owner_binding.task.revision = "2"
    with pytest.raises(FrozenInstanceError):
        request.cli_intent.limits.wall_seconds = 1  # type: ignore[misc]


def test_legacy_nested_json_is_literal() -> None:
    literal = (
        '{"request":{"request_id":"request","run_id":"run","step_id":"step",'
        '"runtime":"reference","profile":"read","prompt":"legacy λ","input_artifacts":[]},'
        '"ref":{"job_id":"job","request_id":"request","run_id":"run","runtime":"reference",'
        '"profile":"read"},"status":"running","result":null,"events":[]}'
    )
    assert DelegatedAgentJob.model_validate_json(literal).model_dump_json() == literal


@pytest.mark.parametrize("tag", [None, "", "lychd-delegated-cli-request@3", 2, True])
def test_unknown_discriminator_has_no_legacy_fallback(tag: object) -> None:
    raw = DelegatedAgentRequest(run_id="run", step_id="step", runtime="reference", prompt="old").model_dump(mode="json")
    raw["request_schema"] = tag
    with pytest.raises(ValueError, match=r"."):
        decode_delegated_request(raw)
    with pytest.raises(ValueError, match=r"."):
        DelegatedAgentJob.model_validate({"request": raw, "ref": _job(cli_request()), "status": "running"})


@pytest.mark.parametrize("field", ["max_stdout_bytes", "max_stderr_bytes", "max_record_bytes", "wall_seconds"])
@pytest.mark.parametrize("value", [True, 1.0, float("inf"), float("nan"), "1", 0, -1, 2**64, None])
def test_limits_are_complete_strict_bounded_integers(field: str, value: object) -> None:
    raw = encode_delegated_request(cli_request())
    intent = cast("dict[str, object]", raw["cli_intent"])
    cast("dict[str, object]", intent["limits"])[field] = value
    with pytest.raises(ValueError, match=r"."):
        decode_delegated_request(raw)
    cast("dict[str, object]", intent["limits"]).pop(field)
    with pytest.raises(ValueError, match=r"."):
        decode_delegated_request(raw)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("request_id",), "unsafe/name"),
        (("step_id",), "λ"),
        (("run_id",), "a" * 129),
        (("cli_intent", "compiler_revision"), "official-one-shot@2"),
        (("cli_intent", "cli_version"), "latest"),
        (("cli_intent", "executable"), "/opt/../cli"),
        (("cli_intent", "model"), "--flag"),
        (("cli_intent", "settings"), {}),
        (("cli_intent", "limits", "unknown"), 1),
        (("cli_intent", "workspace", "scratch"), "/jobs/one/workspace/tmp"),
        (("owner_binding", "task", "revision"), "latest"),
        (("owner_binding", "projection", "digest"), "sha256:" + "A" * 64),
        (("owner_binding", "custody", "owner_namespace"), "other@1"),
        (("owner_binding", "verification", "record_id"), "../plan"),
        (("owner_binding", "verifier_id"), "unsafe id"),
        (("positive_observation",), {}),
    ],
)
def test_closed_request_negative_shapes(path: tuple[str, ...], value: object) -> None:
    raw = encode_delegated_request(cli_request())
    target = raw
    for key in path[:-1]:
        target = cast("dict[str, object]", target[key])
    target[path[-1]] = value
    with pytest.raises(ValueError, match=r"."):
        decode_delegated_request(raw)


@pytest.mark.asyncio
async def test_replay_pins_every_mechanical_and_owner_input() -> None:
    host, owner, store = InertCliHost(), InertOwnerAdmission(), InMemoryDelegatedAgentJobStore()
    runtime = CodexCliRuntime(
        executable="/unused", model="unused", job_roots="/unused", host=host, owner_admission=owner
    )
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    request = cli_request()
    job = await coordinator.submit(request)
    assert await coordinator.submit(decode_delegated_request(encode_delegated_request(request))) == job
    for field in (
        "model",
        "executable",
        "workspace",
        "max_stdout_bytes",
        "max_stderr_bytes",
        "max_record_bytes",
        "wall_seconds",
        "task",
        "projection",
        "custody",
        "verification",
        "verifier_id",
    ):
        candidate = substitute_spec(host.launches[0], field, retain_request=False).request
        with pytest.raises(DelegatedAgentIdempotencyConflictError):
            await coordinator.submit(candidate)
    assert len(host.launches) == owner.calls == 1
    assert (await store.get(job.job_id)).request == request  # type: ignore[union-attr]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid",
    [
        "default",
        "none",
        "denied",
        "dict",
        "job",
        "request_digest",
        "intent_digest",
        "owner_binding",
        "expired",
        "future",
        "generation_bool",
        "generation_float",
        "generation_string",
        "generation_negative",
        "generation_overflow",
        "naive",
    ],
)
async def test_owner_admission_refuses_before_host(invalid: str) -> None:  # noqa: C901 - closed malformed observation matrix
    request = cli_request()
    job = _job(request)
    now = datetime(2026, 10, 15, tzinfo=UTC)
    positive = await InertOwnerAdmission(now).admit(request, job)
    raw: object = positive
    if invalid == "none":
        raw = None
    elif invalid == "denied":
        raw = OwnerAdmissionDenied(decision="denied", reason=OwnerAdmissionReason.REVOKED)
    elif invalid == "dict":
        raw = positive.model_dump(mode="json")
    elif invalid == "job":
        raw = positive.model_copy(update={"job": job.model_copy(update={"job_id": "other"})})
    elif invalid in {"request_digest", "intent_digest"}:
        raw = positive.model_copy(update={invalid: "sha256:" + "b" * 64})
    elif invalid == "owner_binding":
        raw = positive.model_copy(
            update={"owner_binding": positive.owner_binding.model_copy(update={"verifier_id": "other"})}
        )
    elif invalid == "expired":
        raw = positive.model_copy(update={"issued_at": now - timedelta(hours=2), "expires_at": now})
    elif invalid == "future":
        raw = positive.model_copy(update={"issued_at": now + timedelta(minutes=1)})
    elif invalid.startswith("generation_"):
        generations: dict[str, object] = {
            "generation_bool": True,
            "generation_float": 0.0,
            "generation_string": "0",
            "generation_negative": -1,
            "generation_overflow": 2**63,
        }
        raw = positive.model_copy(update={"generation": generations[invalid]})
    elif invalid == "naive":
        raw = positive.model_copy(update={"issued_at": now.replace(tzinfo=None)})

    class InvalidOwner:
        async def admit(self, request: DelegatedCliRequestV2, job: DelegatedAgentJobRef) -> OwnerAdmissionGranted:
            del request, job
            return cast("OwnerAdmissionGranted", raw)

    host = InertCliHost()
    runtime = CodexCliRuntime(
        executable="/unused",
        model="unused",
        job_roots="/unused",
        host=host,
        owner_admission=None if invalid == "default" else InvalidOwner(),
        clock=lambda: now,
    )
    with pytest.raises(CliLaunchRefusedError):
        await runtime.start(request, job)
    assert host.launches == host.polls == host.cancellations == []


@pytest.mark.asyncio
async def test_expiry_does_not_require_new_owner_admission_for_lookup_or_cancellation() -> None:
    request = cli_request()
    job = _job(request)
    now = datetime(2026, 10, 15, tzinfo=UTC)
    owner, host = InertOwnerAdmission(now), InertCliHost()
    original = CodexCliRuntime(
        executable="/unused", model="unused", job_roots="/unused", host=host, owner_admission=owner, clock=lambda: now
    )
    await original.start(request, job)
    recovered = CodexCliRuntime(
        executable="/changed",
        model="changed",
        job_roots="/changed",
        host=host,
        limits=CliLimits(wall_seconds=1),
        clock=lambda: now + timedelta(days=2),
    )
    result = await recovered.poll(job, request=request)
    assert result is not None
    assert result.status is DelegatedAgentJobStatus.SUCCEEDED
    await recovered.cancel(job, request=request)
    assert owner.calls == len(host.launches) == 1
    assert host.polls == host.cancellations == [job]


@pytest.mark.asyncio
async def test_legacy_start_and_reference_v2_refuse_before_host() -> None:
    host = InertCliHost()
    runtime = CodexCliRuntime(executable="/unused", model="unused", job_roots="/unused", host=host)
    legacy = DelegatedAgentRequest(run_id="run", step_id="step", runtime="codex", prompt="legacy")
    with pytest.raises(CliLaunchRefusedError):
        await runtime.start(
            legacy, DelegatedAgentJobRef(job_id="job", request_id=legacy.request_id, run_id="run", runtime="codex")
        )
    assert host.launches == []
    with pytest.raises(ValueError, match="refuses"):
        await ReferenceDelegatedAgentRuntime().start(cli_request(), _job(cli_request()))


@pytest.mark.parametrize("seconds", [0, -1, 86_401])
def test_admission_validity_window_is_bounded(seconds: int) -> None:
    now = datetime(2026, 10, 15, tzinfo=UTC)
    request = cli_request()
    with pytest.raises(ValidationError):
        OwnerAdmissionGranted(
            decision="admitted",
            job=_job(request),
            request_digest="sha256:" + "a" * 64,
            intent_digest="sha256:" + "a" * 64,
            owner_binding=request.owner_binding,
            admission_id="admission",
            issued_at=now,
            expires_at=now + timedelta(seconds=seconds),
            generation=0,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(CliRuntimeKind))
@pytest.mark.parametrize("operation", ["poll", "cancel"])
@pytest.mark.parametrize(
    "substitution",
    [
        "model",
        "executable",
        "argv",
        "environment",
        "workspace",
        "max_stdout_bytes",
        "max_stderr_bytes",
        "max_record_bytes",
        "wall_seconds",
        "task",
        "projection",
        "custody",
        "verification",
        "verifier_id",
    ],
)
async def test_full_retained_spec_rejects_consistent_host_substitution(
    kind: CliRuntimeKind,
    operation: str,
    substitution: str,
) -> None:
    from lychd.domain.delegation.cli_runtime import ClaudeCliRuntime

    host, owner, store = InertCliHost(), InertOwnerAdmission(), InMemoryDelegatedAgentJobStore()
    runtime_type = CodexCliRuntime if kind is CliRuntimeKind.CODEX else ClaudeCliRuntime
    original = runtime_type(executable="/unused", model="unused", job_roots="/unused", host=host, owner_admission=owner)
    coordinator = DelegatedAgentCoordinator(runtimes={original.name: original}, store=store)
    job = await coordinator.submit(cli_request(kind))
    spec = host.launches[0]
    host.observed = substitute_spec(spec, substitution)
    if substitution not in {"task", "projection", "custody", "verification", "verifier_id"}:
        assert host.observed.request == spec.request
        assert host.observed.stdin == spec.stdin
    recovered = runtime_type(executable="/changed", model="changed", job_roots="/changed", host=host)
    coordinator = DelegatedAgentCoordinator(runtimes={recovered.name: recovered}, store=store)
    before = await store.get(job.job_id)
    if operation == "poll":
        settled = await coordinator.refresh(job.job_id)
        assert settled.status is DelegatedAgentJobStatus.LOST
    else:
        assert host.polls == []
        with pytest.raises(CliContainmentUncertainError):
            await coordinator.cancel(job.job_id)
        assert await store.get(job.job_id) == before
    assert len(host.launches) == owner.calls == 1


@pytest.mark.parametrize(
    "path",
    [
        ("request_id",),
        ("request_schema",),
        ("profile",),
        ("input_artifacts",),
        ("cli_intent",),
        ("owner_binding",),
        *(
            ("cli_intent", key)
            for key in ("compiler_revision", "cli_version", "executable", "model", "workspace", "limits")
        ),
        *(("cli_intent", "workspace", key) for key in ("job_root", "workspace", "scratch", "artifacts")),
        *(("owner_binding", key) for key in ("task", "projection", "custody", "verification", "verifier_id")),
        *(("owner_binding", "task", key) for key in ("owner_namespace", "record_id", "revision", "digest")),
    ],
)
def test_v2_inputs_are_required_without_default_backfill(path: tuple[str, ...]) -> None:
    raw = encode_delegated_request(cli_request())
    target = raw
    for key in path[:-1]:
        target = cast("dict[str, object]", target[key])
    target.pop(path[-1])
    with pytest.raises(ValueError, match=r"."):
        decode_delegated_request(raw)


@pytest.mark.asyncio
async def test_valid_owner_still_has_refusing_default_physical_host() -> None:
    request = cli_request()
    job = _job(request)
    runtime = CodexCliRuntime(
        executable="/unused", model="unused", job_roots="/unused", owner_admission=InertOwnerAdmission()
    )
    with pytest.raises(CliLaunchRefusedError, match="Coffin"):
        await runtime.start(request, job)
    result = await runtime.poll(job, request=request)
    assert result is not None
    assert result.status is DelegatedAgentJobStatus.LOST
    with pytest.raises(CliContainmentUncertainError):
        await runtime.cancel(job, request=request)


def test_instance_copy_cannot_bypass_retained_request_validation() -> None:
    request = cli_request()
    forged_limits = replace(request.cli_intent.limits)
    object.__setattr__(forged_limits, "wall_seconds", True)
    malformed = request.model_copy(
        update={"cli_intent": request.cli_intent.model_copy(update={"limits": forged_limits})}
    )
    with pytest.raises(ValueError, match="strict integers"):
        encode_delegated_request(malformed)


@pytest.mark.asyncio
async def test_numeric_host_spec_substitution_is_not_integer_identity() -> None:
    request = cli_request()
    request = request.model_copy(
        update={"cli_intent": request.cli_intent.model_copy(update={"limits": CliLimits(wall_seconds=1)})}
    )
    job = _job(request)
    spec = compile_cli_request(request, job)
    forged_limits = replace(spec.limits)
    object.__setattr__(forged_limits, "wall_seconds", 1.0)
    observed = replace(spec, limits=forged_limits)
    assert observed == spec  # Python value equality alone conflates integer and floating-point intent.
    assert observed.digest != spec.digest
    host = InertCliHost()
    host.observed = observed
    runtime = CodexCliRuntime(executable="/unused", model="unused", job_roots="/unused", host=host)
    result = await runtime.poll(job, request=request)
    assert result is not None
    assert result.status is DelegatedAgentJobStatus.LOST
    with pytest.raises(CliContainmentUncertainError):
        await runtime.cancel(job, request=request)
    assert host.launches == []


_FORGED_CASES = [
    "binding",
    "reference",
    "intent",
    "limits",
    "workspace",
    "artifact_size",
    "artifact_digest",
    "artifact_extra",
    "intent_extra",
    "reference_extra",
    "request_extra",
    "legacy_null_tag",
]


def _forged_request(case: str) -> DelegatedRequest:
    request = cli_request()
    if case == "legacy_null_tag":
        return DelegatedAgentRequest(run_id="run", step_id="step", runtime="codex", prompt="legacy").model_copy(
            update={"request_schema": None}
        )
    if case == "request_extra":
        return request.model_copy(update={"settings": {"unexpected": True}})
    if case in {"binding", "reference", "reference_extra"}:
        reference = request.owner_binding.task.model_copy(
            update={
                "settings" if case == "reference_extra" else "revision": {} if case == "reference_extra" else "latest"
            }
        )
        binding: object = request.owner_binding.model_copy(update={"task": reference})
        if case == "reference":
            binding = {**request.owner_binding.model_dump(mode="python"), "task": reference}
        return request.model_copy(update={"owner_binding": binding})
    if case.startswith("artifact_"):
        artifact = ArtifactRef(artifact_id="input", digest="sha256:" + "a" * 64, media_type="text/plain", size=1)
        updates: dict[str, object] = {
            "artifact_size": {"size": -1},
            "artifact_digest": {"digest": "invalid"},
            "artifact_extra": {"settings": {"unexpected": True}},
        }
        return request.model_copy(
            update={"input_artifacts": (artifact.model_copy(update=cast("dict[str, object]", updates[case])),)}
        )
    intent = request.cli_intent
    if case == "intent":
        intent = intent.model_copy(update={"compiler_revision": "unsupported"})
    elif case == "intent_extra":
        intent = intent.model_copy(update={"settings": {"unexpected": True}})
    elif case == "limits":
        limits = replace(intent.limits)
        object.__setattr__(limits, "wall_seconds", True)
        intent = intent.model_copy(update={"limits": limits})
    else:
        workspace = replace(intent.workspace)
        object.__setattr__(workspace, "scratch", workspace.workspace)
        intent = intent.model_copy(update={"workspace": workspace})
    return request.model_copy(update={"cli_intent": intent})


def _exercise_forged_boundary(malformed: DelegatedRequest, boundary: str) -> None:
    if boundary == "decode_instance":
        decode_delegated_request(malformed)
    elif boundary == "decode_dictionary":
        decode_delegated_request(dict(malformed.__dict__))
    elif boundary == "encode":
        encode_delegated_request(malformed)
    else:
        DelegatedAgentJob.model_validate({"request": malformed, "ref": _job(cli_request()), "status": "running"})


@pytest.mark.parametrize("case", _FORGED_CASES)
@pytest.mark.parametrize("boundary", ["decode_instance", "decode_dictionary", "encode", "nested_job"])
def test_repair1_codec_revalidates_complete_forged_model_contents(case: str, boundary: str) -> None:
    malformed = _forged_request(case)
    with pytest.raises(ValueError, match=r"."):
        _exercise_forged_boundary(malformed, boundary)


def test_repair1_raw_encoded_request_rejects_forged_nested_binding() -> None:
    request = cli_request()
    raw = encode_delegated_request(request)
    raw["owner_binding"] = request.owner_binding.model_copy(
        update={"task": request.owner_binding.task.model_copy(update={"revision": "latest"})}
    )
    with pytest.raises(ValueError, match="immutable"):
        decode_delegated_request(raw)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _FORGED_CASES)
async def test_repair1_forged_request_refuses_before_owner_or_host(case: str) -> None:
    host, owner = InertCliHost(), InertOwnerAdmission()
    runtime = CodexCliRuntime(
        executable="/unused", model="unused", job_roots="/unused", host=host, owner_admission=owner
    )
    with pytest.raises(ValueError, match=r"."):
        await runtime.start(_forged_request(case), _job(cli_request()))
    assert owner.calls == 0
    assert host.launches == host.polls == host.cancellations == []


def _admission_at(issued: datetime, expires: datetime) -> OwnerAdmissionGranted:
    request = cli_request()
    return OwnerAdmissionGranted(
        decision="admitted",
        job=_job(request),
        request_digest="sha256:" + "a" * 64,
        intent_digest="sha256:" + "a" * 64,
        owner_binding=request.owner_binding,
        admission_id="inert",
        issued_at=issued,
        expires_at=expires,
        generation=0,
    )


def test_repair1_dst_fallback_window_exceeds_one_day_of_instants() -> None:
    zone = ZoneInfo("Europe/Bratislava")
    issued = datetime(2026, 10, 24, 12, tzinfo=zone)
    expires = datetime(2026, 10, 25, 12, tzinfo=zone)
    assert (expires.astimezone(UTC) - issued.astimezone(UTC)).total_seconds() == 90_000
    with pytest.raises(ValueError, match="one day"):
        _admission_at(issued, expires)


def test_repair1_fold_expiry_is_compared_by_utc_instant() -> None:
    zone = ZoneInfo("Europe/Bratislava")
    admitted = _admission_at(
        datetime(2026, 10, 25, 2, tzinfo=zone, fold=0), datetime(2026, 10, 25, 2, 45, tzinfo=zone, fold=0)
    )
    assert not admitted.is_current(datetime(2026, 10, 25, 2, 15, tzinfo=zone, fold=1))


@pytest.mark.asyncio
async def test_repair1_fold_expired_admission_has_zero_host_calls() -> None:
    request = cli_request()
    job = _job(request)
    zone = ZoneInfo("Europe/Bratislava")
    issued = datetime(2026, 10, 25, 2, tzinfo=zone, fold=0)
    expires = datetime(2026, 10, 25, 2, 45, tzinfo=zone, fold=0)
    positive = await InertOwnerAdmission(issued).admit(request, job)
    positive = positive.model_copy(update={"expires_at": expires})

    class Owner:
        async def admit(self, request: DelegatedCliRequestV2, job: DelegatedAgentJobRef) -> OwnerAdmissionGranted:
            del request, job
            return positive

    host = InertCliHost()
    runtime = CodexCliRuntime(
        executable="/unused",
        model="unused",
        job_roots="/unused",
        host=host,
        owner_admission=Owner(),
        clock=lambda: datetime(2026, 10, 25, 2, 15, tzinfo=zone, fold=1),
    )
    with pytest.raises(CliLaunchRefusedError):
        await runtime.start(request, job)
    assert host.launches == host.polls == host.cancellations == []


def test_repair1_valid_non_utc_admission_control() -> None:
    zone = ZoneInfo("Europe/Bratislava")
    admitted = _admission_at(
        datetime(2026, 10, 25, 2, tzinfo=zone, fold=0), datetime(2026, 10, 25, 2, 45, tzinfo=zone, fold=0)
    )
    assert admitted.is_current(datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0))
    assert admitted.is_current(datetime(2026, 10, 25, 0, 30, tzinfo=UTC))


def test_repair1_copied_admission_instants_remain_fail_closed() -> None:
    zone = ZoneInfo("Europe/Bratislava")
    issued = datetime(2026, 10, 25, 2, tzinfo=zone, fold=0)
    expires = datetime(2026, 10, 25, 2, 45, tzinfo=zone, fold=0)
    admitted = _admission_at(issued, expires).model_copy(update={"issued_at": issued, "expires_at": expires})
    assert not admitted.is_current(datetime(2026, 10, 25, 2, 15, tzinfo=zone, fold=1))
    naive = admitted.model_copy(update={"issued_at": issued.replace(tzinfo=None)})
    assert not naive.is_current(datetime(2026, 10, 25, 0, 30, tzinfo=UTC))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(CliRuntimeKind))
@pytest.mark.parametrize("extra", ["none", "grant", "binding", "reference", "job", "raw_job", "raw_reference"])
async def test_repair2_closed_positive_observation_runtime_matrix(kind: CliRuntimeKind, extra: str) -> None:
    from lychd.domain.delegation.cli_runtime import ClaudeCliRuntime

    request = cli_request(kind)
    job = _job(request)
    positive = await InertOwnerAdmission().admit(request, job)
    if extra == "grant":
        positive = positive.model_copy(update={"settings": {}})
    elif extra == "binding":
        positive = positive.model_copy(
            update={"owner_binding": positive.owner_binding.model_copy(update={"settings": {}})}
        )
    elif extra in {"reference", "raw_reference"}:
        reference: object = positive.owner_binding.task.model_copy(update={"settings": {}})
        if extra == "raw_reference":
            reference = {**positive.owner_binding.task.model_dump(mode="python"), "settings": {}}
        positive = positive.model_copy(
            update={"owner_binding": positive.owner_binding.model_copy(update={"task": reference})}
        )
    elif extra in {"job", "raw_job"}:
        copied_job: object = positive.job.model_copy(update={"settings": {}})
        if extra == "raw_job":
            copied_job = {**positive.job.model_dump(mode="python"), "settings": {}}
        positive = positive.model_copy(update={"job": copied_job})

    class Owner:
        async def admit(self, request: DelegatedCliRequestV2, job: DelegatedAgentJobRef) -> OwnerAdmissionGranted:
            del request, job
            return positive

    host = InertCliHost()
    runtime_type = CodexCliRuntime if kind is CliRuntimeKind.CODEX else ClaudeCliRuntime
    runtime = runtime_type(
        executable="/unused", model="unused", job_roots="/unused", host=host, owner_admission=Owner()
    )
    if extra == "none":
        await runtime.start(request, job)
        assert len(host.launches) == 1
    else:
        with pytest.raises(CliLaunchRefusedError):
            await runtime.start(request, job)
        assert host.launches == host.polls == host.cancellations == []
