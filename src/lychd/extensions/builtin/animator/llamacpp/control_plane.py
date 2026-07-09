from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode, urlsplit, urlunsplit

from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.lib.http import DEFAULT_TIMEOUT_SECONDS, HttpJsonError, request_json

if TYPE_CHECKING:
    from lychd.config.runes import RuneConfig
    from lychd.domain.animation.animators import Animator
    from lychd.domain.animation.connectors import Connector


type RuntimeAnimator = Animator[Connector, RuneConfig]
_HTTP_SERVICE_UNAVAILABLE = 503

# Back-compat alias: the control plane now returns the runtime-neutral domain DTO
# (spec §5). ``LlamaCppLifecycle`` remains importable for one release.
LlamaCppLifecycle = AnimatorLifecycle


class LlamaCppControlPlaneError(RuntimeError):
    """Raised when llama.cpp control-plane calls fail."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        """Preserve the optional HTTP status for readiness classification."""
        super().__init__(message)
        self.status = status


class LlamaCppControlPlane:
    """Async HTTP client for llama.cpp health/router lifecycle operations.

    The control plane is intentionally decoupled from old resolved-binding DTOs.
    It can inspect:
    - a runtime animator whose connector exposes llama.cpp metadata, or
    - an explicit ``(base_url, mode, model_id)`` target.

    All I/O is async httpx (A3-U3: no blocking ``urlopen``). Endpoint logic
    (``/health`` / ``/props`` / ``/models`` / ``/models/load`` / ``/models/unload``)
    is preserved verbatim.
    """

    def __init__(self, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """Initialize HTTP timeout used for llama.cpp control-plane probes."""
        self._timeout = timeout_seconds

    async def inspect_animator(self, animator: RuntimeAnimator) -> AnimatorLifecycle:
        """Inspect llama.cpp runtime state for a runtime animator.

        The animator must expose a connector with ``kind == 'llamacpp'`` and the
        connector must publish ``mode`` and optional ``router_query_model_id``.
        """
        connector = animator.connector
        if getattr(connector, "kind", None) != "llamacpp":
            msg = f"Animator '{animator.id}' is not backed by a llama.cpp connector."
            raise LlamaCppControlPlaneError(msg)

        mode = getattr(connector, "mode", None)
        if mode not in {"single", "router"}:
            msg = f"llama.cpp connector on animator '{animator.id}' does not expose a valid mode."
            raise LlamaCppControlPlaneError(msg)

        model_id = getattr(connector, "router_query_model_id", None)
        return await self.inspect(
            base_url=connector.base_url,
            mode=cast("str", mode),
            model_id=cast("str | None", model_id),
        )

    async def inspect(self, *, base_url: str, mode: str, model_id: str | None = None) -> AnimatorLifecycle:
        """Inspect runtime state from llama.cpp health/props/models endpoints."""
        lifecycle = AnimatorLifecycle(runtime="llamacpp", base_url=base_url, mode=mode)

        model_query = model_id if mode == "router" else None

        try:
            health = await self._request_json(base_url, "GET", "/health", query=self._query_model(model_query))
            lifecycle.raw["health"] = health
            lifecycle.health = self._coerce_health(health)
        except LlamaCppControlPlaneError as exc:
            lifecycle.raw["health_error"] = str(exc)
            # llama.cpp reports an in-progress model load as HTTP 503 with a
            # JSON error body. This is readiness, not a stopped runtime. Match
            # only the explicit loading signal; unrelated 503s stay unknown.
            if exc.status == _HTTP_SERVICE_UNAVAILABLE and "loading model" in str(exc).lower():
                lifecycle.health = "loading"

        try:
            props = await self._request_json(base_url, "GET", "/props", query=self._query_model(model_query))
            lifecycle.raw["props"] = props
            lifecycle.sleeping = self._as_bool(props.get("is_sleeping"))
            lifecycle.total_slots = self._as_int(props.get("total_slots"))
            lifecycle.active_model = self._as_str(props.get("model_path"))
        except LlamaCppControlPlaneError as exc:
            lifecycle.raw["props_error"] = str(exc)

        if mode == "router":
            try:
                models = await self._request_json(base_url, "GET", "/models")
                lifecycle.raw["models"] = models
                lifecycle.supports_router = True
                self._populate_router_models(lifecycle, models)
            except LlamaCppControlPlaneError as exc:
                lifecycle.raw["models_error"] = str(exc)

        return lifecycle

    async def load_model(self, base_url: str, model: str) -> bool:
        """Request router to load a model by id."""
        payload = {"model": model}
        response = await self._request_json(base_url, "POST", "/models/load", payload=payload)
        return bool(response.get("success"))

    async def unload_model(self, base_url: str, model: str) -> bool:
        """Request router to unload a model by id."""
        payload = {"model": model}
        response = await self._request_json(base_url, "POST", "/models/unload", payload=payload)
        return bool(response.get("success"))

    async def _request_json(
        self,
        base_url: str,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        request_url = self._build_url(base_url, path)
        try:
            return await request_json(
                method,
                request_url,
                query=query,
                payload=payload,
                timeout=self._timeout,
            )
        except HttpJsonError as exc:
            error_msg = f"{method} {path} failed: {exc}"
            raise LlamaCppControlPlaneError(error_msg, status=exc.status) from exc

    def _build_url(self, base_url: str, path: str, *, query: dict[str, str] | None = None) -> str:
        split = urlsplit(base_url)
        base_path = split.path.rstrip("/")
        base_path = base_path.removesuffix("/v1")

        normalized_path = path if path.startswith("/") else f"/{path}"
        final_path = f"{base_path}{normalized_path}"
        query_string = urlencode(query or {})
        return urlunsplit((split.scheme, split.netloc, final_path, query_string, ""))

    def _coerce_health(self, payload: dict[str, object]) -> str:
        status = self._as_str(payload.get("status"))
        if status == "ok":
            return "ok"
        error = payload.get("error")
        error_map = self._as_map(error)
        if error_map is not None:
            message = str(error_map.get("message", "")).lower()
            if "loading model" in message:
                return "loading"
            return "error"
        return "unknown"

    def _populate_router_models(self, lifecycle: AnimatorLifecycle, payload: dict[str, object]) -> None:
        entries = payload.get("data")
        if not isinstance(entries, list):
            return

        available: list[str] = []
        loaded: list[str] = []
        for entry_obj in cast("list[object]", entries):
            entry_map = self._as_map(entry_obj)
            if entry_map is None:
                continue
            model_id = self._as_str(entry_map.get("id"))
            if not model_id:
                continue
            available.append(model_id)

            markers = self._extract_markers(entry_map)
            if markers:
                lifecycle.model_capabilities[model_id] = markers

            status = entry_map.get("status")
            status_map = self._as_map(status)
            if status_map is not None and self._as_str(status_map.get("value")) == "loaded":
                loaded.append(model_id)

        lifecycle.available_models = available
        lifecycle.loaded_models = loaded

    def _extract_markers(self, entry_map: dict[str, object]) -> list[str]:
        """Read tolerant capability markers from one ``/models`` entry (absent → empty)."""
        raw = entry_map.get("capabilities")
        if not isinstance(raw, list):
            return []
        return [str(item) for item in cast("list[object]", raw) if isinstance(item, str) and item.strip()]

    def _query_model(self, model: str | None) -> dict[str, str] | None:
        if model is None:
            return None
        return {"model": model}

    def _as_bool(self, value: object) -> bool | None:
        if isinstance(value, bool):
            return value
        return None

    def _as_int(self, value: object) -> int | None:
        if isinstance(value, int):
            return value
        return None

    def _as_str(self, value: object) -> str | None:
        if isinstance(value, str):
            return value
        return None

    def _as_map(self, value: object) -> dict[str, object] | None:
        if not isinstance(value, Mapping):
            return None

        mapping_value = cast("Mapping[object, object]", value)
        normalized: dict[str, object] = {}
        for key, item in mapping_value.items():
            normalized[str(key)] = item
        return normalized
