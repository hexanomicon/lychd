"""Metadata hydration cannot skip application startup's initial runtime probes."""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from lychd.domain.animation.capabilities import CapabilityPhase
from lychd.domain.animation.embeddings import EmbeddingBinding
from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import IMAGE, PROFILE
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig
from lychd.interface.web.lifespan import altar_services_lifespan

if TYPE_CHECKING:
    from litestar import Litestar


class _RecoveryReachedError(Exception):
    """Stop the inert startup after inspecting the real registry's observations."""


def _offline_registry(
    monkeypatch: pytest.MonkeyPatch, chat_inventory: str
) -> tuple[AnimatorRegistry, list[str], list[httpx.AsyncClient]]:
    """Keep real declaration/adapter behavior inside one effect-free transport."""
    calls: list[str] = []
    clients: list[httpx.AsyncClient] = []
    original_client = httpx.AsyncClient

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        url = str(request.url)
        calls.append(url)
        if url == "http://127.0.0.1:31842/v1/models":
            if chat_inventory == "down":
                message = "inert unavailable runtime"
                raise httpx.ConnectError(message, request=request)
            model = "assistant" if chat_inventory == "exact" else "other-model"
            return httpx.Response(200, json={"data": [{"id": model}]})
        if url == "http://127.0.0.1:31841/health":
            return httpx.Response(200, json={"status": "ok"})
        assert url == "http://127.0.0.1:31841/v1/models"
        return httpx.Response(200, json={"data": [{"id": PROFILE.model_id}]})

    def offline_client(**kwargs: Any) -> httpx.AsyncClient:
        client = original_client(transport=httpx.MockTransport(respond), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr("lychd.lib.http.httpx.AsyncClient", offline_client)
    chat = VllmSoulstoneConfig.model_validate(
        {"name": "desk-chat", "base_url": "http://127.0.0.1:31842/v1", "port": 31842, "served_model_id": "assistant"}
    )
    embedding = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "desk-memory",
            "base_url": "http://127.0.0.1:31841/v1",
            "port": 31841,
            "embedding_profile": PROFILE.profile_id,
            "model_path": "/models/embedding.gguf",
            "quadlet": {"image": IMAGE},
        }
    )
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=(chat, embedding), portals=()),
        runtime_adapters=[
            OpenAICompatibleRuntimeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig),
            LlamaCppRuntimeAdapter(),
        ],
    )
    return registry, calls, clients


@pytest.mark.asyncio
@pytest.mark.parametrize("metadata_preloaded", [False, True])
@pytest.mark.parametrize("chat_inventory", ["exact", "wrong", "down"])
async def test_initial_readiness_precedes_recovery_after_metadata_binding(
    monkeypatch: pytest.MonkeyPatch, *, metadata_preloaded: bool, chat_inventory: str
) -> None:
    """Use real adapters and an in-memory transport; neither path duplicates probes."""
    registry, calls, clients = _offline_registry(monkeypatch, chat_inventory)
    if metadata_preloaded:
        registry.require_embedding(
            EmbeddingBinding(capability_key=f"desk-memory:embedding:{PROFILE.model_id}", profile_digest=PROFILE.digest),
            "embed_query",
        )
        assert registry.list_capability_states() == []
        assert calls == []

    services = SimpleNamespace(registry=registry, substrate=SimpleNamespace(effects=None), aclose=AsyncMock())
    extensions = SimpleNamespace(
        soulstone_registrations=(),
        portal_registrations=(),
        delegated_runtime_adapters={},
        delegated_runtime_catalog=(),
        observation_registrations=(),
        inspection_registrations=(),
    )
    settings = SimpleNamespace(orchestration=SimpleNamespace(switching=SimpleNamespace(actuator="none")))
    monkeypatch.setattr("lychd.config.settings.root.get_settings", lambda: settings)
    monkeypatch.setattr("lychd.extensions.host.get_extensions", lambda: extensions)
    monkeypatch.setattr("lychd.interface.web.lifespan._soft_activation_guard_at_startup", Mock())
    monkeypatch.setattr("lychd.system.services.runtime.wait_for_host_reactor_idle", AsyncMock())
    monkeypatch.setattr("lychd.interface.web.lifespan._collect_run_queues", Mock(return_value={}))
    monkeypatch.setattr("lychd.interface.web.lifespan.connect_run_queues", AsyncMock(return_value=()))
    monkeypatch.setattr("lychd.interface.web.lifespan.build_altar_services", Mock(return_value=services))
    monkeypatch.setattr("lychd.interface.web.lifespan._drain_process_work", AsyncMock())
    disconnect = AsyncMock()
    monkeypatch.setattr("lychd.interface.web.lifespan.disconnect_run_queues", disconnect)
    publish = Mock()
    monkeypatch.setattr("lychd.domain.cortex.substrate.set_run_substrate", publish)
    monkeypatch.setattr("lychd.domain.cortex.substrate.reset_run_substrate", Mock())

    async def inspect_before_recovery(**_kwargs: object) -> None:
        chat_state = registry.get_capability_state("desk-chat:chat:assistant")
        assert chat_state is not None, "initial_chat_observation_missing"
        expected = {"exact": CapabilityPhase.WARM, "wrong": CapabilityPhase.ERROR, "down": CapabilityPhase.COLD}
        assert chat_state.phase is expected[chat_inventory]
        if chat_inventory == "wrong":
            assert chat_state.health == "model_missing"
        embedding_state = registry.get_capability_state(f"desk-memory:embedding:{PROFILE.model_id}")
        assert embedding_state is not None
        assert embedding_state.phase is CapabilityPhase.WARM
        assert Counter(calls) == {
            "http://127.0.0.1:31842/v1/models": 1,
            "http://127.0.0.1:31841/health": 1,
            "http://127.0.0.1:31841/v1/models": 1,
        }
        raise _RecoveryReachedError

    monkeypatch.setattr("lychd.interface.web.lifespan._recover_durable_state", inspect_before_recovery)
    app = cast("Litestar", SimpleNamespace(state=SimpleNamespace(runes=object())))
    with pytest.raises(_RecoveryReachedError):
        async with altar_services_lifespan(app):
            pytest.fail("The recovery sentinel must stop publication.")
    services.aclose.assert_awaited_once()
    disconnect.assert_awaited_once_with(())
    publish.assert_not_called()
    assert len(clients) == 3
    assert all(client.is_closed for client in clients)
