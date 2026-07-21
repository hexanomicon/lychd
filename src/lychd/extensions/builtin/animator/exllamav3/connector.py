from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, SoulstoneAnimator
from lychd.extensions.builtin.animator.soulstones import ExLlamaV3SoulstoneConfig
from lychd.extensions.builtin.animator.tabby_auth import load_tabbyapi_auth_keys

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from lychd.domain.animation.links import Link
    from lychd.domain.animation.schemas import ModelInfo


class ExLlamaV3Connector(OpenAICompatibleConnector):
    """OpenAI-compatible data plane plus TabbyAPI model-name translation."""

    def __init__(
        self,
        *,
        link: Link,
        base_url: str,
        model_infos: Sequence[ModelInfo],
        default_model_id: str,
        runtime_names: Mapping[str, str],
        auth_secret_name: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Store stable LychD ids separately from TabbyAPI directory names."""
        super().__init__(
            kind="exllamav3",
            link=link,
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=default_model_id,
            metadata=metadata,
        )
        self._runtime_names = dict(runtime_names)
        self._model_ids = {runtime_name: model_id for model_id, runtime_name in self._runtime_names.items()}
        self._auth_secret_name = auth_secret_name

    def runtime_model_name(self, model_id: str) -> str | None:
        """Translate one stable capability model id to its TabbyAPI basename."""
        return self._runtime_names.get(model_id)

    def model_id_for_runtime(self, runtime_model_name: str | None) -> str | None:
        """Translate a TabbyAPI basename back to its stable capability model id."""
        if runtime_model_name is None:
            return None
        return self._model_ids.get(runtime_model_name)

    def _provider_model_id(self, selected_model_id: str) -> str:
        """Send TabbyAPI its model-directory name, never LychD's stable id."""
        runtime_model_name = self.runtime_model_name(selected_model_id)
        if runtime_model_name is None:
            msg = f"ExLlamaV3 model id '{selected_model_id}' is not declared by this Soulstone."
            raise ValueError(msg)
        return runtime_model_name

    def _resolve_api_key(self) -> str:
        """Authenticate inference requests with the data-plane key, never the admin key."""
        return load_tabbyapi_auth_keys(self._auth_secret_name).api_key


class ExLlamaV3Stone(SoulstoneAnimator[ExLlamaV3Connector, ExLlamaV3SoulstoneConfig]):
    """Concrete ExLlamaV3/TabbyAPI Soulstone runtime handle."""


__all__ = ["ExLlamaV3Connector", "ExLlamaV3Stone"]
