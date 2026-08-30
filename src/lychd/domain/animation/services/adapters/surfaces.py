"""Connector and animator surface implementations for animation runtimes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.animation.animators import Portal, Soulstone
from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, ModelSurface, PortalConfig, SoulstoneConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset


class OpenAICompatibleConnector(Connector, ModelConnector, ToolConnector):
    """OpenAI-compatible connector backed by Pydantic AI OpenAI model/provider."""

    def __init__(
        self,
        *,
        link: Link,
        base_url: str,
        model_infos: Sequence[ModelInfo] = (),
        default_model_id: str | None = None,
        api_key_secret_name: str | None = None,
        default_surface: ModelSurface = ModelSurface.CHAT,
        provider_name: str = "openai-compatible",
        toolsets: Sequence[AbstractToolset] = (),
    ) -> None:
        """Store readiness, base URL, models, auth, profile policy, and toolsets."""
        self._link = link
        self._base_url = base_url
        self._model_infos = tuple(model_infos)
        self._default_model_id = default_model_id
        self._api_key_secret_name = api_key_secret_name
        self._default_surface = default_surface
        self._provider_name = provider_name
        self._toolsets = tuple(toolsets)
        self._observed_model_ids: tuple[str, ...] | None = None
        self._inventory_error: str | None = None

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
    def observed_model_ids(self) -> tuple[str, ...] | None:
        """Return the last validated live ``/models`` inventory, if one was probed."""
        return self._observed_model_ids

    def set_observed_model_ids(self, model_ids: Sequence[str] | None) -> None:
        """Replace live inventory evidence without mutating the declared catalogue."""
        self._observed_model_ids = None if model_ids is None else tuple(model_ids)

    @property
    def inventory_error(self) -> str | None:
        """Return the last live inventory conformance failure, if any."""
        return self._inventory_error

    def set_inventory_error(self, error: str | None) -> None:
        """Replace inventory conformance evidence independently of link liveness."""
        self._inventory_error = error

    def get_model(self, *, model_id: str | None = None) -> Model:
        selected_model = self._select_model_id(model_id)
        selected_surface = self._select_model_surface(model_id)
        provider_model = self._provider_model_id(selected_model)

        try:
            from lychd.domain.animation.model_factory import build_openai_compatible_model, openai_interface_route
        except ModuleNotFoundError as exc:
            msg = "Pydantic AI OpenAI extras are required to hydrate an OpenAI-compatible connector model."
            raise RuntimeError(msg) from exc

        provider, provider_profile = openai_interface_route(
            provider_name=self._provider_name,
            base_url=self._base_url,
            model_id=provider_model,
            responses=selected_surface == ModelSurface.RESPONSES,
            api_key=self._resolve_api_key(),
        )
        return build_openai_compatible_model(
            model_id=provider_model,
            provider=provider,
            responses=selected_surface == ModelSurface.RESPONSES,
            profile=provider_profile,
        )

    def get_toolsets(self) -> Sequence[AbstractToolset]:
        return self._toolsets

    def _select_model_id(self, requested: str | None) -> str:
        selected = requested or self._default_model_id or (self._model_infos[0].id if self._model_infos else None)
        if selected is None:
            msg = f"{type(self).__name__} cannot hydrate a model because no default or requested model id was provided."
            raise ValueError(msg)
        if self._model_infos and all(info.id != selected for info in self._model_infos):
            msg = f"{type(self).__name__} cannot hydrate undeclared model id {selected!r}."
            raise ValueError(msg)
        return selected

    def _provider_model_id(self, selected_model_id: str) -> str:
        """Translate a stable capability id into the provider-facing model id."""
        return selected_model_id

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


class _ConfiguredAnimator[C: Connector, R: SoulstoneConfig | PortalConfig]:
    def __init__(self, *, rune: R, connector: C) -> None:
        """Store immutable rune and connector references."""
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


class SoulstoneAnimator[C: Connector, R: SoulstoneConfig](
    _ConfiguredAnimator[C, R],
    Soulstone[C, R],
):
    """Concrete Soulstone runtime with immutable rune and connector references."""


class PortalAnimator[C: Connector, R: PortalConfig](
    _ConfiguredAnimator[C, R],
    Portal[C, R],
):
    """Concrete generic Portal runtime with immutable rune + connector references."""


def local_link_default(*, runtime: str) -> Link:
    """Build a default local-runtime link prior to active probing."""
    return Link(
        up=False,
        reason=f"{runtime} runtime not probed/started",
    )


def portal_link_default(*, base_url: str) -> Link:
    """Build an unverified passive link; a configured URL is not reachability proof."""
    if base_url:
        return Link(up=False, reason="portal reachability not probed")
    return Link(up=False, reason="portal base_url missing")


__all__ = [
    "OpenAICompatibleConnector",
    "PortalAnimator",
    "SoulstoneAnimator",
    "local_link_default",
    "portal_link_default",
]
