---
title: 13. Layout
icon: material/file-tree
---

# :material-file-tree: 13. Layout

!!! abstract "Context and decision"
    XDG geography tells LychD where an object belongs; typed creation and binding receipts decide
    what it may later change or remove.

## The three domains

`src/lychd/system/constants.py` is the executable path contract. `~` is the effective LychD
user's home. Shared XDG parents are never recursively owned by LychD.

| Domain | XDG root and default | LychD root | Purpose |
| --- | --- | --- | --- |
| Codex | `XDG_CONFIG_HOME` or `~/.config/` | `~/.config/lychd/` | `lychd.toml`, lifecycle receipt, Runes |
| Crypt | `XDG_DATA_HOME` or `~/.local/share/` | `~/.local/share/lychd/` | durable data, triggers, PostgreSQL, Lab, Core, Extensions |
| Forge | `XDG_CACHE_HOME` or `~/.cache/` | `~/.cache/lychd/` | disposable assembly staging |

The Codex contains `lychd.toml`, `.lychd-lifecycle.json`, and `runes/` including the Animator,
Soulstone, and Portal anchors. The Crypt contains the Vessel's `runtime-guard`, `triggers/inbox` and `triggers/journal`,
`postgres/init_db.sh`, `postgres/pg_hba_v1.conf`, `postgres/data`, `snapshots`, `lab`, `core`, and `extensions`.
`postgres/data` may be an ordinary directory, external mount, or LychD-created Btrfs subvolume.
The Forge contains `assembly`. [Configuration (12)](12-configuration.md) owns what these paths
mean; Security owns credentials and network policy.

Binding takes place in shared host namespaces: `~/.config/containers/`,
`~/.config/containers/systemd/`, `~/.config/systemd/`, and `~/.config/systemd/user/`, with XDG
overrides applied. The lifecycle and Scribe receipts identify exactly which names and objects
LychD owns there. These regular, non-symlink, invoking-UID-owned `0600` files grant no authority
over the shared parents.

## Creation, binding, and deletion authority

`init --dry-run` describes a plan without mutation; `init` journals only successful creation
identities. At the shared binding sites, init creates missing components as `0700` and preserves
safe existing modes. Planning and execution refuse symlinks, non-directories, foreign ownership,
unsafe effective access or group/other writability, and unsafe ancestry (except an appropriate
sticky root/invoker-owned directory or a foreign read-only mount). `bind` applies the same
binding-site law while planning and committing, but never creates a missing site. The
per-UID/per-Codex lifecycle lock is under fixed host `/tmp`, not caller-selected `TMPDIR`.

The exact existing PostgreSQL `data/` leaf is a preservation-only exception to host-UID
ownership: rootless PostgreSQL may own it through a subordinate UID. Init verifies its real,
host-owned parent through no-follow descriptors and observes the leaf without entering it;
neither may be group/other-writable. It neither changes that ownership or mode nor adopts the
leaf into ordinary directory deletion authority. This observation proves safe preservation,
not container access, database readiness, or permission to repair an arbitrary foreign directory.

### Publish an owned object

Every traversal is descriptor-relative and no-follow. A missing component is made under a private
same-directory staging name, opened and device/inode-attested, then atomically published without
replacement. The receipt records the opened identity and parent descriptor authority rather than a
replaceable pathname. File publication follows the same rule: write and `fsync` a candidate,
publish no-clobber, re-attest through the pinned parent, `fsync` the directory, then journal. A
race winner, replacement, ambiguous result, or failed journal is preserved or quarantined as typed
recovery; it is never broadened into deletion authority.

The Designed [Reliquary profile](06-persistence.md#reliquary-custody-designed) binds an explicitly
supplied isolated private root to its exact owned identity; it introduces no implicit Crypt path
or container mount. Artifact identifiers and producer labels never supply unchecked path
components. Reads and publication re-attestation use nonblocking, no-follow opens and verify the
opened inode before reading. Payload retirement follows a durable tombstone and exact identity
attestation, then namespace sync. Unknown names, extra hardlinks, replacements and interrupted
outcomes remain recovery evidence rather than deletion authority.

### Retire only recorded identities

After a complete transaction, the receipt may adopt the exact device/inode identities of the
dedicated Codex, Crypt, and Forge roots. Shared XDG parents, mounts, source checkouts, and external
model shelves remain outside that grant. `del` is a separately confirmed destructive lifecycle:
it joins receipt authority to a live inventory, stops managed installation state, and refuses
unknown mounts, identity mismatches, invalid receipts, foreign objects, or ambiguous ancestry. Recursive
walks reject mount crossings and possible Btrfs root/stub signatures. Deletion moves a
re-attested leaf to a collision-resistant private sibling before type-specific removal; mismatch or
failure restores it when possible, otherwise leaves a typed recovery marker. Published init
creations are never pathname-deleted as rollback.

## PostgreSQL substrate

Only an absent PostgreSQL `data/` target on trusted Btrfs may receive a new subvolume and `+C`
attempt. Creation addresses the leaf through its inherited parent descriptor. Identity observation
uses a bounded, fixed read-only helper with only the opened leaf descriptor: it requires a real
Btrfs root directory and a supported kernel ABI before reading its own UUID and ID through
`BTRFS_IOC_GET_SUBVOL_INFO`. No privileged path or snapshot lookup is required. No-COW mutation
and before/after confirmation remain descriptor-bound. A successful subvolume records canonical
UUID and non-reserved ID as well as device/inode in the version-2 lifecycle receipt. Existing
storage is never retrofitted; `+C` is only an inheritance policy and a false result is a warning.

Retiring a subvolume requires identity established at creation; observing an existing subvolume
cannot adopt it or fill in a missing identity. A mounted Phylactery requires complete live mount
and Btrfs agreement. An unmounted one requires the exact version-2 creation receipt, matching
live identity, and a safe top-level mapping. Once those checks succeed, LychD emits the attested
`btrfs subvolume delete --subvolid ID TOP_LEVEL` operator handoff and waits for proven absence
before generic retirement. It never invokes `sudo`.

## Host and container geography

The Vessel uses identical host/container targets: Codex is read-only; `lab` and `runtime-guard` are read-write; `core`
and `extensions` are read-only; and when selected, Reactor inbox is read-write and journal is
read-only. PostgreSQL data belongs to its PostgreSQL unit; there is no blanket Crypt mount.
`~/work/` is an explicit read-write Outland mount and never gains Three-Domain lifecycle authority.

Tomb's reserved task, workspace, artifact, and cache targets sit beneath
`~/.local/share/lychd/tomb/`, but it receives no Codex and no trigger/signalling path. Its envelope
is secret-forbidden. This is a designed trust delta, not an executor: [Security (09)](09-security.md)
owns its credentials/network/isolation and [Workers (14)](14-workers.md) any executor.

## Consequences

XDG overrides relocate roots while preserving relative topology and ownership law. Knowing an
object's location helps find it; only the appropriate ownership evidence permits adoption,
overwrite, or deletion. The implemented CLI path is Partial, with real-host lifecycle proof still
separate. [State of Work](../state-of-the-work.md#core-cli-rites) owns that maturity boundary.