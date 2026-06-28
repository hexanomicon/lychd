"""Ghoul Rites — background task entrypoints for the ``rites`` queue (ADR 14).

A Rite is a registered SAQ task. The Vessel enqueues work here and a Ghoul
worker process claims it. This module is intentionally minimal: the Weaver-driven
Rite catalogue is future work, so ``perform_rite`` is the single generic
entrypoint the queue config imports today.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


async def perform_rite(ctx: dict[str, Any], *, rite: str | None = None, **_payload: Any) -> dict[str, Any]:
    """Execute a registered background Rite.

    Args:
        ctx: SAQ task context (carries ``db_session_factory``/``db_engine`` when
            the worker profile provisions them).
        rite: Optional name of the Rite to perform.
        **_payload: Rite-specific arguments (ignored by the placeholder).

    Returns:
        A small status envelope. This is a placeholder until Weaver-dispatched
        Rites are bound; it performs no side effects.

    """
    logger.info("perform_rite", rite=rite, has_ctx=bool(ctx))
    return {"status": "noop", "rite": rite}
