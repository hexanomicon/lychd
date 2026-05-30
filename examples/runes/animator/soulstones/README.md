# Soulstone Runes

Soulstones are local/container-backed Animator declarations.

Current examples:

- `vllm/glm.toml`: static vLLM OpenAI-compatible runtime for one model.
- `llamacpp/router.toml`: llama.cpp router-mode runtime backed by an INI model
  catalog.

Start with vLLM when proving one resident local model can bind into agents.
Use llama.cpp router mode when testing dynamic model availability and soft
activation.

By default LychD mounts `~/models` into every Soulstone as `/models`. Add
`volumes` only for extra files, alternate model libraries, or runtime-specific
support files such as llama.cpp preset INIs.
