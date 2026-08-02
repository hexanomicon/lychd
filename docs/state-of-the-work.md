---
title: State of Work
icon: material/list-status
---

# State of Work

LychD is **pre-alpha**. This page is the canonical account of what repository evidence supports,
what still needs a named operator receipt, and what remains design.

The proved envelope is local, loopback-oriented, single-user, and one control process in the
repository-test profile. A disposable PostgreSQL receipt now exercises the real application
factory, in-process SAQ, one completed Bridge Run, shutdown, and a second boot. Real systemd,
rootless Podman, GPU, model, inference-engine, and browser combinations still need the receipts
named below. Remote and multi-tenant operation are not current claims.

[Prophecy](./index.md) names the destination; this page names what can answer now.

## Outcome matrix

| Scenario | Answer now | Decisive limit |
| --- | --- | --- |
| CLI bootstrap | **Partial.** The CLI grammar, dry-run planning, transactional `init`/`bind`, bounded `status`/`logs`, and guarded deletion have repository evidence. | No maintained real-host startup, shutdown, deletion, or full systemd/Podman receipt. See [Core CLI rites](#core-cli-rites) and [systemd/Podman embodiment](#systemd-podman-embodiment). |
| Local text chat | **Partial.** The exact Pydantic AI adapter, local run engine, and Bridge contracts work in the repository-test envelope. | The PostgreSQL application-factory path replaces live dispatch, orchestration, and context collaborators with offline doubles after startup; no named inference-engine + real browser acceptance receipt exists. See [Bridge](#bridge-surface), [first-light persistence](#phylactery-first-light), and the engine records under [Animation](#animation-and-orchestration). |
| Browser safety | **Loopback only.** Generated deployment binds IPv4 loopback; the app constrains Host and CORS, keeps schema assets local, and applies CSRF. | The fixed bootstrap Sigil is not caller authentication, direct-launch visibility is finite, and no production-browser security receipt exists. Proxy, tunnel, remote, and untrusted-browser use remain unsupported. See [Local browser and bind boundary](#local-browser-bind-boundary). |
| PostgreSQL and runtime proof | **Repository lifecycle receipt.** Disposable PostgreSQL tests cover run-ledger races, consent atomicity, migrations, and real `create_app()` + SAQ startup/run/shutdown/second-boot recovery. | After real startup the lifecycle receipt substitutes offline dispatch, orchestration, and context collaborators and uses an HTTP test client. It proves factory, PostgreSQL, SAQ, HTTP, shutdown, and recovery wiring, not composed runtime behavior or a systemd/Podman/GPU/model/browser receipt. See [Phylactery](#phylactery-first-light) and [systemd/Podman embodiment](#systemd-podman-embodiment). |
| Major blockers | Authenticated browser/remote authority, privacy-safe Portal egress, real host/model/runtime receipts, native Oculus, and resource-aware scheduling. | Delegated providers, artifact custody, durable memory/recall, vision/audio bytes, executable evolution, and federation remain Partial or Designed in their records below. |

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

Classify the exact subject, not its upstream dependency or neighboring design. No current record is
Experimental.

## Current evidence envelope

Repository tests cover the local memory-profile composition, important unit/integration/web
contracts, focused disposable-PostgreSQL concurrency and migration paths, and one real
`create_app()` + SAQ + PostgreSQL lifecycle across shutdown and a second boot. After real startup,
that lifecycle replaces live dispatch, orchestration, and context collaborators with offline
structural doubles and uses Litestar's HTTP test client. It proves application-factory,
PostgreSQL, SAQ, HTTP, shutdown, and durable-projection recovery wiring; it does not prove the
replaced collaborators' composed behavior or a production deployment, inference-engine, or browser
receipt.

- **Source:** [Application factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py),
  [web lifespan](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/lifespan.py),
  and [Altar service assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/altar_services.py)
- **Verification:** [Memory-profile composition and two-boot PostgreSQL lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
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
`run`, and `del` grammar; `st` aliases `status`. Dry-run planners do not perform LychD-managed
mutation. Real `init` refuses UID 0, inspects the systemd/Podman/Quadlet/cgroup, filesystem,
Binding-site, and PostgreSQL substrate, then applies one journaled, revalidated layout plan. Real
`bind` uses one immutable Settings/extension/Rune snapshot, compiles core and contributed
declarations, revalidates tools, sites, secrets, and generations under the lifecycle lock, and
reconciles only the exact Scribe-owned unit set. Layout, binding, and deletion operations use
descriptor-pinned no-follow identity checks, compare-and-swap generations, atomic
exchange/quarantine, durable receipts, and explicit cleanly-rolled-back versus indeterminate
outcomes; native terminal signals retain progress and recovery evidence. `status` renders bounded
local ownership, unit, declaration, and mount inventory; `logs` reads an owned-unit journal tail;
direct `start` rejects split runtime state; `stop` covers owned units; `run` exposes typed
operation metadata; and `del` is fingerprinted, confirmed, receipt-gated, and limited to attested
LychD authority. The installed entrypoint initializes shared structured logging before dispatch.

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

**Proved now:** **Design recorded:** the source tree declares a Hatch distribution, Containerfile,
and non-publishing candidate workflow. Tests inspect real wheel/source archives, license and notice
bytes, an isolated install, dependency integrity, process entrypoints, exact source identity, and
SHA-256 receipts without granting publish authority.

**Do not expect yet:** No maintained receipt pairs this revision as an anonymously installable
PyPI package and pullable immutable GHCR image from one tag and commit. The public `0.0.1`
placeholder is not evidence for this MPL-2.0 package; the configured `latest` image was not
anonymously pullable in the recorded audit. Publication still needs a clean hosted gate,
artifact/image/SBOM audit, explicit human promotion, and a named clean-host
install/start/reply/stop receipt.

**Evidence**

- **Source:** [Package version](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__about__.py)
  and [default Vessel image](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/server.py)
- **Version:** [Distribution and version declarations](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml),
  [Vessel build](https://github.com/hexanomicon/lychd/blob/main/Containerfile),
  [non-publishing candidate workflow](https://github.com/hexanomicon/lychd/blob/main/.github/workflows/build.yml),
  [source preflight](https://github.com/hexanomicon/lychd/blob/main/scripts/verify_release_source.py),
  [archive audit](https://github.com/hexanomicon/lychd/blob/main/scripts/verify_release_artifacts.py),
  [third-party source notices](https://github.com/hexanomicon/lychd/blob/main/THIRD_PARTY_NOTICES.md),
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

**Proved now:** The mediated protocol covers durable claim, intent validation, loaded Scribe graph
attestation, one compound Animator-target transaction, bounded and reaped `systemctl` clients,
settled-world observation, cancellation, exact-prior-world compensation, crash recovery, and
host-owned outcome journals. Host mutation shares the interprocess lifecycle lock and uses the
attested absolute `systemctl`; fresh intents name the exact Animator and capability.

**Boundary:** Protocol tests and an isolated private-systemd receipt prove real job ordering only
with inert services, not the operator's Quadlet/Podman/GPU host. `.declined` means no effect,
`.restored` proves the prior world, `.contained` fences a fresh uncertain outcome,
`.processing` retains uncertain reclaimed work, and `.rejected` marks invalid delivery. General
repair remains an operator responsibility.

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
- **Rite:** [Summoning](./summoning.md)
- **Law:** [ADR 08 — Containers](./adr/08-containers.md) and
  [ADR 10 — Privilege](./adr/10-privilege.md)

### Whole-body snapshot and restore {#whole-body-snapshot-restore}

**State:** Designed

**Proved now:** **Design recorded:** filesystem services prepare the Btrfs subvolume and
no-copy-on-write substrate on which ADR 07's snapshot ritual could operate.

**Do not expect yet:** LychD does not coordinate freeze, database and code snapshot, restore, or
post-restore reconciliation as one whole-body ritual.

**Evidence**

- **Source:** [Btrfs preparation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/btrfs.py)
  and [layout service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/layout.py)
- **Verification:** [Filesystem layout tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_layout.py)
- **Law:** [ADR 07 — Snapshots](./adr/07-snapshots.md)

### Tomb untrusted execution {#tomb-untrusted-execution}

**State:** Designed

**Proved now:** **Law in place:** ADR 09 separates future untrusted execution from LychD's trusted,
rootless core.

**Do not expect yet:** There is no Tomb queue, executor, credential, policy, Landlock, or `nono`
integration. The trusted core is not Tomb evidence.

**Evidence**

- **Law:** [ADR 09 — Security](./adr/09-security.md)

## Persistence, execution, and consent {#persistence-execution-and-consent}

### Phylactery first-light persistence {#phylactery-first-light}

**State:** Partial

**Proved now:** Run, delivery, step, session, consent, and checkpoint persistence shapes exist.
Run admission and every resume hop atomically create one exact delivery record; claim and terminal
settlement are sequence-fenced. Process-owned, restart-supervised relays repair publication and
re-fire decided consent or delegated waits under exact ownership. One shared scheduler retains every
degraded, caller-held, or clean-but-still-active external-wait keyset page while still scanning
forward. Run jobs carry a refreshed SAQ heartbeat, and startup terminally fences a proven pre-boot
active delivery before sequence rotation instead of preserving an abandoned pre-claim job. Consent
crash-window recovery requires the first resumable checkpoint to bind the exact latest non-cancelled
Consent, then persists that owner on `Run.consent_id`; ordinary reconciliation reads that exact
pointer rather than inferring ownership from newest-row order. Re-admission requires the same-run
Consent to carry a terminal verdict, decision principal, and decision time. The same rule covers a delegated
pre-park owner, whose same-run job must carry shape-valid terminal result evidence. Generic status mutation cannot bypass either
owner-specific resume gate. Unrecoverable correlated effects are
contained before parent failure. PostgreSQL startup refuses degraded durable recovery. Disposable PostgreSQL tests cover
CAS races, exact terminal evidence, pending-versus-decided consent admission, running-versus-terminal
delegated admission, consent atomicity, and migration 0004's live-work refusal in
both upgrade and downgrade directions plus a drained upgrade/downgrade cycle. Migration 0007
locks its table while refusing to erase retained Nexus request identities. Migration 0008 refuses
ownerless live consent waits and evidence-free settled Consent or delegated rows on upgrade, and
refuses downgrade while a consent wait remains. The first successful Run
claim owns `started_at`; later resume claims do not rewrite boot ownership. A real
application-factory receipt boots PostgreSQL and in-process
SAQ, completes a Bridge Run, shuts down, boots a second application against the same database, and
recovers the terminal Bridge and gapless Orb projections.

**Boundary — Not yet:** PostgreSQL and SAQ are not one distributed transaction, Step events have no
transactional outbox, and full memory/PostgreSQL adapter parity is absent. Persistent worker-side
effect-containment failure has no same-boot `FAILING` custody state or watchdog; it remains
nonterminal until restart orphan recovery. The lifecycle receipt
replaces live dispatch, orchestration, and context collaborators after real startup and uses an
HTTP test client; it is not proof of their composed behavior or a real-host, inference-engine,
browser, or checkpoint-plus-consent restart receipt.

**Evidence**

- **Source:** [First-light migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0001_phylactery_first_light.py),
  [pinned Pattern-manifest migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0002_pin_pattern_manifest.py),
  [Run delivery migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0004_run_delivery_outbox.py),
  [checkpoint adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/checkpoints.py),
  and [run ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/ledger.py)
- **Verification:** [Run-ledger contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py),
  [PostgreSQL run-ledger receipts](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py),
  [PostgreSQL migration cycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_migrations_pg.py),
  and [two-boot production-factory lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [ADR 06 — Persistence](./adr/06-persistence.md)

### Topology-A local run execution {#topology-a-local-runs}

**State:** Available

**Proved now:** One Vessel process can admit, claim, execute, cancel, settle, and project live run
events with bounded replay fencing. Each run pins its validated immutable Pattern manifest,
including a reviewed implementation-compatibility revision;
node, grant/lease, and transition evidence share stable run and occurrence correlation. One
boot-composed catalogue feeds execution and web projections. Multiple source-registered exact
revisions can coexist: new admission selects only declared active revisions while retired-but-
registered revisions remain executable for older pinned Runs and visible as retained in Loom.
Construction rejects manifest/Graph node or transition drift, dynamic unprovable returns,
Gate/delegate kind drift, duplicate semantic edges, and missing or multiple terminals. Initial and
resume admission retain exact durable publication intent, including requested priority; admission refusal is fenced to the exact
delivery generation still in `HELD`, so a release that committed before raising cannot be failed;
bounded refusal retry surfaces unresolved custody rather than silently stranding it. An idempotent
replay inspects existing delivery truth and repairs a stranded `HELD` caller-context gate before it
can return a handle, and republishes an exact `PENDING` hop before returning. Startup plus the runtime relay repair missing broker jobs without rerouting the
Pattern or guessing fresh versus resume mode, fairly revisit every caller-held, degraded, or live
external-wait page while scanning forward, and retry exact abort of a broker job accepted after
cancellation fenced canonical truth; caller cancellation cannot interrupt that containment probe.
Every terminal status is final; retry requires a new Run identity. Terminal paths
drain their ordered Step writer before closing, and startup repairs missing terminal evidence from
canonical Run truth. Worker failure retries transient child-containment faults before settlement;
persistent uncertainty remains nonterminal rather than claiming false `FAILED` truth. Shutdown owns
SAQ launcher tasks as well as worker stop coroutines under one deadline, proves observed tasks ended,
then attempts every queue disconnect while retaining grouped failures and deferring cancellation
until each in-progress teardown and the reverse sweep complete. The queue facade is active before connect and closes a managed
PostgreSQL pool opened before failed SAQ schema initialization.

**Boundary:** The implementation revision is an explicit reviewed declaration, not automatic
source-drift or semantic compatibility proof. This does not claim a transactional event outbox, separate-worker truth, replayable
multi-process streaming, or federation. The delivery relay is process-local and broker probes can
still make required startup fail closed. Replay retention is bounded, but live per-subscriber
queues are currently unbounded; slow-subscriber overflow and backpressure are not governed.

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
`pydantic-ai-slim==1.25.1` contract with serializable state. Provider Portals retain model-aware
profiles selected by alias, while local and generic endpoints explicitly use the conservative
compatibility profile. OpenRouter ids and the provider/surface matrix fail before model dispatch.

**Boundary:** This does not claim Pydantic AI v2 durability, v2 stream events, GraphBuilder, or
automatic usage propagation. Gemini still uses its OpenAI-compatible transport rather than a
native adapter, and current OpenAI-compatible models do not provide exact pre-request token
counting.

**Evidence**

- **Source:** [Agent factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py),
  [model construction](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/model_factory.py),
  [runtime connector](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/surfaces.py),
  [provider registration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/register.py),
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

**Proved now:** **Design recorded:** ADRs 20 and 24 accept a v2 migration while the dependency
declaration and lock preserve the exact v1 compatibility baseline.

**Do not expect yet:** v2 messages, toolsets, deferred events, durability capabilities, and graph
contracts are not installed LychD behavior.

**Evidence**

- **Current baseline:** [Dependency declaration](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
  and [resolved lock](https://github.com/hexanomicon/lychd/blob/main/uv.lock)
- **Law:** [ADR 20 — Agents](./adr/20-agents.md) and [ADR 24 — Graph](./adr/24-graph.md)

### Graph stasis and consent re-admission {#graph-stasis-consent}

**State:** Partial

**Proved now:** Focused tests cover logical parking, bounded chained single-approval rounds,
memory-profile simulated restart, reconciliation, idempotent settlement, graph re-admission, and
fail-closed capability/tool/effect/schema substitution on resume. Unversioned approval effects do
not park. Each model round may request one supported approval; a resumed run may enter another
bounded round. Re-admission atomically creates an exact pending delivery; transient publication
failure is repaired by the same startup/runtime relay as initial work. Resume admission is fenced
to the exact Consent that owns the current wait, so a historical card cannot admit a later approval
round. Run cancellation settles every still-pending owned card as `cancelled` before terminal Run
truth. It abort-fences the parent before its final child/Consent sweep; uncertain or timed-out
containment keeps the Run honestly `CANCELLING`, and a terminal retry repairs escaped cards. A
post-park probe failure or worker-task cancellation preserves `AWAITING_CONSENT`; the runtime consent
relay later re-fires any committed decision and fairly retains all degraded pages.

**Boundary — Not yet:** This is not a Postgres Consent-plus-Checkpoint restart receipt. Multiple
approval calls in one model response are rejected. No tracked production toolset currently
originates approval; focused tests inject the only approval-required tool.

**Evidence**

- **Source:** [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py),
  [stasis adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/stasis.py),
  and [consent ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/ledger.py)
- **Verification:** [Consent resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_consent_resume.py),
  [startup reconciliation tests](https://github.com/hexanomicon/lychd/blob/main/tests/cortex/test_reconcile.py),
  and [web consent endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_consent_endpoint.py)
- **Law:** [ADR 25 — Human in the Loop](./adr/25-hitl.md)

### Delegated agent execution {#delegated-agent-execution}

**State:** Partial

**Proved now:** Typed contracts cover secret-free delegated requests, artifact references,
idempotent process-local `AgentJob` submission/adoption/cancellation, exact wait ownership, Graph
parking with `AWAITING_DELEGATE`, and bounded re-admission. Pure policy modules validate Coffin
filesystem, network, resource, environment, command, Provider Gate, and capacity decisions. The
selectable extension supplies a deterministic no-effect `reference` adapter, delegated database
shapes and migration, a PostgreSQL adapter, exact pre-park startup recovery/containment tests, and
initial Bridge/Loom/Nexus/Orb projections. Post-park probe failure or worker-task cancellation
preserves `AWAITING_DELEGATE`; the runtime relay polls exact owners and fairly retains every
degraded page while continuing forward.

**Boundary — Not yet:** The memory profile remains process-local and the PostgreSQL job ledger has
no real PostgreSQL or migration receipt. Codex CLI, Claude Code, OpenCode Go, OpenRouter, and other
provider entries are declared-only: none launches. Coffin and Gate are policy-only; there is no
lower-trust container, effectful `nono` child/supervisor, credential isolation, provider call,
egress enforcement, process-tree cancellation, durable artifact custody, measured budget ledger,
real provider recovery, or live browser receipt.

**Evidence**

- **Source:** [Delegation contracts and coordinator](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/delegation),
  [PostgreSQL delegated-job store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/delegation.py),
  [delegated-job records](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/delegation.py),
  [delegated-job migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0003_delegated_agent_ledger.py),
  [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py),
  [run engine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py),
  [delegated-runtime extension store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/delegation.py),
  [built-in delegation catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/register.py),
  [delegated web contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/contracts.py),
  [Orb delegation projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/orb.py),
  and [Coffin, Gate, and capacity policy](https://github.com/hexanomicon/lychd/tree/main/src/lychd/system/delegation)
- **Verification:** [Delegation coordinator tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_coordinator.py),
  [Graph park tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_delegate_stasis.py),
  [run re-admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_delegate_resume.py),
  [delegation extension tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py),
  and [security/capacity policy tests](https://github.com/hexanomicon/lychd/tree/main/tests/unit/system/delegation)
- **Law:** [ADR 05 — Extensions](./adr/05-extensions.md),
  [ADR 09 — Security](./adr/09-security.md),
  [ADR 14 — Workers](./adr/14-workers.md),
  [ADR 22 — Dispatcher](./adr/22-dispatcher.md),
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md),
  [ADR 24 — Graph](./adr/24-graph.md), and
  [ADR 29 — Observability](./adr/29-observability.md)

### Durable in-app Attention {#durable-attention}

**State:** Designed

**Proved now:** **Design recorded:** Bridge projects consent cards and a shared count that a future
Attention inbox can consume. Snapshot generations fence delayed decision responses, Run
cancellation removes the corresponding local card authority, and shell-wide attention treats local
events only as invalidation signals before re-reading cross-session status. Overlapping status reads
are request-version fenced, so a stale arriving zero is never accepted directly as "clear" truth.
The selected Bridge revokes cards before its cancellation refetch, so a failed refresh cannot leave
an actionable stale consent visible.

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
behavior are covered by focused repository tests. Registry hydration rejects duplicate runtime and
capability keys before publishing state and reports both conflicting declaration paths and runtime or
capability provenance. Probe publication is serialized, requires an exact key set and matching
dynamic/static shape, and invalidates affected cached observations after exceptions or malformed
results; cancellation during a probe also invalidates the interrupted observations. Capability,
persistent-resident, Animator Rune, and group projections return detached values, adapter activation
and abandonment receive deep specification snapshots, connector model inventories are copied on
admission and projection, and issued grants retain defensive copies of
nested specification and state values while keeping explicitly named runtime handles live.

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

**Proved now:** Explicit built-in selection and dependency-first assembly produce current concrete
Rune, Portal, runtime, and Quadlet contributions. Rune, Soulstone, Portal, Transmutation,
delegated-runtime, and Run-operation stores retain registration ownership and reject cross-provider
replay. The manager retains the root provenance mutator and gives each extension a fixed
provider-bound registration facade, so retained registrant state cannot borrow another extension's
identity. Portal runtime composition preserves the schema/factory definition and dispatches by exact
concrete Rune schema, so activation order cannot let a broad factory claim another provider. Every
normal or bootstrap-installed store seals membership after the single registration pass, preventing
service snapshots and discovery from diverging later. Crypt ids are canonical path selectors and
Rune branch ownership derives only from the admitted schema generation. Rune registry admission and
reads deep-copy nested metadata, and a failed Crypt import or registration clears its synthetic
package namespace before retry. Registration is a synchronous `register(context) -> None` hook;
awaitable or value-returning hooks fail assembly instead of silently freezing an incomplete context.
The seal does not claim recursive immutability for arbitrary trusted
contributor objects outside those explicit snapshot boundaries.

**Boundary — Not yet:** Runtime hydration does not project extension ownership into every live
capability view. Vessel contributions remain reserved. Package installation, dependency locks,
upgrade/uninstall, migration ownership, effectful lifecycle ownership, Forge admission, and a stable
public SDK remain absent.

**Evidence**

- **Source:** [Extension manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/manager.py),
  [contribution context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py),
  [delegated-runtime contributions](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/delegation.py),
  [Run-operation contributions](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/operations.py),
  and [built-in catalog](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/catalog.py)
- **Verification:** [Built-in catalog tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_catalog.py),
  [portal contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_portals.py),
  [registry contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py),
  [Quadlet contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_contributor.py),
  [delegation attribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py),
  and [operation attribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_operations.py)
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

**Proved now:** Soulstone `conflict_domains` compile into one undirected incompatibility graph:
omission on a dedicated non-resident means `default-exclusive`, while explicit `[]` declares
coexistence. Bind rejects unadvertised Soulstones and conflicting Covens, emits one target per
Animator, and aggregates only compatible targets. Switching selects the target's exact active
neighbors, attests the Scribe-owned loaded unit graph and current world, issues one bounded compound
target request, waits for settled systemd jobs, and classifies success or exact restoration.

**Boundary:** Repository evidence plus a private user-manager receipt proves real systemd ordering
with inert services, not the operator's Quadlet/Podman/GPU host. Explicit coexistence is an
operator assertion, not measured capacity admission. The separate
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

**State:** Partial

**Proved now:** Focused protocol tests cover admission closure, lease drain, serialized plans for
the tested dedicated-runtime paths,
readiness convergence, loaded-graph attestation, one compound target transaction, settled-world
classification, exact-prior-world compensation, cancellation restoration, and fail-closed
containment. A proved restoration reopens admission; `.contained` and unresolved `.processing`
fence startup and later Reactor work. Direct Orchestrator admission refuses a non-warm shared
dynamic Animator before soft activation or host effects, matching Dispatcher ownership law. The
absolute warm-up deadline covers target refresh, optional activation, accepted-activation refresh,
and WARM polling. Activation or accepted-refresh interruption performs bounded adapter abandonment
despite repeated caller cancellation before propagating failure. The deadline also bounds post-stop cold probes for evictees, so an
unresponsive observation enters typed compensation or containment rather than holding the gates
forever.

**Boundary — Not yet:** The shared-dynamic guard and dedicated transition protocols are repository
tests, not a swap on a real GPU. A failed soft in-runtime model load has no trustworthy rollback and
requires contained operator recovery. General repair of an arbitrary host world remains an operator
responsibility.

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

**Proved now:** **Design recorded:** ADR 23 provides the scheduling seam; deterministic tests
record the current simple `EvictIdlePolicy` baseline.

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
    ADR 15's client foundation is present: Svelte 5 runes, a SvelteKit static SPA, native CSS,
    generated Litestar OpenAPI types, JSON framework errors, runtime-validated semantic JSON SSE,
    and versioned `/api/v1`. Litestar serves the compiled client; Granian remains the production
    server. Focused Python and Svelte tests prove contracts and shell, not a production-factory
    Playwright receipt, durable cross-process browser events, Android, or every named instrument.

### Bridge conversation and consent surface {#bridge-surface}

**State:** Partial

**Proved now:** The Svelte Bridge uses generated `/api/v1` contracts for sessions, text submission,
consent, inspection, versioned semantic SSE, and closed GenUI descriptors. Server-minted run,
Pattern, Loom, Orb, and evidence identities remain authoritative. Completed turns retain one
bounded Pydantic AI history unit and complete validated GenUI descriptors; old key-only fragment rows
normalize to inert empty-props descriptors that cannot enter current renderers instead of breaking session reconstruction. Consent resume
re-bounds history after the actual grant. Admission stores the user turn before queue publication. A
client request UUID survives ambiguous responses and durably converges on one canonical Run and one
retained turn; a replay repairs an unresolved held retention gate and different work cannot reuse the
identity. Cursor-bound snapshots replace speculative client
state on gaps or resync and reconstruct distinct node, grant, and transition occurrence identities
after remount or reload. Events are bound to the requested Run; a permanently closed stream becomes
visibly stale and receives one bounded authoritative recovery attempt rather than remaining live.
Per-Run cursor and generation fences prevent that delayed recovery from replacing a newer session
projection. Durable terminal status overrides lagging process-local channel state, while a user turn
alone never hides a failed or cancelled Run outcome.
The shared consent indicator reports an unknown state after refresh failure instead of presenting a
stale zero as "clear"; instrument events only trigger a new cross-session status read. An ambiguous verdict request disables the contradictory action while keeping
an exact same-verdict retry available, then refreshes authoritative server truth. Newer consent
snapshot authority fences delayed mutation counts, and Run cancellation immediately settles its
durable cards then refetches selected-session consent authority instead of decrementing a stale
browser count. Root-route cancellation derives that authority from the selected snapshot session,
not a possibly stale route prop. Component destruction fences late submissions, stream callbacks,
state writes, and timers. Malformed PostgreSQL-backed session, Run, and consent read identities resolve through
the declared not-found contract. Route identity is fenced before a replacement Bridge snapshot can render or admit
another message. A same-session root refresh preserves the unsent draft; a canonical selected-session
change clears it. Generated contracts explicitly include shared JSON `404` errors for every Bridge,
Nexus, Loom, and Orb operation that can actually miss.

**Boundary — Not yet:** There is no real-browser receipt, durable cross-process event or token
delivery, general multi-approval round, Attention, or notification channel. The
database delivery outbox protects run admission but does not make SSE/token projection durable.
The Bridge also omits a changing grant epoch when caching the Environment
block, so the same session/capability binding can retain an earlier warm-Coven snapshot and the
process-lifetime snapshot cache has no release path. Reconstruction is process-local; text is the
only command modality.

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
  [client stream-contract tests](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/api/client.test.ts),
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

**Proved now:** The Svelte Nexus consumes typed Coven state and plans, labels preview as
non-binding, submits explicit transitions, and follows process-local tickets over semantic SSE.
Its bounded journal correlates run, occurrence, physical transition, and compensation, preserves
each probe's `checked_at`, supports direct transition URLs, and retains terminal reconnect truth
for 60 seconds without evicting active or fresh-terminal tickets. Polling is completion-driven and
single-flight; ticket events are identity-bound and permanent closure becomes explicit stale state
with one bounded authoritative recovery. A failed board refresh marks the snapshot stale and fences
lifecycle mutation until authoritative state loads again. The client allocates a request id before
transition submission and retains ambiguous identities per target, so inspecting a second target
does not discard the first target's only safe retry. A definitive client rejection clears only its
target; a lost-ticket conflict retains the fenced identity instead of enabling a fresh physical
launch. A refreshed terminal transition rebinds inspector selection by exact request id. A refresh
requested during an in-flight read schedules one dirty trailing refresh, and component destruction
prevents late stream attachment or mutation. The profile-bound admission
ledger reserves the first target before launch: PostgreSQL preserves that identity across process
restart, an exact retry reuses a still-live ticket, and a retry after ticket loss refuses without
relaunch. Reuse for a different target is rejected. The process-local ticket store reserves its
bounded capacity before any awaited durable claim, preventing concurrent requests from both
passing the capacity check; overload and closure have explicit API responses.

**Boundary — Not yet:** Only request admission is durable. Ticket state and transition observations
have no durable owner, complete history, cross-process projection, restart recovery, or
production-browser receipt. A retained admission prevents duplicate physical work but cannot prove
whether a lost transition settled or safely resume it. Nexus is not a general
resource/GPU/topology dashboard or configuration surface.

**Evidence**

- **Source:** [Nexus controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/nexus.py),
  [client Nexus](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/NexusView.svelte),
  [process-local ticket store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/tickets.py),
  and [request-admission port](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/swap_requests.py)
- **Verification:** [Nexus board and endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_nexus.py),
  [ticket-retention tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_tickets.py),
  [PostgreSQL admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_nexus_pg.py),
  [client stream-contract tests](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/api/client.test.ts),
  and [Nexus component tests](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/NexusView.test.ts)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Loom workflow instrument {#loom-workflow-views}

**State:** Partial

**Proved now:** The Svelte Loom browses exact immutable Pattern revisions, presents their semantic
station/permission outline as the primary score, and exposes the pinned checkpoint schema,
declared entry station, reviewed implementation revision, and manifest digest. Optional Mermaid source is a secondary local diagram lens. The same typed Pattern
manifest and source are available through `/api/v1`, and ambiguous unversioned browser deep links
fail rather than selecting a revision silently. Loom labels the active default, route precedence,
and retired-but-registered revisions. The catalogue API returns every registered revision with
active/default metadata; `/{workflow}` is the active-revision convenience lookup, while exact
revision lookup preserves old pinned execution without reopening admission. Plain-text source uses
the longer `/source/workflows/...` and `/source/patterns/...` namespaces, preserving every legal
two-segment exact revision identity. Orb exposes a Loom link only when the valid persisted manifest
equals the complete registered snapshot used by worker replay.
Late catalogue or manifest responses are generation-fenced, and component destruction advances that
generation before teardown so no completed load can navigate afterward.

**Boundary — Not yet:** It is a view over the fixed workflow registry, not a general Weaver editor,
workflow mutation surface, Svelte Flow drafting canvas, or production-browser receipt.

**Evidence**

- **Source:** [Loom controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/loom.py),
  [client Loom](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/LoomView.svelte),
  and [workflow registry contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py)
- **Verification:** [Loom rendering tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_loom.py)
  and [Loom component lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/LoomView.test.ts)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 28 — Workflow](./adr/28-workflow.md)

### Orb instrument {#orb-instrument}

**State:** Partial

**Proved now:** `/orb/{run_id}` renders one Run as ordered bounded evidence with its validated
Pattern revision, capture durability label, separate ledger head/page boundary, explicit gaps,
Nexus transition links, stable event selection, pagination, narrow-screen detail, and a
non-diagnostic failure notice. A failed pagination request retains the already loaded evidence and
offers an explicit bounded retry instead of replacing the whole view with an error.

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

**Proved now:** One tested builder configures human and JSON stdlib/Structlog output for CLI and
Litestar. A settings-independent fallback preserves help and recovery verbs; diagnostics stay on
stderr, command results on stdout, JSON maps event to `message`, unexpected `init`/`bind` failures
emit one semantic event, and Granian/SQLAlchemy logger families follow the same policy.

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

**Proved now:** **Law in place:** ADR 29 makes LychD's evidence model canonical. A dormant,
narrowly tested Phoenix export adapter is compatibility evidence, not Oculus delivery.

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

### Context privatization and Portal egress {#context-privatization-and-portal-egress}

**State:** Designed

**Proved now:** **Law in place:** Context, Security, Dispatcher, and Workflow define
lineage-carrying Privatization Labels, a local Privacy Cut, separate transformation and
declassification authority, exact pre-transmission decisions, retry and delegation handling, and
quarantined returns. Current source only recursively censors values whose dictionary keys look
secret-shaped before storing a consent projection. Dispatcher also fails closed for every Portal
source, including direct capability-key dispatch, until a typed egress path exists.

**Do not expect yet:** Blocks, SQL and tool results do not carry general labels or influence
lineage. There is no deterministic identifier scanner, Privacy Agent, `TransformationReceipt`,
sanitized Context branch, Portal Egress Gate, admission/transmission check, pseudonym map,
or deletion propagation. Portal declarations and probes remain visible but cannot receive a Run.

**Evidence**

- **Source:** [Consent projection censor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/schemas.py)
  and [Dispatcher quarantine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/dispatcher.py)
- **Verification:** [Secret-shaped consent projection test](https://github.com/hexanomicon/lychd/blob/main/tests/codex/test_preauth.py)
  and [Portal quarantine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_portals.py)
- **Law:** [ADR 09 — Security](./adr/09-security.md),
  [ADR 21 — Context](./adr/21-context.md),
  [ADR 22 — Dispatcher](./adr/22-dispatcher.md), and
  [ADR 28 — Workflow](./adr/28-workflow.md)
- **Topic:** [Anonymization, taint, and egress](./sepulcher/extensions/weaver/anonymization.md)

### Local Sigil and scope authority {#local-sigil-authority}

**State:** Partial

**Proved now:** Typed Sigils, scope grammar, guards, and consent preauthorization checks are
implemented and exercised on the current loopback bootstrap surface.

**Boundary — Not yet:** The default Sigil is fixed `magus:*`; there is no caller authentication,
object authorization, delegation, revocation, tenant isolation, or remote exposure. Naive expiry
is accepted and then fails against aware UTC in memory. PostgreSQL use-budget consumption and
consent insertion share one transaction; contradictory decisions retain the first commit. Startup
atomically synchronizes the complete Rune-owned policy set, marks absent rows source-inactive
without changing usage or operator `enabled` state, and blocks PostgreSQL admission on failure.
Auto-grants retain a policy
digest and revalidate enabled state, database-time expiry, and digest equality before Graph accepts
the verdict. These checks do not replace generic effect-time IAM/object/authority reauthorization
after arbitrary intervening work.

**Evidence**

- **Source:** [Sigil identity](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/sigil.py),
  [scope grammar](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/scopes.py),
  [scope middleware](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/middleware.py),
  [guards](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/guards.py),
  [preauthorization Runes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/runes.py),
  [preauthorization service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/services.py),
  [consent ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/ledger.py),
  and [startup synchronization](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/lifespan.py)
- **Verification:** [Web guard tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sigil_guards.py),
  [scope grammar tests](https://github.com/hexanomicon/lychd/blob/main/tests/codex/test_scopes.py),
  [preauthorization tests](https://github.com/hexanomicon/lychd/blob/main/tests/codex/test_preauth.py),
  [preauthorization policy integrity tests](https://github.com/hexanomicon/lychd/tree/main/tests/unit/domain/codex),
  and [PostgreSQL consent atomicity tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_consent_pg.py)
- **Law:** [ADR 09 — Security](./adr/09-security.md),
  [ADR 25 — Human in the Loop](./adr/25-hitl.md), and [ADR 38 — IAM](./adr/38-iam.md)

### Local browser and bind boundary {#local-browser-bind-boundary}

**State:** Partial

**Proved now:** Generated Pod ports and the generated uncaged systemd unit pin the Vessel to IPv4
loopback. The Quadlet schema and extension-contribution boundary reject non-loopback publication.
One shared launch policy rejects visible multi-worker/reload settings and gives the production
application its detected listener port. Host admission permits literal loopback authorities on
that port and the configured external port; CORS defaults to same-origin and validates configured
exceptions as exact loopback origins. The application exposes deterministic schema JSON without
remote UI assets, serves its two fixed root artifacts through narrow handlers, and publishes its
CSRF names to the generated browser contract.

**Boundary — Not yet:** Ordinary requests still receive the fixed `magus:*` bootstrap Sigil rather
than an authenticated caller. The application can reject only direct-launch settings visible in
its process; no hostile-browser/Playwright receipt, security-header contract, or remote principal
exists. CSRF is useful for unsafe methods but is not authentication. Remote, proxied, tunneled,
direct-image-public, foreground non-loopback, and untrusted-browser use remain unsupported.

**Evidence**

- **Source:** [Application composition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py),
  [shared server policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/server_policy.py),
  [CORS and CSRF builders](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/components.py),
  [web defaults](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/server.py),
  [fixed Altar asset routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py),
  [bootstrap Sigil middleware](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/middleware.py),
  [foreground launcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__main__.py),
  [deployment transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py),
  and [Quadlet schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/schemas.py)
- **Verification:** [Generated-network golden tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py),
  [extension publication tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_contributor.py),
  [Quadlet schema tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_schemas.py),
  [generated uncaged-unit tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_uncaged_unit.py),
  [server-policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/test_app.py),
  [native launcher handoff tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py),
  [Host/Origin boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_http_boundary.py),
  [Altar route and asset tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py),
  [error-contract tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_error_contract.py),
  and [application-factory lifecycle receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [ADR 09 — Security](./adr/09-security.md),
  [ADR 11 — Backend](./adr/11-backend.md), and
  [ADR 15 — Frontend](./adr/15-frontend.md)

### Scout web acquisition {#scout-web-acquisition}

**State:** Designed

**Proved now:** **Law in place:** ADR 30 separates acquisition effects into distinct authority
contracts and selects bounded public-page fetch plus network-free extraction as the first passage.

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

### Candidate Archive intake seam {#karma-semantic-memory}

**State:** Partial

**Proved now:** ADR 27 reserves the architectural home for semantic memory. A LychD-owned,
DB-free `CandidateArchivePort` and loop-local adapter explicitly admit bounded attributed raw
candidates and separately identified derivatives, reject semantic identity collisions, preserve
source lineage and anti-reingestion keys, and expose a finite processing lifecycle. Retry attempts
are monotonic; a derivative cannot predate its source observation, stale terminal writes and
derivatives from an older attempt fail closed, and ordinary reads hide derivatives once their exact
source attempt is no longer current and processing or processed. Focused tracked
tests prove those local contracts. A new current attempt can replace an older attempt's stale
derivation key only for the same raw source, without exposing the old derivative; that key cannot
migrate to another source lineage. No external memory framework is a dependency or authority.

**Boundary — Not yet:** The adapter is volatile process memory and has no runtime wiring, namespace
authorization, PostgreSQL implementation, semantic ingestion, embedding pipeline, retrieval tool,
consecration policy, curator loop, memory evolution, or production vector store. There is no
automatic capture, recall injection, RAG, promotion, or training loop. Full Karma semantic memory
remains Designed; this Partial record applies only to the bounded Candidate Archive contract.

**Evidence**

- **Source:** [Candidate Archive contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/memory/ports.py),
  [loop-local adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/memory/in_memory.py),
  and [narrow Karma model](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/karma.py)
- **Verification:** [Candidate Archive contract tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/memory/test_archive.py)
- **Journey:** [Illumination](./divination/transcendence/illumination.md)
- **Law:** [ADR 27 — Memory](./adr/27-memory.md)

### Mirror identity {#mirror-identity}

**State:** Designed

**Proved now:** **Law in place:** ADR 32 defines identity as a filtered, revisable binding rather
than a second cognitive runtime.

**Do not expect yet:** There is no identity store, synthesis loop, hydration adapter, versioned
persona, feedback calibration, or promoted persistent identity.

**Evidence**

- **Topic:** [Mirror identity](./sepulcher/extensions/mirror.md)
- **Law:** [ADR 32 — Identity](./adr/32-identity.md)

### Shadow simulation {#shadow-simulation}

**State:** Designed

**Proved now:** **Law in place:** ADR 31 records branch expansion, scoring, pruning, authority, and
collapse for a future simulation organ.

**Do not expect yet:** There is no runnable branch graph, MCTS engine, branch store, budgeted
simulation, verified collapse, or branch-reaper implementation.

**Evidence**

- **Topic:** [Shadow Realm](./sepulcher/extensions/shadow/index.md)
- **Law:** [ADR 31 — Simulation](./adr/31-simulation.md)

### Riddle evaluation {#riddle-evaluation}

**State:** Designed

**Proved now:** **Law in place:** ADR 34 records the evaluation jurisdiction, adversarial evidence,
capability comparison, and calibration.

**Do not expect yet:** There is no runnable evaluation harness, maintained case suite, scorer
contract, benchmark history, pass-at-k experiment, or routing update from evaluations.

**Evidence**

- **Topic:** [Riddle](./sepulcher/extensions/riddle/index.md)
- **Law:** [ADR 34 — Evaluation](./adr/34-evaluation.md)

### Soulforge training {#soulforge-training}

**State:** Designed

**Proved now:** **Law in place:** ADR 33 records how consecrated examples could enter governed
training.

**Do not expect yet:** There is no dataset harvest, training job, isolated trainer, checkpoint
evaluation, model registration, rollback, or production promotion.

**Evidence**

- **Topic:** [Soulforge](./sepulcher/extensions/soulforge/index.md)
- **Law:** [ADR 33 — Training](./adr/33-training.md)

### Inert Creation promotion envelope {#smith-forge-promotion}

**State:** Partial

**Proved now:** The creation, packaging, evolution, and assimilation laws define an attributable
promotion path. A process-local, effect-free Creation state machine now binds exact source revision
and source-tree digest,
allowed paths, budgets, tools, network declaration, artifact custody, deterministic verification,
compatibility evidence, and explicit human review. Its only terminal output is an idempotent
`PromotionRequest(inert=True)` for a named target owner. Candidate and promotion admission reject
tree drift, and evidence chronology cannot run backward. Set-like packet inputs are canonicalized
before digesting. Review evidence and promotion each bind the full `CandidateArtifact` record digest,
including changed paths and declared effects, rather than only its artifact-byte identity. Candidate
records share the same semantic record-id collision domain as custody, verification, compatibility,
review, and promotion evidence.

**Boundary — Not yet:** There is no workspace allocator, filesystem or command executor, database
adapter, crash recovery, safe code forge, autonomous repair loop, target-owner promotion effect,
rollback controller, or self-extension runtime. The schema records compatibility evidence and a
recovery-plan digest; it does not execute or validate those effects. Smith, Forge, and autonomous
promotion remain Designed; this Partial record applies only to the inert Creation evidence and
request envelope.

**Evidence**

- **Source:** [Inert Creation contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/creation/contracts.py)
  and [process-local state machine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/creation/machine.py)
- **Verification:** [Creation contract tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/creation/test_contracts.py)
  and [Creation state-machine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/creation/test_machine.py)
- **Topic:** [Smith](./sepulcher/extensions/smith.md) and
  [Immortality](./divination/transcendence/immortality.md)
- **Law:** [ADR 16 — Creation](./adr/16-creation.md),
  [ADR 17 — Packaging](./adr/17-packaging.md),
  [ADR 18 — Evolution](./adr/18-evolution.md), and
  [ADR 35 — Assimilation](./adr/35-assimilation.md)

### Remote IAM {#remote-iam}

**State:** Designed

**Proved now:** **Law in place:** ADR 38 assigns future remote identity and authorization to Ward,
not the loopback Sigil.

**Do not expect yet:** There is no credential-backed principal, remote session, object
authorization, delegation, revocation, tenant isolation, or audit contract.

**Evidence**

- **Topic:** [Ward](./sepulcher/extensions/ward.md)
- **Law:** [ADR 38 — IAM](./adr/38-iam.md)

### A2A and Intercom {#a2a-intercom}

**State:** Designed

**Proved now:** **Law in place:** ADR 26 reserves a typed peer-protocol boundary.

**Do not expect yet:** There is no authenticated durable inbox/outbox, peer identity, message
ordering, deduplication, cancellation, delegation, effect receipt, or interoperability profile.

**Evidence**

- **Law:** [ADR 26 — Agent-to-Agent](./adr/26-a2a.md)

### x402 payments {#x402-payments}

**State:** Designed

**Proved now:** **Law in place:** ADR 41 assigns payment negotiation and settlement to Toll and
price discovery to future dispatch.

**Do not expect yet:** There is no quote, reservation, authorization, signer, payment, settlement,
reconciliation, budget enforcement, or safe response to an HTTP 402 challenge.

**Evidence**

- **Topic:** [Toll](./sepulcher/extensions/toll.md)
- **Law:** [ADR 41 — x402](./adr/41-x402.md)

### Legion federation {#legion-federation}

**State:** Designed

**Proved now:** **Law in place:** ADR 42 separates cognitive Master authority from node-local
physical authority and rejects shared databases and universal credentials.

**Do not expect yet:** There is no node enrollment, expiring advertisement, local resource
reservation, fencing, artifact transfer, durable spool, cancellation, or settlement. ADR 42's
accepted Node Agent protocol remains architecture rather than an implemented fleet.

**Evidence**

- **Topic:** [Legion](./sepulcher/extensions/legion.md)
- **Law:** [ADR 42 — Legion](./adr/42-legion.md)

### VPN Tether {#vpn-tether}

**State:** Designed

**Proved now:** **Law in place:** ADR 39 assigns private network transport to Tether.

**Do not expect yet:** There is no VPN provider, enrollment, key rotation, route policy, network
health, revocation, or proof that network reachability establishes identity.

**Evidence**

- **Topic:** [Tether](./sepulcher/extensions/tether.md)
- **Law:** [ADR 39 — VPN](./adr/39-vpn.md)

### Proxy Veil {#proxy-veil}

**State:** Designed

**Proved now:** **Law in place:** ADR 40 assigns edge proxy and TLS composition to Veil.

**Do not expect yet:** There is no proxy provider, certificate lifecycle, generated edge policy,
remote ingress hardening, or proof that a proxy substitutes for application authorization.

**Evidence**

- **Topic:** [Veil](./sepulcher/extensions/veil.md)
- **Law:** [ADR 40 — Proxy](./adr/40-proxy.md)

## Human ruling queue

These are constitutional or operational choices, not ordinary missing-feature tickets. Agents may
produce traces, failure probes, or small option spikes around them, but must not choose the policy or
grow a framework until the operator records a ruling in the owning ADR.

1. **Change-set custody.** Review and land the cathedral as bounded vertical slices. Runtime and
   persistence, animation and extensions, Altar, and Creation/Memory must remain separately
   understandable; merging one undifferentiated change set would make later archaeology and rollback
   needlessly dangerous.
2. **One-Vessel ownership and shutdown.** Choose whether deployment guarantees one process or
   startup must hold a PostgreSQL process lease. Independently choose whether a permanently hung
   queue disconnect may hold custody forever or a bounded deadline delegates final termination to
   the service manager. Agents must not silently invent either policy.
3. **Run authority and persistence.** Decide whether generic `RunLedger.set_status` is trusted to
   enter owner-bearing wait states or only `park_consent` and `park_delegate` may do so. Before
   separate workers or multi-process streaming, rule on a Step-event outbox, same-boot containment
   watchdog, subscriber backpressure, and process epoch fencing.
4. **Core Python ownership.** `domain/cortex/ledger.py`, `ghouls/runs.py`, `domain/cortex/engine.py`,
   web lifespan, Animator registry, and Orchestrator manager each retain multiple roles. Human review
   must name stable ports and transaction owners before role splitting; a mechanical file-splitting
   campaign would be churn, not architecture.
5. **Identity and effect-time authority.** The fixed local `magus:*` Sigil is not authentication.
   Remote use, autonomous promotion, and consequential external effects remain held until caller
   identity, object authority, delegation/revocation, trusted decision time, and effect-time
   reauthorization have an explicit owner.
6. **Extension trust.** Decide whether runtime/Rune/connector handles are trusted-live and whether an
   ownerless Portal may intentionally receive the passive `GenericPortal` fallback. Package trust,
   dependency locking, install/upgrade/uninstall, migrations, lifecycle effects, and SDK stability
   remain outside the synchronous registration seam. A generalized proxy or recursive-immutability
   framework is not authorized.
7. **Creation and autopoiesis.** The current Creation result is inert. Before promotion effects,
   design artifact-byte custody, workspace allocation, effect derivation from observed bytes,
   database recovery, target-owner capability, compatibility proof, rollback execution, and durable
   receipts. Claimant-provided changed paths and recovery digests are evidence inputs, not proof.
8. **Memory, RAG, and training.** Define the canonical derivation specification before persistence:
   which producer, revision, transform configuration, kind, and source fields a derivation key binds.
   Namespace authorization, purpose, privacy, correction, retention/deletion, sharing, license, and
   training eligibility must precede automatic capture, recall injection, RAG, or training.
9. **Delegated external effects.** A real agent runtime needs durable start/cancel operation identity,
   leases, process-tree containment, artifact custody, measured budgets, and terminal receipts.
   Process-local idempotency is not authority over a remote or long-lived external job.
10. **Egress and anonymization.** Secret-shaped key censoring plus Portal quarantine is a safe stop,
    not anonymization. Do not enable Portal dispatch until labels/lineage, deterministic transforms,
    declassification authority, exact pre-transmission decisions, retry semantics, and deletion
    propagation are ruled and tested.
11. **Nexus and browser intent.** Decide how a retained lost-ticket `409` identity is explicitly
    abandoned when the operator later intends genuinely new work for the same target. Durable ticket
    observations, cross-process event delivery, bounded subscriber queues, browser receipts, and
    grant-epoch cache invalidation remain separate follow-on work.
12. **Platform floor.** Exact no-replace filesystem publication currently requires Linux
    `renameat2`; macOS is not an equivalent test host. Keep a Linux CI receipt before merge and rule
    on the support matrix rather than adding a weaker fallback.

A2A, proxy, VPN, federation, autonomous training execution, and other remote expansion remain
deliberately deferred. They are not prerequisites for reviewing and stabilizing this local core.

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

This ledger is a threshold, not a destination. Perform [Summoning](./summoning.md) when you are ready to test one bounded local conjunction. Its four agreeing
observations are a bounded first-life result, not a maintained operator receipt; preserve them
with all metadata above, and let the observed result—not hope—decide what this page may claim next.
