# llama.cpp Support Files

Files here are not Rune TOMLs. They are host-side support files referenced by
llama.cpp Soulstone examples.

- `router-models.ini`: model catalog for `llama-server --models-preset`.

Copy this file to `~/.config/lychd/llamacpp/router-models.ini`, which the
examples mount as `/presets/router-models.ini`, or edit the TOML
`models_preset` path and `/presets` volume together.
