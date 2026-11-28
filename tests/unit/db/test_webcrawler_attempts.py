"""Pure custody invariants; these checks are not PostgreSQL or authentication proof."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lychd.db.models.run import Run
from lychd.db.webcrawler import _review_digest, _validate_run  # pyright: ignore[reportPrivateUsage]
from lychd.domain.codex.schemas import NativeConsentBinding
from lychd.domain.scout.attempts import (
    LocatorInfluence,
    LocatorSource,
    PublicLocatorDeclaration,
    ScoutAllowance,
    ScoutBudgetLimits,
    ScoutConflictError,
    ScoutPreparation,
    document_digest,
)
from lychd.domain.webcrawler.profile import WEBCRAWLER_ANSWER_PURPOSE, WebcrawlerBinding, WebcrawlerProfile
from lychd.domain.webcrawler.review import page_review


def prepared_fixture() -> tuple[ScoutPreparation, Run, NativeConsentBinding, bytes]:
    """Construct synthetic retained admission without asserting live authentication."""
    now, source_id = datetime.now(UTC), uuid4()
    url = "https://example.com/public?exact=1"
    declaration = PublicLocatorDeclaration(
        url=url,
        subject="local-operator",
        authentication_generation=uuid4(),
        purpose=WEBCRAWLER_ANSWER_PURPOSE,
        source_manifest=(LocatorSource(source_id=source_id, url=url),),
        influence_manifest=(LocatorInfluence(source_id=source_id),),
        policy_revision=1,
        declared_at=now,
    )
    allowance = ScoutAllowance(connects=3, transmissions=20, wire_bytes=10000)
    limits = ScoutAllowance(connects=6, transmissions=40, wire_bytes=20000)
    profile = WebcrawlerProfile(
        binding_id="test-native",
        policy_revision=1,
        revocation_generation=0,
        resolver_address="127.0.0.1",
        resolver_custody_statement="Synthetic fixed resolver owned by this isolated test.",
        ca_file=Path("/fixture/ca"),
        bwrap=Path("/fixture/bwrap"),
        python_root=Path("/fixture/python"),
        libraries=(),
        allowance=allowance,
        budget_limits=ScoutBudgetLimits(host=limits, binding=limits),
    )
    binding = WebcrawlerBinding(
        profile=profile, declaration=declaration, question="Read the title.", request_id=uuid4()
    )
    run = Run(
        id=uuid4(),
        workflow_name="webcrawler-page-answer@1",
        pattern_manifest={"key": "webcrawler", "revision": "1"},
        sigil_name="magus",
        source="bridge",
        status="running",
        capability_key="fixture.local",
        enqueue_seq=0,
        queue_name="runs",
        priority=50,
        intent={"admitted_scout": binding.model_dump(mode="json"), "admitted_capability_key": "fixture.local"},
    )
    preparation = ScoutPreparation(
        request_id=binding.request_id,
        attempt_id=uuid4(),
        run_id=run.id,
        enqueue_seq=0,
        workflow_name=run.workflow_name,
        sigil_name=run.sigil_name,
        capability_key="fixture.local",
        pattern_digest=document_digest(run.pattern_manifest),
        intent_digest=document_digest(run.intent),
        subject=declaration.subject,
        authentication_generation=declaration.authentication_generation,
        declaration=declaration,
        url=url,
        provider_id=profile.provider_id,
        profile=profile.profile,
        binding_digest=profile.binding_digest,
        configuration_digest=profile.configuration_digest,
        resolver_address=profile.resolver_address,
        resolver_port=profile.resolver_port,
        resolver_custody_digest=profile.resolver_custody_digest,
        resolver_custody_statement=profile.resolver_custody_statement,
        purpose=declaration.purpose,
        policy_revision=1,
        revocation_generation=0,
        expires_at=now + timedelta(minutes=5),
        allowance=allowance,
    )
    native, review = page_review(preparation)
    return preparation, run, native, review.canonical_bytes()


def test_canonical_preparation_binds_complete_declaration_and_review() -> None:
    preparation, run, native, review = prepared_fixture()
    _validate_run(run, preparation)
    assert ScoutPreparation.model_validate_json(preparation.canonical_bytes()) == preparation
    assert _review_digest(review) == native.review_digest
    assert _review_digest(review) != sha256(review).hexdigest()
    assert preparation.url not in repr(preparation)


@pytest.mark.parametrize("change", ["sigil", "capability", "intent", "pattern", "declaration"])
def test_actual_retained_run_binding_refuses_changes(change: str) -> None:
    preparation, run, _, _ = prepared_fixture()
    if change == "sigil":
        run.sigil_name = "other"
    elif change == "capability":
        run.intent = {**run.intent, "admitted_capability_key": "other.local"}
    elif change == "pattern":
        run.pattern_manifest = {"revision": "other"}
    else:
        run.intent = {"admitted_scout": {"declaration": {}}} if change == "declaration" else {}
    with pytest.raises(ScoutConflictError):
        _validate_run(run, preparation)


@pytest.mark.parametrize("encoded", [b"{}", b'{"schema_version":1,"title":"x","facts":[]}', b"null", b"not-json"])
def test_native_review_requires_actual_canonical_bounded_document(encoded: bytes) -> None:
    with pytest.raises(ScoutConflictError):
        _review_digest(encoded)


def test_mismatched_source_influence_cannot_enter_declaration() -> None:
    preparation, _, _, _ = prepared_fixture()
    document = preparation.declaration.model_dump(mode="json")
    document["influence_manifest"] = [
        {"source_id": str(uuid4()), "classification": "public", "category": "public-web-locator"}
    ]
    with pytest.raises(ValidationError):
        PublicLocatorDeclaration.model_validate(document)


def test_counters_refuse_boolean_underflow_and_overflow() -> None:
    with pytest.raises(ValidationError):
        ScoutAllowance(connects=True, transmissions=1, wire_bytes=1)
    zero = ScoutAllowance(connects=0, transmissions=0, wire_bytes=0)
    one = ScoutAllowance(connects=1, transmissions=1, wire_bytes=1)
    with pytest.raises(ValidationError):
        zero.subtract(one)
    with pytest.raises(ValidationError):
        ScoutAllowance(connects=2**63 - 1, transmissions=0, wire_bytes=0).add(one)
