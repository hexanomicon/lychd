"""Stasis Phylacteries (ADR 24): Live (in-memory) + Durable (file-backed).

`LiveStasisPhylactery` is the resident-loop tier (hardware transitions within one
process lifetime). `DurableStasisPhylactery` is the Wave-4 consent tier: it writes
each node snapshot to a JSON file under the stasis dir, so a run parked on consent
survives process death and resumes from the checkpointed node. Requeue uses
Pydantic Graph's public snapshot-id API; it never mutates private node state.
"""

from __future__ import annotations

import fcntl
import os
import stat
import tempfile
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, Any

import anyio
from pydantic_graph.nodes import generate_snapshot_id
from pydantic_graph.persistence.file import FileStatePersistence
from pydantic_graph.persistence.in_mem import FullStatePersistence

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from pydantic_graph.persistence import Snapshot

__all__ = ["DurableStasisPhylactery", "LiveStasisPhylactery"]

_PRIVATE_DIR_MODE = 0o700


def _refresh_snapshot_id(node: Any) -> None:
    """Assign a fresh public snapshot id before requeueing a suspended node."""
    with suppress(AttributeError):
        node.set_snapshot_id(generate_snapshot_id(node.get_node_id()))


class LiveStasisPhylactery(FullStatePersistence[Any, Any]):
    """In-memory persistence with Live Stasis rehydration for `GraphRunner`.

    Subclasses `FullStatePersistence` (which already implements the whole
    `snapshot_*`/`load_*`/`record_run`/`set_graph_types` surface). Adds the
    `job_id` handle and the stasis requeue hook `GraphRunner` calls when a
    `HardwareTransitionRequired` is caught mid-run.
    """

    job_id: str

    def __init__(self, *, job_id: str) -> None:
        """Bind the phylactery to one run id (the job id)."""
        super().__init__()
        self.job_id = job_id

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """Append a fresh 'created' snapshot so `load_next` resumes from `node`."""
        _refresh_snapshot_id(node)
        await self.snapshot_node(state, node)


class DurableStasisPhylactery(FileStatePersistence[Any, Any]):
    """File-backed persistence for the consent tier (survives process death).

    The base supplies the snapshot surface over a JSON file; this adds the `job_id`
    handle, the `for_run` factory, and the stasis requeue hook.  Checkpoint deletion is
    deliberately owned by ``perform_run`` after it commits a terminal run status.
    """

    job_id: str

    def __init__(self, *, job_id: str, json_file: Path) -> None:
        """Bind the phylactery to one run id and its durable checkpoint file."""
        super().__init__(json_file=json_file)
        self.job_id = job_id

    @classmethod
    def for_run(cls, run_id: str, *, stasis_dir: Path) -> DurableStasisPhylactery:
        """Build a durable phylactery for a fresh run under the stasis dir."""
        if stasis_dir.is_symlink():
            msg = f"Durable stasis root must not be a symlink: {stasis_dir}"
            raise RuntimeError(msg)
        stasis_dir.mkdir(parents=True, mode=_PRIVATE_DIR_MODE, exist_ok=True)
        metadata = stasis_dir.stat()
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != _PRIVATE_DIR_MODE:
            msg = f"Durable stasis root must be owned by uid {os.getuid()} with mode 0o700: {stasis_dir}"
            raise RuntimeError(msg)
        return cls(job_id=run_id, json_file=stasis_dir / f"{run_id}.json")

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """Append a fresh 'created' snapshot so `load_next` resumes from `node`."""
        _refresh_snapshot_id(node)
        await self.snapshot_node(state, node)

    def _save_sync(self, snapshots: list[Snapshot[Any, Any]]) -> None:
        """Replace a complete checkpoint atomically and durably on one filesystem."""
        adapter = self._snapshots_type_adapter
        if adapter is None:
            msg = "snapshots type adapter must be set"
            raise RuntimeError(msg)
        self.json_file.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.json_file.parent,
            prefix=f".{self.json_file.name}.",
            suffix=".tmp",
        )
        temporary = type(self.json_file)(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(adapter.dump_json(snapshots, indent=2))
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.json_file)
            directory_fd = os.open(self.json_file.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    @asynccontextmanager
    async def _lock(self, *, timeout: float = 1.0) -> AsyncIterator[None]:  # noqa: ASYNC109 - upstream override
        """Use a kernel advisory lock, which is released automatically on process death."""
        self.json_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.json_file.parent / f"{self.json_file.name}.lock"
        descriptor = os.open(lock_file, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        os.fchmod(descriptor, 0o600)
        try:
            with anyio.fail_after(timeout):
                while True:
                    try:
                        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        await anyio.sleep(0.01)
                    else:
                        break
            yield
        finally:
            with suppress(OSError):
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
