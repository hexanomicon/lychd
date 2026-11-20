# Soulstone Runes

Soulstones declare local container-backed model services. Choose a model and runtime before
copying a Rune into your Codex.

## Local Qwen on CPU

Use [`llamacpp/qwen-cpu.toml`](llamacpp/qwen-cpu.toml) to try one small local chat model on a
summoned Linux host. The Rune uses the CPU llama.cpp image and an explicit read-only GGUF mount.

1. Download `qwen2.5-0.5b-instruct-q4_k_m.gguf` from the pinned
   [Qwen release](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/9217f5db79a29953eb74d5343926648285ec7e67)
   to a model shelf outside Codex. Its SHA-256 is
   `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`.
2. Enable `animator/llamacpp` and run `lychd init` using the
   [Summoning procedure](../../../../docs/summoning.md#the-inscription). From the repository root,
   copy the Rune:

   ```bash
   CODEX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lychd"
   cp -i examples/runes/animator/soulstones/llamacpp/qwen-cpu.toml \
     "$CODEX_DIR/runes/animator/soulstones/llamacpp/qwen-cpu.toml"
   ```

3. Replace `/absolute/path/to/model-shelf` in the copied Rune with the real host directory. Keep
   the container path `/models`. Choose a free host port if `8082` is occupied. Pull the image
   named by `quadlet.image`, then run `uv run --extra postgres-binary lychd bind --dry-run`.
4. To try this exact model in Bridge, set the following selection in `lychd.toml`. If
   `[weaver.bridge]` already exists, edit that table and replace its previous selection.

   ```toml
   [weaver.bridge]
   revision = "2"
   capability_key = "qwen-local:chat:qwen2.5-0.5b-instruct"
   ```

5. Apply the bind with `uv run --extra postgres-binary lychd bind`. If the Vessel is stopped,
   follow [normal startup](../../../../docs/summoning.md#the-awakening). If it is running,
   follow the [quiescent restart procedure](../../../../docs/sepulcher/extensions/animators/portal.md#4-bind-restart-and-observe)
   to load the new configuration. Send one local Bridge message. On the local Altar, find the
   exact Qwen key in `all_capabilities` at `/orchestrator/status` to confirm registration, and check
   the Bridge reply to confirm inference.

## Other runtime fragments

The directory also retains these earlier configurations:

- `vllm/glm.toml`: an earlier static vLLM configuration for one model.
- `llamacpp/router.toml`: a router-mode configuration backed by an INI model catalogue.

Begin with the current [Rune contract](../../../../docs/sepulcher/extensions/animators/soulstone/rune.md) and
its [engine recipe](../../../../docs/sepulcher/extensions/animators/soulstone/engines/index.md). The older vLLM
framework fields must be expressed through `exec`; model files, runtime support, image, and GPU
devices need explicit declarations.

Current LychD mounts only the declared Rune/runtime volumes. Match model paths to their container
targets and keep host shelves outside Codex, Crypt, generated-unit, and Reactor control roots.
For router INIs, follow [preset placement](../../../llamacpp/README.md) rather than the fragment's
older Codex mount.

A static model is the smaller first workload. Router mode adds dynamic availability and soft
activation; [Summoning](../../../../docs/summoning.md) supplies the host acceptance procedure.
