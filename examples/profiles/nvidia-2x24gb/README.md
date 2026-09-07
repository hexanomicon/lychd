# NVIDIA 2x24 GB Profile

This profile explores two ways to use a pair of 24 GB NVIDIA cards: one static vLLM model or a
llama.cpp router that changes its loaded GGUF model. The available memory and each model's runtime
requirements determine which combination fits.

## Contents

- `runes/animator/soulstones/vllm/glm.toml`: an earlier two-card vLLM configuration.
- `runes/animator/soulstones/llamacpp/router.toml`: a router-mode llama.cpp fragment.
- `llamacpp/router-models.ini`: its model catalogue.

## Copy Flow

1. Choose one runtime and follow its current [vLLM](../../../docs/sepulcher/animator/soulstone/engines/vllm.md)
   or [llama.cpp](../../../docs/sepulcher/animator/soulstone/engines/llamacpp.md) recipe. Adapt the
   fragment rather than copying its old fields unchanged: vLLM framework arguments now belong
   in the Rune's `exec` list.
2. Declare the exact image, NVIDIA CDI devices, ports, and absolute model-directory mounts.
   Current LychD has no automatic model mount or `LYCHD_DEFAULT_SOULSTONE_MOUNTS` setting.
3. For the router, put the INI in an external runtime-support directory and mount it at
   `/presets`. Set `models_preset` and that mount together. The older Codex-directory mount in
   the fragment is refused by current binding; see [preset placement](../../llamacpp/README.md).
4. Match all `/models/...` paths to the declared container mount. Measure the model, context,
   cache, and concurrency on both cards before treating the profile as usable.
5. Follow [Summoning](../../../docs/summoning.md) for the host procedure. Declare conflicts and
   let Orchestrator govern transitions; running both services on the same cards requires its
   own coexistence evidence.

## Wiring Walkthrough

The vLLM extension registers a `VllmSoulstoneConfig` with an `OpenAICompatibleRuntimeAdapter`.
That adapter creates a `SoulstoneAnimator` and its `OpenAICompatibleConnector`; Dispatcher issues
a grant for an eligible, freshly observed capability. The exact model must appear in the runtime's
validated inventory before the capability is warm.

The llama.cpp router adapter captures its preset catalogue and derives dynamic capabilities. A
cold requested model can lead Graph to wait while Orchestrator loads it, after which Dispatcher
rechecks readiness. The [runtime-transition guide](../../../docs/sepulcher/animator/runtime-transitions.md)
explains the admission, drain, and recovery boundaries.

Establish one working static call first. Add router selection and soft activation when those are
the behaviors you want to investigate.
