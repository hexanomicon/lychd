---
title: 19. CLI
icon: material/console-line
---

# :material-console-line: 19. CLI

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
- **Typed Host Authority:** Initialization and Binding share one host-foundation inspection;
  binding effects consume only its exact verified executable and site authorities.
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

Before the filesystem tree, `init` concurrently runs and awaits bounded, read-only host probes
through the same typed host-foundation inspection used by `bind`. The inspection keeps its
immutable readiness report beside the exact trusted-tool discoveries that produced it. Required
Binding foundation covers a reachable systemd user manager, compatible Podman and the effective
Podman user generator, cgroup v2, and the two exact Binding sites. A fully verified inspection can
refine into one `BindingFoundation` token containing the resolved path plus device/inode identity
of `systemctl`, Podman, and the user generator, together with the path plus device/inode identity
of both sites; callers never re-resolve those authorities from `PATH`.

A trusted executable's resolved file and complete ancestor chain must remain under system
authority, closed to group/other writes, and unwritable by the invoking user. Generator discovery
follows systemd's user-generator directory priority and honors higher-priority empty,
non-executable, or `/dev/null` masks. A Binding site is `prepared` only when it is a real
non-symlink directory owned by the invoking UID, owner and effective read/write/search access hold,
group/other writes are closed, and no ancestor is writable by another principal without an
accepted system-authority- or invoking-UID-owned sticky-directory boundary. Initialization creates
a missing site path chain with mode `0700`; `bind` never creates one and initialization never
chmods an existing shared namespace.

SELinux mode, Btrfs tooling/substrate, and the PostgreSQL data directory's current No-COW directory
policy are visible but optional: their absence or degradation does not make a safe inscription
fail. `SELinux: enforcing` proves only the runtime mode, not that every generated `:Z` relabel will
succeed. A `+C` observation proves directory policy for newly created extents, not retroactive
conversion of existing PostgreSQL files. Volatile readiness evidence remains outside
`LifecyclePlan`, so a host-state change cannot masquerade as filesystem plan drift. `ready` is
reserved for the aggregate Binding foundation; ordinary layout existence remains `present`.

`lychd init --dry-run` renders the same initialization plan consumed by execution and performs no
LychD-managed host mutation. Missing or incompatible systemd, Podman, Quadlet, or cgroup
capabilities are visible as later `bind` blockers; they do not prevent a safe layout preview or
inscription. Only lifecycle-plan blockers, including an unsafe or uncreatable Binding site, govern
`init`. Real initialization rejects effective UID 0 before Settings load, host inspection,
planning, locking, or filesystem effects; dry-run inspection remains available under effective
root so a broken host can still be diagnosed without granting mutation authority. Its bounded
external probes may let an inspected tool maintain its own runtime metadata;
therefore the terminal claim is deliberately “No LychD-managed changes made,” not a claim about
undocumented internals of every host executable. Its normal projection is
a concise Rich tree rooted in the three canonical XDG tiers:
**Codex** is projected beneath `XDG_CONFIG_HOME` and includes both LychD configuration and host
Binding, **Crypt** is projected beneath `XDG_DATA_HOME` and includes the Phylactery, and **Forge**
is projected beneath `XDG_CACHE_HOME`. Common path prefixes collapse beneath those roots, routine
shared-host anchors are omitted, and external mounts or blockers remain explicit. Shared XDG,
Podman, and systemd anchors are bright blue because LychD may ensure an absent directory but never
owns the shared namespace; a cyan `will create` or green `present` suffix carries their
lifecycle state. LychD-dedicated paths remain cyan for planned creation and green for existing
state; yellow means removal and red means a blocker. The terminal summary counts exactly the
visible path nodes in the current projection, separating shared-anchor state from LychD path
state, so hidden intermediate anchors appear only with `--verbose`. The default tree contains paths,
states, and operationally relevant qualifiers without explanatory prose.
Every static path draws its verbose description from the first
line of the adjacent attribute docstring in `system/constants.py`; dynamic Rune anchors reuse their
class docstrings, while generated sample files are explicitly marked as inactive examples. The
renderer source-mines this presentation text without duplicating it into an
authority registry, and safely omits it when installed source is unavailable. Generic existence
prose is not operator output. `--verbose` restores every inspected shared-host anchor and all
source-owned path descriptions. Apply
reacquires the lifecycle lock, requires the exact plan to remain unchanged,
rejects any creation outside it, journals each successful batch, and verifies final convergence
before the receipt's root-authority seal becomes the terminal commit. It then reinspects the
Binding sites and PostgreSQL storage, rendering only changed facts and the final Binding-foundation
verdict. Ordinary directory batches carry their pre-install device/inode identities into that
journal; the recorder never grants a replacement pathname the original creation's authority.

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
  fileset in memory, and reports conflicts without LychD-managed mutation. Podman presence probes
  may maintain Podman's own rootless runtime metadata.
- `lychd bind` reacquires the lifecycle lock, revalidates the complete host foundation, binding
  generation, and Podman-secret generation, provisions only absent core secrets through bounded
  subprocesses, commits the owned fileset, and reloads the user manager once.

The preflight refines the shared readiness inspection into the exact `BindingFoundation` used for
planning. Its attested Podman capability is injected into secret reconciliation, its two attested
sites into Scribe, and its attested systemctl capability into the user-manager port. Apply reruns
the complete preflight under the lifecycle lock and requires the new token to equal the preview
before any secret or binding effect; a changed executable, effective generator, or site identity
is plan drift, while a site that is no longer prepared fails the repeated preflight.

Settings, extensions, and Runes use command-snapshot isolation: the composition root loads one
`RuneRegistry`, and the pure Animator hydrator consumes that same snapshot rather than opening the
Codex again. The resulting declarations and registry live in one immutable
`BindingCommandSession`; its Settings generation is retained as immutable serialized data and
materialized through validation separately for preview and locked revalidation. Compilation
produces one immutable `BindRequest`, and preview plus locked
apply consume that same request. A concurrent declarative-source edit does not silently rewrite
the already rendered plan; the next `lychd bind` invocation observes it. Live host tools, Binding
sources, and secret presence are separate authority domains and are explicitly revalidated under
the lifecycle lock.

The binding plan separately fingerprints the observed files and the exact desired paths, bytes,
and ownership receipt; both generations must still match at commit. A settled bind preserves
existing file and receipt identities. If secret creation or binding commit succeeded before a
later failure, the terminal error and structured log retain that confirmed progress instead of
presenting the operation as effect-free. Binding failures distinguish a pre-mutation rejection,
clean rollback, indeterminate binding state, and a committed generation whose systemd reload
failed.

Terminal cancellation is not flattened into an ordinary command failure. After logging and
attaching the classified progress, bind re-raises `KeyboardInterrupt` or `SystemExit` itself—even
when Scribe first wrapped that signal in a transaction error after rollback. Scribe settles every
workspace peer before surfacing a cleanup interruption; the native signal carries a typed cause
that distinguishes an already committed generation from exact rollback or indeterminate state.

Binding expects `init` to have prepared both shared source sites. The Scribe validates them through
the same mode/owner/ancestor law during preview and again immediately before commit; it never
recreates a missing Quadlet or plain systemd-user directory.

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
root authority blocks before unbinding. Final root, child-directory, and file retirement first
moves the live name to an unguessable same-parent quarantine with atomic no-replace semantics,
re-attests it, and deletes only there. Mismatches and failed deletes are restored without
clobbering; a blocked restoration surfaces the exact retained quarantine as typed recovery
evidence and blocks later retries until reconciled. The Codex checkpoint and lifecycle receipt are
excluded from ordinary traversal. `del` detaches the Codex root first, transfers those two
authorities to exact private sibling backups, confirms empty-root retirement, and only then
finalizes the backups. Pre-confirmation failure or terminal cancellation restores root and
authorities; post-confirmation failure retains typed backup recovery. Subsequent plans detect
sibling root/authority recovery markers and block until they are reconciled.

This protects `del` from observable or accidental namespace races. A malicious process with the
same host UID remains outside this boundary because it already holds equivalent authority to
delete or replace the same user-owned paths. The stricter initialization rollback law is separate
and does not become weaker through this destructive, explicitly confirmed command.

A blocker anywhere in the confirmed plan suppresses every deletion effect and every copyable root
handoff. Required privileged work remains visible as inventory, but the operator receives exact
commands only when the complete unprivileged plan is otherwise executable.

When an exact mounted Btrfs Phylactery requires elevation, LychD never invokes `sudo` itself. Its
live mount target, source device, filesystem UUID/root, source mapping, subvolume UUID, and
subvolume ID must agree before LychD checkpoints that identity and prints trusted absolute unmount
and ID-deletion commands.

An unmounted Btrfs target has a narrower authority path. It is eligible only when a version-2
lifecycle receipt proves that the same `init` transaction created the exact PostgreSQL subvolume
and recorded its device, inode, canonical subvolume UUID, and subvolume ID. Live `lstat` and
`btrfs subvolume show` must match that receipt, and the covering Btrfs filesystem must expose a
canonical filesystem UUID, source device, and safe mounted top-level anchor. LychD then checkpoints
the combined identity and prints only
`btrfs subvolume delete --subvolid ID TOP_LEVEL`; no unmount step exists for this case. A
version-1 receipt, pre-existing or later-discovered subvolume, absent probe/tool, unsafe mapping, or
identity drift blocks globally. Resume re-attests the checkpoint and proceeds only after the
subvolume is absent.

A source checkout is never recursively deleted merely because `del` was launched through
`uv run`. When trustworthy installer provenance identifies an isolated CLI installation, its
removal is the final stage; otherwise `del` preserves the package and reports that installer
provenance is unavailable rather than guessing a removal command.

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
- `init`, `bind`, `start`, `stop`, `del`, Host Reactor consumption, and explicit uncaged runtime
  transitions share one interprocess lifecycle authority. Their planners or typed no-effect lock
  rejection prevent concurrent effect paths; execution still obeys ownership, mount, and
  service-state evidence.
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
| `bind` | Preview and apply share typed Codex, Reactor, secret, and host-foundation preflight plus one desired-fileset planner. The verified foundation pins trusted tools and both prepared sites; apply requires the whole token plus binding and secret generations to remain equal under the lifecycle lock. |
| `start` | The direct bootstrap/dead-Vessel path starts the exact Vessel only when every sibling owned unit is inactive; full live-control coverage remains absent. |
| `stop` | The direct dead-Vessel path stops every exact owned unit in one bounded transaction. An active Vessel is refused until its authenticated lifecycle port is wired; there is no graceful public drain yet. |
| `status` / `st` | Local ownership, unit, Animator declaration, storage, configuration, binding, worker, and run projections plus JSON and alias behavior exist. HTTP/database/migration/queue/run/warmth truth and extension sections do not. |
| `logs` | Bounded exact-unit journald reads exist. Follow mode and joined container, run-event, and Oculus history do not. |
| `run` | Callback-free Core/extension registration carries typed execution, mutation, consent, progress, result, input, scope, and provenance metadata. Help works; the default client refuses execution until a Ward-authenticated submission route exists. |
| `del` | A confirmed fingerprinted planner/executor retires exact units, supports the live-attested mounted Btrfs handoff and the receipt-v2-attested init-created unmounted subvolume handoff, clears exact bindings and verified dedicated roots, and replans after each stage. Unreceipted Podman objects, secrets, package, and checkout remain preserved. |

The [State of Work](../state-of-the-work.md#core-cli-rites) must be updated with source and
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
