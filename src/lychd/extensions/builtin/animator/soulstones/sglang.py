from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator

from lychd.domain.animation.schemas import ModelFormat, SoulstoneConfig


class SglangSoulstone(SoulstoneConfig):
    """Builtin Soulstone profile for SGLang.

    Contract:
    - ``exec`` present => passthrough mode (command is authoritative)
    - ``exec`` absent  => managed mode (typed fields synthesize command args)
    - managed mode requires ``model_path`` or explicit ``models``
    """

    relative_path: ClassVar[Path | None] = Path("animator/soulstones/sglang")
    runtime: str = "sglang"
    image: str = "lmsysorg/sglang:latest"
    model_format: ModelFormat | None = ModelFormat.AWQ

    tensor_parallel_size: int = Field(default=1, ge=1)
    trust_remote_code: bool = False
    chat_template: str | None = None
    attention_backend: str | None = None
    quantization: str | None = None
    enable_marlin: bool = True
    extra_args: list[str] = Field(default_factory=list)

    _PASSTHROUGH_CONFLICT_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "model_path",
            "tensor_parallel_size",
            "trust_remote_code",
            "chat_template",
            "attention_backend",
            "quantization",
            "enable_marlin",
            "extra_args",
            "llm_defaults",
        }
    )

    @model_validator(mode="after")
    def _validate_runtime_contract(self) -> SglangSoulstone:
        """Reject mixed command authority and enforce managed prerequisites."""
        if self.exec:
            conflicting = sorted(field for field in self._PASSTHROUGH_CONFLICT_FIELDS if field in self.model_fields_set)
            if conflicting:
                joined = ", ".join(conflicting)
                msg = (
                    "SglangSoulstone uses exec passthrough, but managed fields were also set: "
                    f"{joined}. Remove managed fields or remove 'exec'."
                )
                raise ValueError(msg)
            return self

        if self.model_path or self.models:
            return self

        msg = "SglangSoulstone in managed mode requires 'model_path' or explicit 'models' entries."
        raise ValueError(msg)
