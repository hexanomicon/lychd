"""Boundaries and actual agent assembly with inert Pydantic AI responses."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, Literal, cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from lychd.agents.context_limits import limit_model_requests
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.compositions.creation.schemas import (
    INPUT_TOKENS,
    OUTPUT_TOKENS,
    CaseView,
    ContinueRequest,
    CreationRefused,
    ExternalAssessment,
    InvestigationRequest,
    OwnerDecision,
    canonical,
    decode,
    digest,
    feedback_target,
    validate_annotations,
    validate_output,
)
from lychd.compositions.creation.services import (
    CONSTRUCTOR,
    VERIFIER,
    InvestigationService,
    LocalCreationPolicy,
    ObservedModel,
    Role,
    check_packets,
    register_agents,
    require_profile,
    role_packet,
)
from lychd.compositions.creation.workflow import investigation_workflow
from lychd.config.settings.weaver import CreationCastingSettings, WeaverSettings
from lychd.domain.animation.capabilities import CapabilitySpec
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.codex.sigil import Sigil, default_local_sigil
from lychd.domain.cortex.leases import LeaseLedger
from lychd.interface.web.altar_services import _build_creation  # pyright: ignore[reportPrivateUsage]
from tests.support.creation import (
    CreationDispatcher,
    CreationRegistry,
    assessment_document,
    candidate_document,
    capability,
    request_document,
    verdict_document,
)

ACCESS_VALUE = "inert-test-password"


def test_exact_profile_two_budget_manifest_and_selector() -> None:
    service, _common = stage_fixture(StageStore())
    profile = service.profile()
    assert (profile["composition"], profile["revision"], profile["profile"]) == (
        "creation.investigation",
        "2",
        "public-source-qwen@2",
    )
    assert profile["pattern"]["revision"] == "2"
    assert profile["pattern"]["implementation_revision"] == "py.4"
    assert CONSTRUCTOR.instructions_key == "creation-constructor-v3"
    assert VERIFIER.instructions_key == "creation-verifier-v3"
    assert profile["pattern"]["checkpoint_schema"] == "creation-investigation-state-v1"
    assert profile["context_tokens"] == INPUT_TOKENS + OUTPUT_TOKENS == 4096
    assert INPUT_TOKENS == 3584
    assert profile["output_tokens"] == CONSTRUCTOR.max_tokens == VERIFIER.max_tokens == OUTPUT_TOKENS == 512
    assert profile["role_seconds"] == profile["recovery_seconds"] == 30
    assert profile["lifetime_seconds"] == 180
    assert profile["agent_retries"] == profile["sdk_retries"] == CONSTRUCTOR.retries == VERIFIER.retries == 0
    assert profile["precount_available"] is False
    assert WeaverSettings().creation is None
    assert CreationCastingSettings(revision="2", capability_key=capability().key).revision == "2"
    with pytest.raises(ValidationError):
        CreationCastingSettings.model_validate({"revision": "1", "capability_key": capability().key})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_tokens", 256),
        ("max_tokens", 511),
        ("max_tokens", 513),
        ("max_context", 4095),
        ("max_context", 4097),
        ("temperature", 0.1),
        ("top_p", 0.9),
        ("thinking", None),
    ],
)
def test_profile_two_refuses_old_or_nearby_generation_bindings(field: str, value: Any) -> None:
    data = capability().model_dump(mode="json")
    data["generation_profile"][field] = value
    with pytest.raises(CreationRefused, match="unsupported_capability"):
        require_profile(CapabilitySpec.model_validate(data))


def test_selected_assembly_registers_only_profile_two_and_omission_stays_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Exercise the exact private opt-in assembly without opening a database.
    monkeypatch.setattr("lychd.db.engine.get_session_factory", object)
    selection = WeaverSettings(creation=CreationCastingSettings(revision="2", capability_key=capability().key))
    common = {
        "persistence": "postgres",
        "access": LocalOperatorAccess(access_password=ACCESS_VALUE),
        "registry": CreationRegistry(),
        "leases": LeaseLedger(),
        "workflows": builtin_workflow_registry(),
    }
    service, registered, _forge = _build_creation(
        settings=cast("Any", SimpleNamespace(weaver=selection)), **cast("Any", common)
    )
    assert service is not None
    assert registered.get("creation.investigate") is registered.get_revision("creation.investigate", "2")
    assert registered.is_active("creation.investigate", "2")
    assert registered.get_revision("creation.investigate", "1") is None
    disabled, original, _forge = _build_creation(
        settings=cast("Any", SimpleNamespace(weaver=WeaverSettings())), **cast("Any", common)
    )
    assert disabled is None
    assert original is common["workflows"]
    assert original.get("creation.investigate") is None


@pytest.mark.parametrize("change", ["path", "duplicate", "bytes", "public", "question"])
def test_input_boundary_refuses_ambiguous_or_unsupported_public_source(change: str) -> None:
    data = request_document().model_dump(mode="json")
    if change == "path":
        data["sources"][0]["name"] = "../private.py"
    elif change == "duplicate":
        data["sources"] *= 2
    elif change == "bytes":
        data["sources"][0]["text"] = "é" * 2049
    elif change == "public":
        data["public_material"] = 1
    else:
        data["question"] = "é" * 257
    with pytest.raises((ValidationError, CreationRefused)):
        InvestigationRequest.model_validate(data)


def test_duplicate_keys_and_citation_byte_spans_are_deterministic_not_a_semantic_oracle() -> None:
    with pytest.raises(CreationRefused):
        decode(b'{"question":"one","question":"two"}')
    request = request_document()
    # This intentionally wrong counterexample passes the citation gate; the separate verdict refutes its predicate.
    receipt = decode(validate_output(request, candidate_document()))
    span = receipt["citations"][0]
    assert span["start"] == 0
    assert span["stop"] == len(request.sources[0].text.encode())
    assert receipt["semantic_correctness"] == "not_established"
    bad = candidate_document().model_dump(mode="json")
    bad["findings"][0]["citations"][0]["last_line"] = 3
    with pytest.raises(CreationRefused, match="citation_span"):
        validate_output(request, type(candidate_document()).model_validate(bad))
    assert verdict_document().disposition == "rejected"


@pytest.mark.parametrize("role", ["constructor", "verifier"])
def test_role_packet_line_counts_preserve_utf8_sources_and_match_strict_byte_spans(role: Role) -> None:
    data = request_document().model_dump(mode="json")
    data["sources"] = [
        {"name": "crlf.py", "text": "a\r\nb\r\n"},
        {"name": "unicode.py", "text": "\u03b1\u2028\u03b2\n\u7d42"},
        {"name": "carriage.py", "text": "a\rb"},
        {"name": "single.py", "text": "終"},
        {"name": "empty.py", "text": ""},
    ]
    request = InvestigationRequest.model_validate(data)
    before = canonical(request)
    counts = {"crlf.py": 2, "unicode.py": 2, "carriage.py": 2, "single.py": 1, "empty.py": 0}
    candidate = candidate_document().model_dump(mode="json")
    candidate["findings"][0]["citations"] = [{"source": "crlf.py", "first_line": 2, "last_line": 2}]
    packet = decode(role_packet(request, role, candidate if role == "verifier" else None))
    assert packet["user"]["line_counts"] == counts
    assert canonical(packet["user"]["request"]) == before == canonical(request)
    assert [source["text"].encode("utf-8") for source in packet["user"]["request"]["sources"]] == [
        b"a\r\nb\r\n",
        b"\xce\xb1\xe2\x80\xa8\xce\xb2\n\xe7\xb5\x82",
        b"a\rb",
        b"\xe7\xb5\x82",
        b"",
    ]
    assert packet["user"]["candidate"] == (candidate if role == "verifier" else None)
    assert "inclusive 1-based" in packet["instructions"]
    assert "1 <= first_line <= last_line <= line_counts[source]" in packet["instructions"]
    check_packets(request)
    output = candidate_document() if role == "constructor" else verdict_document()
    spans = {"crlf.py": (3, 6), "unicode.py": (8, 11), "carriage.py": (2, 3), "single.py": (0, 3)}
    for name, count in counts.items():
        document = output.model_dump(mode="json")
        document["findings"][0]["citations"] = [{"source": name, "first_line": max(1, count), "last_line": count + 1}]
        with pytest.raises(CreationRefused, match="citation_span"):
            validate_output(request, type(output).model_validate(document))
        if count:
            document["findings"][0]["citations"][0].update(first_line=count, last_line=count)
            span = decode(validate_output(request, type(output).model_validate(document)))["citations"][0]
            assert (span["start"], span["stop"]) == spans[name]


def test_role_policy_requires_actual_current_marker_not_sigil_or_reconstructed_fields() -> None:
    access = LocalOperatorAccess(access_password=ACCESS_VALUE)
    actual = access.authenticate(username=b"magus", password=b"inert-test-password")
    assert actual is not None
    policy = LocalCreationPolicy(access)
    fake = LocalOperatorAuthentication(
        subject=actual.subject, authentication_generation=actual.authentication_generation
    )
    for marker, principal in [(fake, default_local_sigil()), (actual, Sigil(name="scope-only", scopes=frozenset()))]:
        with pytest.raises(CreationRefused, match="local_authority"):
            policy.http(marker, principal, "read")
    assert policy.http(actual, default_local_sigil(), "read") is actual
    access.revoke()
    with pytest.raises(CreationRefused, match="local_authority"):
        policy.http(actual, default_local_sigil(), "read")


class StageStore:
    """Only records boundary ordering; PostgreSQL tests own transaction/replay evidence."""

    def __init__(self) -> None:
        self.view: CaseView | None = None
        self.events: list[str] = []
        self.responses: list[bytes] = []
        self.usages: list[dict[str, Any]] = []
        self.failures: list[str] = []
        self.cancelled = False

    async def ready(self, _admission_id: UUID, _run_id: str) -> CaseView:
        assert self.view is not None
        return self.view

    async def claim(self, _admission_id: UUID, _run_id: str, role: str, _packet: bytes) -> UUID:
        self.events.append(f"claim:{role}")
        return uuid4()

    async def complete(self, _attempt_id: UUID, response: bytes, usage: dict[str, Any]) -> None:
        self.events.append("complete")
        self.responses.append(response)
        self.usages.append(usage)

    async def overflow(self, _attempt_id: UUID, metadata: dict[str, Any]) -> None:
        self.events.append("overflow")
        assert metadata["response_length"] > 65536

    async def adopt(self, _attempt_id: UUID, _run_id: str, output: bytes, _receipt: bytes) -> None:
        assert self.responses
        assert self.events[-1] == "complete"
        if self.cancelled:
            code = "run_fence"
            raise CreationRefused(code)
        self.events.append("adopt")
        assert self.view is not None
        document = decode(output)
        field = "verdict" if "disposition" in document else "candidate"
        self.view = self.view.model_copy(update={field: document})

    async def fail(self, _admission_id: UUID, reason: str, _attempt_id: UUID | None) -> None:
        self.events.append("fail")
        self.failures.append(reason)


def stage_fixture(store: StageStore) -> tuple[InvestigationService, Any]:
    access = LocalOperatorAccess(access_password=ACCESS_VALUE)
    policy = LocalCreationPolicy(access)
    leases = LeaseLedger()
    service = InvestigationService(
        store=store, policy=policy, registry=CreationRegistry(), leases=leases, capability_key=capability().key
    )
    investigation_workflow(service)
    request = request_document()
    store.view = CaseView(
        case_id=request.request_id,
        request_digest=digest(canonical(request)),
        profile_digest=digest(canonical(service.profile())),
        status="reserved",
        deadline=(datetime.now(UTC) + timedelta(seconds=180)).isoformat(),
        slot_encumbered=True,
        request=request,
        profile=service.profile(),
        admissions=(),
        attempts=(),
        candidate=None,
        candidate_digest=None,
        verdict=None,
        reason=None,
    )
    forge = default_forge()
    register_agents(forge)
    common = SimpleNamespace(
        forge=forge, dispatcher=None, orchestrator=None, context=None, sigil_provider=default_local_sigil
    )
    return service, common


@pytest.mark.asyncio
async def test_two_real_agent_assemblies_have_fresh_messages_and_custody_before_adoption() -> None:
    store = StageStore()
    service, common = stage_fixture(store)
    messages: list[bytes] = []

    async def respond(history: Any, info: Any) -> ModelResponse:
        assert info.model_settings["max_tokens"] == 512
        assert info.model_settings["temperature"] == 0
        assert info.model_settings["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
        user_prompt = next(part for message in history for part in message.parts if isinstance(part, UserPromptPart))
        assert isinstance(user_prompt.content, str)
        user = decode(user_prompt.content.encode("utf-8"))
        assert user["line_counts"] == {"check.py": 2}
        assert user["request"] == cast("CaseView", store.view).request.model_dump(mode="json")
        messages.append(ModelMessagesTypeAdapter.dump_json(history))
        output = candidate_document() if len(messages) == 1 else verdict_document()
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "final_result",
                    output.model_dump(mode="json"),
                    tool_call_id="private-constructor-call" if len(messages) == 1 else "review-call",
                )
            ],
            usage=RequestUsage(input_tokens=3584, output_tokens=512),
        )

    common.dispatcher = CreationDispatcher(FunctionModel(respond), service.leases)
    check_packets(cast("CaseView", store.view).request)
    await service.stage(uuid4(), str(uuid4()), "constructor", common)
    await service.stage(uuid4(), str(uuid4()), "verifier", common)
    assert store.events == ["claim:constructor", "complete", "adopt", "claim:verifier", "complete", "adopt"]
    assert CONSTRUCTOR.instructions.encode() in messages[0]
    assert VERIFIER.instructions.encode() in messages[1]
    assert CONSTRUCTOR.instructions.encode() not in messages[1]
    assert b"private-constructor-call" not in messages[1]
    assert candidate_document().summary.encode() in messages[1]
    assert len(store.responses) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["replay", "continue", "claim", "adopt"])
async def test_prior_instruction_and_implementation_closure_cannot_be_reused(
    action: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = StageStore()
    service, common = stage_fixture(store)
    assert store.view is not None
    original = store.view
    historical = decode(canonical(original.profile))
    historical["constructor"]["instructions_digest"] = (
        "0ee1c848c2b03742a64f5be73b7eb9a3ee2e058e641749a63e28b604477cd121"
    )
    historical["verifier"]["instructions_digest"] = "ddd2d1c7b8d3ab25bb09ab9c2ccb290ffcc41e8a06ad3cf90e261f1b7d7ff978"
    historical["pattern"]["implementation_revision"] = "py.3"
    historical["pattern"].pop("digest")
    historical["pattern"]["digest"] = digest(canonical(historical["pattern"]))
    previous = original.model_copy(update={"profile": historical, "profile_digest": digest(canonical(historical))})
    store.view = original if action == "adopt" else previous
    monkeypatch.setattr(store, "read", AsyncMock(return_value=previous), raising=False)
    engine, sessions = SimpleNamespace(submit=AsyncMock()), SimpleNamespace(create_session=AsyncMock())
    authentication = service.policy.access.authenticate(username=b"magus", password=b"inert-test-password")
    calls: list[str] = []
    complete = store.complete

    async def complete_then_restore_prior_pattern(attempt_id: UUID, response: bytes, usage: dict[str, Any]) -> None:
        await complete(attempt_id, response, usage)
        service.pattern = historical["pattern"]

    async def respond(_messages: Any, _info: Any) -> ModelResponse:
        calls.append("constructor")
        return ModelResponse(
            parts=[ToolCallPart("final_result", candidate_document().model_dump(mode="json"))],
            usage=RequestUsage(input_tokens=100, output_tokens=80),
        )

    common.dispatcher = CreationDispatcher(FunctionModel(respond), service.leases)
    if action == "adopt":
        monkeypatch.setattr(store, "complete", complete_then_restore_prior_pattern)
    if action in {"claim", "adopt"}:
        await service.stage(uuid4(), str(uuid4()), "constructor", common)
        assert store.events == (["claim:constructor", "complete", "fail"] if action == "adopt" else ["fail"])
        assert store.failures == ["profile_changed"]
    elif action == "replay":
        with pytest.raises(CreationRefused, match="conflicting_replay"):
            await service.submit(
                previous.request,
                authentication=authentication,
                principal=default_local_sigil(),
                engine=engine,
                sessions=sessions,
            )
        assert store.events == []
    else:
        with pytest.raises(CreationRefused, match="profile_changed"):
            await service.continue_case(
                previous.case_id,
                ContinueRequest(
                    admission_id=uuid4(),
                    request_digest=previous.request_digest,
                    candidate_digest="a" * 64,
                    profile_digest=previous.profile_digest,
                ),
                authentication=authentication,
                principal=default_local_sigil(),
                engine=engine,
                sessions=sessions,
            )
        assert store.events == []
    assert calls == (["constructor"] if action == "adopt" else [])
    assert len(store.responses) == len(common.dispatcher.calls) == (1 if action == "adopt" else 0)
    assert store.view.candidate is None
    assert store.view.verdict is None
    assert not service.leases.active()
    engine.submit.assert_not_awaited()
    sessions.create_session.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["constructor", "verifier"])
@pytest.mark.parametrize("binding", ["changed", "missing"])
async def test_profile_drift_after_complete_model_response_refuses_adoption_without_another_call(
    role: Role, binding: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = StageStore()
    service, common = stage_fixture(store)
    assert store.view is not None
    original_candidate = candidate_document().model_dump(mode="json") if role == "verifier" else None
    store.view = store.view.model_copy(
        update={"candidate": original_candidate, "status": "candidate" if role == "verifier" else "reserved"}
    )
    original_profile = canonical(store.view.profile)
    replacement = capability().model_copy(update={"registrant_id": "changed-registration"})
    assert require_profile(replacement) is replacement
    registry = SimpleNamespace(get_capability=Mock(return_value=replacement if binding == "changed" else None))
    complete = store.complete

    async def complete_then_change(attempt_id: UUID, response: bytes, usage: dict[str, Any]) -> None:
        await complete(attempt_id, response, usage)
        service.registry = registry

    monkeypatch.setattr(store, "complete", complete_then_change)
    output = candidate_document() if role == "constructor" else verdict_document()
    calls: list[str] = []

    async def respond(_messages: Any, _info: Any) -> ModelResponse:
        calls.append(role)
        return ModelResponse(
            parts=[ToolCallPart("final_result", output.model_dump(mode="json"), tool_call_id="complete-call")],
            usage=RequestUsage(input_tokens=100, output_tokens=80),
            finish_reason="stop",
            provider_response_id="complete-before-profile-drift",
        )

    common.dispatcher = CreationDispatcher(FunctionModel(respond), service.leases)
    await service.stage(uuid4(), str(uuid4()), role, common)
    assert calls == [role]
    assert store.events == [f"claim:{role}", "complete", "fail"]
    assert store.failures == ["profile_changed" if binding == "changed" else "unsupported_capability"]
    assert store.view.candidate == original_candidate
    assert store.view.verdict is None
    assert canonical(store.view.profile) == original_profile
    assert len(common.dispatcher.calls) == 1
    assert not service.leases.active()
    registry.get_capability.assert_called_once_with(capability().key)
    assert len(store.responses) == 1
    retained = ModelMessagesTypeAdapter.validate_json(store.responses[0])[0]
    assert isinstance(retained, ModelResponse)
    assert retained.provider_response_id == "complete-before-profile-drift"
    assert retained.finish_reason == "stop"
    assert retained.usage.input_tokens == 100
    assert retained.usage.output_tokens == 80
    assert store.usages == [{"input_tokens": 100, "output_tokens": 80, "precount_available": False}]
    part = retained.parts[0]
    assert isinstance(part, ToolCallPart)
    assert part.tool_call_id == "complete-call"
    assert part.args == output.model_dump(mode="json")


@pytest.mark.asyncio
async def test_cancel_wins_adoption_but_keeps_complete_late_response() -> None:
    store = StageStore()
    service, common = stage_fixture(store)

    async def respond(_history: Any, _info: Any) -> ModelResponse:
        store.cancelled = True
        return ModelResponse(
            parts=[ToolCallPart("final_result", candidate_document().model_dump(mode="json"))],
            usage=RequestUsage(input_tokens=100, output_tokens=80),
        )

    common.dispatcher = CreationDispatcher(FunctionModel(respond), service.leases)
    await service.stage(uuid4(), str(uuid4()), "constructor", common)
    assert store.events == ["claim:constructor", "complete", "fail"]
    assert store.responses
    assert cast("CaseView", store.view).candidate is None


@pytest.mark.asyncio
async def test_complete_response_custody_survives_context_guard_failure() -> None:
    store = StageStore()

    async def before() -> None:
        store.events.append("before")

    async def respond(_messages: Any, _info: Any) -> ModelResponse:
        return ModelResponse(parts=[TextPart("complete")], usage=RequestUsage(input_tokens=4000, output_tokens=3))

    model = FunctionModel(respond)
    observed = ObservedModel(model, store=store, attempt_id=uuid4(), before=before)
    wrapped, _limits = limit_model_requests(
        observed, context_window=4096, output_reserve=OUTPUT_TOKENS, counter_model=model
    )
    assert wrapped is not None
    with pytest.raises(UsageLimitExceeded, match="input_tokens_limit"):
        await wrapped.request([], None, ModelRequestParameters())
    assert store.events == ["before", "complete"]
    assert b"complete" in store.responses[0]


@pytest.mark.asyncio
async def test_invalid_complete_output_gets_no_validation_repair_call() -> None:
    store = StageStore()
    service, common = stage_fixture(store)
    calls: list[str] = []

    async def respond(_messages: Any, _info: Any) -> ModelResponse:
        calls.append("called")
        return ModelResponse(
            parts=[ToolCallPart("final_result", {"wrong": "schema"})],
            usage=RequestUsage(input_tokens=100, output_tokens=20),
        )

    common.dispatcher = CreationDispatcher(FunctionModel(respond), service.leases)
    await service.stage(uuid4(), str(uuid4()), "constructor", common)
    assert calls == ["called"]
    assert store.events == ["claim:constructor", "complete", "fail"]
    assert len(store.responses) == 1
    assert cast("CaseView", store.view).candidate is None


@pytest.mark.asyncio
async def test_oversized_complete_response_keeps_only_bounded_failure_metadata() -> None:
    store = StageStore()

    async def before() -> None:
        store.events.append("before")

    async def respond(_messages: Any, _info: Any) -> ModelResponse:
        return ModelResponse(parts=[TextPart("x" * 65537)], usage=RequestUsage(input_tokens=100, output_tokens=256))

    model = ObservedModel(FunctionModel(respond), store=store, attempt_id=uuid4(), before=before)
    with pytest.raises(CreationRefused, match="raw_response_bytes"):
        await model.request([], None, ModelRequestParameters())
    assert store.events == ["before", "overflow"]
    assert store.responses == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["constructor", "verifier"])
@pytest.mark.parametrize("case", ["length", "duplicate_top", "duplicate_nested"])
async def test_raw_final_result_refusal_keeps_custody_without_adoption_or_retry(
    role: Role, case: Literal["length", "duplicate_top", "duplicate_nested"]
) -> None:
    store = StageStore()
    service, common = stage_fixture(store)
    assert store.view is not None
    original_candidate = candidate_document().model_dump(mode="json") if role == "verifier" else None
    store.view = store.view.model_copy(
        update={"candidate": original_candidate, "status": "candidate" if role == "verifier" else "reserved"}
    )
    output = candidate_document() if role == "constructor" else verdict_document()
    arguments = canonical(output).decode("utf-8")
    if case == "duplicate_top":
        if role == "constructor":
            arguments = arguments.replace('"summary":', '"summary":"discarded","summary":', 1)
        else:
            arguments = arguments.replace(
                '"disposition":"rejected"', '"disposition":"rejected","disposition":"accepted"', 1
            )
    elif case == "duplicate_nested":
        line_field = f'"first_line":{output.findings[0].citations[0].first_line}'
        arguments = arguments.replace(line_field, f'"first_line":99,{line_field}', 1)
    calls: list[str] = []

    async def respond(_messages: Any, _info: Any) -> ModelResponse:
        calls.append("called")
        return ModelResponse(
            parts=[ToolCallPart("final_result", arguments, tool_call_id="retained-call")],
            usage=RequestUsage(input_tokens=100, output_tokens=256),
            finish_reason="length" if case == "length" else None,
            provider_response_id="retained-response",
            provider_details={"evidence": "retain this complete metadata"},
        )

    common.dispatcher = CreationDispatcher(FunctionModel(respond), service.leases)
    await service.stage(uuid4(), str(uuid4()), role, common)
    assert calls == ["called"]
    assert store.events == [f"claim:{role}", "complete", "fail"]
    assert store.failures == ["output_length" if case == "length" else "invalid_json"]
    assert store.usages == [{"input_tokens": 100, "output_tokens": 256, "precount_available": False}]
    assert store.view.candidate == original_candidate
    assert store.view.verdict is None
    assert len(store.responses) == 1
    retained = ModelMessagesTypeAdapter.validate_json(store.responses[0])[0]
    assert isinstance(retained, ModelResponse)
    assert retained.provider_response_id == "retained-response"
    assert retained.provider_details == {"evidence": "retain this complete metadata"}
    assert retained.finish_reason == ("length" if case == "length" else None)
    assert retained.usage.input_tokens == 100
    assert retained.usage.output_tokens == 256
    part = retained.parts[0]
    assert isinstance(part, ToolCallPart)
    assert part.tool_call_id == "retained-call"
    assert part.args == arguments


def test_feedback_hashes_actual_source_and_criteria_bytes_and_preserves_report() -> None:
    request = request_document()
    candidate, verdict = canonical(candidate_document()), canonical(verdict_document())
    target = feedback_target(canonical(request), b'{"revision":"2"}', candidate, verdict)
    changed = request.model_copy(update={"sources": (request.sources[0].model_copy(update={"text": "changed\n"}),)})
    other = feedback_target(canonical(changed), b'{"revision":"2"}', candidate, verdict)
    assert target.sources_digest != other.sources_digest
    assert target.criteria_digest == other.criteria_digest
    assessment = assessment_document(target)
    assert (
        ExternalAssessment.model_validate(decode(canonical(assessment))).report.encode() == assessment.report.encode()
    )
    validate_annotations(request, assessment)
    annotation = candidate_document().findings[0]
    validate_annotations(request, assessment.model_copy(update={"submitter_annotations": (annotation,)}))
    for mappings, code in [
        ((annotation, annotation), "criterion_binding"),
        ((annotation.model_copy(update={"criterion": "invented"}),), "criterion_binding"),
        (
            (
                annotation.model_copy(
                    update={"citations": (annotation.citations[0].model_copy(update={"source": "foreign"}),)}
                ),
            ),
            "citation_source",
        ),
        (
            (
                annotation.model_copy(
                    update={"citations": (annotation.citations[0].model_copy(update={"last_line": 3}),)}
                ),
            ),
            "citation_span",
        ),
    ]:
        with pytest.raises(CreationRefused, match=code):
            validate_annotations(request, assessment.model_copy(update={"submitter_annotations": mappings}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("report", "č" * 4097),
        ("reviewer_label", "č" * 65),
        ("reviewer_revision", "č" * 65),
        ("exposure", ["č" * 97]),
        ("limitations", ["x"] * 5),
    ],
)
def test_feedback_intake_enforces_utf8_bounds(field: str, value: Any) -> None:
    target = feedback_target(canonical(request_document()), b"{}", b"{}", b"{}")
    body = assessment_document(target).model_dump(mode="json")
    body[field] = value
    with pytest.raises((CreationRefused, ValidationError)):
        ExternalAssessment.model_validate(body)
    decision = {
        "decision_id": str(uuid4()),
        "assessment_id": body["assessment_id"],
        "assessment_digest": "a" * 64,
        "target": target.model_dump(),
        "action": "hold",
        "reason": "č" * 513,
    }
    with pytest.raises((CreationRefused, ValidationError)):
        OwnerDecision.model_validate(decision)


@pytest.mark.asyncio
async def test_feedback_service_needs_no_current_profile_or_execution_collaborators() -> None:
    store = SimpleNamespace(append_feedback=AsyncMock(return_value="retained"), feedback=AsyncMock(return_value="view"))
    service, _common = stage_fixture(StageStore())
    service.store = store
    service.registry = SimpleNamespace(get_capability=Mock(side_effect=AssertionError("no profile lookup")))
    actor = service.policy.access.authenticate(username=b"magus", password=b"inert-test-password")
    target = feedback_target(canonical(request_document()), b"{}", b"{}", b"{}")
    assessment = assessment_document(target)
    case_id = uuid4()
    assert (
        await service.assess(case_id, assessment, authentication=actor, principal=default_local_sigil()) == "retained"
    )
    assert await service.feedback(case_id, authentication=actor, principal=default_local_sigil()) == "view"
    service.policy.access.revoke()
    with pytest.raises(CreationRefused, match="local_authority"):
        await service.assess(case_id, assessment, authentication=actor, principal=default_local_sigil())
    assert store.append_feedback.await_count == 1


@pytest.mark.parametrize(
    ("action", "required"), [("assess", "runs:submit"), ("decide", "runs:submit"), ("feedback", "altar:read")]
)
def test_feedback_policy_requires_actual_marker_and_matching_action_scope(action: str, required: str) -> None:
    access = LocalOperatorAccess(access_password=ACCESS_VALUE)
    policy = LocalCreationPolicy(access)
    actor = access.authenticate(username=b"magus", password=ACCESS_VALUE.encode())
    assert actor is not None
    allowed = Sigil(name="scoped", scopes=frozenset({required}))
    assert policy.http(actor, allowed, action) is actor
    reconstructed = LocalOperatorAuthentication(
        subject=actor.subject, authentication_generation=actor.authentication_generation
    )
    for marker, principal in [
        (reconstructed, allowed),
        (actor, Sigil(name="scoped", scopes=frozenset())),
        (None, allowed),
    ]:
        with pytest.raises(CreationRefused, match="local_authority"):
            policy.http(marker, principal, action)
