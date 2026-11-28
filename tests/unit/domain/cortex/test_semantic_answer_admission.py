"""Effect-free semantic admission, durable reconstruction and composition fences."""
# The persistence/composition tests exercise private owner boundaries without running their hosts.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import ValidationError

from lychd.agents.router import Intent
from lychd.config.settings.weaver import BridgeCastingSettings, WeaverSettings
from lychd.domain.animation.capabilities import CapabilitySpec, SourceKind
from lychd.domain.animation.embeddings import EmbeddingBinding, EmbeddingProfile
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.archive import ArchiveProfile, ArchiveSubject
from lychd.domain.archive.derivation import GenerationManifest, GenerationRef
from lychd.domain.archive.semantic_service import ArchiveSemanticService
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import DbRunLedger, InMemoryRunLedger, _intent_payload
from lychd.domain.cortex.semantic_answer import SemanticAnswerBinding, SemanticAnswerSelection

PROFILE = ArchiveProfile(
    namespace_id=UUID("08f16f45-3ad9-4f40-92a3-afd58488b579"),
    owner_subject=ArchiveSubject(identity="semantic-test-owner"),
    policy_revision="semantic-test@1",
)
EMBEDDING = EmbeddingProfile(
    profile_id="semantic-admission-test@1",
    model_id="fixture-embedding",
    model_sha256="a" * 64,
    image_digest="fixture-image",
    engine_revision="fixture-revision",
    dialect="fixture-dialect",
    conformance_digest="b" * 64,
    query_prefix="Query: ",
    tokenizer="gguf:add_special=true:parse_special=true",
    pooling="last",
    normalization="l2",
    scalar_encoding="float32-le",
    dimension=1024,
    max_input_bytes=4096,
    max_input_tokens=511,
    max_response_bytes=65536,
    timeout_seconds=40,
)
MANIFEST = GenerationManifest(
    archive=PROFILE,
    binding=EmbeddingBinding(capability_key="fixture:embedding:exact", profile_digest=EMBEDDING.digest),
    embedding=EMBEDDING,
)
REFERENCE = GenerationRef(generation_id=UUID("11a67306-e388-4d11-bd80-418f44a2cdcf"), manifest_digest=MANIFEST.digest)
BINDING = SemanticAnswerBinding(min_cosine=0.25, manifest=MANIFEST, generation=REFERENCE)
KEY = "fixture:chat:exact"


def selection() -> BridgeCastingSettings:
    return BridgeCastingSettings(revision="5", capability_key=KEY, semantic=SemanticAnswerSelection(min_cosine=0.25))


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"min_cosine": True},
        {"min_cosine": "0.25"},
        {"min_cosine": float("nan")},
        {"min_cosine": float("inf")},
        {"min_cosine": -1.01},
        {"min_cosine": 1.01},
        {"min_cosine": 0.25, "max_results": True},
        {"min_cosine": 0.25, "max_results": "5"},
        {"min_cosine": 0.25, "max_results": 21},
        {"min_cosine": 0.25, "char_budget": 0},
        {"min_cosine": 0.25, "char_budget": 32001},
        {"min_cosine": 0.25, "char_budget": 8.0},
        {"min_cosine": 0.25, "manifest": MANIFEST},
    ],
)
def test_policy_requires_explicit_finite_threshold_and_existing_exact_bounds(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SemanticAnswerSelection.model_validate(values, strict=False)


def test_binding_is_frozen_and_refuses_a_different_manifest() -> None:
    assert SemanticAnswerSelection(min_cosine=-1).max_results == 5
    assert SemanticAnswerSelection(min_cosine=1).char_budget == 8000
    with pytest.raises(ValidationError, match="frozen"):
        BINDING.min_cosine = 0.5
    with pytest.raises(ValidationError, match="exact configured manifest"):
        SemanticAnswerBinding(
            min_cosine=0.25,
            manifest=MANIFEST,
            generation=REFERENCE.model_copy(update={"manifest_digest": "c" * 64}),
        )


@pytest.mark.parametrize("revision", ["2", "3", "4"])
def test_semantic_policy_is_exclusive_to_five(revision: str) -> None:
    with pytest.raises(ValidationError):
        BridgeCastingSettings.model_validate(
            {"revision": revision, "capability_key": KEY, "semantic": {"min_cosine": 0.25}}
        )


@pytest.mark.parametrize(
    "patch",
    [{"semantic": None}, {"capability_key": None}, {"archive": PROFILE}, {"webcrawler": {}}, {"preference": {}}],
)
def test_revision_five_requires_semantic_and_key_and_rejects_other_profiles(patch: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BridgeCastingSettings.model_validate(selection().model_dump() | patch)


def test_registry_retains_five_but_requires_explicit_boot_selection() -> None:
    from lychd.agents.workflows import BRIDGE_CHAT_SEMANTIC, builtin_workflow_registry

    ordinary = builtin_workflow_registry()
    assert ordinary.default.manifest.revision == "1"
    assert ordinary.get_revision("bridge_chat", "5") is BRIDGE_CHAT_SEMANTIC
    assert not ordinary.is_active("bridge_chat", "5")
    selected = builtin_workflow_registry(weaver=WeaverSettings(bridge=selection()))
    assert selected.default is BRIDGE_CHAT_SEMANTIC
    for revision in ("1", "2", "3", "4"):
        retained = selected.get_revision("bridge_chat", revision)
        assert retained is not None
        assert retained.manifest.revision == revision


@dataclass
class Queue:
    publications: list[dict[str, Any]] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
        self.publications.append({"function": job_or_func, **kwargs})

    async def job(self, job_key: str, /) -> None:
        _ = job_key

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)
        message = "No broker cancellation is expected in these admission cases."
        raise AssertionError(message)


def engine_fixture(**overrides: Any) -> tuple[RunEngine, InMemoryRunLedger, InProcessEventBus, Queue]:
    from lychd.agents.workflows import builtin_workflow_registry

    ledger = InMemoryRunLedger()
    bus = InProcessEventBus(ledger=ledger)
    queue = Queue()
    parameters: dict[str, Any] = {"bridge_capability_key": KEY, "bridge_semantic": BINDING}
    parameters.update(overrides)
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        queues={"runs": queue},
        workflows=builtin_workflow_registry(weaver=WeaverSettings(bridge=selection())),
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        **parameters,
    )
    return engine, ledger, bus, queue


@pytest.mark.asyncio
async def test_admission_pins_full_binding_and_replay_retains_truth_after_config_change() -> None:
    engine, ledger, bus, queue = engine_fixture()
    intent = Intent(session_id="exact-question", prompt="  Exact é\nquestion  ")
    try:
        first = await engine.submit(intent, idempotency_key="semantic-admission-test")
        record = await ledger.get(first.run_id)
        assert record is not None
        assert first.pattern_revision == "5"
        assert record.admitted_semantic == BINDING
        assert record.admitted_capability_key == KEY
        assert record.to_intent().admitted_semantic == BINDING
        assert record.prompt == intent.prompt
        engine.bridge_semantic = BINDING.model_copy(update={"min_cosine": 0.9})
        engine.bridge_capability_key = "changed:chat:other"
        replay = await engine.submit(intent, idempotency_key="semantic-admission-test")
        assert replay.run_id == first.run_id
        retained = await ledger.get(first.run_id)
        assert retained is not None
        assert retained.admitted_semantic == BINDING
        assert retained.admitted_capability_key == KEY
        assert len(queue.publications) == 1
    finally:
        await bus.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("prompt", ["  \n", "invalid\x00query", "x" * 2001, "invalid\ud800query"])
async def test_invalid_query_refuses_before_run_creation_or_queue_publication(prompt: str) -> None:
    engine, ledger, bus, queue = engine_fixture()
    try:
        with pytest.raises(ValidationError):
            await engine.submit(Intent(session_id="invalid", prompt=prompt))
        assert await ledger.list_for_session("invalid") == []
        assert queue.publications == []
    finally:
        await bus.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("overrides", [{"bridge_semantic": None}, {"bridge_capability_key": None}])
async def test_missing_server_binding_refuses_before_queue(overrides: dict[str, Any]) -> None:
    engine, ledger, bus, queue = engine_fixture(**overrides)
    try:
        with pytest.raises(ValueError, match="configured semantic binding"):
            await engine.submit(Intent(session_id="missing", prompt="question"))
        assert await ledger.list_for_session("missing") == []
        assert queue.publications == []
    finally:
        await bus.aclose()


@pytest.mark.asyncio
async def test_caller_cannot_supply_semantic_admission_metadata() -> None:
    engine, ledger, bus, queue = engine_fixture()
    try:
        with pytest.raises(ValueError, match="server-owned"):
            await engine.submit(Intent(session_id="forged", prompt="question", admitted_semantic=BINDING))
        assert await ledger.list_for_session("forged") == []
        assert queue.publications == []
    finally:
        await bus.aclose()


@pytest.mark.asyncio
async def test_json_payload_and_database_reconstruction_retain_binding_and_legacy_absence() -> None:
    ledger = InMemoryRunLedger()
    intent = Intent(session_id="reconstruct", prompt="question", admitted_semantic=BINDING, admitted_capability_key=KEY)
    record = await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=50)
    row = SimpleNamespace(
        id=UUID(record.run_id),
        intent=_intent_payload(intent),
        sigil_name=record.sigil_name,
        workflow_name=record.workflow_name,
        pattern_manifest=record.pattern_manifest,
        source=record.source,
        queue_name=record.queue_name,
        priority=record.priority,
        status=record.status.value,
        attempt=record.attempt,
        enqueue_seq=record.enqueue_seq,
        error=record.error,
        consent_id=record.consent_id,
        delegated_job_id=record.delegated_job_id,
        peer_task_id=record.peer_task_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )
    assert row.intent["admitted_semantic"]["generation"]["generation_id"] == str(REFERENCE.generation_id)
    restored = DbRunLedger._to_record(row)
    assert restored.admitted_semantic == BINDING
    assert restored.to_intent().admitted_semantic == BINDING
    del row.intent["admitted_semantic"]
    assert DbRunLedger._to_record(row).admitted_semantic is None


def assembly_fixture() -> tuple[Any, Any, ArchiveSemanticService, Any]:
    from lychd.config.settings.archive import ArchiveDerivationSettings, ArchiveSettings
    from lychd.config.settings.root import Settings

    settings = Settings.model_construct(
        weaver=WeaverSettings(bridge=selection()),
        archive=ArchiveSettings(
            profile=PROFILE,
            semantic=True,
            derivation=ArchiveDerivationSettings(generation_id=REFERENCE.generation_id, binding=MANIFEST.binding),
        ),
    )
    chat = CapabilitySpec(
        key=KEY,
        animator_name="fixture",
        runtime="fixture",
        source_kind=SourceKind.SOULSTONE,
        family=CapabilityFamily.CHAT,
        model_id="exact",
    )
    embedding = CapabilitySpec(
        key=MANIFEST.binding.capability_key,
        animator_name="fixture",
        runtime="fixture",
        source_kind=SourceKind.SOULSTONE,
        family=CapabilityFamily.EMBEDDING,
        model_id=EMBEDDING.model_id,
        embedding_profile=EMBEDDING,
    )

    def no_effect(*args: Any, **kwargs: Any) -> Any:
        _ = (args, kwargs)
        message = "Readiness, model and store effects are forbidden during composition."
        raise AssertionError(message)

    def require_embedding(binding: EmbeddingBinding, operation: str) -> CapabilitySpec:
        assert binding == MANIFEST.binding
        assert operation == "embed_query"
        return embedding

    def get_capability(key: str) -> CapabilitySpec:
        assert key == KEY
        return chat

    registry = SimpleNamespace(
        require_embedding=require_embedding,
        get_capability=get_capability,
        refresh_capability_state=no_effect,
        activate_capability=no_effect,
    )
    service = ArchiveSemanticService(
        generation_id=REFERENCE.generation_id,
        manifest=MANIFEST,
        store=cast("Any", None),
        authorizer=cast("Any", None),
        dispatcher=cast("Any", None),
    )
    return settings, registry, service, chat


def _subject(_sigil: Any) -> ArchiveSubject:
    return PROFILE.owner_subject


def _other_subject(_sigil: Any) -> ArchiveSubject:
    return ArchiveSubject(identity="another")


def test_composition_reuses_service_identity_without_readiness_or_query_effects() -> None:
    from lychd.interface.web.altar_services import _configured_semantic_answer

    settings, registry, service, _ = assembly_fixture()
    result = _configured_semantic_answer(
        settings=settings,
        selection=selection(),
        registry=registry,
        service=service,
        subject_resolver=lambda _sigil: PROFILE.owner_subject,
    )
    assert result == BINDING


@pytest.mark.parametrize(
    "change",
    [
        "missing-service",
        "missing-resolver",
        "subject",
        "generation",
        "profile",
        "binding",
        "portal",
        "family",
        "wildcard",
        "unknown-key",
        "embedding",
    ],
)
def test_composition_refuses_inconsistent_or_nonlocal_admission(change: str) -> None:
    from lychd.interface.web.altar_services import _configured_semantic_answer

    settings, registry, service, chat = assembly_fixture()
    resolver: Callable[[Any], ArchiveSubject] | None = _subject
    if change == "missing-service":
        service = None
    elif change == "missing-resolver":
        resolver = None
    elif change == "subject":
        resolver = _other_subject
    elif change == "generation":
        settings.archive.derivation.generation_id = UUID(int=1)
    elif change == "profile":
        settings.archive.profile = PROFILE.model_copy(update={"policy_revision": "different"})
    elif change == "binding":
        settings.archive.derivation.binding = MANIFEST.binding.model_copy(update={"capability_key": "other"})
    else:
        updates = {
            "portal": {"source_kind": SourceKind.PORTAL},
            "family": {"family": CapabilityFamily.EMBEDDING},
            "wildcard": {"model_id": "*"},
            "unknown-key": {"key": "another:chat:key"},
        }
        if change == "embedding":

            def missing_embedding(_binding: EmbeddingBinding, _operation: str) -> SimpleNamespace:
                return SimpleNamespace(embedding_profile=None)

            registry.require_embedding = missing_embedding
        else:

            def changed_capability(_key: str) -> CapabilitySpec:
                return chat.model_copy(update=updates[change])

            registry.get_capability = changed_capability
    with pytest.raises(ValueError, match="Semantic Bridge"):
        _configured_semantic_answer(
            settings=settings,
            selection=selection(),
            registry=registry,
            service=service,
            subject_resolver=resolver,
        )


@pytest.mark.parametrize("change", ["memory", "no-operator", "no-semantic"])
def test_composition_requires_postgres_local_operator_and_independent_semantic_opt_in(change: str) -> None:
    from lychd.interface.web.altar_services import _configured_castings

    settings, _, _, _ = assembly_fixture()
    profile = "memory" if change == "memory" else "postgres"
    access = None if change == "no-operator" else cast("Any", object())
    if change == "no-semantic":
        settings.archive.semantic = False
    with pytest.raises(ValueError, match="Semantic Bridge"):
        _configured_castings(
            settings=settings,
            profile=profile,
            operator_access=access,
            workflows=None,
            delegated_runtime_adapters=(),
        )


def test_substrate_passes_the_same_semantic_service_and_maps_the_persisted_sigil() -> None:
    from lychd.domain.archive import ArchiveRefused
    from lychd.domain.codex.sigil import Sigil, default_local_sigil
    from lychd.domain.cortex.substrate import RunSubstrate
    from lychd.interface.web.archive_access import LocalArchivePolicy

    _, _, service, _ = assembly_fixture()
    policy = LocalArchivePolicy(profile=PROFILE, caller=default_local_sigil())
    inert = cast("Any", None)
    substrate = RunSubstrate(
        ledger=inert,
        bus=inert,
        workflows=inert,
        orchestrator=inert,
        dispatcher=inert,
        context=inert,
        fragments=inert,
        turns=inert,
        forge=inert,
        archive_semantic=service,
        archive_subject_resolver=policy.subject_for,
    )
    local = substrate.build_services(sigil=default_local_sigil())
    assert local.archive_semantic is service
    assert local.archive_subject_provider is not None
    assert local.archive_subject_provider() == PROFILE.owner_subject
    other = substrate.build_services(sigil=Sigil(name="other", scopes=frozenset({"*"})))
    assert other.archive_subject_provider is not None
    with pytest.raises(ArchiveRefused, match="local_subject"):
        other.archive_subject_provider()
