---
title: Runes
icon: material/file-tree
---

# :material-file-tree: Runes — the Codex layout

A **Rune** is one validated TOML file under the [Codex](../../sepulcher/codex.md). It
declares intent; it is never the running service and never the generated Quadlet manifest.
This page is the reference for how the Codex is laid out and how declarations resolve.

## The Codex tree

`lychd init` creates the Codex at `~/.config/lychd`:

```
~/.config/lychd/
├── lychd.toml                        # top-level settings
└── runes/
    └── animator/
        ├── soulstones/               # local model services (Soulstone Runes)
        │   └── <group>/<name>.toml
        └── portals/                  # remote providers (Portal Runes)
            └── <group>/<name>.toml
```

- **`lychd.toml`** — the top-level settings payload: `model_root`, the `[orchestration]`
  block, and other core sections. See the [Orchestration reference](orchestration.md).
- **`runes/animator/soulstones/`** — one file per local model service. See the
  [Soulstone Rune reference](soulstones.md).
- **`runes/animator/portals/`** — one file per remote provider. See the
  [Portal Rune reference](portals.md).

Extensions may register additional rune schemas; `init` discovers every installed schema
and writes a sample TOML for each, so the tree you see reflects what is actually installed.

## How declarations resolve

- **Model paths** in a Soulstone Rune resolve against `model_root` in `lychd.toml`.
- **Secrets** are referenced by *name*, never by value: a rune names a secret (for example
  `api_key_secret_name = "portal_openai_main"`) and LychD resolves it from the host's secret
  store at bind/run time. Runes are safe to read; they carry no secret material.
- **`lychd bind`** transmutes every valid rune into podman/systemd Quadlet manifests. A rune
  that fails validation stops the bind with a named error rather than emitting a broken unit.

## Editing safely

The Codex is the source of truth. The [Altar](../../divination/altar/bindings.md)'s
Bindings surface *reflects* it read-only; you make changes by editing the rune files and
running `lychd bind` again. Never hand-edit the generated Quadlet manifests — they are
regenerated on every bind.
