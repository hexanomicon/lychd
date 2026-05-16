from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lychd.config.runes import RuneConfig
from lychd.domain.animation.schemas.runes.models import (
    LLMGenerationDefaults,
    LocalLLMModelConfig,
    ModelCapabilityHints,
)
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

    name: str = Field(default="animator")
    description: str = Field(default="Global animation defaults.")

    orchestration_labels: list[str] = Field(
        default_factory=list,
        description="Advisory routing labels (privacy, locality, cost, latency, etc.).",
    )
    dedicated: bool = Field(
        default=True,
        description="Whether LychD owns this animator lifecycle and may start or stop it during transitions.",
    )
    persistent_resident: bool = Field(
        default=False,
        description="Whether this animator should stay out of the default eviction set when possible.",
    )


class ExternalToolConfig(BaseModel):
    """External/deferred tool definition exposed by a connector-backed animator.

    This is a rune-side declaration only. Connectors translate these entries
    into Pydantic AI ``ToolDefinition`` objects and usually wrap them in an
    ``ExternalToolset`` so deferred/external tool execution is reused directly
    from Pydantic AI.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    parameters_json_schema: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="JSON schema for tool arguments (object schema).",
    )
    description: str | None = None
    strict: bool | None = None
    sequential: bool = False


class SoulstoneConfig(AnimatorConfig, ABC):
    """Abstract branch config for local/container-backed animator schemas.

    Soulstones may declare local models because the system typically owns the
    artifact path and runtime process for local execution. Connectors later turn
    these declarations into runtime offers and executable capability surfaces.
    Concrete runtime subclasses own the TOML files under this branch.
    """

    path_fragment: ClassVar[Path] = Path("soulstones")

    name: str = Field(default="soulstone", min_length=1)
    image: str = Field(..., min_length=1, description="OCI image used for this container.")
    runtime: str = Field(default="generic", min_length=1, description="Local runtime family id for this Soulstone.")
    base_url: str = Field(
        default="",
        description="Explicit local API base URL override. Defaults to http://localhost:{port}/v1.",
    )
    model_path: str | None = Field(
        default=None, description="Primary local model artifact path when using single-model runtimes."
    )
    model_format: ModelFormat | None = Field(
        default=None, description="Primary local model format hint for runtime dispatch/validation."
    )
    port: int = Field(default=8000, ge=1, le=65535)
    groups: list[str] = Field(default_factory=list, description="Coven membership labels.")
    evict_cost: int = Field(default=1, ge=0, description="Relative cost of evicting this soulstone from residency.")
    matrix_sets: list[str] = Field(
        default_factory=list,
        description="Solver-style coexistence set labels used by later transition planning.",
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
    llm_defaults: LLMGenerationDefaults | None = Field(
        default=None,
        description="Optional LLM generation defaults overlay for this Soulstone.",
    )
    capabilities: ModelCapabilityHints | None = Field(
        default=None,
        description="Optional Soulstone-wide capability hints for synthesized model summaries.",
    )
    models: dict[str, LocalLLMModelConfig] = Field(
        default_factory=dict,
        description="Local model declarations owned by this Soulstone.",
    )

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
        if not self.base_url:
            self.base_url = f"http://localhost:{self.port}/v1"
        for env_name, secret_name in self.secret_env_files.items():
            if not env_name.strip():
                msg = "secret_env_files keys must be non-empty environment variable names."
                raise ValueError(msg)
            if not secret_name.strip():
                msg = "secret_env_files values must be non-empty Podman secret names."
                raise ValueError(msg)
        return self


class GenericSoulstoneConfig(SoulstoneConfig):
    """Concrete config for custom local runtimes without a dedicated adapter schema."""

    path_fragment: ClassVar[Path] = Path("generic")
    runtime: str = "generic"


class PortalConfig(AnimatorConfig):
    """Rune config for a remote/API-backed animator (Portal).

    Portals usually do not own local model artifacts. Model availability is
    typically discovered through the connector at runtime. This config focuses on
    endpoint identity and authentication hints.
    """

    path_fragment: ClassVar[Path] = Path("portals")

    name: str = Field(default="portal", min_length=1)
    provider_type: str = Field(default="openai", description="High-level provider type (openai, anthropic, etc).")
    base_url: str = Field(default="", description="Remote API base URL (for example https://api.openai.com/v1).")
    default_model_id: str | None = Field(
        default=None, description="Preferred/default remote model id for this portal connector."
    )
    llm_defaults: LLMGenerationDefaults | None = Field(
        default=None,
        description="Optional LLM generation defaults overlay for this Portal.",
    )
    capabilities: ModelCapabilityHints | None = Field(
        default=None,
        description="Optional Portal-wide capability hints for synthesized model summaries.",
    )
    external_tools: list[ExternalToolConfig] = Field(
        default_factory=list,
        description=(
            "Optional external/deferred tools exposed by this portal. Connectors "
            "map these into Pydantic AI ExternalToolset definitions."
        ),
    )
    api_key_secret: str | None = Field(
        default=None,
        description="Podman secret name used for provider API key injection inside the Vessel runtime.",
    )
