"""Real PostgreSQL admission, isolated acquisition and fixed-child extraction.

Nodes are invoked explicitly. Queue, dispatcher, events and FunctionModel remain
controlled adapters; HTTP routing, a SAQ worker process, Graph checkpoint/resume,
model inference and public Internet operation are not exercised.
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from hashlib import sha256
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
from typing import Any, cast

import dns.rdatatype
import pytest
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.agents.workflows.scout_chat import AcquireAndAnswerPage, SettlePageAnswer
from lychd.db.models import Consent, Run, RunDelivery, ScoutAttempt, ScoutBudget, Session, Step
from lychd.domain.scout.attempts import ScoutSettlement
from lychd.domain.scout.destination import preflight_destination
from lychd.domain.scout.profile import ScoutProfile, ScoutWorkflowCode, ScoutWorkflowError
from lychd.domain.scout.transport import FetchCode, FetchError
from lychd.system.services import scout_extraction
from lychd.system.services.scout_dns import ResolverEndpoint
from lychd.system.services.scout_http import serialize_get
from tests import scout_network_fixture as network
from tests.integration import test_scout_extraction_runtime as extraction_qualification
from tests.postgres_model_tables import with_referenced_tables
from tests.scout_fixtures import scout_profile
from tests.scout_postgres_fixture import isolated_postgres
from tests.scout_workflow_fixture import ScoutWorkflowFixture, approve_workflow, assemble_workflow, workflow_service

pytestmark = [pytest.mark.integration, pytest.mark.container]

_URL = f"https://{network.HOSTNAME}/workflow?exact=1"
_PROMPT = f"/read-public {_URL}\nWhat does the page report?"
_SOURCE = "Exact fixture text."
_ANSWER = "The page contains the fixed public fixture."
_DEPENDENCIES = (
    "asyncpg",
    "sqlalchemy",
    "docker",
    "h11",
    "dnspython",
    "pydantic",
    "pydantic-ai-slim",
    "pydantic-graph",
)
_SOURCE_MODULES = (
    "lychd.domain.codex.local_access",
    "lychd.domain.codex.ledger",
    "lychd.domain.cortex.cancellation",
    "lychd.domain.cortex.engine",
    "lychd.domain.cortex.ledger",
    "lychd.domain.scout.attempts",
    "lychd.domain.scout.authority",
    "lychd.domain.scout.destination",
    "lychd.domain.scout.transport",
    "lychd.domain.scout.extraction",
    "lychd.domain.scout.profile",
    "lychd.domain.scout.review",
    "lychd.db.scout",
    "lychd.db.models.scout",
    "lychd.db.sessions",
    "lychd.interface.web.scout_admission",
    "lychd.interface.web.scout_review",
    "lychd.agents.workflows.scout_chat",
    "lychd.agents.scout_context",
    "lychd.system.scout_worker",
    "lychd.system.services.scout_workflow",
    "lychd.system.services.scout_dns",
    "lychd.system.services.scout_socket",
    "lychd.system.services.scout_http",
    "lychd.system.services.scout_fetch",
    "lychd.system.services.scout_extraction",
    "tests.agents.fakes",
    "tests.agents.conftest",
    "tests.scout_fixtures",
    "tests.scout_network_fixture",
    "tests.scout_postgres_fixture",
    "tests.postgres_model_tables",
    "tests.scout_workflow_fixture",
    "tests.integration.test_scout_extraction_runtime",
    "tests.integration.test_scout_composed_runtime",
)


def _fingerprints() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    paths = [Path(cast("str", import_module(name).__file__)).resolve() for name in _SOURCE_MODULES]
    return {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest() for path in paths}


def _runtime() -> scout_extraction.ScoutExtractionRuntime:
    path = Path(os.environ["LYCHD_SCOUT_EXTRACTION_PROFILE"])
    assert path.is_absolute()
    assert path.stat().st_size <= 8192
    config = json.loads(path.read_text())
    assert set(config) == {"bwrap", "python_root", "libraries"}
    return scout_extraction.ScoutExtractionRuntime(
        bwrap=Path(config["bwrap"]),
        python_root=Path(config["python_root"]),
        libraries=tuple(Path(item) for item in config["libraries"]),
    )


def _profile(runtime: scout_extraction.ScoutExtractionRuntime, resolver: ResolverEndpoint, trust: Path) -> ScoutProfile:
    values = scout_profile().model_dump()
    values.update(
        bwrap=runtime.bwrap,
        python_root=runtime.python_root,
        libraries=runtime.libraries,
        resolver_address=resolver.address,
        resolver_port=resolver.port,
        resolver_custody_statement="Synthetic resolver confined to this proof's loopback-only namespace.",
        ca_file=trust,
    )
    return ScoutProfile.model_validate(values)


@asynccontextmanager
async def _database(socket_directory: Path) -> AsyncGenerator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "postgresql+asyncpg://scout:fixture@/scout",
        connect_args={
            "host": str(socket_directory),
            "port": 5432,
            "ssl": False,
            "direct_tls": False,
            "target_session_attrs": "any",
            "krbsrvname": "postgres",
            "gsslib": "gssapi",
            "timeout": 5,
            "command_timeout": 5,
        },
    )
    tables = cast(
        "list[Table]",
        [
            Session.__table__,
            Run.__table__,
            Consent.__table__,
            RunDelivery.__table__,
            Step.__table__,
            ScoutBudget.__table__,
            ScoutAttempt.__table__,
        ],
    )
    tables = with_referenced_tables(tables)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Run.metadata.drop_all, tables=tables)
            await connection.run_sync(Run.metadata.create_all, tables=tables)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        async with asyncio.timeout(10):
            await engine.dispose()


async def _settlement(
    factory: async_sessionmaker[AsyncSession], assembly: ScoutWorkflowFixture, *, revoked: bool
) -> ScoutSettlement:
    state = assembly.context.state
    assert state.review is not None
    async with factory() as session:
        row = await session.get(ScoutAttempt, state.review.attempt_id)
        assert row is not None
        assert row.settlement_bytes is not None
        settlement = ScoutSettlement.model_validate_json(row.settlement_bytes)
        assert row.status == settlement.outcome == ("refused" if revoked else "succeeded")
        assert row.execution_enqueue_seq == 1
        assert row.claim_id is not None
        assert row.receipt_id == settlement.receipt_id
        assert settlement.sockets == "closed"
        assert settlement.child == ("not_started" if revoked else "reaped")
        assert settlement.usage.connects == 3
        assert settlement.usage.within(assembly.profile.allowance)
        evidence = json.loads(settlement.handoff_evidence)
        assert evidence["claim_id"] == str(row.claim_id)
        assert evidence["preparation_digest"] == row.preparation_digest == state.review.preparation_digest
        handoffs = evidence["handoffs"]
        admitted = [item for item in handoffs if item["outcome"] in {"accepted", "blocked"}]
        assert all(item["authorized"] for item in admitted)
        assert settlement.usage.connects == sum(item["phase"] == "connect" for item in admitted)
        assert settlement.usage.transmissions == sum(item["phase"] != "connect" for item in admitted)
        assert settlement.usage.wire_bytes == sum(item["accepted_bytes"] or 0 for item in handoffs)
        assert sum(item["accepted_bytes"] or 0 for item in handoffs if item["phase"] == "dns") > 0
        assert sum(item["accepted_bytes"] or 0 for item in handoffs if item["phase"] == "tls") > 0
        assert _SOURCE.encode() not in settlement.handoff_evidence
        if revoked:
            assert handoffs[-1]["refusal"] == FetchCode.EGRESS
            assert not any(item["phase"] == "http" and item["accepted_bytes"] for item in handoffs)
            assert "extraction" not in evidence
        else:
            assert state.receipt_id == row.receipt_id
            assert state.receipt_digest == sha256(row.settlement_bytes).hexdigest()
            http = [item for item in handoffs if item["phase"] == "http"]
            assert http
            assert sum(item["accepted_bytes"] or 0 for item in http) > 0
            expected = serialize_get(preflight_destination(_URL))
            assert {item["application_digest"] for item in http} == {sha256(expected).hexdigest()}
            assert evidence["extraction"]["source_digest"] == sha256(network.BODY).hexdigest()
        budgets = list((await session.scalars(select(ScoutBudget))).all())
        assert {row.scope for row in budgets} == {"host", "binding"}
        for budget in budgets:
            assert budget.active_claims == 0
            for dimension in ("connects", "transmissions", "wire_bytes"):
                assert getattr(budget, dimension + "_reserved") == 0
                assert getattr(budget, dimension + "_used") == getattr(settlement.usage, dimension)
        deliveries = list(
            (
                await session.scalars(
                    select(RunDelivery).where(RunDelivery.run_id == state.run_id).order_by(RunDelivery.enqueue_seq)
                )
            ).all()
        )
        assert [(row.enqueue_seq, row.state, row.resume) for row in deliveries] == [
            (0, "settled", False),
            (1, "claimed", True),
        ]
    return settlement


def _assert_no_contact(
    fixture: network.ScoutNetworkFixture, assembly: ScoutWorkflowFixture, processes: list[asyncio.subprocess.Process]
) -> None:
    assert not fixture.queries
    assert fixture.received_dns_bytes == 0
    assert fixture.dns_connections == 0
    assert not fixture.sni
    assert fixture.received_http_bytes == 0
    assert not processes
    assert not assembly.model_requests


async def _passage(
    factory: async_sessionmaker[AsyncSession],
    fixture: network.ScoutNetworkFixture,
    profile: ScoutProfile,
    processes: list[asyncio.subprocess.Process],
    *,
    revoked: bool,
) -> dict[str, object]:
    assembly = await assemble_workflow(factory, profile=profile, prompt=_PROMPT, answer=_ANSWER)
    _assert_no_contact(fixture, assembly, processes)
    await approve_workflow(assembly, expected_url=_URL)
    _assert_no_contact(fixture, assembly, processes)
    ctx = assembly.context
    if revoked:
        fixture.on_sni = assembly.access.revoke
        assert ctx.state.review is not None
        with pytest.raises(FetchError) as error:
            await assembly.service.acquire(run_id=ctx.state.run_id, binding=ctx.state.scout, review=ctx.state.review)
        assert error.value.code is FetchCode.EGRESS
        assert fixture.on_sni is None
        assert assembly.model_requests == []
        assert processes == []
    else:
        assert isinstance(await AcquireAndAnswerPage().run(ctx), SettlePageAnswer)
        assert ctx.state.answer == _ANSWER
        assert len(processes) == 1
        assert processes[0].returncode == 0
        assert len(assembly.model_requests) == 1
        assert _SOURCE.encode() in assembly.model_requests[0]
        assert _SOURCE not in ctx.state.model_dump_json()
        result = await SettlePageAnswer().run(ctx)
        assert result.data.answer == _ANSWER
        retained = await assembly.turns.get_session(ctx.state.session_id)
        assert retained is not None
        assert retained.turns[-1].content == _ANSWER
        assert _SOURCE not in json.dumps(retained.message_history)
    await fixture.settle()
    assert fixture.queries == [(network.HOSTNAME + ".", dns.rdatatype.A), (network.HOSTNAME + ".", dns.rdatatype.AAAA)]
    assert fixture.sni == [network.HOSTNAME]
    assert fixture.requests == ([] if revoked else [serialize_get(preflight_destination(_URL))])
    if revoked:
        assert fixture.received_http_bytes == 0
    settlement = await _settlement(factory, assembly, revoked=revoked)
    if not revoked:
        _, reconstructed = workflow_service(factory, profile, assembly.authorizer, assembly.ledger, assembly.consents)
        before = (len(fixture.queries), fixture.received_http_bytes, len(processes), len(assembly.model_requests))
        assert ctx.state.review is not None
        for service in (assembly.service, reconstructed):
            with pytest.raises(ScoutWorkflowError) as error:
                await service.acquire(run_id=ctx.state.run_id, binding=ctx.state.scout, review=ctx.state.review)
            assert error.value.code is ScoutWorkflowCode.MATERIAL_UNAVAILABLE
        await fixture.settle()
        assert before == (
            len(fixture.queries),
            fixture.received_http_bytes,
            len(processes),
            len(assembly.model_requests),
        )
    return {
        "outcome": settlement.outcome,
        "usage": settlement.usage.model_dump(),
        "child": settlement.child,
        "extraction_processes": len(processes),
        "model_requests": len(assembly.model_requests),
        "http_requests": len(fixture.requests),
        "tls_versions": sorted(fixture.versions),
    }


@pytest.mark.asyncio
async def test_postgres_consent_real_acquisition_and_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    network.require_namespace("LYCHD_REQUIRE_SCOUT_COMPOSED_PROOF")
    runtime = _runtime()
    # Reuse the existing bounded closure inventory without changing its qualification.
    runtime_identity = extraction_qualification._fingerprint(runtime)  # pyright: ignore[reportPrivateUsage]
    fingerprints = _fingerprints()
    receipt: dict[str, Any] = {
        "schema": "scout-composed-local-proof@1",
        "status": "failed",
        "kernel": platform.release(),
        "python": platform.python_version(),
        "openssl": ssl.OPENSSL_VERSION,
        "dependency_versions": {name: version(name) for name in _DEPENDENCIES},
        "network": "isolated-loopback-only",
        "admission": "credential-consent-store-issued-claim",
        "execution": "explicit-service-and-node-choreography",
        "model": "deterministic-FunctionModel",
        "unexercised": [
            "HTTP-routes",
            "SAQ-worker-process",
            "Graph-checkpoint-resume",
            "model-inference",
            "public-Internet",
        ],
        "source_fingerprints": fingerprints,
        "runtime_identity": runtime_identity,
        "identity_boundary": "Critical source and test closure plus selected extractor runtime; not an atomic transitive environment snapshot or repeated hostile-runtime qualification.",
        "passages": {},
    }
    original = asyncio.create_subprocess_exec
    processes: list[asyncio.subprocess.Process] = []

    async def record(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    try:
        with isolated_postgres() as database:
            receipt["database"] = database.evidence
            async with asyncio.timeout(60):
                certificate, key = await asyncio.to_thread(
                    network.certificate, tmp_path, "composed", network.HOSTNAME, include_ip=False
                )
                for revoked in (False, True):
                    processes.clear()
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(certificate, key)
                    context.set_alpn_protocols(["http/1.1"])
                    fixture = network.ScoutNetworkFixture(context, context)
                    fixture.response = network.response("length")
                    try:
                        resolver = await fixture.start()
                        async with _database(database.socket_directory) as factory:
                            with monkeypatch.context() as patch:
                                patch.setattr(scout_extraction.asyncio, "create_subprocess_exec", record)
                                receipt["passages"]["revoked_at_sni" if revoked else "success"] = await _passage(
                                    factory,
                                    fixture,
                                    _profile(runtime, resolver, certificate),
                                    processes,
                                    revoked=revoked,
                                )
                    finally:
                        await fixture.close()
                assert _fingerprints() == fingerprints
                assert extraction_qualification._fingerprint(runtime) == runtime_identity  # pyright: ignore[reportPrivateUsage]
        receipt["status"] = "passed"
    finally:
        (tmp_path / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
