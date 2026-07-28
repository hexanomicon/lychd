"""InMemoryRunLedger: the QUEUED→RUNNING→DONE trail, Step rows, transition guard."""
# Profile-switch test reaches the _build_run_ledger seam.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import pytest

from lychd.agents.router import ArtifactContent, ArtifactRef, Intent
from lychd.domain.cortex.events import RunEvent, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import IllegalRunTransitionError, RunStatus


def _intent(run_id: str = "run_1") -> Intent:
    return Intent(
        session_id="sess_1",
        run_id=run_id,
        prompt="hello",
        source="bridge",
        sigil_name="operator",
        sigil_scopes=frozenset({"runs:submit"}),
    )


def test_profile_switch_selects_ledger_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    """H5/S3: the persistence profile selects the RunLedger impl (DB-free construction)."""
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "test-db-password")
    from lychd.domain.cortex.ledger import DbRunLedger
    from lychd.domain.web.altar_services import _build_run_ledger

    assert isinstance(_build_run_ledger("memory"), InMemoryRunLedger)
    # `postgres` builds the durable ledger; constructing a session factory opens no
    # connection, so this stays DB-free.
    assert isinstance(_build_run_ledger("postgres"), DbRunLedger)


@pytest.mark.asyncio
async def test_create_persists_queued_run() -> None:
    """create() persists a fresh run as QUEUED; the test-only seam keys it by intent.run_id."""
    # honor_intent_run_id is a TEST-ONLY seam; production never adopts intent.run_id (R4).
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    run = await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=70)
    assert run.run_id == "run_1"
    assert run.status is RunStatus.QUEUED
    assert run.workflow_name == "bridge_chat"
    assert run.pattern_manifest["revision"] == "legacy-unversioned"
    assert run.queue_name == "runs"
    assert run.priority == 70
    assert run.sigil_name == "operator"
    assert run.sigil_scopes == frozenset({"runs:submit"})
    assert run.to_intent().sigil_name == "operator"
    assert run.to_intent().sigil_scopes == frozenset({"runs:submit"})
    assert run.to_intent().content == run.content


@pytest.mark.asyncio
async def test_create_preserves_artifact_references_without_embedding_blob_data() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    artifact = ArtifactRef(
        artifact_id="image-1",
        digest="sha256:" + "a" * 64,
        media_type="image/png",
        size=123,
        classification="private",
    )
    intent = _intent().model_copy(update={"content": (ArtifactContent(artifact=artifact),)})

    run = await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=70)

    assert run.to_intent().required_modalities == ("image",)
    assert run.to_intent().content[0].model_dump(mode="json")["artifact"]["digest"] == artifact.digest
    assert (await ledger.get("run_1")) is run


@pytest.mark.asyncio
async def test_create_always_mints_canonical_id_ignoring_intent_run_id() -> None:
    """R4/S3: by default the ledger ALWAYS mints (mirrors DbRunLedger); intent.run_id is advisory only."""
    ledger = InMemoryRunLedger()  # no test seam → production behavior
    run = await ledger.create(_intent("client-corr-id"), workflow_name="bridge_chat", queue_name="runs", priority=70)
    assert run.run_id != "client-corr-id"  # the advisory field was NOT adopted as identity
    assert run.run_id  # a real id was minted
    assert (await ledger.get(run.run_id)) is run
    assert (await ledger.get("client-corr-id")) is None


@pytest.mark.asyncio
async def test_create_mints_canonical_id_when_intent_run_id_is_none() -> None:
    """S3: with no advisory intent.run_id, the ledger assigns the canonical run identity."""
    ledger = InMemoryRunLedger()
    intent = Intent(session_id="sess_1", prompt="hello", source="bridge")  # run_id defaults None
    run = await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=70)
    assert run.run_id  # a real id was minted
    assert run.run_id != "None"
    assert (await ledger.get(run.run_id)) is run


@pytest.mark.asyncio
async def test_queued_running_done_trail() -> None:
    """The lifecycle trail QUEUED→RUNNING→DONE sets started/finished timestamps."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)

    await ledger.set_status("run_1", RunStatus.RUNNING)
    running = await ledger.get("run_1")
    assert running is not None
    assert running.status is RunStatus.RUNNING
    assert running.started_at is not None

    await ledger.set_status("run_1", RunStatus.DONE)
    done = await ledger.get("run_1")
    assert done is not None
    assert done.status is RunStatus.DONE
    assert done.finished_at is not None


@pytest.mark.asyncio
async def test_atomic_run_claim_has_exactly_one_winner() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)

    first = await ledger.try_claim_run("run_1", enqueue_seq=0)
    duplicate = await ledger.try_claim_run("run_1", enqueue_seq=0)

    assert first is True
    assert duplicate is False


@pytest.mark.asyncio
async def test_enqueue_failure_settlement_cannot_overwrite_worker_claim() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(
        Intent(session_id="s", run_id="queued", prompt="p", source="bridge"),
        workflow_name="bridge_chat",
        queue_name="runs",
        priority=70,
    )
    await ledger.create(
        Intent(session_id="s", run_id="claimed", prompt="p", source="bridge"),
        workflow_name="bridge_chat",
        queue_name="runs",
        priority=70,
    )

    assert await ledger.try_fail_queued("queued", error="publish failed") is True
    assert await ledger.try_claim_run("claimed", enqueue_seq=0) is True
    assert await ledger.try_fail_queued("claimed", error="late publish error") is False

    queued = await ledger.get("queued")
    claimed = await ledger.get("claimed")
    assert queued is not None
    assert queued.status is RunStatus.FAILED
    assert claimed is not None
    assert claimed.status is RunStatus.RUNNING


@pytest.mark.asyncio
async def test_claimed_failure_is_owned_by_enqueue_sequence() -> None:
    """An old consent hop cannot fail a newer resume that already claimed the run."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=70)
    assert await ledger.bump_enqueue_seq("run_1") == 1
    assert await ledger.try_claim_run("run_1", enqueue_seq=1) is True

    await ledger.set_status("run_1", RunStatus.AWAITING_CONSENT)
    assert await ledger.try_admit_consent("run_1") == 2
    assert await ledger.try_claim_run("run_1", enqueue_seq=2) is True

    assert await ledger.try_fail_claimed("run_1", enqueue_seq=1, error="old hop failed") is False
    running = await ledger.get("run_1")
    assert running is not None
    assert running.status is RunStatus.RUNNING
    assert running.enqueue_seq == 2

    assert await ledger.try_fail_claimed("run_1", enqueue_seq=2, error="current hop failed") is True
    failed = await ledger.get("run_1")
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error == "current hop failed"


@pytest.mark.asyncio
async def test_stale_consent_delivery_cannot_claim_retried_hop() -> None:
    """Admission allocates identity atomically and stale broker jobs lose the claim."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=70)
    assert await ledger.try_claim_run("run_1", enqueue_seq=0) is True
    await ledger.set_status("run_1", RunStatus.AWAITING_CONSENT)

    assert await ledger.try_admit_consent("run_1") == 1
    assert await ledger.try_restore_consent_wait("run_1", enqueue_seq=1) is True
    assert await ledger.try_admit_consent("run_1") == 2

    assert await ledger.try_claim_run("run_1", enqueue_seq=1) is False
    queued = await ledger.get("run_1")
    assert queued is not None
    assert queued.status is RunStatus.QUEUED
    assert queued.enqueue_seq == 2
    assert await ledger.try_claim_run("run_1", enqueue_seq=2) is True


@pytest.mark.asyncio
async def test_illegal_transition_raises() -> None:
    """An illegal edge (QUEUED→DONE) raises IllegalRunTransitionError."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    with pytest.raises(IllegalRunTransitionError):
        await ledger.set_status("run_1", RunStatus.DONE)  # must pass through RUNNING


@pytest.mark.asyncio
async def test_same_status_is_idempotent_noop() -> None:
    """Re-setting the current status is a no-op (duplicate claim / terminal write)."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("run_1", RunStatus.RUNNING)
    await ledger.set_status("run_1", RunStatus.RUNNING)  # no raise
    assert (await ledger.get("run_1")).status is RunStatus.RUNNING  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_failed_retry_bumps_attempt() -> None:
    """FAILED→QUEUED (explicit retry) increments attempt."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("run_1", RunStatus.RUNNING)
    await ledger.set_status("run_1", RunStatus.FAILED, error="boom")
    await ledger.set_status("run_1", RunStatus.QUEUED)
    run = await ledger.get("run_1")
    assert run is not None
    assert run.attempt == 1
    assert run.status is RunStatus.QUEUED


@pytest.mark.asyncio
async def test_bump_enqueue_seq_is_monotonic() -> None:
    """bump_enqueue_seq yields a fresh, increasing seq per resume hop."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    assert await ledger.bump_enqueue_seq("run_1") == 1
    assert await ledger.bump_enqueue_seq("run_1") == 2


@pytest.mark.asyncio
async def test_append_event_excludes_tokens() -> None:
    """append_event records non-TOKEN events only (tokens are too chatty for Steps)."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.append_event(RunEvent(run_id="run_1", seq=0, kind=RunEventKind.STATUS, data="running"))
    await ledger.append_event(RunEvent(run_id="run_1", seq=1, kind=RunEventKind.TOKEN, data="chatty"))
    await ledger.append_event(RunEvent(run_id="run_1", seq=2, kind=RunEventKind.DONE, data="done"))
    kinds = [str(e.kind) for e in ledger.events("run_1")]
    assert kinds == ["status", "done"]


@pytest.mark.asyncio
async def test_next_seq_tracks_persisted_history() -> None:
    """R1: next_seq is max(persisted seq)+1 (0 with no history) — seeds a reconciled channel."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    assert await ledger.next_seq("run_1") == 0  # no history yet
    await ledger.append_event(RunEvent(run_id="run_1", seq=0, kind=RunEventKind.STATUS, data="running"))
    await ledger.append_event(RunEvent(run_id="run_1", seq=1, kind=RunEventKind.NODE, data="n"))
    assert await ledger.next_seq("run_1") == 2  # past the persisted max
    assert await ledger.next_seq("unknown") == 0  # unknown run → 0


@pytest.mark.asyncio
async def test_list_by_status_and_get_by_consent() -> None:
    """list_by_status feeds reconcile; get_by_consent feeds engine.approve."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(_intent("a"), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.create(_intent("b"), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("a", RunStatus.RUNNING)

    running = await ledger.list_by_status(RunStatus.RUNNING)
    assert [r.run_id for r in running] == ["a"]

    await ledger.set_status("b", RunStatus.RUNNING)
    await ledger.set_status("b", RunStatus.AWAITING_CONSENT)
    await ledger.set_consent("b", "consent_9")
    found = await ledger.get_by_consent("consent_9")
    assert found is not None
    assert found.run_id == "b"
    assert await ledger.get_by_consent("missing") is None
