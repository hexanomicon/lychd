"""Animation domain public surface.

This package now exposes the new runtime core (animators/connectors/link) and
the schema layers (TOML Runes + connector model summaries). Builtin extension
implementations are not re-exported here; they live under ``extensions``.
"""

from lychd.domain.animation.animators import Animator, Portal, Soulstone
from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityFamily,
    CapabilityGrant,
    CapabilityLifecycle,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector
from lychd.domain.animation.errors import (
    ActivationFailed,
    ActivationTimeout,
    CapabilityUnavailable,
    HardwareTransitionRequired,
)
from lychd.domain.animation.extension import PortalStore, SoulstoneStore
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    ConcurrencyIntent,
    GenerationProfile,
    GoogleGeminiPortalConfig,
    LocalLLMModelConfig,
    LocalModelConfig,
    ModelCapabilityHints,
    ModelFormat,
    ModelInfo,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
    is_placeholder,
)

__all__ = [
    "ActivationFailed",
    "ActivationResult",
    "ActivationTimeout",
    "Animator",
    "AnimatorConfig",
    "AnimatorLifecycle",
    "CapabilityFamily",
    "CapabilityGrant",
    "CapabilityLifecycle",
    "CapabilityPhase",
    "CapabilitySpec",
    "CapabilityState",
    "CapabilityUnavailable",
    "ConcurrencyIntent",
    "Connector",
    "GenerationProfile",
    "GoogleGeminiPortalConfig",
    "HardwareTransitionRequired",
    "Link",
    "LocalLLMModelConfig",
    "LocalModelConfig",
    "ModelCapabilityHints",
    "ModelConnector",
    "ModelFormat",
    "ModelInfo",
    "OpenAIPortalConfig",
    "Portal",
    "PortalConfig",
    "PortalStore",
    "Soulstone",
    "SoulstoneConfig",
    "SoulstoneStore",
    "ToolConnector",
    "is_placeholder",
]
