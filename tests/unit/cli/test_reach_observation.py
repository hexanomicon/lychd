"""Host provenance and exact isolated Pattern publication through the generic bridge."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from scripts import reach_operator as operator
from scripts.reach_observation import ReachObservationPublisher
from scripts.reach_trace_capture import TraceCapture
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.operator_observation import ReachPatternObservation
from lychd.compositions.reach.operator_trace import ReachTraceEvent
from lychd.config.settings.observability import SnapshotSourceSettings
from lychd.domain.oculus.models import MAX_ACTIVITIES, SourceSnapshot
from lychd.domain.weaver.inspection import PatternInspectionDescriptor
from lychd.interface.observation import OperationObserver, observation_bytes, observation_context
from lychd.system.services.oculus_snapshot import SnapshotFileReader
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_policy, make_request


def read(root: Path) -> SourceSnapshot:
    result = SnapshotFileReader(
        (SnapshotSourceSettings(source_id="reach.operator", registrant_id="operator:reach", path=root),)
    ).read()[0]
    assert result.failure is None
    assert result.snapshot is not None
    return result.snapshot


@pytest.mark.asyncio
async def test_exact_worker_manifest_and_validated_child_roles_publish_after_close(tmp_path: Path) -> None:
    runtime = build_runtime(make_policy(), make_corpus())
    root = tmp_path / "observations"
    try:
        descriptors = tuple(
            PatternInspectionDescriptor.from_workflow(item) for item in runtime.substrate.workflows.all()
        )
        with ReachObservationPublisher(root) as publisher:
            capture = TraceCapture(lambda _: None, observation=publisher)
            capture.descriptors(ReachPatternObservation(generation=runtime.generation, patterns=descriptors))
            capture.ready(runtime.ready)
            accepted = OperationObserver(
                generation=runtime.generation,
                producer_id="reach.discord-rest",
                source="reach.discord-rest",
                target="reach.discord-api",
                sink=lambda event: capture.operation(event, "edge"),
            )
            attempt = accepted.operation("http.get")
            attempt.start()
            attempt.http_status = 200
            attempt.finish("succeeded")
            forged = OperationObserver(
                generation=runtime.generation,
                producer_id="reach.discord-rest",
                source="reach.discord-rest",
                target="reach.discord-api",
                sink=lambda event: capture.operation(event, "core"),
            )
            forged.operation("http.get").start()
            stale = OperationObserver(
                generation=str(uuid4()),
                producer_id="reach.discord-rest",
                source="reach.discord-rest",
                target="reach.discord-api",
                sink=lambda event: capture.operation(event, "edge"),
            )
            stale.operation("http.get").start()
        snapshot = read(root)
        assert snapshot.patterns == descriptors
        assert [item.manifest_snapshot() for item in snapshot.patterns] == [
            item.manifest.snapshot() for item in runtime.substrate.workflows.all()
        ]
        traffic = [item for item in snapshot.activities if item.kind.startswith("transport")]
        assert len(traffic) == 2
        assert traffic[0].run_id is None
        assert traffic[0].producer_generation == runtime.generation
        assert snapshot.coverage.dropped >= 2
        assert {component.key for component in snapshot.components} >= {"reach.host", "reach.core", "reach.discord-api"}
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_native_station_and_late_delivery_keep_the_admitted_exact_pattern(tmp_path: Path) -> None:
    root = tmp_path / "observations"
    with ReachObservationPublisher(root) as publisher:
        runtime = build_runtime(
            make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW, trace=publisher.trace
        )
        try:
            publisher.ready(runtime.generation)
            publisher.descriptors(
                ReachPatternObservation(
                    generation=runtime.generation,
                    patterns=tuple(
                        PatternInspectionDescriptor.from_workflow(workflow)
                        for workflow in runtime.substrate.workflows.all()
                    ),
                )
            )
            result = await runtime.process(make_request().model_copy(update={"request_id": str(uuid4())}))
            assert result.run_id is not None
            observer = OperationObserver(
                generation=runtime.generation,
                producer_id="reach.discord-rest",
                source="reach.discord-rest",
                target="reach.discord-api",
                sink=lambda event: publisher.operation(event, "edge"),
            )
            with observation_context(run_id=result.run_id):
                operation = observer.operation("http.post")
                operation.start()
                operation.http_status = 200
                operation.finish("succeeded")
        finally:
            await runtime.aclose()
    snapshot = read(root)
    station = next(item for item in snapshot.activities if item.operation == "reach.native_node")
    assert station.station_key is not None
    assert station.native_event_id is not None
    assert station.step_id == station.native_event_id
    assert station.native_seq is not None
    assert station.run_id == result.run_id
    exact = next(item for item in snapshot.patterns if item.pattern_id == station.pattern_id)
    assert station.pattern_revision == exact.revision
    assert station.station_key in {item.key for item in exact.nodes}
    late = snapshot.activities[-1]
    assert late.kind == "transport_result"
    assert (late.pattern_id, late.pattern_revision) == (station.pattern_id, station.pattern_revision)


def test_ring_retires_explicitly_and_private_platform_ids_never_project(tmp_path: Path) -> None:
    root = tmp_path / "observations"
    generation = str(uuid4())
    with ReachObservationPublisher(root) as publisher:
        publisher.ready(generation)
        for seq in range(MAX_ACTIVITIES + 4):
            publisher.trace(
                ReachTraceEvent(
                    producer="core",
                    generation=generation,
                    trace_seq=seq + 1,
                    name="native_node",
                    platform_event_id="123456789123456789",
                    remote_id="987654321987654321",
                    observed_at=datetime.now(UTC),
                )
            )
    snapshot = read(root)
    assert len(snapshot.activities) == MAX_ACTIVITIES
    assert snapshot.coverage.omitted_activities == 4
    encoded = snapshot.model_dump_json()
    assert "123456789123456789" not in encoded
    assert "987654321987654321" not in encoded


def test_model_pre_dispatch_failures_never_become_external_transport_activity(tmp_path: Path) -> None:
    root = tmp_path / "observations"
    with ReachObservationPublisher(root, model=True) as publisher:
        for code in ("model_unavailable", "permission_denied"):
            publisher.trace(ReachTraceEvent(producer="host", name="model_http", status="error", code=code))
        assert not publisher.activities
        publisher.trace(ReachTraceEvent(producer="host", name="model_http", status="error", http_status=403))
    snapshot = read(root)
    assert len(snapshot.activities) == 1
    observed = snapshot.activities[0]
    assert observed.kind == "transport_result"
    assert observed.http_status == 403
    assert observed.target == "reach.model"
    assert observed.effect_outcome is None
    assert "model_without_response_unobserved" in snapshot.coverage.limitations


@pytest.mark.asyncio
async def test_diagnostic_pipe_requires_bound_edge_role_and_discards_payloads(tmp_path: Path) -> None:
    root = tmp_path / "observations"
    generation = str(uuid4())
    with ReachObservationPublisher(root) as publisher:
        publisher.ready(generation)
        capture = TraceCapture(lambda _: None, observation=publisher)
        frames: list[bytes] = []
        observer = OperationObserver(
            generation=generation,
            producer_id="reach.discord-sdk",
            source="reach.discord-sdk",
            target="reach.discord-api",
            sink=lambda event: frames.append(observation_bytes(event)),
        )
        observer.operation("http.get").start()
        malicious = json.loads(frames[0])
        malicious["payload"] = "private-token"
        stream = asyncio.StreamReader()
        stream.feed_data(frames[0] + json.dumps(malicious).encode() + b"\n")
        stream.feed_eof()
        await operator.diagnostics(stream, role="edge", capture=capture)
        forged = asyncio.StreamReader()
        forged.feed_data(frames[0])
        forged.feed_eof()
        await operator.diagnostics(forged, role="core", capture=capture)
    snapshot = read(root)
    traffic = [item for item in snapshot.activities if item.kind == "transport_attempt"]
    assert len(traffic) == 1
    assert "private-token" not in snapshot.model_dump_json()
