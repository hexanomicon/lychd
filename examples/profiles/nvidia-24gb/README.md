# NVIDIA 24 GB Profile

Use a single 24 GB card for one carefully sized local model before adding
router or dual-card complexity.

## Contents

- `runes/animator/soulstones/llamacpp/single.toml`: one llama.cpp Soulstone
  serving one GGUF model through an OpenAI-compatible endpoint.

## Copy Flow

1. Copy `runes/` into `~/.config/lychd/runes/`.
2. Put models in `~/models`, or set `LYCHD_DEFAULT_SOULSTONE_MOUNTS` for a
   different library.
3. Edit `model_path` so `/models/...` resolves in the container.
4. Run the normal bind/start flow; expect one static chat capability.

This is conservative: a desktop 4090 often needs lower context than a headless
3090 because desktop/driver overhead consumes more VRAM.
