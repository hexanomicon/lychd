"""Builtin animator soulstone schemas."""

from lychd.extensions.builtin.animator.soulstones.exllamav3 import (
    TABBYAPI_CONTRACT_REVISION,
    TABBYAPI_IMAGE,
    ExLlamaV3SoulstoneConfig,
    exllamav3_runtime_model_name,
)
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppMode, LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.soulstones.sglang import SglangSoulstoneConfig
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig

__all__ = [
    "TABBYAPI_CONTRACT_REVISION",
    "TABBYAPI_IMAGE",
    "ExLlamaV3SoulstoneConfig",
    "LlamaCppMode",
    "LlamaCppSoulstoneConfig",
    "SglangSoulstoneConfig",
    "VllmSoulstoneConfig",
    "exllamav3_runtime_model_name",
]
