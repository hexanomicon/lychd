"""Connector and animator surface implementations for animation runtimes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from lychd.domain.animation.animators import Portal, Soulstone
from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, ModelSurface, PortalConfig, SoulstoneConfig
from lychd.extensions.builtin.animator import LlamaCppSoulstone, SglangSoulstone, VllmSoulstone

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset


class PassiveConnector(Connector):
    """Connector with readiness only."""

    def __init__(self, *, kind: str, link: Link) -> None:
        """Store readiness-only connector metadata."""
        self._kind = kind
        self._link = link

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def link(self) -> Link:
        return self._link


class OpenAICompatibleConnector(Connector, ModelConnector, ToolConnector):
    """OpenAI-compatible connector backed by Pydantic AI OpenAI model/provider."""

    def __init__(
        self,
        *,
        kind: str,
        link: Link,
        base_url: str,
        model_infos: Sequence[ModelInfo] = (),
        default_model_id: str | None = None,
        api_key_secret: str | None = None,
        default_surface: ModelSurface = ModelSurface.CHAT,
        toolsets: Sequence[AbstractToolset] = (),
    ) -> None:
        """Store readiness, base URL, models, auth, and toolsets."""
        self._kind = kind
        self._link = link
        self._base_url = base_url
        self._model_infos = tuple(model_infos)
        self._default_model_id = default_model_id
        self._api_key_secret = api_key_secret
        self._default_surface = default_surface
        self._toolsets = tuple(toolsets)

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def link(self) -> Link:
        return self._link

    @property
    def base_url(self) -> str:
        return self._base_url

    def list_models(self) -> Sequence[ModelInfo]:
        return self._model_infos

    def get_model(self, *, model_id: str | None = None) -> Model:
        selected_model = self._select_model_id(model_id)
        selected_surface = self._select_model_surface(model_id)

        try:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider
        except ModuleNotFoundError as exc:
            msg = "Pydantic AI OpenAI extras are required to hydrate an OpenAI-compatible connector model."
            raise RuntimeError(msg) from exc

        api_key = self._resolve_api_key()
        if api_key:
            provider = OpenAIProvider(base_url=self._base_url, api_key=api_key)
        else:
            provider = OpenAIProvider(base_url=self._base_url)
        if selected_surface == ModelSurface.RESPONSES:
            from pydantic_ai.models.openai import OpenAIResponsesModel

            return cast("Model", OpenAIResponsesModel(selected_model, provider=provider))
        return cast("Model", OpenAIChatModel(selected_model, provider=provider))

    def get_toolsets(self) -> Sequence[AbstractToolset]:
        return self._toolsets

    def _select_model_id(self, requested: str | None) -> str:
        if requested:
            return requested
        if self._default_model_id:
            return self._default_model_id
        if self._model_infos:
            return self._model_infos[0].id

        msg = f"Connector '{self.kind}' cannot hydrate a model because no default or requested model id was provided."
        raise ValueError(msg)

    def _select_model_surface(self, requested: str | None) -> ModelSurface:
        if requested:
            for info in self._model_infos:
                if info.id == requested and info.surface is not None:
                    return info.surface
            return self._default_surface

        if self._default_model_id:
            for info in self._model_infos:
                if info.id == self._default_model_id and info.surface is not None:
                    return info.surface

        if self._model_infos and self._model_infos[0].surface is not None:
            return self._model_infos[0].surface

        return self._default_surface

    def _resolve_api_key(self) -> str | None:
        """Resolve API key value from mounted Podman secret files when configured."""
        if not self._api_key_secret:
            return None

        root = Path(os.environ.get("LYCHD_SECRET_ROOT", "/run/secrets"))
        path = root / self._api_key_secret
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            msg = (
                f"Portal secret '{self._api_key_secret}' was not found at '{path}'. "
                "Ensure the Vessel unit mounts this Podman secret."
            )
            raise RuntimeError(msg) from exc

        if not value:
            msg = f"Portal secret '{self._api_key_secret}' at '{path}' is empty."
            raise RuntimeError(msg)
        return value


class LlamacppConnector(OpenAICompatibleConnector):
    """OpenAI-compatible connector with llama.cpp router/single lifecycle metadata."""

    def __init__(
        self,
        *,
        link: Link,
        base_url: str,
        model_infos: Sequence[ModelInfo],
        default_model_id: str | None,
        mode: Literal["single", "router"],
        router_query_model_id: str | None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Initialize llama.cpp connector with runtime lifecycle metadata."""
        super().__init__(
            kind="llamacpp",
            link=link,
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=default_model_id,
        )
        self._mode: Literal["single", "router"] = mode
        self._router_query_model_id = router_query_model_id
        self._metadata = dict(metadata or {})

    @property
    def mode(self) -> Literal["single", "router"]:
        return self._mode

    @property
    def router_query_model_id(self) -> str | None:
        return self._router_query_model_id

    @property
    def metadata(self) -> dict[str, object]:
        return dict(self._metadata)


class _BaseSoulstoneAnimator[C: Connector, R: SoulstoneConfig](Soulstone[C, R]):
    """Concrete Soulstone runtime base with immutable rune + connector references."""

    def __init__(self, *, rune: R, connector: C) -> None:
        """Store immutable rune + connector references."""
        self._rune = rune
        self._connector = connector

    @property
    def rune(self) -> R:
        return self._rune

    @property
    def name(self) -> str:
        return self._rune.name

    @property
    def base_url(self) -> str:
        return self._rune.base_url

    @property
    def connector(self) -> C:
        return self._connector

    @property
    def orchestration_labels(self) -> frozenset[str]:
        labels = [*self._rune.orchestration_labels, "local", f"runtime:{self._rune.runtime_name}"]
        return frozenset(labels)


class _BasePortalAnimator[C: Connector, R: PortalConfig](Portal[C, R]):
    """Concrete Portal runtime base with immutable rune + connector references."""

    def __init__(self, *, rune: R, connector: C) -> None:
        """Store immutable rune + connector references."""
        self._rune = rune
        self._connector = connector

    @property
    def rune(self) -> R:
        return self._rune

    @property
    def name(self) -> str:
        return self._rune.name

    @property
    def base_url(self) -> str:
        return self._rune.base_url

    @property
    def connector(self) -> C:
        return self._connector

    @property
    def orchestration_labels(self) -> frozenset[str]:
        labels = [*self._rune.orchestration_labels, "remote", f"provider:{self._rune.provider_type}"]
        return frozenset(labels)


class GenericStone(_BaseSoulstoneAnimator[Connector, SoulstoneConfig]):
    """Fallback local animator when no runtime-specific connector exists yet."""


class OpenAICompatibleStone(_BaseSoulstoneAnimator[OpenAICompatibleConnector, SoulstoneConfig]):
    """Local Soulstone exposing an OpenAI-compatible connector surface."""


class LlamacppStone(_BaseSoulstoneAnimator[LlamacppConnector, LlamaCppSoulstone]):
    """Concrete llama.cpp Soulstone runtime handle."""


class VllmStone(_BaseSoulstoneAnimator[OpenAICompatibleConnector, VllmSoulstone]):
    """Concrete vLLM Soulstone runtime handle (OpenAI-compatible surface)."""


class SglangStone(_BaseSoulstoneAnimator[OpenAICompatibleConnector, SglangSoulstone]):
    """Concrete SGLang Soulstone runtime handle (OpenAI-compatible surface)."""


class GenericPortal(_BasePortalAnimator[Connector, PortalConfig]):
    """Fallback Portal runtime when provider-specific connector is not implemented."""


class OpenAIPortal(_BasePortalAnimator[OpenAICompatibleConnector, PortalConfig]):
    """Portal runtime using an OpenAI-compatible connector surface."""


def local_link_default(*, runtime: str) -> Link:
    """Build a default local-runtime link prior to active probing."""
    return Link(
        up=False,
        activatable=True,
        estimated_ready_ms=None,
        reason=f"{runtime} runtime not probed/started",
    )


def portal_link_default(*, base_url: str) -> Link:
    """Build a passive readiness link for portal providers."""
    if base_url:
        return Link(up=True, activatable=False)
    return Link(up=False, activatable=False, reason="portal base_url missing")


__all__ = [
    "GenericPortal",
    "GenericStone",
    "LlamacppConnector",
    "LlamacppStone",
    "OpenAICompatibleConnector",
    "OpenAICompatibleStone",
    "OpenAIPortal",
    "PassiveConnector",
    "SglangStone",
    "VllmStone",
    "local_link_default",
    "portal_link_default",
]
