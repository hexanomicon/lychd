# LychD Examples

These files collect individual Rune declarations, hardware-oriented profiles, and llama.cpp
support files. LychD does not load this tree automatically.

Some Soulstone fragments retain an earlier configuration shape: they assume a default model
mount, place presets inside Codex, or express vLLM flags as top-level TOML fields. Adapt them to the
current [Rune contract](../docs/sepulcher/animator/soulstone/rune.md) before use. For a first host
and model, follow [Summoning](../docs/summoning.md), which supplies the current declaration and
acceptance procedure.

## Groups

- [Rune snippets](runes/README.md): one declaration for an existing Codex.
- [Operator profiles](profiles/README.md): runtime choices organized by hardware capacity class.
- [llama.cpp support](llamacpp/README.md): router presets and their explicit file mounts.

Choose the runtime and model first, then bind their exact files, image, devices, and launch
arguments. A profile gives you material to adapt; a host receipt records what that adaptation
actually did.
