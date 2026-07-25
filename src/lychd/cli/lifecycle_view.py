"""Concise Rich-tree presentation for lifecycle plans."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Final

from rich.text import Text
from rich.tree import Tree

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
    LifecycleAction,
    LifecycleDisposition,
    LifecycleResourceKind,
)

if TYPE_CHECKING:
    from rich.console import Console

    from lychd.system.services.lifecycle import LifecyclePlan

_HOST_DESCRIPTION: Final = "Resources outside the canonical XDG tiers."
_PATH_STYLES: Final = {
    LifecycleDisposition.WOULD_CREATE: "bold cyan",
    LifecycleDisposition.WOULD_REMOVE: "bold yellow",
    LifecycleDisposition.PRESERVE: "bold green",
    LifecycleDisposition.BLOCKED: "bold red",
}
_DISPOSITION_PRIORITY: Final = {
    LifecycleDisposition.PRESERVE: 0,
    LifecycleDisposition.WOULD_CREATE: 1,
    LifecycleDisposition.WOULD_REMOVE: 2,
    LifecycleDisposition.BLOCKED: 3,
}
_MODE_PATTERN: Final = re.compile(r"\bmode ([0-7]{4})\b")
_STRUCTURAL_PATH_STYLE: Final = "bold cyan"
_SHARED_PATH_STYLE: Final = "bold bright_blue"
_DESCRIPTION_STYLE: Final = "white"


def render_lifecycle_plan(
    *,
    plan: LifecyclePlan,
    console: Console,
    path_descriptions: Mapping[Path, str] | None = None,
    verbose: bool = False,
) -> None:
    """Render an exact plan as compact domain and filesystem trees."""
    from lychd.system import constants
    from lychd.system.attribute_docs import path_attribute_summaries

    topology = HostTopology.current()
    static_paths = {
        *constants.HOST_LAYOUT,
        *(Path(action.target) for action in plan.actions),
        constants.PATH_XDG_CACHE_HOME,
        constants.PATH_XDG_CONFIG_HOME,
        constants.PATH_XDG_DATA_HOME,
    }
    descriptions = path_attribute_summaries(constants, include=static_paths)
    canonical_roots = {
        HostTier.CODEX: constants.PATH_XDG_CONFIG_HOME,
        HostTier.CRYPT: constants.PATH_XDG_DATA_HOME,
        HostTier.FORGE: constants.PATH_XDG_CACHE_HOME,
    }
    for tier, canonical_root in canonical_roots.items():
        description = descriptions.get(canonical_root)
        tier_root = topology.root(tier)
        if description is not None and tier_root is not None:
            descriptions[tier_root] = description
    if path_descriptions is not None:
        descriptions.update(path_descriptions)
    grouped: dict[HostTier, list[LifecycleAction]] = {}
    for action in plan.actions:
        grouped.setdefault(_lifecycle_group(action, topology=topology), []).append(action)

    projected_actions: list[LifecycleAction] = []
    console.print()
    for domain in HOST_TIER_ORDER:
        actions = _visible_actions(
            actions=grouped.get(domain, ()),
            topology=topology,
            verbose=verbose,
        )
        if not actions:
            continue
        projected_actions.extend(actions)
        console.print(
            _domain_tree(
                domain=domain,
                actions=actions,
                path_descriptions=descriptions,
                topology=topology,
            )
        )
        console.print()

    console.print(_summary(tuple(projected_actions), topology=topology))


def _visible_actions(
    *,
    actions: tuple[LifecycleAction, ...] | list[LifecycleAction],
    topology: HostTopology,
    verbose: bool,
) -> tuple[LifecycleAction, ...]:
    """Hide only routine intermediate host anchors from the normal projection."""
    if verbose:
        return tuple(actions)

    return tuple(
        action
        for action in actions
        if not (
            Path(action.target) in topology.routine_anchors and action.disposition is not LifecycleDisposition.BLOCKED
        )
    )


def _domain_tree(
    *,
    domain: HostTier,
    actions: tuple[LifecycleAction, ...],
    path_descriptions: Mapping[Path, str],
    topology: HostTopology,
) -> Tree:
    """Build one domain tree whose path colors carry lifecycle disposition."""
    domain_root = topology.root(domain)
    root_actions = (
        tuple(action for action in actions if Path(action.target) == domain_root) if domain_root is not None else ()
    )
    nested_actions = (
        tuple(action for action in actions if Path(action.target) != domain_root)
        if domain_root is not None
        else actions
    )

    title = Text()
    title.append(domain.value, style="bold")
    if domain_root is not None:
        title.append(" — ", style="dim")
        title.append(
            display_path(domain_root),
            style=_path_style(
                root_actions,
                shared_anchor=domain_root in topology.shared_anchors,
            ),
        )
    else:
        title.append(" — ", style="dim")
    description = path_descriptions.get(domain_root) if domain_root is not None else _HOST_DESCRIPTION
    if description is not None:
        if domain_root is not None:
            title.append(" · ", style="dim")
        title.append(description, style=_DESCRIPTION_STYLE)
    root_state = _shared_anchor_state(root_actions) if domain_root in topology.shared_anchors else None
    if root_state is not None:
        title.append(" · ", style="dim")
        title.append(*root_state)
    tree = Tree(title)

    path_root = build_path_trie(
        nested_actions,
        target_of=lambda action: Path(action.target),
        relative_to=domain_root,
    )
    for node in path_children(path_root):
        _render_path_node(
            tree,
            node,
            path_descriptions=path_descriptions,
            topology=topology,
        )
    return tree


def _render_path_node(
    parent: Tree,
    node: PathNode[LifecycleAction],
    *,
    path_descriptions: Mapping[Path, str],
    topology: HostTopology,
) -> None:
    """Render one trie branch, compressing structural single-child prefixes."""
    labels = [node.label]
    terminal = node
    while not terminal.items:
        children = path_children(terminal)
        if len(children) != 1:
            break
        terminal = children[0]
        labels.append(terminal.label)

    branch = parent.add(
        _path_label(
            labels,
            actions=tuple(terminal.items),
            path_descriptions=path_descriptions,
            shared_anchor=bool(terminal.items) and Path(terminal.items[0].target) in topology.shared_anchors,
        )
    )
    for child in path_children(terminal):
        _render_path_node(
            branch,
            child,
            path_descriptions=path_descriptions,
            topology=topology,
        )


def _path_label(
    labels: list[str],
    *,
    actions: tuple[LifecycleAction, ...],
    path_descriptions: Mapping[Path, str],
    shared_anchor: bool = False,
) -> Text:
    """Build one safe Rich label without interpreting path or detail as markup."""
    path = str(Path(*labels))
    label = Text()
    label.append(path, style=_path_style(actions, shared_anchor=shared_anchor))
    if not actions:
        return label

    description, qualifiers = _action_note_parts(
        actions,
        path_descriptions=path_descriptions,
        shared_anchor=shared_anchor,
    )
    if description is None and not qualifiers:
        return label

    label.append(" — ", style="dim")
    if description is not None:
        label.append(description, style=_DESCRIPTION_STYLE)
    if qualifiers:
        if description is not None:
            label.append(" · ", style="dim")
        for index, (qualifier, style) in enumerate(qualifiers):
            if index:
                label.append(" · ", style="dim")
            label.append(qualifier, style=style)
    return label


def _action_note_parts(
    actions: tuple[LifecycleAction, ...],
    *,
    path_descriptions: Mapping[Path, str],
    shared_anchor: bool,
) -> tuple[str | None, tuple[tuple[str, str], ...]]:
    """Separate source-owned prose from subdued lifecycle state qualifiers."""
    description = path_descriptions.get(Path(actions[0].target))
    qualifiers: list[tuple[str, str]] = []
    if shared_anchor and (state := _shared_anchor_state(actions)) is not None:
        qualifiers.append(state)
    for action in actions:
        if action.kind is LifecycleResourceKind.MOUNT:
            qualifiers.append(("external mount kept", "dim"))
        elif action.kind is LifecycleResourceKind.RECEIPT and description is None:
            qualifiers.append(("initialization ownership receipt", "dim"))
        mode = _MODE_PATTERN.search(action.detail)
        if mode is not None:
            qualifiers.append((f"mode {mode.group(1)}", "dim"))
        if "Btrfs/No-COW" in action.detail and description is None:
            qualifiers.append(("Btrfs/No-COW when available", "dim"))
        if action.disposition is LifecycleDisposition.BLOCKED:
            qualifiers.append((action.detail, "dim"))
    return description, tuple(dict.fromkeys(qualifiers))


def _path_style(
    actions: tuple[LifecycleAction, ...],
    *,
    shared_anchor: bool = False,
) -> str:
    """Encode the strongest lifecycle disposition directly on a path."""
    if not actions:
        return _STRUCTURAL_PATH_STYLE
    disposition = _strongest_disposition(actions)
    if shared_anchor and disposition in {
        LifecycleDisposition.PRESERVE,
        LifecycleDisposition.WOULD_CREATE,
    }:
        return _SHARED_PATH_STYLE
    return _PATH_STYLES[disposition]


def _shared_anchor_state(
    actions: tuple[LifecycleAction, ...],
) -> tuple[str, str] | None:
    """Expose directory state without mistaking presence for host readiness."""
    if not actions:
        return None
    disposition = _strongest_disposition(actions)
    if disposition is LifecycleDisposition.WOULD_CREATE:
        return ("will prepare", "cyan")
    if disposition is LifecycleDisposition.PRESERVE:
        return ("present", "green")
    return None


def _strongest_disposition(actions: tuple[LifecycleAction, ...] | list[LifecycleAction]) -> LifecycleDisposition:
    """Return the one color/status represented by a rendered path node."""
    return max(actions, key=lambda action: _DISPOSITION_PRIORITY[action.disposition]).disposition


def _summary(
    actions: tuple[LifecycleAction, ...],
    *,
    topology: HostTopology,
) -> Text:
    """Count the visible colored path nodes rather than hidden planner rows."""
    nodes: dict[tuple[str, str], list[LifecycleAction]] = {}
    for action in actions:
        nodes.setdefault((_lifecycle_group(action, topology=topology).value, action.target), []).append(action)

    dispositions = {key: _strongest_disposition(node_actions) for key, node_actions in nodes.items()}
    counts = Counter(dispositions.values())
    external_mounts = sum(
        1
        for key, node_actions in nodes.items()
        if dispositions[key] is LifecycleDisposition.PRESERVE
        and any(action.kind is LifecycleResourceKind.MOUNT for action in node_actions)
    )
    shared_planned = sum(
        1
        for key, disposition in dispositions.items()
        if disposition is LifecycleDisposition.WOULD_CREATE and Path(key[1]) in topology.shared_anchors
    )
    shared_present = sum(
        1
        for key, disposition in dispositions.items()
        if disposition is LifecycleDisposition.PRESERVE and Path(key[1]) in topology.shared_anchors
    )
    creates = counts[LifecycleDisposition.WOULD_CREATE] - shared_planned
    existing = counts[LifecycleDisposition.PRESERVE] - external_mounts - shared_present

    summary = Text("PLAN   ", style="bold")
    plan_parts = [
        (f"{creates} create", "cyan"),
        (f"{existing} existing", "green"),
    ]
    if external_mounts:
        mount_label = "external mount" if external_mounts == 1 else "external mounts"
        plan_parts.append((f"{external_mounts} {mount_label}", "green"))
    if counts[LifecycleDisposition.WOULD_REMOVE]:
        plan_parts.append(
            (
                f"{counts[LifecycleDisposition.WOULD_REMOVE]} remove",
                "yellow",
            )
        )
    _append_summary_parts(summary, plan_parts)

    if shared_planned or shared_present:
        summary.append("\nSHARED ", style="bold bright_blue")
        shared_parts: list[tuple[str, str]] = []
        if shared_planned:
            shared_parts.append((f"{shared_planned} will prepare", "cyan"))
        if shared_present:
            shared_parts.append((f"{shared_present} present", "green"))
        _append_summary_parts(summary, shared_parts)

    summary.append("\nCHECK  ", style="bold")
    summary.append(
        f"{counts[LifecycleDisposition.BLOCKED]} blocked",
        style="bold red",
    )
    return summary


def _append_summary_parts(
    summary: Text,
    parts: list[tuple[str, str]],
) -> None:
    """Append one compact summary row with consistent separators."""
    for index, (value, style) in enumerate(parts):
        if index:
            summary.append(" · ", style="dim")
        summary.append(value, style=style)


def _lifecycle_group(
    action: LifecycleAction,
    *,
    topology: HostTopology,
) -> HostTier:
    """Map one lifecycle action onto its canonical XDG presentation tier."""
    if action.kind is LifecycleResourceKind.UNIT:
        return HostTier.CODEX
    return topology.tier_for(Path(action.target))
