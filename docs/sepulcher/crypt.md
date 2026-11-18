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
├── runtime-guard/
├── postgres/
│   ├── init_db.sh
│   ├── pg_hba_v1.conf
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
| `runtime-guard/` | Unsettled model activation that must be reconciled | Vessel read-write, separate from Reactor receipts |
| `postgres/data/` | Phylactery storage | PostgreSQL unit only |
| `snapshots/` | Reserved recovery-snapshot shelf | No whole-body snapshot rite is delivered yet |
| `lab/` | Operator workspace | Vessel read-write |
| `extensions/` | Private Extension source | Runtime read-only |
| `core/` | Reserved Core source | Runtime read-only |

A selected [native Tether](aspects/tether.md) also keeps host-owned admission records,
revocation tombstones and public runtime configuration under `tether/`. Its boot-local sockets
have a separate lifetime.

A location in the Crypt grants neither execution nor deletion authority. **Geography is not
authority:** lifecycle receipts and live identity checks determine what LychD may replace or
remove. When a symlink, mount, receipt, or identity is ambiguous, the operation fails closed,
preserves the object, and returns typed recovery or blocking evidence. Proximity cannot make
external projects, model shelves, foreign mounts, or operator data LychD-owned.

## The Phylactery

A stopped Vessel leaves the [Phylactery](phylactery/index.md) in place. PostgreSQL owns the
files under `postgres/data/`. On a suitable Btrfs host, fresh initialization can create that
exact target as a verified subvolume and apply No-COW inheritance for new files. On supported
ext4 it can create an ordinary directory. The current lifecycle receipt requires verifiable
filesystem and object identities on Btrfs or ext4. Initialization refuses unsupported identity
providers before creating the layout.

Existing database storage is a separate case. Rootless PostgreSQL may own it through a mapped
UID. Initialization can preserve it without entering it, changing its permissions, adopting it
for deletion, or retrofitting No-COW.

For an intact cluster after process death, follow [Reanimation](phylactery/reanimation.md).
Returning the database, code and configuration together to an earlier point requires a sealed
[whole-body checkpoint](../adr/07-snapshots.md). The freeze, capture, restore and reconciliation
are still [Designed](../state-of-the-work.md#whole-body-snapshot-restore).

## The Spheres

Use the **Lab** as LychD's internal workbench. The accepted **Outlands** design would also admit
operator-selected external workspaces beneath `~/work/` inside the Vessel. Native Vessel
generation currently supplies no Outland mount selector. A read-only Outland could serve as a
reference library under that design without becoming a new trust domain.

The trusted Vessel receives these mounts:

- the Codex read-only and the Lab and `runtime-guard/` read-write, independent of the active task;
- private Extensions and reserved Core source read-only; and
- no blanket mount of the Crypt, PostgreSQL data, binding sites, or model shelves.

Unsafe hand-work does not become safe because its files are in the Lab. Trusted orchestration
remains in the Vessel; the future Tomb must receive only task-scoped workspace and artifact paths.

The exact map, ownership receipts, Btrfs identity rules, and mount contract live in
[Layout](../adr/13-layout.md).
