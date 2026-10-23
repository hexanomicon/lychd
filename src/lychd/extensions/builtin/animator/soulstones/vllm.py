from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import SoulstoneConfig


class VllmSoulstoneConfig(SoulstoneConfig):
    """vLLM runtime declarations and launch recipes.

    Exec-passthrough-by-default: the operator supplies the arguments appended
    to the selected image's entrypoint as the ``exec`` list. Container concerns (image,
    port, GPU device, IPC/security flags, volumes, env vars) remain typed
    fields on the Soulstone/Quadlet envelope; every framework flag lives in
    ``exec`` and is never re-typed here.
    """

    path_fragment: ClassVar[Path] = Path("vllm")
    sample_template: ClassVar[str | None] = """
# ~/.config/lychd/runes/animator/soulstones/vllm/qwen35.toml

name = "qwen35"
description = "Editable vLLM example; qualify the exact image and model before use."
groups = ["local-llm"]
port = 8000
served_model_id = "Qwen3.5-27B"

devices = ["nvidia.com/gpu=all"]
# security_label_disable = false  # SELinux stays on for the container (CDI handles GPU access)

volumes = ["/data/models:/models:ro"]

# This example expects the image entrypoint ["vllm", "serve"].
exec = [
  "/models/cyankiwi__Qwen3.5-27B-AWQ-4bit",
  "--served-model-name", "Qwen3.5-27B",
  "--host", "0.0.0.0", "--port", "8000",
  "--tensor-parallel-size", "2",
  "--disable-custom-all-reduce",
  "--gpu-memory-utilization", "0.95",
  "--max-model-len", "163840",
  "--max-num-seqs", "1",
  "--max-num-batched-tokens", "4096",
  "--enable-chunked-prefill",
  "--enable-prefix-caching",
  "--reasoning-parser", "qwen3",
  "--enable-auto-tool-choice",
  "--tool-call-parser", "qwen3_coder",
  "--generation-config", "vllm",
  "--speculative-config", '{"method":"dflash","model":"/models/z-lab__Qwen3.5-27B-DFlash","num_speculative_tokens":4}',
]

[env_vars]
NCCL_CUMEM_ENABLE = "0"
NCCL_P2P_DISABLE = "1"
VLLM_WORKER_MULTIPROC_METHOD = "spawn"
PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True,max_split_size_mb:512"

[quadlet]
image = "vllm/vllm-openai:nightly"
"""
    runtime: Literal["vllm"] = "vllm"  # pyright: ignore[reportIncompatibleVariableOverride]
    quadlet: QuadletConfig = Field(default_factory=lambda: QuadletConfig(image="vllm/vllm-openai:latest"))
