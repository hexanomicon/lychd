"""Disposable, offline native Reach documents worker; run only in the explicit OCI development image.

The caller supplies a public export and generic policy. No ambient configuration,
SDK, database, model, credential, host service or network client is constructed.
Its in-memory Run and turn records expire with this process generation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import stat
import sys
from collections.abc import Callable, MutableMapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn
from uuid import uuid4

import structlog

from lychd.agents.factory import AgentForge
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.compositions.reach.documents import MAX_DOCUMENT_BYTES, CorpusManifest, PublicCorpus, verify_corpus
from lychd.compositions.reach.documents_workflow import (
    DocumentsRefused,
    make_documents_intent,
    reach_documents_workflow,
)
from lychd.compositions.reach.operator_wire import (
    MAX_WIRE_BYTES,
    ReachWorkerReady,
    ReachWorkerRequest,
    ReachWorkerResult,
    parse_request_line,
    protocol_bytes,
    strict_json,
)
from lychd.compositions.reach.schemas import ReachPolicy, require_aware
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import perform_run

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.animation.schemas.capability_family import CapabilityFamily
    from lychd.domain.cortex.priority import Priority
    from lychd.domain.orchestration.schema import TransitionPlan

MAX_REQUESTS = 512


def _read_regular(path: Path, limit: int, *, directory_fd: int | None = None) -> bytes:
    """Open only one explicit regular file, refusing symlinks and excess bytes."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            msg = "file_refused"
            raise ValueError(msg)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            msg = "file_limit"
            raise ValueError(msg)
        return raw
    finally:
        os.close(descriptor)


def load_corpus(directory: Path) -> PublicCorpus:
    """Detach and verify a bounded public export through one no-follow directory handle."""
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        raw = _read_regular(Path("manifest.json"), MAX_WIRE_BYTES, directory_fd=descriptor)
        strict_json(raw)
        manifest = CorpusManifest.model_validate_json(raw)
        contents = tuple(
            _read_regular(Path(document.file), MAX_DOCUMENT_BYTES, directory_fd=descriptor)
            for document in manifest.documents
        )
        return verify_corpus(manifest, contents)
    finally:
        os.close(descriptor)


def load_policy(path: Path) -> ReachPolicy:
    """Read explicit generic JSON policy; never discover operator files or Settings."""
    raw = _read_regular(path, MAX_WIRE_BYTES)
    strict_json(raw)
    return ReachPolicy.model_validate_json(raw)


class NoCapabilities:
    """Every inference, tool, provider and hardware capability is unavailable."""

    def lease_grant(
        self,
        *,
        family: CapabilityFamily | str,
        model_name: str | None = None,
        capability_key: str | None = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
        requires_tools: bool = False,
    ) -> AbstractAsyncContextManager[CapabilityGrant]:
        """Refuse instead of materializing a capability handle."""
        del family, model_name, capability_key, run_id, priority, require_modalities, requires_tools
        msg = "operator_no_capability"
        raise RuntimeError(msg)


class NoTransitions:
    """Open ordinary native claims while forbidding all runtime transitions."""

    def __init__(self) -> None:
        """Create only a local claim gate, without hardware services."""
        self.worker_broker = GhoulBroker()

    async def request_transition(self, target_capability_key: str, priority: Priority) -> TransitionPlan:  # noqa: ARG002
        """Refuse every request to change physical runtime state."""
        msg = "operator_no_transition"
        raise RuntimeError(msg)


@dataclass
class LocalJob:
    """A process-owned notification, with no broker or recovery guarantee."""

    key: str
    task: asyncio.Task[Any] | None = None


@dataclass
class LocalQueue:
    """Keep exact delivery keys until their locally owned worker retires."""

    jobs: dict[str, LocalJob] = field(default_factory=dict)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> LocalJob:
        if job_or_func != "perform_run":
            msg = "operator_job_refused"
            raise ValueError(msg)
        key = str(kwargs["key"])
        return self.jobs.setdefault(key, LocalJob(key))

    async def job(self, job_key: str, /) -> LocalJob | None:
        return self.jobs.get(job_key)

    async def abort(self, job: LocalJob, error: str, /, ttl: float = 5) -> None:  # noqa: ARG002
        if job.task is not None and not job.task.done():
            job.task.cancel()
            await asyncio.gather(job.task, return_exceptions=True)


@dataclass
class DocumentsRuntime:
    """One serial native generation; no result grants a terminal replay or an external send."""

    policy: ReachPolicy
    corpus: PublicCorpus
    started_at: datetime
    clock: Callable[[], datetime]
    engine: RunEngine
    substrate: RunSubstrate
    sessions: BridgeSessionStore
    queue: LocalQueue
    bus: InProcessEventBus
    generation: str = field(default_factory=lambda: str(uuid4()))
    _seen: dict[tuple[str, str, str], str] = field(default_factory=dict)
    _serial: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def ready(self) -> ReachWorkerReady:
        return ReachWorkerReady(
            generation=self.generation,
            started_at=self.started_at,
            policy_digest=self.policy.digest,
            corpus_digest=self.corpus.digest,
        )

    def refuse(
        self, request_id: str, reason: str, *, error: bool = False, run_id: str | None = None
    ) -> ReachWorkerResult:
        """Return only stable codes, excluding foreign text and exception diagnostics."""
        return ReachWorkerResult(
            request_id=request_id,
            status="error" if error else "refused",
            run_id=run_id,
            policy_digest=self.policy.digest,
            corpus_digest=self.corpus.digest,
            reason=reason,
        )

    async def process(self, request: ReachWorkerRequest, *, timeout: float = 15) -> ReachWorkerResult:  # noqa: C901, PLR0911, ASYNC109 - explicit bounded admission and asyncio.timeout ownership
        """Admit once, execute through the real worker, and retrieve its exact settled result."""
        async with self._serial:
            identity = (request.event.platform, request.event.account_id, request.event.event_id)
            canonical = json.dumps(
                request.model_dump(mode="json", exclude={"request_id"}), sort_keys=True, separators=(",", ":")
            )
            digest = sha256(canonical.encode()).hexdigest()
            if identity in self._seen:
                reason = "duplicate" if self._seen[identity] == digest else "duplicate_conflict"
                return self.refuse(request.request_id, reason)
            if len(self._seen) >= MAX_REQUESTS:
                return self.refuse(request.request_id, "generation_budget")
            # Validate before even a fixture session or native Run is constructed.
            try:
                make_documents_intent(
                    self.policy,
                    self.corpus,
                    request,
                    session_id="preflight",
                    started_at=self.started_at,
                    now=self.clock(),
                )
            except DocumentsRefused as error:
                return self.refuse(request.request_id, str(error))
            self._seen[identity] = digest
            session = await self.sessions.create_session(title="Operator public documents")
            intent = make_documents_intent(
                self.policy, self.corpus, request, session_id=session.id, started_at=self.started_at, now=self.clock()
            )
            handle = await self.engine.submit(intent, idempotency_key=f"{self.generation}:{digest}")
            run = await self.substrate.ledger.get(handle.run_id)
            if run is None:
                return self.refuse(request.request_id, "run_missing", error=True)
            task = asyncio.create_task(
                perform_run({"run_substrate": self.substrate}, run_id=run.run_id, enqueue_seq=run.enqueue_seq)
            )
            for job in self.queue.jobs.values():
                if job.task is None:
                    job.task = task
            try:
                async with asyncio.timeout(timeout):
                    await task
                    await self.substrate.bus.wait_persisted(run.run_id)
                terminal = await self.substrate.ledger.get(run.run_id)
                turn = await self.sessions.settled_turn_for_run(run.run_id)
                if terminal is None or terminal.status is not RunStatus.DONE or turn is None:
                    return self.refuse(request.request_id, "run_incomplete", error=True, run_id=run.run_id)
                result = ReachWorkerResult.model_validate_json(turn.content)
                if result.request_id != request.request_id or result.run_id != run.run_id:
                    return self.refuse(request.request_id, "result_binding", error=True, run_id=run.run_id)
                return result  # noqa: TRY300 - settlement retrieval shares the guarded failure boundary
            except TimeoutError:
                return self.refuse(request.request_id, "run_timeout", error=True, run_id=run.run_id)
            except Exception:  # noqa: BLE001 - closed diagnostics never echo input, paths or provider errors
                return self.refuse(request.request_id, "run_failed", error=True, run_id=run.run_id)
            finally:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                self.queue.jobs.clear()

    async def aclose(self) -> None:
        """Retire owned tasks before withdrawing the ephemeral event bus."""
        for job in self.queue.jobs.values():
            await self.queue.abort(job, "shutdown")
        await self.bus.aclose()


def build_runtime(
    policy: ReachPolicy,
    corpus: PublicCorpus,
    *,
    started_at: datetime | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> DocumentsRuntime:
    """Compose isolated memory collaborators; never publish a global application substrate."""
    boundary = started_at if started_at is not None else clock()
    require_aware(boundary)
    workflow = reach_documents_workflow(policy, corpus, started_at=boundary, clock=clock)
    registry = BuiltinWorkflowRegistry(workflows=(workflow,))
    ledger = InMemoryRunLedger()
    bus = InProcessEventBus(ledger=ledger)
    sessions = BridgeSessionStore(sigil_name="reach.guest")
    queue = LocalQueue()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=registry,
        orchestrator=NoTransitions(),
        dispatcher=NoCapabilities(),
        context=ContextOrchestrator(registry=AnimatorRegistry(declarations=AnimatorDeclarations((), ()))),
        fragments=build_fragment_registry(),
        turns=sessions,
        forge=AgentForge(),
        queues={"operator-reach": queue},
    )
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=registry,
        queue_router=QueueRouter({"default": RouteRule(queue="operator-reach", priority=50)}),
        queues=substrate.queues,
        stasis_store=substrate.stasis_store,
        cancellations=substrate.cancellations,
    )
    return DocumentsRuntime(policy, corpus, boundary, clock, engine, substrate, sessions, queue, bus)


async def serve(runtime: DocumentsRuntime, reader: asyncio.StreamReader, write: Callable[[bytes], None]) -> None:
    """Process newline frames serially, stopping on overflow rather than retaining hostile bytes."""
    write(protocol_bytes(runtime.ready))
    while True:
        try:
            raw = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as error:
            if error.partial:
                write(protocol_bytes(runtime.refuse("invalid", "invalid_request", error=True)))
            return
        except asyncio.LimitOverrunError:
            write(protocol_bytes(runtime.refuse("invalid", "input_limit", error=True)))
            return
        try:
            request = parse_request_line(raw)
        except (ValueError, UnicodeError, RecursionError):
            write(protocol_bytes(runtime.refuse("invalid", "invalid_request", error=True)))
            continue
        try:
            result = await runtime.process(request)
        except Exception:  # noqa: BLE001 - malformed continuations never echo their diagnostics
            result = runtime.refuse(request.request_id, "run_failed", error=True)
        write(protocol_bytes(result))


async def run(policy: ReachPolicy, corpus: PublicCorpus) -> None:
    """Own stdin and the native runtime until EOF, cancellation or process shutdown."""
    runtime = build_runtime(policy, corpus)
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    protocol = asyncio.StreamReaderProtocol(reader)
    transport, _ = await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    def write(raw: bytes) -> None:
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()

    try:
        await serve(runtime, reader, write)
    finally:
        transport.close()
        await runtime.aclose()


def _require_image() -> None:
    if not Path("/opt/lychd-test-image").is_file() or not (
        Path("/run/.containerenv").is_file() or Path("/.dockerenv").is_file()
    ):
        msg = "operator_image_required"
        raise ValueError(msg)


def _drop_diagnostic(_logger: Any, _method: str, _event: MutableMapping[str, Any]) -> NoReturn:
    raise structlog.DropEvent


def main(argv: list[str] | None = None) -> int:
    """Explicit startup only; help loads no operator configuration or runtime."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--corpus-dir", required=True, type=Path)
    arguments = parser.parse_args(argv)
    # The wire owns stdout. Foreign/runtime diagnostics cannot become protocol
    # frames or disclose a rejected question through an exception renderer.
    previous_level = logging.root.manager.disable
    previous_config = structlog.get_config()
    logging.disable(logging.CRITICAL)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL), processors=[_drop_diagnostic]
    )
    try:
        _require_image()
        policy, corpus = load_policy(arguments.policy), load_corpus(arguments.corpus_dir)
        asyncio.run(run(policy, corpus))
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except Exception:  # noqa: BLE001 - stdout stays protocol-only; errors never expose input
        print("reach_worker_startup_refused", file=sys.stderr)  # noqa: T201 - fixed local diagnostic
        return 1
    finally:
        logging.disable(previous_level)
        structlog.configure(**previous_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
