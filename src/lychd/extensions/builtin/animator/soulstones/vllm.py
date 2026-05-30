from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator

from lychd.domain.animation.schemas import ModelFormat, SoulstoneConfig


class VllmSoulstoneConfig(SoulstoneConfig):
    """Builtin Soulstone profile for vLLM.

    Contract:
    - ``exec`` present => passthrough mode (command is authoritative)
    - ``exec`` absent  => managed mode (typed fields synthesize command args)
    - managed mode requires ``model_path``
    - container-level toggles (for example ``ipc_host``) still apply in both modes
    """

    path_fragment: ClassVar[Path] = Path("vllm")
    sample_template: ClassVar[str | None] = """
# ~/.config/lychd/runes/animator/soulstones/vllm/glm.toml

name = "glm-vllm"
description = "Static vLLM Soulstone for one OpenAI-compatible local model."
groups = ["local-llm"]
port = 8010

model_path = "/models/GLM-4.7-Flash-AWQ-4bit"
tensor_parallel_size = 1
gpu_memory_utilization = 0.90
max_model_len = 32768
max_num_seqs = 2

language_model_only = true
tool_call_parser = "glm47"
reasoning_parser = "glm45"
enable_auto_tool_choice = true
trust_remote_code = true
ipc_host = true
"""
    runtime: str = "vllm"
    image: str = "vllm/vllm-openai:latest"
    model_format: ModelFormat | None = ModelFormat.AWQ

    tensor_parallel_size: int = Field(default=1, ge=1)
    gpu_memory_utilization: float = Field(default=0.9, gt=0.0, le=1.0)
    language_model_only: bool = False
    max_model_len: int | None = Field(default=None, ge=1)
    max_num_seqs: int | None = Field(default=None, ge=1)
    quantization: str | None = None
    tool_call_parser: str | None = None
    reasoning_parser: str | None = None
    enable_auto_tool_choice: bool = False
    trust_remote_code: bool = False
    ipc_host: bool = True
    network_host: bool = False
    extra_args: list[str] = Field(default_factory=list)

    _PASSTHROUGH_CONFLICT_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "model_path",
            "tensor_parallel_size",
            "gpu_memory_utilization",
            "language_model_only",
            "max_model_len",
            "max_num_seqs",
            "quantization",
            "tool_call_parser",
            "reasoning_parser",
            "enable_auto_tool_choice",
            "trust_remote_code",
            "extra_args",
        }
    )

    @model_validator(mode="after")
    def _validate_runtime_contract(self) -> VllmSoulstoneConfig:
        """Reject mixed command authority and enforce managed prerequisites."""
        if self.exec:
            conflicting = sorted(field for field in self._PASSTHROUGH_CONFLICT_FIELDS if field in self.model_fields_set)
            if conflicting:
                joined = ", ".join(conflicting)
                msg = (
                    "VllmSoulstoneConfig uses exec passthrough, but managed fields were also set: "
                    f"{joined}. Remove managed fields or remove 'exec'."
                )
                raise ValueError(msg)
            return self

        if self.model_path:
            return self

        msg = "VllmSoulstoneConfig in managed mode requires 'model_path'."
        raise ValueError(msg)
