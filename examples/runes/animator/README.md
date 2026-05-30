# Animator Runes

Animator Runes describe model/tool execution surfaces.

- `portals/`: remote providers reached over network APIs.
- `soulstones/`: local runtimes managed as containers/services.

`animator/` itself is a branch anchor. TOML files belong under concrete leaf
anchors such as `portals/openai/`, `soulstones/vllm/`, or
`soulstones/llamacpp/`.
