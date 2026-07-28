"""Transition journal recency and capacity behavior."""

from lychd.domain.orchestration.journal import TransitionJournal
from lychd.domain.orchestration.schema import TransitionTrace


def _trace(target: str) -> TransitionTrace:
    return TransitionTrace(target_capability_key=target, priority=50)


def test_updated_request_becomes_most_recent_and_survives_capacity() -> None:
    journal = TransitionJournal(capacity=2)
    first = _trace("chat:first")
    second = _trace("chat:second")
    third = _trace("chat:third")

    journal.record(first)
    journal.record(second)
    first.phase = "completed"
    journal.record(first)

    assert [record.request_id for record in journal.recent()] == [
        first.request_id,
        second.request_id,
    ]

    journal.record(third)

    assert journal.get(first.request_id) is not None
    assert journal.get(second.request_id) is None
