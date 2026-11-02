"""Explicit same-host custody for bounded, replaceable structural observations.

No archive or payload store is read. A private owner-only directory contains one
atomic snapshot; a finite latest-value queue keeps filesystem work off effect
paths. Shutdown waits only a bounded time and never invents a successful flush.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import queue
import stat
import threading
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self
from uuid import uuid4

from pydantic import ValidationError

from lychd.config.settings.observability import SnapshotSourceSettings
from lychd.domain.oculus.models import MAX_SNAPSHOT_BYTES, MAX_SOURCES, SourceFailure, SourceSnapshot
from lychd.domain.oculus.runtime import SourceRead

SNAPSHOT_NAME = "snapshot.json"
_MAX_CLOCK_SKEW_SECONDS = 5


class SnapshotSafetyError(ValueError):
    """A fixed local failure classification without disclosing filesystem contents."""


def _refuse() -> None:
    msg = "unsafe_observation_path"
    raise SnapshotSafetyError(msg)


def _private(fd: int, *, directory: bool) -> None:
    info = os.fstat(fd)
    expected = 0o700 if directory else 0o600
    if (
        (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode))
        or stat.S_IMODE(info.st_mode) != expected
        or info.st_uid != os.getuid()
        or (not directory and info.st_nlink != 1)
    ):
        _refuse()


def _without_git(directory_fd: int) -> None:
    try:
        os.stat(".git", dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    _refuse()


def _root(path: Path, *, create: bool = False) -> int:
    """Walk pinned no-follow directory descriptors and reject every Git ancestor."""
    if not path.is_absolute() or ".." in path.parts or path == Path(path.anchor):
        _refuse()
    current = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            _without_git(current)
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o700, dir_fd=current)
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = child
        _without_git(current)
        _private(current, directory=True)
    except BaseException:
        os.close(current)
        raise
    else:
        return current


def _unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        if key in value:
            msg = "duplicate_observation_key"
            raise ValueError(msg)
        value[key] = item
    return value


def _snapshot(raw: bytes) -> SourceSnapshot:
    json.loads(raw, object_pairs_hook=_unique)
    return SourceSnapshot.model_validate_json(raw)


def _freshness(selection: SnapshotSourceSettings, snapshot: SourceSnapshot) -> SourceFailure | None:
    if snapshot.source_id != selection.source_id:
        return "invalid"
    if selection.expected_generation is not None and snapshot.generation != selection.expected_generation:
        return "generation_mismatch"
    age = (datetime.now(UTC) - snapshot.generated_at).total_seconds()
    return "stale" if age < -_MAX_CLOCK_SKEW_SECONDS or age > selection.max_age_seconds else None


class SnapshotFileReader:
    """Read only the finite source directories explicitly selected by the host."""

    def __init__(self, selections: tuple[SnapshotSourceSettings, ...]) -> None:
        """Freeze source membership; never enumerate siblings or discover files."""
        if len(selections) > MAX_SOURCES or len({item.source_id for item in selections}) != len(selections):
            msg = "observation_source_limit"
            raise ValueError(msg)
        self.selections = selections

    def read(self) -> tuple[SourceRead, ...]:
        return tuple(self._read(selection) for selection in self.selections)

    @staticmethod
    def _read(selection: SnapshotSourceSettings) -> SourceRead:
        root_fd = file_fd = None
        snapshot = None
        failure: SourceFailure | None = None
        try:
            root_fd = _root(selection.path)
            file_fd = os.open(SNAPSHOT_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
            _private(file_fd, directory=False)
            if os.fstat(file_fd).st_size > MAX_SNAPSHOT_BYTES:
                return SourceRead(selection.source_id, selection.registrant_id, None, "oversize")
            raw = os.read(file_fd, MAX_SNAPSHOT_BYTES + 1)
            if len(raw) > MAX_SNAPSHOT_BYTES:
                return SourceRead(selection.source_id, selection.registrant_id, None, "oversize")
            snapshot = _snapshot(raw)
            failure = _freshness(selection, snapshot)
        except SnapshotSafetyError:
            failure = "unsafe"
        except (ValidationError, ValueError, UnicodeError, RecursionError):
            failure = "invalid"
        except FileNotFoundError:
            failure = "unavailable"
        except OSError:
            failure = "unsafe"
        finally:
            if file_fd is not None:
                os.close(file_fd)
            if root_fd is not None:
                os.close(root_fd)
        # Stale evidence remains dated, but invalid or wrong-generation bytes are never exposed.
        return SourceRead(
            selection.source_id, selection.registrant_id, snapshot if failure in {None, "stale"} else None, failure
        )


class SnapshotFileWriter:
    """Single owner, latest-value bounded queue with finite shutdown and explicit drops."""

    def __init__(self, root: Path) -> None:
        """Acquire private directory custody once; a second writer refuses."""
        self.root_fd = _root(root, create=True)
        self.lock_fd: int | None = None
        try:
            self.lock_fd = os.open(".writer.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=self.root_fd)
            _private(self.lock_fd, directory=False)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            if self.lock_fd is not None:
                os.close(self.lock_fd)
            os.close(self.root_fd)
            raise
        self._queue: queue.Queue[SourceSnapshot] = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self._closed = False
        self.dropped = 0
        self.failures = 0
        self._thread = threading.Thread(target=self._work, name="oculus-snapshot", daemon=True)
        self._thread.start()

    def submit(self, snapshot: SourceSnapshot) -> None:
        """Offer one immutable window without waiting for filesystem or another producer."""
        if self._closed:
            self.dropped += 1
            return
        try:
            self._queue.put_nowait(snapshot)
        except queue.Full:
            with suppress(queue.Empty):
                self._queue.get_nowait()
                self._queue.task_done()
                self.dropped += 1
            try:
                self._queue.put_nowait(snapshot)
            except queue.Full:
                self.dropped += 1

    def _write(self, snapshot: SourceSnapshot) -> None:
        coverage = snapshot.coverage.model_copy(
            update={"dropped": snapshot.coverage.dropped + self.dropped + self.failures}
        )
        raw = snapshot.model_copy(update={"coverage": coverage}).model_dump_json().encode("utf-8")
        if len(raw) > MAX_SNAPSHOT_BYTES:
            msg = "observation_snapshot_limit"
            raise ValueError(msg)
        # Refuse hostile replacement targets even though replace itself would not follow them.
        try:
            old = os.open(SNAPSHOT_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.root_fd)
        except FileNotFoundError:
            pass
        else:
            try:
                _private(old, directory=False)
            finally:
                os.close(old)
        temporary = f".snapshot-{uuid4().hex}"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.root_fd)
        try:
            _private(fd, directory=False)
            offset = 0
            while offset < len(raw):
                count = os.write(fd, raw[offset:])
                if count <= 0:
                    msg = "observation_write_failed"
                    raise OSError(msg)
                offset += count
            os.fsync(fd)
            os.replace(temporary, SNAPSHOT_NAME, src_dir_fd=self.root_fd, dst_dir_fd=self.root_fd)
            os.fsync(self.root_fd)
        finally:
            os.close(fd)
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=self.root_fd)

    def _work(self) -> None:
        try:
            while not self._stop.is_set() or not self._queue.empty():
                try:
                    snapshot = self._queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                try:
                    self._write(snapshot)
                except (Exception, asyncio.CancelledError):  # noqa: BLE001 - capture failure never changes an effect
                    self.failures += 1
                finally:
                    self._queue.task_done()
        finally:
            if self.lock_fd is not None:
                os.close(self.lock_fd)
            os.close(self.root_fd)

    def close(self, *, timeout: float = 2.0) -> bool:
        """Stop capture, wait a bounded interval, and report whether publication flushed."""
        self._closed = True
        self._stop.set()
        self._thread.join(timeout=min(2.0, max(0.0, timeout)))
        return not self._thread.is_alive() and self.failures == 0

    def __enter__(self) -> Self:
        """Retain the writer until bounded context cleanup."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Attempt bounded flush without changing the owning operation outcome."""
        self.close()
