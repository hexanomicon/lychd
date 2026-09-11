"""Operator Rune scenarios across real extension assembly, compilation, and grants.

External HTTP, queue delivery, and SDK host fingerprinting are substituted.
These receipts do not prove a live model, container, host transition, or
multimodal execution.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import httpx2
import pydantic_ai.models
import pytest
import respx
from pydantic import ValidationError
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.config.runes.loader import ConfigLoader
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import Settings
from lychd.domain.animation.capabilities import CapabilityPhase
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.model_factory import openai_compatible_provider
from lychd.domain.animation.services.declarations import AnimatorDeclarations, compile_animator_declarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.extensions.host import AssembledExtensions, assemble_extensions
from lychd.ghouls.runs import perform_run
from lychd.interface.web.altar_services import build_altar_services

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class _ConfiguredRuntime:
    settings: Settings
    runes: RuneRegistry
    extensions: AssembledExtensions
    declarations: AnimatorDeclarations
    registry: AnimatorRegistry


def _configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    documents: dict[str, str],
) -> _ConfiguredRuntime:
    """Load operator TOML through the same schema and declaration owners as boot."""
    monkeypatch.setattr("lychd.config.settings.root.PATH_LYCHD_TOML", tmp_path / "lychd.toml")
    builtins = tuple(dict.fromkeys(f"animator/{path.split('/')[0]}" for path in documents))
    settings = Settings.model_validate(
        {
            "server": {"database": {"profile": "memory"}},
            "orchestration": {},
            "extensions": {"builtins": builtins, "crypt": ()},
        }
    )
    extensions = assemble_extensions(settings)
    root = tmp_path / "runes"
    for relative, content in documents.items():
        path = root / "animator" / "soulstones" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    runes = RuneRegistry(ConfigLoader(root).load_all(list(extensions.rune_schemas)))
    declarations = compile_animator_declarations(settings=settings, runes=runes)
    return _ConfiguredRuntime(
        settings=settings,
        runes=runes,
        extensions=extensions,
        declarations=declarations,
        registry=AnimatorRegistry(
            declarations=declarations,
            runtime_adapters=extensions.runtime_adapters,
            portal_definitions=extensions.portal_definitions,
        ),
    )


def _local_http(respx_mock: respx.MockRouter, *, port: int = 20000, models: tuple[str, ...] = ("qwen",)) -> None:
    respx_mock.get(f"http://localhost:{port}/health").respond(json={"status": "ok"})
    inventory = {"data": [{"id": model, "status": {"value": "loaded"}} for model in models]}
    respx_mock.get(f"http://localhost:{port}/models").respond(json=inventory)
    respx_mock.get(f"http://localhost:{port}/v1/models").respond(json=inventory)


@pytest.mark.asyncio
async def test_local_chat_toml_preserves_generation_overlays_through_a_real_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {
            "llamacpp/chat.toml": """
name = "desk"
model_path = "/models/qwen.gguf"
[generation]
max_tokens = 1024
temperature = 0.7
top_p = 0.9
[[models]]
id = "qwen"
path = "/models/qwen.gguf"
[models.generation]
temperature = 0.2
""",
        },
    )
    _local_http(respx_mock)
    leases = LeaseLedger()
    dispatcher = Dispatcher(configured.registry, leases=leases)

    async with dispatcher.lease_grant(family="chat", run_id="operator-turn", requires_tools=True) as grant:
        assert grant.spec.key == "desk:chat:qwen"
        assert isinstance(grant.model, OpenAIChatModel)
        assert grant.model.model_name == "qwen"
        assert grant.model_settings() == {"max_tokens": 1024, "temperature": 0.2, "top_p": 0.9}
        assert grant.toolsets == ()


def test_managed_llamacpp_alias_agrees_with_declared_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {"llamacpp/chat.toml": 'name="desk"\nmodel_path="/models/weights.gguf"\nserved_model_id="public-qwen"\n'},
    )
    _local_http(respx_mock, models=("public-qwen",))
    stone = configured.declarations.soulstones[0]
    adapter = configured.extensions.runtime_adapters[0]
    command = adapter.plan(stone).exec_args
    assert command[command.index("--alias") + 1] == "public-qwen"
    assert [spec.model_id for spec in configured.registry.list_capabilities()] == ["public-qwen"]


def test_managed_llamacpp_context_matches_its_launch_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {"llamacpp/chat.toml": 'name="desk"\nmodel_path="/models/qwen.gguf"\nn_ctx=4096\n'},
    )
    _local_http(respx_mock)
    command = configured.extensions.runtime_adapters[0].plan(configured.declarations.soulstones[0]).exec_args
    assert command[command.index("-c") + 1] == "4096"
    assert configured.registry.list_capabilities()[0].generation_profile.max_context == 4096


@pytest.mark.parametrize(
    ("configuration", "expected"),
    [
        ("n_ctx=8192\nn_parallel=4\n", 2048),
        ('n_ctx=8192\nn_parallel=4\nextra_args=["--parallel", "2"]\n', 4096),
        ('n_ctx=8192\nn_parallel=4\nextra_args=["--kv-unified-per-slot", "1024"]\n', 1024),
        ('n_ctx=8192\nn_parallel=4\n[env_vars]\nLLAMA_ARG_KV_UNIFIED_PER_SLOT="1024"\n', 1024),
        ('n_ctx=8192\nn_parallel=4\nextra_args=["--kv-unified-per-slot", "invalid"]\n', None),
        (
            (
                'exec=["--sleep-idle-seconds", "-1", "--port", "20000", "--alias", "qwen", '
                '"-m", "/models/qwen.gguf", "-c", "8192", "-np", "4"]\n'
            ),
            2048,
        ),
        (
            (
                'exec=["--sleep-idle-seconds", "-1", "--port", "20000", "--alias", "qwen", '
                '"-m", "/models/qwen.gguf", "-c", "8192"]\n'
            ),
            None,
        ),
        (
            (
                'exec=["--sleep-idle-seconds", "-1", "--port", "20000", "--alias", "qwen", '
                '"-m", "/models/qwen.gguf"]\n'
                '[env_vars]\nLLAMA_ARG_CTX_SIZE="8192"\nLLAMA_ARG_N_PARALLEL="4"\n'
            ),
            2048,
        ),
        ('n_ctx=8192\nextra_args=["--parallel", "0"]\n', None),
        ('n_ctx=8192\nextra_args=["--parallel", "invalid"]\n[env_vars]\nLLAMA_ARG_N_PARALLEL="1"\n', None),
    ],
)
def test_llamacpp_context_is_a_conservative_per_request_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.MockRouter,
    configuration: str,
    expected: int | None,
) -> None:
    identity = 'name="desk"\n'
    if not configuration.startswith("exec="):
        identity += 'model_path="/models/qwen.gguf"\n'
    else:
        identity += "port=20000\n"
    configured = _configured(
        tmp_path,
        monkeypatch,
        {"llamacpp/chat.toml": identity + configuration},
    )
    _local_http(respx_mock)
    assert configured.registry.list_capabilities()[0].generation_profile.max_context == expected


def test_llamacpp_rejects_mixed_passthrough_and_managed_model_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValidationError, match="managed fields were also set: model_path"):
        _configured(
            tmp_path,
            monkeypatch,
            {"llamacpp/chat.toml": 'name="desk"\nmodel_path="/models/qwen.gguf"\nexec=["--alias", "qwen"]\n'},
        )


def test_tabby_rejects_a_response_surface_outside_its_admitted_adapter_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValidationError, match="only the chat surface"):
        _configured(
            tmp_path,
            monkeypatch,
            {
                "exllamav3/chat.toml": """
name = "tabby"
auth_secret_name = "tabby-test-auth"
volumes = ["/models:/app/models:ro"]
[[models]]
id = "stable-qwen"
path = "/app/models/qwen"
[models.capabilities]
surface = "responses"
""",
            },
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime", ["llamacpp", "vllm", "sglang"])
async def test_local_model_surface_hint_reaches_the_executable_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter, runtime: str
) -> None:
    model_id = "/models/qwen" if runtime == "sglang" else "qwen"
    model_path = "/models/qwen.gguf" if runtime == "llamacpp" else "/models/qwen"
    launch = {
        "llamacpp": 'model_path="/models/qwen.gguf"',
        "vllm": 'exec=["serve", "/models/qwen", "--served-model-name", "qwen", "--port", "20000"]',
        "sglang": 'exec=["-m", "sglang.launch_server", "--model-path", "/models/qwen", "--port", "20000"]',
    }[runtime]
    configured = _configured(
        tmp_path,
        monkeypatch,
        {
            f"{runtime}/chat.toml": f"""
name = "desk"
port = 20000
served_model_id = "{model_id}"
{launch}
[[models]]
id = "{model_id}"
path = "{model_path}"
[models.capabilities]
surface = "responses"
supports_tools = true
""",
        },
    )
    _local_http(respx_mock, models=(model_id,))
    grant = await configured.registry.issue_grant(f"desk:chat:{model_id}", holder="run:operator-turn")
    assert isinstance(grant.model, OpenAIResponsesModel)


@pytest.mark.asyncio
async def test_single_model_health_does_not_grant_an_absent_declared_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {
            "llamacpp/chat.toml": """
name = "desk"
model_path = "/models/qwen.gguf"
[[models]]
id = "qwen"
path = "/models/qwen.gguf"
[[models]]
id = "retired-model"
path = "/models/retired.gguf"
""",
        },
    )
    _local_http(respx_mock)
    with pytest.raises(CapabilityUnavailable):
        await configured.registry.issue_grant("desk:chat:retired-model", holder="run:operator-turn")


@pytest.mark.parametrize(
    ("inventory", "expected"),
    [
        ("disconnected", CapabilityPhase.COLD),
        ("malformed", CapabilityPhase.ERROR),
        ("loading", CapabilityPhase.WARMING),
    ],
)
def test_single_model_inventory_distinguishes_transport_loading_and_invalid_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.MockRouter,
    inventory: str,
    expected: CapabilityPhase,
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {"llamacpp/chat.toml": 'name="desk"\nmodel_path="/models/qwen.gguf"\n'},
    )
    respx_mock.get("http://localhost:20000/health").respond(json={"status": "ok"})
    route = respx_mock.get("http://localhost:20000/v1/models")
    if inventory == "disconnected":
        route.mock(side_effect=httpx.ConnectError("runtime stopped between probes"))
    elif inventory == "loading":
        route.respond(503, json={"error": {"message": "Loading model"}})
    else:
        route.respond(json={"data": [{"id": None}]})
    state = configured.registry.get_capability_state("desk:chat:qwen")
    assert state is not None
    assert state.phase is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("family", ["vision", "embedding", "rerank", "stt", "tts"])
async def test_configuring_a_metadata_family_does_not_invent_an_execution_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter, family: str
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {
            "llamacpp/service.toml": f"""
name = "desk"
model_path = "/models/qwen.gguf"
[[models]]
id = "qwen"
path = "/models/qwen.gguf"
[models.capabilities]
families = ["{family}"]
""",
        },
    )
    _local_http(respx_mock)
    key = f"desk:{family}:qwen"
    state = configured.registry.get_capability_state(key)
    assert state is not None
    assert state.phase is CapabilityPhase.WARM
    with pytest.raises(CapabilityUnavailable, match="without an executable grant surface"):
        await configured.registry.issue_grant(key, holder="run:operator-turn")


def test_multiple_engine_endpoints_preserve_one_port_and_model_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {
            "llamacpp/chat.toml": 'name="desk"\nmodel_path="/models/qwen.gguf"\n',
            "vllm/chat.toml": 'name="batch"\nport=23000\nserved_model_id="coder"\n'
            'exec=["serve","/models/coder","--served-model-name","coder","--port","23000"]\n',
        },
    )
    _local_http(respx_mock)
    _local_http(respx_mock, port=23000, models=("coder",))
    assert {(stone.name, stone.port) for stone in configured.declarations.soulstones} == {
        ("desk", 20000),
        ("batch", 23000),
    }
    assert {spec.key for spec in configured.registry.list_capabilities()} == {"desk:chat:qwen", "batch:chat:coder"}
    with pytest.raises(RuntimeError, match="replace the process generation"):
        configured.registry.load()


def test_workflow_selection_and_multimodal_input_are_not_delivered_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("lychd.config.settings.root.PATH_LYCHD_TOML", tmp_path / "lychd.toml")
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Settings.model_validate({"workflows": {"default": "speech-pipeline@1"}})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Intent.model_validate({"session_id": "one", "prompt": "describe this", "artifacts": []})
    registry = builtin_workflow_registry()
    assert {workflow.name for workflow in registry.all()} == {"bridge_chat", "delegated_rite"}


class _Queue:
    """Capture the admitted hop, leaving execution to the real worker function."""

    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
        assert job_or_func == "perform_run"
        self.jobs.append(kwargs)

    async def job(self, job_key: str, /) -> None:
        _ = job_key

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = job, error, ttl
        pytest.fail("a warm offline chat must not require broker cancellation")


@pytest.mark.asyncio
async def test_operator_text_turn_runs_real_assembly_dispatch_and_openai_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    configured = _configured(
        tmp_path,
        monkeypatch,
        {
            "llamacpp/chat.toml": """
name = "desk"
model_path = "/models/qwen.gguf"
n_ctx = 8192
[generation]
max_tokens = 128
temperature = 0.2
""",
        },
    )
    _local_http(respx_mock)
    requests: list[dict[str, Any]] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://localhost:20000/v1/chat/completions"
        body = json.loads(request.content)
        requests.append(body)
        output_tool = body["tools"][0]["function"]["name"]
        chunk = {
            "id": "offline-operator-turn",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "qwen",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "typed-result",
                                "type": "function",
                                "function": {
                                    "name": output_tool,
                                    "arguments": json.dumps({"answer": "A local answer.", "fragments": []}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }
        return httpx2.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n",
        )

    monkeypatch.setattr(
        "pydantic_ai.providers._openai_compatible.create_async_httpx2_client",
        lambda: httpx2.AsyncClient(transport=httpx2.MockTransport(answer)),
    )
    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)

    def offline_platform_provider(
        *, base_url: str, api_key: str | None = None, default_query: Mapping[str, str] | None = None
    ) -> OpenAIProvider:
        provider = openai_compatible_provider(base_url=base_url, api_key=api_key, default_query=default_query)
        # The SDK's unrelated host fingerprint uses a worker thread; replace
        # that host observation just as the HTTP engine boundary is replaced.
        monkeypatch.setattr(provider.client, "_platform", "Linux")
        return provider

    monkeypatch.setattr("lychd.domain.animation.model_factory.openai_compatible_provider", offline_platform_provider)
    queue = _Queue()
    services = build_altar_services(
        queues={"runs": queue, "rites": _Queue()},
        runes=configured.runes,
        runtime_adapters=configured.extensions.runtime_adapters,
        portal_definitions=configured.extensions.portal_definitions,
        settings=configured.settings,
    )
    try:
        session = await services.bridge_sessions.create_session()
        handle = await services.run_engine.submit(Intent(session_id=session.id, prompt="Answer locally."))
        assert len(queue.jobs) == 1
        async with asyncio.timeout(5):
            await perform_run(
                {"run_substrate": services.substrate},
                run_id=handle.run_id,
                enqueue_seq=queue.jobs[0]["enqueue_seq"],
            )
        run = await services.ledger.get(handle.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE, run.error
        completed = await services.bridge_sessions.get_session(session.id)
        assert completed is not None
        assert completed.turns[-1].content == "A local answer."
        assert len(requests) == 1
        body = requests[0]
        assert body["model"] == "qwen"
        assert body["temperature"] == 0.2
        assert body["max_completion_tokens"] == 128
        assert body["stream"] is True
        assert body["tools"]  # BridgeReply uses a schema tool even with no callable runtime tools.
        assert all(tool["function"].get("strict") is not True for tool in body["tools"])
    finally:
        await services.aclose()
