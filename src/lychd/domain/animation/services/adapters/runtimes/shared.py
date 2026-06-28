"""Shared runtime-adapter helpers.

These helpers keep adapter modules focused on runtime-specific planning while
centralizing repeated type-guard and connector construction logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
from lychd.system.schemas import QuadletContainer

if TYPE_CHECKING:
    from lychd.domain.animation.services.adapters.contracts import SoulstoneRuntimePlanner


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


def transmute_single_soulstone_quadlet(
    soulstone: SoulstoneConfig,
    *,
    runtime_planner: SoulstoneRuntimePlanner | None = None,
) -> QuadletContainer:
    """Build the generated Quadlet manifest for a single Soulstone context."""
    from lychd.domain.animation.transmute import Transmuter

    manifests = Transmuter(runtime_planner=runtime_planner).transmute_all([soulstone])
    container_name = f"lychd-{soulstone.name}"
    for manifest in manifests:
        if isinstance(manifest, QuadletContainer) and manifest.container_name == container_name:
            return manifest

    msg = f"Transmutation did not produce QuadletContainer for Soulstone '{soulstone.name}'."
    raise RuntimeError(msg)


PROBE_TIMEOUT_SECONDS = 2.0


def probe_openai_compatible_link(
    connector: OpenAICompatibleConnector,
    *,
    timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
    path: str = "/models",
) -> Link:
    """Perform a live reachability probe of an OpenAI-compatible endpoint.

    Issues a short-timeout ``GET {base_url}{path}`` (default ``/models``, i.e.
    ``/v1/models`` for the standard Soulstone base URL) and returns a refreshed
    ``Link``. The caller is expected to push it onto the connector via
    ``connector.set_link(...)``. A down or non-OpenAI responder resolves to
    ``up=False`` with a human-readable reason; it never raises.
    """
    request_url = f"{connector.base_url.rstrip('/')}{path if path.startswith('/') else f'/{path}'}"
    request = Request(request_url, method="GET", headers={"Accept": "application/json"})  # noqa: S310
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            # ``urlopen`` raises HTTPError for status >= 400 and follows 3xx
            # redirects automatically, so reaching the body implies success.
            up = True
            reason = None
            _ = response.status
    except HTTPError as exc:
        up = False
        reason = f"probe failed: HTTP {exc.code}"
    except URLError as exc:
        up = False
        reason = f"probe unreachable: {exc.reason}"
    except TimeoutError:
        up = False
        reason = f"probe timed out after {timeout_seconds}s"
    except OSError as exc:
        up = False
        reason = f"probe error: {exc}"

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
    "transmute_single_soulstone_quadlet",
]
