from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator

from lychd.domain.animation.schemas import ModelFormat, SoulstoneConfig


class VllmSoulstone(SoulstoneConfig):
    """Builtin Soulstone profile for vLLM.

    Contract:
    - ``exec`` present => passthrough mode (command is authoritative)
    - ``exec`` absent  => managed mode (typed fields synthesize command args)
    - managed mode requires ``model_path`` or declared ``models``
    - container-level toggles (for example ``ipc_host``) still apply in both modes
    """

    relative_path: ClassVar[Path | None] = Path("animator/soulstones/vllm")
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
            "llm_defaults",
        }
    )

    @model_validator(mode="after")
    def _validate_runtime_contract(self) -> VllmSoulstone:
        """Reject mixed command authority and enforce managed prerequisites."""
        if self.exec:
            conflicting = sorted(field for field in self._PASSTHROUGH_CONFLICT_FIELDS if field in self.model_fields_set)
            if conflicting:
                joined = ", ".join(conflicting)
                msg = (
                    "VllmSoulstone uses exec passthrough, but managed fields were also set: "
                    f"{joined}. Remove managed fields or remove 'exec'."
                )
                raise ValueError(msg)
            return self

        if self.model_path or self.models:
            return self

        msg = "VllmSoulstone in managed mode requires 'model_path' or explicit 'models' entries."
        raise ValueError(msg)
