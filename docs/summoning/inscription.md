---
title: The Inscription
icon: material/book-edit
---

# :material-book-edit: Stage 3 — The Inscription

Before the Lich can rise, it must be told where its body will live. `init` creates the two
directories every later rite reads from and writes a starter set of configuration
templates.

```bash
lychd init
```

This establishes the two homes of the daemon:

- **The Codex** (`~/.config/lychd`) — your configuration. It holds `lychd.toml` plus the
  `runes/` tree of TOML declarations (your Soulstones, Portals, and settings). **You edit
  this.** See [The Codex](../sepulcher/codex.md).
- **The Crypt** (`~/.local/share/lychd`) — persistent data: model weights, the
  Phylactery's volumes, and generated state. **LychD manages this; you back it up.** See
  [The Crypt](../sepulcher/crypt.md).

During `init`, the filesystem is inspected. On **Btrfs**, snapshots are used directly; on
any other filesystem a loopback Btrfs image is created inside the Crypt so snapshot-based
rollback (the safety net for self-modification) still works.

## Verify the inscription

Confirm both homes exist:

```bash
ls ~/.config/lychd/lychd.toml ~/.local/share/lychd
```

## Set your model root

`init` also discovers every installed configuration schema and writes one sample TOML per
schema under the Codex `runes/` tree — including sample Soulstone and Portal declarations
you will edit in the next stage.

!!! tip "Set your model root now"
    Open `~/.config/lychd/lychd.toml` and set `model_root` to the directory that holds your
    model weights (GGUF files and the like). Every Soulstone Rune resolves its model paths
    relative to this root.

For the full Codex layout — file precedence, the `runes/` tree, and environment
overrides — see the [Runes reference](../praxis/runes/index.md).

With the Codex inscribed, proceed to [The First Soulstone](first-soulstone.md).
