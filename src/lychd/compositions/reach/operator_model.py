"""Exact vLLM development capability through a fixed host relay, under ordinary grants."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

import httpx2
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider

from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    OperatorModelProbe,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_wire import strict_json
from lychd.domain.animation.capabilities import CapabilityPhase, CapabilitySpec, CapabilityState, SourceKind
from lychd.domain.animation.connectors import Connector, ModelConnector
from lychd.domain.animation.links import Link
from lychd.domain.animation.model_factory import LOCAL_COMPAT_PROFILE
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig

type ModelRelay = Callable[[str, str], Awaitable[str]]

_LOCAL_RELAY_PROFILE: OpenAIModelProfile = {
    **LOCAL_COMPAT_PROFILE,
    "openai_chat_supports_max_completion_tokens": False,
    "openai_system_prompt_role": "system",
}


class _RelayTransport(httpx2.AsyncBaseTransport):
    def __init__(self, profile: OperatorConversationProfile, relay: ModelRelay) -> None:
        """Pin the declared model profile and its narrow relay callable."""
        self.profile, self.relay = profile, relay

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Translate exactly one SDK chat request; no URL or headers cross the pipe."""
        if request.method != "POST" or str(request.url) != "http://reach-model.invalid/v1/chat/completions":
            msg = "model_route"
            raise ValueError(msg)
        value = strict_json(await request.aread())
        if not isinstance(value, dict):
            msg = "model_payload"
            raise TypeError(msg)
        # Pydantic AI's nonstreaming text call has no reason to emit other SDK options.
        body = cast("dict[str, Any]", value)
        body.setdefault("stream", False)
        body.setdefault("chat_template_kwargs", {"enable_thinking": False})
        payload = canonical_json(body)
        validate_generation_payload(self.profile, payload)
        raw = await self.relay("generate", payload)
        result = strict_json(raw.encode())
        try:
            choice = result["choices"][0]
            message = choice["message"]
            valid = (
                result["model"] == self.profile.model_id
                and len(result["choices"]) == 1
                and not message.get("tool_calls")
                and not message.get("function_call")
                and message.get("role") == "assistant"
                and isinstance(message.get("content"), str)
                and bool(message["content"].strip())
            )
        except (KeyError, IndexError, TypeError):
            valid = False
        if not valid:
            msg = "model_response"
            raise ValueError(msg)
        return httpx2.Response(200, json=result)


class _RelayProvider(OpenAIProvider):
    def __init__(self, profile: OperatorConversationProfile, relay: ModelRelay) -> None:
        def client() -> httpx2.AsyncClient:
            return httpx2.AsyncClient(
                transport=_RelayTransport(profile, relay),
                trust_env=False,
                follow_redirects=False,
                timeout=profile.timeout_seconds,
            )

        http_client = client()
        super().__init__(base_url="http://reach-model.invalid/v1", api_key="no-credential", http_client=http_client)
        self._own_http_client = http_client
        self._http_client_factory = client
        self.client.max_retries = 0
        self.client.organization = None
        self.client.project = None
        self.client.webhook_secret = None
        self.client.admin_api_key = None
        empty_headers: dict[str, str] = {}
        ambient_fields: tuple[tuple[str, object], ...] = (
            ("_custom_headers", empty_headers),
            ("_ambient_authorizations", frozenset[str]()),
        )
        for attribute, value in ambient_fields:
            setattr(self.client, attribute, value)


class OperatorModelConnector(Connector, ModelConnector):
    """Only one exact text model; there is no tool or runtime-control surface."""

    def __init__(self, profile: OperatorConversationProfile, relay: ModelRelay) -> None:
        """Pin the declared model profile and its narrow relay callable."""
        self.profile, self.relay = profile, relay
        self._link = Link(up=False, reason="model_unprobed")

    @property
    def link(self) -> Link:
        return self._link

    @property
    def base_url(self) -> str:
        return "http://reach-model.invalid/v1"

    def get_model(self, *, model_id: str | None = None) -> Model:
        if model_id != self.profile.model_id:
            msg = "model_binding"
            raise ValueError(msg)
        return OpenAIChatModel(
            self.profile.model_id,
            provider=_RelayProvider(self.profile, self.relay),
            profile=_LOCAL_RELAY_PROFILE,
        )

    async def probe(self) -> bool:
        result = OperatorModelProbe.model_validate_json(await self.relay("probe", "{}"))
        warm = result.healthy and self.profile.model_id in result.model_ids
        self._link = Link(up=warm, reason=None if warm else "model_unavailable")
        return warm


class OperatorModelAdapter:
    """One explicit adapter snapshot for the already-running local vLLM Soulstone."""

    runtime = "vllm"

    def __init__(self, profile: OperatorConversationProfile, relay: ModelRelay) -> None:
        """Pin the declared model profile and its narrow relay callable."""
        self.profile, self.relay = profile, relay

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        del soulstone
        msg = "operator_no_transition"
        raise RuntimeError(msg)

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator:
        if (
            type(soulstone) is not VllmSoulstoneConfig
            or soulstone.name != self.profile.animator_id
            or soulstone.served_model_id != self.profile.model_id
        ):
            msg = "model_binding"
            raise ValueError(msg)
        return SoulstoneAnimator(rune=soulstone, connector=OperatorModelConnector(self.profile, self.relay))

    def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
        rune = animator.rune
        if not isinstance(rune, VllmSoulstoneConfig):
            msg = "model_binding"
            raise TypeError(msg)
        return [
            CapabilitySpec(
                key=self.profile.capability_key,
                animator_name=animator.name,
                runtime="vllm",
                source_kind=SourceKind.SOULSTONE,
                family=CapabilityFamily.CHAT,
                model_id=self.profile.model_id,
                max_context=self.profile.max_context,
                modalities_in=("text",),
                supports_tools=False,
                concurrency=rune.concurrency,
                generation_profile=GenerationProfile(
                    max_tokens=self.profile.max_tokens, temperature=self.profile.temperature
                ),
            )
        ]

    async def probe_capability_states(
        self, animator: RuntimeAnimator, specs: list[CapabilitySpec]
    ) -> list[CapabilityState]:
        connector = animator.connector
        if not isinstance(connector, OperatorModelConnector):
            msg = "model_connector"
            raise TypeError(msg)
        warm = await connector.probe()
        return [
            CapabilityState(
                capability_key=spec.key,
                phase=CapabilityPhase.WARM if warm else CapabilityPhase.COLD,
                health="ok" if warm else "down",
                checked_at=datetime.now(UTC),
                reason=None if warm else "model_unavailable",
            )
            for spec in specs
        ]


def operator_model_rune(profile: OperatorConversationProfile) -> VllmSoulstoneConfig:
    """Declare the fixed observed runtime route without discovering or changing host configuration."""
    return VllmSoulstoneConfig(name=profile.animator_id, port=28000, served_model_id=profile.model_id)
