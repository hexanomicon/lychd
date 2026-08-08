---
title: Codex
icon: material/book-open-page-variant
---

# :material-book-open-page-variant: Codex

> _The Hexanomicon is prophecy. The Codex is law._

The **Codex** is the written configuration boundary from which one Sepulcher is summoned. By
default it lives at `~/.config/lychd/`; `XDG_CONFIG_HOME` may move the root without changing its
inner geography.

```text
~/.config/lychd/
├── lychd.toml
└── runes/
    └── animator/
        ├── soulstones/
        └── portals/
```

[Configuration](../adr/12-configuration.md) owns loading, validation, and Rune registration.
[Layout](../adr/13-layout.md) owns the exact paths, permissions, receipts, and Host/Container
boundary.

## The Prime Inscription

`lychd.toml` contains process-wide settings only: server and persistence settings, orchestration
policy, and extension selection. Named runtime or provider instances belong in individual Rune
documents beneath `runes/`. **Scroll** is reserved for an immutable Spellweaver Pattern revision;
configuration is not executable workflow law.

Settings resolve in one order: explicit construction → environment overrides → `lychd.toml` →
Pydantic file secrets → model defaults. LychD loads no `.env`; nested sections load no separate
sources.

An incomplete law may be edited; it may not half-enter the body. The complete configuration must
validate before infrastructure projection begins.

The generated foundation selects the caged Host Reactor:

```toml
[orchestration.switching]
actuator = "host-reactor"
```

`actuator = "systemd"` is the explicit uncaged development path. The full Reactor path,
acknowledgement, mount, and validation contract belongs to
[Configuration](../adr/12-configuration.md#extension-activation-and-application-selection).

## The Rune Archive

A **Rune** is one validated TOML document beneath the active Rune root. Its path determines its
owning family and named instance. It is frozen intent—not a running service or generated Quadlet.

```text
runes/animator/soulstones/<family>/<instance>.toml
runes/animator/portals/<family>/<instance>.toml
```

Extensions may register anchors. The Librarian accepts only declared anchors and validated
schemas; a Rune document in an invented directory creates nothing.

Three rules keep the Archive legible:

- Soulstone model paths are container paths, normally below `/models`; a volume binding names the
  Host source.
- Runes name secrets; they never embed secret values.
- Valid Runes feed `lychd bind`; they never edit systemd or Podman state themselves.

Current Animator Runes expose model-shaped `[[models]]` declarations. The Designed
general-service form uses `[[capabilities]]` references to registered interface/profile/driver/
dialect/evidence/resource definitions. Non-model services do not invent a model id, and an
"OpenAI-compatible" label never implies every API beneath `/v1`; see
[Capabilities](animator/capabilities.md) and [Connectors](animator/connectors.md).

Read [Animator](animator/index.md), [Soulstone](animator/soulstone/index.md), and
[Portal](animator/portal.md) for the built-in families.

## The Rite of Binding

Edit the Codex, then project it:

```bash
lychd bind
```

Binding follows one direction:

```text
Codex
→ load declared anchors
→ validate the complete configuration
→ calculate one binding plan
→ transactionally publish owned Quadlet and user-unit files
→ reload systemd
```

Generated Quadlets live by default in `~/.config/containers/systemd/`; selected plain user units
live in `~/.config/systemd/user/`. Both are shared operator directories, not a common workbench.
LychD owns only the exact filenames recorded in the same-UID, mode-`0600` `.lychd-owned.json`
receipt.

If a desired filename exists outside that receipt, binding fails closed: it neither adopts,
overwrites, nor deletes the operator's file. Review the collision deliberately, then bind again.

Never hand-edit a generated file named by the receipt. The next successful bind reconciles it from
the Codex. Mutation failure is either cleanly rolled back or retains indeterminate recovery
evidence. [State of Work](../state-of-the-work.md#core-cli-rites) records the core CLI rites as
Partial; repository tests do not claim real systemd or Podman actuation.

> _To change the manifestation, amend the law._
