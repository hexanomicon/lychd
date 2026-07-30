# Soulstone Runes

Soulstones are local, container-backed Animator declarations.

Current examples:

- `vllm/glm.toml`: static vLLM OpenAI-compatible runtime for one model.
- `llamacpp/router.toml`: llama.cpp router-mode runtime backed by an INI model
  catalog.

Start with vLLM to prove a resident model binds into agents. Use llama.cpp
router mode for dynamic availability and soft activation.

LychD normally mounts `~/models` into every Soulstone as `/models`. Add
`volumes` only for extra files, another model library, or runtime support such
as llama.cpp preset INIs.
