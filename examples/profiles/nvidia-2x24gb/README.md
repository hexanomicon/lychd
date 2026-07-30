# NVIDIA 2x24 GB Profile

Two 24 GB cards can run one larger static vLLM resident or a llama.cpp router
that swaps among GGUF models. This is a starting profile for a dual-RTX-3090
class workstation, not a capacity guarantee.

## Contents

- `runes/animator/soulstones/vllm/glm.toml`: static vLLM OpenAI-compatible
  server, tensor-parallel across two cards.
- `runes/animator/soulstones/llamacpp/router.toml`: llama.cpp router-mode
  Soulstone for dynamic model loading.
- `llamacpp/router-models.ini`: router model catalog consumed by the llama.cpp
  example.

## Copy Flow

1. Copy `runes/` into `~/.config/lychd/runes/`.
2. Put models in `~/models`, or set `LYCHD_DEFAULT_SOULSTONE_MOUNTS` for a
   different library.
3. Copy `llamacpp/router-models.ini` to `~/.config/lychd/llamacpp/`, or edit
   `models_preset` and the `/presets` volume together.
4. Edit `/models/...` paths to match container-visible paths.
5. Start with either vLLM or the llama.cpp router. Running both on the same
   cards is an Orchestrator scheduling decision, not a safe default.

## Wiring Walkthrough

The vLLM Rune is static: `AnimatorLoader` reads TOML,
`RuntimeAdapterRegistry` makes a `VllmStone` with an `OpenAICompatibleConnector`,
then `Dispatcher` binds its capability into a Pydantic AI model.

The llama.cpp Rune is router-mode: its adapter reads `router-models.ini`, makes
one `dynamic_soft` capability per model, and, when a requested model is cold,
the dispatcher signals a transition for the Orchestrator to load it without a
container restart.

Prove a local agent call with vLLM first. Add the router when capability
selection and soft activation are what you need to debug.
