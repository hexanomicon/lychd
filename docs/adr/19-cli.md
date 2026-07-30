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
  lifecycle. Extensions provide inert operation metadata only beneath `run`.
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
not public compatibility. The root verbs are `init`, `bind`, `start`, `stop`, `status`/`st`,
`logs`, `run`, and `del`; no snapshot, restore, selector shorthand, recovery, promotion, or
consent spelling is reserved by the grammar.

### Inscribe, then bind

`lychd init` inspects the host, plans canonical XDG layout, and establishes the lifecycle receipt
and root authority used later; it does not bind declarations or start services. Its `--dry-run`
renders the plan without LychD-managed mutation. Probes are bounded, though an inspected tool may
write its own metadata; therefore this is not a bit-for-bit host no-effect claim. Missing runtime
capabilities remain for `bind`; only an unsafe or impossible inscription blocks `init`.

Effectful `init` rejects effective UID 0 before Settings, host inspection, locks, or filesystem
effects; locks and requires the previewed plan unchanged; creates only planned paths, journals
confirmed progress, verifies convergence; and records exact device, inode, and mount authority for
dedicated Codex, Crypt, and Forge roots. It adopts an existing dedicated root only through that
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
native cancellation survives cleanup classification. `--uncaged` changes the compiled fileset,
not silent unit enablement. Planned binding truth belongs here; current host inventory belongs to
`status`.

### Start, stop, observe, and read

For `lychd start [TARGET]` and `lychd stop [TARGET]`, omission means the source-owned `system`
target. Direct control accepts only the help-advertised lifecycle subset and exact Scribe-owned
user units. Before an effect it holds the lifecycle lock and revalidates binding generation, unit
identity/state, and Vessel authority, refusing unknown, split, or ambiguous state. An active Vessel
must be controlled through its authenticated lifecycle port. That port is not in the production
composition, so both commands refuse rather than bypass the Vessel. Direct control neither runs
migrations nor evaluates application readiness nor executes a general dependency graph; graceful
admission closure, lease-aware draining, and force semantics are likewise not delivered.

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

`lychd run [OPERATION]` is the sole extension execution namespace. Registration contributes inert,
typed identity, inputs, authority/scope, mutation and consent characteristics, and progress/result
shape. It never grants a Click callback or arbitrary host execution. The delivered production
surface is catalogue and schema help; the default client refuses submission because no
Ward-authenticated CLI admission route is wired. Test-injected clients prove an adapter seam, not
production durability. Help does not imply a durable run, consent decision, or follow stream.
If catalogue load fails, core help remains and reports the failure without constructing ASGI.

### Delete only what the body can name

`lychd del` is init's confirmed destructive counterpart. It removes only authority proven by
receipt and live revalidation: familiar paths, units, object names, and mounts are not ownership.
Planning is staged and fingerprinted. Dry-run makes the same authority and blocker decisions
without deletion; an effect requires confirmation unless explicitly supplied, recomputes and
revalidates under the lifecycle lock, and supplies the displayed fingerprint to execution. Any
blocker suppresses every deletion effect.

The executor stops exact owned units, clears exact Scribe bindings, traverses receipted dedicated
roots without following symlinks or crossing mount authority, quarantines and re-attests names
before irreversible removal, and retains typed recovery evidence when restoration fails to
converge. It preserves unreceipted Podman objects, secrets, package installations, source
checkouts, and storage; it never calls `sudo`. Privileged Btrfs is a handoff: copyable arguments
appear only after the unprivileged plan is executable and mounted or receipt-backed unmounted
subvolume identity is attested, then execution waits for reconciliation. A blocked dry run or
incomplete effect exits 2.

### Shared target, recovery, and adapter laws

The delivered target source is fixed `OperatorTarget` enum/resolver, not a runtime extension
registry. `status` and `logs` accept its whole observable set; `start`/`stop` only its explicit
lifecycle subset. A target resolves to visible resources and exact ownership, never arbitrary
units, containers, paths, or tables. Adding one means source, authority mapping, help, tests, and
delivery evidence. Observation never confers actuation; dynamic targets and extension status are
Designed.

Whole-body capture and restoration remain Designed. A future inventory may project through status,
and mutation may use a typed operation or lifecycle target only after freeze, durability,
confirmation, and reconciliation law exists.

Importing or rendering the root does not construct Litestar, connect Postgres, start workers,
initialize models, or load the Altar. Host planning and observation call bounded services directly;
run help loads inert metadata lazily. ASGI, database, and Reactor consumers are hidden process
entrypoints, not alternative operator surfaces. A handler validates input, forms a typed request,
delegates, renders deterministic human or documented machine output, and translates typed refusal.
It does not reimplement lifecycle, authorization, persistence, deletion, or orchestration.

Read-only status and logs do not acquire lifecycle authority. Init, bind, direct control, and
deletion serialize under the lifecycle lock and revalidate the authority they consume. An active
Vessel is preferred authority; direct user-manager control serves only safe bootstrap or inactive
Vessel state. Recovery does not authorize an emergency root or raw substrate argument.

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
