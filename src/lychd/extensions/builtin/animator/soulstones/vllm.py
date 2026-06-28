from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field

from lychd.domain.animation.schemas import ModelFormat, SoulstoneConfig


class VllmSoulstoneConfig(SoulstoneConfig):
    """Builtin Soulstone profile for vLLM.

    Exec-passthrough-by-default: the operator supplies the full vLLM serve
    command as the ``exec`` list (权威). Container-level concerns (image,
    port, GPU device, IPC/security flags, volumes, env vars) remain typed
    fields on the Soulstone/Quadlet envelope; every framework flag lives in
    ``exec`` and is never re-typed here.
    """

    path_fragment: ClassVar[Path] = Path("vllm")
    sample_template: ClassVar[str | None] = """
# ~/.config/lychd/runes/animator/soulstones/vllm/qwen35.toml

name = "qwen35"
description = "Daily-driver vLLM Soulstone."
groups = ["local-llm"]
image = "vllm/vllm-openai:nightly"
port = 8000

ipc_host = true
network_host = false

devices = ["nvidia.com/gpu=all"]
# security_label_disable = false  # SELinux stays on for the container (CDI handles GPU access)

volumes = ["/data/models:/models:ro"]
env_vars = {
  "NCCL_CUMEM_ENABLE"    = "0",
  "NCCL_P2P_DISABLE"     = "1",
  "VLLM_WORKER_MULTIPROC_METHOD" = "spawn",
  "PYTORCH_CUDA_ALLOC_CONF" = "expandable_segments:True,max_split_size_mb:512",
}

exec = [
  "serve", "/models/cyankiwi__Qwen3.5-27B-AWQ-4bit",
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
"""
    runtime: str = "vllm"
    image: str = "vllm/vllm-openai:latest"
    model_format: ModelFormat | None = ModelFormat.AWQ

    ipc_host: bool = True
    network_host: bool = Field(default=False, description="Emit --network=host on the Quadlet.")
