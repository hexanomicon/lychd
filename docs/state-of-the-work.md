---
title: State of Work
icon: material/list-status
---

# State of Work

LychD is **pre-alpha**. This page answers the practical question that follows the grimoire's
promise: what can this revision actually support, and where is the evidence?

The current verified envelope is local, loopback-oriented, single-user, and one control process.
Start with an outcome below, then read the relevant record as a whole: its state, proved subset,
limit, and evidence belong together. The Covenants own architectural decisions; this ledger owns
their delivery interpretation.

## Outcome matrix

| Scenario | Answer now | Decisive limit |
| --- | --- | --- |
| CLI bootstrap | **Partial:** grammar, dry-run plans, transactional `init`/`bind`, bounded inspection, and guarded deletion have repository evidence. | No complete installed-host lifecycle receipt. See [CLI](#core-cli-rites) and [embodiment](#systemd-podman-embodiment). |
| Local text chat | **Partial:** warm-vLLM profiles retain a native Bridge reply; a dated 0cc0988 installed profile also completes one Run. | Current-source installed qualification and real-browser acceptance remain pending. See [vLLM](#vllm-integration), [Bridge](#bridge-surface) and [persistence](#phylactery-first-light). |
| Browser safety | **Loopback only:** a dedicated local credential precedes the fixed Sigil; Host, Origin, CORS, CSRF, and generated bind policy are bounded locally. | Remote IAM and hostile-browser acceptance remain unsupported. |
| PostgreSQL lifecycle | **Named warm-model receipts:** factory, PostgreSQL, SAQ, Graph and vLLM retain one structured Bridge reply across sequential application processes, including a source-CLI/Granian TCP trial. | Test-local two-boot assembly and a refusing host actuator; no installed restart, crash or browser proof. |
| Major blockers | Authenticated caller authority, privacy-safe egress, artifact custody, managed host/model lifecycle receipts, native Oculus, and resource-aware scheduling. | Remote transport, federation, executable evolution, durable recall, and vision/audio bytes remain Partial or Designed. |

## How to read this page

Choose the part of the body you are trying to assess:

| Concern | Records |
| --- | --- |
| Configuration, CLI, generated units, host effects, release and restore | [Inscription and embodiment](#inscription-and-embodiment) |
| Durable Runs, workers, Agent adapter, consent and delegated waits | [Persistence, execution, and consent](#persistence-execution-and-consent) |
| Model runtimes, grants, extensions and physical transitions | [Animation and orchestration](#animation-and-orchestration) |
| Atlas, Bridge, Nexus, Loom, Portfolio, Orb and diagnostics | [Altar and observability](#altar-and-observability) |
| Privacy, caller authority, web acquisition and media custody | [Authority and artifacts](#authority-and-artifacts) |
| Memory, identity, evaluation, training, creation and remote work | [Evolution and federation](#evolution-and-federation) |

Each state describes only its written boundary:

| State | Meaning |
| --- | --- |
| **Available** | Repository evidence supports the written boundary; this is not a production or remote-safety claim. |
| **Operator validation** | The software path exists, but the named real host, hardware, model, or engine receipt is missing. |
| **Partial** | A useful verified subset exists; the explicit not-yet boundary remains binding. |
| **Designed** | Law or design exists, but users cannot rely on the behavior. |
| **Experimental** | A runnable LychD path intentionally carries an unstable support contract; no current record has this state. |
| **External** | Another project owns the subject; this page records only LychD's interoperation boundary. |

Project maturity and delivery state are different. An accepted ADR does not prove implementation.

## Current evidence envelope

One maintained warm-model profile joins the real application factory, disposable PostgreSQL,
in-process SAQ, Graph, Dispatcher, Context and streamed vLLM output through TestClient HTTP. It
settles one structured Bridge reply and preserves its turns and model history across two
application lifespans. A separate maintained selection proves clean shutdown and identical
retained state across two sequential independent `spawn` processes, without second-boot inference.
A third dated selection invokes the source CLI and its owned native Granian launcher over real
loopback TCP. Authenticated readiness and four refused message admissions precede one settled
reply; a second normal boot retains identical turns and history with zero model POSTs. Settings,
Runes, a wrapper around the real production lifespan, and the refusing host actuator remain
explicit test composition. Native limits are per process after interpreter/module startup;
supplemental engine disposal is test cleanup. No aggregate native-resource, installed caged body,
model-byte, managed-model lifecycle, crash, shared-load, autonomy or real-browser qualification
follows. The broader repository two-boot test retains its separate offline-collaborator boundary.

A separate dated installed-source `0cc0988` observation joins canonical model activation, WARM
readiness and one Bridge Run with repeated same-boot API history and Orb reads. Its historical
source and remaining boundary are recorded under [vLLM](#vllm-integration); it does not qualify
the current checkout or extend the preceding restart receipts.

The disposable developer fixture supplies a separate read-only backend for source-client work.
It enters its own lifespan and uses the real controllers and security with memory services.
One labelled synthetic failed Run is shared by the Bridge and Orb projections and identifies
its exact registered Pattern revision in Loom. Focused tests cover startup, refusal of mutation
and execution, and cleanup; the sample records no graph, model, or host execution. Memory state
ends with the process.

For startup commands and the pending manual browser check, see “Browser development and its
backend” in [CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md). Browser
login, credential reuse, and the interactive Bridge–Orb–Loom journey remain unqualified. This fixture establishes
neither Linux host qualification nor production macOS support.

- **Source:** [Application factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py), [Developer fixture](https://github.com/hexanomicon/lychd/blob/main/src/lychd/developer.py)
- **Verification:** [Two-boot lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py), [Developer fixture tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_developer_fixture.py)
- **Law:** [Quality](./adr/03-quality.md), [Testing](./adr/04-testing.md), and [Isolated developer fixture](./adr/11-backend.md#isolated-developer-fixture-designed)

## Inscription and embodiment {#inscription-and-embodiment}

### Settings generations {#settings-generations}

**State:** Available

**Proved now:** Root Settings loads separate bootstrap, runtime and Phoenix database credentials,
the local HTTP access credential, and web signing key once per
construction as excluded `SecretStr` values. Cached consumers and in-memory snapshot restoration
perform no credential I/O; JSON and generated TOML omit credentials. Explicit new Settings reads
fresh inputs. Host bootstrap tolerates unprovisioned default mounts; runtime components reject
missing credentials. Uncaged bind preflight checks the captured bootstrap and runtime database
passwords, local access password, and signing key separately before compilation.

**Boundary:** This covers the core DB/web credentials, not every extension's credential handling
or live Podman provisioning. No automatic credential reload is delivered.

**Evidence**

- **Source:** [Settings](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/root.py), [Credential source](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/sources.py)
- **Verification:** [Credential tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_credentials.py), [Settings tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_settings.py), [Uncaged preflight tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_binding_preflight.py)
- **Law:** [Configuration](./adr/12-configuration.md)

### Rune configuration loading {#rune-configuration-loading}

**State:** Available

**Proved now:** Typed TOML Runes load from their declared hierarchy with validated filesystem
provenance and frozen root values; nested Animator Rune models and collections are immutable. The
writer walks the same exact admitted schema generation as the loader instead of every imported
subclass. Activation-marker detection and TOML parsing consume one file read, so replacement
between separate reads cannot activate an inactive generated sample.

**Boundary:** Configuration parsing and topology do not prove a CLI rite, generated host unit, or
running service.

**Evidence**

- **Source:** [Rune loader](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/runes/loader.py), [Rune writer](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/runes/writer.py)
- **Verification:** [Rune loader tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/runes/test_loader.py), [Rune writer tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/runes/test_writer.py)
- **Law:** [Configuration](./adr/12-configuration.md)

### Core CLI rites {#core-cli-rites}

**State:** Partial

**Proved now:** The closed command grammar, dry-run planners, journaled `init` and `bind`,
bounded `status` and `logs`, guarded lifecycle control, and receipt-gated deletion
are tested. Mutating paths use revalidation, no-follow identity checks, lifecycle locking, durable
receipts, and explicit rollback or indeterminate outcomes. An unsafe shared binding site blocks
initialization planning and the layout preflight; safe existing modes are preserved.

The machine-only installation-stop admission route verifies a bounded signed request and its
corresponding revision-2 reply, including the signed fixed `native-owned-lifespan@1` profile,
with no Basic credential disclosure, Sigil assignment or host effect. Only the captured native
entrypoint arms that profile; old/direct/caged/unarmed responders refuse. Current credential,
production publication and launcher gates close before shutdown awaits, including worker failure.
Host-side
client and sequential Vessel-first settlement logic have focused tests. The owned launcher now
exposes required startup/close failure and waits for Python HTTP callback retirement before
closing services. Seven real native TCP cases use an explicit inert factory, including interrupted
warmup, original encoded path bytes, pending response, post-response background work and repeated
SIGTERM; all owned process groups disappear. An actual generated-unit trial in an exclusive
delegated cgroup and private manager now passes three ordered cases: required-close failure
preserves dependencies; clean closure retains strict exit fields through dependent stop; actual
reference-connection loss after clean capture refuses dependent stop. A held full user-bus
reference prevents premature systemd metadata collection and verifies the manager against its
private control socket. All three cases removed owned processes, listeners and the outer cgroup.
Public host completion is connected lazily for the exact uncaged native profile; composition
tests exercise the admission and reference ports without importing the application at bootstrap.
These manager cases use an explicit inert application and synthetic dependencies. The image
entrypoint shares the runner, but no rebuilt image or caged TCP receipt is claimed.

**Boundary — Not yet:** Status omits full readiness and durable-run health; no run-operation command
or authenticated Run submission route is delivered; active caged or mixed `stop` still refuses;
deletion preserves objects whose creation provenance is not owned.
Unknown unit or mount truth blocks instead of guessing. Native manager mechanism evidence does
not qualify useful composed application work under that launcher. No maintained installed
systemd/Podman lifecycle or GPU receipt exists.

**Evidence**

- **Source:** [CLI assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__main__.py) and [layout admission](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/layout.py)
- **Verification:** [CLI tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py) and [init binding-site tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_init_binding_sites.py)
- **Verification:** [Message profile](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/operator/test_admission.py), [machine HTTP boundary](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_lifecycle_admission.py), [host client](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/operator/test_admission_client.py), and [active-stop settlement candidate](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/operator/test_active_stop.py)
- **Source:** [Owned launcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/server.py)
- **Verification:** [Lifespan/retirement tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_server.py) and [native TCP mechanism cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_server_process.py)
- **Verification:** [Required native manager regression](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_native_stop_systemd.py), [inert native factory](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/web/systemd_server_app.py), [private full-bus fixture](https://github.com/hexanomicon/lychd/blob/main/tests/support/native_stop_bus.py), and [delegation preflight](https://github.com/hexanomicon/lychd/blob/main/tests/support/systemd_transaction.py)
- **Verification:** [Exit-reference tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/operator/test_stop_evidence.py) and [public composition wiring](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/operator/test_composition.py)
- **Law:** [CLI](./adr/19-cli.md) and [Layout](./adr/13-layout.md)

### Public release artifact chain {#public-release-artifact-chain}

**State:** Designed

**Proved now:** Distribution, container, archive-audit, source-preflight, and non-publishing
candidate declarations exist and are tested without granting publish authority. Synthetic wheel
archives exercise exact license-header validation, package identity, source revision, and bundled
license and notice checks.

**Do not expect yet:** No maintained receipt pairs this revision as one anonymously installable
PyPI package and immutable GHCR image, and no clean-host install/start/reply/stop promotion gate
has run.

**Evidence**

- **Source:** [Package version](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__about__.py) and [archive auditor](https://github.com/hexanomicon/lychd/blob/main/scripts/verify_release_artifacts.py)
- **Verification:** [Release artifact tests](https://github.com/hexanomicon/lychd/blob/main/tests/architecture/test_release_legal_artifacts.py)
- **Version:** [Distribution declaration](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
- **Law:** [Packaging](./adr/17-packaging.md)

### Deployment-plan compilation and materialization {#deployment-plan-materialization}

**State:** Available

**Proved now:** Soulstone and extension intent compile into validated Quadlet/systemd plans,
including Animator targets, conflict topology, and compatible Coven aggregates, and Scribe
materializes the declared files. A complete ownership manifest refuses distinct Quadlet/systemd
runtime-bearing sources that systemd would resolve to one runtime unit. Returned extension
containers are revalidated before admission. Raw Podman arguments are restricted to their supported
complete values, rejecting alternate publication, network, host-mount, device, user, and secret
controls. Bind includes external secret sources from every emitted container in its presence and
drift checks; generated Core secrets retain their separate provisioning path.

**Boundary:** Generated unit intent does not prove that systemd or Podman started it on a real host.

**Evidence**

- **Source:** [Deployment transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py), [bind compilation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/bind_compilation.py), [container-policy validation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/schemas.py), and [Scribe ownership manifest](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scribe/models.py)
- **Verification:** [Transmutation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute.py), [compiled bind tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_bind_compilation.py), and [Scribe tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scribe.py)
- **Law:** [Containers](./adr/08-containers.md)

### Runtime actuation and mediated Host Reactor protocol {#host-reactor-protocol}

**State:** Available

**Proved now:** The mediated Host Reactor validates and durably claims intent, attests the loaded
Scribe graph, performs one bounded target transaction, observes settlement, attempts
exact-prior-world compensation, resumes or contains interrupted journal work, and records outcomes
under the lifecycle lock.

Claimed producer bytes pass through a separate acquisition state into a new host-owned snapshot
and versioned digest companion before effects. Retained producer descriptors and hard links
cannot mutate processing or completed authority; processing and compensation reject missing or
mismatched custody, including legacy journal files without proof.

**Boundary:** Protocol tests and an isolated private-systemd receipt use inert services, not the
operator's Quadlet/Podman/GPU host. `.restored` proves the prior world; `.contained` and unresolved
`.processing` and `.acquiring` fence later admission. General repair and legacy-custody
reconciliation remain the operator's responsibility.

**Evidence**

- **Source:** [Host Reactor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/reactor.py)
- **Verification:** [Reactor tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_reactor.py) and [private-systemd receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_target_transaction.py)
- **Law:** [Privilege](./adr/10-privilege.md)

### systemd user and rootless Podman embodiment {#systemd-podman-embodiment}

**State:** Operator validation

**Proved now:** LychD generates its declared Linux service shape and provides a mediated actuator;
Soulstone and Phoenix retain separate identities while sharing validated embedded Quadlet
configuration. An isolated Linux receipt also runs the generated conflict targets through
systemd 261.2 and Quadlet/Podman 6.0.2 with real rootless containers: the first is observed running,
then absent before the second starts; exact owned containers and processes are cleaned up.
The fixture uses a private user manager and image store, a pinned offline image, and no host
mounts, ports, GPUs, model or production configuration.

Compilation explicitly selects the PostgreSQL image account alongside Pod-level `keep-id`,
confines `:U` ownership changes to its dedicated datastore, and rejects Soulstone mounts of known
host credential/control roots or special files. Existing mapped PGDATA is preserved by init
without entering or changing it. Fresh Btrfs preparation and deletion identity checks use a
bounded descriptor helper to observe the exact subvolume UUID and ID without a privileged
pathname lookup. Unknown identity remains unreceipted; existing datastores are never adopted or
retroactively changed to No-COW. Vessel/migrator code is root-owned and their root filesystems
are declared read-only. Their compiled manifests declare a fixed 1 MiB `/run/secrets` tmpfs
parent for the separately mounted secret files; focused tests preserve hardening, configured
secret identities, and the closed manifest policy.

The dated 0cc0988 installed startup/activation observation is scoped under
[vLLM](#vllm-integration). A changed compiler or loaded-graph attestor needs a new same-source
installed profile; that observation contains no Coven and does not qualify the current checkout.

**Receipt needed:** Name the Linux, systemd and Podman versions, generated targets and conflicts,
loaded-source attestation, forward switch, compensation, crash recovery, startup, and shutdown.
GPU and model proof remains separate. Include image account, actual UID/GID maps, mounted secret
readability, read-only code, writable scratch, initial database creation, and repeated init/start
with existing mapped data; compilation and mocked ownership tests do not establish these facts.

**Evidence**

- **Source:** [Quadlet configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/quadlet.py)
- **Verification:** [Isolated Quadlet transaction](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_quadlet_transaction.py), [runtime protocol tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py), [datastore custody tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_datastore_custody.py), and [mount authority tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_mount_authority.py)
- **Verification:** [Btrfs preparation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_btrfs.py), [descriptor observer tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_btrfs_observer.py), and [deletion identity tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_deletion_storage.py)
- **Law:** [Containers](./adr/08-containers.md)

### Whole-body snapshot and restore {#whole-body-snapshot-restore}

**State:** Designed

**Proved now:** Filesystem preparation exists and the snapshot Covenant defines coordinated
filesystem, database, code, and receipt identity.

**Do not expect yet:** LychD does not freeze, snapshot, restore, and reconcile the whole body as one
ritual.

**Evidence**

- **Source:** [Btrfs preparation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/btrfs.py)
- **Verification:** [Layout tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_layout.py)
- **Law:** [Snapshots](./adr/07-snapshots.md)

### Tomb untrusted execution {#tomb-untrusted-execution}

**State:** Designed

**Proved now:** Security law reserves Tomb as the lower-trust execution boundary.

**Do not expect yet:** There is no Tomb queue, executor, credential policy, Landlock, or `nono`
integration.

**Evidence**

- **Law:** [Security](./adr/09-security.md)

## Persistence, execution, and consent {#persistence-execution-and-consent}

### Phylactery first-light persistence {#phylactery-first-light}

**State:** Partial

**Proved now:** Run, delivery, step, session, consent, checkpoint, and delegated-wait shapes exist
with sequence-fenced claim and settlement, terminal-evidence-fenced owner-specific resume gates,
startup reconciliation, and PostgreSQL migration checks. A real factory receipt completes and
recovers a Bridge Run across two boots; a selected warm-vLLM profile also retains its actual
structured reply and model history across two application lifespans and, in a separate trial,
across clean shutdown into an independent application process. A further source-CLI/native
Granian TCP trial retains the same settled state across two normal independent boots, with no
second-boot model POST. Distinct production asyncpg codecs round-trip plain `json` and versioned
JSONB, while memory Run, consent, and Bridge-session stores detach mutable values at the same
public boundary as database reads.

The bootstrap gate separates the preserved administrator from the Vessel/SAQ runtime role and
Phoenix's own database role. The maintained PostgreSQL receipt verifies credential-required TCP,
runtime data and queue operations, denial of schema/role/version-table mutation and cross-database
access, repeatable bootstrap, and preservation of unrelated existing ownership.

**Boundary — Not yet:** PostgreSQL and SAQ are not one transaction; Step events lack an outbox;
memory-profile/PostgreSQL repository parity is incomplete; no general record-retention or
compaction path, partition policy, tablespace lifecycle, automatic capacity expansion, or sharding
path is delivered; persistent same-boot containment failure has no durable watchdog. The lifecycle
test substitutes offline collaborators after startup. The separate warm-model profiles use
explicit test composition and do not exercise checkpoint-plus-consent recovery, process crash,
an installed caged body, or the browser.

**Evidence**

- **Source:** [First-light migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0001_phylactery_first_light.py), [wait-owner migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0008_wait_owner_evidence.py), and [database factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/factory.py)
- **Verification:** [Run ledger tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py), [PostgreSQL run-ledger receipts](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py), [database authority receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_database_authority_pg.py), and [two-boot lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Verification:** [Joined warm-model Bridge test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_runtime.py), [maintained receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-runtime.json), and [receipt freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_receipt.py)
- **Verification:** [Independent-process restart test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_process_restart.py), [maintained process receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-process-restart.json), and [process-receipt freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_process_receipt.py)
- **Verification:** [Native CLI/TCP restart test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_native_tcp.py), [maintained native TCP receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-native-tcp.json), and [native receipt freshness/privacy](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_native_tcp_receipt.py)
- **Law:** [Persistence](./adr/06-persistence.md)

### Topology-A local run execution {#topology-a-local-runs}

**State:** Available

**Proved now:** One Vessel process admits, claims, executes, cancels, settles, resumes, and projects
Runs against immutable Pattern revisions. Durable publication intent, replay repair, external-wait
relays with capped restart backoff, terminal-evidence repair, bounded identity fencing, bounded
slow-reader resynchronization, and orderly shutdown are tested.
Terminal checkpoint deletion is best-effort after durable terminal evidence. A disposable
[PostgreSQL receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_terminal_checkpoint_recovery_pg.py)
injects an actual deletion failure, verifies later Run evidence and cleanup,
and removes retained debt through replacement adapters without duplicate Steps. It uses the
startup helper and ORM-created tables, not a replacement application process or migrations.
Per-Run claim and park coordination prevents stale failure cleanup from touching a successor or a
committed wait. Consent and delegate recovery bound each owner's lookup and re-admission,
preserving the wait or exact pending delivery on timeout while later owners progress. Early
workflow/checkpoint refusal contains child effects before failure; post-park probes also have
deadlines so they release their workers. Post-claim exception groups composed only of cancellation
and ordinary failures preserve cancellation election, exact-generation containment, terminal
cleanup, and propagation of the original group after successful handling.
Unresolved child containment stays nonterminal rather than claiming false `FAILED` truth; a timed-
out cancellation remains `CANCELLING`. Exact revision lookup validates the persisted v2 Pattern
snapshot and digest against the registered manifest, including its reviewed implementation
revision; retained inactive revisions remain executable through that same check.
Registry assembly also freezes a private `legacy_inline` contract, placement and implementation
binding for each executable station. Exact lookup compares the current local binding with its
boot-derived `internal-v0` lock; a mismatch refuses execution and active routing cannot fall back
to the default. Terminal stations remain declarative. Public v2 snapshots and digests are unchanged.
The retained-snapshot validator shares declarative station and score checks with construction;
rehashed malformed nodes, edges, duplicates and undeclared endpoints refuse before Blockworld
freezing or Orb exactness. This does not replace exact registered execution lookup.

Failed claim acknowledgements retain an immutable attempt outcome. Recovery waits for the original
mutator to finish and keeps the same per-Run guard from the unclaimed prestate through exceptional
observation. Only the exact `RUNNING`/`CLAIMED` generation proves ownership for existing interrupted
settlement; that winner never enters Graph. Corrupt exact `QUEUED` delivery pairs refuse before
mutation. In-process fault tests cover ownership, error precedence and these effect boundaries.

**Boundary:** This does not prove automatic source compatibility, a transactional event outbox,
separate-worker truth, multi-process streaming, federation, or producer backpressure. The private
binding lock is not persisted on Run or exposed by Loom/Orb; it proves neither Python source
equivalence nor compatibility across boots. No portable Resolution Lock or public Spell or Scroll
contribution store is delivered.

The exceptional native observer has a five-second cooperative acceptance budget and terminates
acquired handles synchronously; its control flow is tested with substituted driver connections.
The original claim operation has no new lifecycle bound. Real PostgreSQL transaction, authority,
locking, cancellation and Linux startup/CancelRequest transport recovery remain unverified.
Handle termination proves neither completed server rollback nor reclamation of library-owned
transports, callbacks or DNS work.

**Evidence**

- **Source:** [Run engine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py), [worker and recovery](https://github.com/hexanomicon/lychd/blob/main/src/lychd/ghouls/runs.py), [claim coordination](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/claims.py), [claim ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/ledger.py), [native claim observer](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/claim_observer.py), [event bus](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/events.py), [workflow resolution](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py), and [startup relay](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/lifespan.py)
- **Verification:** [Run engine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py), [worker ownership tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_perform_run.py), [claim ledger tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py), [native observer control-flow tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_claim_observer.py), [consent park tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_consent_resume.py), [consent reconciliation tests](https://github.com/hexanomicon/lychd/blob/main/tests/cortex/test_reconcile.py), [event-bus tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_events.py), [workflow identity tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_state_serializable.py), and [lifespan tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_lifespan.py)
- **Verification:** [Private v2 bindings](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_legacy_inline.py) and [exact lookup and routing](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_router.py)
- **Verification:** [Retained-score validation](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_state_serializable.py), [Blockworld admission](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/blockworld/test_placement.py), and [Orb exactness](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb.py)
- **Law:** [Workers](./adr/14-workers.md) and [Workflow](./adr/28-workflow.md)

### Configured Bridge casting {#configured-bridge-casting}

**State:** Partial

**Proved now:** Typed `weaver.bridge` settings select registered `bridge_chat@2` and one exact
capability key. Admission persists that key with Run intent before queue publication. Controlled
queued and consent-resume workflows reconstruct JSON-decoded stores and keep the original selection
after configuration changes or removal, including idempotent retries. Dispatcher applies the exact
key together with family, modalities, tools, readiness, and drain constraints; duplicate model
aliases cannot redirect the turn. Missing or mismatched checkpoint bindings refuse execution before
a node runs. Revision 1 keeps its original manifest and remains executable after activation changes.
The same selector also admits the bounded [public-note](#karma-semantic-memory) and
[Scout public-page](#scout-web-acquisition) revisions; their authority and evidence boundaries
remain with those records.

**Boundary — Not yet:** This pins capability identity, not a model artifact or runtime declaration
generation. No configurable pool, portable Resolution Lock, general Pattern/AgentSpec/Context
selector, or live-model receipt is delivered by this slice. Settings validation does not contact an
engine; unknown or incompatible capability keys fail at execution. The database JSON adapter is
covered without claiming a PostgreSQL restart receipt.

**Evidence**

- **Source:** [Weaver settings](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/weaver.py), [Bridge workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/bridge_chat.py), and [Dispatcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/dispatcher.py)
- **Verification:** [Configuration tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_weaver_settings.py), [configured registry tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_configured_registry.py), [casting workflows](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_bridge_casting_workflow.py), and [exact selection tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_dispatcher_exact_selection.py)
- **Topic:** [Choose a Bridge capability](./sepulcher/extensions/weaver/index.md#choose-a-bridge-capability)
- **Law:** [Configuration](./adr/12-configuration.md), [Workflow](./adr/28-workflow.md), and [Dispatcher](./adr/22-dispatcher.md)

### Pydantic AI 2.55.0 cognitive adapter {#pydantic-ai-adapter}

**State:** Available

**Proved now:** LychD constructs typed agents and runs Bridge through the exact
`pydantic-ai-slim==2.55.0` contract with serializable state and fail-closed provider profiles.
The context window bounds each model request after output reservation, including tool follow-ups
and validation retries, while cumulative Run usage remains intact. Supported pre-counts and
completed streamed/non-streamed responses use the same request bound.
The event-consumer scope closes Agent toolsets before releasing the model grant on failure.
Explicit `end_strategy="early"` preserves the final-output boundary for streamed and ordinary
responses; sibling function tools are not executed after a valid final output. Generic local
profiles replace provider defaults and disable the optional Responses input-token-counting
endpoint. Bridge skips that unsupported counter while preserving other counting implementations
and reported response-usage checks. Named providers resolve their own model policy.
Model transport tests use native HTTPX2 mocks, and the repository-wide model-request guard also
applies when tests outside the agent package are selected alone. Portable agent and core checks
exercise the locked Pydantic 2.14.0 stack on Python 3.14.8 and 3.15.0.

**Boundary:** This does not claim automatic child-Agent usage propagation, Pydantic's external
durability harnesses, or a guaranteed token preflight fence for generic local models. The counting
checks use inert transport; they do not qualify a live provider endpoint, PostgreSQL deployment,
or Linux Vessel image, or admit Portal execution. The serial Graph adapter has its own [evidence and limits](#pydantic-ai-v2-migration).

**Evidence**

- **Source:** [Agent factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py), [model profiles](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/model_factory.py), [Bridge request policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/bridge_chat.py), and [request context bound](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/context_limits.py)
- **Verification:** [Provider factory tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_factory.py), [counting policy](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_model_counting_policy.py), [final-output policy](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_agent_completion_policy.py), [offline request guard](https://github.com/hexanomicon/lychd/blob/main/tests/test_offline_model_floor.py), [Bridge context-limit tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_bridge_chat_graph.py), and [event-consumer cleanup](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_agent_events.py)
- **Version:** [Dependency](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
- **Law:** [Agents](./adr/20-agents.md)

### Native Pydantic Graph 2.55.0 adapter {#pydantic-ai-v2-migration}

**State:** Available

**Proved now:** Workflows use native GraphBuilder and public BaseNode execution through a serial
adapter. LychD owns the typed checkpoint envelope, admitted node catalog, station execution
status and declared-successor checks. State, node arguments and final output are checked against
their declared types in JSON mode before replacing retained history and again on restore. Strict
UUID and tuple values survive a JSON transfer into a replacement runner. Validation starts at the
serialized JSON boundary; serializers can normalize in-memory values before these checks.
Existing built-in Pattern digests stay unchanged. Captured
v1 consent and delegation histories decode against the exact registered graph; captured consent
approval and denial resume through the new runner, and hardware retry budgets survive decoding.

**Boundary:** Forks, joins, arbitrary function steps and transformed paths are refused because
the delivered durable cursor represents one BaseNode station. Pending, running and failed
snapshots are not automatically replayed. These offline compatibility receipts do not prove a
production upgrade, process replacement, exactly-once host effects or external durability engines.

**Evidence**

- **Source:** [Serial graph construction](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph.py), [GraphRunner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py), and [checkpoint codec](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/stasis.py)
- **Verification:** [Native graph and typed-write refusals](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_native_graph_contract.py), [captured checkpoint compatibility](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_graph_checkpoint_codec.py), [rehydration](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_rehydration.py), and [capability workflow recovery](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_capability_graph_workflow.py)
- **Version:** [Dependency](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
- **Law:** [Agents](./adr/20-agents.md) and [Graph](./adr/24-graph.md)

### Graph stasis and consent re-admission {#graph-stasis-consent}

**State:** Partial

**Proved now:** Logical parking, bounded approval rounds, exact Consent ownership, simulated
restart, re-admission, idempotent settlement, and fail-closed substitution on resume are tested.
Post-park probe failure preserves `AWAITING_CONSENT`; uncertain cancellation containment leaves the
Run `CANCELLING` instead of manufacturing terminal truth. Composed native-worker cancellation
releases its lease for broker acknowledgement while retaining the durable checkpoint until terminal
commitment, including a lost acknowledgement followed by an idempotent cancellation retry.
Consent policy stops preserve earlier completed tool results, close known refused calls as denied,
and leave valid history for the next turn without replaying those effects.

Hardware convergence budgets are
checkpoint-owned per Run and survive a durable park plus a replacement GraphRunner.

Combined offline cases reconstruct JSON-decoded stores across checkpoint-before-park,
verdict-before-resume-publication, and terminal-commit-before-checkpoint-deletion windows, including
approval and denial. Stale deliveries do not replay the inert tool; terminal cleanup and evidence
repair are idempotent under these controlled collaborators.

Ordinary node-observer failures preserve successful execution, original failures, and consent,
delegation, or hardware waits; cancellation remains observable to the caller.

**Boundary — Not yet:** There is no PostgreSQL Consent-plus-Checkpoint restart receipt. A legacy
checkpoint from before the hardware-budget field cannot reconstruct attempts that already
happened. Multiple approval calls in one model response are rejected, and no production toolset
currently originates approval.

**Evidence**

- **Source:** [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py), [Run engine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py), and [Worker settlement](https://github.com/hexanomicon/lychd/blob/main/src/lychd/ghouls/runs.py)
- **Verification:** [Consent resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_consent_resume.py), [Run engine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py), [rehydration tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_rehydration.py), [offline recovery windows](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_offline_recovery_workflow.py), [composed Bridge resume and cancellation](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_bridge_casting_workflow.py), and [node-observer failures](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_graph_observer_failures.py)
- **Law:** [Graph](./adr/24-graph.md) and [Human in the Loop](./adr/25-hitl.md)

### Delegated agent execution {#delegated-agent-execution}

**State:** Partial

**Proved now:** Typed requests without credential or ambient-authority fields, artifact references, process-local job
submission/adoption/cancellation serialized with runtime-start acceptance, exact wait ownership,
terminal-evidenced Graph parking and re-admission, typed containment-profile intent, PostgreSQL
shapes, and a no-effect reference adapter exist. Optional `weaver.delegation` selects
`delegated_rite@2` with one exact registered runtime/profile. Admission, persisted intent and
checkpoint validation retain that binding across configuration changes; omission preserves
reference-only revision 1. Refusal and uncertain start never select an alternate runtime.

Codex 0.159.2 and Claude Code 2.1.296 have bounded one-shot command/protocol adapters behind a
refusing-by-default host port. Offline fixtures exercise complete JSONL outcomes, exact launch
identity, persisted limits, malformed/truncated output, uncertain lookup and cancellation. The
adapters are not registered by default and contain no subprocess launcher. These are protocol and
correlation tests, not an executed Coffin or Provider Gate.

Poll and cancellation receive the store-retained request. Legacy lookup rejects substituted
request metadata or UTF-8 stdin even with a consistently recomputed host receipt. The reference
runtime checks its retained pure projection. Legacy request, nested job and launch goldens and
retained score revisions 1 and 2 keep their meaning; fresh legacy CLI starts now refuse before
calling a host.

A sibling V2 CLI request retains the exact compiler/version, executable/model, workspace roots,
capture/wall limits and four qualified operator task/projection/custody/verification references.
Explicit top-level, nested-job and database codecs refuse unknown tags/fields and malformed or
bypassed model instances. V2 lookup/cancellation independently compiles the complete expected
specification from retained intent, defeating consistent model, argv, environment, executable,
root, limit and owner-binding substitutions. It never obtains fresh admission or launches.

A trusted injected owner-observation port denies by default. Its consumer checks exact occurrence,
request/intent digests, bindings and bounded validity as UTC instants before host launch, including
non-UTC offset/fold cases. The only positive producer is an inert test fixture: this is consumer
conformance, not actual owner authorization, source-byte closure, custody or verifier reservation.
A migrated-PostgreSQL receipt retains complete V2 JSON, rejects changed-content replay, reconstructs
fresh engines/adapters under different defaults and refuses consistently recomputed substitutions,
including cancellation before poll after admission expiry. Unknown stored versions remain unchanged
and unavailable. This is adapter reconstruction, not a V2 independent-process or physical-host proof.

A separate mechanical host-disposition store retains exact canonical V2 preparation, one
issuer-local dispatch opportunity and monotonic logical intake closure under the AgentJob lock.
Replay and adapter replacement return history without recreating a fresh handle. A migrated
PostgreSQL receipt covers concurrent preparation/close/consumption, lost acknowledgement, strict
current-request identity, restrictive history and both downgrade/writer lock orders. Logical close
remains possible for damaged intent. This precursor supplies no owner permit, runtime launch,
physical closure or restore activation.

The reference adapter reconstructs its deterministic projection for refresh and cancellation after
coordinator/runtime restart without replaying an external effect, retains it across failed durable
adoption, and retires it after terminal settlement. Oversized reference echoes retain a successful
effect-free result with an explicit truncation marker, including after reconstruction. This does
not qualify truncated output from a foreign runtime. Oversized start-error diagnostics
retain an explicit truncation marker without preventing `LOST` settlement.

An unclassified runtime-start exception now
records `LOST`; inert lost-acknowledgement tests prove exact-request replay cannot start again,
late success cannot replace that terminal, and cancellation still reaches the owning runtime.

After start returns, an ordinary acceptance-write failure triggers one conditional settlement.
A committed `RUNNING` or terminal result is preserved; only `PREPARING` under the store's mutation
lock becomes `LOST`. Repeated caller cancellation waits for that disposition, without repeating
the write or runtime start. Reference-runtime, Graph, and worker tests prove that preserved
`RUNNING` can resume once to completion, while newly `LOST` work is contained before Run failure.
Portable DB-adapter tests model lock ordering and rollback with session doubles. Additional
disposable PostgreSQL cases observe the exact challenger backend blocked on the winning job's
locking SELECT, preserve RUNNING and terminal winners, fence late RUNNING after LOST, and retain
one result event across duplicate settlement. A real event-INSERT constraint failure rolls back
the preceding job/result change; removing the constraint permits one fresh settlement. These cases
use independent sessions and ORM-created tables, not migrations,
replacement processes, broker delivery, foreign-provider recovery, or application startup.

Separate Alembic receipts exercise terminal delegated-result enforcement on migrated PostgreSQL:
upgrade refuses absent, non-object or mismatched retained evidence without changing the version
or data; explicit correction permits the upgrade. At head, the database rejects equivalent
invalid inserts and updates. An empty head-to-pre-delegation-and-back cycle verifies schema
reversibility only; it does not qualify retained-history rollback.

A separate migrated-PostgreSQL receipt runs two sequential independent `spawn` processes. The
first commits one `delegated_rite@2` wait and exits; the second reconstructs all adapters,
rehydrates the effect-free reference result and resumes the same request/job once. A changed
current admission profile does not replace the retained binding. Exact replay, repeated
reconciliation and stale/current deliveries leave one adoption, resume hop and settled turn.
The queue is captured and neighboring capability/consent ports are inert; clean process
replacement proves neither abrupt-crash recovery, broker delivery, application startup nor an
external provider.

**Boundary — Not yet:** No declared external provider launches. There is no lower-trust executor,
credential or egress isolation, process-tree containment, durable artifact custody, measured
budgets, real external-provider recovery receipt, or live-browser proof. The actual operator-record
producer, current authority/revocation, immutable source closure, full enforced resource envelope,
custody service and reserved independent verification remain undelivered.
Request prompts are persisted verbatim; callers must apply the Privacy Cut and egress policy before
any future remote runtime receives them. Effectful runtimes still need durable provider identity,
definite-rejection evidence, and reconciliation of ambiguous start outcomes.

**Evidence**

- **Source:** [Delegation coordinator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/delegation/services.py), [delegated job store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/delegation.py), [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py), [reference runtime](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/reference.py), and [reference adapter catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/register.py)
- **Verification:** [Delegation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_coordinator.py), [ambiguous-start tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_start_outcomes.py), [acceptance-write recovery](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_acceptance_failure.py), [acceptance through Graph and worker](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_delegate_acceptance.py), [modeled DB acceptance](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_delegation_acceptance.py), [restart-resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_delegate_resume.py), [delegation schema tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_delegation_schema.py), and [extension-policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py)
- **Source:** [Mechanical host-disposition store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/delegated_host.py) and [typed preparation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/delegation/host_disposition.py)
- **Verification:** [Preparation codec tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_host_disposition.py) and [migrated host-disposition receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_delegated_host_disposition_pg.py)
- **Law:** [Workers](./adr/14-workers.md)

Additional source and verification for the exact selection and closed adapters:
[runtime protocols](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/delegation/cli_protocol.py),
[runtime boundary](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/delegation/cli_runtime.py),
[adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_cli_runtime.py),
[configured casting tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_delegated_routing.py),
[PostgreSQL acceptance/rollback tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py),
[migrated delegated-result enforcement](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_migrations_pg.py), and
[clean-process delegated recovery](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_delegated_process_recovery_pg.py),
[V2 codec/admission/recovery cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_cli_request_v2.py), and
[migrated V2 retention](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_delegated_cli_v2_pg.py).

### Durable in-app Attention {#durable-attention}

**State:** Designed

**Proved now:** Bridge consent cards and shared invalidation-aware counts establish a bounded
projection that a future Attention inbox can consume.

**Do not expect yet:** There is no owned inbox, acknowledgement, retry, expiry, escalation,
notification delivery, or external channel.

**Evidence**

- **Source:** [Bridge consent projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py)
- **Verification:** [Consent endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_consent_endpoint.py)
- **Law:** [Frontend](./adr/15-frontend.md)

## Animation and orchestration {#animation-and-orchestration}

### Animator dispatch spine {#animator-dispatch-spine}

**State:** Available

**Proved now:** One-shot catalogue hydration, matching, probe publication, grant issue and
settlement, and lease-aware dispatch are tested with duplicate attribution, snapshot isolation,
cancellation invalidation, and strict endpoint-root policy.
Grant scope closes model-provider clients before lease release, including failure, cancellation,
and an admission race after hydration. A per-Animator admission generation rejects preparation
that spans a completed drain and reopen, including asynchronous grant issue and provider entry.
Inert hard-swap and soft-reload cases verify refusal without a lease or dispatch event, provider
cleanup, and fresh redispatch; an unrelated Animator's drain does not invalidate the grant.
OpenAI-shaped clients discard ambient SDK account, admin, webhook, and custom-header configuration;
request tests prove that only the declared credential reaches the configured endpoint.
Model, readiness, and local control-plane clients also ignore ambient HTTP proxies and refuse
redirect following. Inert transport tests observe direct routing for local prompts and TabbyAPI
admin credentials, including streaming load requests. Model clients preserve that policy after
close and re-entry and make no implicit SDK retransmission after a server error or lost response.
These checks do not implement anonymization, a Provider Gate, or remote fallback.

A non-empty Soulstone `[[models]]`
catalogue is an ordered exact allowlist, capability concurrency must match its Rune,
concrete runtime leaves cannot claim a foreign adapter,
and only an exact registered Portal definition can create a Portal runtime or capability.

Every issue re-probes the exact chosen record rather than trusting cached warmth. Fixed
OpenAI-compatible local and opt-in Portal probes
validate `/models` inventory and warm only an exact returned model id; malformed or missing
inventory fails closed, and inventory count and id length are bounded before retention.

A `served_model_id` Rune field pins the provider-facing identity when it differs from a path or
Soulstone name.

The v1 grant exposes no Animator or Connector: `chat` admits a hydrated model and
only declared agent-loop toolsets, `tool_execution` requires a non-empty toolset, and all
metadata-only families fail closed. There is no public registry handle-binding bypass around grant
issue. Registry and Dispatcher both quarantine Portal issue.

An explicitly configured local `model.embed@1` compatibility path now leases the exact
Qwen3-Embedding-0.6B Q8_0/llama.cpp b9445 profile. It accepts one bounded document or query,
reauthorizes before each source-bearing request, validates canonical float32 vectors, and closes
active requests before releasing the ordinary lease. Unsupported profile selectors refuse before
readiness. A maintained opt-in CPU-only isolated runtime check exercised the real registry, Dispatcher and
HTTPX driver for two documents and one query, plus byte/token/authority/scope refusals; leases and
owned runtime processes were cleaned up. This was an externally started fixture, not an
Orchestrator activation or Archive derivation test. The Linux harness requires an existing pinned
image and public model fixture; it verifies artifact hashes and owned-process cleanup without
downloading or relabeling inputs. Ordinary integration tests substitute HTTP.

Unregistered runtime aliases, including generic OpenAI-shaped labels, retain inert command planning
but cannot create a capability-bearing runtime; Bind and registry load reject their missing
capability coverage.

**Boundary:** This is the v1 `{animator}:{family}:{model_id}` catalogue with one chat-model/toolset
compatibility grant plus the explicitly selected embedding path, not the general discriminated
grant union. The catalogue has no in-process hot reload; lease expiry is recorded but not enforced;
current Soulstone/Portal inheritance and raw
Quadlet contribution remain. General interface/profile compilation, call/job/session grants,
`[[capabilities]]`, service-job attempts, general per-dialect OpenAI-compatible drivers, and
secret-vault integration are not delivered. The fixed embedding profile is configured admission;
health/inventory does not attest a replaced model file or process. Its laboratory resource and
network limits are not general deployment guarantees, and its tiny cosine check is not a quality
benchmark.

**Evidence**

- **Source:** [Animator registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/registry.py),
  [grant lifecycle](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/dispatcher.py),
  [Soulstone Rune schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/runes/animators.py),
  [OpenAI-compatible probe](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/shared.py),
  [fixed-runtime projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/openai_compat.py),
  and [bounded embedding driver](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/llamacpp/embedding.py)
- **Verification:** [Registry tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py),
  [model transport tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_model_transport.py),
  [control-plane transport tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/lib/test_control_plane_transport.py),
  [grant lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_dispatcher.py),
  [admission-generation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_dispatcher_admission_generation.py),
  [runtime adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py),
  [unregistered-runtime admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_unregistered_runtime_admission.py),
  [catalogue tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_catalog.py),
  [endpoint-policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_soulstone_endpoint_policy.py),
  [declaration-compiler tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_declarations.py),
  [Portal tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_portals.py),
  [configured embedding dispatch tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_llamacpp_embedding_dispatch.py),
  [embedding dialect receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/embeddings/qwen3-06b-q8-b9445.json),
  [recorded real-driver receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/embeddings/qwen3-06b-q8-b9445-dispatch.json),
  [opt-in runtime test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_llamacpp_embedding_runtime.py),
  and [maintained runtime receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/embeddings/qwen3-06b-q8-b9445-runtime.json)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### General service capability substrate {#general-service-capabilities}

**State:** Designed

**Proved now:** No general-service implementation is claimed. Accepted law separates semantic
interfaces, immutable implementation profiles, typed demand, readiness, discriminated
model/call/job/session grants, exact Connector dialects, and durable service attempts while
retaining the current model path as explicit v1 compatibility.

**Do not expect yet:** There is no `CapabilitySpecV2`, `CapabilityDemand@1`, `[[capabilities]]`
compiler, general call/job/session driver registry, `ServiceJobAttempt@1` persistence or relay,
`AWAITING_SERVICE`, local durable reservation transfer, OpenAI audio/image/video dialect bake, or
CapabilitySet placement solver.

**Evidence**

- **Topic:** [Capabilities](./sepulcher/animator/capabilities.md) and [Connectors](./sepulcher/animator/connectors.md)
- **Law:** [Dispatcher](./adr/22-dispatcher.md), [Workers](./adr/14-workers.md), and [Graph](./adr/24-graph.md)

### Extension activation and contributions {#extension-activation-contributions}

**State:** Partial

**Proved now:** Dependency-first built-in assembly supplies Rune, Portal, runtime, Quadlet, and
delegation contributions under registrant-bound registration, sealed membership, owned schema
branches, and fail-closed synchronous hooks. Host-assigned registrant attribution survives v1
capability hydration, detached reads, grants, Orchestrator status, and Nexus response rows;
adapter-supplied attribution cannot override it. Raw adapter injection remains unattributed.

Separate Python interpreters verify Phoenix selection, inactive samples, configured Rune and
Quadlet projection, and disable with retained fixture files. The current cached generation stays
unchanged when its Settings file changes.

**Boundary — Not yet:** These are registration, projection, and offline grant receipts, not Linux
inscription, service startup, or database recovery. Package installation, locks, upgrade/uninstall,
migrations, lifecycle effects, Forge admission, and a stable public SDK are absent. General-service
interface/profile/driver contributions remain Designed; v1 attribution does not pin code, model
artifacts, or runtime generations for resumed work.

**Evidence**

- **Source:** [Extension manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/manager.py), [registration context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py), and [assembly host](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/host.py)
- **Verification:** [Assembly tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_catalog.py), [activation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_admission.py), [private contribution through dispatch and Nexus](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_crypt_extension_vertical.py), [Phoenix process generations](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_extension_configuration.py), [delegation contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py), and [generated bind-fileset tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_bind_fileset.py)
- **Topic:** [Extension authoring](./sepulcher/extensions/authoring.md)
- **Law:** [Extensions](./adr/05-extensions.md)

### llama.cpp integration {#llamacpp-integration}

**State:** Operator validation

**Proved now:** Runtime planning, static and router connectors, discovery, capability derivation,
model-load control, and contract tests exist. Known command/endpoint port conflicts fail during
declaration compilation. Runtime construction captures one preset catalogue and generation
profile; capability synthesis uses that captured generation even if the preset file changes.
Router inventory distinguishes exact loaded, loading, and clean unloaded models and rejects
missing or malformed evidence. Dispatch-to-convergence tests cover loading without duplicate
activation and inference refusal with autoload disabled after warmth is lost. The supported
command profile explicitly disables engine idle sleep: managed plans begin with the disabling
pair, and passthrough commands must carry it at the supported argument-vector or executable prefix
without being rewritten. Later sleep controls and ambiguous spellings fail declaration validation.
This is command admission, not live runtime attestation. Explicit managed modes govern the plan
and connector mode; conflicting known model-source arguments and environment projections fail
validation, including `secret_env_files`. AUTO and passthrough metadata follows the final command
and projected environment: per-option CLI overrides preserve explicit empty sources, main models
take precedence over router inputs, and aliases accumulate before inventory identity is selected.
Default model selection uses the captured catalogue. Effective main Hugging Face repositories,
main-model shortcuts, and ambiguous source/alias syntax fail admission. Projected secret presets
are not opened locally for catalogue or generation-default discovery. The
[engine profile](./sepulcher/animator/soulstone/engines/llamacpp.md#launch-and-identity) defines the
bounded grammar and remaining runtime-validation requirements.
Model unloading is not a separate adapter operation; Orchestrator shuts down whole runtimes.

**Receipt needed:** Name the image and revision, model and quantization, GPU and driver, flags,
systemd/Podman host, load, inference, disabled-sleep behavior, and whole-runtime shutdown results.

**Evidence**

- **Source:** [llama.cpp adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/llamacpp.py)
- **Verification:** [Adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py), [router dispatch tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_llamacpp_dispatch.py), [sleep-profile admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_llamacpp_sleep_contract.py), and [endpoint/preset generation tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_runtime_endpoint_contract.py)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### vLLM integration {#vllm-integration}

**State:** Operator validation

**Proved now:** A vLLM runtime plan, OpenAI-compatible connector, model/capability derivation, and
focused tests exist.

The standalone local-model probe explicitly registers the built-in adapter and exercises exact
Dispatcher grants, AgentForge text output, and an observed harmless tool round. Its offline
tests cover response-identity and completion-state refusal before tool processing, unavailable
or malformed inventory, transport failure, retained observations across deadline/cancellation,
and client/lease cleanup. It reads no installation configuration and has
no lifecycle authority. An operator-generated probe receipt does not qualify the installed
Vessel, Bridge, persistent Runs, model artifacts, managed activation or shutdown.

A separate maintained profile joins the source-registered vLLM adapter to the production factory,
Dispatcher, Graph, Context, SAQ and PostgreSQL. One actual streamed `BridgeReply` settles; the same
turns and valid model history survive a second application boot without another model POST.
Both startups observe the exact shared model as `WARM`; no lifecycle actuation occurs. HTTP is
TestClient and the host actuator is a refusing fixture. A second selection performs those boots
in independent sequential `spawn` processes: the first fully exits before the second, which
retains identical settled turns and history and submits no inference. This qualifies clean
application process restart; both selections use TestClient HTTP.

A third maintained selection invokes the source CLI's native Granian launcher with real loopback
TCP. Both boots reach authenticated HTTP readiness. Before one admitted Run, wrong or absent
local access and foreign-Origin or missing-CSRF message submissions refuse with zero durable
Runs and model POSTs. One structured reply settles through the production services and the second
normal process boot recovers identical turns/history without inference. The test supplies
Settings/Runes, wraps the real production lifespan and refuses host actuation; engine disposal
after CLI return is supplemental test cleanup. Observed native limits apply per process after
interpreter/module startup; PostgreSQL's separate CPU, memory and PID limits were read back.
This qualifies the named TCP and clean-restart conjunction, without installed caged-body,
managed-model, model-byte, crash, cancellation, browser, autonomy or aggregate-native-resource
qualification.

A closed model-local `qwen3.8-non-thinking` generation policy now compiles through the frozen
capability grant to the exact Qwen chat-template request field. Unsupported bindings, runtime
and Soulstone defaults, Portals and Responses refuse it; omitted settings remain unchanged.
Real-SDK mock-wire tests cover ordinary and streaming calls. A dated `bf1162f` source-app
observation completes one fixed public-source review in196 generated tokens and retains it over
two ordinary in-process boots. Its independent reviewer accepts only partial semantic utility:
the core assertions are correct, but a claimed passing counterexample would fail the displayed
test. DONE is not a correctness verdict. That separate Codex review is operator evidence, not a
delivered native verifier, installed cutover or autonomous development.

A dated operator observation on 2026-10-16 uses installed source `0cc0988`, a matching
noneditable host CLI and pinned Vessel image. One canonical `/orchestrator/activate` request
launches the dedicated vLLM service through the Host Reactor; completed intent/custody, exact
model WARM and inventory from the Core pod are observed. One model HTTP200 POST settles a DONE
Bridge Run, followed by repeated retained API history and Orb reads with empty queues/leases.
This is same-boot API projection evidence, without raw model history or raw Run-result access.
The receipt preserves the historical compiler and attestor fingerprints and the 447-file
archive/host/image parity-map digest. Its offline check validates dated metadata and privacy; it is not
a current-source freshness gate. A changed compiler, attestor or installed image needs its own
same-source qualification. Full caged stop, model shutdown, restart/crash recovery, browser,
autonomy, model bytes and aggregate resource containment remain unqualified by this observation.

**Receipt needed:** Name the image and revision, model, GPU and driver, arguments, systemd/Podman
host, readiness, inference, and shutdown.

**Evidence**

- **Source:** [vLLM registration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/vllm/register.py), [vLLM Rune](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/soulstones/vllm.py), [shared OpenAI-compatible runtime](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/openai_compat.py), and [local-model probe](https://github.com/hexanomicon/lychd/blob/main/scripts/local_model_probe.py)
- **Verification:** [Adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py) and [probe acceptance tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_local_model_probe.py)
- **Verification:** [Joined Bridge test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_runtime.py), [maintained warm-model receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-runtime.json), and [source/dependency freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_receipt.py)
- **Verification:** [Independent-process test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_process_restart.py), [maintained process-restart receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-process-restart.json), and [process source/dependency freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_process_receipt.py)
- **Verification:** [Native CLI/TCP restart test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_native_tcp.py), [maintained native TCP receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-native-tcp.json), and [native receipt freshness/privacy](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_native_tcp_receipt.py)
- **Verification:** [Dated 0cc0988 installed observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-installed-0cc0988.json) and [offline dated metadata/privacy check](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_installed_0cc0988_receipt.py)
- **Verification:** [Policy scope and binding tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_catalog.py), [real-SDK wire tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_model_transport.py), [dated selected-policy observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-qwen-policy-bf1162f.json), and [observation integrity/privacy](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_qwen_policy_receipt.py)
- **Topic:** [Standalone probe and first-reply boundaries](./sepulcher/animator/soulstone/engines/vllm.md#bring-one-service-to-a-first-reply)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### SGLang integration {#sglang-integration}

**State:** Operator validation

**Proved now:** An SGLang runtime plan, OpenAI-compatible connector, model derivation, and focused
tests exist.

**Receipt needed:** Name the image and revision, model, GPU and driver, arguments, systemd/Podman
host, readiness, inference, and shutdown.

**Evidence**

- **Source:** [SGLang registration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/sglang/register.py), [SGLang Rune](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/soulstones/sglang.py), and [shared OpenAI-compatible runtime](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/openai_compat.py)
- **Verification:** [Adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### ExLlamaV3 through TabbyAPI {#exllamav3-tabbyapi}

**State:** Operator validation

**Proved now:** The TabbyAPI-backed runtime, control plane, connector, Soulstone, registration,
revision boundary, and contract tests exist.

**Receipt needed:** Name TabbyAPI and ExLlamaV3 revisions, NVIDIA GPU and driver, EXL3 model and
quantization, cache, split, flags, load/inference/unload, and measured VRAM.

**Evidence**

- **Source:** [ExLlamaV3 control plane](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/exllamav3/control_plane.py)
- **Verification:** [ExLlamaV3 tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_exllamav3.py)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### Declared conflict topology and systemd target switching {#declared-conflict-topology}

**State:** Available

**Proved now:** Declared conflict domains compile into an incompatibility graph and compatible
Animator/Coven targets. Switching attests the loaded graph and current world, performs one bounded
compound target request, waits for systemd settlement, and classifies success or exact restoration.

**Boundary:** The private user-manager receipts cover inert services and an opt-in real rootless
Quadlet transaction using production-generated target relationships. The latter verifies container
ordering and cleanup in an isolated fixture; it does not exercise the Orchestrator, Host Reactor,
production pod, GPU or model. Declared coexistence is not measured capacity admission.

**Evidence**

- **Source:** [Conflict schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/concurrency.py) and [runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py)
- **Verification:** [Conflict tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_conflicts.py) and [private-systemd receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_target_transaction.py), plus the [real Quadlet transaction](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_quadlet_transaction.py)
- **Law:** [Containers](./adr/08-containers.md)

### Safe runtime transitions {#safe-runtime-transitions}

**State:** Partial

**Proved now:** Admission closure, lease drain, serialized transition plans, compound target
actuation, exact-prior-world compensation, interrupted-work containment, and refusal on stale
topology are covered by focused protocol tests. Manual transition priority is constrained to the
canonical `0..100` doctrine range before trace publication or arbitration and at the HTTP query
boundary. Each preflight and owned replan bounds the complete managed-runtime observation set
with one configurable planning deadline. A timed-out observation settles before a no-effect
decline; cohort followers share that result, gates remain open, and fresh requests can retry.
Transition callbacks receive the journal's immutable observation; traces and projection callbacks
cannot expose the mutable eviction and launch plans used during execution.
Soft convergence failures before invoking adapter activation are classified as no effect, including
observation-only static or already-warming waits. Their gates reopen, coalesced requests share the
classification, and unrelated warm capabilities remain usable.
Soft activation writes a durable owner-only guard before invocation and clears the exact record
only after target WARM. Crash, failed activation, or incomplete marker writes fence a replacement
Vessel before queue connection, under either actuator profile. Focused filesystem tests include an
abrupt process exit; generated mount and initialization tests cover persistent storage and mode
agreement. Hidden host recovery validates the exact record, current declarations, Scribe-owned
loaded topology, stopped Vessel and target runtime, and pending jobs before release.
Hard-transition compensation completes or contains before caller or observer cancellation propagates,
including a first cancellation that arrives during the inverse after ordinary readiness failure.
Coalesced followers retain the owner's terminal classification and physical/compensation IDs while
keeping their own request identity, independently of bounded journal eviction. These cases are
covered by [hard-effect boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_hard_effect_boundary.py)
with inert runtime effects.
Direct actuator observation failures before submission reopen admission without claiming an effect.
Cancelled Host Reactor requests preserve proved decline/restoration receipts; uncertain outcomes
remain contained. [Actuator tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py)
exercise both cancellation paths and the manager's gates.

Direct local activation accepts optional `admission_timeout_s`, with distinct HTTP 409 codes for
owner expiry and a follower's expired wait. The cutoff covers queueing and observation until
invocation or confirmed readiness; timely admission leaves later settlement under the existing
safety budgets. Coalesced followers cannot tighten the owner's cutoff or cancel its work.
Planning, drain, and convergence reject success after their actual cutoffs, including delayed
timer delivery when no admission timeout was requested. Repeated cancellation settles required
probe cleanup, and an already-selected deadline retains its cause through that cleanup.
The soft activation path rechecks both cutoffs after the durable guard write, immediately before
invoking the runtime. If persistence consumed the deadline, no activation occurs; the exact guard
and closed gates remain for explicit recovery. Deterministic tests exercise a real guard file,
fresh-instance startup refusal, and independently expiring coalesced followers.

**Boundary — Not yet:** Dynamic shared-capacity admission, durable multi-process orchestration,
general repair, and a maintained real model/GPU transition receipt are absent. After a soft
activation call is invoked, its failure has no trustworthy rollback and requires contained operator
recovery; its durable `runtime-guard/pending.json` fences Vessel restart separately from the Host
Reactor's `.contained` and unresolved `.processing` records. General recovery of corrupt or changed
declarations is absent; the bounded host command refuses them. Live recovery remains unvalidated.

**Evidence**

- **Source:** [Orchestrator manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/manager.py)
- **Verification:** [Transition tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_manager.py), [runtime workflow scenarios](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_workflow_scenarios.py), [soft effect-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_soft_effect_boundary.py), [durable guard tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_guard.py), [guard initialization tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_guard_initialization.py), [soft activation integration](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_soft_activation_recovery.py), [host recovery tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_recovery.py), [admission-expiry tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_admission_expiry.py), [observer boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_observation_boundaries.py), and [Orchestrator API tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_api_orchestrator.py)
- **Law:** [Orchestrator](./adr/23-orchestrator.md)

### Resource-aware VRAM and topology scheduling {#resource-aware-scheduling}

**State:** Designed

**Proved now:** Orchestrator law defines the scheduling seam; deterministic tests preserve the
current simple eviction baseline.

**Do not expect yet:** Current policy counts conflicting neighbors; it does not model VRAM,
footprints, load time, topology, bandwidth, LRU, refits, tiers, or transition peaks.

**Evidence**

- **Source:** [Current eviction policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/policies.py)
- **Verification:** [Policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_policies.py)
- **Law:** [Orchestrator](./adr/23-orchestrator.md)

## Altar and observability {#altar-and-observability}

The Svelte 5 static client, generated `/api/v1` types, validated semantic SSE, local schema assets,
and Litestar delivery exist. Loom and Orb share an immutable graph-projection supply and a
read-only Svelte Flow adapter, with [`@xyflow/svelte` 1.6.6](https://github.com/hexanomicon/lychd/blob/main/clients/web/package.json) installed. Focused tests establish
contracts and components; the required cross-engine retained-heap qualification after forced
collection remains under verification. Installation and a visible canvas do not discharge
[ADR 15's renderer admission gate](./adr/15-frontend.md#xyflow-admission).
The [reading hierarchy and visual direction](./adr/15-frontend.md#reading-hierarchy-and-visual-direction)
and [instrument reading scenarios](./divination/altar/index.md#presentation-direction) distinguish
current reading surfaces from further presentation targets. Design studies and illustrative browser checks do not establish
renderer qualification, restart recovery, large-collection performance, or accessibility
acceptance; the instrument records below retain their existing evidence boundaries.
The document language and interface copy are English. There is no message catalogue, explicit
locale resolver or selector, Principal-preference binding, translated accessibility surface, or
right-to-left receipt. Browser-native date/time formatting may reflect a device locale, but that
incidental variation is not delivered localization support.
The compiled Altar has one fixed LychD Dark palette, dark browser metadata, dark native-control
colour scheme, and no light/system selector, system-scheme following, palette configuration,
runtime theme loader, or supported theme extension. Semantic CSS custom properties establish a
future refactoring seam, but hard-coded dark surfaces remain in the main background, graph chrome, and
static artwork. There is no complete contrast matrix or bright/dim production-browser receipt;
ADR 15's bounded operator-palette contract is design law, not delivered configurability.

### Atlas undertaking map {#atlas-projects}

**State:** Partial

**Proved now:** Atlas provides a fifth Altar route with a project list and detail forms.
Projects retain a brief, concerns and criteria, attributed assessments with the requirement text
and revisions judged, append-only decisions and supersession, a proposed next step, lifecycle,
and explicit session or Run references. Changes are owner-scoped and version-checked; retained
request identities prevent repeated writes after an uncertain response. Editing requirements
marks earlier assessments for review. Bridge and Orb display links back to explicitly related
Projects. Creating, pausing, closing, reopening, or linking a Project admits no execution.
The shared PostgreSQL profile retains these records; disposable database tests exercise races,
replay, owner boundaries, and migration downgrade refusal. The real application factory's
two-boot HTTP receipt restores a Project and its Run reference and replays the retained request.

The next-step area groups conversation destinations without merging their concern relationships,
and offers an explicit Bridge chooser carrying an inert Project return hint. Board summaries
separate current insufficient/disputed judgments from missing or stale assessments. Bridge and Orb can
carry an activity identity through project selection into an Atlas link draft; navigation alone
saves nothing. Concerns support local search and assessment filters, with the active editor kept
beside its concern during comparison. Conflict comparison exposes differing fields and explicit
saved-value choices; citations can open in a separate tab while a draft remains. Superseded
decisions remain available by disclosure. Board filters describe the loaded page, not the full
catalogue or an inferred project-health judgment.
Project detail places concerns first, with separate assessment-group filters and a read-only
comparison of a stale judgment's retained basis against current requirements. Secondary Project
context preserves explicit continuation links alongside the concern list.

**Boundary — Not yet:** Concerns remain embedded in Projects. The
[independent Concern contract](./adr/15-frontend.md#independent-concerns-decomposition-and-addressing)
is Designed: no standalone Concerns, shared decomposition, addressing or decision-to-Concern
relations, versioned source derivations, or source-based proposal acceptance are delivered.
There is no AI concern generation, automated coverage judgment, autonomous continuation, project
scheduler, implicit Context injection, inferred clustering, or project-wide control over Run
admission and cancellation. References identify related activity; they do not freeze execution
evidence. The surface has no delete action or complete edit audit.
The local Sigil remains bootstrap context rather than an authenticated person. The memory profile
is process-local. Production-browser, multi-user, and large-history performance receipts remain
outside this evidence; existing installations require migration `0009` before use.

**Evidence**

- **Law:** [Frontend](./adr/15-frontend.md#atlas-and-continuity-across-invocations) and [Persistence](./adr/06-persistence.md#atlas-records)
- **Source:** [Atlas domain](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/atlas.py), [API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/atlas.py), [PostgreSQL adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/atlas.py), and [Atlas client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/AtlasView.svelte)
- **Verification:** [Domain tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_atlas.py), [API tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_atlas.py), [PostgreSQL tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_atlas_pg.py), [migration tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_migrations_pg.py), [two-boot application test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py), and [client tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/AtlasView.test.ts)
- **Topic:** [Atlas](./divination/altar/atlas.md)

### Bridge conversation and consent surface {#bridge-surface}

**State:** Partial

**Proved now:** Bridge supports typed sessions, one-nonterminal-Run session admission, consent,
inspection, semantic SSE, closed GenUI descriptors, durable request identity, authoritative
snapshot recovery, lifecycle fencing, and bounded reconstruction against server-owned Run and
Pattern identities. Exact retries reuse the canonical Run; distinct overlapping turns are refused.
Its compact per-turn Circle exposes complete supplied identity, evidence and exact declared-score
links, status/activity and eligible cancellation. Older retained replies report missing metadata;
a mismatched Run projection cannot provide another Run's status or actions. Dispatcher grant ids
rebind the Environment snapshot before inference and after consent re-entry. History governors
retain whole exchanges, including legacy tool-call, result, and retry chains without Run ids.
Browser-shell state retains per-session drafts and immutable unknown-admission envelopes across
instrument navigation. The shell's Bridge link returns to the last explicit session path, restoring
that session's draft; before any explicit selection, it leaves the root session choice to the
server. Later middleware refusals cannot replace an earlier uncertain identity. Late responses
settle that state even after view teardown, and admission overtaking a snapshot requires a newer
read.
After an initial snapshot read fails, **Retry read** repeats the current route's read, preserving
drafts and unresolved offerings without submitting text.
Terminal Run snapshots prefer the retained reply and fragments over incomplete live deltas while
preserving the stream cursor. Definitely refused text is retained alongside a later draft. Hard
unload warns; this state does not survive browser termination. The shell's consent link opens a
session chooser with server-owned per-session counts; decisions update only their owning
session's visible attention.
The same workspace retains pending and uncertain consent verdicts across card and instrument
remounts, reconciles late responses, and warns before document exit. IME confirmation does not
submit an unfinished message.
Shell consent counts refresh without overlapping reads every five seconds while visible, and on
focus or return to a visible tab. Hidden, loading, and failed reads show unknown; teardown and
newer invalidations fence late results. This remains a sampled count, not durable Attention.
The conversation has a collapsible rail and secondary session detail. Incoming text preserves an
older reading position; an explicit Latest turn action releases linked-Run focus without losing
the draft. The composer explains the current admission or active-Run restriction.
The Bridge snapshot also identifies the admission engine's configured default casting, separate
from retained Run identities. A configured Scout default supplies fixed command guidance with a
two-line example and the complete URL's public declaration. The composer renders that text
literally, preserves its line breaks, and removes it when refreshed guidance is absent. This is
configuration help, not readiness or permission; ordinary admission and native review still apply.

The conversation rail reads metadata in pages of 50 with an explicit continuation and Load more;
its pending counts use one grouped PostgreSQL query without hydrating archive histories. HTTP
event streams reserve capacity before headers, at most four per Run and 32 per process; excess
connections receive 429 with retry guidance, and disconnects release their reservation.
The browser caps envelopes awaiting a Run snapshot at 256, closes on overflow, and invokes its
bounded recovery path. Nexus detects permanently closed native SSE and uses its existing one-shot
ticket recovery. Refreshing a linked transition preserves the operator's keyboard focus.

Native prepared-action Consent has a portable server prerequisite: an immutable review binding,
complete owner-produced text, and an authenticated reviewer passed through snapshots, events and
decisions. Both verdicts require the exact review identity and fresh judgment eligibility before
settlement or resume; retries preserve the first verdict. Missing or malformed required review
stays unavailable. The client renders the complete review as labelled, escaped text, preserves
long and multiline values, and sends its exact binding with either verdict. Read-only or unavailable
reviews cannot submit a decision. An unresolved choice retains its original verdict and review
identity across remounts and later refusals; a changed review permits outcome refresh, not a new
choice or a retry against different material. Legacy Consent remains supported. Existing PostgreSQL
installations require migration `0010` before running this code.
The opt-in [Scout public-page workflow](#scout-web-acquisition) supplies an owner-produced native
review, atomic preparation/Consent custody, and current authority checks before acquisition and
local inference. Its deployment and mechanism qualification limits remain those of Scout.

**Boundary — Not yet:** There is no production-browser plus inference-engine receipt, durable cross-process event/token
delivery, general multi-approval, Attention, or notification channel. Text is the only command
modality, and no focused Circle workspace composes Scroll, active Spell placement,
Context/authority, capability, and evidence projections.
Selected-session turns and model history still hydrate that one conversation. There is no general
storage quota or retention policy; archive paging and stream limits do not bound every retained
payload or protect against a hostile authenticated operator.
Native action owners beyond that Scout path still require their own production admission,
review/custody transaction, and effect-time authorization. The client review and recovery tests use
component fixtures and intercepted HTTP requests; they do not qualify complete production-browser
layout or accessibility. The separately assembled
[Blockworld test workflow](#composition-portfolio-delivery) exercises a native action with inert
effects. Native binding and reviewer unit tests use memory or session doubles. Separate disposable
PostgreSQL receipts now exercise migration `0010`, exact binding, decision concurrency and rollback;
they do not qualify production deployment or live effects.

**Evidence**

- **Source:** [Bridge controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py), [Bridge client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeView.svelte), [Altar shell](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/AltarShell.svelte), and [Context assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/context.py), with [native review resolution](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/consent_reviews.py) and [binding migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0010_native_consent_binding.py).
- **Source:** [Circle Run disclosure](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/CircleRun.svelte)
- **Verification:** [Circle identity/action tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/CircleRun.test.ts)
- **Verification:** [Configured composer projection tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge_composer.py)
- **Verification:** [Bridge tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge.py), [archive tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge_archive.py), [stream admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge_stream_budget.py), [PostgreSQL archive receipts](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_consent_pg.py), and [client recovery tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeView.test.ts), [initial read recovery tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/InstrumentReadRecovery.test.ts), [shell navigation tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeShellNavigation.test.ts), [client review tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/ConsentCard.test.ts), and [decision transport tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/api/client.test.ts), plus [complete-history tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_context.py), [native binding tests](https://github.com/hexanomicon/lychd/blob/main/tests/codex/test_native_consent.py), and [reviewer and decision tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_native_consent_review.py).
- **Law:** [Frontend](./adr/15-frontend.md), [Context](./adr/21-context.md), and [native Consent review](./adr/25-hitl.md#required-review-for-native-actions-designed)

### Nexus transition board {#nexus-transition-board}

**State:** Partial

**Proved now:** Nexus renders typed state and plans, submits explicit transitions, fences
ambiguous request identities, follows bounded process-local tickets, and durably reserves the
first target request before launch.
An earlier unknown outcome retains its UUID through later middleware refusal. Navigation guards
protect in-flight and unresolved admission from accidental discard.
Native capability disclosures expose served health, warmth and reason independently of the
compact chip. Preview loading is target-specific and closing it fences late responses. Full
uncertain request identities remain visible, and a previous ticket survives selecting another
preview. Containment and no-op conditions explicitly disable the transition action.

**Boundary — Not yet:** Only request admission is durable. Transition observations lack a durable
owner, complete history, cross-process projection, restart recovery, and production-browser
receipt. Durable admission prevents duplicate launch, but a lost ticket cannot prove the outcome
or resume safely; retry refuses to relaunch it.

**Evidence**

- **Source:** [Nexus controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/nexus.py)
- **Verification:** [Nexus tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_nexus.py) and [client transition tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/NexusView.test.ts)
- **Law:** [Frontend](./adr/15-frontend.md)

### Loom workflow instrument {#loom-workflow-views}

**State:** Partial

**Proved now:** Loom browses exact immutable Pattern revisions, manifests, semantic station and
permission outlines, checkpoint schemas, implementation revisions, source, active/default state,
and retained revisions with stale-response-fenced client loading. Verified Orb origin links retain
the Run and selected event on return; mismatched context is reported without choosing another Run.
The semantic outline selects a station with labeled incoming and outgoing permissions, declared
self-loops, and keyboard return to its row. The shared Svelte Flow canvas displays the same
read-only score, folding the whole Pattern or revealing its stations through zoom and explicit
controls. Graph failure leaves the outline and inspector available. Failed score reads offer an
exact-revision retry. Copied Mermaid source retains the exact Pattern key, revision and manifest
digest even when two revisions declare the same topology; it remains a view, not execution evidence.

**Boundary — Not yet:** Loom is a view over the fixed registry, not a Spellweaver editor, mutation
surface, independent Spell identity or catalogue, compatibility or teaching surface, drafting
canvas, inert unresolved-Spell projection, or Suite executor. The shared renderer's cross-engine
forced-collection qualification and complete production-browser acceptance remain unproved.

**Evidence**

- **Source:** [Loom controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/loom.py), [Pattern registry contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py), [Loom client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/LoomView.svelte), and [shared graph adapter](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/graph/GraphCanvas.svelte)
- **Verification:** [Loom tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_loom.py), [client lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/LoomView.test.ts), and [semantic projection tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/graph/loom.test.ts)
- **Law:** [Workflow](./adr/28-workflow.md)

### Composition Portfolio {#composition-portfolio-delivery}

**State:** Partial

**Proved now:** The Portfolio publishes Native Reference Composition contracts and examples; the
default boot catalogue contains the Core `bridge_chat` lineage (revisions 1, 2 and 3) and
`delegated_rite` lineage (revisions 1 and 2). An explicit application selector additionally registers
the bounded `creation.investigate@2` Pattern.
The accepted designs include [Health](./compositions/health/index.md) for attributable personal
clinical records and bounded diagnostic and care proposals,
[Keeper](./compositions/keeper/index.md) for animal and colony care,
[Cultivator](./compositions/cultivator/index.md) for cultivation, and the narrowed
[Homestead revision 2](./compositions/homestead/index.md#revision-continuity) for site and stores stewardship.

[Creation investigation](./compositions/creation/index.md) revision 2 has an explicitly selected
PostgreSQL application, protected local submit/read/cancel/continue API and serial
`creation.investigate@2` Pattern. It retains immutable public sources, role reservations, one-shot
claims, complete provider bytes, a candidate and a fresh attributed verdict. The
[Creation delivery boundary](#smith-forge-promotion) keeps its focused evidence and remaining gaps.

Blockworld has an explicitly assembled, inactive one-block placement Pattern. Portable tests drive
real Run admission, the worker, serial Graph, native Consent review, HTTP decision, and resume with
a composite memory store and an inert effect port. They reconstruct serialized fixture state into
fresh services, retain the canonical Run and exact command through interruption, and reconcile a
claimed action without repeating its invocation. Matching response and event evidence settle the
receipt, mission cursor, and placement budget together in that fixture. PostgreSQL models, a store,
and migration `0011` have passed disposable PostgreSQL transaction, recovery and migration-cycle
tests, including comparison with the ORM schema.
A further PostgreSQL vertical connects those stores to actual Run admission, worker execution,
native HTTP Consent review, and serialized checkpoints. Fresh adapters resolve acknowledged and
lost-acknowledgement outcomes without repeating the world command; an injected SQL failure proves
receipt/cursor/budget rollback, and racing reconciliation returns one settled receipt. Current
authority and world-epoch changes refuse execution after an earlier approval. This uses an inert
world and captured queue in one process; it does not establish broker delivery or automatic
recovery of an orphaned running worker after process death.

Companion has a pure Kotlin/JVM model for memory-only client interaction: expiring text drafts,
exact review before a separate submit request, reconnect without replay, observed presentation
and playback state, and separate local stop/cancel controls. Its pinned harness compiles and tests
those local transitions. A submit signal establishes neither native admission nor a settled handoff;
its one-signal guarantee follows the returned state lineage and provides no transport deduplication.

A native Android Compose screen now exposes the offline text-draft path. The person chooses a
positive whole-second lifetime, edits against the original deadline, sees idle expiry, and cancels
locally before starting a fresh session. The Activity preserves its state across configuration
recreation within the same process; process death restores neither the draft nor unsubmitted form
input. Review and Submit remain disabled while disconnected. The prototype lives in the opt-in
`offline` application alongside the existing audio client. Its Kotlin/JVM reducer has passed the
shared JDK 17 toolchain checks. ViewModel and instrumented Activity tests are authored, including
input batches before recomposition and lifecycle-bound expiry sampling; this combined checkout
has not yet been qualified with an Android SDK, emulator or handset.

**Boundary — Not yet:** Creation's one application selector supplies no general Composition or
Product catalogue, shared store, Suite execution or application scheduler. Other Portfolio members
have no domain/effect path enabled in normal application assembly. Blockworld has no
server, bot, Minecraft adapter, production route or review producer registration. Its portable
fixture alone does not establish database atomicity or migration safety; those boundaries have
separate disposable PostgreSQL receipts. Neither fixture qualifies live game effects or a deployed
Linux operation. Crucible is a designed Weaver choreography, not a
registered Pattern, parallel Graph, dossier schema, or Altar surface.
Keeper and Cultivator's durable record contracts do not supply database models or migrations.
[Transmuter](./compositions/transmuter/index.md) remains a candidate study outside the accepted
Portfolio. Its Extractor and Synthesizer pages establish proposed responsibilities, not import
adapters, processing records, executable Patterns, or Memory/Identity handoffs.
[Accounting Office](./compositions/accounting-office/index.md) also remains a candidate study:
its proposed mail/bank ports, entity books, jurisdiction profiles, privacy workflow, and accounting
Patterns establish no implementation, live account access, tax filing, or supported-country claim.
[Thorn](./compositions/thorn/index.md) remains a candidate whitehat security workbench for scoped
assessment, incident response, cooperative investigation, and reviewed reports/corrections.
General monitoring and system maintenance remain outside its case ownership. It supplies no
implemented case records, monitoring integration, response automation, peer investigation network,
actor attribution, or reporting adapter; deterrence remains unmeasured.

The Android screen supplies no device capture/playback, transport, persistence, credential
enrollment, or authoritative Companion records and receipts. Emulator evidence does not qualify
physical devices or every Android version allowed by the declared minimum SDK.

**Evidence**

- **Source:** [Blockworld workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/workflow.py), [placement custody](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/blockworld.py), [placement migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0011_blockworld_placement.py), [Workflow registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py), [client interaction model](https://github.com/hexanomicon/lychd/blob/main/clients/android/interaction/src/main/kotlin/org/lychd/companion/interaction/Interaction.kt), [Android screen](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/main/kotlin/org/lychd/companion/CompanionScreen.kt), and [Activity state](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/main/kotlin/org/lychd/companion/OfflineDraftViewModel.kt)
- **Verification:** [Portable placement workflow tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_blockworld_placement_vertical.py), [PostgreSQL placement tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_blockworld_pg.py), [PostgreSQL worker and review vertical](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_blockworld_postgres_vertical.py), [Workflow routing tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_router.py), [client interaction tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/interaction/src/test/kotlin/org/lychd/companion/interaction/InteractionTest.kt), [ViewModel tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/test/kotlin/org/lychd/companion/OfflineDraftViewModelTest.kt), [Activity tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/androidTest/kotlin/org/lychd/companion/CompanionScreenTest.kt), [production-lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/androidTest/kotlin/org/lychd/companion/CompanionLifecycleTest.kt), and [client check commands](https://github.com/hexanomicon/lychd/blob/main/clients/android/README.md)
- **Topic:** [Composition Portfolio](./compositions/index.md)
- **Law:** [Workflow](./adr/28-workflow.md)

### Offline music and Comfy engineering probes {#music-comfy-engineering-probes}

**State:** Partial

**Proved now:** A source development runner validates immutable bounded recipes, preserves earlier
control variants behind an expected-digest guard, and renders finite owned FAUST instruments or
exact PCM clips through an isolated optional DawDreamer process. Aligned stems and a mix retain
source, recipe, implementation, executable-package and output identities. Verified cache hits
refuse corrupted/incomplete entries. A standalone read-only audition shows the exact recipe
timeline and verified mix/stems without a native editor or independent synthesis. A classic
loopback Comfy probe pins reviewed workflow/input declarations, persists an indeterminate submit
fence before POST, reconciles exact prompt identity,
and retains bounded immutable artifacts with partial-download receipts. Deterministic local staging
supports explicit digest-verified repair after interrupted file installation, without HTTP or
receipt identity changes. Unpinned staging blocks refetch. Focused tests exercise real
DawDreamer 0.9.0 audio and MockTransport Comfy failure paths.

**Boundary — Not yet:** These are finite engineering mechanisms, not a native Riffmaw or Atelier
application, canonical musical project, registered Pattern, Invocation, ServiceJob, media custody
or semantic acceptance path. There is no shipped studio API/editor, live input, plug-in loading,
realtime/latency proof, engine containment, Comfy deployment, loaded-model attestation or real
MiniMax generation. Lost, damaged or unpinned Comfy staging and conflicting final files still
require manual reconciliation; targeted
cancellation refuses. Stable operator-owned external directories and the optional native profile
remain explicit prerequisites. Portfolio and general-service delivery stay Designed.

**Evidence**

- **Source:** [Recipe contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/riffmaw/offline/models.py), [guarded edits](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/riffmaw/offline/recipe.py), [offline worker](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/music_probe.py), [audition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/riffmaw/offline/audition.py), [Comfy attempt contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/comfy_probe.py), [Comfy probe](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/comfy_probe.py), and [development runner](https://github.com/hexanomicon/lychd/blob/main/scripts/music_probe.py)
- **Verification:** [Recipe tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_riffmaw_offline.py), [runner tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_music_probe_cli.py), [audition boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_music_audition.py), [native audio tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_music_probe.py), and [Comfy protocol tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_comfy_probe.py)
- **Topic:** [Riffmaw Workbench](./compositions/riffmaw/workbench.md)
- **Law:** [Backend package boundaries](./adr/11-backend.md), [Workers](./adr/14-workers.md), and [Workflow](./adr/28-workflow.md)

### Companion Android Client {#companion-android-client}

**State:** Partial

**Proved now:** The native Kotlin/Compose client provides a development-only Bridge HTTP fixture,
generated wire models and token-shape checks from the Altar OpenAPI export, bounded local
interaction state, and Android foreground AudioRecord/Media3 capture and replay. A closed local
presentation policy gates views and direct actions, defaults to unavailable and fences context
replacement. The Android assembly delegates transient mechanics to a controller with injected
audio ports. Focused JVM tests verify malformed/bounded responses, lost acknowledgements,
denied offers, stale callbacks, WAV bounds and file custody. Real Ktor fixture tests distinguish
caller cancellation from the transport's own deadline, keep unacknowledged submissions unknown,
and refuse redirect/replay or late-response restoration after context clearing. The fixture
performs no host work; these client mechanics do not deliver a Portfolio Composition.
The debug APK builds with the pinned Gradle toolchain and passes Android lint; that compile
evidence is separate from the outstanding handset probe.

**Boundary — Not yet:** There is no enrolled handset or real-device validation receipt, live
network engine, protected mobile ingress, Ward/Familiar enrollment, authenticated working-view
projection, object-scoped authorization, semantic event subscription,
Echo transcription/synthesis transport, settled Companion handoff/presentation, or Communion
Suite execution. Release builds show an unavailable screen. Music, photo access and copy sync
remain candidate work.

**Evidence**

- **Source:** [Android client](https://github.com/hexanomicon/lychd/tree/main/clients/android), [Bridge transport](https://github.com/hexanomicon/lychd/blob/main/clients/android/core/src/main/kotlin/io/github/hexanomicon/lychd/companion/core/KtorBridgeTransport.kt), [presentation policy](https://github.com/hexanomicon/lychd/blob/main/clients/android/core/src/main/kotlin/io/github/hexanomicon/lychd/companion/core/presentation/PresentationPolicy.kt), [interaction controller](https://github.com/hexanomicon/lychd/blob/main/clients/android/app/src/main/kotlin/io/github/hexanomicon/lychd/companion/CompanionController.kt), and [foreground recorder](https://github.com/hexanomicon/lychd/blob/main/clients/android/app/src/main/kotlin/io/github/hexanomicon/lychd/companion/audio/ForegroundRecorder.kt)
- **Verification:** [Core tests](https://github.com/hexanomicon/lychd/tree/main/clients/android/core/src/test/kotlin/io/github/hexanomicon/lychd/companion/core), [presentation tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/core/src/test/kotlin/io/github/hexanomicon/lychd/companion/core/presentation/PresentationPolicyTest.kt), [controller tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/app/src/test/kotlin/io/github/hexanomicon/lychd/companion/CompanionControllerTest.kt), [WAV tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/app/src/test/kotlin/io/github/hexanomicon/lychd/companion/audio/Pcm16WavFileTest.kt), and [wire generator tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/tools/test_generate_wire.py)
- **Topic:** [Android Development](./compositions/companion/android-development.md) and [Access and Views](./compositions/companion/access-and-views.md)
- **Law:** [Source topology](./adr/01-doctrine.md#repository-source-topology), [Audio](./adr/37-audio.md), and [IAM](./adr/38-iam.md)

### Orb instrument {#orb-instrument}

**State:** Partial

**Proved now:** Orb opens a paginated Run catalogue and a parallel pan/zoom field. At most three
live lenses retain 100 records each; the visible catalogue refreshes every five seconds; zoom or explicit controls disclose Run, station/subject,
supplied occurrence, and loaded records. Exact pinned workflow graphs show declared permissions
separately from retained evidence. Catalogue queries select bounded metadata without loading
prompts, manifests, or event histories. The selected-Run route retains ordered, paginated evidence
with Pattern revision, capture durability, ledger boundaries, gaps, transition links, stable selection, bounded retry, and
teardown-cancelled reads. Its ledger-polled SSE serves bounded batches, resumes from a delivered
cursor, reports resets, and closes after the currently retained terminal account drains. Feed
connection state does not settle Run status. Its delegated-job projection applies newest-job and
per-job event limits at the store query boundary before rendering the public 32/64 suffixes. The shell
Orb tab opens the parallel field. Exact Run/event links and the Loom round trip preserve selection, and Bridge return focuses the exact Run's turn or reports its
absence.
Capture limits and coverage precede the evidence list. Rows expose supplied subjects and dated
local timestamps; selecting one focuses its inspector, and closing it returns focus to the row.
Delegated jobs unfold after the evidence, with verified linked-job focus preserved.
The selected Run has a loaded-record playback cursor with a frozen evidence lens; live events
continue without moving that lens. LIVE and Follow latest resume the newest loaded account.
Allowlisted Animator dispatch identities supply a coloured rail and cursor highlight, with no
inferred call duration or uptime. Loom and Orb share hover/focus previews and a dot-free canvas.
Run groups retain an explicit unloaded-evidence label or loaded-record and supplied-gap counts
at every folding depth, including supplied omission notices and further retained history outside
the lens.

Initial read recovery and loaded-record subject/attempt browsing preserve the current route and historical selection. Refresh and pagination do not move focus when an unchanged job hint becomes available.

**Boundary — Not yet:** Loaded graph counts are not complete-history counts. The current manifest
supplies no nested subworkflow or parent-Run identity. There is no durable Oculus read model,
Sigma/Graphology adapter, cross-process completeness, health query, artifact custody, or annotation.
There is no wall-clock workspace replay, configurable retention, continuous model-call activity,
or historical Animator availability projection.
The shared renderer's cross-engine forced-collection qualification remains under verification.

**Evidence**

- **Source:** [Orb controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/orb.py), [Run catalogue queries](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/ledger.py), [parallel field](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbField.svelte), and [selected-Run client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbView.svelte)
- **Verification:** [Orb API and stream tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb.py), [catalogue privacy and pagination tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb_catalogue.py), [parallel-field tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbField.test.ts), [folded coverage tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/graph/orb.test.ts), [selected-Run tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbView.test.ts), and [feed recovery tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/orb/live.test.ts)
- **Law:** [Observability](./adr/29-observability.md)

### Structured logging configuration {#structured-logging}

**State:** Available

**Proved now:** One tested builder configures human and JSON stdlib/Structlog output for CLI and
Litestar while preserving stdout/stderr semantics, recovery-command fallback, and thread-stable
repeated bootstrap without an unused logging queue.

**Boundary:** Shared configuration does not prove complete semantic audit coverage, trace storage,
OpenTelemetry export, redaction, retention, resource correlation, or Oculus.

**Evidence**

- **Source:** [Logging configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/logging.py)
- **Verification:** [Logging tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_logging.py)
- **Law:** [Observability](./adr/29-observability.md)

### Native Oculus {#native-oculus}

**State:** Designed

**Proved now:** Observability law defines LychD's canonical evidence meanings and a native
read-model boundary; no native Oculus implementation is delivered.

**Do not expect yet:** There is no native ingestion, durable query/read model, retention path, or
Oculus-backed Svelte service. Orb is a bounded Run projection, not Oculus.

**Evidence**

- **Topic:** [Oculus](./sepulcher/extensions/oculus.md)
- **Law:** [Observability](./adr/29-observability.md)

### Phoenix {#phoenix-eye}

**State:** External

**Proved now:** LychD can generate an optional Phoenix service contribution and preserves an
explicitly configured legacy service name.
Its generated database connection uses a separate role and credential after the migration gate;
it receives neither the administrative nor Vessel runtime database password.

**External owner and boundary:** [Arize owns Phoenix](https://github.com/arize-ai/phoenix). LychD
does not own its lifecycle or state, require it for Oculus, or prove application trace export. A
`latest` image is not a reproducible receipt.

**Evidence**

- **Source:** [Phoenix configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/config.py)
- **Verification:** [Phoenix generation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py)
- **Law:** [Observability](./adr/29-observability.md)

## Authority and artifacts {#authority-and-artifacts}

### Context privatization and Portal egress {#context-privatization-and-portal-egress}

**State:** Partial

**Proved now:** Immutable influence labels and conservative joins exist. Context Blocks default to
unknown/restricted; assembly accounts for ungoverned query, history and continuation without
lowering known ancestry. The offline `closed-diagnostic@1` profile prepares one complete typed
projection through deterministic redaction, ordered receipts, independent reconstruction and
utility verification, and a process-local authenticated Cut. Its closed vocabulary and exact
sensitive spans cover a synthetic diagnostic fixture, not arbitrary text or code. The public
event projection exposes only an opaque random identifier. Changed bytes, evidence, policy,
identity, target, expiry, unknown lineage and meaningless redaction refuse verification.

**Boundary — Not yet:** No governed SQL/tool/artifact adapters, end-to-end source lineage, semantic
Privacy Agent, general PII detector, reversible map/Vault, provider-specific sanitized wire branch,
Egress Gate, transmission accounting, cumulative-disclosure policy or deletion propagation ships.
An in-memory Cut neither survives restart nor grants disclosure. Normal private Context and
effectful delegated execution remain ineligible for remote use.

**Evidence**

- **Source:** [Privacy preparation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/privacy/preparation.py), [independent verifier](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/privacy/verification.py), and [Context integration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/context.py)
- **Verification:** [Adversarial preparation fixtures](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/privacy/test_preparation.py), [Context influence tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_context_privacy.py), and [offline probe output](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/privacy/test_probe.py)
- **Topic:** [Portal](./sepulcher/animator/portal.md)
- **Law:** [Context](./adr/21-context.md#privatization-and-the-privacy-cut) and [Security](./adr/09-security.md#portal-privatization-and-egress)

### Local Sigil and scope authority {#local-sigil-authority}

**State:** Partial

**Proved now:** Typed Sigils, scopes, guards, consent preauthorization, transactional use-budget
consumption, policy synchronization, and digest-bound auto-grant revalidation are tested on the
loopback bootstrap surface.

**Boundary — Not yet:** A dedicated local possession credential precedes the fixed `magus:*`
Sigil, but it does not identify separate people. There is no object
authorization, delegation, revocation, tenant isolation, remote exposure, or general effect-time
reauthorization.

**Evidence**

- **Source:** [Sigil identity](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/sigil.py), [consent ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/ledger.py), and [policy synchronization](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/lifespan.py)
- **Verification:** [Guard tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sigil_guards.py), [policy-integrity tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/codex/test_policy_safety.py), and [PostgreSQL consent tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_consent_pg.py)
- **Law:** [Security](./adr/09-security.md)

### Local browser and bind boundary {#local-browser-bind-boundary}

**State:** Partial

**Proved now:** Generated ports and uncaged service policy bind IPv4 loopback; native `serve`
refuses non-loopback host, inherited-file-descriptor, and UNIX-domain-socket arguments and
environment overrides, including Granian alternate-listener aliases, then publishes one effective
`127.0.0.1` or `::1` TCP listener. Native short-option clusters cannot conceal listener authority;
unknown short options are refused. Native serve refuses an enabled metrics exporter and preserves
its admitted listener settings through late dotenv loading. Worker and reload admission includes
Granian reload-path and filter aliases. Launch, Host, CORS, local schema assets, fixed root handlers,
and CSRF contracts are bounded and tested. Missing, wrong, malformed, or duplicate HTTP Basic
credentials fail before fixed-Sigil admission on protected HTTP/API/SSE paths; foreign-Origin
mutations fail even with valid credentials and CSRF. `lychd access` explicitly retrieves the
local credential without exposing it in generated commands or ordinary status. The raw SAQ
diagnostic UI configuration is refused while its workers remain available. The HTTP assembly
tests verify this security configuration against memory services without entering runtime lifespan.

**Boundary — Not yet:** Admitted requests still receive the fixed local Sigil. No hostile-browser receipt,
security-header contract, or remote principal exists. The developer fixture's configured loopback
Vite proxy has a bounded development exception; authenticated browser acceptance is still pending.
Production access through a proxy, tunnels, non-loopback access, and untrusted-browser use remain
unsupported.

**Evidence**

- **Source:** [Application composition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py), [server policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/server_policy.py), and [fixed Altar routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py)
- **Verification:** [Network policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py), [native launcher tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py), [HTTP boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_http_boundary.py), [Factory HTTP assembly tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_app_factory.py), and [Altar route tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
- **Law:** [Security](./adr/09-security.md)

### Scout web acquisition {#scout-web-acquisition}

**State:** Partial

**Proved now:** Web-acquisition law separates search, fetch, render, extraction, destination
pinning, quarantine, authentication, and paid effects. The accepted design selects native static
Fetch + Extract, a SearXNG Search Soulstone, and a later isolated Crawl4AI renderer candidate;
Firecrawl remains deferred and paid web-acquisition Portals remain private-extension territory.
The design now binds Scout provider contributions, a narrow SearXNG query/result contract,
per-transmission engine egress mediation, and static extraction qualification limits and cases.
The complete acquisition envelope remains a design target.
Pure destination preflight now validates bounded canonical HTTPS URLs and exact-host supplied
address sets against an explicit conservative IP policy. Its tests cover ambiguous syntax,
forbidden and mixed answers, caller-forged facts, bounds and absence of I/O. These facts establish
neither actual DNS resolution nor permission to connect. Workflow law now separates stable
acquisition identity from Graph re-entry and requires separate custody before content can survive
a workflow park or restart.

The fixed native extractor now projects bounded UTF-8 HTML and plain text through a supervised
Linux child. A maintained Linux x86-64/Bubblewrap 0.12.0/CPython 3.15.0 receipt proves that exact
runtime's ordinary and hostile fixtures, host-network/filesystem/environment/descriptor denial,
CPU/address-space/process limits, bounded pipes, and timeout/cancellation/parent-death cleanup
with observed new-session descendants. It fingerprints the runtime closure and source; a freshness
test prevents a historical pass from silently qualifying changed code. This proves the local
extraction mechanism, not arbitrary host compatibility or acquisition authority.

The native acquisition mechanisms now use explicit A/AAAA DNS-over-TCP observations, a pinned
hostname-verified TLS connection, a gate at every network write, bounded HTTP/gzip decoding and
exact manual redirects. A maintained Linux receipt proves real DNS/TLS/HTTP and extraction in an
isolated loopback-only namespace, including wrong certificates, mixed addresses, unlisted
redirects and revocation during TLS preventing the HTTP send. Unit tests challenge malformed and
fragmented inputs, deadlines, cancellation and limits. Source and dependency freshness checks
prevent reuse of that proof for changed mechanisms. Optional Run-effect lifecycle hooks fence
the exact worker claim before settlement awaits, preserve refusal after failed cleanup, and
fence shutdown before draining; their tests include stale-worker/successor races.

A second maintained isolated-network receipt joins the production credential owner, current
policy, Run fence and network gate to real DNS/TLS/HTTP. It verifies the exact GET and accounting,
refuses same-host path/query substitution, and observes no HTTP bytes after authentication,
policy, claim, Run or shutdown revocation during TLS. Zero budgets prevent their next effect;
finite exhaustion after DNS prevents the origin connect or TLS ClientHello as applicable.
Its source/dependency freshness check includes the authorizer and shared network fixture.
Preparation and claim are explicit fixtures, so this proof does not establish database admission,
extraction authorization or inference.

The opt-in `bridge_chat@4` path now binds an actual local authentication marker, an explicit
public-locator declaration, an immutable Scout profile and an exact local chat capability. Native
review precedes acquisition. PostgreSQL retains preparation and consent atomically, admits one
active claim per binding, reserves host/binding counters, and releases them only against an owned
completion. Unknown attempts keep reservations and their slot; a new process cannot reconstruct
material or live authority from those rows. Transactional migration and retained-history downgrade
guards have separate PostgreSQL acceptance.

The production composition shares the same effect lifecycle between HTTP and workers. Current
authority is checked after waits and before DNS, TLS/HTTP writes, extraction, token counting and
local inference. The source envelope is transient and contributes unknown/restricted Context
influence; only references and the ordinary answer enter the retained workflow. The answer may
quote its source. Controlled workflow tests cover native consent, exact local-model selection,
hardware waits, cancellation races, material loss and absence of refetch or remote fallback.
An assembled PostgreSQL fixture additionally crosses actual credential admission, Run delivery,
native consent and resumed claim, owned settlement and persisted turns. Its transport, child
process and model are controlled substitutes, distinct from the separately qualified mechanisms.

A worker-driven PostgreSQL test now parks the actual Graph and restores its typed continuation
from durable storage through `perform_run`. Scout checkpoints carry the exact native consent
owner before entering the Gate and clear it before proceeding. Approval acquires and settles
once; denial settles a refusal without acquisition or inference. Missing or conflicting owners
fail before any resumed station, stale deliveries remain inert, and terminal events, delivery
settlement and source exclusion are checked. Legacy checkpoints without an owner remain
non-resumable; the worker never infers authority from their review reference. The test reconstructs
checkpoint and event-bus objects, while retaining the admitted Scout service in the same process;
queue publication, dispatcher, acquisition and model remain controlled substitutes.

A maintained composed Linux receipt now joins actual credential admission, PostgreSQL native
consent and a store-issued claim to the real current-authority DNS/TLS/HTTP path and fixed
supervised extraction child. The disposable database has no IP network or published port;
its dedicated pathname socket remains reachable from the isolated acquisition namespace.
The passage checks the exact request, all settled host/binding counters, reference-to-receipt
identity, ordinary answer retention and absence of transient source input from retained state,
history and settlement. Reconstructing the service cannot refetch consumed material. Revoking
access during TLS prevents HTTP application bytes, extraction and the deterministic model call,
while retaining a refused settlement. Container, anonymous volume and socket-directory removal
are observed before the receipt passes. Nodes and services are invoked explicitly; queue,
dispatcher, events and model remain controlled adapters.

**Boundary — Not yet:** No SearXNG or Crawl4AI Rune/adapter, general Scout provider store,
effect-scoped Agent tool, download quarantine, website authentication/session custody, or Smith
ingestion path ships. No Search engine has passed qualification. The transport/extraction proof
uses a synthetic audit gate; the additional current-authority network proof uses fixture admission
data. The composed receipt adds real PostgreSQL and extraction but does not exercise HTTP routing,
a SAQ worker process, durable Graph checkpoint/resume or model inference. The separate worker test
proves durable Graph continuation with substituted effects; no receipt joins that execution to the
real network, extractor and inference service. These receipts do not prove a deployed combination
or arbitrary host compatibility. The first workflow accepts only its explicit public-page command, follows no
redirects, and requires a qualified local extractor and exact local model. Budget reset and
unknown-attempt reconciliation have no automatic operational path. Rendering remains separately
unimplemented outside the shared Pod.

**Evidence**

- **Topic:** [Scout](./sepulcher/extensions/scout.md)
- **Law:** [Webcrawler](./adr/30-webcrawler.md)
- **Source:** [Pure destination preflight](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/scout/destination.py), [fixed extraction worker](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/scout_worker.py), and [Linux supervisor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_extraction.py)
- **Verification:** [Destination boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/scout/test_destination.py), [worker tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_scout_worker.py), [supervision and receipt-freshness tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_extraction.py), [live host proof](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_extraction_runtime.py), and [maintained qualification receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-extraction-runtime.json)
- **Source:** [Native acquisition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_fetch.py), [gated transport](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_socket.py), and [Run effect fences](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/cancellation.py)
- **Verification:** [Acquisition and freshness tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_fetch.py), [HTTP decoder tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_http.py), [Run fencing tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_cancellation.py), [isolated network proof](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_fetch_runtime.py), and [maintained transport receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-fetch-runtime.json)
- **Source:** [Current authority](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/scout/authority.py), [durable attempts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/scout.py), [owned coordinator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_workflow.py), and [public-page casting](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/scout_chat.py)
- **Verification:** [Authority contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/scout/test_authority.py), [PostgreSQL attempts](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_attempts_pg.py), [migration custody](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_migrations_pg.py), [coordinator boundaries](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_workflow.py), and [transient workflow projection](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_scout_chat.py)
- **Verification:** [Assembled PostgreSQL workflow](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_workflow_pg.py)
- **Verification:** [Worker and durable Graph continuation](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_graph_workflow_pg.py) and [consent checkpoint ownership](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_scout_consent_owner.py)
- **Verification:** [Composed isolated passage](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_composed_runtime.py), [maintained composed receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-composed-runtime.json), and [composed receipt freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/scout/test_composed_receipt.py)
- **Verification:** [Current-authority network proof](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_authority_runtime.py), [maintained authority receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-authority-runtime.json), and [authority receipt freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/scout/test_authority_receipt.py)

### Vision admission {#vision-admission}

**State:** Partial

**Proved now:** Capability declarations distinguish the Vision family from image modality and
dispatch metadata preserves that distinction. A `WARM` v1 `vision` record still fails closed at
grant issue because no typed visual execution surface exists.

**Boundary — Not yet:** LychD does not upload, store, normalize, request, transport, or render image
bytes through Bridge and an engine.

**Evidence**

- **Source:** [Capability vocabulary](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/capability_family.py)
- **Verification:** [Vision catalogue tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_catalog.py)
  and [grant-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py)
- **Law:** [Vision](./adr/36-vision.md)

### Audio admission {#audio-admission}

**State:** Partial

**Proved now:** V1 capability metadata can declare audio input through `modalities_in`; it has no
output-modality field. Speech services remain the `stt` and `tts` families. Even when observed
`WARM`, both v1 families fail closed at grant issue because no typed transcription or synthesis call surface exists.
A pure, unregistered Echo helper checks supplied bytes against their `ArtifactRef` digest, size, and
media type, then inspects the exact canonical PCM WAV subset: mono, 16 kHz, 16-bit samples,
1–480,000 frames, at most 1 MiB. It returns immutable source and measured PCM facts.

A separate trusted Echo helper consumes retained bytes through the explicit
[local custody profile](#artifact-reference-contract). It reruns the PCM inspector under
quarantine-inspection authority, needs a separate admission decision, and obtains fresh read
authority before consuming an admitted payload.

**Boundary — Not yet:** Structural inspection proves neither speech, consent nor provider
compatibility. The local helpers have no capture, upload, transport or dispatch integration.
There is no streaming socket, resonance buffer, working STT/TTS adapter, selectable Echo extension,
or Audio Coven.

**Evidence**

- **Source:** [Capability contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/capabilities.py), [Echo PCM inspection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/echo/material.py), and [trusted custody consumer](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/echo/custody.py)
- **Verification:** [Grant-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py)
  and [dispatch-refusal tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_dispatcher_scenarios.py), plus [real-byte PCM inspection tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_echo_material.py), [Echo custody refusal](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_echo_custody.py), and [retained-byte lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_artifact_custody.py)
- **Law:** [Audio](./adr/37-audio.md)

### Artifact references and local custody {#artifact-reference-contract}

**State:** Partial

**Proved now:** `ArtifactRef` defines immutable artifact identity, digest, classification, size,
and media type. Delegated-agent requests and results carry those references; focused coordinator
tests pass input metadata to an inert runtime, and a PostgreSQL receipt covers reference
round-tripping through delegated-job creation and result adoption.

An explicitly constructed filesystem adapter implements the bounded
`same-host-trusted-bootstrap@1` Reliquary profile. It copies supplied immutable `audio/wav` bytes
into quarantine under a retained private-root binding and requires an injected current authorizer.
Reads compare the complete retained record before accessing payload bytes; admission reruns a
trusted inspector and needs separate current authority. Immutable holds and exact releases govern
manual retention. A tombstone denies reads and identity reuse before physical cleanup, whose result
distinguishes absence, pending cleanup and recovery. Focused tests exercise actual WAV bytes,
authorized access, control transitions, failure boundaries and clean same-root reopening.

**Boundary — Not yet:** This is an unregistered local composition seam, with no configured root,
upload endpoint, credential-backed Principal/Ward integration, provider retrieval or derivation
graph. Injected-authorizer tests prove consultation and refusal, not deployed caller security.
Activation checks metadata and controls; only an authorized payload read establishes byte
integrity. Native Linux physical retirement and power-loss recovery still need receipts. Known
restore, clone or uncertain history cannot activate; in-place rollback by a hostile same-UID
process is outside this trusted profile. Intent and Bridge remain text-only, with no artifact or
required-modality fields in the Run ledger. A bare `ArtifactRef` grants neither custody nor access.

**Evidence**

- **Source:** [Artifact reference](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/artifacts.py), [custody contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/artifact_custody.py), [local adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/artifact_custody.py), and [Intent](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/router.py)
- **Verification:** [Custody contract tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/test_artifact_custody.py), [filesystem lifecycle and refusal tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_artifact_custody.py), [delegated coordinator tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_coordinator.py), and [PostgreSQL delegated-artifact receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py)
- **Law:** [Persistence](./adr/06-persistence.md#reliquary-custody-designed), [Vision](./adr/36-vision.md), and [trusted local authority](./adr/38-iam.md#trusted-local-custody)

## Evolution and federation {#evolution-and-federation}

### Archive intake and semantic memory {#karma-semantic-memory}

**State:** Partial

**Proved now:** The opt-in `local-public-notes@1` profile admits explicit public notes to one
configured PostgreSQL namespace. Exact request and source revisions are idempotent; explicit
promotion, supersession, archival and revocation enforce lifecycle versions. Revocation clears
controlled text and its search index while retaining minimal anti-reingestion identity. Bounded
lexical recall writes text-free receipts and rechecks current subject, namespace, policy and
selected revisions before returning source bytes. Transaction timeouts bound database work.

`bridge_chat@3` pins the exact local chat capability and Archive profile at admission. Its
read-only answer uses an attributed transient source message, reserves its Context budget, and
revalidates the receipt before dispatch, each model request and settlement. It exposes no tools
and replays no settled history. PostgreSQL tests cover real HTTP controllers, Run admission and
worker execution, typed checkpoint reconstruction, stale-source refusal, migration lineage and
the actual restricted runtime database role. Earlier Bridge manifests remain retained unchanged.

An independent optional Archive configuration exposes its exact generation reference through
the authorized `GET /api/v1/archive/derivations/generations/configured` route. Discovery checks
current policy without reading storage, registering rows, acquiring a lease or probing a model.
The caller can then explicitly register that generation and derive promoted notes into
1024-dimensional pgvector values. Each explicit attempt retains
its source, profile and generation identity, with a database deadline and conditional completion.
Archive, revocation, supersession and generation retirement clear affected vectors and prevent
late results from restoring them. Status exposes metadata only; expired work requires an explicit
retry. PostgreSQL tests cover concurrency, expiry, lifecycle races, float32 round trips, migration
rollback and restricted runtime permissions. The configured HTTP test uses the real Core driver
with substituted model responses, covers discovery through registration and derivation, and
shares the application's lease ledger without emitting Run events for caller-supplied Run identifiers.

**Boundary — Not yet:** This is lexical RAG for explicit same-host public notes, without semantic
retrieval, general `CandidateArchivePort`, automatic conversation retention, extraction, Curator,
GraphRAG, shared namespaces, remote IAM, private-material egress or training. There is no Archive
browser editor. Ordinary revision 3 execution uses live Graph persistence; separately proved typed
checkpoint reconstruction does not establish automatic recovery after worker death. The model and
resource seams in the vertical receipt are controlled fixtures, not a live GPU/model qualification.
The derivation path has no background worker, automatic model activation, chunking or ANN index;
oversize notes refuse. The separate live Core embedding proof does not qualify the combined
Archive/database/model path.
Generated answers can quote sources; later revocation does not erase earlier output or influence.

**Evidence**

- **Source:** [Archive contracts and service](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/archive), [PostgreSQL adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/archive.py), [migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0012_archive_public_notes.py), [Archive API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/archive.py), [transient projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/archive_context.py), and [public-note workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/archive_chat.py)
- **Source:** [Derivation service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/archive/derivation_service.py), [derivation store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/archive_derivation.py), [migration 0013](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0013_archive_derivations.py), and [configured derivation API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/archive_derivation.py)
- **Verification:** [Domain tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/test_archive.py), [PostgreSQL lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_pg.py), [migrations](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_migrations_pg.py), [runtime role](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_runtime_pg.py), [worker and typed continuation](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_vertical_pg.py), and [projection tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_archive_context.py)
- **Verification:** [Derivation races](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_pg.py), [configured HTTP and lease integration](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_http_pg.py), [migration rollback](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_migrations_pg.py), and [derivation runtime role](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_runtime_pg.py)
- **Topic:** [Public-note answers](./divination/altar/bridge.md#public-note-answers)
- **Law:** [Memory](./adr/27-memory.md)

### Mirror identity {#mirror-identity}

**State:** Designed

**Proved now:** Identity law defines a filtered, revisable binding rather than a second cognitive
runtime.

**Do not expect yet:** There is no identity store, synthesis loop, hydration adapter, versioned
Persona, calibration, or promoted persistent identity.

**Evidence**

- **Topic:** [Mirror](./sepulcher/extensions/mirror.md)
- **Law:** [Identity](./adr/32-identity.md)

### Shadow simulation {#shadow-simulation}

**State:** Designed

**Proved now:** Simulation law defines branch expansion, scoring, pruning, authority, and verified
collapse, including versioned exploration strategies and retained histories for bounded replay.

**Do not expect yet:** There is no runnable branch graph, MCTS engine, branch store, exploration
strategy executor, budgeted simulation, collapse implementation, or reaper.

**Evidence**

- **Topic:** [Shadow](./sepulcher/extensions/shadow/index.md)
- **Law:** [Simulation](./adr/31-simulation.md)

### Drift evaluation {#drift-evaluation}

**State:** Designed

**Proved now:** Evaluation law binds declared goals to versioned Cases and Rubrics, with adversarial
evidence, capability comparison, and calibration. The reference workflow-improvement method
specifies baseline/candidate comparison, causal replay limits, human-attention measures and
proposed starter Cases. It includes a historical exploration-replay pilot outline; evaluation law
distinguishes mechanism reuse from measured improvement in its successors.

**Do not expect yet:** There is no runnable harness, replay simulator, maintained suite, scorer
contract, benchmark history, pass-at-k experiment, or routing update.

**Evidence**

- **Topic:** [Drift](./sepulcher/extensions/drift/index.md) and
  [workflow improvement](./sepulcher/extensions/drift/workflow-improvement.md)
- **Law:** [Evaluation](./adr/34-evaluation.md)

### Soulforge training {#soulforge-training}

**State:** Designed

**Proved now:** Training law defines how consecrated examples may enter governed training. The
discernment-training reference applies it to conditional human corrections, lineage-safe splits
and independently evaluated model candidates.

**Do not expect yet:** There is no dataset harvest, training job, isolated trainer, checkpoint
evaluation, model registration, rollback, or production promotion.

**Evidence**

- **Topic:** [Soulforge](./sepulcher/extensions/soulforge/index.md) and
  [discernment training](./sepulcher/extensions/soulforge/discernment-training.md)
- **Law:** [Training](./adr/33-training.md)

### Offline Evolution comparison {#evolution-comparison}

**State:** Available

**Proved now:** A bounded offline mechanism checks caller-admitted historical obligations and
retain, reconcile, replace or reject dispositions against an exact base, candidate, policy and
history. For retain, reconcile and replace, missing required, failing, conflicting or mismatched
summaries block; replacement requires declared owner retirement and transition/recovery evidence. Deterministic reports distinguish completed
comparison, recorded rejection and blocked work. Focused tests cover insecure-contract retirement
with unrelated-extension preservation, exact replay and strict input refusal.

**Boundary:** This is consistency checking over admitted claims. It does not retrieve or
authenticate artifacts, establish factual test results or independent evaluation, create a Drift
Outcome or Promotion Request, persist an adoption ledger, dispatch work, or authorize activation.
Native autonomous Creation and target-owner promotion remain designed.

**Evidence**

- **Source:** [Comparison contract and calculation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/evolution/comparison.py) and [offline utility](https://github.com/hexanomicon/lychd/blob/main/scripts/compare_evolution.py)
- **Verification:** [Historical comparison and input-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/test_evolution.py)
- **Topic:** [Ouroboros operation](./sepulcher/extensions/weaver/ouroboros.md#run-an-offline-historical-comparison)
- **Law:** [Evolution](./adr/18-evolution.md#synchronic-syncretizer)

### Creation and Forge promotion {#smith-forge-promotion}

**State:** Partial

**Proved now:** The narrower [Creation investigation](./compositions/creation/index.md) revision 2
has a PostgreSQL store, explicit selector, protected local API, fixed serial Pattern and distinct
constructor/verifier AgentSpecs. It retains original request/source/profile bytes, admission
attribution, reserved attempts, complete provider responses and separate candidate/verdict. Current
credential-backed local object/action policy and actual Run state fence claims and adoption.
Invalid, duplicate-key and length-terminated output remains retained noncompletion without repair
calls. Valid citations establish exact source spans, not semantic correctness. Deterministic line
counts guide both roles without changing source bytes or relaxing citation validation.

Focused unit/API and real PostgreSQL cases cover admission refusal, observed-usage limits,
authority and profile changes, cancellation winning adoption, worker loss after candidate commit
followed by one explicit fresh-authority verification Run, and unknown claims retaining the slot.
Migration `0016` covers empty-cycle and retained-custody downgrade refusal. Those worker histories
reconstruct adapters in one process with a captured queue and inert model; they do not prove an
OS-kill or live broker. Generated OpenAPI/TypeScript and the frontend checks pass.

A dated operator observation at `3e518e81` also records an actual Qwen3.8 constructor/verifier pair:
two calls retain separate outputs, two ordinary application lifespans preserve custody, changed-base
replay refuses, and exact replay under fresh current credentials performs no inference. Native
verification returns `accepted`; a separate coding-agent review judges the content **partial**:
the core assertions are supported, but generic-message assurance is overstated and replacement
wording lacks the appropriate source citation. The native verifier misses those qualifications.
The earlier length-limited and invalid-span occurrences remain failed observations. This one-case
profile injects settings, Rune and extension declarations and a refusing runtime actuator into the
real application; it qualifies neither normal configuration/deployment, semantic reliability,
independent-model verification nor autonomous improvement.

A separate dated observation at `b3820bd` uses ordinary XDG/TOML/Rune loading, native CLI,
credential-backed loopback TCP, live SAQ workers and a separately owned SCRAM PostgreSQL cluster,
with no fixture injection. One complete constructor response is retained as `incomplete/output_bytes`:
its canonical result is 1619 bytes against the unchanged 1536-byte ceiling. No candidate is adopted
and no verifier runs. An ordinary native CLI restart preserves exact case custody; exact replay
performs no additional inference. Root independently observes unit/group/process/listener closure,
matching model counters and unchanged installed bindings. The task container is removed; its named
storage is intentionally retained. This qualifies normal loading and retained noncompletion/replay,
not permanent deployment, useful semantic completion, crash recovery or hostile-runtime containment.
Native aggregate enforcement covers pids only; per-process limits and separate PostgreSQL limits
are narrower observations.

A distinct occurrence at `7929389` states that same canonical-output ceiling and concise writing
margin in both role instructions. Ordinary configuration, native CLI, SAQ and protected TCP
complete both calls in approximately 23 seconds (3743 prompt and 550 generated tokens), adopting
candidate and verdict. Native disposition is `accepted`; external review judges both **partial**:
settlement assertions cite only replacement-message prose, and the error string is blurred with
the exception object. The actual test supports those assertions elsewhere; a valid span alone does
not support the claim. This is a known-task iteration, not a controlled causal comparison or
semantic reliability benchmark. Two ordinary app starts retain the new case, exact replay issues
no inference, and the earlier failed case survives database-container replacement with unchanged
named storage. Independent resource/model observations settle the task processes, listeners and
container; storage intentionally remains. No permanent daemon, autonomous editing or improvement,
crash recovery, whole-environment closure or model-byte attestation follows.

A separate protected feedback surface now retains an exact external UTF-8 report, claimed reviewer
and authenticated submitting authority against the original request/profile/candidate/verdict and
source/criterion identities. Optional submitter annotations stay distinct from the report; absent
criteria remain `not_assessed`. An explicit owner `hold` or `reject` preserves the native verdict.
Canonical identical replay returns original attribution; conflicting identity refuses. Case locking
serializes append sequence and current decision, and a new assessment makes prior decisions
historical. Feedback neither expires nor mutates original execution and requires settled bound
Runs/deliveries, resolved inference and no matching local lease. Historical revision 2 assessment
needs no current model readiness. There is no successor proposal or execution path.

Focused tests cover current credentials, scopes, Origin/CSRF, duplicate JSON, literal report and
canonical target bounds. Fourteen real PostgreSQL cases cover custody, restart attribution,
concurrent sequence/decisions, capacity/replay, post-lock revocation and settlement refusals. The
complete affected migration module passes 89 cases, including additive `0017`, original custody
and retained-feedback downgrade refusal. Generated API/client checks and 341 frontend tests pass;
previous OpenAPI paths/schemas are unchanged. These trusted inert-model checks issue no inference.
A dated ordinary-native observation at `69829ad` appends the original 2611-byte external report
and explicit owner hold in approximately 10 seconds, with no additional inference. Native `accepted`,
external `partial` and owner `hold` remain separate. An ordinary different-process restart and fresh
protected client preserve both historical cases, exact feedback and original attribution; changed
same-ID bodies refuse. The API does not expose the restarted current authority generation. Root
independently observes task processes, ports, unit/group and container absent, unchanged model
counters and installed bindings, and exact retained named storage without attachment. A complete
private logical backup precedes migration; restore and rollback remain unproved. This establishes
dated ordinary feedback custody and settlement, not a successor, automatic editing or measured
improvement.

A further unfamiliar case at `16da86f` retains `incomplete/UnexpectedModelBehavior` after one
constructor call (1956 prompt and 423 generated tokens), with no adopted candidate or verifier.
Offline validation of the exact returned arguments finds a 514-character summary against 512;
compact JSON is also 1632 bytes against the unchanged 1536-byte ceiling. The SDK's internal exception
message was not retained. Separate source-only review finds the core ordering and possible
counterexample correct, but both criteria fail operative citation support: test line 31 checks
non-None; the decisive maximum-ID assertion is line 32. The approximately 29-second native occurrence
preserves this noncompletion and earlier custody through normal restart and observed protected
replay without new inference. Independent resource/model settlement passes; owned storage and the
private backup remain. Private operator lineage supplies no native successor authority. This is a
failed transfer observation, not useful native completion or measured improvement.

Explicit numbered-source presentation now reconstructs the exact original request and UTF-8 bytes;
concise per-field guidance changes both instruction keys to v4 and implementation to `py.5`.
Dense-line overflow refuses before admission; existing packet/output limits remain unchanged.
A dated known-case correction at `18235a8` completes both roles in approximately 28 seconds,
using 6216 prompt and 646 generated tokens across two calls. Both retained packets roundtrip;
1115/1023-byte canonical outputs meet the unchanged 1536-byte ceiling. Native `accepted` and
external judgment remain separate: fresh source-only review gives both outputs ordering PASS,
discrimination PARTIAL. The operative test citation is now line 32, but both roles categorically
assert that the last parked random UUID is greatest; their own qualification denies guaranteed
UUID/insertion order. The verifier accepts that same defect. The correct counterexample is
conditional on the second ID being greater. Normal restart and observed protected POST replay
preserve the new case, three historical cases and parent hold without new inference. Independent
resource/model settlement passes. This is one known-case correction observation, not causal
improvement, unfamiliar transfer or native successor authority. An earlier zero-inference transport
failure and its narrow observer-only repair remain separately recorded; its precise cause is unproved.

A subsequent ordinary-native feedback occurrence at `5844a22` appends the exact 2977-byte public
report and separate local owner hold in approximately 8.7 seconds, with zero inference. Both typed
criterion coverages remain `not_assessed`; report PASS/PARTIAL text is not submitter annotation.
Native accepted, external partial and owner hold remain separate. Normal distinct-process restart,
fresh protected client, observed POST200 replays and 409 conflicts preserve all four CaseViews,
old parent hold, exact new feedback and original authenticated attribution. The API does not expose
current authority generation. Independent resource/model settlement preserves original storage and
backup; no bootstrap, migration, new backup or source change occurs. A preceding zero-write setup
failure used an unconfigured version-table name; the corrected read-only query follows the owning
LychD constant. The precise database error was not retained. No successor authority follows.

The wider SDLC law defines attributable request → candidate → verification → promotion-request →
target-owner-effect ownership. The Creation method and Ouroboros map connect work to separately
governed evaluation, memory, training and body change. The Development bootstrap procedure orders
operator-controlled work and incremental qualification; these methods introduce no general scheduler
or autonomous development service.

**Boundary — Not yet:** This investigation performs no source editing, executable workspace,
filesystem/command execution, safe Forge, autonomous repair, target-owner promotion, rollback or
self-extension. Its local credential role supplies no remote IAM or person-level tenancy; an
unknown issued inference has no automatic slot-release path. External feedback supplies no native
successor lineage/admission, automatic correction or measured recursive improvement. There is
likewise no instantiated
distributed repository identity or maintainer roster, executable key-custody/rotation mechanism,
governance-epoch ledger, quorum verifier, signed portable promotion envelope, independent
attestation plane, canonical source on Radicle, Radicle node topology or downstream-mirror cutover.

**Evidence**

- **Source:** [Investigation service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/services.py), [Pattern](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/workflow.py), [PostgreSQL owner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/creation.py), and [protected API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/api/creation.py)
- **Verification:** [Agent boundaries](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_creation.py), [local API](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_creation.py), [PostgreSQL worker histories](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_creation_postgres_vertical.py), and [migration cycle/refusal](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_migrations_pg.py)
- **Verification:** [Dated native investigation outcomes](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/investigation-2026-10-17.json) retains the three distinct occurrences, exact public inputs/outputs, resource evidence and separate verdicts.
- **Verification:** [Ordinary native configuration observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-configuration-2026-10-17.json) retains the separate noncompletion, exact public packet/result, canonical-byte failure and bounded service/replay evidence.
- **Verification:** [Ordinary native two-role observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-configuration-guidance-2026-10-17.json) retains the distinct successful occurrence, exact public role packets/results, replay/custody observations and separate partial external judgment.
- **Verification:** [Ordinary native feedback observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-feedback-2026-10-17.json) retains the exact external report, separate native/external/owner dispositions, normal restart/replay and bounded resource observations.
- **Verification:** [Unfamiliar native noncompletion](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-successor-2026-10-17.json) retains the exact public role packet, unadopted output, separate schema/byte failures and attributed citation review.
- **Verification:** [Known-case source projection](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-source-projection-2026-10-17.json) retains both exact projected packets/results, native accepted, separate partial external judgments and normal restart/closure observations.
- **Verification:** [Native attachment of the later review](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-source-projection-feedback-2026-10-17.json) retains the subsequent exact-report attachment, separate partial/hold, typed coverage, replay/restart and zero-inference settlement.
- **Topic:** [Creation investigation](./compositions/creation/index.md), [Smith](./sepulcher/extensions/smith.md),
  [Creation](./sepulcher/extensions/weaver/creation.md), and [Ouroboros](./sepulcher/extensions/weaver/ouroboros.md),
  with [Development bootstrap](./sepulcher/extensions/weaver/development-bootstrap.md) and
  [coding-runtime research](./sepulcher/extensions/weaver/coding-runtime-research.md)
- **Law:** [SDLC](./adr/16-sdlc.md), [Packaging](./adr/17-packaging.md#forge-neutral-source-trust),
  and [Evolution](./adr/18-evolution.md#future-quorum-roster)

### Remote IAM {#remote-iam}

**State:** Designed

**Proved now:** IAM law assigns remote identity and authorization to Ward rather than the loopback
Sigil.

**Do not expect yet:** There is no credential-backed principal, remote session, object authority,
delegation, revocation, tenant isolation, or audit contract.

**Evidence**

- **Topic:** [Ward](./sepulcher/extensions/ward.md)
- **Law:** [IAM](./adr/38-iam.md)

### A2A and Intercom {#a2a-intercom}

**State:** Designed

**Proved now:** A2A law defines sovereign asynchronous labor, bounded public-task envelopes,
verification, replay, expiry and revocation boundaries, and durable inbox/outbox ownership.

**Do not expect yet:** There is no envelope, policy, or ledger implementation; peer/key custody,
discovery, cryptographic verifier, transport, durable inbox/outbox, callback or artifact fetch,
Run/Graph bridge, restart recovery, effect receipt, or interoperability profile.

**Evidence**

- **Law:** [Agent-to-Agent](./adr/26-a2a.md)

### Toll economics and payments {#x402-payments}

**State:** Designed

**Proved now:** Toll law separates local MANA accounting from external payment negotiation and
settlement. Toll judges economic terms before Dispatcher binds an eligible capability; neither
road requires x402 or a global asset.

**Do not expect yet:** There is no MANA ledger or issuance path, quote, reservation, authorization,
signer, conventional PAYG adapter, payment, settlement, reconciliation, budget enforcement, or safe
HTTP 402 response.

**Evidence**

- **Topic:** [Toll](./sepulcher/extensions/toll.md)
- **Law:** [Toll](./adr/41-x402.md)

### Legion federation {#legion-federation}

**State:** Designed

**Proved now:** Federation law separates cognitive Master authority from node-local physical
authority and rejects shared databases and universal credentials.

**Do not expect yet:** There is no enrollment, expiring advertisement, reservation, fencing,
artifact transfer, durable spool, cancellation, or settlement.

**Evidence**

- **Topic:** [Legion](./sepulcher/extensions/legion.md)
- **Law:** [Multinode](./adr/42-multinode.md)

### VPN Tether {#vpn-tether}

**State:** Designed

**Proved now:** VPN law defines Tether as private reachability over WireGuard without application
authority, with exact peer and route intent and separate lifecycle ownership. It distinguishes
that road from anonymous browsing and provider-visible request content.

**Do not expect yet:** There is no Tether Domain contract, Rune or provider, generated service, UDP
publication, interface or enrollment effect, peer/key custody, live route policy, health,
reconciliation, revocation effect, or identity proof.

**Evidence**

- **Topic:** [Tether](./sepulcher/extensions/tether.md)
- **Law:** [VPN](./adr/39-vpn.md)

### Proxy Veil {#proxy-veil}

**State:** Designed

**Proved now:** Proxy law assigns edge proxy and TLS composition to Veil, including explicit
plaintext custody at TLS termination. Re-encryption to Core does not remove edge visibility.

**Do not expect yet:** There is no provider, certificate lifecycle, generated edge policy,
Gateway Host manifest or Home/Remote realization, firewall projection, remote ingress hardening,
or proof that a proxy substitutes for application authorization.

**Evidence**

- **Topic:** [Veil](./sepulcher/extensions/veil.md) and [Gateway](./sepulcher/gateway.md)
- **Law:** [Proxy](./adr/40-proxy.md)

## Boundaries still to cross {#human-ruling-queue}

The missing pieces converge at a few larger boundaries. Their Covenants retain decisions;
implementation and named receipts must establish the passage before this ledger can promote it:

- single-Vessel ownership, hung shutdown, durable process leases, and multi-process event custody;
- authenticated caller/object authority, effect-time reauthorization, and remote exposure;
- extension trust, package lifecycle, stable ownership splits, and external-provider containment;
- durable Creation, memory derivation, privacy, training eligibility, promotion, and rollback; and
- Linux platform floor, production-browser evidence, and recovery of ambiguous physical effects.

## Operator receipt requirements

A receipt names the exact commit, configuration, host and security context, runtime and dependency
revisions, hardware/model identity when relevant, commands, expected and observed results, bounded
timings, useful work, cancellation, shutdown, recovery, redacted logs, artifact digests, date,
operator, verdict, and uncovered boundary. A materially different engine, model, image, driver,
hardware topology, or configuration needs its own receipt.

## Update law

When behavior or evidence changes, update source, focused verification, the owning topic, and this
one delivery record together; downgrade immediately when proof disappears. Do not copy canonical
states into README, Prophecy, Lexicon, ADR indexes, or every Composition leaf.

## Enter the Work

Perform [Summoning](./summoning.md) to test one bounded local conjunction. Preserve the observations
as a named receipt; hope does not promote a delivery state.
