from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import respx
from pydantic import AnyHttpUrl
from respx.models import Call

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
                    {"id": "qwen-next-7b", "status": {"value": "loading"}},
                ]
            }
        return {}

    monkeypatch.setattr(control, "_request_json", fake_request_json)
    lifecycle = await control.inspect_animator(_router_animator())

    assert lifecycle.health == "ok"
    assert lifecycle.supports_router is True
    assert lifecycle.loaded_models == ["qwen-next-80b"]
    assert lifecycle.loading_models == ["qwen-next-7b"]
    assert lifecycle.available_models == ["qwen-next-80b", "qwen-next-7b"]
    assert calls == [
        ("GET", "/health", {"model": "qwen-next-80b", "autoload": "false"}),
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
async def test_router_loading_health_does_not_override_exact_inventory(monkeypatch: Any) -> None:
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
    phases = {state.capability_key: state.phase for state in states}
    assert phases == {
        "router:chat:qwen-next-80b": CapabilityPhase.ACTIVATABLE,
        "router:chat:qwen-next-7b": CapabilityPhase.ERROR,
    }


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
@pytest.mark.parametrize(
    "invalid_entry",
    [
        None,
        {"id": ""},
        {"id": "qwen-next-80b", "status": {"value": "unloaded"}},
        {"id": "qwen-next-7b"},
    ],
    ids=["malformed-entry", "missing-identity", "duplicate-identity", "missing-status"],
)
async def test_router_inventory_cannot_publish_partial_warmth(
    respx_mock: respx.MockRouter,
    invalid_entry: object,
) -> None:
    respx_mock.get("http://localhost:8080/health").respond(200, json={"status": "ok"})
    respx_mock.get("http://localhost:8080/models").respond(
        200,
        json={"data": [{"id": "qwen-next-80b", "status": {"value": "loaded"}}, invalid_entry]},
    )
    animator = _router_animator()
    adapter = LlamaCppRuntimeAdapter()
    states = await adapter.probe_capability_states(animator, adapter.build_capability_specs(animator))

    assert states
    assert all(state.phase is CapabilityPhase.ERROR for state in states)
    assert all(state.reason and "inventory invalid" in state.reason for state in states)


@pytest.mark.asyncio
@pytest.mark.parametrize("health_status", ["ok", "loading"])
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ({"value": "loaded"}, CapabilityPhase.WARM),
        ({"value": "loading"}, CapabilityPhase.WARMING),
        ({"value": "unloaded"}, CapabilityPhase.ACTIVATABLE),
        ({"value": "unloaded", "failed": True}, CapabilityPhase.UNKNOWN),
        ({"value": "sleeping"}, CapabilityPhase.UNKNOWN),
        ({"value": "downloading"}, CapabilityPhase.UNKNOWN),
        ({"value": "unsupported"}, CapabilityPhase.UNKNOWN),
    ],
)
async def test_router_inventory_admits_only_proved_model_states(
    respx_mock: respx.MockRouter,
    status: dict[str, object],
    expected: CapabilityPhase,
    health_status: str,
) -> None:
    health = respx_mock.get("http://localhost:8080/health").respond(
        200,
        json={"status": "ok"} if health_status == "ok" else {"error": {"message": "Loading model"}},
    )
    respx_mock.get("http://localhost:8080/models").respond(
        200,
        json={
            "data": [
                {"id": "qwen-next-80b", "status": status},
                {"id": "qwen-next-7b", "status": {"value": "loaded"}},
            ]
        },
    )
    load = respx_mock.post("http://localhost:8080/models/load").respond(200, json={"success": True})
    animator = _router_animator()
    adapter = LlamaCppRuntimeAdapter()
    specs = adapter.build_capability_specs(animator)
    states = {state.capability_key: state for state in await adapter.probe_capability_states(animator, specs)}
    target = next(spec for spec in specs if spec.model_id == "qwen-next-80b")

    loaded_phase = CapabilityPhase.WARM if health_status == "ok" else CapabilityPhase.UNKNOWN
    observed_target = loaded_phase if expected is CapabilityPhase.WARM else expected
    assert states[target.key].phase is observed_target
    assert states["router:chat:qwen-next-7b"].phase is loaded_phase
    result = await adapter.activate_capability(animator, target)
    assert result.accepted is (expected is not CapabilityPhase.UNKNOWN)
    assert load.called is (expected is CapabilityPhase.ACTIVATABLE)
    assert all(call.request.url.params["autoload"] == "false" for call in cast("list[Call]", health.calls))


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
