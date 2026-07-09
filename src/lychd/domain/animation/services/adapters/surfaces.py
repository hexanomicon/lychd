"""Connector and animator surface implementations for animation runtimes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.animation.animators import Portal, Soulstone
from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, ModelSurface, PortalConfig, SoulstoneConfig
from lychd.system.schemas import QuadletContainer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset


class PassiveConnector(Connector, ToolConnector):
    """Connector with readiness and optional toolsets."""

    def __init__(
        self,
        *,
        kind: str,
        link: Link,
        base_url: str = "",
        toolsets: Sequence[AbstractToolset] = (),
    ) -> None:
        """Store readiness-only connector metadata."""
        self._kind = kind
        self._link = link
        self._base_url = base_url
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

    def get_toolsets(self) -> Sequence[AbstractToolset]:
        return self._toolsets


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
        api_key_secret_name: str | None = None,
        default_surface: ModelSurface = ModelSurface.CHAT,
        toolsets: Sequence[AbstractToolset] = (),
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Store readiness, base URL, models, auth, and toolsets."""
        self._kind = kind
        self._link = link
        self._base_url = base_url
        self._model_infos = tuple(model_infos)
        self._default_model_id = default_model_id
        self._api_key_secret_name = api_key_secret_name
        self._default_surface = default_surface
        self._toolsets = tuple(toolsets)
        self._metadata = dict(metadata or {})

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def link(self) -> Link:
        return self._link

    def set_link(self, link: Link) -> None:
        """Replace the readiness link after a live reachability probe."""
        self._link = link

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def metadata(self) -> dict[str, object]:
        return dict(self._metadata)

    def list_models(self) -> Sequence[ModelInfo]:
        return self._model_infos

    def get_model(self, *, model_id: str | None = None) -> Model:
        selected_model = self._select_model_id(model_id)
        selected_surface = self._select_model_surface(model_id)

        try:
            from lychd.domain.animation.model_factory import (
                build_openai_compatible_model,
                openai_compatible_provider,
            )
        except ModuleNotFoundError as exc:
            msg = "Pydantic AI OpenAI extras are required to hydrate an OpenAI-compatible connector model."
            raise RuntimeError(msg) from exc

        # THE one model constructor (shared with agents.factory.build_local_model) so
        # tool-call JSON schemas are identical between the reference and production.
        provider = openai_compatible_provider(base_url=self._base_url, api_key=self._resolve_api_key())
        return build_openai_compatible_model(
            model_id=selected_model,
            provider=provider,
            responses=selected_surface == ModelSurface.RESPONSES,
        )

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
        if not self._api_key_secret_name:
            return None

        root = Path(os.environ.get("LYCHD_SECRET_ROOT", "/run/secrets"))
        path = root / self._api_key_secret_name
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            msg = (
                f"Portal secret '{self._api_key_secret_name}' was not found at '{path}'. "
                "Ensure the Vessel unit mounts this Podman secret."
            )
            raise RuntimeError(msg) from exc

        if not value:
            msg = f"Portal secret '{self._api_key_secret_name}' at '{path}' is empty."
            raise RuntimeError(msg)
        return value


class SoulstoneAnimator[C: Connector, R: SoulstoneConfig](Soulstone[C, R]):
    """Concrete generic Soulstone runtime with immutable rune + connector references.

    Extensions may subclass this for connector typing (e.g. llama.cpp) but the
    base is fully usable on its own; per-runtime stone subclasses are no longer
    domain types (spec §5).
    """

    def __init__(self, *, rune: R, connector: C, quadlet: QuadletContainer) -> None:
        """Store immutable rune, connector, and generated Quadlet references."""
        self._rune = rune
        self._connector = connector
        self._quadlet = quadlet

    @property
    def rune(self) -> R:
        return self._rune

    @property
    def quadlet(self) -> QuadletContainer:
        return self._quadlet

    @property
    def name(self) -> str:
        return self._rune.name

    @property
    def connector(self) -> C:
        return self._connector


class PortalAnimator[C: Connector, R: PortalConfig](Portal[C, R]):
    """Concrete generic Portal runtime with immutable rune + connector references."""

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
    def connector(self) -> C:
        return self._connector


class GenericStone(SoulstoneAnimator[Connector, SoulstoneConfig]):
    """Fallback local animator when no runtime-specific connector exists yet."""


class OpenAICompatibleStone(SoulstoneAnimator[OpenAICompatibleConnector, SoulstoneConfig]):
    """Local Soulstone exposing an OpenAI-compatible connector surface."""


class GenericPortal(PortalAnimator[Connector, PortalConfig]):
    """Fallback Portal runtime when provider-specific connector is not implemented."""


class OpenAIPortal(PortalAnimator[OpenAICompatibleConnector, PortalConfig]):
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
    "OpenAICompatibleConnector",
    "OpenAICompatibleStone",
    "OpenAIPortal",
    "PassiveConnector",
    "PortalAnimator",
    "SoulstoneAnimator",
    "local_link_default",
    "portal_link_default",
]
