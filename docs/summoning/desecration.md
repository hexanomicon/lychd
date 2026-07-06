---
title: The Desecration
icon: material/download
---

# :material-download: Stage 2 — The Desecration

Install the `lychd` command-line tool (the [Pulse](../lexicon.md) — the Hand that governs
the daemon). Pick one path. The Iron Path is recommended; it installs `lychd` into an
isolated environment so it never collides with your other Python tools.

## The Iron Path (recommended)

[`uv`](https://docs.astral.sh/uv/) installs the tool cleanly and instantly:

```bash
uv tool install lychd
```

## The Acolyte's Path (pip)

Standard pip installation, for hosts without `uv`:

```bash
pip install lychd
```

## The Necromancer's Path (source)

For Magi who intend to modify the core:

```bash
git clone https://github.com/hexanomicon/lychd.git
cd lychd
uv sync
```

From a source checkout the command runs as `uv run lychd`.

## Verify the install

Confirm the Hand answers:

```bash
lychd --help
```

You should see the command groups — `init`, `bind`, and the others. If the shell reports
`command not found`, the tool's install directory is not on your `PATH`; see
[Exorcism](../praxis/exorcism.md).

With `lychd` installed, proceed to [The Inscription](inscription.md).
