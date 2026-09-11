from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import urlencode, urlsplit, urlunsplit

from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.services.adapters.runtimes.shared import parse_openai_model_inventory
from lychd.extensions.builtin.animator.llamacpp.connector import LlamacppConnector
from lychd.lib.http import DEFAULT_TIMEOUT_SECONDS, HttpJsonError, request_json

_HTTP_SERVICE_UNAVAILABLE = 503


class LlamaCppControlPlaneError(RuntimeError):
    """Raised when llama.cpp control-plane calls fail."""

    def __init__(self, message: str, *, status: int | None = None, transport: bool = False) -> None:
        """Preserve the optional HTTP status for readiness classification."""
        super().__init__(message)
        self.status = status
        self.transport = transport


class LlamaCppControlPlane:
    """Async HTTP client for llama.cpp health/router lifecycle operations.

    The control plane is intentionally decoupled from old resolved-binding DTOs.
    It can inspect:
    - a runtime animator whose connector exposes llama.cpp metadata, or
    - an explicit ``(base_url, mode, model_id)`` target.

    All I/O is async httpx (A3-U3: no blocking ``urlopen``). Endpoint logic
    (``/health`` / ``/models`` / ``/models/load``) is kept behind this boundary.
    """

    def __init__(self, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """Initialize HTTP timeout used for llama.cpp control-plane probes."""
        self._timeout = timeout_seconds

    async def inspect_animator(self, animator: RuntimeAnimator) -> AnimatorLifecycle:
        """Inspect llama.cpp runtime state for a runtime animator.

        The animator must expose a llama.cpp connector with ``mode`` and optional
        ``router_query_model_id``.
        """
        connector = animator.connector
        if not isinstance(connector, LlamacppConnector):
            msg = f"Animator '{animator.name}' is not backed by a llama.cpp connector."
            raise LlamaCppControlPlaneError(msg)

        mode = getattr(connector, "mode", None)
        if mode not in {"single", "router"}:
            msg = f"llama.cpp connector on animator '{animator.name}' does not expose a valid mode."
            raise LlamaCppControlPlaneError(msg)

        model_id = getattr(connector, "router_query_model_id", None)
        return await self.inspect(
            base_url=connector.base_url,
            mode=cast("str", mode),
            model_id=cast("str | None", model_id),
        )

    async def inspect(self, *, base_url: str, mode: str, model_id: str | None = None) -> AnimatorLifecycle:
        """Inspect runtime state from llama.cpp health and router-model endpoints."""
        lifecycle = AnimatorLifecycle()

        model_query = model_id if mode == "router" else None

        try:
            health = await self._request_json(base_url, "GET", "/health", query=self._query_model(model_query))
            lifecycle.health = self._coerce_health(health)
        except LlamaCppControlPlaneError as exc:
            lifecycle.error = str(exc)
            # llama.cpp reports an in-progress model load as HTTP 503 with a
            # JSON error body. This is readiness, not a stopped runtime. Match
            # only the explicit loading signal; unrelated 503s stay unknown.
            if exc.status == _HTTP_SERVICE_UNAVAILABLE and "loading model" in str(exc).lower():
                lifecycle.health = "loading"

        if mode == "router":
            try:
                models = await self._request_json(base_url, "GET", "/models")
                lifecycle.supports_router = True
                self._populate_router_models(lifecycle, models)
            except LlamaCppControlPlaneError as exc:
                lifecycle.error = str(exc)
            except HttpJsonError as exc:
                lifecycle.health = "error"
                lifecycle.error = f"model inventory invalid: {exc}"
        elif lifecycle.health == "ok":
            try:
                models = await self._request_json(base_url, "GET", "/v1/models")
                model_ids = parse_openai_model_inventory(models)
                lifecycle.available_models = list(model_ids)
                lifecycle.loaded_models = list(model_ids)
            except LlamaCppControlPlaneError as exc:
                lifecycle.health = "unknown" if exc.transport else "error"
                if exc.status == _HTTP_SERVICE_UNAVAILABLE and "loading model" in str(exc).lower():
                    lifecycle.health = "loading"
                lifecycle.error = f"model inventory unavailable: {exc}"
            except HttpJsonError as exc:
                lifecycle.health = "error"
                lifecycle.error = f"model inventory unavailable or invalid: {exc}"

        return lifecycle

    async def load_model(self, base_url: str, model: str) -> bool:
        """Request router to load a model, accepting only a literal JSON ``true`` receipt."""
        payload = {"model": model}
        response = await self._request_json(base_url, "POST", "/models/load", payload=payload)
        return response.get("success") is True

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
            raise LlamaCppControlPlaneError(error_msg, status=exc.status, transport=exc.transport) from exc

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
        available = list(parse_openai_model_inventory(payload))
        entries = cast("list[dict[str, object]]", payload["data"])
        loaded: list[str] = []
        loading: list[str] = []
        unloaded: list[str] = []
        for model_id, entry in zip(available, entries, strict=True):
            status = entry.get("status")
            status_map = self._as_map(status)
            value = self._as_str(status_map.get("value")) if status_map is not None else None
            if value is None:
                msg = f"router model {model_id!r} has no status.value string"
                raise HttpJsonError(msg)
            if status_map is not None and status_map.get("failed", False) is not False:
                continue
            if value == "loaded":
                loaded.append(model_id)
            elif value == "loading":
                loading.append(model_id)
            elif value == "unloaded":
                unloaded.append(model_id)

        lifecycle.available_models = available
        lifecycle.loaded_models = loaded
        lifecycle.loading_models = loading
        lifecycle.unloaded_models = unloaded

    def _query_model(self, model: str | None) -> dict[str, str] | None:
        if model is None:
            return None
        return {"model": model, "autoload": "false"}

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
