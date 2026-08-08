"""Shared runtime-adapter helpers.

These helpers keep adapter modules focused on runtime-specific planning while
centralizing repeated type-guard and connector construction logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from lychd.domain.animation.capabilities import ActivationResult, CapabilityPhase, CapabilitySpec
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
MAX_OPENAI_MODEL_INVENTORY_ENTRIES = 1024
MAX_OPENAI_MODEL_ID_LENGTH = 512


async def probe_openai_compatible_link(
    connector: OpenAICompatibleConnector,
    *,
    timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
    path: str = "/models",
) -> Link:
    """Probe link liveness and the exact OpenAI-compatible model inventory.

    Issues a short-timeout ``GET {base_url}{path}`` (default ``/models``, i.e.
    ``/v1/models`` for the standard Soulstone base URL), validates the standard
    ``data[*].id`` inventory, records that observation separately from the
    connector's declared catalogue, bounds retained inventory cardinality and
    id length, and returns a refreshed ``Link``. Transport failure resolves to
    ``up=False``. A reachable but non-conformant response keeps the physical
    link live and records a separate inventory error; this function never
    raises (A3-U3: async httpx replaces the blocking ``urlopen``).
    """
    normalized_path = path if path.startswith("/") else f"/{path}"
    request_url = f"{connector.base_url.rstrip('/')}{normalized_path}"
    try:
        payload = await request_json(
            "GET",
            request_url,
            headers={"Accept": "application/json"},
            timeout=timeout_seconds,
        )
    except HttpJsonError as exc:
        connector.set_observed_model_ids(None)
        if exc.transport:
            connector.set_inventory_error(None)
            up = False
            reason = f"probe failed: {exc}"
        else:
            connector.set_inventory_error(f"inventory probe failed: {exc}")
            up = True
            reason = None
    else:
        up = True
        reason = None
        try:
            model_ids = _parse_openai_model_inventory(payload)
        except HttpJsonError as exc:
            connector.set_observed_model_ids(None)
            connector.set_inventory_error(f"inventory validation failed: {exc}")
        else:
            connector.set_observed_model_ids(model_ids)
            connector.set_inventory_error(None)

    return Link(
        up=up,
        activatable=True,
        reason=reason,
        checked_at=datetime.now(UTC),
    )


def _parse_openai_model_inventory(payload: dict[str, object]) -> tuple[str, ...]:
    """Validate and detach one OpenAI ``/models`` response."""
    data = payload.get("data")
    if not isinstance(data, list):
        msg = "OpenAI-compatible /models response has no data list"
        raise HttpJsonError(msg)
    entries = cast("list[object]", data)
    if len(entries) > MAX_OPENAI_MODEL_INVENTORY_ENTRIES:
        msg = (
            "OpenAI-compatible /models response exceeds "
            f"{MAX_OPENAI_MODEL_INVENTORY_ENTRIES} entries"
        )
        raise HttpJsonError(msg)

    model_ids: list[str] = []
    seen: set[str] = set()
    for index, entry_value in enumerate(entries):
        if not isinstance(entry_value, dict):
            msg = f"OpenAI-compatible /models entry {index} is not an object"
            raise HttpJsonError(msg)
        entry = cast("dict[object, object]", entry_value)
        model_id = entry.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            msg = f"OpenAI-compatible /models entry {index} has no non-empty string id"
            raise HttpJsonError(msg)
        if len(model_id) > MAX_OPENAI_MODEL_ID_LENGTH:
            msg = (
                f"OpenAI-compatible /models entry {index} id exceeds "
                f"{MAX_OPENAI_MODEL_ID_LENGTH} characters"
            )
            raise HttpJsonError(msg)
        if model_id in seen:
            msg = f"OpenAI-compatible /models repeats model id {model_id!r}"
            raise HttpJsonError(msg)
        seen.add(model_id)
        model_ids.append(model_id)
    return tuple(model_ids)


def fixed_openai_activation_result(
    connector: OpenAICompatibleConnector,
    spec: CapabilitySpec,
) -> ActivationResult:
    """Reject activation while preserving the exact observed fixed-runtime phase."""
    reason = "fixed capability; lifecycle owned by unit"
    if not connector.link.up:
        return ActivationResult(accepted=False, phase=CapabilityPhase.COLD, reason=reason)
    if connector.inventory_error is not None:
        return ActivationResult(
            accepted=False,
            phase=CapabilityPhase.ERROR,
            reason=connector.inventory_error,
        )
    observed_model_ids = connector.observed_model_ids
    if observed_model_ids is None:
        return ActivationResult(
            accepted=False,
            phase=CapabilityPhase.ERROR,
            reason="fixed capability inventory is unverified",
        )
    if spec.model_id not in observed_model_ids:
        return ActivationResult(
            accepted=False,
            phase=CapabilityPhase.ERROR,
            reason=f"declared model {spec.model_id!r} is absent from /models",
        )
    return ActivationResult(accepted=False, phase=CapabilityPhase.WARM, reason=reason)


__all__ = [
    "build_openai_connector",
    "fixed_openai_activation_result",
    "probe_openai_compatible_link",
    "require_runtime_soulstone",
    "resolved_soulstone_base_url",
    "resolved_soulstone_port",
]
