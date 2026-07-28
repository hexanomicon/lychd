"""Private workspace allocation and creation-failure settlement."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Never

from lychd.system.descriptor_settlement import (
    DescriptorSet,
    find_settlement_outcome,
)
from lychd.system.services.scribe.workspace_settlement import (
    WorkspaceSettlementError,
    workspace_failure_ledger,
)


def allocate_workspace(parent: Path, *, parent_fd: int) -> Path:
    """Allocate one unpredictable directory through the pinned site."""
    for _attempt in range(128):
        path = parent / f".lychd-transaction-{secrets.token_hex(12)}"
        try:
            os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            continue
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent_fd)
        except BaseException as primary:  # noqa: BLE001 - mkdir may complete before adapter return
            raise_after_workspace_allocation_error(
                path,
                parent_fd=parent_fd,
                primary=primary,
            )
        return path
    message = f"Could not allocate a unique Scribe workspace below {parent}."
    raise FileExistsError(message)


def raise_after_workspace_allocation_error(
    path: Path,
    *,
    parent_fd: int,
    primary: BaseException,
) -> Never:
    """Classify a mkdir failure without adopting an un-tokened candidate."""
    recovery = workspace_failure_ledger(recovery_paths=(path,))
    try:
        os.stat(
            path.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        settled = workspace_failure_ledger()
        settled.raise_primary_after_verified_settlement(
            primary,
            outcome="unchanged",
            terminal_note=(f"Scribe verified that failed workspace allocation left {path} absent."),
        )
    except BaseException as observation_error:  # noqa: BLE001 - exact possible name is evidence
        recovery.record(primary, observation_error)
        recovery.raise_if_any(
            message=f"Could not classify failed Scribe workspace allocation at {path}.",
            outcome="recovery",
            terminal_note="",
            verified=False,
        )
    recovery.record(primary)
    recovery.raise_if_any(
        message=(
            f"Scribe workspace allocation did not return an identity token; preserving possible recovery at {path}."
        ),
        outcome="recovery",
        terminal_note="",
        verified=False,
    )
    raise primary


def raise_workspace_creation_failure(
    *,
    parent: Path,
    path: Path | None,
    primary: BaseException,
    descriptors: DescriptorSet,
    outcome: str,
    verified: bool,
) -> Never:
    """Settle all acquired workspace descriptors before surfacing creation truth."""
    settlement = find_settlement_outcome(primary)
    if settlement is not None:
        outcome = settlement.name
        verified = settlement.verified
    primary_paths = primary.recovery_paths if isinstance(primary, WorkspaceSettlementError) else ()
    retained_paths = primary_paths or ((path,) if path is not None and outcome == "workspace_retained" else ())
    cleanup = workspace_failure_ledger(recovery_paths=retained_paths)
    cleanup.record_all(descriptors.settle())
    if verified and retained_paths:
        cleanup.record(primary)
        cleanup.raise_if_any(
            message=(
                f"Scribe workspace creation retained exact recovery at "
                f"{', '.join(str(candidate) for candidate in retained_paths)}."
            ),
            outcome=outcome,
            terminal_note=(
                f"Scribe settled every descriptor after preserving the verified {outcome} outcome for {path or parent}."
            ),
            verified=True,
        )
    if verified:
        cleanup.raise_primary_after_verified_settlement(
            primary,
            outcome=outcome,
            terminal_note=(
                f"Scribe settled every descriptor after preserving the verified {outcome} outcome for {path or parent}."
            ),
        )
    cleanup.record(primary)
    cleanup.raise_if_any(
        message=f"Scribe workspace creation left indeterminate recovery below {parent}.",
        outcome="recovery",
        terminal_note="",
        verified=False,
    )
    raise primary


__all__ = (
    "allocate_workspace",
    "raise_workspace_creation_failure",
)
