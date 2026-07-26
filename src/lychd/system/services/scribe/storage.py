"""Descriptor-pinned, attested atomic path transitions for Scribe."""

from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from lychd.system.atomic_paths import rename_exchange_at, rename_noreplace_at


@dataclass(frozen=True)
class PinnedPath:
    """One filename resolved only through an already pinned directory."""

    directory_fd: int
    name: str
    display: Path

    def __post_init__(self) -> None:
        """Reject values that could escape the pinned directory."""
        if self.directory_fd < 0:
            message = "Pinned path requires an open directory descriptor."
            raise ValueError(message)
        if not self.name or self.name in {".", ".."} or "/" in self.name:
            message = "Pinned path name must be one relative filename component."
            raise ValueError(message)

    def __str__(self) -> str:
        """Render the operator-facing path without using it for authority."""
        return str(self.display)


@dataclass(frozen=True)
class PathState:
    """No-follow identity, ownership, and optional regular-file content."""

    device: int
    inode: int
    mode: int
    user_id: int
    size: int
    modified_ns: int
    content: bytes | None


@dataclass(frozen=True)
class AttestedPath:
    """A pinned path plus the exact state approved during preparation."""

    path: PinnedPath
    state: PathState


@dataclass(frozen=True)
class AtomicMutation:
    """One proven live transition plus its exact quarantined rollback object."""

    target: PinnedPath
    before: PathState | None
    after: PathState | None
    quarantine: PinnedPath
    authority: bool = False


@dataclass(frozen=True)
class AtomicOutcome:
    """A proven transition and any adapter error raised after it occurred."""

    mutation: AtomicMutation
    adapter_error: BaseException | None = None


class PathDriftError(RuntimeError):
    """A concurrent path generation was restored or preserved without mutation."""


class PathStateIndeterminateError(RuntimeError):
    """An atomic attempt left state that cannot be classified safely."""

    def __init__(
        self,
        message: str,
        *,
        paths: frozenset[Path],
        cause: BaseException | None = None,
    ) -> None:
        """Retain every path whose generation can no longer be proved."""
        super().__init__(message)
        self.paths = paths
        self.cause = cause


class AtomicPathStorage:
    """Perform atomic transitions through exact pinned directory identities."""

    def replace(
        self,
        staged: AttestedPath,
        target: PinnedPath,
        *,
        expected_before: PathState | None,
        rollback_quarantine: PinnedPath,
        authority: bool = False,
    ) -> AtomicOutcome:
        """Install only the exact staged inode and bytes approved at preparation."""
        if capture_pinned_path_state(staged.path) != staged.state:
            message = f"Prepared Scribe replacement changed before commit: {staged.path}."
            raise PathDriftError(message)
        if expected_before is None:
            return self._install(
                staged.path,
                target,
                expected_after=staged.state,
                rollback_quarantine=rollback_quarantine,
                authority=authority,
            )
        return self._exchange(
            staged.path,
            target,
            source_before=staged.state,
            target_before=expected_before,
            authority=authority,
        )

    def remove(
        self,
        target: PinnedPath,
        quarantine: PinnedPath,
        *,
        expected_before: PathState,
        authority: bool = False,
    ) -> AtomicOutcome:
        """Move one exact live generation into descriptor-pinned quarantine."""
        adapter_error: BaseException | None = None
        try:
            self._rename_noreplace(target, quarantine)
        except BaseException as exc:  # noqa: BLE001 - post-call state decides whether it moved
            adapter_error = exc
        target_after, quarantine_after = self._observe_after_atomic(target, quarantine)
        if target_after is None and quarantine_after == expected_before:
            return AtomicOutcome(
                AtomicMutation(
                    target=target,
                    before=expected_before,
                    after=None,
                    quarantine=quarantine,
                    authority=authority,
                ),
                adapter_error,
            )
        if target_after == expected_before and quarantine_after is None:
            if adapter_error is not None:
                raise adapter_error
            message = "Scribe removal returned success without moving the target."
            raise self._indeterminate(message, target, quarantine)
        if target_after is None and quarantine_after is not None:
            self._restore_raced_removal(
                target,
                quarantine,
                raced_state=quarantine_after,
                cause=adapter_error,
            )
        message = f"Scribe could not prove the quarantined removal state of {target}."
        raise self._indeterminate(message, target, quarantine, cause=adapter_error)

    def restore(self, mutation: AtomicMutation) -> None:
        """Restore one proven mutation without overwriting a concurrent generation."""
        if mutation.before is None:
            self._restore_created_path(mutation)
        elif mutation.after is None:
            self._restore_removed_path(mutation)
        else:
            self._restore_exchanged_path(mutation)

    def _install(
        self,
        staged: PinnedPath,
        target: PinnedPath,
        *,
        expected_after: PathState,
        rollback_quarantine: PinnedPath,
        authority: bool,
    ) -> AtomicOutcome:
        adapter_error: BaseException | None = None
        try:
            self._rename_noreplace(staged, target)
        except BaseException as exc:  # noqa: BLE001 - post-call state decides whether it moved
            adapter_error = exc
        source_after, target_after = self._observe_after_atomic(staged, target)
        if source_after is None and target_after == expected_after:
            return AtomicOutcome(
                AtomicMutation(
                    target=target,
                    before=None,
                    after=expected_after,
                    quarantine=rollback_quarantine,
                    authority=authority,
                ),
                adapter_error,
            )
        if source_after == expected_after and target_after is not None:
            message = f"Binding path appeared during atomic installation; preserved it: {target}."
            raise PathDriftError(message) from adapter_error
        if source_after == expected_after and target_after is None and adapter_error is not None:
            raise adapter_error
        message = f"Scribe could not prove the installation state of {target}."
        raise self._indeterminate(message, staged, target, cause=adapter_error)

    def _exchange(
        self,
        staged: PinnedPath,
        target: PinnedPath,
        *,
        source_before: PathState,
        target_before: PathState,
        authority: bool,
    ) -> AtomicOutcome:
        adapter_error: BaseException | None = None
        try:
            self._rename_exchange(staged, target)
        except BaseException as exc:  # noqa: BLE001 - post-call state decides whether it moved
            adapter_error = exc
        source_after, target_after = self._observe_after_atomic(staged, target)
        if source_after == target_before and target_after == source_before:
            return AtomicOutcome(
                AtomicMutation(
                    target=target,
                    before=target_before,
                    after=source_before,
                    quarantine=staged,
                    authority=authority,
                ),
                adapter_error,
            )
        if source_after == source_before and target_after == target_before:
            if adapter_error is not None:
                raise adapter_error
            message = "Scribe exchange returned success without exchanging its operands."
            raise self._indeterminate(message, staged, target)
        if target_after == source_before and source_after is not None:
            self._restore_raced_exchange(
                staged,
                target,
                raced_state=source_after,
                installed_state=source_before,
                cause=adapter_error,
            )
        message = f"Scribe could not prove the exchanged replacement state of {target}."
        raise self._indeterminate(message, staged, target, cause=adapter_error)

    def _restore_created_path(self, mutation: AtomicMutation) -> None:
        """Quarantine a created generation during rollback."""
        outcome = self.remove(
            mutation.target,
            mutation.quarantine,
            expected_before=self._require_state(mutation.after, mutation.target),
            authority=mutation.authority,
        )
        if outcome.mutation.after is not None:  # pragma: no cover - remove invariant
            message = f"Scribe rollback did not remove created path {mutation.target}."
            raise RuntimeError(message)

    def _restore_removed_path(self, mutation: AtomicMutation) -> None:
        """Return one quarantined generation only when its target remains absent."""
        before = self._require_state(mutation.before, mutation.target)
        adapter_error: BaseException | None = None
        try:
            self._rename_noreplace(mutation.quarantine, mutation.target)
        except BaseException as exc:  # noqa: BLE001 - post-call state decides whether it moved
            adapter_error = exc
        quarantine_after, target_after = self._observe_after_atomic(
            mutation.quarantine,
            mutation.target,
        )
        if quarantine_after is None and target_after == before:
            return
        if quarantine_after == before and target_after is not None:
            message = f"Scribe rollback preserved a concurrent path at {mutation.target}."
            raise PathDriftError(message) from adapter_error
        message = f"Scribe could not prove restoration of removed path {mutation.target}."
        raise self._indeterminate(
            message,
            mutation.quarantine,
            mutation.target,
            cause=adapter_error,
        )

    def _restore_exchanged_path(self, mutation: AtomicMutation) -> None:
        """Exchange quarantined old content back and preserve a raced live edit."""
        before = self._require_state(mutation.before, mutation.target)
        after = self._require_state(mutation.after, mutation.target)
        outcome = self._exchange(
            mutation.quarantine,
            mutation.target,
            source_before=before,
            target_before=after,
            authority=mutation.authority,
        )
        if outcome.mutation.after != before:  # pragma: no cover - exchange invariant
            message = f"Scribe rollback restored an unexpected state at {mutation.target}."
            raise RuntimeError(message)

    def _restore_raced_exchange(
        self,
        staged: PinnedPath,
        target: PinnedPath,
        *,
        raced_state: PathState,
        installed_state: PathState,
        cause: BaseException | None,
    ) -> None:
        """Reverse an exchange that captured a last-moment concurrent generation."""
        reverse_error: BaseException | None = None
        try:
            self._rename_exchange(staged, target)
        except BaseException as exc:  # noqa: BLE001 - attest even when an adapter raises
            reverse_error = exc
        staged_after, target_after = self._observe_after_atomic(staged, target)
        if staged_after == installed_state and target_after == raced_state:
            message = f"Binding path changed during atomic exchange; restored the concurrent generation: {target}."
            raise PathDriftError(message) from (cause or reverse_error)
        message = f"Scribe could not restore a generation raced during exchange at {target}."
        raise self._indeterminate(
            message,
            staged,
            target,
            cause=reverse_error or cause,
        )

    def _restore_raced_removal(
        self,
        target: PinnedPath,
        quarantine: PinnedPath,
        *,
        raced_state: PathState,
        cause: BaseException | None,
    ) -> None:
        """Return a last-moment concurrent generation captured by quarantine."""
        restore_error: BaseException | None = None
        try:
            self._rename_noreplace(quarantine, target)
        except BaseException as exc:  # noqa: BLE001 - attest even when an adapter raises
            restore_error = exc
        quarantine_after, target_after = self._observe_after_atomic(quarantine, target)
        if quarantine_after is None and target_after == raced_state:
            message = f"Binding path changed during atomic removal; restored the concurrent generation: {target}."
            raise PathDriftError(message) from (cause or restore_error)
        message = f"Scribe could not restore a generation raced during removal at {target}."
        raise self._indeterminate(
            message,
            quarantine,
            target,
            cause=restore_error or cause,
        )

    @staticmethod
    def _rename_exchange(source: PinnedPath, destination: PinnedPath) -> None:
        rename_exchange_at(
            source.name,
            destination.name,
            source_dir_fd=source.directory_fd,
            destination_dir_fd=destination.directory_fd,
        )

    @staticmethod
    def _rename_noreplace(source: PinnedPath, destination: PinnedPath) -> None:
        rename_noreplace_at(
            source.name,
            destination.name,
            source_dir_fd=source.directory_fd,
            destination_dir_fd=destination.directory_fd,
        )

    @staticmethod
    def _require_state(state: PathState | None, target: PinnedPath) -> PathState:
        if state is not None:
            return state
        message = f"Missing required Scribe path state for {target}."
        raise RuntimeError(message)

    @staticmethod
    def _indeterminate(
        message: str,
        *paths: PinnedPath,
        cause: BaseException | None = None,
    ) -> PathStateIndeterminateError:
        """Construct one evidence-carrying indeterminate-state failure."""
        return PathStateIndeterminateError(
            message,
            paths=frozenset(path.display for path in paths),
            cause=cause,
        )

    @classmethod
    def _observe_after_atomic(
        cls,
        *paths: PinnedPath,
    ) -> tuple[PathState | None, ...]:
        """Observe every descriptor-relative operand or retain it as evidence."""
        try:
            return tuple(capture_pinned_path_state(path) for path in paths)
        except BaseException as cause:
            rendered_paths = ", ".join(str(path) for path in paths)
            message = f"Scribe could not observe atomic-operation operands: {rendered_paths}."
            raise cls._indeterminate(message, *paths, cause=cause) from cause


def capture_pinned_path_state(path: PinnedPath) -> PathState | None:
    """Capture a stable no-follow state through one pinned directory descriptor."""
    try:
        named_before = os.stat(
            path.name,
            dir_fd=path.directory_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(named_before.st_mode):
        return _state_from_metadata(named_before, content=None)

    descriptor = os.open(
        path.name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        dir_fd=path.directory_fd,
    )
    try:
        opened_before = os.fstat(descriptor)
        if _identity(named_before) != _identity(opened_before):
            raise _observation_race(path)
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read()
        opened_after = os.fstat(descriptor)
        try:
            named_after = os.stat(
                path.name,
                dir_fd=path.directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError as exc:
            raise _observation_race(path) from exc
        if _stable_metadata(opened_before) != _stable_metadata(opened_after) or _stable_metadata(
            opened_after
        ) != _stable_metadata(named_after):
            raise _observation_race(path)
        return _state_from_metadata(opened_after, content=content)
    finally:
        os.close(descriptor)


def capture_path_state(path: Path) -> PathState | None:
    """Capture one path via a short-lived pinned parent descriptor."""
    try:
        directory_fd = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
        )
    except FileNotFoundError:
        return None
    try:
        return capture_pinned_path_state(
            PinnedPath(
                directory_fd=directory_fd,
                name=path.name,
                display=path,
            )
        )
    finally:
        os.close(directory_fd)


def _state_from_metadata(
    metadata: os.stat_result,
    *,
    content: bytes | None,
) -> PathState:
    return PathState(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        user_id=metadata.st_uid,
        size=metadata.st_size,
        modified_ns=metadata.st_mtime_ns,
        content=content,
    )


def _identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _stable_metadata(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _observation_race(path: PinnedPath) -> OSError:
    return OSError(
        errno.ESTALE,
        f"Scribe path changed while it was being observed: {path}.",
        str(path.display),
    )


__all__ = (
    "AtomicMutation",
    "AtomicOutcome",
    "AtomicPathStorage",
    "AttestedPath",
    "PathDriftError",
    "PathState",
    "PathStateIndeterminateError",
    "PinnedPath",
    "capture_path_state",
    "capture_pinned_path_state",
)
