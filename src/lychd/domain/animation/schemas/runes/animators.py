from __future__ import annotations

import re
from abc import ABC
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Final, Never, Self

from pydantic import AnyHttpUrl, Field, field_validator, model_validator

from lychd.config import QuadletConfig
from lychd.config.runes import RuneConfig
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.runes.models import LocalModelConfig, PortalModelConfig
from lychd.system.secret_names import is_valid_podman_secret_name

_ENV_NAME: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_PORT: Final = 65535


class _FrozenStringMap(dict[str, str]):
    """JSON-serializable mapping that cannot mutate after Rune validation."""

    @staticmethod
    def _immutable() -> Never:
        msg = "Validated Rune mappings are immutable."
        raise TypeError(msg)

    def __setitem__(self, _key: str, _value: str, /) -> Never:
        self._immutable()

    def __delitem__(self, _key: str, /) -> Never:
        self._immutable()

    def clear(self) -> Never:
        self._immutable()

    def pop(self, *_args: object, **_kwargs: object) -> Never:
        self._immutable()

    def popitem(self) -> Never:
        self._immutable()

    def setdefault(self, *_args: object, **_kwargs: object) -> Never:
        self._immutable()

    def update(self, *_args: object, **_kwargs: object) -> Never:
        self._immutable()

    def __ior__(self, _value: object, /) -> Self:
        self._immutable()

    def __deepcopy__(self, _memo: dict[int, object]) -> _FrozenStringMap:
        return type(self)(self)


def _require_unique_model_ids(models: Sequence[LocalModelConfig | PortalModelConfig]) -> None:
    """Reject exact duplicate identities before a catalogue can collapse them."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for model in models:
        if model.id in seen and model.id not in duplicates:
            duplicates.append(model.id)
        seen.add(model.id)
    if duplicates:
        msg = f"models contains duplicate ids: {', '.join(repr(model_id) for model_id in duplicates)}"
        raise ValueError(msg)


class OpenAICompatibleProvider(StrEnum):
    """Provider aliases implemented by the built-in OpenAI-compatible Portal factory."""

    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai-compatible"
    OPENAI_COMPATIBLE_UNDERSCORE = "openai_compatible"
    GOOGLE_GEMINI = "google-gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    LITELLM = "litellm"


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
    base_url: AnyHttpUrl | None = Field(
        default=None,
        description="HTTP(S) endpoint root for URL-backed animator connectors.",
    )

    @field_validator("base_url")
    @classmethod
    def _validate_endpoint_root(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        """Require a composable endpoint prefix without credentials or URL suffix state."""
        if value is None:
            return None
        if value.username is not None or value.password is not None:
            msg = "base_url must not contain embedded credentials"
            raise ValueError(msg)
        if value.query is not None or value.fragment is not None:
            msg = "base_url must not contain a query or fragment"
            raise ValueError(msg)
        if value.port is not None and not 1 <= value.port <= _MAX_PORT:
            msg = "base_url port must be between 1 and 65535"
            raise ValueError(msg)
        return value


class SoulstoneConfig(AnimatorConfig, ABC):
    """Local container-backed capability runtimes.

    Soulstones may declare local models because the system typically owns the
    artifact path and runtime process for local execution. Connectors later turn
    these declarations into runtime offers and executable capability surfaces.
    Concrete runtime subclasses own the TOML files under this branch.
    """

    path_fragment: ClassVar[Path] = Path("soulstones")

    description: str = ""
    quadlet: QuadletConfig = Field(
        description="Typed deployment body compiled into the Soulstone's Quadlet container.",
    )
    runtime: str = Field(default="generic", min_length=1, description="Local runtime family id for this Soulstone.")
    model_path: str | None = Field(
        default=None,
        description=(
            "Single model artifact or model directory inside the runtime container. "
            "Use runtime-specific catalogs for multi-model runtimes."
        ),
    )
    served_model_id: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Exact provider-facing model id returned by the runtime inventory. "
            "Set this when it differs from the model_path basename or Soulstone name."
        ),
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
    groups: tuple[str, ...] = Field(default_factory=tuple, description="Coven membership labels.")
    devices: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "Host devices passed through to the container (Quadlet AddDevice= lines). "
            "Use 'nvidia.com/gpu=all' for all NVIDIA GPUs via the CDI device specifier."
        ),
    )
    security_label_disable: bool = Field(
        default=False,
        description="Emit SecurityLabelDisable=true (SELinux label off) on the Quadlet.",
    )
    volumes: tuple[str, ...] = Field(default_factory=tuple, description="Extra bind mounts for this soulstone.")
    env_vars: dict[str, str] = Field(default_factory=dict)
    secret_env_files: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map ENV var name -> Podman secret name. "
            "Transmutation hydrates entries as ENV=/run/secrets/<secret> and mounts Secret=<secret>."
        ),
    )
    exec: tuple[str, ...] = Field(default_factory=tuple, description="Explicit container command arguments.")
    concurrency: ConcurrencyIntent = Field(
        default_factory=ConcurrencyIntent,
        description=(
            "Lifecycle intent for this Soulstone. Dedicated (LychD-owned, mutually exclusive) "
            "stones must not be auto-started at boot; only persistent residents are wanted by "
            "default.target. Threaded into Quadlet WantedBy= at transmute time."
        ),
    )
    models: tuple[LocalModelConfig, ...] = Field(
        default_factory=tuple,
        description=(
            "Operator-declared local model identity allowlist. Entries provide capability hints "
            "and generation overlays; discovery may enrich or downgrade only matching ids."
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
    def _validate_exec_command_separators(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Reject tokens that Quadlet/systemd can reinterpret as another command."""
        if any(token.strip("'\"") == ";" for value in values for token in value.split()):
            msg = "exec cannot contain a standalone systemd command separator"
            raise ValueError(msg)
        return values

    @field_validator("env_vars", "secret_env_files")
    @classmethod
    def _freeze_string_maps(cls, values: dict[str, str]) -> dict[str, str]:
        return _FrozenStringMap(values)

    @property
    def control_plane_secret_names(self) -> tuple[str, ...]:
        """Secrets the Vessel needs to operate this local runtime's control plane."""
        return ()

    @model_validator(mode="after")
    def _hydrate_local_defaults(self) -> SoulstoneConfig:
        _require_unique_model_ids(self.models)
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
    models: tuple[PortalModelConfig, ...] = Field(
        default_factory=tuple,
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

    @model_validator(mode="after")
    def _validate_model_ids(self) -> PortalConfig:
        _require_unique_model_ids(self.models)
        return self


class OpenAIPortalConfig(PortalConfig):
    """OpenAI-compatible remote model declarations."""

    path_fragment: ClassVar[Path] = Path("openai")

    provider_name: str = Field(
        default=OpenAICompatibleProvider.OPENAI.value,
        description="OpenAI-compatible provider alias implemented by the exact Portal factory.",
    )
    base_url: AnyHttpUrl | None = Field(
        default=AnyHttpUrl("https://api.openai.com/v1"),
        description="OpenAI API base URL.",
    )

    @field_validator("provider_name")
    @classmethod
    def _validate_provider_name(cls, value: str) -> str:
        try:
            return OpenAICompatibleProvider(value.strip().lower()).value
        except ValueError as exc:
            message = f"Unsupported OpenAI-compatible provider alias: {value!r}."
            raise ValueError(message) from exc


class GoogleGeminiPortalConfig(PortalConfig):
    """Google Gemini remote model declarations."""

    path_fragment: ClassVar[Path] = Path("google-gemini")

    provider_name: str = Field(
        default="google-gemini",
        description="Google Gemini provider alias.",
    )
    base_url: AnyHttpUrl | None = Field(
        default=AnyHttpUrl("https://generativelanguage.googleapis.com/v1beta/openai/"),
        description="Google Gemini OpenAI-compatible API base URL.",
    )

    @field_validator("provider_name")
    @classmethod
    def _validate_provider_name(cls, value: str) -> str:
        provider = value.strip().lower()
        if provider != OpenAICompatibleProvider.GOOGLE_GEMINI.value:
            message = "GoogleGeminiPortalConfig only accepts provider_name='google-gemini'."
            raise ValueError(message)
        return provider
