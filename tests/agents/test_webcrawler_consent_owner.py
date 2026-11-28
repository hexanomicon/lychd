"""Webcrawler's exact wait owner survives a park and disappears before later stations."""

# Exercise the same private recovery guards used by the worker before dispatch.
# pyright: reportPrivateUsage=false
from __future__ import annotations

from typing import Literal
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from lychd.agents.workflows.webcrawler_chat import (
    WEBCRAWLER_CHAT_GRAPH,
    AwaitPageConsent,
    PreparePageReview,
    WebcrawlerChatState,
)
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from lychd.domain.webcrawler.profile import WebcrawlerWorkflowCode, WebcrawlerWorkflowError
from lychd.ghouls.runs import _checkpoint_binds_consent
from tests.agents.test_webcrawler_chat import _context


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", ["granted", "refused", "error"])
async def test_only_the_webcrawler_gate_checkpoint_can_recover_its_consent(
    verdict: Literal["granted", "refused", "error"], monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx, webcrawler, _, model, _ = _context()
    next_node = await PreparePageReview().run(ctx)
    assert isinstance(next_node, AwaitPageConsent)
    assert ctx.state.review is not None
    consent_id = str(ctx.state.review.consent_id)
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id=ctx.state.run_id, store=store)
    persistence.set_graph_types(WEBCRAWLER_CHAT_GRAPH)
    await persistence.snapshot_node(ctx.state, next_node)
    parked = await store.load(ctx.state.run_id)
    assert parked is not None
    assert "scout" in parked[0]["state"]
    assert "webcrawler" not in parked[0]["state"]
    assert _checkpoint_binds_consent(parked, run_id=ctx.state.run_id, consent_id=consent_id)
    # Decode a fresh state, as worker re-entry does, rather than reusing its fields.
    ctx.state = WebcrawlerChatState.model_validate(parked[0]["state"])
    if verdict == "error":
        monkeypatch.setattr(
            webcrawler, "consent", AsyncMock(side_effect=WebcrawlerWorkflowError(WebcrawlerWorkflowCode.CONSENT))
        )
    else:
        webcrawler.verdict = verdict
    successor = await AwaitPageConsent().run(ctx)
    next_store = InMemoryStasisStore()
    next_persistence = DurableStasisPhylactery(job_id=ctx.state.run_id, store=next_store)
    next_persistence.set_graph_types(WEBCRAWLER_CHAT_GRAPH)
    await next_persistence.snapshot_node(ctx.state, successor)
    later = await next_store.load(ctx.state.run_id)
    assert later is not None
    assert not _checkpoint_binds_consent(later, run_id=ctx.state.run_id, consent_id=consent_id)
    assert webcrawler.acquisitions == 0
    assert model.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ["missing-review", "different-consent"])
async def test_checkpoint_cannot_rebind_pending_owner_away_from_native_review(corruption: str) -> None:
    ctx, _, _, _, _ = _context()
    await PreparePageReview().run(ctx)
    raw = ctx.state.model_dump(mode="json")
    if corruption == "missing-review":
        raw["review"] = None
    else:
        raw["pending_consent_id"] = str(UUID(int=91))
    with pytest.raises(ValidationError, match="Webcrawler page answer refused: binding"):
        WebcrawlerChatState.model_validate(raw)
