---
title: State of the Work
icon: material/list-status
---

# State of the Work

LychD is **pre-alpha**. This page is the canonical account of what repository evidence supports,
what still needs a named operator receipt, and what remains design.

The proved foundation is local, loopback-oriented, single-user, and one LychD control process in
the repository-test profile. Real systemd, rootless Podman, GPU, model, and inference-engine
combinations still need named operator receipts. Remote or multi-tenant operation, native
observability, general resource-aware scheduling, semantic evolution, and federation are
horizons—not current product claims.

LychD names the software body under construction. The Lich names the recurrent whole the Work is
meant to sustain—not any one model.

Inside the current repository-test envelope, evidence covers typed configuration, core CLI
behavior, deployment planning, local runs and bounded chained single-approval consent, the current agent and dispatch
paths, safe runtime-transition protocols, and structured logging configuration. The records below
bind every part of that foundation to its exact proof and limit.

[The Prophecy](./index.md) names the destination; this page names what can answer now.

Go directly to:

- [Attempt the bounded first-life rite](./summoning.md)
- [Inscription and embodiment](#inscription-and-embodiment)
- [Persistence, execution, and consent](#persistence-execution-and-consent)
- [Animation and orchestration](#animation-and-orchestration)
- [Altar and observability](#altar-and-observability)
- [Authority and artifacts](#authority-and-artifacts)
- [Evolution and federation](#evolution-and-federation)

## How to read this page

- **Available** — repository evidence supports the behavior inside the boundary written in its
  record. This does not mean stable, production-ready, remote-safe, or architecture-complete.
- **Operator validation** — the software path and contract tests exist, but the named real
  host, hardware, model, or engine receipt is still missing. Missing code never receives this label.
- **Partial** — a useful verified subset exists. Read the literal **Not yet** boundary before
  deciding whether it meets your use case.
- **Designed** — architecture or doctrine exists, but users must not rely on the behavior yet.
- **Experimental** — a runnable LychD path exists and intentionally carries an unstable support
  contract. An upstream beta or empty package does not qualify.
- **External** — another project owns and versions the subject. The record states what LychD can
  interoperate with and which authority remains outside LychD.

**Pre-alpha** is the project maturity and support envelope, not a seventh delivery state. An
accepted ADR records a decision; it does not prove delivery.

Classification starts with the exact subject. Upstream products are External. A LychD-owned
integration receives its own delivery label. Among LychD subjects, no useful runnable slice means
Designed; an intentionally unstable runnable slice means Experimental; an incomplete useful slice
means Partial; a complete software contract missing one named environment receipt means Operator
validation; and Available is reserved for the whole boundary claimed by that record. No current
LychD subject on this page qualifies as Experimental.

## Current evidence envelope

Repository tests cover the local memory-profile composition and important unit, integration, and
web contracts. The real `create_app()` plus Postgres startup, run, and shutdown test is still an
unconditional skipped skeleton. Test evidence therefore proves only the boundary named by each
record; it is not a production deployment receipt.

- **Source:** [Application factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py),
  [web lifespan](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/lifespan.py),
  and [Altar service assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/altar_services.py)
- **Verification:** [Memory-profile composition and explicit Postgres receipt gap](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [ADR 03 — Quality](./adr/03-quality.md) and [ADR 04 — Testing](./adr/04-testing.md)

## Inscription and embodiment {#inscription-and-embodiment}

### Rune configuration loading {#rune-configuration-loading}

**State:** Available

**Proved now:** Typed TOML Runes load from their declared hierarchy with validated, immutable
filesystem provenance.

**Boundary:** This proves configuration parsing and topology, not a CLI rite, generated host unit,
or running service.

**Evidence**

- **Source:** [Rune configuration loader](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/runes/loader.py)
- **Verification:** [Rune loading and provenance tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/runes/test_loader.py)
- **Law:** [ADR 12 — Configuration](./adr/12-configuration.md)

### Core CLI rites {#core-cli-rites}

**State:** Partial

**Proved now:** Public help exposes the closed `init`, `bind`, `start`, `stop`, `status`, `logs`,
`run`, and `del` grammar; `st` resolves to `status` without becoming a ninth root. `init` and
`bind` have planners that perform no LychD-managed mutation. Their bounded external observations
may still let Podman or another inspected tool maintain its own runtime metadata. A real `init`
rejects effective UID 0 before loading Settings, probing the host, or acquiring effect authority;
its dry run remains available for read-only diagnosis. `init` revalidates and consumes its exact
plan, rejects
unplanned creations, journals partial progress, proves convergence before its terminal seal, and
records device/inode plus parent-mount authority for the dedicated roots. Its default projection
collapses the exact plan beneath Codex/config, Crypt/share, and Forge/cache XDG tiers, with Binding
inside Codex and the Phylactery inside Crypt; `--verbose` restores routine host anchors and
source-owned path descriptions without changing the plan. Shared host anchors have a distinct role
color and explicit planned/present state,
so their materialization is not presented as recursive LychD ownership. Initialization also
concurrently awaits one typed host-foundation inspection for systemd user-manager reachability,
Podman/Quadlet/cgroup-v2 compatibility, SELinux, Btrfs, both Binding sites, and observed PostgreSQL
No-COW directory policy. The report retains the exact trusted executable discoveries behind it:
resolved files and their complete ancestor chains must remain owned by UID 0 or on a
kernel-reported read-only mount and
unwritable by the invoking user, while effective user-generator discovery honors systemd priority
and masks. Those volatile facts remain outside lifecycle equality; after apply, Binding sites and
storage are reinspected. Shared anchors say `will create`/`present`, verified sites say
`prepared`, and only the aggregate next phase says `ready`. Missing Binding-site path components
are created with mode `0700`; an existing site must be a non-symlink current-UID directory with
owner and effective read/write/search access, no group/other writes, and no unsafe writable
ancestor. SELinux `enforcing` remains a mode observation rather than proof that a particular `:Z`
relabel succeeds, and `+C` proves policy for new extents rather than conversion of existing files.
The first line of each static path's adjacent attribute
docstring—and each dynamic Rune class docstring—owns the concise description shown beside its node
in the verbose projection; generic existence prose remains internal. Binding refines the same inspection into one typed
foundation carrying the resolved path plus device/inode identity of systemctl, Podman, the user
generator, and both Binding sites. Preview injects those values into the secret, Scribe, and
user-manager ports; apply rechecks the whole foundation plus binding and secret generations under
the lifecycle lock before any effect. Settings, extensions, and the Rune filesystem are loaded once
per bind command into one immutable session; Animator hydration consumes that same registry
snapshot instead of reopening the Codex. One declaration compiler merges the Settings-owned core
ports with every `PortReserver` Rune before hydration; bind, status, the Host Reactor, and the web
runtime all consume that policy, and the live `AnimatorRegistry` receives compiled declarations
rather than reparsing TOML. Web preauthorization synchronization also consumes the existing process
Rune snapshot, so one startup cannot split Animator and consent truth across two filesystem reads.
Transmutation receives the session `Settings` explicitly instead of
reading the process cache. The retained bind session stores Settings as an immutable serialized
generation and materializes a freshly validated tree for preview and locked revalidation, so
between-phase mutation cannot bypass section validators. Each extension contributor sees an isolated deep copy of settings
and declarations behind tuple collections. Contributor-returned containers are copied
before admission, so the typed additive seam cannot mutate core output or later contributors.
The Scribe requires initialization-prepared Quadlet and plain-user-unit sites during planning and
immediately before commit rather than silently creating them. Bind supplies the approved
`AttestedBindingSites`, and Scribe compares each newly pinned site descriptor with that exact
device/inode before staging and re-attests both sites before a no-op return. Every planned write set carries a
mandatory base compare-and-swap over the exact authority bytes and every source recorded by that
receipt, including missing sources at an intentionally absent site; the caller's observed token and
the exact desired-byte generation are additional guards. Stable no-follow observations derive those
tokens, settled reconciliation preserves inode/mtime identity, and a failed later bind phase reports
any confirmed secret creation or committed binding generation plus rejected, cleanly rolled-back,
or indeterminate commit state. Terminal cancellation is logged with that progress and then
re-raised as `KeyboardInterrupt` or `SystemExit`, including through Scribe's rollback wrapper.
Scribe-managed generations are replaced, removed, and rolled back
through descriptor-relative atomic exchange/quarantine operations pinned to the prepared site and
workspace identities. Staged inode/content is re-attested before installation, final-gap writers are
restored or preserved, and binding-site or workspace pathname substitution cannot redirect a
transition. Indeterminate recovery workspaces remain on disk—including after rollback interruption
by `KeyboardInterrupt` or `SystemExit`—and successful flat cleanup refuses a replaced workspace
pathname. Empty Scribe authority deletion is part of the same generation-guarded transaction, so
post-inspection manifest drift cannot enlarge destructive authority. Workspace cleanup settles
every peer before re-raising a native terminal signal, with a typed cause
that preserves whether the public generation committed, rolled back exactly, or remains
indeterminate. Existing and newly created layout paths use no-follow directory descriptors;
rollback authority remains
pinned to exact parent/device/inode creations through receipt persistence. Missing directories
are attested under private staging names and installed with atomic no-replace semantics. Their
creation identities pass directly into the receipt; rollback quarantines before comparison,
restores replacements, and never pathname-deletes a published quarantine because Linux cannot
condition `rmdir` on the attested inode. The typed failure names that recovery location. A shared
journal-bound creation session now also owns Codex files, Rune anchors and samples, and configured
Reactor directories. It never infers ownership from precomputed absence: directory race losers are
excluded, text-file parents must already exist, and complete file candidates are file-`fsync`ed,
no-clobber published, descriptor-relative re-attested, and parent-`fsync`ed before the receipt
callback. Clean interruption rollback preserves native terminal signals, concurrent replacements
are never unlinked, and Codex returns the exact committed ledger rather than reconstructing it from
public names. The just-created Btrfs target is created and inspected as
`/proc/self/fd/<inherited-parent>/<leaf>`
after the parent matches the transaction's earlier device/inode observation. The child remains
pinned while No-COW is applied through its descriptor and re-attested before journaling. Its
canonical substrate ancestry is retained after identity drift, exceptional preparation, or
receipt failure, with creation identity logged for an attested recovery handoff rather than unsafe
pathname deletion. Failed, timed-out, and terminally interrupted creation commands first classify
the pinned leaf as absent, present-but-unattested, or indeterminate. Only proven absence after a
nonterminal command failure permits directory fallback; residue is retained without adopting a
post-failure UUID/ID that could belong to a racer. Bootstrap-safe `status`/`st` can
render exact local ownership, unit, declaration,
and mount inventory as human output or JSON, degrading split or corrupt authority instead of
guessing. `logs` reads a bounded journal tail over exact owned units. The direct dead-Vessel
`start` path refuses a split runtime, while direct `stop` covers every exact owned unit. The
callback-free `run` registry carries typed
execution, mutation, consent, progress, result, input, scope, and provider metadata. `del` renders
one fingerprinted staged plan, confirms it, retires exact owned units, pauses with retained evidence
for a live-attested mounted Btrfs handoff or, more narrowly, an init-created unmounted PostgreSQL
subvolume whose version-2 lifecycle receipt device/inode and UUID/ID still match live evidence. The
unmounted path also requires a canonical covering-filesystem UUID/device and safe mounted top-level
anchor before it emits an ID-based privileged command; a missing receipt or any drift blocks
globally. Deletion removes exact bindings and receipt-verified dedicated roots through
descriptor-relative, mount-ID-checked traversal. Root, child, and file retirement uses an atomic
random-name quarantine beneath the pinned parent, descriptor re-attestation, no-clobber restoration
of mismatches, and typed retained-quarantine recovery on a blocked restore. Observable/accidental
namespace races are contained; malicious mutation by the same host UID is explicitly outside this
boundary because that UID already has equivalent deletion authority. Codex ordinary entries retire
while the privileged-handoff checkpoint and lifecycle receipt remain protected. The Codex root is
then detached; both authorities move to private sibling backups and are finalized only after root
retirement is confirmed. Failure or cancellation restores them with the root when possible, and
typed sibling recovery markers block later plans instead of disappearing from inventory.
Execution replans between irreversible stages. The installed entrypoint initializes the shared
Structlog pipeline before dispatching any verb.

**Boundary — Not yet:** `status` does not probe HTTP or database readiness, migration result, queue
health, durable runs, or model warmth; extension-contributed status sections are not delivered.
`stop` refuses an active Vessel until its authenticated lifecycle port exists. `logs` neither
follows nor joins Podman, run-event, and Oculus records. `run` discovers operations but its default
client refuses submission until a Ward-authenticated Vessel route exists. `del` deliberately
preserves Podman containers, pods, secrets, the installed package, and the source checkout because
their immutable creation provenance is absent or separately owned; unknown unit or mount truth
blocks rather than guesses. No real systemd/Podman startup, shutdown, deletion, or GPU receipt is
claimed by repository tests.

**Evidence**

- **Source:** [CLI assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__main__.py),
  [lifecycle plan view](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/lifecycle_view.py),
  [operator commands](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/operator.py),
  [run projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/run.py),
  [run-operation schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/operations.py),
  [deletion command](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/deletion.py),
  [bind transaction](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/bind.py),
  [Scribe transaction](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scribe/transaction.py),
  [Scribe atomic storage](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scribe/storage.py),
  [binding preflight](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/binding_preflight.py),
  [binding-site authority](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/binding_sites.py),
  [trusted host-tool discovery](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/host_tools.py),
  [host-readiness probes](https://github.com/hexanomicon/lychd/tree/main/src/lychd/system/readiness),
  [lifecycle receipt](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/lifecycle/receipt.py),
  [operator services](https://github.com/hexanomicon/lychd/tree/main/src/lychd/system/operator),
  and [lifecycle services](https://github.com/hexanomicon/lychd/tree/main/src/lychd/system/services/lifecycle)
- **Verification:** [Focused CLI command tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py),
  [lifecycle tree tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_lifecycle_view.py),
  [CLI run tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_run.py),
  [CLI deletion tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_deletion.py),
  [operator tests](https://github.com/hexanomicon/lychd/tree/main/tests/unit/system/operator),
  [run-operation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_operations.py),
  [bind-transaction tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_bind.py),
  [Scribe safety tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scribe.py),
  [binding-preflight tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_binding_preflight.py),
  [trusted host-tool tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_host_tools.py),
  [host-readiness tests](https://github.com/hexanomicon/lychd/tree/main/tests/unit/system/readiness),
  [initialization transaction tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_initialization.py),
  [layout tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_layout.py),
  [lifecycle-receipt tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_lifecycle.py),
  [deletion safety tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_deletion.py),
  and [Btrfs checkpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_deletion_storage.py)
- **Law:** [ADR 19 — CLI](./adr/19-cli.md)

### Public release artifact chain {#public-release-artifact-chain}

**State:** Designed

**Proved now:** The source tree declares a Hatch-built Python distribution, a Containerfile, and a
tag-triggered workflow that can build and push a Vessel image.

**Do not expect yet:** No maintained receipt pairs this revision as an anonymously installable
PyPI package and pullable GHCR image from one tag and commit. A 2026-07-22 audit found only the
placeholder `lychd==0.0.1` on PyPI while source declares `0.0.2`; an anonymous pull of the
configured `ghcr.io/hexanomicon/lychd:latest` was denied, and no immutable tag or digest pairs it
with the source wheel. That audit did build and isolated-install the source wheel, expose the real
CLI tree, and complete `lychd init`, but a one-time manual pass is not a public release or a
maintained packed-artifact receipt. Promotion needs one version owner, automated wheel/image
inspection, matching public artifacts, and a named clean-host install/start/reply/stop receipt.

**Evidence**

- **Source:** [Package version](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__about__.py)
  and [default Vessel image](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/server.py)
- **Version:** [Distribution and version declarations](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml),
  [Vessel build](https://github.com/hexanomicon/lychd/blob/main/Containerfile),
  [tag-triggered image workflow](https://github.com/hexanomicon/lychd/blob/main/.github/workflows/build.yml),
  and [public PyPI project](https://pypi.org/project/lychd/)
- **Law:** [ADR 17 — Packaging](./adr/17-packaging.md) and
  [ADR 18 — Evolution](./adr/18-evolution.md)

### Deployment-plan compilation and materialization {#deployment-plan-materialization}

**State:** Available

**Proved now:** LychD can compile Soulstone and extension intent—including per-Animator targets,
the conservative/default conflict graph, and compatible Coven aggregates—into validated
Quadlet/systemd plans and materialize the declared files through the Scribe boundary.

**Boundary:** Generated unit intent is not evidence that systemd or Podman started the workload on
a real host. Runtime graph attestation and compound target actuation are tracked separately below;
this compilation record does not pre-claim them.

**Evidence**

- **Source:** [Deployment transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py)
  and [Scribe materialization](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scribe/facade.py)
- **Verification:** [Transmutation contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute.py),
  [extension contribution contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_contributor.py),
  and [Scribe rendering tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scribe_render.py)
- **Law:** [ADR 08 — Containers](./adr/08-containers.md),
  [ADR 10 — Privilege](./adr/10-privilege.md), and
  [ADR 12 — Configuration](./adr/12-configuration.md)

### Runtime actuation and mediated Host Reactor protocol {#host-reactor-protocol}

**State:** Available

**Proved now:** The software protocol covers durable inbox claim, validation, Scribe-owned loaded
graph attestation, one compound Animator-target transaction, exact target-and-service world
observation, cancellation-safe settlement, exact-prior-world compensation, crash recovery,
readiness inversion, bounded `systemctl` clients, and host-owned outcome journaling. A client
timeout terminates and reaps the local process; before submission it is a typed no-effect decline,
while after submission the actuator still settles and classifies the systemd-owned job before
acceptance, compensation, or containment. Fresh intents carry the exact target capability as well
as its Animator; legacy records without that field are accepted only when the Animator has one
unambiguous configured capability. Host consumption shares the interprocess lifecycle lock with
the other mutating rites and invokes only an injected, root-controlled absolute `systemctl`
discovery. The explicit uncaged Systemd composition holds that lock across attestation,
observation, effects, and compensation; contention surfaces as a typed, verified no-effect
precondition.

**Boundary:** Repository protocol tests and an isolated private systemd user-manager receipt prove
the generated relation surface and a conflicting target switch with real systemd job ordering.
That hermetic receipt uses inert services; it is not the operator's live
Quadlet/Podman/GPU-host receipt. A `.declined` record proves no new effect, `.restored` proves the
exact prior world, `.contained` preserves a fresh physically uncertain outcome across application
restart, and an uncertain crash-reclaimed record remains `.processing`; `.rejected` is reserved
for an invalid delivery rather than physical classification. Startup remains fenced on
`.processing` or `.contained`. General repair of an arbitrary physical world remains outside the
contract.

**Evidence**

- **Source:** [Host Reactor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/reactor.py),
  [runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py),
  [runtime topology attestor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime_topology.py),
  [lifecycle lock](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/lifecycle/lock.py),
  [private Reactor composition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/commands.py),
  and [trusted host-tool discovery](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/host_tools.py)
- **Verification:** [Reactor recovery tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_reactor.py),
  [runtime action tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py),
  [loaded-topology attestation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_topology.py),
  [isolated real-systemd target receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_target_transaction.py),
  [cross-environment lock tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_lifecycle.py),
  [entrypoint composition tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py),
  and [host-tool attestation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_host_tools.py)
- **Law:** [ADR 10 — Privilege](./adr/10-privilege.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### systemd user and rootless Podman embodiment {#systemd-podman-embodiment}

**State:** Operator validation

**Proved now:** LychD has a generated unit contract and a mediated host actuator for its declared
Linux deployment shape.

**Receipt needed:** A maintained receipt naming Linux distribution and kernel, systemd and Podman
versions, the generated Animator/Coven targets and conflict edges, loaded-source attestation, a
forward compound switch, exact-prior-world compensation, crash recovery, startup, and shutdown.
GPU and model validation remain separate receipts.

**Evidence**

- **Source:** [Runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py)
  and [runtime topology attestor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime_topology.py)
- **Verification:** [Runtime protocol tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py),
  [loaded-topology attestation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_topology.py),
  and [pending llama.cpp fixture boundary](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/llamacpp/README.md)
- **Rite:** [The Summoning](./summoning.md)
- **Law:** [ADR 08 — Containers](./adr/08-containers.md) and
  [ADR 10 — Privilege](./adr/10-privilege.md)

### Whole-body snapshot and restore {#whole-body-snapshot-restore}

**State:** Designed

**Proved now:** Filesystem services prepare the Btrfs subvolume and no-copy-on-write substrate on
which the snapshot design can be built.

**Do not expect yet:** LychD does not coordinate freeze, database and code snapshot, restore, or
post-restore reconciliation as one whole-body ritual.

**Evidence**

- **Source:** [Btrfs preparation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/btrfs.py)
  and [layout service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/layout.py)
- **Verification:** [Filesystem layout tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_layout.py)
- **Law:** [ADR 07 — Snapshots](./adr/07-snapshots.md)

### Tomb untrusted execution {#tomb-untrusted-execution}

**State:** Designed

**Proved now:** The security law separates future untrusted execution from LychD's trusted,
rootless core.

**Do not expect yet:** There is no Tomb queue, executor, credential, policy, Landlock, or `nono`
integration. The trusted core is not Tomb evidence.

**Evidence**

- **Law:** [ADR 09 — Security](./adr/09-security.md)

## Persistence, execution, and consent {#persistence-execution-and-consent}

### Phylactery first-light persistence {#phylactery-first-light}

**State:** Partial

**Proved now:** Run, step, session, consent, and checkpoint persistence shapes exist, and focused
memory-profile tests prove important run-ledger behavior.

**Boundary — Not yet:** The conditional PostgreSQL run-ledger module is skipped in the standard
suite, and the real production-factory lifecycle test is an unconditional skeleton. There is no
transactional outbox or full memory/Postgres adapter parity.

**Evidence**

- **Source:** [First-light migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0001_phylactery_first_light.py),
  [pinned Pattern-manifest migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0002_pin_pattern_manifest.py),
  [checkpoint adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/checkpoints.py),
  and [run ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/ledger.py)
- **Verification:** [Run-ledger contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py),
  [skipped PostgreSQL run-ledger receipt gap](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py),
  and [production-factory receipt gap](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [ADR 06 — Persistence](./adr/06-persistence.md)

### Topology-A local run execution {#topology-a-local-runs}

**State:** Available

**Proved now:** One Vessel process can admit, claim, execute, cancel, settle, and project live run
events with replay fencing inside the repository-test envelope. Each admitted run pins the
validated immutable Pattern manifest it began with. Runtime node evidence carries a stable
occurrence identity for the entered/settled/waiting/failed phases of one attempt; Dispatcher grant
evidence carries that occurrence plus the issued grant/lease identity; Orchestrator transition
evidence carries the same run/occurrence correlation through its observed phase.

**Boundary:** This does not claim a transactional event outbox, separate-worker truth, replayable
multi-process streaming, or federation. Replay retention is bounded, but live per-subscriber queues
are currently unbounded; slow-subscriber overflow and backpressure are not governed.

**Evidence**

- **Source:** [Run engine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py),
  [process-local event broker](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/events.py),
  and [run Ghoul](https://github.com/hexanomicon/lychd/blob/main/src/lychd/ghouls/runs.py)
- **Verification:** [Run-engine transition tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py),
  [run execution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_perform_run.py),
  [event replay and resynchronization tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_events.py),
  and [HTTP event-stream tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sse.py)
- **Law:** [ADR 14 — Workers](./adr/14-workers.md),
  [ADR 22 — Dispatcher](./adr/22-dispatcher.md),
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md),
  [ADR 24 — Graph](./adr/24-graph.md),
  [ADR 28 — Workflow](./adr/28-workflow.md), and
  [ADR 29 — Observability](./adr/29-observability.md)

### Pydantic AI 1.25.1 cognitive adapter {#pydantic-ai-v1-adapter}

**State:** Available

**Proved now:** LychD constructs typed agents and runs its Bridge workflow through the exact
`pydantic-ai-slim==1.25.1` contract with serializable state.

**Boundary:** This does not claim Pydantic AI v2 durability, v2 stream events, GraphBuilder, or
automatic usage propagation.

**Evidence**

- **Source:** [Agent factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py),
  [workflow contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py),
  and [Bridge workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/bridge_chat.py)
- **Verification:** [Agent factory tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_factory.py),
  [Bridge graph tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_bridge_chat_graph.py),
  and [state serialization tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_state_serializable.py)
- **Version:** [Exact dependency declaration](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
  and [resolved dependency lock](https://github.com/hexanomicon/lychd/blob/main/uv.lock)
- **Law:** [ADR 20 — Agents](./adr/20-agents.md) and [ADR 24 — Graph](./adr/24-graph.md)

### Pydantic AI v2 migration {#pydantic-ai-v2-migration}

**State:** Designed

**Proved now:** The architectural direction accepts a migration while the repository records the
exact v1 baseline from which compatibility must be measured.

**Do not expect yet:** v2 messages, toolsets, deferred events, durability capabilities, and graph
contracts are not installed LychD behavior.

**Evidence**

- **Current baseline:** [Dependency declaration](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
  and [resolved lock](https://github.com/hexanomicon/lychd/blob/main/uv.lock)
- **Law:** [ADR 20 — Agents](./adr/20-agents.md) and [ADR 24 — Graph](./adr/24-graph.md)

### Graph stasis and consent re-admission {#graph-stasis-consent}

**State:** Partial

**Proved now:** Focused tests cover logical parking, bounded chained single-approval rounds,
memory-profile simulated restart, reconciliation, idempotent settlement, and graph re-admission.
Each model round may request one supported approval; a resumed run may enter another bounded round.

**Boundary — Not yet:** This is not a Postgres Consent-plus-Checkpoint restart receipt. Multiple
approval calls in one model response are rejected; after verdict commit plus enqueue failure,
web and CLI suppress the live retry, leaving startup reconciliation as the automatic repair path.

**Evidence**

- **Source:** [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py),
  [stasis adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/stasis.py),
  and [consent ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/ledger.py)
- **Verification:** [Consent resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_consent_resume.py),
  [startup reconciliation tests](https://github.com/hexanomicon/lychd/blob/main/tests/cortex/test_reconcile.py),
  and [web consent endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_consent_endpoint.py)
- **Law:** [ADR 25 — Human in the Loop](./adr/25-hitl.md)

### Durable in-app Attention {#durable-attention}

**State:** Designed

**Proved now:** Bridge can project pending consent cards and counts from consent records.

**Do not expect yet:** There is no owned Attention inbox, acknowledgement contract, live retry,
expiry or escalation policy, redacted notification delivery, or external channel.

**Evidence**

- **Source:** [Bridge consent projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py),
  [client consent card](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/ConsentCard.svelte),
  and [shared Altar attention](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/AltarShell.svelte)
- **Verification:** [Consent-card endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_consent_endpoint.py)
  and [SSE refresh tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sse.py)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 25 — Human in the Loop](./adr/25-hitl.md)

## Animation and orchestration {#animation-and-orchestration}

### Animator dispatch spine {#animator-dispatch-spine}

**State:** Available

**Proved now:** The current catalog, matching, grant issue and settlement, and lease-aware dispatch
behavior are covered by focused repository tests.

**Boundary:** `AnimatorRegistry` still combines several ownership roles. `GrantLease.expires_at`
exists, but the ledger does not enforce it; current leases are context-managed, not renewable
temporal leases.

**Evidence**

- **Source:** [Animator registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/registry.py),
  [Dispatcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/dispatcher.py),
  and [lease ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/leases.py)
- **Verification:** [Registry tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py),
  [Dispatcher tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_dispatcher.py),
  [lease tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_leases.py),
  and [dispatch decision table](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_dispatch_decision_table.py)
- **Law:** [ADR 22 — Dispatcher](./adr/22-dispatcher.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Extension activation and contributions {#extension-activation-contributions}

**State:** Partial

**Proved now:** Explicit built-in selection and current concrete Rune, portal, runtime, and Quadlet
contributions can be assembled and tested.

**Boundary — Not yet:** Registration brackets an extension identifier but contributed records do
not retain that owner. Collision attribution, full lifecycle ownership, and a stable public SDK
remain absent.

**Evidence**

- **Source:** [Extension manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/manager.py),
  [contribution context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py),
  and [built-in catalog](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/catalog.py)
- **Verification:** [Built-in catalog tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_catalog.py),
  [portal contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_portals.py),
  [registry contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py),
  and [Quadlet contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_contributor.py)
- **Law:** [ADR 05 — Extensions](./adr/05-extensions.md)

### llama.cpp integration {#llamacpp-integration}

**State:** Operator validation

**Proved now:** LychD implements llama.cpp runtime planning, static and router connectors, model
discovery, capability derivation, load/unload control, and contract tests.

**Receipt needed:** A named llama.cpp image digest and revision, model and quantization, GPU and
driver, runtime flags, systemd/Podman host, load result, inference result, and unload result.

**Evidence**

- **Source:** [llama.cpp runtime adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/llamacpp.py)
  and [llama.cpp control plane](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/llamacpp/control_plane.py)
- **Verification:** [Runtime adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py)
  and [llama.cpp control tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_llamacpp_control.py)
- **Law:** [ADR 22 — Dispatcher](./adr/22-dispatcher.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### vLLM integration {#vllm-integration}

**State:** Operator validation

**Proved now:** LychD implements a vLLM runtime plan, OpenAI-compatible connector, model and
capability derivation, and focused adapter tests.

**Receipt needed:** A named vLLM image digest and revision, model, GPU and driver, authoritative
`exec` arguments, systemd/Podman host, readiness, inference, and shutdown result.

**Evidence**

- **Source:** [vLLM runtime adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/vllm.py)
- **Verification:** [vLLM planning and connector tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py)
- **Law:** [ADR 22 — Dispatcher](./adr/22-dispatcher.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### SGLang integration {#sglang-integration}

**State:** Operator validation

**Proved now:** LychD implements an SGLang runtime plan, OpenAI-compatible connector, model
derivation, and focused adapter tests.

**Receipt needed:** A named SGLang image digest and revision, model, GPU and driver, authoritative
`exec` arguments, systemd/Podman host, readiness, inference, and shutdown result.

**Evidence**

- **Source:** [SGLang runtime adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/sglang.py)
- **Verification:** [SGLang planning and connector tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py)
- **Law:** [ADR 22 — Dispatcher](./adr/22-dispatcher.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### ExLlamaV3 through TabbyAPI {#exllamav3-tabbyapi}

**State:** Operator validation

**Proved now:** LychD has a concrete TabbyAPI-backed runtime, control plane, connector, Soulstone,
registration path, digest/revision boundary, and contract tests for ExLlamaV3.

**Receipt needed:** A named TabbyAPI and ExLlamaV3 revision, NVIDIA GPU and driver, EXL3 model and
quantization, cache mode, GPU split, runtime flags, load/inference/unload results, and measured VRAM.

**Evidence**

- **Source:** [ExLlamaV3 control plane](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/exllamav3/control_plane.py),
  [connector](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/exllamav3/connector.py),
  [Soulstone schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/soulstones/exllamav3.py),
  [registration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/exllamav3/register.py),
  and [runtime adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/exllamav3.py)
- **Verification:** [ExLlamaV3 contract tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_exllamav3.py)
- **Law:** [ADR 22 — Dispatcher](./adr/22-dispatcher.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Declared conflict topology and systemd target switching {#declared-conflict-topology}

**State:** Available

**Proved now:** Soulstone `conflict_domains` validate into an undirected incompatibility graph.
Omission on a dedicated non-resident becomes the conservative `default-exclusive` wildcard;
explicit `[]` alone declares coexistence. Bind compiles one target per Animator plus inspectable
conflict edges, rejects internally conflicting Covens, and aggregates compatible Animator targets.
Bind and live registry load also reject any Soulstone whose registered adapter synthesizes no
capability, because phase-one planner activity truth is capability-derived while host attestation
is unit-derived.
The switch policy selects only the target's exact active neighbors from that same graph. Before one
compound target request, the actuator validates the intent closure, exact Scribe ownership and
source paths, installed/loaded LychD target namespace, target/service/Coven relations, unit-file
state, and current target-and-service world. Every `systemctl` client has a configurable positive
timeout and is terminated, killed if necessary, and reaped when that budget expires. Failure
handling still waits for relevant systemd jobs and classifies the settled whole world before
accepting success or exact restoration; timing out the client never impersonates cancellation of a
systemd-owned job.

**Boundary:** Repository evidence proves compilation, attestation, request shape, and recovery
semantics. A hermetic private user-manager receipt additionally proves the generated relation
surface and real systemd ordering during a conflicting target switch with inert services; it does
not prove the operator's live Quadlet/Podman/GPU host. An explicit empty conflict set remains an
operator assertion of safe coexistence, not measured capacity admission. The separate
[systemd and Podman embodiment](#systemd-podman-embodiment) record owns that live-host receipt.

**Evidence**

- **Source:** [Concurrency schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/concurrency.py),
  [conflict compiler](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/conflicts.py),
  [bind compiler](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/bind_compilation.py),
  [Animator registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/registry.py),
  [target transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py),
  [switch policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/policies.py),
  [runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py),
  and [runtime topology attestor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime_topology.py)
- **Verification:** [Conflict-schema and topology tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_conflicts.py),
  [target-generation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute.py),
  [switch-policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_policies.py),
  [compound transaction tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py),
  [loaded-topology attestation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_topology.py),
  and [isolated real-systemd target receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_target_transaction.py)
- **Law:** [ADR 08 — Containers](./adr/08-containers.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Safe runtime transitions {#safe-runtime-transitions}

**State:** Available

**Proved now:** Admission closure, lease drain, serialized transition plans, readiness convergence,
loaded-graph attestation, one compound per-Animator target transaction, settled-world
classification, exact-prior-world compensation, typed cancellation restoration, and fail-closed
containment have focused software-protocol tests. A proved restoration reopens the manager barrier;
in mediated mode, an uncertain fresh host effect becomes a durable `.contained` startup fence,
while uncertain crash recovery remains `.processing`. The Host Reactor refuses all new work when
containment already exists and stops the current batch before claiming another intent as soon as
fresh containment or unresolved recovery appears.

**Boundary:** This proves the bounded software protocol, not a swap on a real GPU or
capacity-optimal model selection. A failed soft in-runtime model load has no trustworthy rollback
and requires contained operator recovery. General repair of an arbitrary host world remains an
operator responsibility.

**Evidence**

- **Source:** [Orchestrator manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/manager.py),
  [actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/actuator.py),
  [arbiter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/arbiter.py),
  [runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py),
  and [runtime topology attestor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime_topology.py)
- **Verification:** [Manager transition tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_manager.py),
  [actuator tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_actuator.py),
  [arbiter serialization tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_arbiter.py),
  [runtime transaction tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py),
  [Host Reactor recovery tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_reactor.py),
  [loaded-topology attestation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_topology.py),
  and [orchestration integration tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_orchestrator.py)
- **Law:** [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Resource-aware VRAM and topology scheduling {#resource-aware-scheduling}

**State:** Designed

**Proved now:** ADR 23 provides a policy seam, and the current `EvictIdlePolicy` has deterministic
tests for its deliberately simple behavior.

**Do not expect yet:** The current declared-conflict policy selects exact active graph neighbors
and prices only their count. This is an incompatibility graph, not a capacity solver: it does not
know VRAM capacity, model footprint, load time, topology, bandwidth, LRU, refit profiles, tier
substitution, or transition peaks. `persistent_resident` and explicit coexistence are not capacity
admission.

**Evidence**

- **Source:** [Current eviction policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/policies.py),
  [transition schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/schema.py),
  and [concurrency intent](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/concurrency.py)
- **Verification:** [Current policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_policies.py)
  and [current matrix behavior](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_matrix_solver.py)
- **Law:** [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

## Altar and observability {#altar-and-observability}

!!! success "Canonical client foundation"
    ADR 15's client architecture is present: a Svelte 5 runes-only source tree, SvelteKit static
    SPA build, Node/npm lock and commands, native CSS system, generated Litestar OpenAPI types,
    runtime-validated semantic JSON SSE, and a versioned `/api/v1` surface. Litestar serves the
    compiled fallback and assets; Granian remains the only production server. Tailwind,
    project-owned PostCSS, Jinja Altar templates, HTMX markup and client behavior, Alpine,
    `litestar-vite`, and LychD's direct `litestar-htmx` dependency are absent from this surface.
    Litestar 2.24 still resolves `litestar-htmx` as an unused transitive framework dependency;
    removing that installed helper requires the future Litestar 3 migration, not a second LychD
    frontend.

    Focused Python and Svelte tests prove the contract and static shell, not a complete
    operator-browser acceptance pass. There is not yet a Playwright receipt over the production
    factory, durable cross-process browser events, Android client, or useful implementation behind
    every named instrument.

### Bridge conversation and consent surface {#bridge-surface}

**State:** Partial

**Proved now:** The Svelte Bridge consumes generated `/api/v1` contracts for local sessions,
message submission, pending consent cards and decisions, and inspection. Per-run events arrive as
versioned semantic JSON SSE and closed GenUI descriptors. Status, node occurrence, Dispatcher grant,
and Orchestrator transition are distinct event classes rather than one overloaded activity label.
A successful admission response carries the server-minted Run, exact Pattern, Loom, Orb, and
evidence-capture identities; the client does not guess them. Completed turns append their visible
agent reply and Pydantic AI `new_messages()` suffix together, normalizing every provider hop to
the owning LychD run so one completed turn remains indivisible. The next turn reads only that
completed session model history, applies whole-turn and character governors, rebinds Context after
the actual capability grant, and passes the validated bounded messages to Pydantic AI with a
resolved context-window usage fence. A parked consent chain is reserved whole and prior settled
history is re-bounded under the capability acquired on resume. Display turns never become model history.
A Bridge admission retains the user turn under the server-minted run identity before publishing
the queue hop, so a fast worker cannot settle a reply ahead of its prompt.
A cursor-bound run snapshot replaces live text, status, and descriptors after an explicit resync or
detected numeric gap; duplicate and gapped events are not projected speculatively. The
selected-session snapshot also exposes active Run identities, exact Pattern/Orb links, and
current process-local projections. Snapshot reconstruction preserves separate current-node,
dispatch, and transition occurrence identities, so a Bridge route remount or hard browser reload
neither hides an acknowledged body crossing nor falsely joins evidence from two occurrences. Focused Python and
component tests cover admission, consent ordering, terminal replay, descriptor safety, snapshot
replacement, reload reconstruction, delayed-admission navigation ownership, and
terminal-refresh navigation races.

**Boundary — Not yet:** There is no complete production-factory receipt, durable cross-process
event or token delivery, general multi-approval round, Attention contract, or external
notification channel. Active-run reconstruction is process-local and does not recover token bytes
lost with a process. Run admission uses ordered user-turn retention before broker publication plus
failure compensation, rather than one database transaction/outbox spanning the session, run, and
broker. Text is the implemented command modality; the designed record-then-send voice
path and continuous voice mode are not delivered.

**Evidence**

- **Source:** [Bridge controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py),
  [client Bridge](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/BridgeView.svelte),
  [Context assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/context.py),
  [Bridge Pattern](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/bridge_chat.py),
  [session history](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/sessions.py),
  [run admission](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py),
  and [event contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/contracts.py)
- **Verification:** [Bridge behavior tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge.py),
  [consent endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_consent_endpoint.py),
  [Context tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_context.py),
  [consent-resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_consent_resume.py),
  [session-history tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sessions.py),
  [run-admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py),
  [event-stream tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sse.py),
  and [Bridge component tests](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/BridgeView.test.ts)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md),
  [ADR 21 — Context](./adr/21-context.md),
  [ADR 22 — Dispatcher](./adr/22-dispatcher.md),
  [ADR 24 — Graph](./adr/24-graph.md),
  [ADR 25 — Human in the Loop](./adr/25-hitl.md),
  [ADR 28 — Workflow](./adr/28-workflow.md), and
  [ADR 29 — Observability](./adr/29-observability.md)

### Nexus transition board {#nexus-transition-board}

**State:** Partial

**Proved now:** The Svelte Nexus consumes typed Coven state and transition plans from `/api/v1`,
labels preview as non-binding, submits explicit swap intents, and follows process-local tickets to
settled or failed outcomes over semantic JSON SSE. A separate bounded process-local transition
journal projects the latest observed phase for both run-origin and operator-origin requests,
including run, occurrence, physical-transition, and compensation correlation where those records
exist, orders updates by latest observation, and exposes each capability probe's own `checked_at`
rather than presenting response-construction time as fresh hardware truth. Direct transition URLs
resolve and refresh the same latest observation. The ticket store retains
terminal endpoint and SSE reconnect truth for a 60-second process-local window, retires it only
after expiry, and refuses capacity rather than evicting active or fresh-terminal tickets.

**Boundary — Not yet:** It has no general resource truth. Tickets and transition observations have
no durable owner, complete history, cross-process retention, or restart recovery; the production
lifespan also lacks an operator-browser receipt. It is not a general resource, queue, GPU, VRAM,
topology, thermal, or hardware-pressure dashboard. Nexus has no broad binding inventory,
configuration mutation, proposal workflow, or separate Bindings instrument; Configuration remains
the owning authority.

**Evidence**

- **Source:** [Nexus controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/nexus.py),
  [client Nexus](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/NexusView.svelte),
  and [process-local ticket store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/tickets.py)
- **Verification:** [Nexus board and endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_nexus.py)
  and [ticket-retention tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_tickets.py)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Loom workflow instrument {#loom-workflow-views}

**State:** Partial

**Proved now:** The Svelte Loom browses exact immutable Pattern revisions, presents their semantic
station/permission outline as the primary score, and exposes the pinned checkpoint schema and
manifest digest. Optional Mermaid source is a secondary local diagram lens. The same typed Pattern
manifest and source are available through `/api/v1`, and ambiguous unversioned browser deep links
fail rather than selecting a revision silently. The unversioned catalogue API remains an
intentional current-revision lookup.

**Boundary — Not yet:** It is a view over the fixed workflow registry, not a general Weaver editor,
workflow mutation surface, Svelte Flow drafting canvas, or production-browser receipt.

**Evidence**

- **Source:** [Loom controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/loom.py),
  [client Loom](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/LoomView.svelte),
  and [workflow registry contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py)
- **Verification:** [Loom rendering tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_loom.py)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 28 — Workflow](./adr/28-workflow.md)

### Orb instrument {#orb-instrument}

**State:** Partial

**Proved now:** `/orb/{run_id}` returns and renders one selected Run as an ordered,
bounded evidence list. The snapshot identifies its exact Pattern revision when the pinned manifest
still validates, labels process-local versus durable-best-effort capture, exposes the ledger head
and current page boundary separately, interleaves explicit gaps, and links recorded transition
requests to Nexus. Safe events have URL-stable selection, bounded pagination, a narrow-screen
detail sheet, and an explicit failure-presence notice without exposing private diagnostics.

**Boundary — Not yet:** There is no authorized run-list query, live Orb tail, graph-shaped
evidence view, durable native Oculus ingestion/read model, cross-process completeness, health
query, artifact custody, annotation, or multi-run field. Token deltas are intentionally omitted
from retained structural evidence. The focused Altar does not expose a separate Reliquary route.

**Evidence**

- **Source:** [Orb controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/orb.py),
  [Orb contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/contracts.py),
  and [client Orb](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/OrbView.svelte)
- **Verification:** [Orb endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb.py)
  and [Altar route tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
- **Topic:** [Orb](./divination/altar/orb.md)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md),
  [ADR 24 — Graph](./adr/24-graph.md), and
  [ADR 29 — Observability](./adr/29-observability.md)

### Structured logging configuration {#structured-logging}

**State:** Available

**Proved now:** The shared logging builder produces tested human-readable and JSON
stdlib/Structlog output. The installed CLI entrypoint invokes the same bootstrap before Click
dispatch, with a settings-independent fallback that keeps help and recovery verbs available when
operator configuration is malformed; Litestar composition consumes its injected Settings through
the same builder. Direct and stdlib diagnostics share level policy and remain on stderr, preserving
stdout for stable command results. Human rendering retains the event as the primary line, JSON
renames it to `message`, and unexpected `init`/`bind` failures emit one semantic command-failure
event. Granian server/access and SQLAlchemy engine/pool logger families are explicitly covered.

**Boundary:** Shared configuration does not prove that every lifecycle effect emits a complete
semantic audit event. This record also does not prove trace storage, OpenTelemetry export,
capture-class redaction, retention, resource correlation, or Oculus.

**Evidence**

- **Source:** [Logging configuration and bootstrap helper](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/logging.py)
- **Verification:** [Logging configuration and output tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_logging.py)
  and [CLI bootstrap tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py)
- **Law:** [ADR 29 — Observability](./adr/29-observability.md)

### Native Oculus {#native-oculus}

**State:** Designed

**Proved now:** The observability law makes LychD's own evidence model and Altar surface canonical.
A dormant Phoenix-specific export adapter has a narrow direct unit test; it is external-Eye
compatibility evidence, not native Oculus delivery.

**Do not expect yet:** The telemetry class is not installed by current application or extension
composition. There is no native ingestion, durable query/read model, retention path, or
native-Oculus-backed Svelte read service. The delivered Orb is a bounded selected-Run projection
over currently available records, not native Oculus.

**Evidence**

- **Source:** [Dormant Phoenix export adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/telemetry.py)
  and [current application assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py)
- **Verification:** [Narrow telemetry capture test](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_telemetry.py)
- **Topic:** [Oculus](./sepulcher/extensions/oculus.md)
- **Law:** [ADR 29 — Observability](./adr/29-observability.md)

### Phoenix {#phoenix-eye}

**State:** External

**Proved now:** LychD can generate an optional Phoenix Eye service contribution. New configuration
uses the `lychd-phoenix` identity; an explicitly configured legacy service name remains loadable.

**External owner and boundary:** [Arize owns Phoenix](https://github.com/arize-ai/phoenix). LychD
does not own its lifecycle or state, does not require it for Oculus, and does not currently prove
application trace export to it. The sample `latest` image is not a reproducible receipt.

**Evidence**

- **Source:** [Phoenix configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/config.py)
  and [Quadlet contribution](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/contributor.py)
- **Verification:** [Generated-unit golden tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py)
  and [bound fileset tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_bind_fileset.py)
- **Law:** [ADR 29 — Observability](./adr/29-observability.md)

## Authority and artifacts {#authority-and-artifacts}

### Local Sigil and scope authority {#local-sigil-authority}

**State:** Partial

**Proved now:** Typed Sigils, scope grammar, guards, and consent preauthorization checks are
implemented and exercised on the current loopback bootstrap surface.

**Boundary — Not yet:** The default Sigil is fixed `magus:*`; there is no caller authentication,
object authorization, delegation, revocation, tenant isolation, or remote exposure. Naive expiry
is accepted and then fails against aware UTC in memory, and expiring preauthorization is not
rechecked immediately before a protected effect after waiting.

**Evidence**

- **Source:** [Sigil identity](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/sigil.py),
  [scope grammar](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/scopes.py),
  [scope middleware](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/middleware.py),
  [guards](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/guards.py),
  and [preauthorization Runes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/runes.py)
- **Verification:** [Web guard tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sigil_guards.py),
  [scope grammar tests](https://github.com/hexanomicon/lychd/blob/main/tests/codex/test_scopes.py),
  and [preauthorization tests](https://github.com/hexanomicon/lychd/blob/main/tests/codex/test_preauth.py)
- **Law:** [ADR 09 — Security](./adr/09-security.md),
  [ADR 25 — Human in the Loop](./adr/25-hitl.md), and [ADR 38 — IAM](./adr/38-iam.md)

### Local browser and bind boundary {#local-browser-bind-boundary}

**State:** Partial

**Proved now:** Generated Pod ports and the generated uncaged systemd unit pin the Vessel to IPv4
loopback. The Quadlet schema and extension-contribution boundary reject non-loopback publication,
and the production application composes Litestar CSRF protection and publishes its configured
double-submit cookie/header names to the generated browser contract.

**Boundary — Not yet:** The hostile-browser contract fails. Production configuration permits
wildcard CORS, does not constrain the Host authority, and stamps ordinary requests with the fixed
`magus:*` bootstrap Sigil rather than authenticating a caller. The internal foreground server
entrypoint and its environment can bypass the typed loopback host setting, while `/schema/scalar`
loads mutable CDN assets into the local browser origin. CSRF remains a useful unsafe-method layer,
but it does not protect GET or SSE confidentiality or stop DNS rebinding. Remote, proxied, tunneled,
direct-image-public, foreground non-loopback, and untrusted-browser use are unsupported until the
bind, Host, Origin, local-asset, security-header, full-production-app, and hostile-browser
contracts pass.

**Evidence**

- **Source:** [Application composition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py),
  [CORS and CSRF builders](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/components.py),
  [web defaults](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/server.py),
  [bootstrap Sigil middleware](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/middleware.py),
  [foreground launcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__main__.py),
  [deployment transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py),
  and [Quadlet schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/schemas.py)
- **Verification:** [Generated-network golden tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py),
  [extension publication tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_contributor.py),
  [Quadlet schema tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_schemas.py),
  [generated uncaged-unit tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_uncaged_unit.py),
  and [explicit production-wiring receipt gap](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [ADR 09 — Security](./adr/09-security.md),
  [ADR 11 — Backend](./adr/11-backend.md), and
  [ADR 15 — Frontend](./adr/15-frontend.md)

### Scout web acquisition {#scout-web-acquisition}

**State:** Designed

**Proved now:** ADR 30 separates search, fetch, extraction, crawl, rendering, interaction,
credential use, session custody, screenshots, downloads, and artifact admission into distinct
authority contracts. It selects one bounded static public-page fetch and network-free extraction
as the first passage.

**Do not expect yet:** There is no Scout provider, browser service, web endpoint, Agent tool,
destination-pinning implementation, acquisition receipt, download quarantine, authenticated
session, Smith ingestion path, or automatic Toll. A URL, redirect, CAPTCHA, payment challenge, or
provider failure cannot authorize a stronger effect.

**Evidence**

- **Topic:** [Scout](./sepulcher/extensions/scout.md)
- **Law:** [ADR 30 — Web Acquisition](./adr/30-webcrawler.md)

### Vision admission {#vision-admission}

**State:** Partial

**Proved now:** Capability declarations can distinguish the dedicated Vision family from image
modality admission, and dispatch metadata can preserve that distinction.

**Boundary — Not yet:** LychD does not upload or materialize image bytes, normalize them, request
the image modality through Bridge, transport them to an engine, or render a returned image.

**Evidence**

- **Source:** [Capability family vocabulary](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/capability_family.py)
  and [capability admission shape](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/capabilities.py)
- **Verification:** [Vision and modality catalog tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_catalog.py)
- **Topic:** [Prism](./sepulcher/extensions/prism.md)
- **Law:** [ADR 36 — Vision](./adr/36-vision.md)

### Audio admission {#audio-admission}

**State:** Partial

**Proved now:** Capabilities can declare audio input/output modalities while dedicated speech
services remain the `stt` and `tts` families.

**Boundary — Not yet:** There is no audio byte materialization, engine transport, streaming socket,
resonance buffer, working STT/TTS adapter, or Audio Coven. Audio is not a capability family.

**Evidence**

- **Source:** [Capability family vocabulary](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/capability_family.py)
  and [artifact modality projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/router.py)
- **Verification:** [Audio admission and no-audio-family tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_catalog.py)
- **Topic:** [Echo](./sepulcher/extensions/echo.md)
- **Law:** [ADR 37 — Audio](./adr/37-audio.md)

### Artifact reference contract {#artifact-reference-contract}

**State:** Partial

**Proved now:** An Intent can carry immutable artifact metadata and preserve its digest,
classification, size, media type, and required modality through the Run ledger.

**Boundary — Not yet:** An `ArtifactRef` is not byte custody. LychD has no upload/store adapter,
principal-bound retrieval, materializer, derivation provenance, retention/deletion contract,
provider fetch audit, or Reliquary backend.

**Evidence**

- **Source:** [Artifact reference and Intent shapes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/router.py)
- **Verification:** [Artifact reference preservation test](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py)
- **Law:** [ADR 36 — Vision](./adr/36-vision.md) and [ADR 37 — Audio](./adr/37-audio.md)

## Evolution and federation {#evolution-and-federation}

### Karma semantic memory {#karma-semantic-memory}

**State:** Designed

**Proved now:** A narrow Karma database row and ADR 27 reserve an architectural home for future
memory work.

**Do not expect yet:** There is no semantic ingestion, embedding pipeline, retrieval tool,
consecration policy, curator loop, memory evolution, or production vector store.

**Evidence**

- **Source:** [Narrow Karma model](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/karma.py)
- **Journey:** [Illumination](./divination/transcendence/illumination.md)
- **Law:** [ADR 27 — Memory](./adr/27-memory.md)

### Mirror identity {#mirror-identity}

**State:** Designed

**Proved now:** ADR 32 and the Mirror doctrine define identity as a filtered, revisable binding
rather than a second cognitive runtime.

**Do not expect yet:** There is no identity store, synthesis loop, hydration adapter, versioned
persona, feedback calibration, or promoted persistent identity.

**Evidence**

- **Topic:** [Mirror identity](./sepulcher/extensions/mirror.md)
- **Law:** [ADR 32 — Identity](./adr/32-identity.md)

### Shadow simulation {#shadow-simulation}

**State:** Designed

**Proved now:** ADR 31 defines branch expansion, scoring, pruning, authority, and collapse as a
future simulation organ.

**Do not expect yet:** There is no runnable branch graph, MCTS engine, branch store, budgeted
simulation, verified collapse, or branch-reaper implementation.

**Evidence**

- **Topic:** [Shadow Realm](./sepulcher/extensions/shadow.md)
- **Law:** [ADR 31 — Simulation](./adr/31-simulation.md)

### Riddle evaluation {#riddle-evaluation}

**State:** Designed

**Proved now:** ADR 34 defines the evaluation jurisdiction, including adversarial cases, execution
evidence, capability comparison, and calibration.

**Do not expect yet:** There is no runnable evaluation harness, maintained case suite, scorer
contract, benchmark history, pass-at-k experiment, or routing update from evaluations.

**Evidence**

- **Topic:** [Riddle](./sepulcher/extensions/riddle.md)
- **Law:** [ADR 34 — Evaluation](./adr/34-evaluation.md)

### Soulforge training {#soulforge-training}

**State:** Designed

**Proved now:** ADR 33 defines how consecrated examples could enter a governed training pipeline.

**Do not expect yet:** There is no dataset harvest, training job, isolated trainer, checkpoint
evaluation, model registration, rollback, or production promotion.

**Evidence**

- **Topic:** [Soulforge](./sepulcher/extensions/soulforge.md)
- **Law:** [ADR 33 — Training](./adr/33-training.md)

### Smith and Forge promotion {#smith-forge-promotion}

**State:** Designed

**Proved now:** The creation, packaging, evolution, and assimilation laws define a future verified
path from candidate code to an attributable extension.

**Do not expect yet:** There is no safe code forge, autonomous repair loop, verified package
promotion, compatibility gate, rollback controller, or self-extension runtime.

**Evidence**

- **Topic:** [Smith](./sepulcher/extensions/smith.md) and
  [Immortality](./divination/transcendence/immortality.md)
- **Law:** [ADR 16 — Creation](./adr/16-creation.md),
  [ADR 17 — Packaging](./adr/17-packaging.md),
  [ADR 18 — Evolution](./adr/18-evolution.md), and
  [ADR 35 — Assimilation](./adr/35-assimilation.md)

### Remote IAM {#remote-iam}

**State:** Designed

**Proved now:** ADR 38 assigns future remote identity and authorization to the Ward rather than
stretching the loopback Sigil into a network credential.

**Do not expect yet:** There is no credential-backed principal, remote session, object
authorization, delegation, revocation, tenant isolation, or audit contract.

**Evidence**

- **Topic:** [Ward](./sepulcher/extensions/ward.md)
- **Law:** [ADR 38 — IAM](./adr/38-iam.md)

### A2A and Intercom {#a2a-intercom}

**State:** Designed

**Proved now:** ADR 26 reserves a typed peer protocol boundary for future agent-to-agent labor.

**Do not expect yet:** There is no authenticated durable inbox/outbox, peer identity, message
ordering, deduplication, cancellation, delegation, effect receipt, or interoperability profile.

**Evidence**

- **Law:** [ADR 26 — Agent-to-Agent](./adr/26-a2a.md)

### x402 payments {#x402-payments}

**State:** Designed

**Proved now:** ADR 41 assigns payment negotiation and settlement to a future Toll extension and
makes price discovery an input to future economic dispatch.

**Do not expect yet:** There is no quote, reservation, authorization, signer, payment, settlement,
reconciliation, budget enforcement, or safe response to an HTTP 402 challenge.

**Evidence**

- **Topic:** [Toll](./sepulcher/extensions/toll.md)
- **Law:** [ADR 41 — x402](./adr/41-x402.md)

### Legion federation {#legion-federation}

**State:** Designed

**Proved now:** ADR 42 names the multi-node jurisdiction, separates cognitive Master authority
from node-local physical authority, and rejects shared databases and universal credentials.

**Do not expect yet:** There is no node enrollment, expiring advertisement, local resource
reservation, fencing, artifact transfer, durable spool, cancellation, or settlement. ADR 42's
accepted Node Agent protocol remains architecture rather than an implemented fleet.

**Evidence**

- **Topic:** [Legion](./sepulcher/extensions/legion.md)
- **Law:** [ADR 42 — Legion](./adr/42-legion.md)

### VPN Tether {#vpn-tether}

**State:** Designed

**Proved now:** ADR 39 assigns private network transport to a separate Tether jurisdiction.

**Do not expect yet:** There is no VPN provider, enrollment, key rotation, route policy, network
health, revocation, or proof that network reachability establishes identity.

**Evidence**

- **Topic:** [Tether](./sepulcher/extensions/tether.md)
- **Law:** [ADR 39 — VPN](./adr/39-vpn.md)

### Proxy Veil {#proxy-veil}

**State:** Designed

**Proved now:** ADR 40 assigns edge proxy and TLS composition to a distinct Veil jurisdiction.

**Do not expect yet:** There is no proxy provider, certificate lifecycle, generated edge policy,
remote ingress hardening, or proof that a proxy substitutes for application authorization.

**Evidence**

- **Topic:** [Veil](./sepulcher/extensions/veil.md)
- **Law:** [ADR 40 — Proxy](./adr/40-proxy.md)

## Operator receipt requirements

An operator receipt promotes only the subject and environment it actually exercises. It records:

- exact LychD commit and configuration profile;
- host distribution, kernel, systemd, Podman, and security context;
- GPU, driver, runtime, topology, and relevant memory observations;
- engine image digest and upstream revision;
- model identity, revision, format, quantization, cache, split, and runtime flags;
- exact commands or API calls, expected result, observed result, and bounded timings;
- startup, readiness, useful work, cancellation when relevant, shutdown, and recovery outcomes;
- redacted logs and artifact digests sufficient to audit the result;
- date, operator, pass/fail decision, and the precise boundary the receipt does not cover.

A receipt is maintained evidence, not an anecdote. A new engine, model, image, driver, hardware
topology, or materially different configuration requires its own named receipt.

## Update law

When behavior changes, its source, focused verification, owning technical documentation, and this
record change together. When evidence disappears or the claimed boundary fails, downgrade the
record immediately. A delivery change must not require copying states into README, the Prophecy,
the Lexicon, or ADR indexes.

Decision, delivery, and proof remain separate: ADRs own law, this page owns delivery boundaries,
topic pages own operation, and source, tests, and maintained receipts own executable evidence.

## Enter the Work

This ledger is a threshold, not a destination. Perform [The Summoning
Rite](./summoning.md) when you are ready to test one bounded local conjunction. Its four agreeing
observations are a bounded first-life result, not a maintained operator receipt; preserve them
with all metadata above, and let the observed result—not hope—decide what this page may claim next.
