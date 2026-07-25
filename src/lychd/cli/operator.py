"""Click adapters for the compact read/actuate operator surface."""

from __future__ import annotations

import json

import click

from lychd.system.operator import (
    InventoryReport,
    OperatorAction,
    OperatorError,
    OperatorTarget,
    build_operator_services,
)

_TARGET_CHOICE = click.Choice([target.value for target in OperatorTarget], case_sensitive=False)
_ACTUATION_TARGET_CHOICE = click.Choice(
    [
        OperatorTarget.SYSTEM.value,
        OperatorTarget.STORAGE.value,
        OperatorTarget.ANIMATORS.value,
    ],
    case_sensitive=False,
)


def _target(value: str) -> OperatorTarget:
    return OperatorTarget(value.lower())


def _render_status(report: InventoryReport) -> None:
    click.echo(f"LychD: {report.summary.value.upper()}")
    for item in report.items:
        detail = f" — {item.detail}" if item.detail else ""
        click.echo(f"  {item.state.value.upper():8} {item.name}{detail}")
        for key, value in item.attributes:
            if value:
                click.echo(f"           {key}: {value}")
    if report.warnings:
        click.echo("WARNINGS")
        for warning in report.warnings:
            click.echo(f"  • {warning}")


@click.command(name="status", help="Show installation, runtime, storage, and readiness truth.")
@click.argument("target", required=False, type=_TARGET_CHOICE, default=OperatorTarget.SYSTEM.value)
@click.option("--json", "as_json", is_flag=True, help="Emit stable machine-readable JSON.")
def status(target: str, *, as_json: bool) -> None:
    """Render one read-only status projection."""
    report = build_operator_services().inventory.inspect(_target(target))
    if as_json:
        click.echo(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        _render_status(report)


def _act(action: OperatorAction, target: str) -> None:
    try:
        result = build_operator_services().control.execute(action, _target(target))
    except (OperatorError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    units = f" ({', '.join(result.units)})" if result.units else ""
    detail = f": {result.detail}" if result.detail else ""
    click.echo(f"{action.value.capitalize()} complete via {result.authority.value}{units}{detail}")


@click.command(name="start", help="Start the system or a safely supported target.")
@click.argument("target", required=False, type=_ACTUATION_TARGET_CHOICE, default=OperatorTarget.SYSTEM.value)
def start(target: str) -> None:
    """Start through the proven Vessel/direct authority boundary."""
    _act(OperatorAction.START, target)


@click.command(name="stop", help="Stop the system or a safely supported target.")
@click.argument("target", required=False, type=_ACTUATION_TARGET_CHOICE, default=OperatorTarget.SYSTEM.value)
def stop(target: str) -> None:
    """Stop through the proven Vessel/direct authority boundary."""
    _act(OperatorAction.STOP, target)


@click.command(name="logs", help="Read bounded logs for exact LychD-owned runtime targets.")
@click.argument("target", required=False, type=_TARGET_CHOICE, default=OperatorTarget.SYSTEM.value)
@click.option("--lines", type=click.IntRange(min=1, max=10_000), default=100, show_default=True)
def logs(target: str, *, lines: int) -> None:
    """Render one bounded, non-following journal tail."""
    try:
        read = build_operator_services().journal.read(_target(target), lines=lines)
    except (OperatorError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(read.content, nl=not read.content.endswith("\n"))
