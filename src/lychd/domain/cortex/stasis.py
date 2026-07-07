"""Stasis Phylacteries (ADR 24): Live (in-memory) + Durable (file-backed).

`LiveStasisPhylactery` is the resident-loop tier (hardware transitions within one
process lifetime). `DurableStasisPhylactery` is the Wave-4 consent tier: it writes
each node snapshot to a JSON file under the stasis dir, so a run parked on consent
survives process death and resumes from the checkpointed node. Both share the
`_clear_snapshot_id` rehydration trick (mint a fresh snapshot id so `load_next`
resumes from the parked node, not its errored attempt).
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any

from pydantic_graph.persistence.file import FileStatePersistence
from pydantic_graph.persistence.in_mem import FullStatePersistence

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["DurableStasisPhylactery", "LiveStasisPhylactery"]


def _clear_snapshot_id(node: Any) -> None:
    """Drop a node's cached `__snapshot_id` so `snapshot_node` mints a fresh one.

    The node carried out of a failed/parked `graph.iter()` still holds the snapshot
    id of its errored attempt; clearing it forces a new, unique id so the resumed
    snapshot is found by `record_run` (not the stale one that shares the node's id).
    """
    with suppress(AttributeError):
        node.__dict__.pop("__snapshot_id", None)


class LiveStasisPhylactery(FullStatePersistence[Any, Any]):
    """In-memory persistence with Live Stasis rehydration for `GraphRunner`.

    Subclasses `FullStatePersistence` (which already implements the whole
    `snapshot_*`/`load_*`/`record_run`/`set_graph_types` surface). Adds the
    `job_id` handle and the two stasis hooks `GraphRunner` calls when a
    `HardwareTransitionRequired` is caught mid-run.
    """

    job_id: str

    def __init__(self, *, job_id: str) -> None:
        """Bind the phylactery to one run id (the job id)."""
        super().__init__()
        self.job_id = job_id

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """Append a fresh 'created' snapshot so `load_next` resumes from `node`."""
        _clear_snapshot_id(node)
        await self.snapshot_node(state, node)

    async def mark_job_resumed(self, job_id: str) -> None:
        """Finalize rehydration. No-op in the Live tier (resident loop)."""
        _ = job_id


class DurableStasisPhylactery(FileStatePersistence[Any, Any]):
    """File-backed persistence for the consent tier (survives process death).

    The base supplies the snapshot surface over a JSON file; this adds the `job_id`
    handle, the `for_run` factory, and the two stasis hooks. `mark_job_resumed`
    tombstones the file — but ONLY on a non-parked resume (a chained re-park keeps
    the file; `resume_graph` skips `mark_job_resumed` when the result is `RunParked`).
    """

    job_id: str

    def __init__(self, *, job_id: str, json_file: Path) -> None:
        """Bind the phylactery to one run id and its durable checkpoint file."""
        super().__init__(json_file=json_file)
        self.job_id = job_id

    @classmethod
    def for_run(cls, run_id: str, *, stasis_dir: Path) -> DurableStasisPhylactery:
        """Build a durable phylactery for a fresh run under the stasis dir."""
        stasis_dir.mkdir(parents=True, exist_ok=True)
        return cls(job_id=run_id, json_file=stasis_dir / f"{run_id}.json")

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """Append a fresh 'created' snapshot so `load_next` resumes from `node`."""
        _clear_snapshot_id(node)
        await self.snapshot_node(state, node)

    async def mark_job_resumed(self, job_id: str) -> None:
        """Tombstone the durable file (non-parked resume only)."""
        _ = job_id
        self.json_file.unlink(missing_ok=True)
