from __future__ import annotations

from collections.abc import Iterator

from click.testing import CliRunner

from lychd.cli.run import (
    RunInvocation,
    RunStreamEvent,
    RunSubmission,
    build_run_command,
)
from lychd.domain.cortex.operations import (
    RunConsentMode,
    RunExecutionKind,
    RunExecutionTarget,
    RunInputKind,
    RunInputSpec,
    RunMutationCharacteristic,
    RunOperationSpec,
    RunProgressProjection,
    RunResultProjection,
)
from lychd.extensions.context import ExtensionContext


class RecordingRunClient:
    def __init__(self) -> None:
        self.invocations: list[RunInvocation] = []
        self.streamed: list[str] = []

    def submit(self, invocation: RunInvocation) -> RunSubmission:
        self.invocations.append(invocation)
        return RunSubmission(run_id="run_123", workflow_name="bridge_chat")

    def stream(self, run_id: str) -> Iterator[RunStreamEvent]:
        self.streamed.append(run_id)
        yield RunStreamEvent(kind="status", data="running")
        yield RunStreamEvent(kind="done", data="done", terminal=True)


def test_generated_help_discovers_operations_without_constructing_client() -> None:
    context = ExtensionContext()
    client_calls = 0

    def client_factory() -> RecordingRunClient:
        nonlocal client_calls
        client_calls += 1
        return RecordingRunClient()

    command = build_run_command(
        catalog_factory=lambda: context.run_operations,
        client_factory=client_factory,
    )
    runner = CliRunner()

    root_help = runner.invoke(command, ["--help"])
    operation_help = runner.invoke(command, ["agent", "--help"])

    assert root_help.exit_code == 0
    assert "agent" in root_help.output
    assert "default agent workflow" in root_help.output
    assert operation_help.exit_code == 0
    assert "Execution: workflow bridge_chat" in operation_help.output
    assert "Mutation: may-mutate" in operation_help.output
    assert "Consent: policy" in operation_help.output
    assert "Progress: run-events" in operation_help.output
    assert "Result: durable-run-record" in operation_help.output
    assert "PROMPT" in operation_help.output
    assert "instruction or question" in operation_help.output
    assert "--follow" in operation_help.output
    assert client_calls == 0


def test_generated_command_submits_validated_values_and_follows_events() -> None:
    context = ExtensionContext()
    operation = RunOperationSpec(
        name="render",
        summary="Render a bounded artifact.",
        execution=RunExecutionTarget(
            kind=RunExecutionKind.SERVICE,
            name="illustrator.render",
        ),
        mutation=RunMutationCharacteristic.MAY_MUTATE,
        consent=RunConsentMode.POLICY,
        progress=RunProgressProjection.RUN_EVENTS,
        result=RunResultProjection.DURABLE_RUN_RECORD,
        inputs=(
            RunInputSpec(name="subject", help="Subject to render."),
            RunInputSpec(
                name="count",
                help="Number of variants.",
                kind=RunInputKind.INTEGER,
                positional=False,
            ),
            RunInputSpec(
                name="transparent",
                help="Request a transparent background.",
                kind=RunInputKind.FLAG,
                positional=False,
                required=False,
            ),
        ),
    )
    with context.provenance("illustrator"):
        context.run_operations.add(operation)

    client = RecordingRunClient()
    command = build_run_command(
        catalog_factory=lambda: context.run_operations,
        client_factory=lambda: client,
    )

    result = CliRunner().invoke(
        command,
        ["render", "ouroboros", "--count", "2", "--transparent", "--follow"],
    )

    assert result.exit_code == 0
    assert result.output == "Run run_123 accepted.\n[status] running\n[done] done\n"
    assert client.invocations == [
        RunInvocation(
            operation="render",
            values=(
                ("subject", "ouroboros"),
                ("count", 2),
                ("transparent", True),
            ),
        )
    ]
    assert client.streamed == ["run_123"]


def test_default_transport_fails_honestly_without_vessel_submission_route() -> None:
    context = ExtensionContext()
    command = build_run_command(catalog_factory=lambda: context.run_operations)

    result = CliRunner().invoke(command, ["agent", "Awaken"])

    assert result.exit_code == 1
    assert "authenticated CLI submission is not wired yet" in result.output
    assert "Bridge" in result.output


def test_operation_without_progress_does_not_expose_follow() -> None:
    context = ExtensionContext()
    operation = RunOperationSpec(
        name="lookup",
        summary="Return one bounded lookup.",
        execution=RunExecutionTarget(
            kind=RunExecutionKind.SERVICE,
            name="catalog.lookup",
        ),
        mutation=RunMutationCharacteristic.READ_ONLY,
        consent=RunConsentMode.NONE,
        progress=RunProgressProjection.NONE,
        result=RunResultProjection.DURABLE_RUN_RECORD,
        inputs=(RunInputSpec(name="query", help="Lookup query."),),
    )
    with context.provenance("catalog"):
        context.run_operations.add(operation)
    client = RecordingRunClient()
    command = build_run_command(
        catalog_factory=lambda: context.run_operations,
        client_factory=lambda: client,
    )

    help_result = CliRunner().invoke(command, ["lookup", "--help"])
    rejected = CliRunner().invoke(command, ["lookup", "rune", "--follow"])
    accepted = CliRunner().invoke(command, ["lookup", "rune"])

    assert help_result.exit_code == 0
    assert "--follow" not in help_result.output
    assert rejected.exit_code != 0
    assert "No such option: --follow" in rejected.output
    assert accepted.exit_code == 0
    assert client.invocations == [
        RunInvocation(
            operation="lookup",
            values=(("query", "rune"),),
        )
    ]
