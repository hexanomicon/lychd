# NVIDIA 24 GB Profile

Begin with one model and a measured context size on one 24 GB NVIDIA card. The single-server
shape gives you a small first workload before adding router or multi-card coordination.

## Contents

- `runes/animator/soulstones/llamacpp/single.toml`: an earlier llama.cpp declaration for one GGUF
  model and an OpenAI-compatible endpoint.

## Copy Flow

1. Start from the current [llama.cpp Rune](../../../docs/sepulcher/animator/soulstone/rune.md),
   using this fragment's single-server intent as a reference.
2. Declare an absolute host model directory in `volumes`, with the intended container target
   such as `/models`, and declare the NVIDIA CDI device. There is no automatic `~/models` mount
   or current `LYCHD_DEFAULT_SOULSTONE_MOUNTS` setting.
3. Set `model_path` to the container-visible GGUF file. Choose the image and size context,
   parallelism, and cache against the actual free VRAM; desktop and driver allocations need
   room too.
4. Follow [Summoning](../../../docs/summoning.md) for configuration, binding, first reply, and
   shutdown. This profile aims at one static chat capability; only your recorded observations
   establish the running combination.
