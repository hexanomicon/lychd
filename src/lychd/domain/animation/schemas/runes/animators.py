from __future__ import annotations

import re
from abc import ABC
from pathlib import Path
from typing import ClassVar, Final

from pydantic import AnyHttpUrl, Field, field_validator, model_validator

from lychd.config.runes import RuneConfig
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.runes.models import LocalModelConfig, PortalModelConfig
from lychd.domain.animation.schemas.shared import ModelFormat
from lychd.system.secret_names import is_valid_podman_secret_name

_ENV_NAME: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AnimatorConfig(RuneConfig, ABC):
    """Local and remote capability endpoints.

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
    """Local container-backed capability runtimes.

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
    devices: list[str] = Field(
        default_factory=list,
        description=(
            "Host devices passed through to the container (Quadlet AddDevice= lines). "
            "Use 'nvidia.com/gpu=all' for all NVIDIA GPUs via the CDI device specifier."
        ),
    )
    security_label_disable: bool = Field(
        default=False,
        description="Emit SecurityLabelDisable=true (SELinux label off) on the Quadlet.",
    )
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
    concurrency: ConcurrencyIntent = Field(
        default_factory=ConcurrencyIntent,
        description=(
            "Lifecycle intent for this Soulstone. Dedicated (LychD-owned, mutually exclusive) "
            "stones must not be auto-started at boot; only persistent residents are wanted by "
            "default.target. Threaded into Quadlet WantedBy= at transmute time."
        ),
    )
    models: list[LocalModelConfig] = Field(
        default_factory=list,
        description=(
            "Operator-declared local models this Soulstone serves. Entries provide capability "
            "hints (families/modalities/tool support) and per-model generation overlays; they "
            "match discovered models by id (llama.cpp router: file stem)."
        ),
    )
    generation: GenerationProfile | None = Field(
        default=None,
        description=(
            "Soulstone-level generation overlay applied over runtime-derived defaults and under "
            "any per-model [[models]].generation overlay."
        ),
    )

    @field_validator("exec")
    @classmethod
    def _validate_exec_command_separators(cls, values: list[str]) -> list[str]:
        """Reject tokens that Quadlet/systemd can reinterpret as another command."""
        if any(token.strip("'\"") == ";" for value in values for token in value.split()):
            msg = "exec cannot contain a standalone systemd command separator"
            raise ValueError(msg)
        return values

    @property
    def service_name(self) -> str:
        """Systemd service stem used by conflict generation."""
        from lychd.system.unit_names import animator_service_stem

        return animator_service_stem(self.name)

    @property
    def runtime_name(self) -> str:
        """Normalized runtime id for adapter dispatch."""
        return str(getattr(self, "runtime", "generic"))

    @property
    def control_plane_secret_names(self) -> tuple[str, ...]:
        """Secrets the Vessel needs to operate this local runtime's control plane."""
        return ()

    @model_validator(mode="after")
    def _hydrate_local_defaults(self) -> SoulstoneConfig:
        for env_name, secret_name in self.secret_env_files.items():
            if _ENV_NAME.fullmatch(env_name) is None:
                msg = "secret_env_files keys must be valid environment variable names."
                raise ValueError(msg)
            if not is_valid_podman_secret_name(secret_name):
                msg = "secret_env_files values must be option-free Podman secret names."
                raise ValueError(msg)
        return self


class GenericSoulstoneConfig(SoulstoneConfig):
    """Generic container-backed runtime declarations."""

    path_fragment: ClassVar[Path] = Path("generic")


class PortalConfig(AnimatorConfig, ABC):
    """Remote capability endpoints.

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
    models: list[PortalModelConfig] = Field(
        default_factory=list,
        description=(
            "Operator-declared remote models this Portal is allowed to route to. Zero models "
            "means the Portal advertises no capabilities (reachable but unadvertised)."
        ),
    )
    generation: GenerationProfile | None = Field(
        default=None,
        description="Portal-level generation overlay applied under any per-model overlay.",
    )
    probe: bool = Field(
        default=False,
        description="Opt-in live reachability probe (no surprise egress by default).",
    )

    @field_validator("api_key_secret_name")
    @classmethod
    def _validate_api_key_secret_name(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_podman_secret_name(value):
            msg = "api_key_secret_name must be one option-free Podman secret name."
            raise ValueError(msg)
        return value


class OpenAIPortalConfig(PortalConfig):
    """OpenAI-compatible remote model declarations."""

    path_fragment: ClassVar[Path] = Path("openai")

    provider_name: str = Field(default="openai", description="OpenAI provider alias.")
    base_url: AnyHttpUrl | None = Field(
        default=AnyHttpUrl("https://api.openai.com/v1"),
        description="OpenAI API base URL.",
    )


class GoogleGeminiPortalConfig(PortalConfig):
    """Google Gemini remote model declarations."""

    path_fragment: ClassVar[Path] = Path("google-gemini")

    provider_name: str = Field(default="google-gemini", description="Google Gemini provider alias.")
    base_url: AnyHttpUrl | None = Field(
        default=AnyHttpUrl("https://generativelanguage.googleapis.com/v1beta/openai/"),
        description="Google Gemini OpenAI-compatible API base URL.",
    )
