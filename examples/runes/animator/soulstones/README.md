# Soulstone Runes

Soulstones declare local container-backed model services. This directory retains two runtime
shapes:

- `vllm/glm.toml`: an earlier static vLLM configuration for one model.
- `llamacpp/router.toml`: a router-mode configuration backed by an INI model catalogue.

Begin with the current [Rune contract](../../../../docs/sepulcher/animator/soulstone/rune.md) and
its [engine recipe](../../../../docs/sepulcher/animator/soulstone/engines/index.md). The older vLLM
framework fields must be expressed through `exec`; model files, runtime support, image, and GPU
devices need explicit declarations.

Current LychD mounts only the declared Rune/runtime volumes. Match model paths to their container
targets and keep host shelves outside Codex, Crypt, generated-unit, and Reactor control roots.
For router INIs, follow [preset placement](../../../llamacpp/README.md) rather than the fragment's
older Codex mount.

A static model is the smaller first workload. Router mode adds dynamic availability and soft
activation; [Summoning](../../../../docs/summoning.md) supplies the host acceptance procedure.
