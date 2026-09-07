from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import AnyHttpUrl

from lychd.domain.animation.capabilities import CapabilityPhase
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import GenerationProfile, ModelInfo
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator
from lychd.extensions.builtin.animator import LlamaCppMode, LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.llamacpp import (
    LlamacppConnector,
    LlamaCppControlPlane,
    LlamaCppControlPlaneError,
    LlamaCppPresetDocument,
)
from lychd.extensions.builtin.animator.llamacpp.parser_preset import LlamaCppPresetParser
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter
from lychd.lib.http import HttpJsonError


def _router_animator() -> SoulstoneAnimator[LlamacppConnector, LlamaCppSoulstoneConfig]:
    rune = LlamaCppSoulstoneConfig(
        name="router",
        startup_mode=LlamaCppMode.ROUTER,
        base_url=AnyHttpUrl("http://localhost:8080/v1"),
        models_preset="/models/models.ini",
    )
    connector = LlamacppConnector(
        link=Link(up=True),
        base_url=str(rune.base_url),
        model_infos=(ModelInfo(id="qwen-next-80b"), ModelInfo(id="qwen-next-7b")),
        default_model_id="qwen-next-80b",
        mode="router",
        router_query_model_id="qwen-next-80b",
        generation_defaults=GenerationProfile(),
    )
    return SoulstoneAnimator(rune=rune, connector=connector)


@pytest.mark.asyncio
async def test_llamacpp_control_inspect_animator_router_lifecycle(monkeypatch: Any) -> None:
    control = LlamaCppControlPlane()
    calls: list[tuple[str, str, dict[str, str] | None]] = []

    async def fake_request_json(
        _uri: str,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert payload is None
        calls.append((method, path, query))
        if path == "/health":
            return {"status": "ok"}
        if path == "/models":
            return {
                "data": [
                    {"id": "qwen-next-80b", "status": {"value": "loaded"}},
                    {"id": "qwen-next-7b", "status": {"value": "unloaded"}},
                ]
            }
        return {}

    monkeypatch.setattr(control, "_request_json", fake_request_json)
    lifecycle = await control.inspect_animator(_router_animator())

    assert lifecycle.health == "ok"
    assert lifecycle.supports_router is True
    assert lifecycle.loaded_models == ["qwen-next-80b"]
    assert lifecycle.available_models == ["qwen-next-80b", "qwen-next-7b"]
    assert calls == [
        ("GET", "/health", {"model": "qwen-next-80b"}),
        ("GET", "/models", None),
    ]


@pytest.mark.asyncio
async def test_llamacpp_control_inspect_degrades_on_endpoint_error(monkeypatch: Any) -> None:
    control = LlamaCppControlPlane()

    async def fake_request_json(
        _uri: str,
        _method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _ = query, payload
        if path == "/health":
            return {"error": {"message": "Loading model"}}
        error_msg = "unavailable"
        raise LlamaCppControlPlaneError(error_msg)

    monkeypatch.setattr(control, "_request_json", fake_request_json)
    lifecycle = await control.inspect(base_url="http://localhost:8080/v1", mode="router", model_id="qwen-next-80b")

    assert lifecycle.health == "loading"
    assert lifecycle.available_models == []


@pytest.mark.asyncio
async def test_llamacpp_503_loading_is_warming_runtime_not_cold(monkeypatch: Any) -> None:
    import lychd.extensions.builtin.animator.llamacpp.control_plane as control_plane_mod

    async def fake_transport(
        method: str,
        url: str,
        **_kwargs: Any,
    ) -> dict[str, object]:
        _ = method
        if url.endswith("/health"):
            message = 'GET /health failed with status 503: {"error":{"message":"Loading model"}}'
            raise HttpJsonError(message, status=503)
        if url.endswith("/models"):
            return {"data": [{"id": "qwen-next-80b", "status": {"value": "unloaded"}}]}
        return {}

    monkeypatch.setattr(control_plane_mod, "request_json", fake_transport)
    control = LlamaCppControlPlane()
    animator = _router_animator()
    lifecycle = await control.inspect_animator(animator)
    adapter = LlamaCppRuntimeAdapter(control_plane=control)
    specs = adapter.build_capability_specs(animator)
    states = await adapter.probe_capability_states(animator, specs)

    assert lifecycle.health == "loading"
    assert lifecycle.error
    assert states
    assert all(state.phase is CapabilityPhase.WARMING for state in states)
    assert all(state.runtime_started for state in states)


@pytest.mark.asyncio
async def test_llamacpp_control_load_model(monkeypatch: Any) -> None:
    control = LlamaCppControlPlane()
    seen: list[tuple[str, str, dict[str, Any] | None]] = []

    async def fake_request_json(
        _uri: str,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _ = query
        seen.append((method, path, payload))
        return {"success": True}

    monkeypatch.setattr(control, "_request_json", fake_request_json)

    assert await control.load_model("http://localhost:8080/v1", "qwen-next-80b") is True
    assert seen == [("POST", "/models/load", {"model": "qwen-next-80b"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("success", ["false", "true", 1])
async def test_llamacpp_control_rejects_truthy_non_boolean_success(monkeypatch: Any, success: object) -> None:
    control = LlamaCppControlPlane()

    async def fake_request_json(
        _uri: str,
        _method: str,
        _path: str,
        **_kwargs: Any,
    ) -> dict[str, object]:
        return {"success": success}

    monkeypatch.setattr(control, "_request_json", fake_request_json)

    assert await control.load_model("http://localhost:8080/v1", "qwen-next-80b") is False


def test_llamacpp_preset_parser_keeps_numeric_values_numeric(tmp_path: Path) -> None:
    document = LlamaCppPresetDocument(
        path=tmp_path / "models.ini",
        sections={"*": {"c": "1", "temp": "1", "top-p": "0"}},
    )

    defaults = LlamaCppPresetParser().parse_preset_defaults(
        path=str(document.path),
        model_provider=None,
        model_path=None,
        preset=document,
    )

    assert defaults == {"n_ctx": 1, "temperature": 1.0, "top_p": 0.0}
    assert type(defaults["n_ctx"]) is int
    assert type(defaults["temperature"]) is float
    assert type(defaults["top_p"]) is float


def test_llamacpp_preset_parser_ignores_boolean_words_for_numeric_fields(tmp_path: Path) -> None:
    document = LlamaCppPresetDocument(
        path=tmp_path / "models.ini",
        sections={"*": {"c": "true", "temp": "false", "top-p": "off"}},
    )

    defaults = LlamaCppPresetParser().parse_preset_defaults(
        path=str(document.path),
        model_provider=None,
        model_path=None,
        preset=document,
    )

    assert defaults == {}
