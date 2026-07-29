---
title: Reanimation
icon: material/eject-outline
---

# :material-eject-outline: Reanimation

> _"Daemons return through Systemd. A thought returns only through a boundary committed before
> death."_

**Reanimation** is the recovery path after the Vessel process dies: Systemd raises a new process,
the application rebuilds volatile services from the Codex and live probes, and the Phylactery and
queue records decide what may continue. It is not hot reload, whole-body rollback, or a promise
that every intermediate thought survives.

The myth is exact here. Death separates breath from inscription. Process memory, live event
subscribers, open leases, and uncommitted frames vanish. Durable rows and a valid graph checkpoint
remain only where the running workflow committed them before the boundary.

## Three rites that must not be confused

### Live Stasis — the body never died

An ordinary model or VRAM transition is **Live Stasis**. The run stays inside the Vessel process,
releases its capability lease, waits while the Orchestrator drains and converges the hardware, and
resumes itself. Restarting the Vessel is neither required nor a safe substitute.

### Reanimation — a new Vessel judges durable truth

After process death, the new Vessel reconnects the fixed `runs` and `rites` queues, warms the
Animator registry, publishes a fresh process-local run substrate, and attempts startup
reconciliation before serving the Altar. An unexpected reconciliation exception is contained and
logged so the application may still serve; a live Altar therefore does not prove that reconciliation
succeeded. Current outcomes after a successful reconciliation attempt are deliberately unequal:

- **`AWAITING_CONSENT` remains parked.** A pending verdict waits. A verdict committed while the
  process was down is re-fired through the run engine when reconciliation succeeds; the resume hop
  reads the durable graph checkpoint and continues event sequence after the persisted history. If
  that reconciliation attempt fails, the consent remains parked for a later retry or operator
  recovery rather than being called resumed.
- **`QUEUED` remains queue-owned.** An aged row is failed only after the exact
  `(run_id, enqueue_seq)` SAQ job is proved absent. If the broker cannot be checked, the row is
  preserved and reconciliation reports degradation rather than guessing.
- **Previous-process `RUNNING` and `AWAITING_HARDWARE` do not resume.** They become `FAILED` with
  `ghoul lost`, their checkpoint is deleted, and a terminal event is recorded. A checkpoint beside
  an active row is not authority to replay arbitrary work.
- **A missing consent checkpoint fails honestly.** Reanimation never silently restarts the graph
  from its first node when durable stasis has been lost.

Focused tests prove a memory-profile consent restart and these reconciliation rules. [State of
Work](../../state-of-the-work.md#graph-stasis-consent) records the missing Postgres
Consent-plus-Checkpoint restart receipt and the current single-approval boundary.

### Restoration — the whole body moves through time

Whole-body snapshot and restore is a different ritual. LychD has filesystem groundwork, but it
does not yet coordinate database, code, configuration, freeze, restore, and post-restore
reconciliation as one proved operation. See [State's snapshot
boundary](../../state-of-the-work.md#whole-body-snapshot-restore); a service restart must never be
sold as rollback.

## The generated body

`lychd bind` compiles validated Codex intent into the current Pod, Phylactery, migration gate,
Vessel, Host-Reactor units, selected extensions, and Soulstones, then asks the Scribe to reconcile
the complete owned fileset atomically. The generated files are projections, not operator-authored
configuration. Do not paste a Quadlet from this page or edit one in the binding directory.

The current generated contract gives the Vessel a Systemd restart policy and requires the
one-shot migration gate before an explicit Vessel start. That is repository protocol evidence, not
yet a maintained real-host reboot receipt; [systemd and rootless Podman embodiment remains an
operator-validation boundary](../../state-of-the-work.md#systemd-podman-embodiment).

!!! warning "A restart is a host-lifecycle action, not a checkpoint command"
    Do not restart a Vessel with active work and expect that work to continue. Park at a supported
    Durable Stasis boundary first, or accept that current active runs will settle as failed. A
    direct Systemd action also bypasses the Orchestrator's admission and lease-drain protocol.

A Vessel-only restart does not mean “stop every Soulstone,” “clear all VRAM,” or “restore a
snapshot.” Individual adapters may declare additional dependency edges, but model transitions
belong to the Orchestrator and whole-pod actions remain explicit break glass.

## Perform one bounded reanimation

This rite assumes the four observations in [Summoning](../../summoning.md#the-awakening) have
already agreed. If they have not, return there; Reanimation cannot repair an incomplete first life.

The public Pulse reserves `status` for the active-run census and `stop` for graceful system-wide
drain. [State](../../state-of-the-work.md#core-cli-rites) owns whether this revision has proved
those boundaries. Until both are useful, this page cannot offer a copyable zero-loss precondition.
For a bounded local demonstration, stop new submissions and wait for every run visible in the
Bridge to settle; that observation is incomplete. If unseen work may exist or continuity matters,
do not restart the Vessel.

If Codex intent changed, bind the new projection first. If no configuration or unit intent changed,
do not bind merely to restart:

```bash
# Only when Codex or generated-unit intent changed:
uv run --extra postgres-binary lychd bind --dry-run
uv run --extra postgres-binary lychd bind

systemctl --user restart lychd-vessel.service
uv run --extra postgres-binary lychd status
systemctl --user show lychd-migrate.service \
  --property=Result --property=ExecMainStatus
uv run --extra postgres-binary lychd logs services --lines 200
```

The public `stop` verb cannot yet perform this restart: while the Vessel is active, arbitration
correctly refuses direct actuation until an authenticated Vessel lifecycle port exists. The status
projection proves exact owned unit activity and mount truth, while the separate migration probe
must show `Result=success` and `ExecMainStatus=0`. Neither proves model warmth. Repeat the Nexus and
Bridge observations rather than trusting process state alone.

Open the [Bridge](../../divination/altar/index.md) only through its stated same-host browser
boundary and send one benign message. If unit state, runtime readiness, and the reply do not agree,
stay in [The Awakening](../../summoning.md#the-awakening) and diagnose the first missing
observation.

## Read the ashes

After return, inspect durable run truth before claiming continuity:

- a consent card still pending is a preserved wait, not a hung process;
- a decided consent that re-enters `QUEUED` is a re-admitted resume hop;
- `FAILED / ghoul lost` names work that crossed death without a supported durable boundary; and
- a surviving SAQ job protects queued labor, but does not recreate an in-memory event stream.

Preserve the exact host, unit, image, database, queue, run, shutdown, and recovery observations if
you intend to promote this from a bounded local result to a maintained operator receipt.

> _The promise is not that nothing dies. The promise is that the Phylactery never calls an
> uncommitted breath immortal._
