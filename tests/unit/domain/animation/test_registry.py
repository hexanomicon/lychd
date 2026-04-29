from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai import Agent, DeferredToolRequests
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import ExternalToolset

from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, PortalConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, OpenAIPortal
from lychd.domain.animation.services.loader import AnimatorLoader
from lychd.domain.animation.services.registry import AnimatorRegistry, RuntimeAnimator
from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane, LlamaCppLifecycle


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


def test_registry_binds_model_and_external_toolset_for_portal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runes_dir = tmp_path / "runes"
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    (secrets_dir / "portal_openai_main").write_text("sk-proj-test\n", encoding="utf-8")
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(secrets_dir))
    _write(
        runes_dir / "animator" / "portals" / "openai.toml",
        """
        name = "openai-main"
        base_url = "https://api.openai.com/v1"
        provider_type = "openai"
        default_model_id = "gpt-5"
        api_key_secret = "portal_openai_main"
        external_tools = [
          { name = "frontend_ping", description = "Frontend deferred ping", parameters_json_schema = { type = "object", properties = {} } }
        ]
        """,
    )

    registry = AnimatorRegistry(loader=AnimatorLoader(runes_dir=runes_dir, reserved_ports={}))

    model = registry.bind_model("openai-main")
    toolset = registry.bind_toolset("openai-main")
    toolsets = registry.bind_toolsets("openai-main")

    assert isinstance(model, OpenAIChatModel)
    assert model.model_name == "gpt-5"
    assert model.base_url.rstrip("/") == "https://api.openai.com/v1"
    assert isinstance(toolset, ExternalToolset)
    assert len(toolsets) == 1
    assert isinstance(toolsets[0], ExternalToolset)
    assert registry.prepare("openai-main") is None

    agent = Agent(
        TestModel(call_tools=["frontend_ping"]),
        toolsets=[toolset],
        output_type=[str, DeferredToolRequests],
    )
    result = agent.run_sync("Ping the frontend")

    assert isinstance(result.output, DeferredToolRequests)
    assert [call.tool_name for call in result.output.calls] == ["frontend_ping"]
    assert result.output.approvals == []


def test_registry_prepare_returns_runtime_plan_for_soulstone(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        port = 18080
        """,
    )

    registry = AnimatorRegistry(loader=AnimatorLoader(runes_dir=runes_dir, reserved_ports={}))
    plan = registry.prepare("qwen-local")

    assert plan is not None
    assert plan.exec_args[:2] == ["-m", "/models/qwen.gguf"]


def test_registry_unknown_animator_returns_empty_bindings(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    (runes_dir / "animator" / "soulstones").mkdir(parents=True, exist_ok=True)
    (runes_dir / "animator" / "portals").mkdir(parents=True, exist_ok=True)
    registry = AnimatorRegistry(loader=AnimatorLoader(runes_dir=runes_dir, reserved_ports={}))

    assert registry.get_runtime("missing") is None
    assert registry.bind_model("missing") is None
    assert registry.bind_toolset("missing") is None
    assert registry.bind_toolsets("missing") == ()
    assert registry.prepare("missing") is None
    assert registry.is_ready("missing") is False
    assert registry.list_models("missing") == ()


def test_registry_inspect_lifecycle_delegates_to_llamacpp_control(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )

    class StubControl(LlamaCppControlPlane):
        def __init__(self) -> None:
            super().__init__()
            self.seen_animator_id: str | None = None

        def inspect_animator(self, animator: RuntimeAnimator) -> LlamaCppLifecycle:
            self.seen_animator_id = animator.id
            return LlamaCppLifecycle(
                base_url=animator.base_url,
                mode="single",
                health="ok",
            )

    control = StubControl()
    registry = AnimatorRegistry(
        loader=AnimatorLoader(runes_dir=runes_dir, reserved_ports={}),
        llamacpp_control=control,
    )

    lifecycle = registry.inspect_lifecycle("qwen-local")

    assert lifecycle is not None
    assert lifecycle.health == "ok"
    assert control.seen_animator_id == "qwen-local"


def test_runtime_adapter_registry_supports_custom_portal_factories() -> None:
    portal = PortalConfig(
        name="custom-portal",
        base_url="https://custom.portal/v1",
        provider_type="my-openai-gateway",
        default_model_id="custom-gpt",
    )

    def custom_factory(config: PortalConfig) -> OpenAIPortal | None:
        if config.provider_type != "my-openai-gateway":
            return None
        connector = OpenAICompatibleConnector(
            kind="portal:my-openai-gateway",
            link=Link(up=True, activatable=False),
            base_url=config.base_url,
            model_infos=(ModelInfo(id="custom-gpt"),),
            default_model_id="custom-gpt",
        )
        return OpenAIPortal(rune=config, connector=connector)

    adapters = RuntimeAdapterRegistry(portal_factories=[custom_factory])
    runtime = adapters.build_runtime(portal)

    assert runtime is not None
    assert isinstance(runtime, OpenAIPortal)
    assert runtime.connector.kind == "portal:my-openai-gateway"


def test_registry_logs_unresolved_runtime_factory(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )

    def unresolved(_rune: object) -> None:
        return None

    caplog.set_level("WARNING")

    registry = AnimatorRegistry(
        loader=AnimatorLoader(runes_dir=runes_dir, reserved_ports={}),
        runtime_factories=[unresolved],
    )
    registry.load()

    assert registry.get_runtime("qwen-local") is None
    assert any("runtime_unresolved" in record.getMessage() for record in caplog.records)
