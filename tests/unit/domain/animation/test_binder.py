from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from pydantic_ai import FunctionToolset
from pydantic_ai.models.openai import OpenAIChatModel

from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, OpenAIPortalConfig, PortalConfig
from lychd.domain.animation.services.adapters.surfaces import (
    GenericPortal,
    OpenAICompatibleConnector,
    OpenAIPortal,
    PassiveConnector,
)
from lychd.domain.animation.services.binder import AnimatorBinder, AnimatorBindingError


class CustomPortalConfig(PortalConfig):
    path_fragment: ClassVar[Path] = Path("custom")


def _openai_portal_animator(*, toolsets: tuple[FunctionToolset, ...] = ()) -> OpenAIPortal:
    rune = OpenAIPortalConfig.model_validate(
        {
            "name": "openai-main",
            "description": "OpenAI test portal",
        }
    )
    connector = OpenAICompatibleConnector(
        kind="portal:openai",
        link=Link(up=True),
        base_url=str(rune.base_url or ""),
        model_infos=(ModelInfo(id="gpt-5"),),
        default_model_id="gpt-5",
        toolsets=toolsets,
    )
    return OpenAIPortal(rune=rune, connector=connector)


def test_binder_hydrates_openai_model_from_connector() -> None:
    binder = AnimatorBinder()
    animator = _openai_portal_animator()

    model = binder.bind_model(animator)

    assert isinstance(model, OpenAIChatModel)
    assert model.model_name == "gpt-5"
    assert model.base_url.rstrip("/") == "https://api.openai.com/v1"


def test_binder_returns_empty_toolsets_for_non_tool_connector() -> None:
    rune = CustomPortalConfig.model_validate(
        {
            "name": "passive",
            "description": "Custom passive portal",
            "provider_name": "custom",
            "base_url": "https://example.test/v1",
        }
    )
    animator = GenericPortal(
        rune=rune,
        connector=PassiveConnector(kind="portal:custom", link=Link(up=True)),
    )

    binder = AnimatorBinder()
    assert binder.bind_toolsets(animator) == ()
    assert binder.bind_toolset(animator) is None


def test_binder_combines_multiple_toolsets() -> None:
    def alpha() -> str:
        return "a"

    def beta() -> str:
        return "b"

    animator = _openai_portal_animator(
        toolsets=(
            FunctionToolset(tools=[alpha]),
            FunctionToolset(tools=[beta]),
        )
    )
    binder = AnimatorBinder()

    combined = binder.bind_toolset(animator)
    toolsets = binder.bind_toolsets(animator)

    assert combined is not None
    assert combined.__class__.__name__ == "CombinedToolset"
    assert len(toolsets) == 2


def test_binder_raises_for_missing_model_capability() -> None:
    rune = CustomPortalConfig.model_validate(
        {
            "name": "passive",
            "description": "Custom passive portal",
            "provider_name": "custom",
            "base_url": "https://example.test/v1",
        }
    )
    animator = GenericPortal(
        rune=rune,
        connector=PassiveConnector(kind="portal:custom", link=Link(up=True)),
    )

    with pytest.raises(AnimatorBindingError, match="does not provide models"):
        AnimatorBinder().bind_model(animator)
