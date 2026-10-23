"""Explicit PostgreSQL native public-peer operator lab with in-process delivery.

This opt-in profile runs the real RunEngine, perform_run, Graph and durable
checkpoint adapters. Its local queue is deliberately process-owned; it proves no
SAQ broker operation. It exposes no models, hardware transitions or incoming peer
service. The existing public-text policy and actual installed operator credential
remain mandatory. The caller supplies an already migrated database.
"""

from __future__ import annotations

# ruff: noqa: ARG002 - disabled ports preserve the required collaborator signatures
import argparse
import asyncio
import getpass
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.agents.factory import AgentForge
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.agents.workflows.native_public_peer import NATIVE_PUBLIC_PEER
from lychd.db.checkpoints import PostgresStasisStore
from lychd.db.intercom import IntercomStore, IntercomStoreError
from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.peer import PeerAuthorityError, PublicDeclaration, PublicTextSource
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate, reset_run_substrate, set_run_substrate
from lychd.domain.intercom.native import PeerTaskOutcomeError
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.web.fragments import build_fragment_registry
from lychd.ghouls.runs import perform_run, reconcile_runs
from lychd.system.services.intercom import IntercomService, IntercomUnknownError
from lychd.system.services.local_access import load_local_access
from lychd.system.services.peer_authority import PeerAuthority
from lychd.system.services.peer_runs import PeerRunService

if __package__:
    from scripts.intercom_lab import operate, policy_from_record
else:
    from intercom_lab import operate, policy_from_record

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.animation.schemas.capability_family import CapabilityFamily
    from lychd.domain.cortex.priority import Priority
    from lychd.domain.orchestration.schema import TransitionPlan


def _refuse(code: str) -> NoReturn:
    raise PeerAuthorityError(code) from None


class NoCapabilities:
    """Refuse every capability road in this exact no-model lab profile."""

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
        """Refuse rather than materializing any local inference or hardware handle."""
        _refuse("native-profile-no-capability")


class NoTransitions:
    """Keep the shared worker admission gate; refuse every hardware transition."""

    def __init__(self) -> None:
        """Open ordinary Run claims without claiming hardware readiness."""
        self.worker_broker = GhoulBroker()

    async def request_transition(self, target_capability_key: str, priority: Priority) -> TransitionPlan:
        """Refuse all hardware changes from this bounded public-peer profile."""
        _refuse("native-profile-no-transition")


@dataclass
class LocalJob:
    """A declared local delivery object, without broker durability claims."""

    key: str
    run_id: str
    enqueue_seq: int
    task: asyncio.Task[Any] | None = None
    status: str = "queued"


@dataclass
class NativeLabQueue:
    """Publish exact delivery keys locally; PostgreSQL owns recoverable intent."""

    jobs: dict[str, LocalJob] = field(default_factory=dict)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> LocalJob:
        """Retain one local notification for a durable Run delivery."""
        if job_or_func != "perform_run":
            _refuse("native-profile-job")
        key = str(kwargs["key"])
        job = self.jobs.get(key)
        if job is None:
            job = LocalJob(key, str(kwargs["run_id"]), int(kwargs["enqueue_seq"]))
            self.jobs[key] = job
        return job

    async def job(self, job_key: str, /) -> LocalJob | None:
        """Return only an actually retained process-local delivery."""
        return self.jobs.get(job_key)

    async def abort(self, job: LocalJob, error: str, /, ttl: float = 5) -> None:
        """Cancel and await the actual locally owned worker before acknowledging."""
        task = job.task
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            if not task.done():
                _refuse("native-worker-retirement")
        job.status = "aborted"

    async def abort_orphan(self, job: LocalJob, error: str, /) -> None:
        """Retire only this process's actual local notification after restart."""
        await self.abort(job, error)


@dataclass
class NativePeerRuntime:
    """One explicitly assembled local Run lifecycle over actual durable adapters."""

    peer: PeerRunService
    engine: RunEngine
    substrate: RunSubstrate
    sessions: DbBridgeSessionStore
    queue: NativeLabQueue

    async def run_once(self, run_id: str) -> dict[str, Any]:
        """Claim one exact native delivery through the existing worker."""
        run = await self.substrate.ledger.get(run_id)
        if run is None or run.status is not RunStatus.QUEUED:
            return {"run_id": run_id, "status": run.status.value if run else "missing"}
        task = asyncio.current_task()
        if task is None:
            _refuse("native-worker")
        for job in self.queue.jobs.values():
            if (job.run_id, job.enqueue_seq) == (run_id, run.enqueue_seq):
                job.task, job.status = task, "active"
        try:
            return await perform_run({}, run_id=run_id, enqueue_seq=run.enqueue_seq)
        finally:
            for job in self.queue.jobs.values():
                if job.task is task:
                    job.task, job.status = None, "complete"


def build_runtime(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    intercom: IntercomService,
    authority: PeerAuthority,
) -> NativePeerRuntime:
    """Compose the exact opt-in native lab without loading configuration or secrets."""
    ledger = DbRunLedger(session_factory=session_factory)
    sessions = DbBridgeSessionStore(session_factory, sigil_name="magus")
    bus = InProcessEventBus(ledger=ledger)
    checkpoints = PostgresStasisStore(session_factory)
    registry = BuiltinWorkflowRegistry(workflows=(NATIVE_PUBLIC_PEER,))
    queue = NativeLabQueue()
    peer = PeerRunService(
        store=IntercomStore(session_factory),
        intercom=intercom,
        ledger=ledger,
        authority=authority,
        fence=RunEffectFence(),
    )
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
        queues={"native-peer": queue},
        stasis_store=checkpoints,
        peer=peer,
        effects=peer,
    )
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=registry,
        queue_router=QueueRouter(routing={"default": RouteRule(queue="native-peer", priority=50)}),
        queues=substrate.queues,
        stasis_store=checkpoints,
        cancellations=substrate.cancellations,
        effects=peer,
        peer=peer,
        peer_admission=peer.admission,
    )
    peer.bind_engine(engine)
    set_run_substrate(substrate)
    return NativePeerRuntime(peer, engine, substrate, sessions, queue)


async def operate_native(  # noqa: C901 - explicit dispatch and terminal outcome guards
    runtime: NativePeerRuntime, authentication: object, command: dict[str, Any]
) -> dict[str, Any]:
    """Execute only explicit native operations under the actual operator marker."""
    runtime.peer.authenticate_operator(authentication)
    operation = command["operation"]
    if operation == "submit-public-run":
        runtime.peer.authenticate_operator(authentication)  # host assembly, before session creation
        session_id = command.get("session_id")
        if session_id is None:
            session_id = (await runtime.sessions.create_session(title="Public peer task")).id
        source_record = dict(command["source"])
        for name in ("source_manifest", "influence_manifest"):
            if name in source_record:
                source_record[name] = tuple(source_record[name])
        handle = await runtime.peer.admit_public_run(
            authentication,
            session_id=str(session_id),
            request_id=UUID(command["request_id"]),
            source=PublicTextSource(**source_record),
            peer_id=UUID(command["peer_id"]),
            purpose=command["purpose"],
            task_schema=command["task_schema"],
            endpoint=command["endpoint"],
        )
        await runtime.run_once(handle.run_id)
        return await runtime.peer.status(authentication, run_id=handle.run_id)
    run_id = str(command["run_id"])
    if operation == "reauthorize-run":
        return await runtime.peer.reauthorize_existing_run(
            authentication,
            run_id=run_id,
            expected_task_id=command["task_id"],
            expected_binding_digest=command["binding_digest"],
            actions=frozenset(command["actions"]),
            reaffirm_public_source=command.get("reaffirm_public_source", False),
        )
    if operation == "tick":
        await runtime.peer.drive_wait(run_id)
        try:
            await runtime.run_once(run_id)
        except PeerTaskOutcomeError as error:
            if error.outcome not in {"unknown", "expired", "revoked", "refused", "remote_noncompletion"}:
                raise
            settled = await runtime.peer.status(authentication, run_id=run_id)
            if settled["status"] not in {"failed", "cancelled"}:
                raise
            return {**settled, "outcome": error.outcome}
    elif operation == "cancel-run":
        runtime.peer.authenticate_operator(authentication)  # local cancellation requires no peer permission
        await runtime.engine.cancel(run_id)
    elif operation != "status":
        _refuse("native-operation")
    result = await runtime.peer.status(authentication, run_id=run_id)
    if result["status"] == "done":
        result["reply"] = await runtime.peer.read_result(authentication, run_id=run_id)
    return result


async def run_session(configuration: dict[str, Any], password: str) -> None:
    """Authenticate once, compose durable native custody, and retire before closing it."""
    access = LocalOperatorAccess(access_password=load_local_access().password.get_secret_value())
    authority = PeerAuthority(access=access, policy=policy_from_record(configuration["policy"]))
    authentication = access.authenticate(username=b"magus", password=password.encode())
    if authentication is None:
        _refuse("authentication")
    key_path = Path(os.environ["LYCHD_INTERCOM_SIGNING_KEY_FILE"])
    if not key_path.is_absolute():
        _refuse("signing-key")
    database = create_async_engine(os.environ["LYCHD_INTERCOM_DATABASE_URL"], echo=False, hide_parameters=True)
    factory = async_sessionmaker(database, expire_on_commit=False)
    intercom = IntercomService(
        store=IntercomStore(factory),
        authority=authority,
        workload_id=UUID(configuration["workload_id"]),
        signing_key=key_path.read_bytes(),  # noqa: ASYNC240 - startup read before live effects
        signing_key_id=configuration["signing_key_id"],
    )
    runtime = build_runtime(session_factory=factory, intercom=intercom, authority=authority)
    declarations: dict[UUID, PublicDeclaration] = {}
    try:
        await reconcile_runs({})
        for line in sys.stdin:
            try:
                command = cast("dict[str, Any]", json.loads(line))
                if command["operation"] in {
                    "enroll",
                    "rotate",
                    "revoke",
                    "declare-public",
                    "submit",
                    "poll",
                    "cancel",
                    "read",
                }:
                    result = await operate(intercom, authentication, command, declarations)
                else:
                    result = await operate_native(runtime, authentication, command)
            except IntercomUnknownError as error:
                result = {"error": "unknown", "task_id": str(error.task_id)}
            except (PeerAuthorityError, IntercomStoreError) as error:
                result = {"error": error.code}
            except (KeyError, TypeError, ValueError):
                result = {"error": "input"}
            print(json.dumps(result, sort_keys=True), flush=True)  # noqa: T201 - explicit operator projection
    finally:
        runtime.peer.fence_all("native_lab_shutdown")
        await runtime.peer.contain_all()
        await cast("InProcessEventBus", runtime.substrate.bus).aclose()
        access.revoke()
        reset_run_substrate()
        await database.dispose()


def main() -> None:
    """Start the explicit lab; --help performs no database or network operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args()
    configuration = cast("dict[str, Any]", json.loads(arguments.config.read_text()))
    try:
        asyncio.run(run_session(configuration, getpass.getpass("Dedicated local operator password: ")))
    except Exception:  # noqa: BLE001 - never expose credential/driver/foreign diagnostics
        print('{"error":"startup-refused"}', file=sys.stderr)  # noqa: T201 - closed operator error
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
