"""Compact Rich projection of host-foundation evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from rich.text import Text
from rich.tree import Tree

from lychd.cli.host_topology import display_path
from lychd.system.readiness import (
    HostReadinessItem,
    HostReadinessReport,
    ReadinessSection,
    ReadinessState,
)

if TYPE_CHECKING:
    from rich.console import Console

_STATE_MARKS: Final = {
    ReadinessState.VERIFIED: ("✓", "bold green"),
    ReadinessState.PLANNED: ("◌", "bold cyan"),
    ReadinessState.OPTIONAL: ("○", "dim"),
    ReadinessState.DEGRADED: ("!", "bold yellow"),
    ReadinessState.BLOCKED: ("✗", "bold red"),
    ReadinessState.UNKNOWN: ("?", "bold yellow"),
}


def render_host_readiness(
    *,
    report: HostReadinessReport,
    console: Console,
) -> None:
    """Render stable capability groups followed by the bind-foundation verdict."""
    console.print()
    for section in ReadinessSection:
        items = tuple(item for item in report.items if item.section is section)
        if not items:
            continue
        tree = Tree(Text(section.value, style="bold"))
        for item in items:
            tree.add(_item_label(item))
        console.print(tree)
        console.print()
    console.print(_bind_verdict(report))


def render_readiness_changes(
    *,
    before: HostReadinessReport,
    after: HostReadinessReport,
    console: Console,
) -> None:
    """Render only facts changed by initialization, then the terminal verdict."""
    prior = {item.key: item for item in before.items}
    changed = tuple(item for item in after.items if prior.get(item.key) != item)
    if changed:
        console.print()
        tree = Tree(Text("AFTER INITIALIZATION", style="bold"))
        for item in changed:
            tree.add(_item_label(item))
        console.print(tree)
    console.print()
    console.print(_bind_verdict(after))


def _item_label(item: HostReadinessItem) -> Text:
    mark, state_style = _STATE_MARKS[item.state]
    label = Text()
    label.append(f"{mark} ", style=state_style)
    label.append(item.label, style="bold")
    if item.target is not None and item.section is ReadinessSection.BINDING_SITES:
        label.append(" — ", style="dim")
        label.append(display_path(item.target), style="bright_blue")
        label.append(" · ", style="dim")
    else:
        label.append(" — ", style="dim")
    label.append(item.detail, style="white")
    return label


def _bind_verdict(report: HostReadinessReport) -> Text:
    verdict = Text("BIND   ", style="bold")
    if report.ready_for_bind:
        verdict.append("✓ host foundation and binding sites ready", style="bold green")
    elif report.ready_after_init:
        verdict.append(
            "◌ host foundation ready · binding sites will be prepared",
            style="bold cyan",
        )
    else:
        verdict.append("✗ host prerequisites incomplete", style="bold red")
    return verdict


__all__ = ("render_host_readiness", "render_readiness_changes")
