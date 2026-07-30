---
title: Reanimation
icon: material/eject-outline
---

# :material-eject-outline: Reanimation

> _“Daemons return through Systemd. A thought returns only through a boundary committed before
> death.”_

**Reanimation** follows Vessel death: Systemd raises a process, volatile services rebuild, and
Phylactery and queue records decide what may continue. It is not reload or rollback.

Death separates breath from inscription. Memory, subscribers, leases, and uncommitted frames
vanish. Only prior commits remain.

## Three rites that must not be confused

### Live Stasis — the body never died

An ordinary model or VRAM transition is **Live Stasis**. The Run stays in the Vessel, releases its
lease, waits for Orchestrator convergence, and resumes itself. Restart is not a substitute.

### Reanimation — a new Vessel judges durable truth

The new Vessel must reconnect `runs` and `rites`, construct services, warm the registry, and
publish the run substrate before the Altar serves. Reconciliation then runs best-effort; failure
is logged, and serving does not prove recovery:

- **`AWAITING_CONSENT` remains parked.** A pending verdict waits. A verdict committed while the
  process was down is re-fired; one admission advances the sequence and reads durable verdict and
  checkpoint. Failed reconciliation leaves it parked.
- **`QUEUED` remains queue-owned.** An aged row is failed only after the exact
  `(run_id, enqueue_seq)` job is proved absent, becoming `FAILED / enqueue lost`. An unprobeable
  broker preserves it and reports degradation.
- **Previous-process `RUNNING` and `AWAITING_HARDWARE` do not resume.** They become
  `FAILED / ghoul lost`; checkpoint deletion and one sequence-correct terminal event follow.
- **`AWAITING_DELEGATE` has no startup recovery today.** Its durable park is real, but startup does
  not re-fire it.
- **Missing resume checkpoints fail as `stasis lost`.** The Graph never restarts from its first
  node or original Intent.

Terminal truth commits before cleanup; [Ghouls](../vessel/ghouls.md#parks-terminal-truth-and-cancellation)
owns the exact order, and cleanup cannot revise it. There is no periodic scheduler, automatic SAQ
retry, public failed-Run retry, or outbox.

Memory-profile recovery is proved. [Graph stasis and consent
re-admission](../../state-of-the-work.md#graph-stasis-consent) remain **Partial**: no PostgreSQL
restart receipt exists, and only one approval call per model round works.

### Restoration — the whole body moves through time

Whole-body restore is different. Filesystem groundwork exists, but database, code, configuration,
freeze, restore, and reconciliation are not one operation. See [State's snapshot
boundary](../../state-of-the-work.md#whole-body-snapshot-restore); a service restart must never be
sold as rollback.

## The generated body

`lychd bind` compiles Codex intent into owned units; the Scribe reconciles them atomically. They
are projections. Do not paste or edit a Quadlet in the binding directory.

The generated contract gives the Vessel a restart policy and migration gate before start. This is
protocol evidence, not a host receipt; [systemd and rootless Podman
embodiment](../../state-of-the-work.md#systemd-podman-embodiment) remains **Operator validation**.

!!! warning "A restart is a host-lifecycle action, not a checkpoint command"
    Do not restart with active work and expect continuation. Park at Durable Stasis or accept
    failure. Direct Systemd action bypasses Orchestrator admission and lease drain.

A Vessel restart does not stop every Soulstone, clear VRAM, or restore a snapshot. Model
transitions remain Orchestrator work.

## Perform one bounded reanimation

This assumes the four [Awakening](../../summoning.md#the-awakening) observations already agree.
Reanimation cannot repair an incomplete first life.

Pulse reserves `status` for Run census and `stop` for graceful drain.
[State](../../state-of-the-work.md#core-cli-rites) owns delivery. There is no copyable zero-loss
precondition: stop submissions and settle Bridge-visible Runs, but do not restart if unseen work or
continuity matters.

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

`stop` cannot restart an active Vessel until an authenticated lifecycle port exists. `status`
proves unit and mount truth; migration must show `Result=success` and `ExecMainStatus=0`. Neither
proves model warmth. Repeat Nexus and Bridge observations.

At the same-host [Bridge](../../divination/altar/index.md), send one benign message. If state,
readiness, and reply disagree, return to [The Awakening](../../summoning.md#the-awakening).

## Read the ashes

After return, inspect durable run truth before claiming continuity:

- a consent card still pending is a preserved wait, not a hung process;
- a decided consent that re-enters `QUEUED` is a re-admitted resume hop;
- `FAILED / ghoul lost` names active work that crossed death without a supported durable boundary;
- `FAILED / enqueue lost` names an aged queued Run whose exact broker job was proved absent; and
- a surviving SAQ job protects queued labor, but does not recreate an in-memory event stream.

Preserve host, unit, image, database, queue, Run, shutdown, and recovery observations before
promoting a local result to an operator receipt.

> _The promise is not that nothing dies. The promise is that the Phylactery never calls an
> uncommitted breath immortal._
