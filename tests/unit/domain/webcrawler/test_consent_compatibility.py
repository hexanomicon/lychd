"""Canonical and previously retained native Webcrawler page and feed judgments."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import Literal
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from lychd.db.models.consent import Consent
from lychd.db.models.webcrawler import WebcrawlerAttempt
from lychd.db.webcrawler import DbWebcrawlerAttemptStore, _snapshot  # pyright: ignore[reportPrivateUsage]
from lychd.domain.codex.schemas import ConsentView
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.scout.attempts import ScoutAnyPreparation, ScoutConflictError, ScoutPreparation, ScoutStoreError
from lychd.domain.web.consent_reviews import ConsentReviewUnavailableError
from lychd.domain.webcrawler.profile import WebcrawlerWorkflowError
from lychd.domain.webcrawler.review import webcrawler_review
from lychd.interface.web.webcrawler_review import WebcrawlerConsentReviews
from tests.unit.domain.webcrawler.test_feed_values import fixture
from tests.webcrawler_feed_fixtures import install_effects, scenario


def _preparation(kind: Literal["page", "feed"]) -> ScoutAnyPreparation:
    feed, _ = fixture()
    if kind == "feed":
        return feed
    return ScoutPreparation.model_validate(
        feed.model_dump(exclude={"schema_version", "consumer"})
        | {
            "profile": "static-public-page@1",
            "workflow_name": "bridge_chat",
            "capability_key": "synthetic:chat",
            "purpose": "scout:answer-public-page",
            "declaration": feed.declaration.model_copy(update={"purpose": "scout:answer-public-page"}),
        }
    )


@pytest.mark.parametrize(
    ("kind", "binding_digest", "document_sha256"),
    [
        (
            "page",
            "3fd623833451b1d008595423269c34ee8eb4d8006705bf4a8aee0b2cdafa34ae",
            "894297a96ddc8f05fa29bf86ffa56f8ad598ce0922e608f32fe38b3c2495f5fe",
        ),
        (
            "feed",
            "65fabd305aff8880b5a10f11db10d7eba1a33250c241b3abf5d6d41c0a125d16",
            "bdbd36e4acf0ebad551482ba56ccc715c4dfcfc7528caeb63878f2d983d4e748",
        ),
    ],
)
def test_previously_retained_review_bytes_and_binding(
    kind: Literal["page", "feed"], binding_digest: str, document_sha256: str
) -> None:
    # Independent frozen output of these synthetic preparations at f890f904.
    native, document = webcrawler_review(_preparation(kind), legacy=True)
    assert native.digest == binding_digest
    assert sha256(document.canonical_bytes()).hexdigest() == document_sha256


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["page", "feed"])
@pytest.mark.parametrize("legacy", [False, True])
async def test_retained_consent_resolves_only_its_exact_review_and_tool(
    kind: Literal["page", "feed"], *, legacy: bool
) -> None:
    preparation = _preparation(kind)
    native, document = webcrawler_review(preparation, legacy=legacy)
    other, alternate = webcrawler_review(preparation, legacy=not legacy)
    expected_name = "Scout" if legacy else "Webcrawler"
    owner = expected_name.lower()
    assert native.owner == owner
    assert native.review_profile == f"{owner}.public-{kind}"
    assert native.review_producer == f"{owner}.public-{kind}-review"
    assert expected_name in next(f.value for f in document.facts if f.key == "withdrawal")

    row = WebcrawlerAttempt(
        id=preparation.attempt_id,
        request_id=preparation.request_id,
        run_id=preparation.run_id,
        consent_id=UUID(int=9),
        preparation_enqueue_seq=preparation.enqueue_seq,
        preparation_bytes=preparation.canonical_bytes(),
        preparation_digest=preparation.digest,
        native_binding=native.document(),
        review_bytes=document.canonical_bytes(),
        status="prepared",
    )
    snapshot = _snapshot(row)
    row.native_binding = replace(native, owner=other.owner).document()
    with pytest.raises(ScoutConflictError):
        _snapshot(row)
    row.native_binding = native.document()
    row.review_bytes = alternate.canonical_bytes()
    with pytest.raises(ScoutConflictError):
        _snapshot(row)

    now = preparation.declaration.declared_at
    tool = f"{owner}.fetch_extract"
    consent = Consent(
        id=row.consent_id,
        run_id=row.run_id,
        tool_name=tool,
        tool_call_id=str(row.id),
        native_review_required=True,
        native_binding=native.document(),
        status="granted",
        decided_by="magus",
        decided_at=now,
        expires_at=preparation.expires_at,
    )
    DbWebcrawlerAttemptStore._validate_consent(snapshot, consent, now)  # pyright: ignore[reportPrivateUsage]
    consent.tool_name = f"{other.owner}.fetch_extract"
    with pytest.raises(ScoutStoreError):
        DbWebcrawlerAttemptStore._validate_consent(snapshot, consent, now)  # pyright: ignore[reportPrivateUsage]

    access, authorizer, store = Mock(), Mock(), Mock()
    access.current.return_value = True
    authorizer.authorize.return_value.allowed = True
    store.read = AsyncMock(return_value=snapshot)
    producer = WebcrawlerConsentReviews(access=access, authorizer=authorizer, store=store)
    view = ConsentView(
        id=str(row.consent_id),
        run_id=str(row.run_id),
        tool_name=tool,
        status="pending",
        native_binding=native,
        native_review_required=True,
    )
    reviewer = default_local_sigil()
    resolution = await producer.resolve(consent=view, reviewer=reviewer, purpose="decide")
    assert resolution.binding == native
    assert resolution.document == document
    assert resolution.decision_allowed
    with pytest.raises(ConsentReviewUnavailableError):
        await producer.resolve(consent=replace(view, tool_name=consent.tool_name), reviewer=reviewer, purpose="decide")


@pytest.mark.asyncio
async def test_retained_feed_can_consume_only_its_original_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    s = await scenario()
    current = s.review
    legacy, _ = webcrawler_review(s.snapshot.preparation, legacy=True)
    s.snapshot = replace(s.snapshot, native_binding=legacy)
    s.store.read.return_value = s.store.read_request.return_value = s.snapshot
    s.consents.get.return_value = replace(
        s.consents.get.return_value, native_binding=legacy, tool_name="scout.fetch_extract"
    )
    restored = await s.service.prepare(run_id=s.run.run_id, binding=s.binding)
    assert restored == current.model_copy(update={"native_binding_digest": legacy.digest})
    s.store.prepare.assert_awaited_once()
    assert await s.service.consent(run_id=s.run.run_id, binding=s.binding, review=restored) == "granted"

    fetch, _, _ = install_effects(monkeypatch)
    material = await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=restored)
    s.service.authorize_feed_consume(run_id=s.run.run_id, binding=s.binding, review=restored, material=material)
    with pytest.raises(WebcrawlerWorkflowError):
        s.service.authorize_feed_consume(run_id=s.run.run_id, binding=s.binding, review=current, material=material)
    fetch.assert_awaited_once()
