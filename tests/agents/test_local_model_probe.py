"""Real probe assembly and cleanup with inert HTTP observations and model responses."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, cast

import httpx
import httpx2
import pytest
from click.testing import CliRunner
from pydantic import ValidationError
from pydantic_ai.models import override_allow_model_requests
from scripts import local_model_probe as probe

if TYPE_CHECKING:
    import respx

_URL = "http://127.0.0.1:28761/v1"
_MODEL = "synthetic-probe-model"


def profile(**changes: Any) -> probe.ProbeProfile:
    return probe.ProbeProfile.model_validate(
        {"base_url": _URL, "model_id": _MODEL, "source_revision": "a" * 40, **changes}
    )


def response(
    content: str | None,
    *,
    calls: list[dict[str, object]] | None = None,
    model_id: str = _MODEL,
    finish_reason: str | None = None,
) -> httpx2.Response:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if calls is not None:
        message["tool_calls"] = calls
    return httpx2.Response(
        200,
        json={
            "id": "synthetic-completion",
            "object": "chat.completion",
            "created": 0,
            "model": model_id,
            "choices": [
                {"index": 0, "finish_reason": finish_reason or ("tool_calls" if calls else "stop"), "message": message}
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
        },
    )


def tool_call(value: str = "cobalt-731") -> dict[str, object]:
    return {
        "id": "synthetic-tool-call",
        "type": "function",
        "function": {"name": "probe_echo", "arguments": json.dumps({"value": value})},
    }


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://example.com/v1",
        "http://localhost:28761/v1",
        "http://127.0.0.1/v1",
        "http://secret@127.0.0.1:28761/v1",
        f"{_URL}?key=secret",
        f"{_URL}#secret",
        "http://127.0.0.1:28761/other",
        " http://127.0.0.1:28761/v1",
    ],
)
def test_profile_refuses_ambient_or_nonlocal_routes(endpoint: str) -> None:
    with pytest.raises(ValidationError):
        profile(base_url=endpoint)


def test_profile_requires_exact_identity_and_input_budget() -> None:
    for changes in ({"model_id": " model "}, {"source_revision": "main"}, {"context_tokens": 1024, "max_tokens": 1024}):
        with pytest.raises(ValidationError):
            profile(**changes)
    assert profile(base_url="http://[::1]:28761/v1/").base_url == "http://[::1]:28761/v1"


@pytest.fixture
def inventory(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{_URL}/models").mock(return_value=httpx.Response(200, json={"data": [{"id": _MODEL}]}))


@pytest.mark.asyncio
async def test_real_registered_dispatch_forge_and_observed_tool_round(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
) -> None:
    from lychd.config.settings.root import Settings

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("The probe reached ambient installation Settings")

    monkeypatch.setattr(Settings, "settings_customise_sources", forbidden)
    clients: list[httpx2.AsyncClient] = []
    requests: list[dict[str, Any]] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        assert str(request.url) == f"{_URL}/chat/completions"
        assert request.headers["authorization"] == "Bearer api-key-not-set"
        payload: dict[str, Any] = json.loads(request.content)
        requests.append(payload)
        if not payload.get("tools"):
            return response("cobalt-731")
        tool_results = [item for item in payload["messages"] if item["role"] == "tool"]
        if tool_results:
            return response(tool_results[-1]["content"])
        return response(None, calls=[tool_call()])

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)
        clients.append(item)
        return item

    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-secret")
    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())
    assert receipt["status"] == "passed", receipt
    assert receipt["registrant_id"] == "builtin:animator/vllm"
    assert receipt["inventory_matched_model_id"] == _MODEL
    assert receipt["tool_executions"] == 1
    assert receipt["active_leases_after"] == 0
    assert len(requests) == 3
    assert all(item.is_closed for item in clients)
    assert all(item["max_completion_tokens"] == 256 for item in requests)


@pytest.mark.asyncio
@pytest.mark.parametrize("models", [[], [{"id": "different-model"}]])
async def test_missing_model_refuses_before_inference(
    respx_mock: respx.MockRouter,
    models: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respx_mock.get(f"{_URL}/models").mock(return_value=httpx.Response(200, json={"data": models}))

    def forbidden() -> Any:
        pytest.fail("Missing inventory model must not construct an inference client")

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", forbidden)
    receipt = await probe.run_probe(profile())
    assert receipt["status"] == "failed"
    assert receipt["stage"] == "text:dispatch"
    assert receipt["active_leases_after"] == 0
    assert receipt["tool_executions"] == 0
    assert receipt["error_type"] == "model_missing"


@pytest.mark.asyncio
async def test_unreachable_endpoint_returns_a_bounded_refusal(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{_URL}/models").mock(side_effect=httpx.ConnectError("private diagnostic"))
    receipt = await probe.run_probe(profile())
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "endpoint_unreachable"
    assert receipt["active_leases_after"] == 0
    assert "private diagnostic" not in json.dumps(receipt)


@pytest.mark.asyncio
async def test_invalid_inventory_is_distinguished_from_unreachable(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{_URL}/models").mock(return_value=httpx.Response(200, json={"data": "invalid"}))
    receipt = await probe.run_probe(profile())
    assert receipt["error_type"] == "inventory_invalid"
    assert receipt["observed_phase"] == "error"
    assert receipt["active_leases_after"] == 0


@pytest.mark.asyncio
async def test_response_model_must_match_inventory_and_request(
    monkeypatch: pytest.MonkeyPatch, inventory: None
) -> None:
    client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda _request: response("cobalt-731", model_id="other-model"))
    )
    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", lambda: client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "response_model_mismatch"
    assert receipt["tool_executions"] == 0
    assert receipt["active_leases_after"] == 0
    assert client.is_closed


@pytest.mark.asyncio
async def test_output_exhaustion_cannot_pass_even_with_the_expected_marker(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
) -> None:
    client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda _request: response("cobalt-731", finish_reason="length"))
    )
    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", lambda: client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "output_limit"
    assert receipt["tool_executions"] == 0
    assert receipt["active_leases_after"] == 0
    assert client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_reply", ["claim", "bad-arguments", "transport"])
async def test_claimed_tool_bad_arguments_and_transport_error_cannot_pass(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
    tool_reply: str,
) -> None:
    clients: list[httpx2.AsyncClient] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        payload: dict[str, Any] = json.loads(request.content)
        if not payload.get("tools"):
            return response("cobalt-731")
        if tool_reply == "transport":
            message = "private provider diagnostic"
            raise httpx2.ConnectError(message)
        if tool_reply == "bad-arguments":
            return response(None, calls=[tool_call("invalid")])
        return response("I executed the tool")

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle))
        clients.append(item)
        return item

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())
    assert receipt["status"] == "failed"
    assert receipt["tool_executions"] == 0
    assert receipt["active_leases_after"] == 0
    assert all(item.is_closed for item in clients)
    assert "private provider diagnostic" not in json.dumps(receipt)


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_deadline_and_cancellation_close_clients_and_release_grants(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
    cancel: bool,  # noqa: FBT001 - parametrized failure mode
) -> None:
    entered = asyncio.Event()
    clients: list[httpx2.AsyncClient] = []

    async def handle(_request: httpx2.Request) -> httpx2.Response:
        entered.set()
        await asyncio.Event().wait()
        return response("unreachable")

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle))
        clients.append(item)
        return item

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        task = asyncio.create_task(probe.run_probe(profile(deadline_seconds=1)))
        await asyncio.wait_for(entered.wait(), timeout=2)
        if cancel:
            task.cancel()
        receipt = await asyncio.wait_for(task, timeout=3)
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == ("cancelled" if cancel else "deadline")
    assert receipt["active_leases_after"] == 0
    assert all(item.is_closed for item in clients)


def test_cli_invalid_profile_never_prints_supplied_credential() -> None:
    result = CliRunner().invoke(
        probe.cli,
        ["--base-url", "http://private-secret@127.0.0.1:28761/v1", "--model-id", _MODEL, "--source-revision", "a" * 40],
    )
    assert result.exit_code == 2
    assert json.loads(result.stdout) == {"status": "failed", "error_type": "invalid_profile"}
    assert "private-secret" not in result.output


@pytest.mark.asyncio
async def test_close_failure_cannot_produce_a_pass(monkeypatch: pytest.MonkeyPatch, inventory: None) -> None:
    class FailingCloseClient(httpx2.AsyncClient):
        async def aclose(self) -> None:
            await super().aclose()
            message = "synthetic close failure"
            raise RuntimeError(message)

    client = FailingCloseClient(transport=httpx2.MockTransport(lambda _request: response("cobalt-731")))
    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", lambda: client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "RuntimeError"
    assert receipt["active_leases_after"] == 0
    assert client.is_closed


@pytest.mark.asyncio
async def test_cancellation_waits_for_shielded_close(monkeypatch: pytest.MonkeyPatch, inventory: None) -> None:
    closing, release = asyncio.Event(), asyncio.Event()

    class HeldCloseClient(httpx2.AsyncClient):
        async def aclose(self) -> None:
            closing.set()
            await release.wait()
            await super().aclose()

    client = HeldCloseClient(transport=httpx2.MockTransport(lambda _request: response("cobalt-731")))
    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", lambda: client)
    with override_allow_model_requests(allow_model_requests=True):
        task = asyncio.create_task(probe.run_probe(profile()))
        await asyncio.wait_for(closing.wait(), timeout=2)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        receipt = await asyncio.wait_for(task, timeout=2)
    assert receipt["error_type"] == "cancelled"
    assert receipt["active_leases_after"] == 0
    assert client.is_closed


def test_cli_separates_json_receipt_from_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run(_profile: probe.ProbeProfile) -> dict[str, object]:
        print("diagnostic")  # noqa: T201 - verify diagnostic redirection
        return {"status": "passed"}

    monkeypatch.setattr(probe, "run_probe", run)
    result = CliRunner().invoke(
        probe.cli,
        ["--base-url", _URL, "--model-id", _MODEL, "--source-revision", "a" * 40],
    )
    assert result.exit_code == 0
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "passed"
    assert len(receipt["probe_sha256"]) == 64
    assert "diagnostic" in result.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["text", "tool-call", "final"])
@pytest.mark.parametrize("finish_reason", ["content_filter", "unknown", "error"])
async def test_noncompletion_never_passes_or_advances_the_probe(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
    stage: str,
    finish_reason: str,
) -> None:
    clients: list[httpx2.AsyncClient] = []
    requests: list[dict[str, Any]] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        payload: dict[str, Any] = json.loads(request.content)
        requests.append(payload)
        if not payload.get("tools"):
            return response("cobalt-731", finish_reason=finish_reason if stage == "text" else "stop")
        tool_results = [item for item in payload["messages"] if item["role"] == "tool"]
        if tool_results:
            return response(tool_results[-1]["content"], finish_reason=finish_reason if stage == "final" else "stop")
        return response(
            None, calls=[tool_call()], finish_reason=finish_reason if stage == "tool-call" else "tool_calls"
        )

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)
        clients.append(item)
        return item

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())

    assert receipt["status"] == "failed", receipt
    assert len(requests) == {"text": 1, "tool-call": 2, "final": 3}[stage]
    assert receipt["tool_executions"] == (1 if stage == "final" else 0)
    assert receipt["active_leases_after"] == 0
    assert all(item.is_closed for item in clients)
    raw_cases = receipt["cases"]
    assert isinstance(raw_cases, list)
    cases = cast("list[dict[str, object]]", raw_cases)
    assert [case["name"] for case in cases] == (["text"] if stage == "text" else ["text", "tool"])
    if stage != "text":
        assert cases[0]["passed"] is True
    failed = cases[-1]
    assert failed["passed"] is False
    prior_responses = 1 if stage == "final" else 0
    # Invalid raw enum values are refused by the SDK before it returns a ModelResponse.
    received = prior_responses + (1 if finish_reason == "content_filter" else 0)
    assert failed["responses_received"] == received
    assert failed["response_model_ids"] == [_MODEL] * received
    reasons = ["tool_call"] if prior_responses else []
    if finish_reason == "content_filter":
        assert receipt["error_type"] == "incomplete_response"
        reasons.append("content_filter")
    assert failed["finish_reasons"] == reasons


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["tool-call", "final"])
async def test_wrong_model_in_tool_round_refuses_before_further_effects(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
    stage: str,
) -> None:
    clients: list[httpx2.AsyncClient] = []
    requests: list[dict[str, Any]] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        payload: dict[str, Any] = json.loads(request.content)
        requests.append(payload)
        if not payload.get("tools"):
            return response("cobalt-731")
        tool_results = [item for item in payload["messages"] if item["role"] == "tool"]
        if tool_results:
            return response(tool_results[-1]["content"], model_id="other-model" if stage == "final" else _MODEL)
        return response(None, calls=[tool_call()], model_id="other-model" if stage == "tool-call" else _MODEL)

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)
        clients.append(item)
        return item

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())

    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "response_model_mismatch"
    assert len(requests) == (2 if stage == "tool-call" else 3)
    assert receipt["tool_executions"] == (0 if stage == "tool-call" else 1)
    assert receipt["active_leases_after"] == 0
    assert all(item.is_closed for item in clients)
    raw_cases = receipt["cases"]
    assert isinstance(raw_cases, list)
    cases = cast("list[dict[str, object]]", raw_cases)
    assert len(cases) == 2
    assert cases[0]["passed"] is True
    failed = cases[1]
    assert failed["passed"] is False
    assert failed["response_model_ids"] == (["other-model"] if stage == "tool-call" else [_MODEL, "other-model"])
    assert failed["finish_reasons"] == (["tool_call"] if stage == "tool-call" else ["tool_call", "stop"])
    assert failed["responses_received"] == (1 if stage == "tool-call" else 2)


@pytest.mark.asyncio
async def test_empty_output_exhaustion_retains_the_observed_response(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
) -> None:
    clients: list[httpx2.AsyncClient] = []
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return response(None, finish_reason="length")

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)
        clients.append(item)
        return item

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())

    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "output_limit"
    assert len(requests) == 1
    assert receipt["tool_executions"] == 0
    assert receipt["active_leases_after"] == 0
    assert all(item.is_closed for item in clients)
    raw_cases = receipt["cases"]
    assert isinstance(raw_cases, list)
    cases = cast("list[dict[str, object]]", raw_cases)
    assert len(cases) == 1
    assert cases[0]["passed"] is False
    assert cases[0]["response_model_ids"] == [_MODEL]
    assert cases[0]["finish_reasons"] == ["length"]
    assert cases[0]["responses_received"] == 1


@pytest.mark.asyncio
async def test_final_deadline_preserves_received_tool_response_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
) -> None:
    clients: list[httpx2.AsyncClient] = []
    requests: list[dict[str, Any]] = []
    final_entered = asyncio.Event()

    async def handle(request: httpx2.Request) -> httpx2.Response:
        payload: dict[str, Any] = json.loads(request.content)
        requests.append(payload)
        if not payload.get("tools"):
            return response("cobalt-731")
        tool_results = [item for item in payload["messages"] if item["role"] == "tool"]
        if tool_results:
            final_entered.set()
            await asyncio.Event().wait()
            return response("unreachable")
        return response(None, calls=[tool_call()])

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)
        clients.append(item)
        return item

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await asyncio.wait_for(probe.run_probe(profile(deadline_seconds=1)), timeout=3)

    assert final_entered.is_set()
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "deadline"
    assert len(requests) == 3
    assert receipt["tool_executions"] == 1
    assert receipt["active_leases_after"] == 0
    assert all(item.is_closed for item in clients)
    raw_cases = receipt["cases"]
    assert isinstance(raw_cases, list)
    cases = cast("list[dict[str, object]]", raw_cases)
    assert len(cases) == 2
    assert cases[0]["passed"] is True
    assert cases[0]["response_model_ids"] == [_MODEL]
    assert cases[0]["finish_reasons"] == ["stop"]
    assert cases[0]["responses_received"] == 1
    assert cases[1]["passed"] is False
    assert cases[1]["response_model_ids"] == [_MODEL]
    assert cases[1]["finish_reasons"] == ["tool_call"]
    assert cases[1]["responses_received"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["text", "tool-call", "final"])
@pytest.mark.parametrize("wire_reason", ["missing", "null"])
async def test_missing_wire_finish_cannot_be_replaced_by_sdk_completion(
    monkeypatch: pytest.MonkeyPatch,
    inventory: None,
    stage: str,
    wire_reason: str,
) -> None:
    clients: list[httpx2.AsyncClient] = []
    requests: list[dict[str, Any]] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        payload: dict[str, Any] = json.loads(request.content)
        requests.append(payload)
        if not payload.get("tools"):
            current_stage = "text"
            completed = response("cobalt-731")
        else:
            tool_results = [item for item in payload["messages"] if item["role"] == "tool"]
            if tool_results:
                current_stage = "final"
                completed = response(tool_results[-1]["content"])
            else:
                current_stage = "tool-call"
                completed = response(None, calls=[tool_call()])
        body: dict[str, Any] = completed.json()
        if current_stage == stage:
            choice: dict[str, Any] = body["choices"][0]
            if wire_reason == "missing":
                choice.pop("finish_reason")
            else:
                choice["finish_reason"] = None
        return httpx2.Response(200, json=body)

    def client() -> httpx2.AsyncClient:
        item = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)
        clients.append(item)
        return item

    monkeypatch.setattr("lychd.domain.animation.model_factory._model_http_client", client)
    with override_allow_model_requests(allow_model_requests=True):
        receipt = await probe.run_probe(profile())

    assert receipt["status"] == "failed", receipt
    assert receipt["error_type"] == "incomplete_response"
    assert len(requests) == {"text": 1, "tool-call": 2, "final": 3}[stage]
    assert receipt["tool_executions"] == (1 if stage == "final" else 0)
    assert receipt["active_leases_after"] == 0
    assert all(item.is_closed for item in clients)
    raw_cases = receipt["cases"]
    assert isinstance(raw_cases, list)
    cases = cast("list[dict[str, object]]", raw_cases)
    assert [case["name"] for case in cases] == (["text"] if stage == "text" else ["text", "tool"])
    if stage != "text":
        assert cases[0]["passed"] is True
        assert cases[0]["provider_finish_reasons"] == ["stop"]
    failed = cases[-1]
    assert failed["passed"] is False
    assert failed["response_model_ids"] == [_MODEL] * (2 if stage == "final" else 1)
    assert failed["responses_received"] == (2 if stage == "final" else 1)
    assert failed["finish_reasons"] == (["tool_call", "stop"] if stage == "final" else ["stop"])
    assert failed["provider_finish_reasons"] == (["tool_calls", None] if stage == "final" else [None])
