from __future__ import annotations

from typing import cast

import pytest
from pydantic import AnyHttpUrl

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.services.loader import AnimatorConfigError, AnimatorLoader


def _hydrate(*, base_url: str, port: int | None = None) -> GenericSoulstoneConfig:
    stone = GenericSoulstoneConfig(
        name="local-runtime",
        quadlet=QuadletConfig(image="example/runtime:latest"),
        runtime="openai_compatible",
        model_path="/models/model.gguf",
        base_url=AnyHttpUrl(base_url),
        port=port,
    )
    soulstones, _ = AnimatorLoader(
        reserved_ports={},
        core_secret_names=("core_app", "core_db"),
    ).hydrate_all([stone])
    return cast("GenericSoulstoneConfig", soulstones[0])


@pytest.mark.parametrize(
    "base_url",
    [
        "https://models.example.test:8443/v1",
        "http://192.0.2.10:8000/v1",
        "http://localhost.localdomain:8000/v1",
    ],
)
def test_soulstone_rejects_non_loopback_endpoint(base_url: str) -> None:
    with pytest.raises(AnimatorConfigError, match="approved loopback host"):
        _hydrate(base_url=base_url)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://user:password@localhost:8000/v1",
        "http://localhost:8000/v1?token=value",
        "http://localhost:8000/v1#fragment",
    ],
)
def test_soulstone_rejects_authority_bearing_or_ambiguous_url_components(base_url: str) -> None:
    with pytest.raises(AnimatorConfigError, match="userinfo, query, or fragment"):
        _hydrate(base_url=base_url)


def test_soulstone_explicit_url_requires_and_agrees_with_runtime_port() -> None:
    with pytest.raises(AnimatorConfigError, match="explicit port"):
        _hydrate(base_url="http://localhost/v1")
    with pytest.raises(AnimatorConfigError, match="declares port 8001 but base_url uses port 8000"):
        _hydrate(base_url="http://localhost:8000/v1", port=8001)


@pytest.mark.parametrize("base_url", ["http://127.0.0.2:8000/v1", "http://[::1]:8000/v1"])
def test_soulstone_accepts_explicit_loopback_endpoint(base_url: str) -> None:
    hydrated = _hydrate(base_url=base_url)

    assert hydrated.port == 8000
    assert str(hydrated.base_url).rstrip("/") == base_url
