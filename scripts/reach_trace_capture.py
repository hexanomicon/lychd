"""Trusted-host correlation for the isolated operator's structural observations."""

from __future__ import annotations

from lychd.compositions.reach.operator_trace import (
    ReachTraceEvent,
    TraceEmitter,
    TraceSink,
    platform_id_or_none,
    uuid_or_none,
)
from lychd.compositions.reach.operator_wire import ReachWorkerReady, ReachWorkerRequest, ReachWorkerResult

_INTERRUPTED_EXIT = 130


class TraceCapture:
    """Keep explicit wire relations without interpreting prompt text or timing proximity."""

    def __init__(self, sink: TraceSink, *, source_ids: frozenset[str] | None = None) -> None:
        """Bind local capture to one frozen public source catalogue."""
        self.sink = sink
        self.host = TraceEmitter("host", sink)
        self.generation: str | None = None
        self.source_ids = source_ids

    def child(self, event: ReachTraceEvent, role: str) -> None:
        """Bind source selection and producer identity to the actual hosted child."""
        if event.producer != role or (
            event.source_id is not None and self.source_ids is not None and event.source_id not in self.source_ids
        ):
            self.host.record("child_diagnostic", status="refused", code="protocol_error", generation=self.generation)
            return
        self.sink(event)

    def request(self, request: ReachWorkerRequest) -> None:
        self.host.record(
            "request_received",
            status="started",
            generation=self.generation,
            request_id=uuid_or_none(request.request_id),
            platform=request.event.platform,
            platform_event_id=platform_id_or_none(request.event.event_id),
            conversation_id=platform_id_or_none(request.event.conversation_id),
            context_round=request.context_round,
            count=len(request.history),
            chars=sum(len(item.text) for item in request.history),
        )

    def ready(self, value: ReachWorkerReady) -> None:
        self.generation = value.generation
        self.host.record("session_started", status="started", generation=self.generation)

    def result(self, result: ReachWorkerResult) -> None:
        self.host.record(
            "request_finished",
            status=result.status,
            generation=self.generation,
            request_id=uuid_or_none(result.request_id),
            run_id=uuid_or_none(result.run_id),
            chars=len(result.text),
        )

    def close(self, status: int) -> None:
        self.host.record(
            "session_finished",
            status="ok" if status == 0 else "cancelled" if status == _INTERRUPTED_EXIT else "unknown",
            generation=self.generation,
        )
