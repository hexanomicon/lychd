---
title: 19. CLI
icon: material/console-line
---

# :material-console-line: 19. CLI

!!! abstract "Context and Problem Statement"
    Pulse is LychD's one host-side operator language: inscription, binding, bounded lifecycle
    control, observation, work admission, and retirement. It is a small local adapter over owned
    services, neither a daemon nor a catalogue of framework organs. Help owns current spelling;
    source, focused tests, and [State](../state-of-the-work.md#core-cli-rites) own delivery.

## Requirements

- The root grammar is closed: internal frameworks and extensions add no public root command.
- Commands name operator intent rather than Litestar, systemd, Podman, database, queue, or worker
  topology. Click validates and renders; typed services retain authority.
- One source-owned target vocabulary supplies observation, with a safely actuable subset for
  lifecycle. A future extension-operation namespace must remain beneath a single host-owned verb.
- A mutating `--dry-run` previews the same typed plan or request later admitted for effect.
- Help and host-local rites do not need ASGI, Postgres, or a Vessel. Effects revalidate exact
  ownership while serialized, and only documented machine projections are stable.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| One command per organ | Rejected | It leaks topology, expands without bound, and fragments safety and output contracts. |
| Extension-owned Click callbacks | Rejected | It allows namespace collisions and unreviewed host execution without common admission. |
| Closed verbs with typed targets and operations | Selected | It preserves one public language, authority boundary, and safe extension contribution point. |

## Decision Outcome

The installed command is **`lychd`**. `PulseGroup` owns the closed grammar and the exact `st`
alias for `status`; `lychd --help` is its executable inventory. No `lych` alias is promised.
Generated services and development machinery have hidden entrypoints, but hidden registration is
not public compatibility. The managed image uses the fixed process entrypoint
defined by [Backend](11-backend.md#process-and-listener-boundary). There is no host Vessel `serve`
entrypoint. Database commands retain their
lazy framework delegation. The root verbs are `init`, `bind`, `start`, `stop`, `status`/`st`,
`logs`, `access`, and `del`; no run-operation, snapshot, restore, selector shorthand, recovery, promotion, or
consent spelling is reserved by the grammar.

### Inscribe, then bind

`lychd init` establishes the layout and creation evidence that later commands rely on. It
inspects the host, plans canonical XDG layout, and records lifecycle and root authority without
binding declarations or starting services. `--dry-run` renders the same plan without
LychD-managed mutation. Probes are bounded, but an inspected tool may write its own metadata, so
the preview makes no bit-for-bit host no-effect claim. Only unsafe or impossible inscription
blocks `init`; missing runtime capabilities remain for `bind`.

Effectful `init` rejects effective UID 0 before Settings, host inspection, locks or filesystem
effects. It then takes the lifecycle lock and requires the previewed plan to remain unchanged.
Execution creates only planned paths, journals confirmed progress, verifies convergence, and
records exact device, inode and mount authority for dedicated Codex, Crypt and Forge roots. It adopts an existing dedicated root only through that
verified receipt. Shared XDG parents, source checkouts, foreign mounts, and the mounted
Phylactery are never recursively adopted. Dry-run is available under effective root because it
does not grant LychD mutation authority.

`lychd bind` compiles one immutable snapshot of Settings, extensions, Runes, runtime declarations,
secrets, and host foundation into the exact Scribe-owned fileset. Its dry run validates and renders
without LychD-managed mutation. Effectful bind reacquires the lifecycle lock, repeats preflight,
and requires trusted executables, effective generator, sites, desired and observed files, Settings
generation, and secret generation to remain equal before commit. Missing or unsafe sites block;
bind does not create the sites that init owns.

Apply provisions only authorized absent core secrets, commits the exact fileset, and reloads the
user manager once. A late failure reports confirmed progress rather than claiming no effect;
cancellation survives cleanup classification. Planned binding truth belongs here; current host
inventory belongs to `status`.

Bind compiles the container Vessel only. The former `--native-only` and `--uncaged` options are
usage errors before host inspection or effects. A retained native Vessel source or owned runtime
identity blocks bind, including locked revalidation. Bind cannot silently replace, remove, adopt
or migrate it. There is no host-native test profile; tests use the OCI verification path under
[Containers](08-containers.md#core-deployment-and-verification).

### Start, stop, observe, and read

For `lychd start [TARGET]` and `lychd stop [TARGET]`, omission means the source-owned `system`
target. Direct control accepts only the help-advertised lifecycle subset and exact Scribe-owned
user units. Before an effect it holds the lifecycle lock and revalidates binding generation, unit
identity/state, and Vessel authority, refusing unknown, split, or ambiguous state.

Before direct `start system` submits the owned Vessel start, a separate bounded observation of
its exact opposite fixed Vessel name must prove it quiescent. The counterpart may be loaded or
manager-attested not-found, but must be inactive/dead with no main/control process or pending job.
A successful exact property reply is required; failed, unknown, malformed, nonzero or transitional
observations refuse. This check follows owned-generation/state revalidation under the lifecycle
lock. It grants no ownership or authority to stop, replace or disable the counterpart and does not
change storage-only control or stop admission. The observation is not an atomic reservation of
the user manager namespace: other manager clients can race after the final check. Retiring the native
profile does not remove the possibility of an existing legacy counterpart.

Active container-Vessel lifecycle completion remains unavailable until its own authenticated
admission and exact container/service settlement are implemented and qualified. Current active
operations refuse before effects; they do not fall back to direct stop, a retired native launcher,
or another transport. The removed native stop protocol cannot certify container cleanup.

A retired native Vessel identity blocks lifecycle mutation and retirement; read-only inventory
may still name it so the operator can reconcile the existing installation separately. Removing
support does not grant ownership, stop authority or migration authority. The opposite-Vessel
start observation above remains a bounded legacy-conflict guard.

Direct control handles only its safe inactive bootstrap subset. It does not run migrations,
evaluate application readiness or execute a general dependency graph. Graceful admission closure,
lease-aware draining and force semantics need their own delivered container lifecycle contract.

`lychd status [TARGET]` and exact `st` inspect bounded local evidence. The default is `system`,
and fixed choices are published by help. `--json` is the stable machine result; Rich is for humans.
It inventories local ownership, exact user-unit state, declarations, storage, configuration,
bindings, workers, and locally visible runs. It does not attest HTTP/database health, migration
currency, queue readiness, durable run health, model warmth, or extension status; silence is not
proof.

`lychd logs [TARGET]` maps a target to exact owned units and takes one bounded journald tail; Click
validates and help advertises the line bound. It has no follow mode or joined container, run-event,
or Oculus evidence view.

### Admit work without ceding the language

`lychd access` explicitly displays the local Altar address, fixed operator username, and dedicated
HTTP Basic password to the invoking host operator. It reads the configured runtime credential or
its exact Podman secret through the trusted host adapter; it neither starts the Vessel nor opens
a browser. Ordinary help, status, logs, startup, generated units, and URLs never contain that
password. Replace its external secret and restart the Vessel to rotate access. This is a local
operator credential, not Ward enrollment or a remote CLI admission interface.

A future host-owned run-operation verb may become the sole extension execution namespace.
Registration would contribute inert, typed identity, inputs, authority/scope, mutation and consent
characteristics, and progress/result shape; it must never grant an extension-owned Click callback
or arbitrary host execution. No run-operation catalogue, schema help, injected client seam, or
Ward-authenticated CLI admission route is delivered today.

### Delete only what the body can name

`lychd del` retires an installation through init's separately confirmed destructive counterpart.
It may remove only what receipts and live revalidation prove it owns; familiar paths, units,
object names, and mounts are insufficient. Planning is staged and fingerprinted. Dry-run reaches
the same authority and blocker decisions without deleting. For effect, the command requires
confirmation unless explicitly supplied, recomputes and revalidates under the lifecycle lock, and
passes the displayed fingerprint to execution. Any blocker suppresses every deletion effect.

The executor stops exact owned units, clears exact Scribe bindings, traverses receipted dedicated
roots without following symlinks or crossing mount authority, quarantines and re-attests names
before irreversible removal, and retains typed recovery evidence when restoration fails to
converge. It preserves unreceipted Podman objects, secrets, package installations, source
checkouts, and storage; it never calls `sudo`. Privileged Btrfs is a handoff: copyable arguments
appear only after the unprivileged plan is executable and mounted or receipt-backed unmounted
subvolume identity is attested, then execution waits for reconciliation. A blocked dry run or
incomplete effect exits 2.

### Shared target, recovery, and adapter laws

One fixed `OperatorTarget` enum/resolver supplies delivered targets. `status` and `logs` can
observe its whole set, while `start`/`stop` accept only its explicit lifecycle subset. Each target
resolves visible resources and exact ownership, never arbitrary units, containers, paths, or
tables. Adding a target therefore requires source, authority mapping, help, tests, and delivery
evidence. Observation grants no actuation. Dynamic targets and extension status remain Designed;
this source is not a runtime extension registry.

Whole-body capture and restoration remain Designed. A future inventory may project through status,
and mutation may use a typed operation or lifecycle target only after freeze, durability,
confirmation, and reconciliation law exists.

Importing or rendering the root does not construct Litestar, connect Postgres, start workers,
initialize models, or load the Altar. Host planning and observation call bounded services directly;
run help loads inert metadata lazily. ASGI, database, and Reactor consumers are hidden process
entrypoints. The hidden `reactor recover-soft ACTIVATION_ID` is a bounded host recovery operation:
it verifies the exact durable activation record, current declarations and owned topology, and cold
Vessel and target Animator before clearing the fence. It accepts no arbitrary path or unit and
never stops or starts a service. [Orchestrator (23)](23-orchestrator.md) owns that recovery law;
this spelling adds no public root verb or stable machine projection. A handler validates input, forms a typed request,
delegates, renders deterministic human or documented machine output, and translates typed refusal.
It does not reimplement lifecycle, authorization, persistence, deletion, or orchestration.

Read-only status and logs do not acquire lifecycle authority. Init, bind, direct control, and
deletion serialize under the lifecycle lock and revalidate the authority they consume. An active
Vessel is preferred authority; direct user-manager control serves only safe bootstrap or inactive
Vessel state, when no active or retired Vessel requires a separately admitted lifecycle operation.
Recovery does not authorize an emergency root or raw substrate argument.

Normal dispatch installs structured logging before execution; effectful root rejection in init
comes earlier. Results go stdout; logs and diagnostics stderr. `status --json` alone is a stable
machine projection. Status 0 means help, successful read/effect, or unblocked dry run; 1 means
ordinary refusal, unavailable run transport, effectful root init, or concise ritual failure; 2
means Click usage, blocked `del --dry-run`, or partial deletion. Confirmation abort and native
cancellation remain nonzero. Ritual-wrapped bootstrap failure emits one `cli_command_failed` event;
ordinary CLI errors do not disclose a traceback.

## Consequences

!!! success "Positive"
    Operators gain one small language bounded by ownership proof; extensions describe work without
    acquiring roots or host callbacks; host recovery probes survive application-stack failure.

!!! failure "Negative"
    New targets and operations need typed evidence; human output stays non-API, while several verbs
    deliberately expose refusal or a narrower surface until authenticated runtime ports arrive.
