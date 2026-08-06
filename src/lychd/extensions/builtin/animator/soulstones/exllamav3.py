from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import LocalModelConfig, ModelFormat, SoulstoneConfig
from lychd.extensions.builtin.animator.tabby_auth import is_valid_tabby_auth_secret_name

_MIN_VOLUME_PARTS = 2
_TABBY_MODEL_DIR = Path("/app/models")
_NVIDIA_CDI_DEVICE = re.compile(r"^nvidia\.com/gpu=(?:all|[A-Za-z0-9_.:-]+)$")
TABBYAPI_CONTRACT_REVISION = "0158fb48d76546a6475d1d63f6cd5b90932d1d11"
TABBYAPI_IMAGE = "ghcr.io/theroyallab/tabbyapi@sha256:a2a4c5b5cd9ae38ea01410c0e495a39c3784d5c213122b2d6365bfa0a88266b3"


def exllamav3_runtime_model_name(model: LocalModelConfig) -> str:
    """Return the single TabbyAPI directory name for a local model declaration."""
    return model.path.name


class ExLlamaV3SoulstoneConfig(SoulstoneConfig):
    """ExLlamaV3 runtimes served through TabbyAPI."""

    path_fragment: ClassVar[Path] = Path("exllamav3")
    sample_template: ClassVar[str | None] = """
# ~/.config/lychd/runes/animator/soulstones/exllamav3/exl3.toml

name = "exl3"
description = "Dynamic ExLlamaV3 Soulstone served by TabbyAPI."
groups = ["local-llm"]

port = 5000
model_dir = "/app/models"
auth_secret_name = "tabby_exl3_auth"

devices = ["nvidia.com/gpu=all"]
volumes = ["/data/models:/app/models:ro"]

# Create this Podman secret from a JSON document that TabbyAPI accepts as YAML:
# {"api_key":"<random-data-key>","admin_key":"<different-random-admin-key>"}

[[models]]
id = "qwen-exl3"
path = "/app/models/qwen-exl3"
format = "EXL3"

# Pinned linux/amd64 manifest from the official rolling image (2026-07-21).
# Re-pin only after the contract tests and a local NVIDIA hardware receipt pass.
[quadlet]
image = "ghcr.io/theroyallab/tabbyapi@sha256:a2a4c5b5cd9ae38ea01410c0e495a39c3784d5c213122b2d6365bfa0a88266b3"
"""

    runtime: str = "exllamav3"
    quadlet: QuadletConfig = Field(default_factory=lambda: QuadletConfig(image=TABBYAPI_IMAGE))
    port: int | None = Field(default=5000, ge=1, le=65535)
    model_format: ModelFormat | None = ModelFormat.EXL3
    model_dir: Path = _TABBY_MODEL_DIR
    devices: list[str] = Field(default_factory=lambda: ["nvidia.com/gpu=all"])
    auth_secret_name: str = Field(
        min_length=1,
        description=(
            "Podman secret containing JSON keys api_key/admin_key. It is mounted as TabbyAPI's "
            "api_tokens.yml and into the Vessel for authenticated data/control requests."
        ),
    )
    disable_auth: Literal[False] = False

    @field_validator("auth_secret_name")
    @classmethod
    def _validate_auth_secret_name(cls, value: str) -> str:
        if not is_valid_tabby_auth_secret_name(value):
            msg = "auth_secret_name must be one option-safe Podman secret name"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_runtime_contract(self) -> ExLlamaV3SoulstoneConfig:
        self._validate_envelope()
        self._validate_endpoint()
        self._validate_models()
        return self

    def _validate_envelope(self) -> None:
        if self.exec:
            msg = "ExLlamaV3SoulstoneConfig owns the pinned TabbyAPI command; exec passthrough is not supported"
            raise ValueError(msg)
        if self.quadlet.image != TABBYAPI_IMAGE:
            msg = "ExLlamaV3 image must match the digest-pinned TabbyAPI envelope"
            raise ValueError(msg)
        if self.model_path is not None:
            msg = "ExLlamaV3SoulstoneConfig uses [[models]]; model_path is not supported"
            raise ValueError(msg)
        if self.port is None:
            msg = "ExLlamaV3 port is required so TabbyAPI cannot silently choose another endpoint"
            raise ValueError(msg)
        if self.model_dir != _TABBY_MODEL_DIR:
            msg = "ExLlamaV3 model_dir is fixed at /app/models by the pinned TabbyAPI envelope"
            raise ValueError(msg)
        self._validate_container_overrides()

    def _validate_container_overrides(self) -> None:
        """Keep operator inputs inside the pinned Tabby container envelope."""
        if self.env_vars:
            msg = "ExLlamaV3 env_vars are closed; the digest-pinned TabbyAPI envelope owns its environment"
            raise ValueError(msg)
        if self.secret_env_files:
            msg = "ExLlamaV3 secret_env_files are closed; only the dedicated Tabby auth document is mounted"
            raise ValueError(msg)
        if not self.devices or any(_NVIDIA_CDI_DEVICE.fullmatch(device) is None for device in self.devices):
            msg = "ExLlamaV3 devices must be explicit NVIDIA CDI selectors"
            raise ValueError(msg)
        if len(self.volumes) != 1 or not self._mounts_model_dir(self.volumes[0]):
            msg = "ExLlamaV3 volumes may contain only the read-only /app/models mount"
            raise ValueError(msg)
        if not self._model_mount_is_read_only(self.volumes[0]):
            msg = "ExLlamaV3 model directory must be mounted read-only"
            raise ValueError(msg)

    def _validate_endpoint(self) -> None:
        if self.base_url is None:
            return
        if self.base_url.scheme != "http":
            msg = "ExLlamaV3 base_url must use plain HTTP inside the local LychD pod"
            raise ValueError(msg)
        if self.base_url.username is not None or self.base_url.password is not None:
            msg = "ExLlamaV3 base_url must not contain embedded credentials"
            raise ValueError(msg)
        if self.base_url.host not in {"localhost", "127.0.0.1", "::1"}:
            msg = "ExLlamaV3 base_url must address its local LychD pod endpoint"
            raise ValueError(msg)
        if self.base_url.port != self.port:
            msg = "ExLlamaV3 base_url port must match port"
            raise ValueError(msg)
        if (self.base_url.path or "").rstrip("/") not in {"", "/v1"}:
            msg = "ExLlamaV3 base_url path must be empty or /v1"
            raise ValueError(msg)
        if self.base_url.query is not None or self.base_url.fragment is not None:
            msg = "ExLlamaV3 base_url must not contain a query or fragment"
            raise ValueError(msg)

    def _validate_models(self) -> None:
        allowed_formats = {ModelFormat.EXL3, ModelFormat.RAW}
        if self.model_format not in allowed_formats:
            msg = "ExLlamaV3 model_format must be EXL3 or RAW (FP16/BF16)"
            raise ValueError(msg)
        if not self.models:
            msg = "ExLlamaV3 requires at least one [[models]] declaration"
            raise ValueError(msg)
        self._validate_distinct_models(allowed_formats)

    def _validate_distinct_models(self, allowed_formats: set[ModelFormat]) -> None:
        model_ids: set[str] = set()
        runtime_names: set[str] = set()
        for model in self.models:
            runtime_name = self._validate_model_declaration(model, allowed_formats)
            if model.id in model_ids:
                msg = f"Duplicate ExLlamaV3 model id '{model.id}'"
                raise ValueError(msg)
            if runtime_name in runtime_names:
                msg = f"Duplicate TabbyAPI model directory '{runtime_name}'"
                raise ValueError(msg)
            model_ids.add(model.id)
            runtime_names.add(runtime_name)

    def _validate_model_declaration(
        self,
        model: LocalModelConfig,
        allowed_formats: set[ModelFormat],
    ) -> str:
        runtime_name = exllamav3_runtime_model_name(model)
        if (
            not runtime_name.strip()
            or runtime_name != runtime_name.strip()
            or not runtime_name.isprintable()
            or runtime_name in {".", ".."}
            or Path(runtime_name).name != runtime_name
            or "\\" in runtime_name
        ):
            msg = f"ExLlamaV3 model '{model.id}' path must end in one model-directory basename"
            raise ValueError(msg)
        if model.format is not None and model.format not in allowed_formats:
            msg = f"ExLlamaV3 model '{model.id}' format must be EXL3 or RAW (FP16/BF16)"
            raise ValueError(msg)
        if not model.path.is_absolute():
            msg = f"ExLlamaV3 model '{model.id}' path must be absolute"
            raise ValueError(msg)
        if model.path.parent != self.model_dir:
            msg = f"ExLlamaV3 model '{model.id}' path must be a direct child of model_dir '{self.model_dir}'"
            raise ValueError(msg)
        return runtime_name

    @property
    def resolved_port(self) -> int:
        """Return the validator-guaranteed TabbyAPI port."""
        if self.port is None:  # pragma: no cover - post-validation invariant
            msg = "ExLlamaV3 port invariant violated"
            raise RuntimeError(msg)
        return self.port

    def _mounts_model_dir(self, volume: str) -> bool:
        parts = volume.split(":")
        return len(parts) >= _MIN_VOLUME_PARTS and parts[1] == str(self.model_dir)

    def _model_mount_is_read_only(self, volume: str) -> bool:
        parts = volume.split(":")
        return len(parts) > _MIN_VOLUME_PARTS and "ro" in parts[2].split(",")

    @property
    def control_plane_secret_names(self) -> tuple[str, ...]:
        """Mount the shared Tabby auth document into the trusted Vessel."""
        return (self.auth_secret_name,)


__all__ = [
    "TABBYAPI_CONTRACT_REVISION",
    "TABBYAPI_IMAGE",
    "ExLlamaV3SoulstoneConfig",
    "exllamav3_runtime_model_name",
]
