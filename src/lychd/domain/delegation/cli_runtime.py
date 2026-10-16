"""Shared one-shot CLI supervision through a trusted host port, closed by default.

There is deliberately no subprocess implementation or runtime registration here.
The host owns live evidence, atomic durable launch ownership, resource enforcement,
Gate admission/revocation, bounded capture, and complete-process-tree settlement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from lychd.domain.delegation.cli_protocol import (
    CliLaunchSpec,
    CliLimits,
    CliRuntimeKind,
    compile_cli_request,
    parse_cli_output,
    reviewed_cli_version,
    validate_cli_path,
)
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentResult,
    DelegatedCliRequestV2,
    DelegatedRequest,
    cli_intent_digest,
    decode_delegated_request,
    delegated_request_digest,
)
from lychd.domain.delegation.owner_admission import (
    DenyingOwnerAdmission,
    OwnerAdmissionGranted,
    OwnerAdmissionPort,
)

_MAX_EVIDENCE_ID_LENGTH = 256
_SHA256_LENGTH = 64


class CliLaunchRefusedError(RuntimeError):
    """No admitted host boundary exists; no external launch was performed."""


class CliContainmentUncertainError(RuntimeError):
    """The host cannot prove containment of this exact occurrence."""


@dataclass(frozen=True, slots=True)
class CliContainmentReceipt:
    """Trusted host reference to observed whole-job containment and Gate revocation.

    Shape is not proof. Only a trusted host may issue this after observing the full
    process tree stopped and reconciling outstanding external effects. The evidence
    must survive restart and bind the exact job and its launch specification.
    """

    job: DelegatedAgentJobRef
    evidence_id: str
    launch_digest: str

    def __post_init__(self) -> None:
        """Require bounded references to host evidence and the admitted launch."""
        if not self.evidence_id or len(self.evidence_id) > _MAX_EVIDENCE_ID_LENGTH:
            msg = "A bounded host containment evidence identity is required."
            raise ValueError(msg)
        if len(self.launch_digest) != _SHA256_LENGTH or any(
            char not in "0123456789abcdef" for char in self.launch_digest
        ):
            msg = "Containment must bind the admitted launch digest."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CliCancellationObservation:
    """Host-retained launch and exact whole-job cancellation evidence.

    The digest checks correlation only. Trusted host observation and retained admission
    evidence remain required, including when cancellation precedes the first poll.
    """

    spec: CliLaunchSpec
    containment: CliContainmentReceipt


@dataclass(frozen=True, slots=True)
class CliExitObservation:
    """Complete bounded capture linked to trusted containment evidence."""

    spec: CliLaunchSpec
    containment: CliContainmentReceipt
    exit_code: int
    stdout: bytes
    stderr: bytes = b""
    termination: Literal["exited", "timed_out", "output_limit"] = "exited"


class CliHostPort(Protocol):
    """Trusted physical boundary, never selectable or satisfiable by a model.

    Launch MUST refuse unless fresh observed ADR 09 evidence admits the exact spec,
    executable, isolated roots/config, nono series/ABI, outer service and resource
    ceilings, sole TLS Gate destination, phantom authentication bridge, per-call
    Portal authorization, and artifact quarantine. No inherited environment/auth.
    Durable exact-job ownership precedes effects; replay never submits twice.

    Wall/output limits apply while running, including stdout and stderr independently;
    overflow/timeout must revoke the Gate and contain the whole tree. An unknown launch,
    missing durable lookup, partial capture, or uncertain stop raises, never resubmits.
    """

    async def launch(self, spec: CliLaunchSpec) -> None: ...

    async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation | None:
        """Lookup by exact durable identity after restart; never recreate a process."""
        ...

    async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
        """Revoke/contain/reconcile before returning evidence, including LOST jobs."""
        ...


class RefusingCliHost:
    """Default host cannot launch, invent a lookup result, or attest cancellation."""

    async def launch(self, spec: CliLaunchSpec) -> None:
        del spec
        msg = "No admitted Coffin host or Provider Gate bridge is installed."
        raise CliLaunchRefusedError(msg)

    async def observe(self, job: DelegatedAgentJobRef) -> CliExitObservation | None:
        del job
        msg = "No durable CLI host lookup is installed."
        raise CliContainmentUncertainError(msg)

    async def cancel(self, job: DelegatedAgentJobRef) -> CliCancellationObservation:
        del job
        msg = "No host can prove whole-job CLI containment."
        raise CliContainmentUncertainError(msg)


class _CliRuntime:
    """Two protocol adapters share exact-identity supervision without local replay state."""

    kind: CliRuntimeKind

    def __init__(
        self,
        *,
        executable: str,
        model: str,
        job_roots: str,
        limits: CliLimits | None = None,
        host: CliHostPort | None = None,
        owner_admission: OwnerAdmissionPort | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        validate_cli_path(executable)
        root = validate_cli_path(job_roots)
        if str(root) == "/":
            msg = "CLI job roots cannot be the filesystem root."
            raise ValueError(msg)
        self._executable = executable
        self._model = model
        self._job_roots = str(root)
        self._limits = limits or CliLimits()
        self._host = host if host is not None else RefusingCliHost()
        self._owner_admission = owner_admission if owner_admission is not None else DenyingOwnerAdmission()
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)

    @property
    def name(self) -> str:
        return self.kind.value

    async def start(self, request: DelegatedRequest, job: DelegatedAgentJobRef) -> None:
        request = decode_delegated_request(request)
        if not isinstance(request, DelegatedCliRequestV2):
            msg = "Fresh legacy CLI starts have no retained intent or owner admission."
            raise CliLaunchRefusedError(msg)
        self._check_runtime(job)
        spec = compile_cli_request(request, job)
        observed = await self._owner_admission.admit(request, job)
        if type(observed) is not OwnerAdmissionGranted:
            msg = "Missing or denied owner admission."
            raise CliLaunchRefusedError(msg)
        try:
            admitted = OwnerAdmissionGranted.model_validate(observed)
            if (
                admitted.job != job
                or admitted.request_digest != delegated_request_digest(request)
                or admitted.intent_digest != cli_intent_digest(request)
                or admitted.owner_binding != request.owner_binding
                or not admitted.is_current(self._clock())
            ):
                msg = "Owner admission does not bind this current occurrence."
                raise CliLaunchRefusedError(msg)
        except (ValueError, TypeError, AttributeError) as exc:
            msg = "No matching current owner admission is established."
            raise CliLaunchRefusedError(msg) from exc
        await self._host.launch(spec)

    async def poll(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> DelegatedAgentResult | None:
        self._check_runtime(job)
        try:
            observed = await self._host.observe(job)
        except (CliContainmentUncertainError, OSError):
            return self._lost(job)
        if observed is None:
            return None
        return self._interpret_observation(job, observed, request=request)

    def _interpret_observation(
        self, job: DelegatedAgentJobRef, observed: CliExitObservation, *, request: DelegatedRequest
    ) -> DelegatedAgentResult:
        if not self._matching_containment(job, observed.spec, observed.containment, request=request):
            return self._lost(job)
        if observed.termination == "timed_out":
            return DelegatedAgentResult(
                job_id=job.job_id,
                status=DelegatedAgentJobStatus.TIMED_OUT,
                error="CLI exceeded its admitted wall deadline; host containment is evidenced.",
            )
        if observed.termination != "exited":
            return self._lost(job)
        limits = observed.spec.limits
        if len(observed.stderr) > limits.max_stderr_bytes:
            return parse_cli_output(self.kind, b"", job_id=job.job_id, exit_code=1, limits=limits)
        return parse_cli_output(
            self.kind,
            observed.stdout,
            job_id=job.job_id,
            exit_code=observed.exit_code,
            limits=limits,
        )

    async def cancel(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> None:
        self._check_runtime(job)
        self._check_cancellation(job, await self._host.cancel(job), request=request)

    def _check_cancellation(self, job: DelegatedAgentJobRef, observed: object, *, request: DelegatedRequest) -> None:
        if not isinstance(observed, CliCancellationObservation) or not self._matching_containment(
            job, observed.spec, observed.containment, request=request
        ):
            msg = "Host cancellation evidence does not bind the exact admitted launch."
            raise CliContainmentUncertainError(msg)

    @staticmethod
    def _lost(job: DelegatedAgentJobRef) -> DelegatedAgentResult:
        return DelegatedAgentResult(
            job_id=job.job_id,
            status=DelegatedAgentJobStatus.LOST,
            error="Host observation could not establish the exact bounded CLI outcome; containment still requires reconciliation.",
        )

    def _check_runtime(self, job: DelegatedAgentJobRef) -> None:
        if job.runtime != self.name:
            msg = "CLI runtime identity mismatch."
            raise ValueError(msg)

    def _matching_containment(
        self,
        job: DelegatedAgentJobRef,
        spec: CliLaunchSpec,
        receipt: CliContainmentReceipt,
        *,
        request: DelegatedRequest,
    ) -> bool:
        try:
            retained = decode_delegated_request(request)
            if isinstance(retained, DelegatedCliRequestV2):
                expected = compile_cli_request(retained, job)
                if spec != expected or spec.digest != expected.digest:
                    return False
            return (
                receipt.job == job
                and spec.job == job
                and spec.request == retained
                and spec.stdin == retained.prompt.encode("utf-8")
                and spec.kind is self.kind
                and spec.cli_version == reviewed_cli_version(self.kind)
                and receipt.launch_digest == spec.digest
            )
        except (ValueError, TypeError, AttributeError):
            return False


class CodexCliRuntime(_CliRuntime):
    """Official ``codex exec --json`` protocol; no admitted host ships by default."""

    kind = CliRuntimeKind.CODEX


class ClaudeCliRuntime(_CliRuntime):
    """Official bare Claude print protocol; no admitted host ships by default."""

    kind = CliRuntimeKind.CLAUDE
