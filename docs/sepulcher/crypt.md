---
title: Crypt
icon: material/grave-stone
---

# :material-grave-stone: Crypt

> _The Codex writes the law. The Crypt keeps what must survive it._

The **Crypt** is LychD's durable data and workspace root. By default it lives at
`~/.local/share/lychd/`; `XDG_DATA_HOME` may move the root. It is not mounted wholesale into the
Vessel.

```text
~/.local/share/lychd/
├── triggers/
│   ├── inbox/
│   └── journal/
├── postgres/
│   ├── init_db.sh
│   └── data/
├── snapshots/
├── lab/
├── extensions/
└── core/
```

Each chamber has one owner:

| Chamber | Purpose | Runtime boundary |
| --- | --- | --- |
| `triggers/inbox/` | Host Reactor transition intents | Vessel read-write when the Host Reactor is selected |
| `triggers/journal/` | Terminal Reactor receipts | Vessel read-only when the Host Reactor is selected |
| `postgres/data/` | Phylactery storage | PostgreSQL unit only |
| `snapshots/` | Reserved recovery-snapshot shelf | No whole-body snapshot rite is delivered yet |
| `lab/` | Operator workspace | Read-write only when explicitly admitted |
| `extensions/` | Private Extension source | Runtime read-only |
| `core/` | Reserved Core source | Runtime read-only |

The Crypt itself grants no execution or deletion authority. **Geography is not authority:**
lifecycle receipts and live identity checks decide what LychD may replace or remove. Symlink,
mount, receipt, or identity ambiguity is witnessed, never guessed; it fails closed, preserves the
object, and returns typed recovery or blocking evidence. External projects, model shelves, foreign
mounts, and operator data do not become LychD-owned because they are near the Crypt.

## The Phylactery

PostgreSQL owns `postgres/data/`. On a suitable Btrfs host, initialization may create that exact
target as a verified subvolume and apply No-COW inheritance for new database files. On other
filesystems it remains an ordinary directory. Existing files are never retrofitted, and neither
case proves that coordinated snapshot and restore exists.

[State of Work](../state-of-the-work.md#whole-body-snapshot-restore) records that the
whole-body rite is still designed. [Snapshots](../adr/07-snapshots.md) defines the future
checkpoint protocol; [Layout](../adr/13-layout.md) owns present creation and deletion safety.

## The Spheres

The **Lab** is LychD's internal workbench. The **Outlands** are operator-selected external
workspaces mounted beneath `~/work/` inside the Vessel. A read-only Outland may serve as a
reference library; that does not make it a new trust domain.

The Vessel receives only declared mounts:

- the Lab when the active task needs it;
- selected Outlands with explicit read-only or read-write policy;
- private Extensions and reserved Core source read-only; and
- no blanket mount of the Crypt, Codex, PostgreSQL data, binding sites, or model shelves.

Unsafe hand-work does not become safe because its files are in the Lab. Trusted orchestration
remains in the Vessel; the future Tomb must receive only task-scoped workspace and artifact paths.

The exact map, ownership receipts, Btrfs identity rules, and mount contract live in
[Layout](../adr/13-layout.md).
