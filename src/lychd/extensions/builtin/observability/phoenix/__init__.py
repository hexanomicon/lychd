"""Built-in integration for the external Arize Phoenix Eye.

Phoenix is not native Oculus and owns no LychD evidence semantics or canonical state.
"""

from lychd.extensions.builtin.observability.phoenix.config import ObservabilityConfig, PhoenixSettings

__all__ = ["ObservabilityConfig", "PhoenixSettings"]
