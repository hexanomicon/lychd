---
title: Reanimation
icon: material/eject-outline
---

# :material-eject-outline: Reanimation

> _Read the ashes before you call the dead by name._

**Reanimation** brings a new Vessel to the records committed before its predecessor died.
Systemd can raise the process; the Phylactery, queue, checkpoint, and wait owners determine which
work may return. Volatile memory, subscribers, leases, and uncommitted frames are gone.

A [durable park](../aspects/weaver/stasis-and-return.md) can return through a fresh worker
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

For a planned host trial, first establish the four [Awakening witnesses](../../summoning.md#the-awakening)
and record the settled session and Run you want to find on the far side. Stop submissions and
let visible work settle. Active work needs a supported durable boundary or explicit acceptance
of its loss. Neither an idle Bridge nor `lychd status` supplies a complete Run census.

The public CLI refuses active-Vessel lifecycle control. An operator planning to interrupt the
process needs an independently authorized plan to identify the owned units and containers,
close admission, establish terminal state, and preserve dependencies wherever the outcome is
unknown. [Close the rite](../../summoning.md#close-the-rite) explains these requirements.
If the plan calls for
`systemctl --user restart lychd-vessel.service`, that action bypasses Orchestrator admission
and lease drain. If required continuity or the fate of unseen work is uncertain, stop
at observation. An unexpected process death can still be investigated from the records below.

### The generated body {#the-generated-body}

The generated Vessel has a restart policy and a migration gate. Keep the existing binding for a
process-only return. If the Codex itself changed, the [binding rite](../codex.md#the-rite-of-binding)
projects the new intent into owned units. Editing a generated Quadlet by hand would lose that
source of truth. The actual [systemd/Podman embodiment](../../state-of-the-work.md#systemd-podman-embodiment)
still needs operator validation.

After the new process starts, observe it from the stable
[Summoning checkout](../../summoning.md#the-desecration), under the same operator user and XDG
environment:

```bash
uv run --extra postgres-binary lychd status
systemctl --user show lychd-migrate.service \
  --property=Result --property=ExecMainStatus
uv run --extra postgres-binary lychd logs services --lines 200
```

Read the unit and mount observations. Require migration `Result=success` and `ExecMainStatus=0`.
Reopen the original session and match its retained reply and Run identity. Then check Nexus
readiness and submit a benign same-host [Bridge](../../divination/altar/index.md) turn if the
trial admits new work. A new reply tests current service. Reading the earlier one tests
retention. Disagreement returns the investigation to [The Awakening](../../summoning.md#the-awakening).

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

Startup repairs missing terminal evidence from canonical terminal Runs. Conflicting terminal
evidence instead aborts required PostgreSQL startup; recovery does not overwrite it. Cancellation
cleanup may still remove a checkpoint if evidence fails. [Ghouls](../vessel/ghouls.md#parks-terminal-truth-and-cancellation)
explains terminal ordering. Conversely, a checkpoint surviving failed cleanup cannot revive a
terminal Run.

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

If a terminal Run still has a checkpoint, inspect the ledger and terminal evidence before
drawing a conclusion from that row. In the [PostgreSQL cleanup test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_terminal_checkpoint_recovery_pg.py),
deletion of one checkpoint fails. Both Runs stay `DONE` and receive their ordered terminal
evidence. Once the fault is lifted, a later sweep clears the checkpoint without replaying a Run.
The test replaces the recovery adapters against the same database. A host trial must also
retain its actual host, unit, image, database, queue, Run, shutdown and recovery observations.

> _Inscribe the breath before it passes beyond recall._
