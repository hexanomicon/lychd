from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import ClassVar

from pydantic import AnyHttpUrl, Field, model_validator

from lychd.config.runes import RuneConfig
from lychd.domain.animation.schemas.shared import ModelFormat


class AnimatorConfig(RuneConfig, ABC):
    """Abstract branch config for animator-owned Rune schemas.

    ``AnimatorConfig`` is intentionally generic. It should only contain defaults
    that make sense across all animator kinds (local Soulstones and remote
    Portals) and across connector capability sets.

    It must not carry resolved provider/tool identities or modality-specific
    configuration that only applies to LLM connectors. As a branch rune class,
    it contributes inherited fields but owns no TOML files.
    """

    path_fragment: ClassVar[Path] = Path("animator")

    name: str
    description: str = ""
    base_url: AnyHttpUrl | None = Field(
        default=None,
        description="HTTP(S) endpoint root for URL-backed animator connectors.",
    )


class SoulstoneConfig(AnimatorConfig, ABC):
    """Abstract branch config for local/container-backed animator schemas.

    Soulstones may declare local models because the system typically owns the
    artifact path and runtime process for local execution. Connectors later turn
    these declarations into runtime offers and executable capability surfaces.
    Concrete runtime subclasses own the TOML files under this branch.
    """

    path_fragment: ClassVar[Path] = Path("soulstones")

    image: str = Field(..., min_length=1, description="OCI image used for this container.")
    runtime: str = Field(default="generic", min_length=1, description="Local runtime family id for this Soulstone.")
    model_path: str | None = Field(
        default=None,
        description=(
            "Single model artifact or model directory inside the runtime container. "
            "Use runtime-specific catalogs for multi-model runtimes."
        ),
    )
    model_format: ModelFormat | None = Field(
        default=None,
        description="Optional model weight format for connector metadata and runtime planning.",
    )
    base_url: AnyHttpUrl | None = Field(
        default=None,
        description="Local API base URL. Omit to let the loader derive one.",
    )
    port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
        description="Host port for the local API. Omit to let the loader allocate one.",
    )
    groups: list[str] = Field(default_factory=list, description="Coven membership labels.")
    volumes: list[str] = Field(default_factory=list, description="Extra bind mounts for this soulstone.")
    env_vars: dict[str, str] = Field(default_factory=dict)
    secret_env_files: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map ENV var name -> Podman secret name. "
            "Transmutation hydrates entries as ENV=/run/secrets/<secret> and mounts Secret=<secret>."
        ),
    )
    exec: list[str] = Field(default_factory=list, description="Explicit container command arguments.")

    @property
    def service_name(self) -> str:
        """Systemd service stem used by conflict generation."""
        return f"lychd-{self.name}"

    @property
    def runtime_name(self) -> str:
        """Normalized runtime id for adapter dispatch."""
        return str(getattr(self, "runtime", "generic"))

    @model_validator(mode="after")
    def _hydrate_local_defaults(self) -> SoulstoneConfig:
        for env_name, secret_name in self.secret_env_files.items():
            if not env_name.strip():
                msg = "secret_env_files keys must be non-empty environment variable names."
                raise ValueError(msg)
            if not secret_name.strip():
                msg = "secret_env_files values must be non-empty Podman secret names."
                raise ValueError(msg)
        return self


class GenericSoulstoneConfig(SoulstoneConfig):
    """Leaf Soulstone Rune for simple container-backed generic runtimes."""

    path_fragment: ClassVar[Path] = Path("generic")


class PortalConfig(AnimatorConfig, ABC):
    """Abstract branch config for remote/API-backed animator schemas.

    Portals declare endpoint identity and authentication references. Provider
    subclasses own the concrete TOML anchors because ``portals/`` is only the
    broad remote-service family, not a loadable provider by itself.
    """

    path_fragment: ClassVar[Path] = Path("portals")

    provider_name: str = Field(..., description="High-level provider type (openai, anthropic, etc).")
    base_url: AnyHttpUrl | None = Field(
        default=None,
        description="Remote API base URL, when the Portal Rune declares one directly.",
    )
    api_key_secret_name: str | None = Field(
        default=None,
        description="Podman secret name for provider API key injection inside the Vessel runtime.",
    )


class OpenAIPortalConfig(PortalConfig):
    """Leaf Portal Rune for OpenAI's native API."""

    path_fragment: ClassVar[Path] = Path("openai")

    provider_name: str = Field(default="openai", description="OpenAI provider alias.")
    base_url: AnyHttpUrl | None = Field(
        default=AnyHttpUrl("https://api.openai.com/v1"),
        description="OpenAI API base URL.",
    )


class GoogleGeminiPortalConfig(PortalConfig):
    """Leaf Portal Rune for Google's OpenAI-compatible Gemini endpoint."""

    path_fragment: ClassVar[Path] = Path("google-gemini")

    provider_name: str = Field(default="google-gemini", description="Google Gemini provider alias.")
    base_url: AnyHttpUrl | None = Field(
        default=AnyHttpUrl("https://generativelanguage.googleapis.com/v1beta/openai/"),
        description="Google Gemini OpenAI-compatible API base URL.",
    )
