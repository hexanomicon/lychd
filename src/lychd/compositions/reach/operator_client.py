"""Platform-neutral process-wire client for the operator development profile."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from typing import Any, NoReturn, cast
from uuid import uuid4

from lychd.compositions.reach.conversation_session import ProgressHandler
from lychd.compositions.reach.operator_limits import TurnDeadline, operator_limits
from lychd.compositions.reach.operator_trace import TraceEmitter, TraceSink, error_code, platform_id_or_none
from lychd.compositions.reach.operator_wire import (
    MAX_WIRE_BYTES,
    ReachHistoryEntry,
    ReachWorkerReady,
    ReachWorkerRequest,
    ReachWorkerResult,
    protocol_bytes,
    strict_json,
)
from lychd.compositions.reach.research_wire import ReachResearchAcknowledgement, ReachResearchProgress
from lychd.compositions.reach.schemas import ReachEvent


def _refuse(code: str) -> NoReturn:
    raise ValueError(code)


def _write_stdio_frame(frame: bytes) -> None:
    """Resolve the current private output stream for each complete frame."""
    sys.stdout.buffer.write(frame)
    sys.stdout.buffer.flush()


class PipeWorker:
    """One bounded outstanding request on the supervisor's private standard streams."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        ready: ReachWorkerReady,
        *,
        write_frame: Callable[[bytes], None] | None = None,
        trace: TraceSink | None = None,
    ) -> None:
        """Bind exactly one worker generation to the private pipe."""
        self.reader = reader
        self.ready = ready
        self.lock = asyncio.Lock()
        self.available = True
        self._write_frame = write_frame if write_frame is not None else _write_stdio_frame
        self.trace = TraceEmitter("edge", trace)

    @classmethod
    async def open(cls) -> PipeWorker:
        reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)
        async with asyncio.timeout(30):
            raw = await reader.readline()
        if not raw or len(raw) > MAX_WIRE_BYTES:
            msg = "worker_readiness"
            raise ValueError(msg)
        return cls(reader, ReachWorkerReady.model_validate_json(raw))

    async def request(
        self,
        event: ReachEvent,
        history: tuple[ReachHistoryEntry, ...],
        *,
        context_round: int = 0,
        history_state: str = "exhausted",
        reply_to_event_id: str | None = None,
        reply_anchor: ReachHistoryEntry | None = None,
        continuation_anchor: ReachHistoryEntry | None = None,
        progress: ProgressHandler | None = None,
        deadline: TurnDeadline | None = None,
    ) -> ReachWorkerResult:
        if not self.available or self.lock.locked():
            msg = "worker_busy_or_unavailable"
            raise ValueError(msg)
        request = ReachWorkerRequest.model_validate(
            {
                "request_id": str(uuid4()),
                "event": event,
                "history": history,
                "context_round": context_round,
                "history_state": history_state,
                "reply_to_event_id": reply_to_event_id,
                "reply_anchor": reply_anchor,
                "continuation_anchor": continuation_anchor,
            }
        )
        frame = protocol_bytes(request)
        binding = {
            "generation": self.ready.generation,
            "request_id": request.request_id,
            "platform": event.platform,
            "platform_event_id": platform_id_or_none(event.event_id),
            "conversation_id": platform_id_or_none(event.conversation_id),
            "context_round": context_round,
        }
        self.trace.record(
            "history",
            count=len(history),
            chars=sum(len(item.text) for item in history),
            code="budget"
            if history_state == "budget"
            else "permission_denied"
            if history_state == "permission_denied"
            else "source_unavailable"
            if history_state == "unavailable"
            else None,
            **binding,
        )
        async with self.lock:
            try:
                if deadline is not None:
                    deadline.check()
                self.trace.record("request_received", status="started", **binding)
                self._write_frame(frame)
                maximum = operator_limits(
                    conversation=self.ready.model_binding_digest is not None, research=self.ready.research_enabled
                ).pipe_seconds
                async with asyncio.timeout(deadline.remaining(maximum) if deadline is not None else maximum):
                    raw = await self._read_result(request, progress=progress)
                if not raw or len(raw) > MAX_WIRE_BYTES:
                    _refuse("worker_protocol")
                result = ReachWorkerResult.model_validate_json(raw)
                if (
                    result.request_id != request.request_id
                    or result.policy_digest != self.ready.policy_digest
                    or result.corpus_digest != self.ready.corpus_digest
                    or result.model_binding_digest != self.ready.model_binding_digest
                ):
                    _refuse("worker_correlation")
                self.ready.expressions.validate_selection(result.reaction, result.gif_id)
                if event.trigger == "command" and (result.reaction is not None or result.gif_id is not None):
                    _refuse("worker_expression_audience")
            except (ValueError, OSError, TimeoutError, asyncio.CancelledError) as error:
                self.trace.record(
                    "request_finished",
                    status="cancelled" if isinstance(error, asyncio.CancelledError) else "error",
                    code=error_code(error),
                    **binding,
                )
                self.available = False
                raise
            self.trace.record(
                "request_finished", status=result.status, run_id=result.run_id, chars=len(result.text), **binding
            )
            return result

    async def _read_result(self, request: ReachWorkerRequest, *, progress: ProgressHandler | None) -> bytes:
        """Permit one correlated plan acknowledgement before the terminal result."""
        observed_progress = False
        while True:
            raw = await self.reader.readline()
            if not raw or len(raw) > MAX_WIRE_BYTES:
                _refuse("worker_protocol")
            parsed = strict_json(raw)
            value = cast("dict[str, Any]", parsed) if isinstance(parsed, dict) else None
            if value is None or value.get("kind") != "progress":
                return raw
            observed = ReachResearchProgress.model_validate_json(raw)
            if (
                not self.ready.research_enabled
                or observed_progress
                or observed.request_id != request.request_id
                or observed.binding_digest != self.ready.model_binding_digest
            ):
                _refuse("worker_progress_binding")
            observed_progress = True
            accepted = await progress(observed) if progress is not None else False
            acknowledgement = ReachResearchAcknowledgement(
                call_id=observed.call_id,
                request_id=observed.request_id,
                binding_digest=observed.binding_digest,
                accepted=accepted,
            )
            self._write_frame(acknowledgement.model_dump_json().encode() + b"\n")
