"""Declarative operations exposed beneath the public ``lychd run`` verb.

An operation describes input shape, execution identity, admission requirements,
and observable projections. It never carries an executable callback: extensions
may contribute work to the living Run plane, but they may not inject arbitrary
host-side Click code through the Pulse.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Protocol

from lychd.extensions.base import ExtensionStore

_OPERATION_NAME: Final = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_INPUT_NAME: Final = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_EXECUTION_TARGET_NAME: Final = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*)*$")
_RUN_SUBMIT_SCOPE: Final = "runs:submit"
_HOST_OWNED_INPUTS: Final = frozenset({"follow", "help"})


class RunInputKind(StrEnum):
    """Scalar input kinds the host CLI knows how to parse safely."""

    TEXT = "text"
    INTEGER = "integer"
    NUMBER = "number"
    PATH = "path"
    FLAG = "flag"


class RunExecutionKind(StrEnum):
    """Host-resolved execution identities an operation may name."""

    WORKFLOW = "workflow"
    SERVICE = "service"


class RunMutationCharacteristic(StrEnum):
    """Whether admitted execution can change state beyond its durable run record."""

    READ_ONLY = "read-only"
    MAY_MUTATE = "may-mutate"


class RunConsentMode(StrEnum):
    """How Ward determines whether execution needs operator consent."""

    NONE = "none"
    POLICY = "policy"
    REQUIRED = "required"


class RunProgressProjection(StrEnum):
    """How an accepted operation exposes progress."""

    NONE = "none"
    RUN_EVENTS = "run-events"


class RunResultProjection(StrEnum):
    """Where an operation's canonical result remains observable."""

    NONE = "none"
    DURABLE_RUN_RECORD = "durable-run-record"


@dataclass(frozen=True, kw_only=True)
class RunExecutionTarget:
    """One inert workflow or service identity resolved by the living control plane."""

    kind: RunExecutionKind
    name: str

    def __post_init__(self) -> None:
        """Reject blank or ambiguous target identities at registration time."""
        if not self.name.strip():
            msg = "Run execution target requires a non-blank name."
            raise ValueError(msg)
        if _EXECUTION_TARGET_NAME.fullmatch(self.name) is None:
            msg = f"Invalid run execution target {self.name!r}; use a lower-case snake, kebab, or dotted identifier."
            raise ValueError(msg)


@dataclass(frozen=True, kw_only=True)
class RunInputSpec:
    """One declarative positional argument or long option."""

    name: str
    help: str
    kind: RunInputKind = RunInputKind.TEXT
    positional: bool = True
    required: bool = True
    multiple: bool = False

    def __post_init__(self) -> None:
        """Reject shapes Click cannot represent unambiguously."""
        if _INPUT_NAME.fullmatch(self.name) is None:
            msg = f"Invalid run input name {self.name!r}; use lower_snake_case."
            raise ValueError(msg)
        if not self.help.strip():
            msg = f"Run input {self.name!r} requires help text."
            raise ValueError(msg)
        if self.kind is RunInputKind.FLAG and self.positional:
            msg = f"Run input {self.name!r}: flags must be options."
            raise ValueError(msg)
        if self.kind is RunInputKind.FLAG and (self.required or self.multiple):
            msg = f"Run input {self.name!r}: flags cannot be required or repeated."
            raise ValueError(msg)


@dataclass(frozen=True, kw_only=True)
class RunOperationSpec:
    """A host-rendered operation contract contributed by Core or an extension."""

    name: str
    summary: str
    execution: RunExecutionTarget
    mutation: RunMutationCharacteristic
    consent: RunConsentMode
    progress: RunProgressProjection
    result: RunResultProjection
    inputs: tuple[RunInputSpec, ...] = ()
    required_scopes: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate stable names and a deterministic Click-compatible input shape."""
        if _OPERATION_NAME.fullmatch(self.name) is None:
            msg = f"Invalid run operation name {self.name!r}; use lower-kebab-case."
            raise ValueError(msg)
        if not self.summary.strip():
            msg = f"Run operation {self.name!r} requires a summary."
            raise ValueError(msg)
        if any(not scope.strip() for scope in self.required_scopes):
            msg = f"Run operation {self.name!r} contains an empty required scope."
            raise ValueError(msg)

        names: set[str] = set()
        optional_positional_seen = False
        for index, input_spec in enumerate(self.inputs):
            if input_spec.name in _HOST_OWNED_INPUTS:
                msg = f"Run operation {self.name!r} cannot reserve the host-owned {input_spec.name!r} input."
                raise ValueError(msg)
            if input_spec.name in names:
                msg = f"Run operation {self.name!r} declares duplicate input {input_spec.name!r}."
                raise ValueError(msg)
            names.add(input_spec.name)

            if not input_spec.positional:
                continue
            if optional_positional_seen and input_spec.required:
                msg = f"Run operation {self.name!r} cannot place a required argument after an optional one."
                raise ValueError(msg)
            optional_positional_seen = not input_spec.required
            later_inputs = self.inputs[index + 1 :]
            if input_spec.multiple and any(later.positional for later in later_inputs):
                msg = f"Run operation {self.name!r} must place its repeated argument last."
                raise ValueError(msg)


@dataclass(frozen=True, kw_only=True)
class RegisteredRunOperation:
    """One operation with host-assigned provenance and effective admission scopes."""

    provider_id: str
    spec: RunOperationSpec
    required_scopes: frozenset[str]


class RunOperationCatalog(Protocol):
    """Read-only catalogue projection consumed by host interfaces."""

    @property
    def operations(self) -> tuple[RegisteredRunOperation, ...]:
        """Return every registered operation."""
        ...

    def get(self, name: str) -> RegisteredRunOperation | None:
        """Return one registered operation by canonical name."""
        ...


class RunOperationStore(ExtensionStore):
    """Strict registry for Core and extension-contributed Run operations."""

    def __init__(
        self,
        *,
        current_provider: Callable[[], str],
        core_operations: tuple[RunOperationSpec, ...] = (),
    ) -> None:
        """Create a store bound to provenance and seed host-owned operations."""
        super().__init__()
        self._current_provider = current_provider
        self._operations: dict[str, RegisteredRunOperation] = {}
        for operation in core_operations:
            self._add(operation, provider_id="core")

    @property
    def operations(self) -> tuple[RegisteredRunOperation, ...]:
        """Registered operations in deterministic registration order."""
        return tuple(self._operations.values())

    def get(self, name: str) -> RegisteredRunOperation | None:
        """Return one operation by its canonical name."""
        return self._operations.get(name)

    def add(self, spec: RunOperationSpec) -> None:
        """Register an extension operation under the active provenance bracket."""
        self._require_mutable()
        self._add(spec, provider_id=self._current_provider())

    def _add(self, spec: RunOperationSpec, *, provider_id: str) -> None:
        existing = self._operations.get(spec.name)
        if existing is not None:
            msg = (
                f"Run operation {spec.name!r} from {provider_id!r} conflicts with "
                f"the operation already registered by {existing.provider_id!r}."
            )
            raise ValueError(msg)
        self._operations[spec.name] = RegisteredRunOperation(
            provider_id=provider_id,
            spec=spec,
            required_scopes=frozenset({_RUN_SUBMIT_SCOPE, *spec.required_scopes}),
        )


AGENT_RUN_OPERATION: Final = RunOperationSpec(
    name="agent",
    summary="Submit a prompt to LychD's default agent workflow.",
    execution=RunExecutionTarget(
        kind=RunExecutionKind.WORKFLOW,
        name="bridge_chat",
    ),
    mutation=RunMutationCharacteristic.MAY_MUTATE,
    consent=RunConsentMode.POLICY,
    progress=RunProgressProjection.RUN_EVENTS,
    result=RunResultProjection.DURABLE_RUN_RECORD,
    inputs=(
        RunInputSpec(
            name="prompt",
            help="The instruction or question to give the agent.",
        ),
    ),
)


def build_core_run_operation_catalog() -> RunOperationCatalog:
    """Return the settings-independent Core catalogue for degraded discovery."""
    return RunOperationStore(
        current_provider=lambda: "core",
        core_operations=(AGENT_RUN_OPERATION,),
    )


__all__ = [
    "AGENT_RUN_OPERATION",
    "RegisteredRunOperation",
    "RunConsentMode",
    "RunExecutionKind",
    "RunExecutionTarget",
    "RunInputKind",
    "RunInputSpec",
    "RunMutationCharacteristic",
    "RunOperationCatalog",
    "RunOperationSpec",
    "RunOperationStore",
    "RunProgressProjection",
    "RunResultProjection",
    "build_core_run_operation_catalog",
]
