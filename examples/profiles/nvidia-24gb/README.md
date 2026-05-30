# NVIDIA 24 GB Profile

Single-card 24 GB machines are good for one carefully sized local model at a
time. Use this profile for a first local agent model before adding router or
dual-card complexity.

## Contents

- `runes/animator/soulstones/llamacpp/single.toml`: one llama.cpp Soulstone
  serving one GGUF model through an OpenAI-compatible endpoint.

## Copy Flow

1. Copy this profile's `runes/` subtree into `~/.config/lychd/runes/`.
2. Put model files under `~/models`, or override
   `LYCHD_DEFAULT_SOULSTONE_MOUNTS` if your model library lives elsewhere.
3. Edit `model_path` so `/models/...` resolves inside the container.
4. Run the normal LychD bind/start flow.
5. The registry should expose one static chat capability for the Soulstone.

This profile is intentionally conservative. A 4090 often needs lower context
than a headless 3090 because desktop/driver VRAM overhead is usually higher.
