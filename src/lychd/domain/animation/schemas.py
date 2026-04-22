from __future__ import annotations

import os
from enum import StrEnum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class ModelFormat(StrEnum):
    """Identifies the physical layout of the model weights."""

    GGUF = "GGUF"
    AWQ = "AWQ"
    GPTQ = "GPTQ"
    EXL2 = "EXL2"
    RAW = "RAW"
    NIM = "NIM"
    NVFP4 = "NVFP4"
    OTHER = "OTHER"


class Capability(StrEnum):
    """The Ritual Interface (Calling Convention)."""

    OPENAI_CHAT_COMPLETIONS = "OpenAIChatCompletions"
    OPENAI_EMBEDDINGS = "OpenAIEmbeddings"
    TTS = "TTS"
    STT = "STT"
    OCR = "OCR"


class Tag(StrEnum):
    """Architectural Abilities and Features."""

    VISION = "vision"
    TOOLS = "tools"
    REASONING = "reasoning"
    LONG_CONTEXT = "long-context"
    OFFLINE = "offline"


class GenerationParams(BaseModel):
    """The Intelligence Profile."""

    max_context: int = Field(4096, description="Maximum context window size.")
    max_tokens: int = Field(4096, description="The limit of the entity's breath.")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    top_k: int = Field(40, ge=0)
    repetition_penalty: float = Field(1.1, ge=0.0)


class Animator(GenerationParams):
    """The Base Animator Interface."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- Identity ---
    name: str
    description: str | None = None
    capability: Capability = Field(default=Capability.OPENAI_CHAT_COMPLETIONS)
    tags: list[Tag] = Field(default_factory=list)

    # --- Connectivity ---
    model_name: str = Field(..., description="The API model ID.")
    base_uri: str = Field(..., description="The API base URL.")

    # --- Security ---
    # The actual secret (Result)
    api_key: SecretStr | None = Field(default=None)

    # The instruction (Source)
    api_key_env: str | None = Field(default=None, description="Env var to load key from.")

    @model_validator(mode="before")
    @classmethod
    def migrate_and_resolve(cls, data: Any) -> Any:
        """Universal Security & Migration Logic.

        1. Migrates legacy 'capabilities' (list) to 'capability' (singular) and 'tags'.
        2. Resolves 'api_key_env' into 'api_key'.
        """
        if isinstance(data, dict):
            d = cast("dict[str, Any]", data)

            # 1. Migration Logic
            if "capabilities" in d and "capability" not in d:
                caps = d.pop("capabilities")
                if isinstance(caps, list) and caps:
                    # The first one is the interface
                    d["capability"] = caps[0]
                    # The rest are treated as potential tags (if they match the Tag enum)
                    # For now just log or skip, but let's try to match them.
                    # Actually, better to just let the user fix their TOML,
                    # but we can try to be helpful.

            # 2. Security Logic
            if (env_name := d.get("api_key_env")) and (secret := os.environ.get(str(env_name))):
                d["api_key"] = secret

            # 3. URI Alignment
            if "uri" in d and "base_uri" not in d:
                d["base_uri"] = d.pop("uri")

            return d
        return data


class Soulstone(Animator):
    """Local Body: A containerized engine."""

    # --- Identity Overrides ---
    model_name: str = Field(default="", description="The API model ID. Defaults to name.")

    # --- Grouping ---
    groups: list[str] = Field(
        default_factory=list,
        description="The mutually inclusive groups the model can be a part of",
    )
    # --- Infrastructure ---
    image: str
    port: int = Field(8780, ge=1, le=65535)
    port_expose: bool = True
    forward_port: bool = True

    # --- The Weights ---
    model_format: ModelFormat | None = None
    model_path: str | None = Field(None, description="Host path to model weights.")

    # --- Runtime ---
    env_vars: dict[str, str] = Field(default_factory=dict)
    exec: list[str] = Field(default_factory=list)
    volumes: list[str] = Field(default_factory=list)

    @property
    def service_name(self) -> str:
        return f"lychd-soulstone-{self.name}"

    @model_validator(mode="before")
    @classmethod
    def inject_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = cast("dict[str, Any]", data)

            # 1. Port & URI logic
            # ALWAYS OVERRIDE THE URI. we are always localhost in managed soulstones
            # Must be different port due to Linux dropping the port for 60 seconds
            port = d.get("port", 8000)
            d["port"] = port
            d["base_uri"] = f"http://localhost:{port}/v1"

            # 2. Identity fallback
            # If model_name is missing or empty, use the soulstone name
            if not d.get("model_name") and d.get("name"):
                d["model_name"] = d["name"]

            return d
        return data


class Portal(Animator):
    """Cloud Body: An external bridge."""

    provider: str | None = None
