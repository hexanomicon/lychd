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
| `lab/` | Operator workspace | Vessel read-write |
| `extensions/` | Private Extension source | Runtime read-only |
| `core/` | Reserved Core source | Runtime read-only |

A location in the Crypt grants neither execution nor deletion authority. **Geography is not
authority:** lifecycle receipts and live identity checks determine what LychD may replace or
remove. When a symlink, mount, receipt, or identity is ambiguous, the operation fails closed,
preserves the object, and returns typed recovery or blocking evidence. Proximity cannot make
external projects, model shelves, foreign mounts, or operator data LychD-owned.

## The Phylactery

PostgreSQL owns `postgres/data/`. On a suitable Btrfs host, initialization may create that exact
target as a verified subvolume and apply No-COW inheritance for new database files. On other
filesystems it remains an ordinary directory. Existing files are never retrofitted, and neither
case proves that coordinated snapshot and restore exists.

[State of Work](../state-of-the-work.md#whole-body-snapshot-restore) records that the
whole-body rite is still designed. [Snapshots](../adr/07-snapshots.md) defines the future
checkpoint protocol; [Layout](../adr/13-layout.md) owns present creation and deletion safety.

## The Spheres

Use the **Lab** as LychD's internal workbench. The accepted **Outlands** design would also admit
operator-selected external workspaces beneath `~/work/` inside the Vessel. Native Vessel
generation currently supplies no Outland mount selector. A read-only Outland could serve as a
reference library under that design without becoming a new trust domain.

The trusted Vessel receives these mounts:

- the Codex read-only and the Lab read-write, independent of the active task;
- private Extensions and reserved Core source read-only; and
- no blanket mount of the Crypt, PostgreSQL data, binding sites, or model shelves.

Unsafe hand-work does not become safe because its files are in the Lab. Trusted orchestration
remains in the Vessel; the future Tomb must receive only task-scoped workspace and artifact paths.

The exact map, ownership receipts, Btrfs identity rules, and mount contract live in
[Layout](../adr/13-layout.md).
