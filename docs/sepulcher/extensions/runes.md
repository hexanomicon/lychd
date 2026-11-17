---
title: Runes
---

# Runes

To add typed configuration, define and register Rune schemas. Phoenix's
[configuration module](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/config.py)
is a working example: `ObservabilityConfig` has `path_fragment = Path("observability")` and
`PhoenixSettings` adds `Path("phoenix")`, forming `observability/phoenix`. The branch cannot own
TOML; the leaf can. The [registration shim](lifecycle.md) adds both schemas.

## Give the contribution a typed Rune

A Rune is a frozen, validated top-level TOML instance. The integration fixture writes an active
document at `<Codex>/runes/observability/phoenix/desk.toml`:

```toml
name = "desk-eye"
ui_port = 16006
otlp_port = 14317

[quadlet]
image = "docker.io/arize-ai/phoenix:latest"
```

`PhoenixSettings` rejects unknown fields and validates `name` as a safe service identity. The
example overrides the default name and ports; the image repeats the typed default. The loader
derives `source_file` from the path; do not put it in TOML. This example is configuration, not
a pull or live-service receipt.

The schema supplies a `sample_template` whose rendered sample is inactive when its first nonempty
line is exactly:

```toml
# lychd: sample-rune
```

Remove the marker in a configured document to activate it. An absent or marked sample Rune produces
no Phoenix container even when the package is selected. [Codex](../codex.md) owns configuration,
Rune operations, and binding; [Services](services.md) follows the active Rune into projection.

The [configuration integration test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_extension_configuration.py)
checks registered schemas and provenance, inactive samples, the frozen active Rune and its exact
`source_file`. Run it and the extension unit tests using the command in [Lifecycle](lifecycle.md#finish-a-bounded-contribution).
