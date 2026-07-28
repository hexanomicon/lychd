"""Typed preparation and progress records for one Scribe transaction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from lychd.system.interruptions import iter_exception_graph
from lychd.system.services.scribe.storage import (
    AtomicMutation,
    AttestedPath,
    PathState,
    PinnedPath,
)
from lychd.system.services.scribe.workspace import TransactionWorkspace


def collect_recovery_paths(
    *errors: BaseException | None,
) -> tuple[Path, ...]:
    """Collect exact operator-visible paths across nested settlement evidence."""
    paths: list[Path] = []
    for error in errors:
        if error is None:
            continue
        for candidate in iter_exception_graph(error):
            recovery_paths: object = getattr(candidate, "recovery_paths", ())
            if not isinstance(recovery_paths, tuple):
                continue
            paths.extend(path for path in cast("tuple[object, ...]", recovery_paths) if isinstance(path, Path))
    return tuple(dict.fromkeys(paths))


@dataclass(frozen=True)
class PreparedPath:
    """One pinned target, its pre-state, staging object, and rollback name."""

    target: PinnedPath
    before: PathState | None
    staged: AttestedPath | None
    quarantine: PinnedPath


@dataclass
class PreparedCommit:
    """Pinned directories and complete per-path transaction preparations."""

    workspaces: dict[Path, TransactionWorkspace]
    sites: dict[tuple[Path, str], PreparedPath]
    authority: PreparedPath | None


def collect_workspace_recovery(
    prepared: PreparedCommit,
) -> tuple[tuple[Path, ...], tuple[BaseException, ...]]:
    """Resolve retained workspaces once without letting observation replace truth."""
    paths: list[Path] = []
    failures: list[BaseException] = []
    for workspace in prepared.workspaces.values():
        try:
            recovery_path = workspace.recovery_path()
        except BaseException as exc:  # noqa: BLE001 - lexical path remains safe evidence
            failures.append(exc)
            paths.append(workspace.path)
        else:
            paths.append(recovery_path)
    return tuple(dict.fromkeys(paths)), tuple(failures)


@dataclass
class CommitProgress:
    """Proven mutations and paths whose post-attempt state is not classifiable."""

    mutations: list[AtomicMutation] = field(default_factory=list)
    indeterminate_paths: set[Path] = field(default_factory=set)
    retain_recovery_evidence: bool = False


__all__ = (
    "CommitProgress",
    "PreparedCommit",
    "PreparedPath",
    "collect_recovery_paths",
    "collect_workspace_recovery",
)
