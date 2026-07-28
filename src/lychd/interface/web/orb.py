"""Selected-Run Orb read API."""

from __future__ import annotations

from typing import Annotated

from litestar import Controller, get
from litestar.datastructures import State
from litestar.exceptions import NotFoundException
from litestar.params import FromPath, QueryParameter

from lychd.agents.workflows import WORKFLOW_REGISTRY
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.web.contracts import OrbRunSnapshot
from lychd.domain.web.orb import build_orb_snapshot


class OrbController(Controller):
    """Let the operator scry retained evidence for one explicitly selected Run."""

    path = "/api/v1/orb"

    @get(
        "/runs/{run_id:str}",
        name="orb:run",
        operation_id="getOrbRun",
        guards=[requires_scopes("altar:read")],
    )
    async def run(
        self,
        run_id: FromPath[str],
        state: State,
        after_seq: Annotated[int, QueryParameter(name="after_seq", ge=-1)] = -1,
        limit: Annotated[int, QueryParameter(name="limit", ge=1, le=500)] = 100,
    ) -> OrbRunSnapshot:
        """Return a bounded selected-Run evidence snapshot."""
        try:
            record = await state.services.ledger.get(run_id)
        except ValueError as exc:
            raise NotFoundException(detail="Unknown run.") from exc
        if record is None:
            raise NotFoundException(detail="Unknown run.")
        manifest = record.pattern_manifest
        pattern = WORKFLOW_REGISTRY.get_revision(
            str(manifest.get("key") or record.workflow_name),
            str(manifest.get("revision") or "legacy-unversioned"),
        )
        loom_available = (
            pattern is not None
            and isinstance(manifest.get("digest"), str)
            and pattern.manifest.digest == manifest["digest"]
        )
        return await build_orb_snapshot(
            state.services.ledger,
            record,
            after_seq=after_seq,
            limit=limit,
            loom_available=loom_available,
        )
