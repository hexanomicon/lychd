from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from lychd.config.runes import RuneConfig
    from lychd.domain.animation.animators import Animator
    from lychd.domain.animation.connectors import Connector


type RuntimeAnimator = Animator[Connector, RuneConfig]


class LlamaCppControlPlaneError(RuntimeError):
    """Raised when llama.cpp control-plane calls fail."""


class LlamaCppLifecycle(BaseModel):
    """Observed runtime lifecycle state from llama.cpp control-plane endpoints."""

    model_config = ConfigDict(extra="forbid")

    runtime: str = "llamacpp"
    base_url: str
    mode: str
    health: str = "unknown"
    sleeping: bool | None = None
    supports_router: bool = False
    active_model: str | None = None
    loaded_models: list[str] = Field(default_factory=list)
    available_models: list[str] = Field(default_factory=list)
    total_slots: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class LlamaCppControlPlane:
    """Minimal HTTP client for llama.cpp health/router lifecycle operations.

    The control plane is intentionally decoupled from old resolved-binding DTOs.
    It can inspect:
    - a runtime animator whose connector exposes llama.cpp metadata, or
    - an explicit ``(base_url, mode, model_id)`` target.
    """

    def __init__(self, *, timeout_seconds: float = 5.0) -> None:
        """Initialize HTTP timeout used for llama.cpp control-plane probes."""
        self._timeout = timeout_seconds

    def inspect_animator(self, animator: RuntimeAnimator) -> LlamaCppLifecycle:
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
        return self.inspect(base_url=animator.base_url, mode=cast("str", mode), model_id=cast("str | None", model_id))

    def inspect(self, *, base_url: str, mode: str, model_id: str | None = None) -> LlamaCppLifecycle:
        """Inspect runtime state from llama.cpp health/props/models endpoints."""
        lifecycle = LlamaCppLifecycle(base_url=base_url, mode=mode)

        model_query = model_id if mode == "router" else None

        try:
            health = self._request_json(base_url, "GET", "/health", query=self._query_model(model_query))
            lifecycle.raw["health"] = health
            lifecycle.health = self._coerce_health(health)
        except LlamaCppControlPlaneError as exc:
            lifecycle.raw["health_error"] = str(exc)

        try:
            props = self._request_json(base_url, "GET", "/props", query=self._query_model(model_query))
            lifecycle.raw["props"] = props
            lifecycle.sleeping = self._as_bool(props.get("is_sleeping"))
            lifecycle.total_slots = self._as_int(props.get("total_slots"))
            lifecycle.active_model = self._as_str(props.get("model_path"))
        except LlamaCppControlPlaneError as exc:
            lifecycle.raw["props_error"] = str(exc)

        if mode == "router":
            try:
                models = self._request_json(base_url, "GET", "/models")
                lifecycle.raw["models"] = models
                lifecycle.supports_router = True
                self._populate_router_models(lifecycle, models)
            except LlamaCppControlPlaneError as exc:
                lifecycle.raw["models_error"] = str(exc)

        return lifecycle

    def load_model(self, base_url: str, model: str) -> bool:
        """Request router to load a model by id."""
        payload = {"model": model}
        response = self._request_json(base_url, "POST", "/models/load", payload=payload)
        return bool(response.get("success"))

    def unload_model(self, base_url: str, model: str) -> bool:
        """Request router to unload a model by id."""
        payload = {"model": model}
        response = self._request_json(base_url, "POST", "/models/unload", payload=payload)
        return bool(response.get("success"))

    def _request_json(
        self,
        base_url: str,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        request_url = self._build_url(base_url, path, query=query)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        request = Request(request_url, data=body, headers=headers, method=method)  # noqa: S310

        try:
            with urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            error_msg = f"{method} {path} failed with status {exc.code}: {message}"
            raise LlamaCppControlPlaneError(error_msg) from exc
        except URLError as exc:
            error_msg = f"{method} {path} failed: {exc.reason}"
            raise LlamaCppControlPlaneError(error_msg) from exc

        if not raw.strip():
            return {}

        try:
            parsed: object = json.loads(raw)
        except json.JSONDecodeError as exc:
            error_msg = f"{method} {path} returned invalid JSON: {raw[:120]}"
            raise LlamaCppControlPlaneError(error_msg) from exc

        parsed_map = self._as_map(parsed)
        if parsed_map is not None:
            return parsed_map
        if isinstance(parsed, list):
            return {"data": cast("list[object]", parsed)}
        error_msg = f"{method} {path} returned unsupported payload type: {type(parsed)}"
        raise LlamaCppControlPlaneError(error_msg)

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

    def _populate_router_models(self, lifecycle: LlamaCppLifecycle, payload: dict[str, object]) -> None:
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

            status = entry_map.get("status")
            status_map = self._as_map(status)
            if status_map is not None and self._as_str(status_map.get("value")) == "loaded":
                loaded.append(model_id)

        lifecycle.available_models = available
        lifecycle.loaded_models = loaded

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
