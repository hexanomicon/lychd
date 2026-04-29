from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lychd.config.runes import RuneConfig
from lychd.domain.animation.animators import Animator
from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset


type RuntimeAnimator = Animator[Connector, RuneConfig]


class AnimatorBindingError(ValueError):
    """Raised when an animator connector cannot hydrate agent-facing objects."""


class AnimatorBinder:
    """Thin hydrator from runtime animators to Pydantic AI abstractions.

    This binder intentionally delegates integration logic to the animator's
    connector. LychD keeps orchestration concerns in the domain (`Animator`,
    `Connector`, `Link`), while Pydantic AI remains the source of truth for
    model/provider/toolset abstractions.
    """

    def bind_model(self, animator: RuntimeAnimator, *, model_id: str | None = None) -> Model:
        """Hydrate a Pydantic AI model from a model-capable connector."""
        connector = animator.connector
        if not isinstance(connector, ModelConnector):
            msg = f"Animator '{animator.id}' connector '{connector.kind}' does not provide models."
            raise AnimatorBindingError(msg)
        return connector.get_model(model_id=model_id)

    def bind_toolsets(self, animator: RuntimeAnimator) -> Sequence[AbstractToolset]:
        """Hydrate Pydantic AI toolsets from a tool-capable connector.

        Returns an empty sequence when the connector does not implement the tool
        capability mixin.
        """
        connector = animator.connector
        if not isinstance(connector, ToolConnector):
            return ()
        return tuple(connector.get_toolsets())

    def bind_toolset(self, animator: RuntimeAnimator) -> AbstractToolset | None:
        """Hydrate a single toolset, combining multiple toolsets when needed."""
        toolsets = tuple(self.bind_toolsets(animator))
        if not toolsets:
            return None
        if len(toolsets) == 1:
            return toolsets[0]

        from pydantic_ai import CombinedToolset

        return CombinedToolset(list(toolsets))
