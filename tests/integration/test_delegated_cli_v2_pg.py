"""Alembic-head V2 retention with inert owner/host consumer conformance only.

Fresh engines read authoritative retained V2 intent despite changed adapter defaults.
Synthetic positive observations establish no actual owner/source closure, current
permission, custody, verifier capacity, process containment or cross-process receipt.
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from lychd.agents.router import Intent
from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_CONFIG
from lychd.db.delegation import DbDelegatedAgentJobStore
from lychd.db.models import DelegatedAgentJobRecord
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.delegation.cli_protocol import CliLimits, CliRuntimeKind
from lychd.domain.delegation.cli_runtime import ClaudeCliRuntime, CliContainmentUncertainError, CodexCliRuntime
from lychd.domain.delegation.models import DelegatedAgentJobStatus, DelegatedCliRequestV2, encode_delegated_request
from lychd.domain.delegation.services import DelegatedAgentCoordinator, DelegatedAgentIdempotencyConflictError
from tests.support.delegated_cli import InertCliHost, InertOwnerAdmission, cli_request, substitute_spec

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """Apply the real linear Alembic head to a fresh disposable database."""
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            command.upgrade(
                AlembicCommandConfig(
                    engine=engine,
                    version_table_name=DB_MIGRATION_VERSION_TABLE,
                    file_=PATH_MIGRATION_CONFIG,
                    render_as_batch=False,
                ),
                "head",
            )
        finally:
            asyncio.run(engine.dispose())
        yield url


async def _seed(
    pg_url: str,
    kind: CliRuntimeKind,
) -> tuple[DelegatedCliRequestV2, InertCliHost, InertOwnerAdmission]:
    engine = create_async_engine(pg_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        ledger = DbRunLedger(session_factory=factory)
        run = await ledger.create(
            Intent(session_id="inert-cli-v2", prompt="consumer conformance", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=50,
        )
        request = cli_request(kind, run_id=run.run_id, request_id=f"cli-{run.run_id}")
        host, owner = InertCliHost(), InertOwnerAdmission(datetime.now(UTC))
        coordinator = _coordinator(factory, kind, host, owner)
        job = await coordinator.submit(request)
        assert await coordinator.submit(request) == job
        async with factory() as session:
            raw = await session.scalar(
                select(DelegatedAgentJobRecord.request).where(DelegatedAgentJobRecord.job_id == job.job_id)
            )
        assert raw == encode_delegated_request(request)
        for field in (
            "model",
            "executable",
            "workspace",
            "max_stdout_bytes",
            "max_stderr_bytes",
            "max_record_bytes",
            "wall_seconds",
            "task",
            "projection",
            "custody",
            "verification",
            "verifier_id",
        ):
            with pytest.raises(DelegatedAgentIdempotencyConflictError):
                await coordinator.submit(substitute_spec(host.launches[0], field, retain_request=False).request)
        assert len(host.launches) == owner.calls == 1
        return request, host, owner
    finally:
        await engine.dispose()


def _coordinator(
    factory: async_sessionmaker[AsyncSession],
    kind: CliRuntimeKind,
    host: InertCliHost,
    owner: InertOwnerAdmission | None = None,
) -> DelegatedAgentCoordinator:
    runtime_type = CodexCliRuntime if kind is CliRuntimeKind.CODEX else ClaudeCliRuntime
    first = owner is not None
    runtime = runtime_type(
        executable="/first/default/cli" if first else "/different/cli",
        model="first-default" if first else "different-default",
        job_roots="/first-default" if first else "/different",
        limits=CliLimits() if first else CliLimits(max_stdout_bytes=1, max_record_bytes=1, wall_seconds=1),
        host=host,
        owner_admission=owner,
        clock=None if owner is not None else lambda: datetime.now(UTC) + timedelta(days=2),
    )
    return DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=DbDelegatedAgentJobStore(factory))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(CliRuntimeKind))
@pytest.mark.parametrize("operation", ["poll", "cancel"])
@pytest.mark.parametrize(
    "substitution",
    [
        "none",
        "model",
        "executable",
        "argv",
        "environment",
        "workspace",
        "max_stdout_bytes",
        "max_stderr_bytes",
        "max_record_bytes",
        "wall_seconds",
        "stdin",
        "task",
        "projection",
        "custody",
        "verification",
        "verifier_id",
    ],
)
async def test_retained_v2_reconstruction_and_consistent_substitution_refusal(
    pg_url: str,
    kind: CliRuntimeKind,
    operation: str,
    substitution: str,
) -> None:
    request, host, owner = await _seed(pg_url, kind)
    original = host.launches[0]
    engine: AsyncEngine = create_async_engine(pg_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        coordinator = _coordinator(factory, kind, host)
        store = DbDelegatedAgentJobStore(factory)
        job = await store.get_by_request(request.request_id)
        assert job is not None
        assert job.request == request
        assert isinstance(job.request, DelegatedCliRequestV2)
        assert await coordinator.submit(job.request) == job.ref
        host.observed = original if substitution == "none" else substitute_spec(original, substitution)
        assert host.observed is not None
        # Host emits a newly recomputed matching receipt even for a substituted spec.
        if operation == "poll":
            settled = await coordinator.refresh(job.ref.job_id)
            assert settled.status is (
                DelegatedAgentJobStatus.SUCCEEDED if substitution == "none" else DelegatedAgentJobStatus.LOST
            )
        else:
            assert host.polls == []
        if substitution != "none":
            before = await store.get(job.ref.job_id)
            with pytest.raises(CliContainmentUncertainError):
                await coordinator.cancel(job.ref.job_id)
            assert await store.get(job.ref.job_id) == before
            assert host.cancellations == [job.ref]
        elif operation == "cancel":
            assert await coordinator.cancel(job.ref.job_id)
            settled = await store.get(job.ref.job_id)
            assert settled is not None
            assert settled.status is DelegatedAgentJobStatus.CANCELLED
        assert host.polls == ([job.ref] if operation == "poll" else [])
        assert owner.now is not None
        assert owner.now + timedelta(hours=1) < datetime.now(UTC) + timedelta(days=2)
        assert len(host.launches) == owner.calls == 1
        assert (await store.get(job.ref.job_id)).request == request  # type: ignore[union-attr]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unknown_stored_schema_remains_unchanged_and_unavailable(pg_url: str) -> None:
    request, host, _owner = await _seed(pg_url, CliRuntimeKind.CODEX)
    engine = create_async_engine(pg_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    raw = encode_delegated_request(request)
    raw["request_schema"] = "lychd-delegated-cli-request@99"
    try:
        async with factory() as session, session.begin():
            await session.execute(
                update(DelegatedAgentJobRecord)
                .where(
                    DelegatedAgentJobRecord.request_id == request.request_id,
                )
                .values(request=raw)
            )
        coordinator = _coordinator(factory, CliRuntimeKind.CODEX, host)
        with pytest.raises(ValueError, match="Unsupported"):
            await coordinator.get(host.launches[0].job.job_id)
        with pytest.raises(ValueError, match="Unsupported"):
            await coordinator.submit(request)
        async with factory() as session:
            retained = await session.scalar(
                select(DelegatedAgentJobRecord.request).where(
                    DelegatedAgentJobRecord.request_id == request.request_id,
                )
            )
        assert retained == raw
        assert len(host.launches) == 1
    finally:
        await engine.dispose()
