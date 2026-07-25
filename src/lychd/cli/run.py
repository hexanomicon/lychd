"""Host-owned Click projection of declarative ``lychd run`` operations."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Protocol, cast

import click
import structlog

from lychd.domain.cortex.operations import (
    RegisteredRunOperation,
    RunInputKind,
    RunInputSpec,
    RunOperationCatalog,
    RunProgressProjection,
    build_core_run_operation_catalog,
)

logger = structlog.get_logger(__name__)

type RunScalar = str | int | float | bool
type RunValue = RunScalar | tuple[RunScalar, ...] | None


@dataclass(frozen=True, kw_only=True)
class RunInvocation:
    """Validated CLI input ready for an authenticated submission transport."""

    operation: str
    values: tuple[tuple[str, RunValue], ...]

    def as_payload(self) -> dict[str, RunValue]:
        """Return a JSON-compatible operation payload."""
        return dict(self.values)


@dataclass(frozen=True, kw_only=True)
class RunSubmission:
    """Canonical identity returned after the Vessel accepts an operation."""

    run_id: str
    workflow_name: str | None = None


@dataclass(frozen=True, kw_only=True)
class RunStreamEvent:
    """One transport-neutral event suitable for basic terminal following."""

    kind: str
    data: str
    terminal: bool = False


class RunOperationClient(Protocol):
    """Authenticated submit/stream boundary implemented by a future Vessel client."""

    def submit(self, invocation: RunInvocation) -> RunSubmission:
        """Submit an admitted operation and return its canonical run identity."""
        ...

    def stream(self, run_id: str) -> Iterator[RunStreamEvent]:
        """Yield the run's observable events until its terminal event."""
        ...


class RunTransportUnavailableError(RuntimeError):
    """Raised when operation discovery exists but no authenticated transport does."""


class UnavailableRunOperationClient:
    """Honest boundary used until the Vessel exposes a Ward-governed CLI route."""

    _MESSAGE = (
        "Run operations are discoverable, but authenticated CLI submission is not wired yet. "
        "Use the Bridge until the Vessel's Ward-governed run endpoint lands."
    )

    def submit(self, invocation: RunInvocation) -> RunSubmission:  # noqa: ARG002
        """Refuse rather than bypassing Ward or constructing the ASGI app locally."""
        raise RunTransportUnavailableError(self._MESSAGE)

    def stream(self, run_id: str) -> Iterator[RunStreamEvent]:  # noqa: ARG002
        """Refuse rather than pretending process-local SSE is available."""
        raise RunTransportUnavailableError(self._MESSAGE)


type CatalogFactory = Callable[[], RunOperationCatalog]
type ClientFactory = Callable[[], RunOperationClient]


class RunOperationGroup(click.Group):
    """Lazy Click group generated solely from host-owned declarative schemas."""

    def __init__(
        self,
        *,
        catalog_factory: CatalogFactory,
        client_factory: ClientFactory,
    ) -> None:
        """Create the public ``run`` group without loading extensions or the Vessel."""
        super().__init__(
            name="run",
            help="Perform a Core or extension operation through LychD's durable Run plane.",
            no_args_is_help=True,
        )
        self._catalog_factory = catalog_factory
        self._client_factory = client_factory

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List operation names deterministically for generated help."""
        return sorted(operation.spec.name for operation in self._catalog(ctx).operations)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Project one registered schema into a host-owned Click command."""
        operation = self._catalog(ctx).get(cmd_name)
        if operation is None:
            return None
        return self._make_command(operation)

    def _catalog(self, ctx: click.Context) -> RunOperationCatalog:
        cache_key = f"{__name__}.catalog.{id(self)}"
        cached = ctx.meta.get(cache_key)
        if cached is None:
            cached = self._catalog_factory()
            ctx.meta[cache_key] = cached
        return cast("RunOperationCatalog", cached)

    def _make_command(self, operation: RegisteredRunOperation) -> click.Command:
        params = [_click_parameter(input_spec) for input_spec in operation.spec.inputs]
        if operation.spec.progress is RunProgressProjection.RUN_EVENTS:
            params.append(
                click.Option(
                    ["--follow"],
                    is_flag=True,
                    default=False,
                    help="Follow run events until the operation reaches a terminal state.",
                )
            )

        def invoke(**values: RunValue) -> None:
            follow = bool(values.pop("follow", False))
            invocation = RunInvocation(
                operation=operation.spec.name,
                values=tuple((input_spec.name, values.get(input_spec.name)) for input_spec in operation.spec.inputs),
            )
            client = self._client_factory()
            try:
                submission = client.submit(invocation)
                click.echo(f"Run {submission.run_id} accepted.")
                if follow:
                    for event in client.stream(submission.run_id):
                        click.echo(f"[{event.kind}] {event.data}")
            except RunTransportUnavailableError as exc:
                raise click.ClickException(str(exc)) from exc

        return click.Command(
            name=operation.spec.name,
            help=_operation_help(operation),
            params=params,
            callback=invoke,
        )


def build_run_command(
    *,
    catalog_factory: CatalogFactory,
    client_factory: ClientFactory = UnavailableRunOperationClient,
) -> click.Command:
    """Build the lazy public ``run`` command for registration on the root."""
    return RunOperationGroup(
        catalog_factory=catalog_factory,
        client_factory=client_factory,
    )


def load_run_operation_catalog() -> RunOperationCatalog:
    """Load extension operations, retaining Core help when settings are invalid."""
    from lychd.extensions.host import get_extensions

    try:
        return get_extensions().run_operation_catalog
    except Exception as exc:  # noqa: BLE001 - command discovery is a recovery surface
        logger.warning(
            "run_catalog_extensions_unavailable",
            error_type=type(exc).__name__,
        )
        return build_core_run_operation_catalog()


def _click_parameter(input_spec: RunInputSpec) -> click.Parameter:
    """Translate one inert input schema into a host-owned Click parameter."""
    value_type: click.ParamType = {
        RunInputKind.TEXT: click.STRING,
        RunInputKind.INTEGER: click.INT,
        RunInputKind.NUMBER: click.FLOAT,
        RunInputKind.PATH: click.Path(path_type=str),
        RunInputKind.FLAG: click.BOOL,
    }[input_spec.kind]

    if input_spec.positional:
        return click.Argument(
            [input_spec.name],
            required=input_spec.required,
            nargs=-1 if input_spec.multiple else 1,
            type=value_type,
        )

    declaration = f"--{input_spec.name.replace('_', '-')}"
    if input_spec.kind is RunInputKind.FLAG:
        return click.Option(
            [declaration, input_spec.name],
            is_flag=True,
            default=False,
            help=input_spec.help,
        )
    return click.Option(
        [declaration, input_spec.name],
        required=input_spec.required,
        multiple=input_spec.multiple,
        type=value_type,
        help=input_spec.help,
    )


def _operation_help(operation: RegisteredRunOperation) -> str:
    """Render the operation's declarative execution and observation contract."""
    spec = operation.spec
    contract = "\n".join(
        (
            f"  Execution: {spec.execution.kind.value} {spec.execution.name}",
            f"  Mutation: {spec.mutation.value}",
            f"  Consent: {spec.consent.value}",
            f"  Progress: {spec.progress.value}",
            f"  Result: {spec.result.value}",
        )
    )
    sections = [spec.summary, f"\b\nContract:\n{contract}"]
    positional_inputs = tuple(input_spec for input_spec in operation.spec.inputs if input_spec.positional)
    if positional_inputs:
        inputs = "\n".join(f"  {input_spec.name.upper()}: {input_spec.help}" for input_spec in positional_inputs)
        sections.append(f"\b\nInputs:\n{inputs}")
    return "\n\n".join(sections)


__all__ = [
    "RunInvocation",
    "RunOperationCatalog",
    "RunOperationClient",
    "RunOperationGroup",
    "RunStreamEvent",
    "RunSubmission",
    "RunTransportUnavailableError",
    "UnavailableRunOperationClient",
    "build_run_command",
    "load_run_operation_catalog",
]
