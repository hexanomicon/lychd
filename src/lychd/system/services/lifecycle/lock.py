"""Interprocess exclusion for real lifecycle mutations."""

from __future__ import annotations

import fcntl
import hashlib
import os
import stat
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Self

from lychd.system.services.lifecycle._authority import current_authority
from lychd.system.services.lifecycle.models import LifecycleError

_LOCK_MODE = 0o600
_LOCK_ROOT = Path("/tmp")  # noqa: S108 - fixed host namespace; file creation is no-follow and attested


class LifecycleLock(AbstractContextManager["LifecycleLock"]):
    """Serialize real lifecycle effects across local processes.

    Dry runs never acquire this lock because creating a lock file would itself
    violate their zero-effect contract. Real commands re-plan only after
    acquiring it.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Select a stable per-user, per-Codex lock outside managed host roots.

        The fixed Linux lock root is deliberate: ``TMPDIR`` is process-local
        input and the generated Host Reactor must contend with an operator CLI
        even when their environments differ.
        """
        if path is None:
            identity = hashlib.sha256(os.fsencode(current_authority().codex_root)).hexdigest()[:16]
            path = _LOCK_ROOT / f"lychd-lifecycle-{os.getuid()}-{identity}.lock"
        self.path = path
        self._descriptor = -1

    def __enter__(self) -> Self:
        """Acquire the exclusive lock without following an attacker-controlled link."""
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags, _LOCK_MODE)
        except OSError as exc:
            msg = f"Cannot open lifecycle lock safely: {self.path}"
            raise LifecycleError(msg) from exc
        try:
            self._validate_metadata(os.fstat(descriptor))
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                msg = "Another LychD lifecycle or Host Reactor operation is already in progress."
                raise LifecycleError(msg) from exc
        except BaseException:
            os.close(descriptor)
            raise
        self._descriptor = descriptor
        return self

    def _validate_metadata(self, metadata: os.stat_result) -> None:
        """Validate an opened lock descriptor before trusting it."""
        if not stat.S_ISREG(metadata.st_mode):
            msg = f"Lifecycle lock must be a regular file: {self.path}"
            raise LifecycleError(msg)
        if metadata.st_uid != os.getuid():
            msg = f"Lifecycle lock must be owned by uid {os.getuid()}: {self.path}"
            raise LifecycleError(msg)
        if stat.S_IMODE(metadata.st_mode) != _LOCK_MODE:
            msg = f"Lifecycle lock must have mode 0600: {self.path}"
            raise LifecycleError(msg)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release the process lock."""
        del exc_type, exc_value, traceback
        if self._descriptor >= 0:
            try:
                fcntl.flock(self._descriptor, fcntl.LOCK_UN)
            finally:
                os.close(self._descriptor)
                self._descriptor = -1
