"""BridgeSessionStore semantics: run index, settled-turn lookup, consents, channels."""

from __future__ import annotations

from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import BridgeSessionStore


def test_session_for_run_indexed_by_turn() -> None:
    """A settled agent turn indexes its run for O(1) session lookup."""
    store = BridgeSessionStore()
    session = store.create_session()
    store.add_turn(session.id, BridgeTurn(role="agent", content="risen", run_id="r1", state="settled"))
    assert store.session_for_run("r1") is session
    assert store.settled_turn_for_run("r1").content == "risen"
    assert store.session_for_run("missing") is None
    assert store.settled_turn_for_run("missing") is None


def test_session_for_run_via_consent_index() -> None:
    """Parking a consent also indexes its run to the session."""
    store = BridgeSessionStore()
    session = store.create_session()
    store.park_consent(run_id="rc", session_id=session.id, tool_name="t", args={}, requests=None)
    assert store.session_for_run("rc") is session


def test_pending_consent_count_tracks_verdicts() -> None:
    """Pending count reflects unresolved consents only."""
    store = BridgeSessionStore()
    session = store.create_session()
    consent_id = store.park_consent(run_id="r", session_id=session.id, tool_name="t", args={}, requests=None)
    assert store.pending_consent_count() == 1
    store.resolve_consent(consent_id, approved=True)
    assert store.pending_consent_count() == 0


def test_pending_consent_for_run_probe() -> None:
    """The ghoul's park probe returns a run's still-pending consent, else None."""
    store = BridgeSessionStore()
    session = store.create_session()
    consent_id = store.park_consent(run_id="rp", session_id=session.id, tool_name="t", args={}, requests=None)
    assert store.pending_consent_for_run("rp") is not None
    store.resolve_consent(consent_id, approved=True)
    assert store.pending_consent_for_run("rp") is None
    assert store.pending_consent_for_run("unknown") is None
