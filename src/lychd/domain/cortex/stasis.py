"""Live Stasis Phylactery (ADR 24).

`LiveStasisPhylactery` is the in-memory, Live-Stasis-only persistence handed to
`GraphRunner`. The run event plane (`RunEvent`/`RunChannel`/`RunEventBus`) was
extracted to `domain/cortex/events.py` in Wave 2; the Durable tier
(`DurableStasisPhylactery`) lands with honest consent in Wave 4.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from pydantic_graph.persistence.in_mem import FullStatePersistence

__all__ = ["LiveStasisPhylactery"]


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
        """Append a fresh 'created' snapshot so `load_next` resumes from `node`.

        The node carried out of a failed `graph.iter()` still holds the cached
        snapshot id of its errored attempt; clearing it forces `snapshot_node` to
        mint a new, unique id so the resumed snapshot is found (not the errored
        one that shares the node's id) by `record_run`.
        """
        with suppress(AttributeError):
            node.__dict__.pop("__snapshot_id", None)
        await self.snapshot_node(state, node)

    async def mark_job_resumed(self, job_id: str) -> None:
        """Finalize rehydration. No-op in the Live tier (resident loop)."""
        _ = job_id
