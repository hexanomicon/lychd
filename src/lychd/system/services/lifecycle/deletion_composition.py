"""Production composition for the staged deletion lifecycle."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator import (
    OperatorPaths,
    ProcessRunner,
    SubprocessRunner,
    build_operator_services,
)
from lychd.system.services.lifecycle.bindings import BindingLifecycleService
from lychd.system.services.lifecycle.deletion import DeletionExecutor, DeletionPlanner
from lychd.system.services.lifecycle.deletion_checkpoint import (
    DeletionCheckpointStore,
)
from lychd.system.services.lifecycle.deletion_models import DeletionPaths
from lychd.system.services.lifecycle.deletion_storage import (
    CommandBtrfsSubvolumeProbe,
)
from lychd.system.services.lifecycle.paths import is_within, lexically_normal
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
from lychd.system.services.lifecycle.trees import ManagedTreeService
from lychd.system.services.scribe import ScribeService


@dataclass(frozen=True)
class DeletionServices:
    """One shared planner/executor graph for a CLI invocation."""

    paths: DeletionPaths
    planner: DeletionPlanner
    executor: DeletionExecutor


def build_deletion_services(
    *,
    source_checkout: Path | None = None,
    runner: ProcessRunner | None = None,
    paths: DeletionPaths | None = None,
    operator_paths: OperatorPaths | None = None,
) -> DeletionServices:
    """Compose deletion without constructing ASGI, Postgres, or an extension host.

    Explicit ``source_checkout`` wins. Otherwise the factory attests an
    editable checkout only from the imported package's real path, a matching
    ``project.name``, the canonical ``src/lychd`` layout, and a VCS marker. It
    never trusts the current working directory or the spelling of ``uv run``.
    """
    process = runner or SubprocessRunner()
    base_paths = paths or DeletionPaths.current()
    protected_source = _protected_source(
        explicit=source_checkout,
        configured=base_paths.source_checkout,
        roots=base_paths.dedicated_roots,
    )
    deletion_paths = replace(base_paths, source_checkout=protected_source)
    locations = operator_paths or OperatorPaths.current()
    _require_matching_authority(deletion_paths, locations)

    operator = build_operator_services(runner=process, paths=locations)
    systemctl = trusted_host_tool("systemctl")
    scribe = ScribeService(
        output_dir=locations.bindings,
        systemd_dir=locations.systemd_bindings,
    )
    checkpoint = DeletionCheckpointStore(
        deletion_paths.codex_root / ".lychd-del-state.json",
        codex_root=deletion_paths.codex_root,
    )
    trees = ManagedTreeService(deletion_paths.dedicated_roots)
    root_authority = LifecycleReceiptStore(deletion_paths.lifecycle_receipt)
    btrfs = trusted_host_tool("btrfs")
    planner = DeletionPlanner(
        paths=deletion_paths,
        retirement=operator.retirement,
        scribe=scribe,
        storage=operator.storage,
        subvolumes=CommandBtrfsSubvolumeProbe(
            process,
            btrfs_bin=btrfs,
        ),
        checkpoint=checkpoint,
        trees=trees,
        root_authority=root_authority,
        umount_bin=trusted_host_tool("umount"),
        btrfs_bin=btrfs,
    )
    executor = DeletionExecutor(
        planner=planner,
        retirement=operator.retirement,
        bindings=BindingLifecycleService(
            scribe,
            runner=process,
            systemctl_bin=systemctl,
        ),
        checkpoint=checkpoint,
        trees=trees,
    )
    return DeletionServices(
        paths=deletion_paths,
        planner=planner,
        executor=executor,
    )


def _protected_source(
    *,
    explicit: Path | None,
    configured: Path | None,
    roots: tuple[Path, ...],
) -> Path | None:
    """Return positively attested source provenance or protect the live package."""
    if explicit is not None and configured is not None and explicit != configured:
        msg = "Explicit and configured source-checkout provenance disagree."
        raise ValueError(msg)
    selected = explicit or configured
    if selected is not None:
        return _validate_explicit_source(selected)
    if checkout := _attest_imported_checkout():
        return checkout

    imported = Path(__file__).resolve()
    if any(is_within(imported, root) for root in roots):
        # Even without checkout provenance, deleting the running package from a
        # dedicated root would violate the source/self-preservation boundary.
        return imported
    return None


def _validate_explicit_source(path: Path) -> Path:
    """Require explicit provenance to identify one real canonical directory."""
    if not lexically_normal(path):
        msg = "Explicit source-checkout provenance must be an absolute canonical path."
        raise ValueError(msg)
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_dir():
        msg = f"Explicit source-checkout provenance is not a real directory: {path}"
        raise ValueError(msg)
    return resolved


def _attest_imported_checkout() -> Path | None:
    """Recognize the current LychD checkout without consulting the CWD."""
    imported = Path(__file__).resolve()
    for candidate in imported.parents:
        project_file = candidate / "pyproject.toml"
        source_root = candidate / "src" / "lychd"
        if (
            not project_file.is_file()
            or not source_root.is_dir()
            or not ((candidate / ".git").exists() or (candidate / ".jj").exists())
        ):
            continue
        try:
            with project_file.open("rb") as stream:
                payload: dict[str, Any] = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        project = payload.get("project")
        if (
            isinstance(project, dict)
            and cast("dict[str, object]", project).get("name") == "lychd"
            and is_within(imported, source_root.resolve())
        ):
            return candidate
    return None


def _require_matching_authority(
    deletion: DeletionPaths,
    operator: OperatorPaths,
) -> None:
    """Reject a service graph that observes different roots than it deletes."""
    mismatches: list[str] = []
    if deletion.codex_root != operator.codex_root:
        mismatches.append("Codex")
    if deletion.postgres_data != operator.storage_data:
        mismatches.append("Postgres data")
    if mismatches:
        joined = ", ".join(mismatches)
        msg = f"Deletion and operator authority disagree for: {joined}."
        raise ValueError(msg)


__all__ = ("DeletionServices", "build_deletion_services")
