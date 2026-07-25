"""Human-facing adapter for the staged ``lychd del`` lifecycle."""

from __future__ import annotations

import shlex
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import click
import structlog

from lychd.cli.host_topology import (
    HOST_TIER_ORDER,
    HostTier,
    HostTopology,
    PathNode,
    build_path_trie,
    display_path,
    path_children,
)
from lychd.system.services.lifecycle import (
    DELETION_STAGE_ORDER,
    DeletionAction,
    DeletionDisposition,
    DeletionOutcome,
    DeletionPlan,
    DeletionResult,
    LifecycleError,
    build_deletion_services,
)

if TYPE_CHECKING:
    from rich.text import Text
    from rich.tree import Tree

    from lychd.system.services.lifecycle import PrivilegedHandoff

logger = structlog.get_logger(__name__)

_DELETION_STYLES = {
    DeletionDisposition.WOULD_APPLY: "bold yellow",
    DeletionDisposition.REQUIRES_ROOT: "bold magenta",
    DeletionDisposition.PRESERVE: "bold green",
    DeletionDisposition.SATISFIED: "bold green",
    DeletionDisposition.BLOCKED: "bold red",
}
_DELETION_PRIORITY = {
    DeletionDisposition.SATISFIED: 0,
    DeletionDisposition.PRESERVE: 1,
    DeletionDisposition.WOULD_APPLY: 2,
    DeletionDisposition.REQUIRES_ROOT: 3,
    DeletionDisposition.BLOCKED: 4,
}


def _render_plan(plan: DeletionPlan) -> None:
    """Render every deletion jurisdiction in deterministic stage order."""
    topology = HostTopology.current()
    click.echo()
    click.echo(f"DELETION PLAN  {plan.fingerprint[:12]}")
    for stage in DELETION_STAGE_ORDER:
        actions = plan.actions_for(stage)
        if not actions:
            continue
        click.echo()
        click.echo(stage.value.upper())
        _render_stage(actions, topology=topology)

    counts = Counter(action.disposition for action in plan.actions)
    click.echo()
    click.echo(
        "SUMMARY  "
        f"Apply {counts[DeletionDisposition.WOULD_APPLY]} · "
        f"Root {counts[DeletionDisposition.REQUIRES_ROOT]} · "
        f"Preserve {counts[DeletionDisposition.PRESERVE]} · "
        f"Blocked {counts[DeletionDisposition.BLOCKED]} · "
        f"Satisfied {counts[DeletionDisposition.SATISFIED]}"
    )
    if plan.handoffs:
        _render_handoffs(plan.handoffs)


def _render_stage(
    actions: tuple[DeletionAction, ...],
    *,
    topology: HostTopology,
) -> None:
    """Project absolute paths as XDG trees while retaining symbolic rows."""
    path_actions = tuple(action for action in actions if Path(action.target).is_absolute())
    symbolic_actions = tuple(action for action in actions if not Path(action.target).is_absolute())

    grouped: dict[HostTier, list[DeletionAction]] = {}
    for action in path_actions:
        grouped.setdefault(topology.tier_for(Path(action.target)), []).append(action)

    for tier in HOST_TIER_ORDER:
        tier_actions = tuple(grouped.get(tier, ()))
        if tier_actions:
            _render_deletion_tree(
                tier=tier,
                actions=tier_actions,
                topology=topology,
            )
    for action in symbolic_actions:
        _render_symbolic_action(action)


def _render_deletion_tree(
    *,
    tier: HostTier,
    actions: tuple[DeletionAction, ...],
    topology: HostTopology,
) -> None:
    """Render one stage-local path trie without merging safety stages."""
    from rich.padding import Padding
    from rich.text import Text
    from rich.tree import Tree

    from lychd.cli.base import get_console

    tier_root = topology.root(tier)
    title = Text(tier.value, style="bold")
    if tier_root is not None:
        title.append(" — ", style="dim")
        title.append(display_path(tier_root), style="bold")
    else:
        title.append(" — paths outside the canonical XDG tiers", style="dim")
    tree = Tree(title)
    path_root = build_path_trie(
        actions,
        target_of=lambda action: Path(action.target),
        relative_to=tier_root,
        compact_home=tier is not HostTier.HOST,
    )
    for node in path_children(path_root):
        _render_deletion_node(tree, node)
    get_console().print(Padding(tree, (0, 0, 0, 2), expand=False))


def _render_deletion_node(
    parent: Tree,
    node: PathNode[DeletionAction],
) -> None:
    """Render one compressed deletion path and every verdict attached to it."""
    from rich.text import Text

    labels = [node.label]
    terminal = node
    while not terminal.items:
        children = path_children(terminal)
        if len(children) != 1:
            break
        terminal = children[0]
        labels.append(terminal.label)

    path = str(Path(*labels))
    label = Text(path, style=_deletion_path_style(tuple(terminal.items)))
    if len(terminal.items) == 1:
        label.append(" — ", style="dim")
        label.append_text(_deletion_action_note(terminal.items[0]))
    branch = parent.add(label)
    if len(terminal.items) > 1:
        for action in terminal.items:
            branch.add(_deletion_action_note(action))
    for child in path_children(terminal):
        _render_deletion_node(branch, child)


def _deletion_action_note(action: DeletionAction) -> Text:
    """Render one explicit deletion verdict and its safety evidence."""
    from rich.text import Text

    style = _DELETION_STYLES[action.disposition]
    note = Text(action.disposition.value.replace("-", " ").upper(), style=style)
    note.append(" · ", style="dim")
    note.append(action.detail, style="white")
    return note


def _deletion_path_style(actions: tuple[DeletionAction, ...]) -> str:
    """Color a path by its strongest stage-local deletion verdict."""
    if not actions:
        return "bold"
    strongest = max(actions, key=lambda action: _DELETION_PRIORITY[action.disposition])
    return _DELETION_STYLES[strongest.disposition]


def _render_symbolic_action(action: DeletionAction) -> None:
    """Retain the flat grammar for units, inventories, and other symbolic targets."""
    label = action.disposition.value.replace("-", " ").upper()
    click.echo(f"  {label:13} {action.target}")
    click.echo(f"                {action.detail}")


def _render_handoffs(handoffs: tuple[PrivilegedHandoff, ...]) -> None:
    """Render exact privileged commands without executing them."""
    click.echo()
    click.echo("ROOT HANDOFF — LychD will not run these commands")
    for handoff in handoffs:
        click.echo(f"  {handoff.reason}:")
        click.echo(f"    {shlex.join(handoff.argv)}")


def _render_result(result: DeletionResult) -> None:
    """Render the terminal state of one bounded executor invocation."""
    click.echo()
    click.echo(f"DELETION {result.outcome.value.upper()}")
    if result.applied_stages:
        stages = ", ".join(stage.value for stage in result.applied_stages)
        click.echo(f"  Applied stages: {stages}")
    if result.detail:
        click.echo(f"  {result.detail}")
    if result.plan.handoffs:
        _render_handoffs(result.plan.handoffs)
        click.echo("  Run the handoff, then invoke `lychd del` again.")


@click.command(
    name="del",
    help="Permanently remove every safely owned LychD installation resource.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show the complete staged deletion plan without changing the host.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip the interactive confirmation without widening deletion authority.",
)
def delete_installation(
    *,
    dry_run: bool,
    yes: bool,
) -> None:
    """Plan, confirm, and execute the safe prefix of permanent deletion."""
    try:
        services = build_deletion_services()
        plan = services.planner.plan()
    except (LifecycleError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("⌁ Beginning the Dissolution (lychd del)...")
    _render_plan(plan)
    if dry_run:
        click.echo()
        click.echo("No changes made.")
        if plan.requires_root and plan.first_blocked_stage is None:
            click.echo(
                "Execution will quiesce owned services, retain deletion evidence, and pause for the root handoff."
            )
        elif plan.requires_root:
            click.echo("Root work is informational only until every blocker is cleared.")
        if plan.first_blocked_stage is not None:
            click.echo(f"Blocked at stage: {plan.first_blocked_stage.value}.")
            raise click.exceptions.Exit(2)
        return

    if not yes:
        click.confirm(
            "Permanently delete every safely owned resource shown above?",
            abort=True,
        )

    logger.warning(
        "lychd_deletion_started",
        plan_fingerprint=plan.fingerprint,
        requires_root=plan.requires_root,
    )
    try:
        result = services.executor.execute(plan.fingerprint)
    except (LifecycleError, OSError, ValueError) as exc:
        logger.exception(
            "lychd_deletion_failed",
            plan_fingerprint=plan.fingerprint,
            error=str(exc),
        )
        raise click.ClickException(str(exc)) from exc

    _render_result(result)
    logger.info(
        "lychd_deletion_finished",
        outcome=result.outcome.value,
        applied_stages=tuple(stage.value for stage in result.applied_stages),
    )
    if result.outcome is not DeletionOutcome.COMPLETE:
        raise click.exceptions.Exit(2)


__all__ = ("delete_installation",)
