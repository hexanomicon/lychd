from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit, urlunsplit

import httpx

from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.extensions.builtin.animator.tabby_auth import (
    TabbyAPIAuthSecretError,
    load_tabbyapi_auth_keys,
)
from lychd.lib.http import DEFAULT_TIMEOUT_SECONDS, HttpJsonError, request_json

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from lychd.config.runes import RuneConfig
    from lychd.domain.animation.animators import Animator
    from lychd.domain.animation.connectors import Connector


type RuntimeAnimator = Animator[Connector, RuneConfig]

_HTTP_OK = 200
_HTTP_SERVICE_UNAVAILABLE = 503
_NO_MODEL_DETAIL = "no models are currently loaded"


class TabbyAPIControlPlaneError(RuntimeError):
    """A rejected, malformed, or unreachable TabbyAPI control operation."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        ambiguous: bool = False,
        unreachable: bool = False,
    ) -> None:
        """Retain status and whether a detached upstream operation may continue."""
        super().__init__(message)
        self.status = status
        self.ambiguous = ambiguous
        self.unreachable = unreachable


@dataclass(slots=True)
class _LoadOperation:
    """Local observation of one TabbyAPI detached model-load stream."""

    model_name: str
    acceptance: asyncio.Future[None]
    task: asyncio.Task[None] | None = None
    stream_finished: bool = False
    ambiguous: bool = False
    uncertainty: str | None = None
    error: str | None = None


class TabbyAPIControlPlane:
    """Async lifecycle client for ExLlamaV3 served by TabbyAPI.

    Contract verified against TabbyAPI ``0158fb48``. A healthy service may have
    no loaded model. Loads are detached server-side and report progress over SSE,
    so this client starts consumption in a background task and lets orchestration
    converge through ordinary readiness probes.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Configure short request timeouts; the Orchestrator owns convergence time."""
        self._timeout = timeout_seconds
        self._loads: dict[str, _LoadOperation] = {}
        self._auth_secret_names: dict[str, str] = {}

    def register_runtime(self, base_url: str, auth_secret_name: str) -> None:
        """Bind one runtime endpoint to its Vessel-mounted Tabby auth document."""
        self._auth_secret_names[self._runtime_key(base_url)] = auth_secret_name

    async def inspect_animator(self, animator: RuntimeAnimator) -> AnimatorLifecycle:
        """Inspect the TabbyAPI service backing one ExLlamaV3 animator."""
        connector = animator.connector
        if getattr(connector, "kind", None) != "exllamav3":
            msg = f"Animator '{animator.id}' is not backed by an ExLlamaV3 connector."
            raise TabbyAPIControlPlaneError(msg)
        return await self.inspect(base_url=connector.base_url)

    async def inspect(self, *, base_url: str) -> AnimatorLifecycle:
        """Read service health, model inventory, and the currently loaded model."""
        lifecycle = AnimatorLifecycle(
            runtime="exllamav3",
            base_url=base_url,
            mode="dynamic",
            supports_router=True,
        )

        health = await self._request_json(base_url, "GET", "/health")
        lifecycle.raw["health"] = health
        health_status = self._as_str(health.get("status"))
        if health_status != "healthy":
            lifecycle.health = "error"
            lifecycle.raw["health_error"] = health.get("issues", "tabbyapi_unhealthy")
            return lifecycle
        lifecycle.health = "ok"

        models = await self._request_json(base_url, "GET", "/v1/models")
        lifecycle.raw["models"] = models
        lifecycle.available_models = self._model_ids(models)

        try:
            current = await self._request_json(base_url, "GET", "/v1/model")
        except TabbyAPIControlPlaneError as exc:
            if exc.status != _HTTP_SERVICE_UNAVAILABLE or _NO_MODEL_DETAIL not in str(exc).lower():
                raise
            lifecycle.raw["current_model"] = None
        else:
            lifecycle.raw["current_model"] = current
            active_model = self._as_str(current.get("id"))
            if not active_model:
                msg = "TabbyAPI /v1/model returned HTTP 200 without a non-empty id."
                raise TabbyAPIControlPlaneError(msg)
            lifecycle.active_model = active_model
            lifecycle.loaded_models = [active_model]
            lifecycle.total_slots = self._total_slots(current)

        await self._apply_pending_load(lifecycle)
        return lifecycle

    async def load_model(self, base_url: str, model: str) -> bool:
        """Start a detached TabbyAPI load and return once HTTP acceptance is known."""
        self._validate_model_name(model)
        key = self._runtime_key(base_url)
        existing = self._loads.get(key)
        if existing is not None and existing.error is None:
            if existing.model_name == model:
                await self._await_acceptance(existing)
                return True
            msg = f"TabbyAPI is already loading '{existing.model_name}'; refusing concurrent load of '{model}'."
            raise TabbyAPIControlPlaneError(msg, ambiguous=True)

        acceptance: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        operation = _LoadOperation(model_name=model, acceptance=acceptance)
        self._loads[key] = operation
        operation.task = asyncio.create_task(
            self._drive_model_load(base_url, operation),
            name=f"tabbyapi-load:{model}",
        )

        await self._await_acceptance(operation)
        return True

    async def _await_acceptance(self, operation: _LoadOperation) -> None:
        """Share one shielded HTTP-acceptance result between coalesced callers."""
        try:
            await asyncio.wait_for(asyncio.shield(operation.acceptance), timeout=self._timeout)
        except TimeoutError as exc:
            operation.ambiguous = True
            msg = (
                f"TabbyAPI load acceptance for '{operation.model_name}' timed out; "
                "the detached load may still be running."
            )
            operation.uncertainty = msg
            raise TabbyAPIControlPlaneError(msg, ambiguous=True) from exc

    async def abandon_model_load(self, base_url: str, model: str) -> None:
        """Stop only LychD's SSE observer after the canonical warm-up deadline."""
        operation = self._loads.get(self._runtime_key(base_url))
        if operation is None or operation.model_name != model:
            return
        operation.ambiguous = True
        operation.uncertainty = "Warm-up convergence ended while TabbyAPI may still be loading the model."
        task = operation.task
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        operation.task = None

    async def unload_model(self, base_url: str, model: str) -> bool:
        """Unload the named current model; never interrupt an ambiguous load."""
        key = self._runtime_key(base_url)
        operation = self._loads.get(key)
        if operation is not None and not operation.stream_finished:
            return False

        lifecycle = await self.inspect(base_url=base_url)
        if lifecycle.active_model != model:
            return False
        await self._request_json(base_url, "POST", "/v1/model/unload", allow_null=True)
        self._loads.pop(key, None)
        return True

    async def _drive_model_load(
        self,
        base_url: str,
        operation: _LoadOperation,
    ) -> None:
        """Consume every SSE stage; only EOF after a terminal frame is success."""
        acceptance = operation.acceptance
        key = self._runtime_key(base_url)
        url = self._build_url(base_url, "/v1/model/load")
        timeout = httpx.Timeout(connect=self._timeout, read=None, write=self._timeout, pool=self._timeout)
        try:
            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream(
                    "POST",
                    url,
                    json={"model_name": operation.model_name, "backend": "exllamav3"},
                    headers={"Content-Type": "application/json", **self._authorization_headers(base_url)},
                ) as response,
            ):
                await self._consume_model_load_response(response, acceptance)
            operation.stream_finished = True
        except asyncio.CancelledError:
            operation.ambiguous = True
            operation.uncertainty = operation.uncertainty or "TabbyAPI load observer was cancelled."
            if not acceptance.done():
                acceptance.cancel()
            raise
        except httpx.HTTPError as exc:
            operation.ambiguous = True
            operation.uncertainty = f"TabbyAPI model-load transport became uncertain: {exc}"
            if not acceptance.done():
                acceptance.set_exception(
                    TabbyAPIControlPlaneError(
                        f"POST /v1/model/load transport failed: {exc}",
                        ambiguous=True,
                        unreachable=True,
                    )
                )
        except TabbyAPIControlPlaneError as exc:
            self._record_load_error(key, operation, exc)
        except Exception as exc:  # noqa: BLE001 - post-accept observer failure leaves server truth ambiguous
            operation.ambiguous = True
            operation.uncertainty = (
                f"TabbyAPI model-load observer failed after an unknown boundary ({type(exc).__name__})."
            )
            if not acceptance.done():
                acceptance.set_exception(TabbyAPIControlPlaneError(operation.uncertainty, ambiguous=True))

    def _record_load_error(
        self,
        key: str,
        operation: _LoadOperation,
        error: TabbyAPIControlPlaneError,
    ) -> None:
        """Record a post-accept error or discard a definitive pre-accept rejection."""
        acceptance = operation.acceptance
        accepted = acceptance.done() and not acceptance.cancelled() and acceptance.exception() is None
        if error.ambiguous:
            operation.ambiguous = True
            operation.uncertainty = str(error)
        elif accepted:
            operation.error = str(error)
        if acceptance.done():
            return
        acceptance.set_exception(error)
        if not error.ambiguous and self._loads.get(key) is operation:
            # Tabby rejected before accepting any mutation; later health and
            # retries remain governed by observed server truth.
            self._loads.pop(key, None)

    async def _consume_model_load_response(
        self,
        response: httpx.Response,
        acceptance: asyncio.Future[None],
    ) -> None:
        """Validate HTTP acceptance and consume every model-load SSE stage."""
        if response.status_code != _HTTP_OK:
            body = (await response.aread()).decode(errors="replace")[:200]
            msg = f"POST /v1/model/load failed with status {response.status_code}: {body}"
            raise TabbyAPIControlPlaneError(msg, status=response.status_code)
        if not acceptance.done():
            acceptance.set_result(None)

        saw_finished_model = False
        async for payload in self._iter_sse_json(response):
            error = self._error_message(payload)
            if error is not None:
                msg = f"TabbyAPI model load failed: {error}"
                raise TabbyAPIControlPlaneError(msg)
            if self._is_finished_model_event(payload):
                saw_finished_model = True

        if not saw_finished_model:
            msg = "TabbyAPI model-load stream ended without a finished model event."
            raise TabbyAPIControlPlaneError(msg, ambiguous=True)

    async def _iter_sse_json(self, response: httpx.Response) -> AsyncIterator[dict[str, object]]:
        """Decode standard SSE data fields into JSON objects, ignoring comments."""
        data_lines: list[str] = []
        async for line in response.aiter_lines():
            if not line:
                if data_lines:
                    yield self._decode_sse_data("\n".join(data_lines))
                    data_lines.clear()
                continue
            if line.startswith(":"):
                continue
            field, separator, value = line.partition(":")
            if field != "data":
                continue
            data_lines.append(value[1:] if separator and value.startswith(" ") else value)
        if data_lines:
            yield self._decode_sse_data("\n".join(data_lines))

    def _decode_sse_data(self, data: str) -> dict[str, object]:
        try:
            payload: object = json.loads(data)
        except json.JSONDecodeError as exc:
            msg = f"TabbyAPI model-load stream returned invalid JSON: {data[:120]}"
            raise TabbyAPIControlPlaneError(msg, ambiguous=True) from exc
        if not isinstance(payload, dict):
            msg = f"TabbyAPI model-load stream returned {type(payload).__name__}, expected an object."
            raise TabbyAPIControlPlaneError(msg, ambiguous=True)
        mapping = cast("dict[object, object]", payload)
        return {str(key): value for key, value in mapping.items()}

    def _is_finished_model_event(self, payload: dict[str, object]) -> bool:
        """Recognize only a complete terminal event from the pinned Tabby contract."""
        if payload.get("status") != "finished" or payload.get("model_type") != "model":
            return False
        module = payload.get("module")
        modules = payload.get("modules")
        valid_counters = (
            isinstance(module, int)
            and not isinstance(module, bool)
            and isinstance(modules, int)
            and not isinstance(modules, bool)
            and module > 0
            and module == modules
        )
        if not valid_counters:
            msg = "TabbyAPI model-load stream returned an invalid finished-model counter."
            raise TabbyAPIControlPlaneError(msg, ambiguous=True)
        return True

    async def _apply_pending_load(self, lifecycle: AnimatorLifecycle) -> None:
        key = self._runtime_key(lifecycle.base_url)
        operation = self._loads.get(key)
        if operation is None:
            return

        lifecycle.raw["pending_model"] = operation.model_name
        lifecycle.raw["load_stream_finished"] = operation.stream_finished
        lifecycle.raw["load_ambiguous"] = operation.ambiguous
        if operation.uncertainty is not None:
            lifecycle.raw["load_uncertainty"] = operation.uncertainty
        if lifecycle.active_model == operation.model_name:
            task = operation.task
            if task is not None:
                if not task.done():
                    task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            self._loads.pop(key, None)
            lifecycle.raw.pop("pending_model", None)
            return
        if operation.stream_finished:
            # The pinned stream reached a valid terminal event, but server truth
            # no longer contains the target. The process restarted or discarded
            # the load; no detached mutation remains to fence.
            self._loads.pop(key, None)
            lifecycle.raw.pop("pending_model", None)
            lifecycle.raw["load_reconciliation"] = "finished_stream_without_active_model"
            return
        if operation.error is not None:
            lifecycle.health = "error"
            lifecycle.raw["load_error"] = operation.error
            return
        task = operation.task
        if operation.ambiguous and (task is None or task.done()):
            lifecycle.health = "error"
            lifecycle.raw["load_error"] = (
                f"{operation.uncertainty or 'TabbyAPI load outcome is ambiguous'} "
                "Restart the caged Vessel to reset the runtime epoch safely."
            )
            return
        lifecycle.health = "loading"

    async def _request_json(
        self,
        base_url: str,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        allow_null: bool = False,
    ) -> dict[str, object]:
        try:
            return await request_json(
                method,
                self._build_url(base_url, path),
                payload=payload,
                headers=self._authorization_headers(base_url),
                timeout=self._timeout,
                allow_null=allow_null,
            )
        except HttpJsonError as exc:
            msg = f"{method} {path} failed: {exc}"
            raise TabbyAPIControlPlaneError(
                msg,
                status=exc.status,
                unreachable=exc.transport,
            ) from exc

    def _authorization_headers(self, base_url: str) -> dict[str, str]:
        secret_name = self._auth_secret_names.get(self._runtime_key(base_url))
        if secret_name is None:
            msg = "TabbyAPI endpoint has no registered auth secret; refusing an unauthenticated request."
            raise TabbyAPIControlPlaneError(msg)
        try:
            admin_key = load_tabbyapi_auth_keys(secret_name).admin_key
        except TabbyAPIAuthSecretError as exc:
            raise TabbyAPIControlPlaneError(str(exc)) from exc
        return {"Authorization": f"Bearer {admin_key}"}

    def _build_url(self, base_url: str, path: str) -> str:
        split = urlsplit(base_url)
        base_path = split.path.rstrip("/").removesuffix("/v1")
        normalized_path = path if path.startswith("/") else f"/{path}"
        return urlunsplit((split.scheme, split.netloc, f"{base_path}{normalized_path}", "", ""))

    def _runtime_key(self, base_url: str) -> str:
        return self._build_url(base_url, "/")

    def _validate_model_name(self, model: str) -> None:
        if (
            not model
            or model != model.strip()
            or not model.isprintable()
            or model in {".", ".."}
            or "/" in model
            or "\\" in model
        ):
            msg = "TabbyAPI model name must be one declared directory basename."
            raise TabbyAPIControlPlaneError(msg)

    def _model_ids(self, payload: dict[str, object]) -> list[str]:
        entries = payload.get("data")
        if not isinstance(entries, list):
            msg = "TabbyAPI /v1/models response has no data list."
            raise TabbyAPIControlPlaneError(msg)
        result: list[str] = []
        for index, entry in enumerate(cast("list[object]", entries)):
            if not isinstance(entry, dict):
                msg = f"TabbyAPI /v1/models entry {index} is not an object."
                raise TabbyAPIControlPlaneError(msg)
            model_id = self._as_str(cast("dict[object, object]", entry).get("id"))
            if model_id is None or not model_id.strip():
                msg = f"TabbyAPI /v1/models entry {index} has no non-empty string id."
                raise TabbyAPIControlPlaneError(msg)
            result.append(model_id)
        return result

    def _total_slots(self, current: dict[str, object]) -> int | None:
        parameters = current.get("parameters")
        if not isinstance(parameters, dict):
            return None
        slots = cast("dict[object, object]", parameters).get("max_batch_size")
        if slots is None:
            return None
        if not isinstance(slots, int) or isinstance(slots, bool) or slots <= 0:
            msg = "TabbyAPI /v1/model parameters.max_batch_size must be a positive integer."
            raise TabbyAPIControlPlaneError(msg)
        return slots

    def _error_message(self, payload: dict[str, object]) -> str | None:
        error = payload.get("error")
        if not isinstance(error, dict):
            return None
        message = cast("dict[object, object]", error).get("message")
        return str(message) if message is not None else "unknown stream error"

    def _as_str(self, value: object) -> str | None:
        return value if isinstance(value, str) else None


__all__ = ["TabbyAPIControlPlane", "TabbyAPIControlPlaneError"]
