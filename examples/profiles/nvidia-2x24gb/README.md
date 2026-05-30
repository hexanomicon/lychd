# NVIDIA 2x24 GB Profile

Dual 24 GB machines can support either one larger static vLLM resident or a
llama.cpp router that swaps between multiple GGUF models. Treat this as a
starting profile for a dual RTX 3090 class workstation.

## Contents

- `runes/animator/soulstones/vllm/glm.toml`: static vLLM OpenAI-compatible
  server, tensor-parallel across two cards.
- `runes/animator/soulstones/llamacpp/router.toml`: llama.cpp router-mode
  Soulstone for dynamic model loading.
- `llamacpp/router-models.ini`: router model catalog consumed by the llama.cpp
  example.

## Copy Flow

1. Copy this profile's `runes/` subtree into `~/.config/lychd/runes/`.
2. Put model files under `~/models`, or override
   `LYCHD_DEFAULT_SOULSTONE_MOUNTS` if your model library lives elsewhere.
3. Copy `llamacpp/router-models.ini` to `~/.config/lychd/llamacpp/`, or edit
   `models_preset` and the `/presets` volume together.
4. Edit `/models/...` model paths to match the container-visible paths.
4. Pick either the vLLM resident or the llama.cpp router first. Running both on
   the same two cards is a scheduling decision for the orchestrator, not a good
   default.

## Wiring Walkthrough

The vLLM Rune is a static Soulstone. `AnimatorLoader` reads the TOML,
`RuntimeAdapterRegistry` builds a `VllmStone` with an `OpenAICompatibleConnector`,
and `Dispatcher` later binds the selected capability into a Pydantic AI model.

The llama.cpp Rune is router-mode. The adapter reads `router-models.ini`,
synthesizes one capability per model section, and marks those capabilities as
`dynamic_soft`. When a requested router model is not warm, the dispatcher raises
a transition signal and the orchestrator asks llama.cpp to load that model
without restarting the container.

Do the vLLM path first when proving that agents can call a local model. Add the
router path once capability selection and soft activation are the thing you are
debugging.
