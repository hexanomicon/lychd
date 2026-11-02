"""Host-bound public structural projection, separate from private trace retention."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Self
from uuid import uuid4

from lychd.compositions.reach.operator_observation import ReachPatternObservation
from lychd.compositions.reach.operator_trace import ReachTraceEvent
from lychd.domain.oculus.models import (
    MAX_ACTIVITIES,
    ComponentDefinition,
    DeclaredRelation,
    ObservationCoverage,
    RuntimeActivity,
    SourceSnapshot,
)
from lychd.domain.weaver.inspection import PatternInspectionDescriptor
from lychd.interface.observation import OperationObservation
from lychd.system.services.oculus_snapshot import SnapshotFileWriter

SOURCE_ID = "reach.operator"
PROFILE_ID = "reach.operator"


def _components(*, model: bool) -> tuple[ComponentDefinition, ...]:
    values = [
        ComponentDefinition(
            key="reach.host", label="Reach operator host", kind="host", owner="reach", activity_coverage="partial"
        ),
        ComponentDefinition(
            key="reach.core",
            label="Isolated Reach Core",
            kind="runtime",
            owner="reach",
            activity_coverage="partial",
            icon="runtime",
        ),
        ComponentDefinition(
            key="reach.edge",
            label="Discord edge",
            kind="interface",
            owner="reach",
            activity_coverage="partial",
            icon="interface",
            icon_asset="icons/discord.svg",
        ),
        ComponentDefinition(
            key="reach.discord-rest",
            label="Discord REST driver",
            kind="interface",
            owner="reach",
            activity_coverage="instrumented",
            icon="interface",
        ),
        ComponentDefinition(
            key="reach.discord-sdk",
            label="Discord SDK HTTP",
            kind="interface",
            owner="reach",
            activity_coverage="partial",
            icon="interface",
        ),
        ComponentDefinition(
            key="reach.discord-api",
            label="Discord API",
            kind="external",
            owner="reach",
            activity_coverage="partial",
            icon="external",
            icon_asset="icons/discord.svg",
        ),
        ComponentDefinition(
            key="reach.discord-gateway",
            label="Discord Gateway handshake",
            kind="external",
            owner="reach",
            activity_coverage="partial",
            icon="external",
            icon_asset="icons/discord.svg",
        ),
        ComponentDefinition(
            key="reach.discord-cdn",
            label="Discord media endpoint",
            kind="external",
            owner="reach",
            activity_coverage="partial",
            icon="external",
        ),
        ComponentDefinition(
            key="reach.sdk-unclassified",
            label="Unclassified SDK destination",
            kind="external",
            owner="reach",
            activity_coverage="partial",
            icon="external",
        ),
        ComponentDefinition(
            key="reach.corpus", label="Selected public document corpus", kind="resource", owner="reach", icon="resource"
        ),
    ]
    if model:
        values.append(
            ComponentDefinition(
                key="reach.model",
                label="Selected local model endpoint",
                kind="external",
                owner="reach",
                activity_coverage="partial",
                icon="external",
            )
        )
    return tuple(values)


def _relations(*, model: bool) -> tuple[DeclaredRelation, ...]:
    values = [
        ("host-core", "reach.host", "reach.core", "hosted"),
        ("host-edge", "reach.host", "reach.edge", "hosted"),
        ("edge-rest", "reach.edge", "reach.discord-rest", "hosted"),
        ("edge-sdk", "reach.edge", "reach.discord-sdk", "hosted"),
        ("rest-api", "reach.discord-rest", "reach.discord-api", "attached"),
        ("sdk-api", "reach.discord-sdk", "reach.discord-api", "attached"),
        ("sdk-gateway", "reach.discord-sdk", "reach.discord-gateway", "attached"),
        ("sdk-cdn", "reach.discord-sdk", "reach.discord-cdn", "attached"),
        ("core-corpus", "reach.core", "reach.corpus", "references"),
        ("core-host-ipc", "reach.core", "reach.host", "attached"),
    ]
    if model:
        values.append(("host-model", "reach.host", "reach.model", "attached"))
    return tuple(
        DeclaredRelation.model_validate({"key": key, "source": source, "target": target, "relation": relation})
        for key, source, target, relation in values
    )


class ReachObservationPublisher:
    """Admit child role and exact generation before emitting generic source metadata."""

    def __init__(self, path: Path, *, model: bool = False) -> None:
        """Select one private handoff root; no diagnostic database is opened or queried."""
        self.generation = str(uuid4())
        self.worker_generation: str | None = None
        self.components: tuple[ComponentDefinition, ...] = _components(model=model)
        self.relations = _relations(model=model)
        self.writer = SnapshotFileWriter(path)
        self.patterns: tuple[PatternInspectionDescriptor, ...] = ()
        self._run_patterns: dict[str, tuple[str, str]] = {}
        self.activities: deque[RuntimeActivity] = deque(maxlen=MAX_ACTIVITIES)
        self.sequence = 0
        self.dropped = 0
        self.gaps = 0
        self.retired = 0
        self._producer_sequences: dict[str, int] = {}
        self._model = model
        self.publish()

    def ready(self, generation: str) -> None:
        if self.worker_generation not in {None, generation}:
            self.dropped += 1
            return
        self.worker_generation = generation
        self.components = tuple(
            component.model_copy(update={"lifecycle": "observed", "instance_id": generation})
            if component.key == "reach.core"
            else component
            for component in self.components
        )
        self.publish()

    def descriptors(self, value: ReachPatternObservation) -> None:
        """Accept only one immutable set from the hosted Core's own stdout stream."""
        if self.worker_generation not in {None, value.generation} or (
            self.patterns and self.patterns != value.patterns
        ):
            self.dropped += 1
            return
        self.worker_generation = value.generation
        self.patterns = value.patterns
        self.publish()

    def operation(self, value: OperationObservation, role: str) -> None:
        """Admit only the hosted edge and its declared transport endpoints."""
        if (
            role != "edge"
            or value.producer_id not in {"reach.discord-rest", "reach.discord-sdk"}
            or value.source != value.producer_id
            or value.target
            not in (
                {"reach.discord-api"}
                if value.producer_id == "reach.discord-rest"
                else {"reach.discord-api", "reach.discord-gateway", "reach.discord-cdn", "reach.sdk-unclassified"}
            )
            or value.generation != self.worker_generation
            or not value.operation.startswith(("http.", "discord."))
        ):
            self.dropped += 1
            return
        previous = self._producer_sequences.get(value.producer_id, 0)
        if value.seq <= previous:
            self.dropped += 1
            return
        self.gaps += max(0, value.seq - previous - 1)
        self._producer_sequences[value.producer_id] = value.seq
        fields = value.model_dump(exclude={"kind", "schema_version", "generation", "seq", "activity_kind"})
        pattern = self._run_patterns.get(value.run_id or "")
        self._append(
            RuntimeActivity(
                **fields,
                seq=self.sequence + 1,
                received_at=datetime.now(UTC),
                kind=value.activity_kind,
                producer_seq=value.seq,
                producer_generation=value.generation,
                pattern_id=pattern[0] if pattern else None,
                pattern_revision=pattern[1] if pattern else None,
            )
        )

    def _bind_run_pattern(self, event: ReachTraceEvent) -> None:
        if event.producer != "core" or event.name not in {"run_started", "native_node"} or event.run_id is None:
            return
        pattern = next(
            (
                descriptor
                for descriptor in self.patterns
                if descriptor.pattern_id == event.pattern_id and descriptor.revision == event.pattern_revision
            ),
            None,
        )
        if pattern is not None:
            if event.run_id not in self._run_patterns and len(self._run_patterns) >= MAX_ACTIVITIES:
                del self._run_patterns[next(iter(self._run_patterns))]
            self._run_patterns[event.run_id] = pattern.pattern_id, pattern.revision

    def trace(self, event: ReachTraceEvent) -> None:
        """Project a closed in-memory record, never private IDs, bodies or archive rows."""
        if event.producer == "core" and event.generation != self.worker_generation:
            self.dropped += 1
            return
        self._bind_run_pattern(event)
        if event.producer == "core" and event.name in {
            "run_started",
            "run_finished",
            "native_node",
            "native_status",
            "native_done",
        }:
            source, target, producer = "reach.core", "reach.core", "reach.core"
        elif event.producer == "host" and event.name in {"session_started", "session_finished", "gateway"}:
            source, target, producer = (
                "reach.host",
                "reach.edge" if event.name == "gateway" else "reach.core",
                "reach.host",
            )
        elif event.producer == "host" and event.name == "model_http" and self._model:
            if event.http_status is None:
                return
            source, target, producer = "reach.host", "reach.model", "reach.host"
        else:
            return
        phase = (
            "started"
            if event.status in {"started", "entered", "running"}
            else "succeeded"
            if event.status
            in {"ok", "succeeded", "done", "settled", "docs", "conversation", "context", "clarify", "empty"}
            else "cancelled"
            if event.status == "cancelled"
            else "failed"
            if event.status in {"error", "failed", "refused", "rejected"}
            else "unknown"
        )
        if event.name == "gateway":
            self.components = tuple(
                component.model_copy(update={"lifecycle": "observed" if event.status == "ok" else "unknown"})
                if component.key == "reach.edge"
                else component
                for component in self.components
            )
        if event.name == "session_finished":
            self.components = tuple(
                component.model_copy(update={"lifecycle": "stopped"})
                if component.key in {"reach.core", "reach.edge"}
                else component
                for component in self.components
            )
        pattern = self._run_patterns.get(event.run_id or "")
        self._append(
            RuntimeActivity(
                event_id=event.event_id,
                operation_id=event.call_id or event.run_id or event.event_id,
                attempt_id=event.event_id if event.name == "model_http" else None,
                seq=self.sequence + 1,
                observed_at=event.observed_at,
                received_at=datetime.now(UTC),
                producer_id=producer,
                producer_generation=event.generation if event.trace_seq and event.generation else None,
                producer_seq=event.trace_seq if event.trace_seq and event.generation else None,
                source=source,
                target=target,
                operation=f"reach.{event.name}",
                kind="transport_result" if event.name == "model_http" else "lifecycle",
                phase=phase,
                http_status=event.http_status,
                elapsed_ms=float(event.duration_ms) if event.duration_ms is not None else None,
                run_id=event.run_id,
                request_id=event.request_id,
                station_attempt_id=event.occurrence_id,
                station_key=event.node,
                step_id=event.step_id,
                native_event_id=event.native_event_id,
                native_seq=event.native_seq,
                pattern_id=pattern[0] if pattern else None,
                pattern_revision=pattern[1] if pattern else None,
            )
        )

    def _append(self, activity: RuntimeActivity) -> None:
        if any(item.event_id == activity.event_id for item in self.activities):
            self.dropped += 1
            return
        if len(self.activities) == MAX_ACTIVITIES:
            self.retired += 1
        self.sequence = activity.seq
        self.activities.append(activity)
        self.publish()

    def publish(self) -> None:
        try:
            self.writer.submit(
                SourceSnapshot(
                    source_id=SOURCE_ID,
                    generation=self.generation,
                    profile_id=PROFILE_ID,
                    profile_revision="1",
                    generated_at=datetime.now(UTC),
                    components=self.components,
                    relations=self.relations,
                    activities=tuple(self.activities),
                    patterns=self.patterns,
                    coverage=ObservationCoverage(
                        first_seq=self.activities[0].seq if self.activities else None,
                        last_seq=self.activities[-1].seq if self.activities else None,
                        dropped=self.dropped,
                        gaps=self.gaps,
                        omitted_activities=self.retired,
                        limitations=(
                            "gateway_frames_uninstrumented",
                            "sdk_http_headers_only",
                            "sdk_header_dispatch_before_socket_write",
                            "sdk_preheader_failures_unobserved",
                            "model_attempt_start_unavailable",
                            "model_without_response_unobserved",
                            "bounded_run_pattern_links",
                            "process_window_only",
                        ),
                    ),
                )
            )
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - observations never control work
            self.dropped += 1

    def close(self) -> bool:
        self.publish()
        return self.writer.close()

    def __enter__(self) -> Self:
        """Retain publication custody for the operator generation."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Flush the final dated window within a finite cleanup budget."""
        self.close()
