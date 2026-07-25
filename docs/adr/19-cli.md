---
title: 19. CLI
icon: material/console-line
---

# :material-console-line: 19. CLI: The Pulse

!!! abstract "Context and Problem Statement"
    LychD is primarily an always-on daemon, but the operator still needs one host-side control
    surface for inscription, binding, lifecycle, observation, and work. That surface must hide
    systemd, Podman, XDG geography, database machinery, and application-framework entrypoints
    without becoming an ever-growing catalogue of implementation organs.

    The command line is therefore designed as a small operator language. Its roots express stable
    intent; targets and registered operations carry the system's extensibility beneath them.

## Requirements

- **Closed Root Grammar:** The public root contains exactly `init`, `bind`, `start`, `stop`,
  `status`, `logs`, `run`, and `del`; `st` is an alias for `status`.
- **Orchestration Abstraction:** Operators act on LychD, not directly on Litestar, Alembic,
  systemd, Podman, SAQ, or internal Reactor entrypoints.
- **Progressive Detail:** The root help remains small. Target-specific and operation-specific help
  reveals detail only after the operator chooses a verb.
- **Shared Target Language:** `start`, `stop`, `status`, and `logs` resolve the same registered
  target identities rather than inventing command-specific selectors.
- **Extension Containment:** Extensions may contribute typed `run` operations and read-only
  `status` sections. They never add public root commands.
- **Plan/Apply Symmetry:** Every mutating command that offers `--dry-run` computes its preview
  through the same planner used for execution.
- **Bootstrap Independence:** Help, initialization, binding validation, deletion planning, and
  local inventory must not require a live ASGI application or reachable database.
- **Single Physical Will:** CLI actuation must obey the same orchestration and authority laws as
  web-originated actuation.
- **Truthful Delivery:** The stable grammar may be decided before every verb is useful, but the
  delivery ledger must distinguish implemented behavior from reserved command shape.

## Considered Options

!!! failure "Option 1: One command per organ"
    Expose `doctor`, `animators`, `database`, `serve`, `reactor`, consent commands, migration
    commands, and later every extension as separate roots.

    - **Pros:** Direct mapping from implementation module to command.
    - **Cons:** Teaches internal architecture instead of operator intent, fragments help, and gives
      every new organ pressure to expand the root namespace.

!!! failure "Option 2: Arbitrary extension command injection"
    Let each extension graft top-level commands into the Click group.

    - **Pros:** Maximum freedom for extension authors.
    - **Cons:** No stable grammar, collision-prone help, inconsistent authorization, and no common
      durability or observability path for extension work.

!!! success "Option 3: Closed verbs with target and operation registries"
    Keep eight stable roots. Extend observation through registered status sections and extend work
    through registered run operations.

    - **Pros:** A glanceable operator language, one target grammar, one work-admission path, and
      extension freedom without root-command sprawl.
    - **Cons:** Internal and extension capabilities must invest in typed registration instead of
      exposing their framework-native CLI directly.

## Decision Outcome

A native Click root with a **closed eight-verb grammar** is adopted as the **Pulse**:

```text
init
bind
start
stop
status (st)
logs
run
del
```

!!! note "Ruling: the binary is `lychd` (DOC-R1)"
    The installed command is **`lychd`** everywhere. There is no promised `lych` alias.

The roots name operator intent. Database migrations, foreground server launch, consent
adjudication, Host Reactor consumption, and framework-native utilities remain internal machinery.
They may support a public verb, but they do not appear as public roots.

### 1. Root Command Contract

#### `lychd init`

Establish the initial Codex, XDG layout, and lifecycle evidence. It does not bind or start the
system.

Before the filesystem tree, `init` concurrently runs and awaits bounded, read-only host probes.
Required Binding foundation covers a reachable systemd user manager, compatible Podman and an
available Quadlet user generator, cgroup v2, and the two exact Binding sites. SELinux mode, Btrfs
tooling/substrate, and the PostgreSQL data directory's current No-COW policy are visible but
optional: their absence or degradation does not make a safe inscription fail. Volatile readiness
evidence remains outside `LifecyclePlan`, so a host-state change cannot masquerade as filesystem
plan drift. `ready` is reserved for the aggregate Binding foundation; a directory is merely
`present` until its real-directory shape, current-user ownership, and write/search access prove it
`prepared`.

`lychd init --dry-run` renders the same initialization plan consumed by execution and performs no
host mutation. Its normal projection is a concise Rich tree rooted in the three canonical XDG tiers:
**Codex** is projected beneath `XDG_CONFIG_HOME` and includes both LychD configuration and host
Binding, **Crypt** is projected beneath `XDG_DATA_HOME` and includes the Phylactery, and **Forge**
is projected beneath `XDG_CACHE_HOME`. Common path prefixes collapse beneath those roots, routine
shared-host anchors are omitted, and external mounts or blockers remain explicit. Shared XDG,
Podman, and systemd anchors are bright blue because LychD may ensure an absent directory but never
owns the shared namespace; a cyan `will prepare` or green `present` suffix carries their
lifecycle state. LychD-dedicated paths remain cyan for planned creation and green for existing
state; yellow means removal and red means a blocker. The terminal summary counts exactly the
visible path nodes in the current projection, separating shared-anchor state from LychD path
state, so hidden intermediate anchors appear only with `--verbose`.
Every static path draws its concise description from the first
line of the adjacent attribute docstring in `system/constants.py`; dynamic Rune anchors reuse their
class docstrings, while generated sample files are explicitly marked as inactive examples. The
renderer source-mines this presentation text without duplicating it into an
authority registry, and safely omits it when installed source is unavailable. Generic existence
prose is not operator output. `--verbose` restores every inspected shared-host anchor. Apply
reacquires the lifecycle lock, requires the exact plan to remain unchanged,
rejects any creation outside it, journals each successful batch, and verifies final convergence
before the receipt's root-authority seal becomes the terminal commit. It then reinspects the
Binding sites and PostgreSQL storage, rendering only changed facts and the final Binding-foundation
verdict.

Existing state is never silently adopted. A successful non-dry initialization explicitly seals the
current device/inode identities of the three dedicated LychD roots—Codex, Crypt, and Forge—and
proves that each shares its parent's mount ID. The dry run names this adoption because it grants a
later confirmed `del` recursive authority over those roots, including content already inside the
dedicated LychD namespace. An unsafe existing root blocks the complete transaction even when a peer
root is absent. Initialization does not adopt shared XDG parents, source checkouts, model shelves,
foreign mounts, or the mounted Phylactery; those require their own authority and storage evidence.

#### `lychd bind`

Compile declared intent into host infrastructure. Binding owns two faces of one planner:

- `lychd bind --dry-run` loads and validates settings and Runes, resolves extensions and runtime
  declarations, checks host prerequisites and secret references, renders the proposed owned
  fileset in memory, and reports conflicts without mutation.
- `lychd bind` reacquires the lifecycle lock, revalidates the binding and Podman-secret
  generations, provisions only absent core secrets through bounded subprocesses, commits the owned
  fileset, and reloads the user manager once.

Binding expects `init` to have prepared both shared source sites. The Scribe validates them during
preview and again immediately before commit; it never recreates a missing Quadlet or plain
systemd-user directory.

This absorbs the former `doctor` command. Planned truth belongs to `bind --dry-run`; live truth
belongs to `status`.

#### `lychd start [TARGET]`

Start the whole declared installation when no target is given, or start one registered target.
Startup follows dependency, migration, readiness, and orchestration policy rather than exposing raw
systemd or Podman commands.

#### `lychd stop [TARGET]`

Drain and stop the whole installation or one registered target. Graceful admission closure and
lease-aware draining are the default; any future forced mode must remain explicit and separately
authorized.

#### `lychd status [TARGET]`

Report read-only installation, inventory, health, readiness, and drift truth. With no target it
provides a compact whole-system summary; a target selects deeper detail. `lychd st` is an exact
alias.

Animator capability/readiness, workers, services, storage, runs, bindings, and future snapshot
inventory are status jurisdictions rather than root commands. The available target vocabulary is
registry-backed and exposed by help; this ADR does not freeze every target spelling before its
provider exists.

#### `lychd logs [TARGET]`

Read or follow the operational history of the whole installation or one registered target. The
command may join journald, container output, run events, and Oculus evidence behind one projection;
the operator does not need to know which substrate owns each record.

#### `lychd run [OPERATION]`

Submit durable work through the system's ordinary admission, authority, consent, execution, and
observability path. `run` is both the core work surface and the **only public CLI extension
namespace**.

Every registered operation declares:

- a stable identity and typed arguments;
- the workflow or service it invokes;
- required capabilities and authority;
- mutation and consent characteristics; and
- progress/result projection.

The CLI contribution is inert metadata, not an executable Click callback. The living control plane
resolves the operation identity to a host-owned workflow or service after admission. This prevents
an extension from turning command registration into arbitrary host execution.

Extensions may add `run` operations, but never root commands. An operation must not bypass
Dispatcher, Orchestrator, Ward/HitL, durable run identity, or traceability merely because it began
at the CLI.

The exact shorthand for an ordinary natural-language prompt and the final catalogue of core
operations remain owned by the operation registry and its implementation evidence, not guessed by
this ADR.

#### `lychd del`

Permanently remove a LychD installation. This is the deliberately destructive counterpart to
`init`, not Python syntax and not a vague directory unlink.

`lychd del --dry-run` inventories and groups every proposed action before mutation: managed
services, bindings, containers, Codex, cache, Crypt state, snapshots, and the Phylactery. Execution
also accounts for LychD-managed secrets. It must stop LychD workloads first, require unambiguous
confirmation, avoid following symlinks or crossing unknown mounts, and verify what remains
afterward.

The deletion preview preserves its ordered safety stages. Within filesystem-oriented inventory it
reuses the same Codex, Crypt, and Forge XDG topology as `init`; presentation hierarchy never changes
deletion authority.

Destructive intent does not turn a familiar name into ownership. A container, pod, secret, package,
or other object without immutable creation provenance appears in the plan as **preserved**, not
silently adopted for deletion. This can leave installation residue until the corresponding
creation receipts exist, but it cannot widen deletion authority by convention.

The dedicated Codex, Crypt, and Forge roots are the deliberate exception only after a successful
`init` has recorded their exact identities. `del` revalidates those identities and traverses them
through no-follow descriptors without crossing mount IDs. Missing, corrupt, replaced, or drifted
root authority blocks before unbinding.

A blocker anywhere in the confirmed plan suppresses every deletion effect and every copyable root
handoff. Required privileged work remains visible as inventory, but the operator receives exact
commands only when the complete unprivileged plan is otherwise executable.

When an inspected mount or subvolume requires elevation, LychD never invokes `sudo` itself. It
retains the canonical filesystem UUID, subvolume UUID, subvolume ID, source mapping, and mount
target needed to finish later, then prints a handoff composed only from trusted absolute tool
paths. Resume requires that complete identity to match. A source checkout is never recursively
deleted merely because `del` was launched through `uv run`. When trustworthy installer provenance
identifies an isolated CLI installation, its removal is the final stage; otherwise `del` reports
what remains and the exact package-manager command rather than guessing.

### 2. The Shared Target Registry

`start`, `stop`, `status`, and `logs` consume one typed target resolver. A target identifies an
operator-visible resource, not an arbitrary systemd unit, container name, filesystem path, or
database table.

The registry must support:

- deterministic identity and help;
- read-only status and log projection;
- optional lifecycle capability for start/stop;
- extension ownership and collision rejection; and
- authority checks at the effect boundary.

An extension may contribute a status section for resources it owns. It cannot acquire actuation
merely by becoming observable, and it cannot create a ninth root command.

### 3. Snapshot and Recovery Boundary

Whole-body capture and restoration remain designed and are not assigned a new root command.
Snapshot inventory naturally belongs under `status`; capture or recovery may later be admitted as
a registered operation or lifecycle target only after ADR 07's freeze, durability, confirmation,
and reconciliation contract is implemented.

This ADR intentionally does **not** promise `snapshot`, `restore`, or
`start snapshot:<id>` syntax. The eight-root grammar is settled; the safest composition beneath it
is not.

### 4. Bootstrap and Runtime Separation

Importing the CLI root does not construct the Litestar application, connect to Postgres, start
workers, initialize Pydantic AI, or load the Altar.

- Host-local planning and observation use domain/system services directly.
- Live operations enter the public control plane through bounded clients or shared application
  services without exposing a framework CLI.
- The ASGI server, migration runner, Reactor consumer, and other service entrypoints remain
  package-private or hidden process entrypoints used by generated units.

This is a process boundary, not a second “light” application composition.

### 5. Thin Command Doctrine

Command handlers are orchestration edges, not policy engines:

- parse and validate CLI input;
- resolve a typed target or operation;
- delegate to domain/system services;
- render deterministic human output or a documented machine projection; and
- return stable non-zero behavior on failure.

No CLI handler reimplements lifecycle, authorization, persistence, or orchestration law already
owned elsewhere.

### 6. Arbitration Doctrine

Observation and actuation have different authority:

- `status` and `logs` are read-only and never acquire lifecycle authority.
- `start`, `stop`, and lifecycle-bearing `run` operations first use the living Vessel's control
  plane when it is authoritative. Direct host actuation is permitted only through the documented
  dead-Vessel or bootstrap path.
- `init`, `bind`, and `del` remain host lifecycle operations. Their planners and locks prevent
  concurrent effect paths; their execution still obeys ownership, mount, and service-state
  evidence.
- A future Mundane Anchor may be a separate internal recovery executable, but its public entrance
  must fit this root grammar. Recovery necessity is not permission to add emergency roots.

### 7. Structured Output and Logging

Human output should be grouped by operator jurisdiction and lead with the result. Commands that are
useful to automation should also offer a stable structured projection rather than requiring ANSI
or prose scraping.

CLI mode bootstraps the shared structured logging pipeline before effects. Logs use semantic event
identities and retain correlation with target, operation, run, and transition identities without
placing lore in machine fields. Human terminals retain the event as the primary line; redirected
or configured machine logs use JSON. Command results remain on stdout while Structlog and stdlib
diagnostics use stderr, so `status --json` stays parseable. Unexpected ritual failures emit one
semantic `cli_command_failed` event before the concise human error.

### 8. Public-Surface Transition

Earlier revisions exposed implementation-shaped roots:

- `doctor` is folded into `bind --dry-run` and `status`;
- `animators` is folded into `status`;
- `destroy` is superseded by `del`;
- `database` and `serve` become internal lifecycle machinery;
- `runs approve/deny` remains an Altar/API consent concern and internal service operation;
- `reactor consume` remains a generated-service entrypoint, not operator vocabulary; and
- `list`, `promote`, `rebirth`, `restore`, `rollback`, and `snapshot` are not reserved roots.

The removed operator-shaped commands are not registered as compatibility aliases; in particular,
there is no supported `destroy` command. Hidden `serve`, `database`, and `reactor` process
entrypoints exist only for framework or generated-service machinery. Any future temporary
compatibility alias must be hidden, emit a migration notice, and have a removal boundary; it does
not enlarge the canonical public grammar.

### 9. Implementation Status

xDDD permits doctrine-first specification, but State owns the current evidence. At the time this
decision was established:

| Public root | Delivery boundary |
| :--- | :--- |
| `init` | Inscription and its side-effect-free planner have focused tests. |
| `bind` | Preview and apply share typed Codex, host, Reactor, mode, and secret preflight plus one desired-fileset planner. First-bind Reactor units are proved by that plan rather than required to pre-exist. |
| `start` | The direct bootstrap/dead-Vessel path starts the exact Vessel only when every sibling owned unit is inactive; full live-control coverage remains absent. |
| `stop` | The direct dead-Vessel path stops every exact owned unit in one bounded transaction. An active Vessel is refused until its authenticated lifecycle port is wired; there is no graceful public drain yet. |
| `status` / `st` | Local ownership, unit, Animator declaration, storage, configuration, binding, worker, and run projections plus JSON and alias behavior exist. HTTP/database/migration/queue/run/warmth truth and extension sections do not. |
| `logs` | Bounded exact-unit journald reads exist. Follow mode and joined container, run-event, and Oculus history do not. |
| `run` | Callback-free Core/extension registration carries typed execution, mutation, consent, progress, result, input, scope, and provenance metadata. Help works; the default client refuses execution until a Ward-authenticated submission route exists. |
| `del` | A confirmed fingerprinted planner/executor retires exact units, supports a filesystem- and subvolume-identity-bound Btrfs handoff, clears exact bindings and verified dedicated roots, and replans after each stage. Unreceipted Podman objects, secrets, package, and checkout remain preserved. |

The [State of the Work](../state-of-the-work.md#core-cli-rites) must be updated with source and
focused tests as each boundary lands. Presence in `--help` alone is not delivery.

### Consequences

!!! success "Positive"
    - **Glanceability:** A new operator can understand the whole public grammar from one help page.
    - **Extensibility without sprawl:** Extensions gain a rich work and observation surface without
      fragmenting the root namespace.
    - **Substrate independence:** The CLI names intent while services hide Litestar, systemd,
      Podman, database, and observability mechanics.
    - **Operational symmetry:** The same target identity can be started, stopped, observed, and
      traced.

!!! failure "Negative"
    - **Registry investment:** Targets, operations, help, authority, and projections require shared
      typed registries rather than direct Click grafting.
    - **Migration cost:** Existing implementation-shaped commands must be folded or hidden without
      falsifying current delivery.
    - **Deliberate restraint:** Useful internal capabilities may exist before the public verb that
      safely composes them.
