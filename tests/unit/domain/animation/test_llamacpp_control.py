from __future__ import annotations

from typing import Any

from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo
from lychd.domain.animation.services.adapters.surfaces import LlamacppConnector, LlamacppStone
from lychd.extensions.builtin.animator import LlamaCppMode, LlamaCppSoulstone
from lychd.extensions.builtin.animator.llamacpp import (
    LlamaCppControlPlane,
    LlamaCppControlPlaneError,
)


def _router_animator() -> LlamacppStone:
    rune = LlamaCppSoulstone(
        name="router",
        startup_mode=LlamaCppMode.ROUTER,
        base_url="http://localhost:8080/v1",
        models_preset="/models/models.ini",
    )
    connector = LlamacppConnector(
        link=Link(up=True),
        base_url=rune.base_url,
        model_infos=(ModelInfo(id="qwen-next-80b"), ModelInfo(id="qwen-next-7b")),
        default_model_id="qwen-next-80b",
        mode="router",
        router_query_model_id="qwen-next-80b",
        metadata={},
    )
    return LlamacppStone(rune=rune, connector=connector)


def test_llamacpp_control_inspect_animator_router_lifecycle(monkeypatch: Any) -> None:
    control = LlamaCppControlPlane()
    calls: list[tuple[str, str, dict[str, str] | None]] = []

    def fake_request_json(
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
        if path == "/props":
            return {"is_sleeping": False, "total_slots": 2, "model_path": "/models/qwen-next-80b.gguf"}
        if path == "/models":
            return {
                "data": [
                    {"id": "qwen-next-80b", "status": {"value": "loaded"}},
                    {"id": "qwen-next-7b", "status": {"value": "unloaded"}},
                ]
            }
        return {}

    monkeypatch.setattr(control, "_request_json", fake_request_json)
    lifecycle = control.inspect_animator(_router_animator())

    assert lifecycle.health == "ok"
    assert lifecycle.supports_router is True
    assert lifecycle.sleeping is False
    assert lifecycle.total_slots == 2
    assert lifecycle.loaded_models == ["qwen-next-80b"]
    assert lifecycle.available_models == ["qwen-next-80b", "qwen-next-7b"]
    assert ("GET", "/props", {"model": "qwen-next-80b"}) in calls


def test_llamacpp_control_inspect_degrades_on_endpoint_error(monkeypatch: Any) -> None:
    control = LlamaCppControlPlane()

    def fake_request_json(
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
    lifecycle = control.inspect(base_url="http://localhost:8080/v1", mode="router", model_id="qwen-next-80b")

    assert lifecycle.health == "loading"
    assert "props_error" in lifecycle.raw
    assert "models_error" in lifecycle.raw


def test_llamacpp_control_load_and_unload_model(monkeypatch: Any) -> None:
    control = LlamaCppControlPlane()
    seen: list[tuple[str, str, dict[str, Any] | None]] = []

    def fake_request_json(
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

    assert control.load_model("http://localhost:8080/v1", "qwen-next-80b") is True
    assert control.unload_model("http://localhost:8080/v1", "qwen-next-80b") is True
    assert ("POST", "/models/load", {"model": "qwen-next-80b"}) in seen
    assert ("POST", "/models/unload", {"model": "qwen-next-80b"}) in seen
