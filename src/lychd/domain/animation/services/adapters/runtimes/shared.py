"""Shared runtime-adapter helpers.

These helpers keep adapter modules focused on runtime-specific planning while
centralizing repeated type-guard and connector construction logic.
"""

from __future__ import annotations

from datetime import UTC, datetime

from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import (
    default_model_id_for_soulstone,
    model_infos_from_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import (
    OpenAICompatibleConnector,
    local_link_default,
)
from lychd.lib.http import HttpJsonError, request_json


def require_runtime_soulstone[RuntimeSoulstone: SoulstoneConfig](
    soulstone: SoulstoneConfig,
    *,
    expected_type: type[RuntimeSoulstone],
    runtime: str,
) -> RuntimeSoulstone:
    """Validate adapter input type and return the narrowed soulstone."""
    if not isinstance(soulstone, expected_type):
        msg = f"{runtime} adapter received unsupported soulstone type: {type(soulstone)}"
        raise TypeError(msg)
    return soulstone


def build_openai_connector(
    *,
    soulstone: SoulstoneConfig,
    runtime: str,
    kind: str | None = None,
    metadata: dict[str, object] | None = None,
) -> OpenAICompatibleConnector:
    """Build a standard OpenAI-compatible connector for a local runtime."""
    model_infos = model_infos_from_soulstone(soulstone)
    return OpenAICompatibleConnector(
        kind=kind or runtime,
        link=local_link_default(runtime=runtime),
        base_url=resolved_soulstone_base_url(soulstone),
        model_infos=model_infos,
        default_model_id=default_model_id_for_soulstone(soulstone, model_infos),
        metadata=metadata,
    )


def resolved_soulstone_port(soulstone: SoulstoneConfig) -> int:
    """Return a hydrated Soulstone port or fail with a domain-facing error."""
    if soulstone.port is None:
        msg = f"Soulstone '{soulstone.name}' has no hydrated port. Load it through AnimatorLoader first."
        raise ValueError(msg)
    return soulstone.port


def resolved_soulstone_base_url(soulstone: SoulstoneConfig) -> str:
    """Return a hydrated Soulstone connector base URL."""
    if soulstone.base_url is not None:
        return str(soulstone.base_url)
    return f"http://localhost:{resolved_soulstone_port(soulstone)}/v1"


PROBE_TIMEOUT_SECONDS = 2.0


async def probe_openai_compatible_link(
    connector: OpenAICompatibleConnector,
    *,
    timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
    path: str = "/models",
) -> Link:
    """Perform a live async reachability probe of an OpenAI-compatible endpoint.

    Issues a short-timeout ``GET {base_url}{path}`` (default ``/models``, i.e.
    ``/v1/models`` for the standard Soulstone base URL) and returns a refreshed
    ``Link``. The caller is expected to push it onto the connector via
    ``connector.set_link(...)``. A down or non-OpenAI responder resolves to
    ``up=False`` with a human-readable reason; it never raises (A3-U3: async
    httpx replaces the blocking ``urlopen``).
    """
    normalized_path = path if path.startswith("/") else f"/{path}"
    request_url = f"{connector.base_url.rstrip('/')}{normalized_path}"
    try:
        await request_json("GET", request_url, headers={"Accept": "application/json"}, timeout=timeout_seconds)
        up = True
        reason = None
    except HttpJsonError as exc:
        up = False
        reason = f"probe failed: {exc}"

    return Link(
        up=up,
        activatable=True,
        reason=reason,
        checked_at=datetime.now(UTC),
    )


__all__ = [
    "build_openai_connector",
    "probe_openai_compatible_link",
    "require_runtime_soulstone",
    "resolved_soulstone_base_url",
    "resolved_soulstone_port",
]
