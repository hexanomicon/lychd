# Animator Runes

Animator Runes describe model and tool execution surfaces.

- `portals/`: remote providers reached over network APIs.
- `soulstones/`: local runtimes managed as containers/services.

`animator/` is a branch anchor: TOML belongs in a concrete leaf such as
`portals/openai/`, `soulstones/vllm/`, or `soulstones/llamacpp/`.
