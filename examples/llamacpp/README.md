# llama.cpp Support Files

These are host-side support files, not Rune TOMLs, for llama.cpp Soulstone
examples.

- `router-models.ini`: model catalog for `llama-server --models-preset`.

Copy it to `~/.config/lychd/llamacpp/router-models.ini`; examples mount that
path as `/presets/router-models.ini`. If you relocate it, change the TOML
`models_preset` and `/presets` volume together.
