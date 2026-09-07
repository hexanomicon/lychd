---
title: Reanimation
icon: material/eject-outline
---

# :material-eject-outline: Reanimation

> _“Daemons return through Systemd. A thought returns only through a boundary committed before
> death.”_

**Reanimation** brings a new Vessel to the records committed before its predecessor died.
Systemd can raise the process; the Phylactery, queue, checkpoint, and wait owners determine which
work may return. Volatile memory, subscribers, leases, and uncommitted frames are gone.

A [durable park](../extensions/weaver/stasis-and-return.md) can return through a fresh worker
claim in the same Vessel. Reanimation is needed only when the application process has died.

## Three rites that must not be confused

| Need | Rite | Continuity boundary |
| --- | --- | --- |
| A model or VRAM transition during live work | **Live Stasis** | The resident Run releases its lease, waits for Orchestrator convergence, then resumes itself. |
| A new application process after Vessel death | **Reanimation** | A new process reconciles committed truth before admitting work. |
| An earlier whole body, including database, code, and configuration | **Restoration** | Coordinated snapshot, freeze, restore, and reconciliation remain Designed. |

<span id="live-stasis-the-body-never-died"></span>
<span id="restoration-the-whole-body-moves-through-time"></span>

A Vessel restart neither substitutes for a model transition nor stops every Soulstone or clears
VRAM. [Snapshot State](../../state-of-the-work.md#whole-body-snapshot-restore) keeps the
whole-body boundary separate.

## Perform one bounded reanimation

Begin only after the four [Awakening](../../summoning.md#the-awakening) observations agree.
Reanimation cannot complete a host's unfinished first life. Run the commands below from the stable
[Summoning checkout](../../summoning.md#the-desecration), under the same operator user and XDG
environment.

Stop submissions and let Bridge-visible work settle. There is no complete Run census or graceful
drain command that proves zero-loss restart; if unseen work or continuity matters, do not restart.
Pulse reserves `status` for Run census and `stop` for graceful drain, while
[State](../../state-of-the-work.md#core-cli-rites) records their current limits. Direct Systemd
action bypasses Orchestrator admission and lease drain. Active work must reach a supported durable
boundary, or its loss must be accepted.

### The generated body {#the-generated-body}

`lychd bind` and the Scribe project Codex intent into owned units atomically. Edit that intent,
never paste or hand-edit a generated Quadlet. The generated Vessel has a restart policy and a
migration gate before start; real [systemd/Podman embodiment](../../state-of-the-work.md#systemd-podman-embodiment)
still needs operator validation.

When Codex or unit intent changed, bind first. Otherwise restart the existing projection:

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

The current `stop` cannot stop an active Vessel without the authenticated lifecycle port.
`status` establishes unit and mount truth; the migration unit must report `Result=success` and
`ExecMainStatus=0`. Neither proves model warmth. Repeat Nexus readiness and a benign same-host
[Bridge](../../divination/altar/index.md) reply. Disagreement among state, readiness, and reply
returns the investigation to [The Awakening](../../summoning.md#the-awakening).

## Reanimation — a new Vessel judges durable truth

Before publishing its substrate or Altar services, the Vessel connects `runs` and `rites`,
constructs services, warms the registry, synchronizes standing policy, and reconciles durable
state. Required PostgreSQL recovery must finish cleanly; failure or degradation aborts startup.
The memory profile has no cross-process truth and remains best-effort.

- **`AWAITING_CONSENT` remains parked.** A pending verdict waits. A verdict committed while the
  process was down is re-fired; one admission atomically creates its next delivery and later reads
  durable verdict and checkpoint. The pre-park crash window is recoverable only when the first
  resumable snapshot binds this Run and its exact latest Consent id, with that owner still
  non-cancelled. An already-decided owner is parked and then re-fired.
- **`QUEUED` remains Run-ledger-owned.** Its exact `RunDelivery` says fresh versus resume, queue,
  priority, and publication state. `HELD` is refused because initiating context never became
  publishable. Current-boot work is retained; a proven pre-boot active generation is terminally
  fenced and re-probed; an absent job is republished under the same key; a terminal broker record
  rotates to a fresh sequence without changing delivery mode. Missing or mismatched delivery
  truth, unprovable active ownership, queue absence, or probe failure makes recovery degraded
  rather than inventing an outcome.
- **Previous-process `RUNNING` and `AWAITING_HARDWARE` do not replay.** Startup may recover
  the exact first-node Consent or delegate pre-park boundary; otherwise it contains correlated
  effects and records `FAILED / ghoul lost`. Checkpoint deletion and one sequence-correct durably
  drained terminal event follow.
- **`AWAITING_DELEGATE` refreshes its exact owner.** Only a terminal owning `AgentJob` may re-admit
  it. Missing coordination or owner identity fails required PostgreSQL startup.
- **Missing resume checkpoints fail as `stasis lost`.** The Graph never restarts from its first
  node or original Intent.
- **`CANCELLING` still owes containment.** Startup continues the elected cancellation; a broker
  or delegate whose containment remains uncertain cannot be declared terminal merely to open the
  Altar.

Startup repairs missing or mismatched terminal evidence from canonical terminal Runs before
removing residual checkpoints. [Ghouls](../vessel/ghouls.md#parks-terminal-truth-and-cancellation)
owns terminal ordering. A checkpoint left by failed cleanup never revives a terminal Run.

Lifespan-owned delivery, consent, and delegated-wait relays continue repair after startup. They
retain degraded keyset pages while scanning newer owners. There is no periodic workflow scheduler,
generic automatic SAQ retry, public failed-Run retry, same-boot worker-failure custody watchdog,
or transactional Step/event outbox.

The disposable [two-boot factory receipt](../../state-of-the-work.md#phylactery-first-light)
proves a narrower PostgreSQL lifecycle with offline collaborators. It does not prove a real
Consent-plus-Checkpoint restart. [Graph stasis and consent re-admission](../../state-of-the-work.md#graph-stasis-consent)
remain Partial, and Bridge accepts only one approval call per model round.

## Read the ashes

A pending consent card is a preserved wait. A decided consent back in `QUEUED` has won a resume
hop, but still awaits a worker claim. `FAILED / ghoul lost` identifies work that crossed death
without a supported durable boundary. A surviving or republished SAQ job preserves queued labor,
not the old in-memory event stream.

Retain the host, unit, image, database, queue, Run, shutdown, and recovery observations before
promoting the result to an operator receipt.

> _The promise is not that nothing dies. The promise is that the Phylactery never calls an
> uncommitted breath immortal._
