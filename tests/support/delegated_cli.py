"""Inert CLI/owner conformance fixtures: no owner authority or physical containment."""

# ruff: noqa: INP001 - bounded test support uses a namespace package
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from lychd.domain.delegation.cli_protocol import (
    CliLaunchSpec,
    CliLimits,
    CliRuntimeKind,
    CliWorkspace,
    reviewed_cli_version,
)
from lychd.domain.delegation.cli_runtime import (
    CliCancellationObservation,
    CliContainmentReceipt,
    CliExitObservation,
)
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentProfile,
    DelegatedCliIntentV1,
    DelegatedCliRequestV2,
    OperatorCampaignBinding,
    OperatorCampaignReference,
    cli_intent_digest,
    delegated_request_digest,
)
from lychd.domain.delegation.owner_admission import OwnerAdmissionGranted


def cli_request(
    kind: CliRuntimeKind = CliRuntimeKind.CODEX, *, run_id: str = "run", request_id: str = "request"
) -> DelegatedCliRequestV2:
    """Provide synthetic immutable identities, never a source closure or execution permit."""

    def reference(name: str) -> OperatorCampaignReference:
        return OperatorCampaignReference(
            owner_namespace="operator-campaign@1", record_id=name, revision="1", digest="sha256:" + "a" * 64
        )

    return DelegatedCliRequestV2(
        request_schema="lychd-delegated-cli-request@2",
        request_id=request_id,
        run_id=run_id,
        step_id="delegate",
        runtime=kind.value,
        profile=DelegatedAgentProfile.READ,
        prompt="Retain λ exactly.",
        input_artifacts=(),
        cli_intent=DelegatedCliIntentV1(
            compiler_revision="official-one-shot@1",
            cli_version=reviewed_cli_version(kind),
            executable=f"/opt/agents/{kind}",
            model="original-model",
            workspace=CliWorkspace("/jobs/one", "/jobs/one/workspace", "/jobs/one/scratch", "/jobs/one/artifacts"),
            limits=CliLimits(),
        ),
        owner_binding=OperatorCampaignBinding(
            task=reference("task"),
            projection=reference("projection"),
            custody=reference("custody"),
            verification=reference("verification"),
            verifier_id="independent-verifier",
        ),
    )


class InertOwnerAdmission:
    """Echo exact consumer bindings only; perform no owner/source/authority verification."""

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now
        self.calls = 0

    async def admit(self, request: DelegatedCliRequestV2, job: DelegatedAgentJobRef) -> OwnerAdmissionGranted:
        self.calls += 1
        now = self.now if self.now is not None else datetime.now(UTC)
        return OwnerAdmissionGranted(
            decision="admitted",
            job=job,
            request_digest=delegated_request_digest(request),
            intent_digest=cli_intent_digest(request),
            owner_binding=request.owner_binding,
            admission_id="inert-conformance-only",
            issued_at=now,
            expires_at=now + timedelta(hours=1),
            generation=0,
        )


class InertCliHost:
    """Retain plain intent in memory and emit synthetic observations without any effects."""

    def __init__(self) -> None:
        self.launches: list[CliLaunchSpec] = []
        self.polls: list[DelegatedAgentJobRef] = []
        self.cancellations: list[DelegatedAgentJobRef] = []
        self.observed: CliLaunchSpec | None = None

    async def launch(self, spec: CliLaunchSpec) -> None:
        self.launches.append(spec)
        self.observed = spec

    async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation:
        self.polls.append(job)
        assert self.observed is not None
        if self.observed.kind is CliRuntimeKind.CODEX:
            stdout = (
                b'{"type":"thread.started","thread_id":"synthetic"}\n'
                b'{"type":"turn.started"}\n'
                b'{"type":"item.completed","item":{"type":"agent_message","text":"candidate only"}}\n'
                b'{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":2}}\n'
            )
        else:
            stdout = (
                b'{"type":"system","subtype":"init","session_id":"synthetic"}\n'
                b'{"type":"result","subtype":"success","is_error":false,"result":"candidate only",'
                b'"session_id":"synthetic"}\n'
            )
        return CliExitObservation(
            self.observed, CliContainmentReceipt(job, "inert-no-containment", self.observed.digest), 0, stdout
        )

    async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
        self.cancellations.append(job)
        assert self.observed is not None
        return CliCancellationObservation(
            self.observed, CliContainmentReceipt(job, "inert-no-containment", self.observed.digest)
        )


def substitute_spec(spec: CliLaunchSpec, field: str, *, retain_request: bool = True) -> CliLaunchSpec:
    """Recompute fully consistent synthetic substitutions for consumer-negative tests."""
    request = spec.request
    assert isinstance(request, DelegatedCliRequestV2)
    if field in {"task", "projection", "custody", "verification"}:
        binding = request.owner_binding
        reference = getattr(binding, field)
        request = request.model_copy(
            update={
                "owner_binding": binding.model_copy(
                    update={field: reference.model_copy(update={"digest": "sha256:" + "b" * 64})}
                )
            }
        )
        return replace(spec, request=request)
    if field == "verifier_id":
        return replace(
            spec,
            request=request.model_copy(
                update={
                    "owner_binding": request.owner_binding.model_copy(update={"verifier_id": "replacement-verifier"})
                }
            ),
        )
    if field == "environment":
        return replace(spec, environment=(*spec.environment, ("EXTRA", "substituted")))
    if field == "argv":
        return replace(spec, argv=(*spec.argv, "--substituted"))
    if field == "stdin":
        return replace(spec, stdin=b"substituted")
    intent = request.cli_intent
    if field == "model":
        intent = intent.model_copy(update={"model": "replacement-model"})
    elif field == "executable":
        intent = intent.model_copy(update={"executable": "/replacement/cli"})
    elif field == "workspace":
        intent = intent.model_copy(
            update={
                "workspace": CliWorkspace(
                    "/replacement", "/replacement/work", "/replacement/scratch", "/replacement/artifacts"
                )
            }
        )
    elif field in {"max_stdout_bytes", "max_stderr_bytes", "max_record_bytes", "wall_seconds"}:
        intent = intent.model_copy(
            update={
                "limits": replace(
                    intent.limits, **{field: intent.limits.max_stdout_bytes - 1 if field == "max_stdout_bytes" else 1}
                )
            }
        )
    else:
        raise ValueError(field)
    from lychd.domain.delegation.cli_protocol import compile_cli_request

    compiled = compile_cli_request(request.model_copy(update={"cli_intent": intent}), spec.job)
    return replace(compiled, request=request) if retain_request else compiled
