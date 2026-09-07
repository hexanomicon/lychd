# llama.cpp Support Files

`router-models.ini` supplies a model catalogue for `llama-server --models-preset`. It is a runtime
support file, separate from a Soulstone's Rune TOML.

Keep the host copy outside Codex, Crypt, generated-unit, and Host Reactor control roots—for
example, in a dedicated directory beside your model shelf. Resolve that directory to an absolute
path and declare its read-only mount at `/presets`; set `models_preset` to
`/presets/router-models.ini`. Moving the host directory changes the mount source. Change
`models_preset` only if the file's path inside the container also changes.

Older fragments mount `~/.config/lychd/llamacpp/`. Current binding refuses a Soulstone mount into
Codex, so relocate that support directory before adapting them. Model files need their own
explicit mount matching the paths in the INI. See the current [llama.cpp
recipe](../../docs/sepulcher/animator/soulstone/engines/llamacpp.md) and
[Rune authoring](../../docs/sepulcher/animator/soulstone/rune.md).
