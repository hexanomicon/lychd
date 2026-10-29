---
title: State of Work
icon: material/list-status
---

# State of Work

LychD is **pre-alpha**. This page answers the practical question that follows the grimoire's
promise: what can this revision actually support, and where is the evidence?

The supported runtime boundary is local, loopback-oriented, single-user, one control process,
and a managed container Vessel. Host-native Core deployment and Core test deployment are retired.
Core checks execute only in the explicit OCI test image. A fresh production-image and Ward
PostgreSQL observation is recorded separately from the retained observations below.
Start with an outcome below, then read the relevant record as a whole: its state, proved subset,
limit, and evidence belong together. The Covenants own architectural decisions; this ledger owns
their delivery interpretation.

## Outcome matrix

| Scenario | Answer now | Decisive limit |
| --- | --- | --- |
| CLI bootstrap | **Partial:** grammar, transactional initialization/binding and guarded lifecycle control have source contracts. Native installed-hybrid observations are frozen history. | Full generated rootless deployment and managed-model lifecycle remain unqualified. See [CLI](#core-cli-rites) and [embodiment](#systemd-podman-embodiment). |
| Local text chat | **Partial:** retained source, browser and installed-hybrid receipts record structured replies and a bounded useful task under their dated profiles. | General answer quality, wider browser acceptance and full generated installed deployment remain pending. See [vLLM](#vllm-integration), [Bridge](#bridge-surface) and [persistence](#phylactery-first-light). |
| Browser safety | **Loopback only:** a dedicated local credential precedes the fixed Sigil; Host, Origin, CORS, CSRF, and generated bind policy are bounded locally. | Remote IAM and hostile-browser acceptance remain unsupported. |
| PostgreSQL lifecycle | **Historical restart receipts:** source TCP, source-browser and installed-hybrid profiles retained structured history across native boots before retirement. | These frozen profiles do not qualify current OCI tests or a rebuilt Vessel; checkpoint-plus-consent recovery, crash and full generated deployment remain unqualified. |
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

## Current evidence envelope {#current-evidence-envelope}

The 20 October 2026 container-only correction retires the former Core host-native runtime and
its native stop, credential-source, server/TCP and host fixtures. Core pytest, lint, format checks
and typing now enter the explicit `Containerfile.tests` image through the Makefile and bounded
OCI harness. Domain/ASGI helpers may still construct the application inside that image. Those
helpers do not create another supported deployment. The 21 October OCI recheck passed lint,
formatting, strict typing and 6,447 tests, with 14 explicit optional skips and 525 container
deselections. The PostgreSQL ledger module separately passed all 42 cases, including retained
event fields, sequence, cursor and kind-filtered reads. Altar passed type checking, all 617 tests
and its static build; generated API contracts and dependency locks stayed unchanged. The dated
20 October OCI occurrence passed all 23 Ward/candidate PostgreSQL cases.
The rebuilt, unmodified production image completed all 20 migrations with system libpq, then
two authenticated empty-workload boots and normal SIGTERM exits as UID 1001, with a read-only
root filesystem. Host, Origin and CSRF refusals passed on both boots. Its fresh bridge, mounted
synthetic credentials and empty owned Reactor directories do not qualify the generated managed
body, real Reactor transitions or a model workload. All owned proof containers, volumes and
networks were removed; no model request was sent. The [dated production recheck](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/runtime/container-recheck-2026-10-21.json)
binds the 21 October production observation to its actual inputs. Its source closure no longer
matches the combined source; the receipt oracle preserves those observations and refuses current
qualification until a new production occurrence is recorded. The unchanged
[20 October OCI receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/runtime/container-only-2026-10-20.json)
retains its dated production observation and the separately bounded Ward inputs. Active public
container start/stop completion remains unavailable; F2 hostile-constructor and F5 enrolled-peer
qualification are not added.

The combined migration source preserves the existing `0015`–`0020` lineage and appends disclosure
custody at `0021`, Intercom at `0022` and native peer Graph custody at the current head `0023`.
This source reconciliation does not renew the 21 October production observation or the imported
22–23 October peer and companion observations. Their original source maps, migration identities,
dependencies and limits remain dated evidence; current combined-source qualification is separate.

The raw warm-model ASGI, sequential `spawn`, source-native TCP, trusted source-browser and
installed-hybrid receipts are frozen dated history, retired on **2026-10-20** at source base
**7057210a**. Their historical validators preserve original receipt bytes, source maps, dependency
lineage, oracles and limits; they do not compare those old profiles to current code or renew their
observed facts. The former current-source TCP shared-chain join is historical as well.

The ASGI and spawned profiles recorded one real structured Bridge reply and identical turns/model
history across two application lifespans or two sequential processes, without second-boot
inference. The source-native TCP occurrence additionally recorded authenticated readiness, four
security refusals, one complete SDK reply and normal process closure. Its 20 October renewal used
511 prompt and 143 generated tokens and passed the retained 18 terminal checks. Explicit
Settings/Runes, lifespan wrappers, refusing host actuation and per-process limits bound those
observations; none qualifies the current container or managed-model lifecycle.

The frozen [trusted source-browser receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-browser-2026-10-20.json)
recorded compiled Altar and sandbox-enabled Chrome against the retired source-native CLI/Granian
fixture: authentication, four security refusals, controlled local503 with zero upstream POSTs,
one useful reply, keyboard Bridge→Orb→exact Loom→Bridge navigation and retained reload after a
second normal boot. Its [historical validator](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_browser_receipt.py)
preserves that profile and dated assets. Retained failed text does not imply every live badge
survives. This is historical browser evidence, not current container-fixture, installed, hostile
browser or general usability qualification.

The frozen [trusted installed-hybrid receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-installed-hybrid-2026-10-20.json)
recorded source `3e30a84`, 548 matching installed files, 91 dependency versions, 20 migrations and
a matching migration image, one useful reply, two native boots/signed stops and normal
private-manager exit. Its [historical validator](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_installed_hybrid_receipt.py)
preserves the old package/profile facts. Plain Docker dependencies, inert model units and borrowed
warm vLLM did not execute the full generated rootless body or qualify managed-model lifecycle.
The separate installed-source `0cc0988` activation observation retains its own historical scope
under [vLLM](#vllm-integration).

The developer fixture remains a separate read-only memory composition with real controllers and
security, synthetic failed Run/Pattern links and refusing execution. `make developer-fixture`
runs it in the explicit OCI image at fixed internal `0.0.0.0:8000`, published only at host
`127.0.0.1:8000`. Its current source and frontend guards remain; a new image/browser occurrence is
pending. The fixture reads no operator configuration or credentials and grants no production
authority. [CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md)
owns the workflow.

All older ordinary-native Core startup/restart and browser observations elsewhere on this page
retain only their dated profile, even where the report quotes an occurrence as successful.
Domain uses of “native”—including the live checked Ward candidate-authority foundation—retain
their own meaning and are not retired by this deployment correction.

- **Source:** [Application factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py), [Developer fixture](https://github.com/hexanomicon/lychd/blob/main/src/lychd/developer.py), [OCI harness](https://github.com/hexanomicon/lychd/blob/main/scripts/container_checks.sh)
- **Verification:** [Two-boot lifecycle helper](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py), [Developer fixture controls](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_developer_fixture.py)
- **Law:** [Containers](./adr/08-containers.md#core-deployment-and-verification), [Testing](./adr/04-testing.md), [Backend](./adr/11-backend.md)

## Inscription and embodiment {#inscription-and-embodiment}

### Settings generations {#settings-generations}

**State:** Available

**Proved now:** Root Settings loads separate bootstrap, runtime and Phoenix database credentials,
the local HTTP access credential, and web signing key once per
construction as excluded `SecretStr` values. Cached consumers and in-memory snapshot restoration
perform no credential I/O; JSON and generated TOML omit credentials. Explicit new Settings reads
fresh inputs. Host bootstrap tolerates unprovisioned default mounts; runtime components reject
missing credentials. Container bind preflight validates the declared secret references before
compilation; application startup consumes only its narrowly mounted runtime secrets.

The former `LYCHD_RUNTIME_SECRETS=podman-core@1` host-native source is retired. Explicit selection
refuses before credential I/O; there is no automatic fallback, conversion, rotation or export.
The host Podman adapter retains its separate bind/access role.

**Boundary:** This covers the declared DB/web credential contract, not every extension's handling,
new image-mounted secret readability or live retained-role agreement. No automatic credential
reload is delivered. Prior native source-control evidence is historical.

**Evidence**

- **Source:** [Settings](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/root.py), [Credential source](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/sources.py)
- **Verification:** [Credential tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_credentials.py), [Settings tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_settings.py), [Binding preflight tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_binding_preflight.py)
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
are tested. Direct `start system` now separately requires an exact quiescent opposite Vessel
observation after owned-state revalidation; unknown or conflicting evidence refuses without
adopting or controlling that counterpart. Focused tests cover both fixed identities, malformed
replies, pending work and timeout. This is a start admission check, not continuous exclusion or
an installed native graph qualification. Mutating paths use revalidation, no-follow identity checks, lifecycle locking, durable
receipts, and explicit rollback or indeterminate outcomes. An unsafe shared binding site blocks
initialization planning and the layout preflight; safe existing modes are preserved.

The host-native signed-stop profile and route are removed. Current active Vessel lifecycle
operations refuse before effects until authenticated container admission and exact
container/service settlement are implemented and qualified. Safe inactive bootstrap control
retains its narrower source contract. Legacy native bindings remain observable but block mutation;
retirement provides no stop, conversion or deletion authority.

The shared image launcher owns ordered startup, HTTP callback retirement and application closure;
required failure propagates. A successful exit or manager reply alone cannot establish full
container lifecycle completion. The old inert native TCP/private-manager stop trials, retained
Scavenger readback/stops and installed-hybrid stops remain dated history under the
[current evidence envelope](#current-evidence-envelope), with all original failures and limits.

**Boundary — Not yet:** Status omits full readiness and durable-run health; no run-operation command
or authenticated Run submission route is delivered. Active container stop/start completion,
active-work shutdown, rebuilt-image lifecycle and managed GPU/model operation remain unqualified.
Unknown unit or mount truth blocks; deletion preserves objects without owned creation provenance.
No direct-manager or native fallback is admitted.

**Evidence**

- **Source:** [CLI assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__main__.py) and [layout admission](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/layout.py)
- **Verification:** [CLI tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py) and [init binding-site tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_init_binding_sites.py)
- **Verification:** [Exact counterpart start admission](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/operator/test_vessel_counterpart.py)
- **Source:** [Owned launcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/server.py)
- **Verification:** [Lifespan/retirement tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_server.py)
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

The frozen [trusted installed-hybrid profile](#current-evidence-envelope) recorded its private
manager, installed native CLI, plain Docker PostgreSQL/migrator dependencies and borrowed warm
model with inert owned model units. It does not execute the full generated rootless graph or
qualify managed-model lifecycle.

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

The current operator trial's mandatory hostile-constructor enforcement is externally blocked
under the operator's administrative-test deferral. Trusted candidate-byte
custody is not that enforcement. Positive candidate adoption and fresh-generation activation
remain separate undelivered implementation work; an external prerequisite does not complete them.

**Evidence**

- **Law:** [Security](./adr/09-security.md)

## Persistence, execution, and consent {#persistence-execution-and-consent}

### Phylactery first-light persistence {#phylactery-first-light}

**State:** Partial

**Proved now:** Run, delivery, step, session, consent, checkpoint, and delegated-wait shapes exist
with sequence-fenced claim and settlement, terminal-evidence-fenced owner-specific resume gates,
startup reconciliation, and PostgreSQL migration checks. A historical factory receipt completed and
recovered a Bridge Run across two boots; a frozen warm-vLLM profile retained its actual
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
test substitutes offline collaborators after startup. The source ASGI, spawned-process and TCP
warm-model profiles use explicit test composition. Distinct
[trusted browser and installed-hybrid profiles](#current-evidence-envelope) record only their historical
normal-restart/readback paths; none qualifies current container runtime or establishes checkpoint-plus-consent recovery, process crash
or a full generated installed deployment.

**Evidence**

- **Source:** [First-light migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0001_phylactery_first_light.py), [wait-owner migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0008_wait_owner_evidence.py), and [database factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/factory.py)
- **Verification:** [Run ledger tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py), [PostgreSQL run-ledger receipts](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py), [database authority receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_database_authority_pg.py), and [two-boot lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Verification:** [Joined warm-model Bridge test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_runtime.py), [maintained receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-runtime.json), and [historical receipt integrity](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_receipt.py)
- **Verification:** [Independent-process restart test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_process_restart.py), [maintained process receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-process-restart.json), and [historical process-receipt integrity](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_process_receipt.py)
- **Verification:** [maintained native TCP receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-native-tcp.json), and [historical native receipt integrity/privacy](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_native_tcp_receipt.py)
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
The same selector also admits the bounded [public-note and semantic-source-answer](#karma-semantic-memory)
and [Scout public-page](#scout-web-acquisition) revisions; their authority and evidence boundaries
remain with those records. The explicitly boot-selected `bridge_chat@5` retains its complete exact
Archive generation manifest/reference, threshold and finite recall bounds with the local Chat key.
Omitting configuration still selects revision 1 for new admissions.

Revision 2 also accepts a bounded two-route local Chat preference instead of an exact configured
key. Strict integer weights rank only freshly observed warm routes with unchanged declarations
and open, unchanged admission generations after one cooperative five-second probe batch. Zero
disables eligibility and omits retained phase/time; a shared Animator's complete probe may still
include that capability. Ties use literal key order. Admission retains the complete policy, digest,
observations and selected exact key. Idempotent replay bypasses selection; controlled reconstructed
records retain the decision, and malformed retained bindings refuse reconstruction. A safe 503
code reports probe failure or an empty eligible set before retaining a Run or user turn.
Real PostgreSQL concurrent sessions retain one winning policy and exact key; a reconstructed
adapter and idempotent lookup return that decision, while changed JSONB digests, selected keys
or admitted bindings refuse reconstruction.

**Boundary — Not yet:** The Chat key pins capability identity, not a chat model artifact or runtime
declaration generation for future execution. The preference batch reserves no future readiness; existing exact-key
execution, tools, consent and retry rules still apply. There is no execution fallback, adaptive or
multimodal route policy, portable Resolution Lock, or general Pattern/AgentSpec/Context selector.
Settings loading does not contact an engine. Revision 2's exact-key configuration checks declaration
at execution; revision 5 also validates exact local Chat and embedding declaration metadata at boot
without readiness or model work. The preference mode checks both declarations at admission,
including disabled routes.
Live two-route preference remains unqualified; existing default-Bridge receipts do not establish
it. The synthetic PostgreSQL controls use ORM metadata and do not claim migrations or a server restart.

**Evidence**

- **Source:** [Weaver settings](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/weaver.py), [Bridge workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/bridge_chat.py), and [Dispatcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/dispatcher.py)
- **Verification:** [Configuration tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_weaver_settings.py), [configured registry tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_configured_registry.py), [casting workflows](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_bridge_casting_workflow.py), [exact selection tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_dispatcher_exact_selection.py), and [semantic selection, admission and metadata-only composition](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_semantic_answer_admission.py)
- **Source:** [Preference admission](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/bridge_preference.py), [Run admission](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py), and [retained decisions](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/ledger.py)
- **Verification:** [Preference controls](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_bridge_preference.py), [Run admission and replay](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py), and [safe HTTP refusals](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge_preference.py)
- **Verification:** [PostgreSQL retained winner and corruption controls](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py)
- **Topic:** [Choose a Bridge capability](./sepulcher/extensions/weaver/index.md#choose-a-bridge-capability) and [prefer a ready route](./sepulcher/extensions/weaver/index.md#prefer-a-ready-route-at-admission)
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
currently originates approval. The [consent-history contract](./adr/25-hitl.md#consent-history-and-proposal-branches)
defines immutable proposals, revision branches, attributable decisions and linked effect receipts.
Its append-only journal, independent retention, supersession/issuance fencing, legacy import,
authorized paginated history API and Bridge/Orb tree remain Designed; current Consent rows and
pending cards do not implement that history.

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

A frozen historical profile joined the source-registered vLLM adapter to the production factory,
Dispatcher, Graph, Context, SAQ and PostgreSQL. One actual streamed `BridgeReply` settles; the same
turns and valid model history survive a second application boot without another model POST.
Both startups observe the exact shared model as `WARM`; no lifecycle actuation occurs. HTTP is
TestClient and the host actuator is a refusing fixture. A second selection performs those boots
in independent sequential `spawn` processes: the first fully exits before the second, which
retains identical settled turns and history and submits no inference. This recorded the former clean
application-process restart profile; both selections used TestClient HTTP and do not qualify current OCI execution.

A third frozen historical selection invoked the removed source CLI native Granian launcher with real loopback
TCP. Both boots reach authenticated HTTP readiness. Before one admitted Run, wrong or absent
local access and foreign-Origin or missing-CSRF message submissions refuse with zero durable
Runs and model POSTs. One structured reply settles through the production services and the second
normal process boot recovers identical turns/history without inference. The test supplies
Settings/Runes, wraps the real production lifespan and refuses host actuation; engine disposal
after CLI return is supplemental test cleanup. Observed native limits apply per process after
interpreter/module startup; PostgreSQL's separate CPU, memory and PID limits were read back.
This recorded only the retired TCP and clean-restart conjunction, without installed caged-body,
managed-model, model-byte, crash, cancellation, browser, autonomy or aggregate-native-resource
qualification.

The frozen [trusted installed-hybrid profile](#current-evidence-envelope) used the installed
local vLLM adapter and a borrowed warm model for one useful attributed reply retained across two
normal native boots and signed stops. Complete SDK history and exact durable capability/Pattern
are verified; inert owned model units do not activate the model. This bounded profile does not
satisfy full generated deployment or managed-model lifecycle requirements below.

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
- **Verification:** [Joined Bridge test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_runtime.py), [maintained warm-model receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-runtime.json), and [historical source/dependency lineage](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_receipt.py)
- **Verification:** [Independent-process test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_local_bridge_process_restart.py), [maintained process-restart receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-process-restart.json), and [historical process source/dependency lineage](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_process_receipt.py)
- **Verification:** [maintained native TCP receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-native-tcp.json), and [historical native receipt integrity/privacy](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_local_bridge_native_tcp_receipt.py)
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
runtime theme loader, or supported theme extension. Its canonical semantic palette now uses a black
work plane, neutral graphite, icy-blue interaction, green confirmation/activity and bounded
deep-purple context surfaces. Shared controls, instrument typography and graph chrome consume
that palette; fixed brand artwork remains separately attributed. There is no complete contrast matrix or bright/dim production-browser receipt;
ADR 15's bounded operator-palette contract is design law, not delivered configurability.

### Shared workbench and persistent Bridge {#altar-workbench}

**State:** Partial

**Proved now:** The shared masthead provides icon-and-label instrument navigation, an
Applications menu reachable by hover, click, or keyboard, and a separate Bridge control. One
ordinary conversation stays mounted across work navigation and collapse, retaining exact-session
drafts, unresolved offering identity, and live subscriptions. Explicit Bridge URLs still select
session, Project, Run, and consent focus. Investigation and public-note applications keep their
separate composition.

The dock supports left/right placement, bounded pointer/keyboard resizing, and layout-only local
preferences. Wide windows allocate space beside it; narrow windows provide modal focus
containment, Escape, and opener return. Navigating work or applications reveals the main view
without destroying the conversation. Source-development Canvas opens that shell offline and
makes no protected Bridge/status requests until an explicit connection. Production
authentication remains intact.

**Boundary — Not yet:** The dock supplies no new model context or attachment admission, voice,
global conversation merge, cross-instance history, durable browser draft storage or execution
authority. Viewing a page is not transmitting it to a model. Browser and component checks do not
qualify every device, bright/dim environment, forced-colour combination or the renderer's separate
cross-engine heap gate. Existing server-held recovery, current-access and consent limits remain.

**Evidence**

- **Source:** [Shell](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/AltarShell.svelte), [Bridge dock](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeDock.svelte), [conversation](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeView.svelte), [bounded layout preferences](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/navigation/dock.ts), and [semantic styling](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/app.css)
- **Verification:** [Server shell fallbacks](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py), [shell admission/status tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/AltarShell.test.ts), [mounted conversation/navigation tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeShellNavigation.test.ts), [dock interaction tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeDock.test.ts), [layout preference tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/navigation/dock.test.ts), and [offline source profile](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/routes/canvas/layout.test.ts)
- **Law:** [Shared workbench and Bridge dock](./adr/15-frontend.md#the-shared-workbench-and-bridge-dock)
- **Topic:** [Altar](./divination/altar/index.md#keep-bridge-beside-the-work)

### Canvas board authoring {#canvas-board-authoring}

**State:** Partial

**Proved now:** Canvas supplies a portable board authoring profile at `/canvas`: actual pointer
strokes, native nodes and connections, rectangle or freehand-lasso whole-object selection,
original geometry and a
same-revision bounded PNG packet, deterministic text, optional local PNG artwork, explicitly local
Tidy, bounded CPU arrangement, proposal preview/apply/reject and undo/redo. Portable JSON files
retain the current scene and bounded history; browser drafts claim no automatic retention.
Closed Composition-owned contracts and stateless scoped HTTP validation refuse stale or
out-of-selection changes, dangling references, invalid geometry and unbounded image envelopes.
Browser and Python share a conservative numeric size budget and common parity fixtures.
On the black, undotted work plane, the transient lasso follows actual stroke/connector paths
and node silhouettes without entering retained ink. The development-only source profile omits
protected status/Bridge reads until connection, so offline authoring needs no sign-in; the
compiled application keeps its authenticated shell and API boundaries.

**Boundary — Not yet:** There is no native vision transmission, live microphone, automatic model
interpretation, generated-art engine, server-retained board, collaborative editing, registered
Canvas Pattern or Invocation. The example proposal is manually authored by Codex from a captured
selection and imported; it is not a live inference receipt. Local PNG envelope validation does
not prove compressed pixels render correctly. No GPU, model, Comfy deployment, broad touch or
cross-engine browser qualification is established. Canvas does not edit Loom scores, Atlas
judgments or Orb evidence, and layout creates no semantic relation or execution authority.

**Evidence**

- **Source:** [Canvas records](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/canvas/schemas.py), [pure review](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/canvas/operations.py), [stateless API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/canvas.py), [client engine](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/canvas/engine.ts), and [Canvas surface](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/CanvasView.svelte)
- **Verification:** [Domain and parity tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_canvas.py), [HTTP admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_canvas.py), [client engine tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/canvas/engine.test.ts), [gesture/review tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/canvas/CanvasView.test.ts), [offline preview test](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/routes/canvas/layout.test.ts), and [manual model example](https://github.com/hexanomicon/lychd/blob/main/examples/canvas/README.md)
- **Law:** [Frontend](./adr/15-frontend.md#canvas-portable-board-authoring)
- **Topic:** [Canvas](./compositions/canvas/index.md)

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
preserving the stream cursor. A failed Run's nonempty live text carries an explicit notice that it
is not a completed answer, including when a terminal event already supplied a failure message.
The session snapshot's retained agent turn replaces that live projection and notice. Empty failed
text keeps the explicit no-reply message; transport errors alone do not trigger the notice.
Definitely refused text is retained alongside a later draft. Hard
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

The [trusted source-browser profile](#current-evidence-envelope) separately qualifies its fixed
controlled-failure/useful-reply, exact Orb/Loom journey and retained reload. It does not extend
Consent, other castings or public-note browser acceptance.

**Boundary — Not yet:** There is no ordinary installed production-browser receipt, durable cross-process event/token
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

The [trusted source-browser profile](#current-evidence-envelope) covers only its keyboard link
to the exact `bridge_chat@2` score and return to the same Run. It does not discharge renderer
lifecycle, graph-failure, editor or general accessibility acceptance.

**Evidence**

- **Source:** [Loom controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/loom.py), [Pattern registry contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py), [Loom client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/LoomView.svelte), and [shared graph adapter](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/graph/GraphCanvas.svelte)
- **Verification:** [Loom tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_loom.py), [client lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/LoomView.test.ts), and [semantic projection tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/graph/loom.test.ts)
- **Law:** [Workflow](./adr/28-workflow.md)

### Composition Portfolio {#composition-portfolio-delivery}

**State:** Partial

**Proved now:** The Portfolio publishes Native Reference Composition contracts and examples; the
default boot catalogue contains the Core `bridge_chat` lineage (revisions 1, 2 and 3) and
`delegated_rite` lineage (revisions 1 and 2). An explicit application selector additionally registers
the bounded `creation.investigate@2` Pattern. The exact `scavenger.observe_market@2` Pattern
is registered for historical resolution and receives new admissions only under its explicit selector.
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

Scavenger revision 3 now defines one model-free finite-feed observation contract with a complete
supplied campaign seed, whole title/link field, explicit deletion and recovery law. Pure immutable
value contracts validate the bounded seed and source-order field, group exact-locator duplicate
occurrences without dropping them, and derive a literal local filter over the unchanged field.
Their tests cover explicit unknowns, UTF-8/total byte bounds, excluded-content projection and
literal filtering. These values confer no acquisition, consumption, retention or retrieval authority.
An explicit PostgreSQL selector now enables the model-free `scavenger.observe_market@2`
Pattern and its protected application admission/read/filter/delete API. The serial Graph retains
only references, uses native Core consent and commits the whole field under application custody.
The Altar's `/scavenger` application view supplies the complete seed, displays source/coverage and
all occurrences, and separates local filtering, Run cancellation and terminal payload deletion.
[Scout's evidence boundary](#scout-web-acquisition) owns the assembled development proof and its
remaining installed, public-network and process limits.

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

A separate opt-in Horizon-assist profile admits strict finite text or externally transcribed
instructions through native Run admission, worker execution and a serial Graph. Its Linux Unix
socket adapter pins one client process generation and reported world label, enforces exclusive endpoint ownership,
rechecks policy and observed pose before send, and records client-observed outcomes without
automatic replay. Cancellation uses a second socket, drains the original reply and observes idle;
unknown or interrupted client generations remain quarantined across controller restart. An
explicit singleplayer lab mode is separate from remote-server identity. The engineering voice
entrypoint can retain one such session across bounded capture/STT/Graph attempts, private source
and transcript artifacts, native-event JSONL and stage timings, with optional generated reply WAV.
Status replies cross a closed operational projection before binding checks or result custody;
debug/clipboard, keyboard and unknown nested fields cannot enter returned status or native logs.
Portable socket/Run tests preserve useful renderer/server fields and the missing/null/malformed
server distinctions while checking exclusion from results and events.
This profile does not implement the managed placement mission or its authoritative receipts.

A separate opt-in Fabric companion lab connects typed Slovak/Czech/English text instructions
and explicitly transcribed WAV to a finite operator FIFO, native Run admission and a serial
validate/execute/report Graph. A small dedicated-server mod controls one persistent vanilla wolf
through a loopback authenticated HTTP mailbox. The server tick owns navigation, head gaze and
ordinary chat. Stop has independent admission and generation fencing; uncertain effects are not
reposted. Idle has a finite lease and performs no repeated model calls. Shared local delivery
primitives preserve the older Horizon assembly. This is an NPC body, not an authenticated player
or the canonical managed placement mission.

An explicitly selected local intent profile now adds interpretation within the same native Run
and FIFO. Pattern revision 2 retains the deterministic three-node path; raw input adds one
tool-free Agent through the exact Dispatcher grant and Forge. Closed decisions permit only state,
idle, captured-player follow, no action or clarification. One model request has finite context,
output, time and session budgets, with no repair retry, model fallback or runtime activation.
Response identity and completion metadata are checked before Agent processing; bounded provider
reasoning is discarded and only the decision is retained. Reserved-command bypasses, copied
configuration limits and substituted checkpoint targets, expiry or material references refuse.
The original capture deadline survives inference and caps physical handoff.

A live eleven-case check crossed the selected local Qwen service, native Graph and real game
bridge. Synthetic Slovak idle, Czech state and English idle applied, while the tested Slovak
negative follow and unsupported Czech building request returned no-action decisions with no game
action POST. Multiple instructions refused or returned no action. An affirmative follow proposal
for the configured offline player was refused by host policy. The typed control made no model
request; original transcript/artifact correlation and released leases were checked. This optional
model check is separate from the CPU-only typed/server/speech proof and establishes no general
language accuracy, human microphone quality or live-player following.

Operator request identities now survive queue expiry and cancellation before native admission.
Those early results resolve synchronously; owned publication tasks retain final evidence status
and are joined during stop or close. Failed evidence does not erase a known game disposition.
Stop identities have an independent finite history; historical replay and cross-kind reuse cannot
interrupt fresh work. The final history slot seals new admission while retaining its priority
barrier. Localized state feedback describes only the correlated observed mode and rounded
coordinates, without reading raw diagnostics or player identifiers aloud.

The follow controller has configurable stopping and resuming distances, defaulting to two and
three blocks. It waits near its target without requiring a path and retains the finite follow
lease; the wider resuming threshold avoids repeated close-contact navigation. Pure policy and
configuration tests cover the distance boundaries and invalid settings. An opt-in server
GameTest now drives the unchanged production controller and mailbox with normal wolf physics
and a synthetic player registered in the actual player list. It observes displacement, approach
without overlapping bodies, waiting, resumed movement, non-replacing state/chat, refused
navigation under the original lease, queue expiry, target distance/loss/death and correlated
priority stop. Its explicit synthetic lease clock advances fifty milliseconds per controller
tick; this is no real-time latency measurement. An independent wait-only policy copy fails on
missing displacement while the authoritative build passes. Both paths remove their owned
players and actor and release the private ticket. Default builds start no GameTest server and
both delivery archives exclude test assets. Human online following, wrong-dimension transfer
and navigation across chunks remain unqualified.

Closed host-known refusal reasons now survive native and session results into localized
feedback. Missing target observation, bounds, interpreter budget, unavailable inference and
rejected completion have distinct recovery guidance, without classifying foreign diagnostics.
Native/session identity, kind and reason must agree before a specific outcome is spoken;
conflicts remain unknown. A nine-case local qualification observed those five refusal causes
with zero Minecraft action POSTs through audited transport assertions. Three subsequent exact
state commands applied through the native typed path without model dispatch; nine reply WAVs
were generated without physical playback.

Opt-in companion replies now retain request-correlated generated WAV and unchanged synthesis
metadata, plus separate evidence for the game outcome, Run identity, artifact retention and
player settlement. Caller cancellation cannot discard the later session-owned result. Stop
joins audio and evidence owners even before a reply watcher starts; repeated cancellation and
native stop failure preserve retirement without leaking that failure through the loop handler.
An actual seven-case native/game/CPU-synthesis check retained five generated replies, including
an applied result after caller cancellation and a no-action result with its real Run. Two
commands stopped before native admission retained absent-Run cancellation evidence and generated
no speech. All reply owners and leases settled. Playback retirement has separate synthetic
process tests; this live check started no playback process and qualifies no human hearing.

Voice input captures its request UUID, stop generation and bound player before asynchronous
capture or transcription. Target changes affect later utterances only; a target absent at capture
cannot appear implicitly afterwards. Private source, transcript and voice records share the admitted
command identity. Portable asynchronous race tests cover changes before task execution, during
capture and during transcription, including no-target refusal and spoken-stop correlation.

Console input now retains its reader-observed identity, stop generation and original deadline,
including partial lines and commands buffered while stop settles. Ordinary input acquired during
that settlement refuses; stop and quit retain priority, and a fresh line after settlement works.
Target changes retain console order. Expired recording triggers cannot arm the microphone after
waiting for audio ownership. Actual-pipe regressions cross the native Graph with a controlled
transport; the original console fails both stale-action and delayed-recording negative controls.
A fresh empty-server headless check and two synthetic CPU Whisper/Supertonic voice cases passed
after this change. These do not qualify a human microphone or physical playback. The maintained
receipt distinguishes this source requalification from unchanged historical cohorts.

The private companion console also offers explicit `--output human` with Slovak, Czech and
English labels. It displays bounded, escaped original recognition before parsing, preserves
localized game feedback, and separates native evidence, generated audio, playback and reply
retention failures. JSON remains the default without added raw recognized words. `:status` reads
owner-held local queue and audio-operation state without game/model calls, Run admission, expiry
or settlement; a zero countdown does not assert a terminal result. Native and controlled-speech
regressions exercise priority stop, original identity, refused transcripts and custody failures,
including cancellation before publication. Two actual CLI-pipe sessions applied synthetic Slovak
idle and English state through CPU Whisper and the native Graph/game bridge, retained both reply
WAVs and closed stopped. These establish no physical microphone, hearing or game-focused trigger.

An opt-in client-only Fabric voice artifact now builds against the pinned 26.3 tuple and passes
twenty-six pure Java cases. It supplies remappable finite-record and independent stop mappings with
held-input/focus guards, original gesture identity/deadlines, bounded separate workers and local
Slovak/Czech/English result labels. A distinct authenticated loopback adapter feeds the existing
console voice/queue owners; it has no game-command, transcript or provider-selection ingress.
Twenty-two real-socket/native fixture cases cover strict HTTP admission, same-ID lookup after
lost acknowledgement, first-byte stop fences, final shutdown, expiry and queued evidence ordering.
Five deliberate counterfactual cases fail when those fences/evidence guards are disabled.
Two empty-server checks used the compiled production Java transport/parser, controlled synthetic
capture, actual CPU Whisper/Supertonic and native Graph/game bridge: Slovak idle and English state
applied, original identities/deadlines and two reply WAVs were retained, and the actor closed
stopped. No game client, physical microphone, playback or GPU was used in those wire checks.
The maintained receipt keeps these boundaries separate from historical proofs.

A separate opt-in official client GameTest then exercised the real production initializer,
registered mappings and untouched ticks in a disposable offline world. It observed five record
requests and four stops through the real client transport: held-input suppression across settled
polls, actual menu/context release barriers, same-binding and menu stop priority, reserved stop
before a blocked ordinary response, own-ID HUD submission and stop after disconnect. The actual
client-stopping event recorded one initialization, all scenarios complete and both worker owners
retired; the process exited normally and the owned container was removed. Minecraft selected
Vulkan llvmpipe after its OpenGL visual failed, under verified 2 CPU/4 GiB/no-swap limits without
GPU/audio devices or a human account. No native host command or speech request was made; fixture
results remain synthetic. The current multiline HUD replaces the clipped action bar and keeps
the own ID, all five outcome/evidence channels, missing-as-unreported values and failure reasons.
Five display cases cover three mixed-result payloads: applied game with failed reply/evidence in
SK/CS/EN and 400-character literal feedback, uncertain playback/server work, and player exit with
hearing unconfirmed. The complete text fit the default font's 320×240 scaled GUI at 640×480;
settled screenshots were inspected after initial join toasts retired. F1/menu absence requires
GUI extraction progress, recovery requires a fresh complete panel, and the stopping witness is
registered after production initialization. If a complete result cannot fit, the view retains
the own ID in a display-space notice rather than showing a successful subset. Other fonts,
transient overlay occlusion, physical keys/focus and human audio remain unqualified. Test assets
remain excluded from default jars. The maintained receipt separates the earlier clipped client
cohort from this source/build/runtime HUD requalification.

The prepared authenticated local profile was also checked against its active launcher identity,
allowlist, non-operator status and console target. A real foreground console opened with Slovak,
CPU Whisper and strict interpretation, exposed fresh recording authority, rendered query-only
status and refused the previous session identity without changing its owners. One explicit stop
retained the original caller ID, a distinct server-stop ID and an applied result; quit closed
the listener and the actor remained stopped. These are local assembly checks, not an authenticated
human join or physical-key qualification. The shared recorder now selects the host's ALSA
`default` instead of requiring an installed `pulse` PCM; an explicit Pulse selection never retries
another device. One separate one-second invocation returned 16,000 frames in a 32,044-byte
canonical WAV and retired its owned recorder group. The bytes stayed private and were not sent
to a model or played. This qualifies finite default-route acquisition on that host, without
attesting physical-source identity, human speech accuracy, a complete game voice turn or hearing.

A later source-only capture recovery qualification separates failed recordings whose owned
group retired from unknown launch or retirement. Synthetic tests preserve cancellation during
final retirement, classify independently cancelled launch/retirement as unknown, permit only a
fresh gesture after settled failure, and suppress a waiting reply after unknown capture. The
companion keeps text control; the older Horizon voice entry fences its session on unknown
ownership. This later cohort did not repeat the physical recording, launch a game or call speech
models; the maintained receipt preserves the earlier host acquisition as historical evidence.

The shared reply player also uses ALSA `default`, with a strictly validated explicit Pulse
alternative and no device fallback. Synthetic tests cover exact argv/stdin, invalid-device
no-launch, failed selected devices without retry, and independently cancelled retirement as
unknown ownership. One subsequent host invocation used the existing CPU Supertonic profile
to generate a fixed Slovak acknowledgement: 66,084 mono 16-bit frames at 44.1 kHz, about 1.5
seconds. One default-route player received that inspected WAV, exited zero and retired its
owned group. No microphone, transcription, game command, GPU, route or volume change occurred.
The synthesis observation and playback record remain separate. This qualifies one finite
default-output operation; it does not attest physical output identity, human hearing or a
complete microphone-to-game turn. Earlier client and recorder cohorts were not reexecuted.

Applied companion controllers now retain the host's exact outgoing authorization deadline,
clipped by the configured lease, original instruction and session expiry. Slovak/Czech/English
feedback states a short upper bound and directs a fresh `stav`/`state` query; elapsed time does
not assert an observed stop or ending cause. State/chat and uncertain results gain no controller
claim, and an identical request cannot renew its deadline. That cohort kept Pattern topology revision 2,
with implementation `py.3` and checkpoint schema `companion-state-v3`; older result shape parsing
does not migrate an old pinned Run. A later CPU-only real-server check retained a two-second
original limit through the native Run/event log, observed its active ID and then no active ID
after that deadline, and closed with an applied priority stop. An earlier helper assertion
incorrectly required an optional observation in the applied idle receipt; that occurrence was
settled and stopped before the corrected probe used a new ID and a separate state read. Both
records remain distinct. No microphone, speech/model call, GPU use or client rebuild occurred.
The maintained receipt separates this qualification from unchanged historical cohorts.

The companion voice producer now retains the failed host operation and fixed localized
recovery feedback through both foreground output and the existing game-control feedback field.
Local recording/read/retention/transcription/admission refusal keeps the game disposition
unreported; uncertain admission cannot assert that no command was sent, even with blocked audio.
Known native outcomes
survive later local failure. Failed spoken-stop settlement is correlated as unknown stop without
an invented server-stop identity or replay. Unknown audio ownership still disables further audio;
known settled failure permits only a fresh deliberate input. Portable tests exercise real local
control sockets, synthetic speech/game transports, same-ID deduplication, fresh-input recovery,
all three locales, post-enqueue faults and native result precedence. Pure Java parser/HUD tests
accept the unchanged feedback shape with local refusal/uncertainty and unreported game state.
This source qualification made no actual recording, speech-provider, game or GPU request and
launched no game client. It does not qualify physical audio or fresh GUI rendering; an unknown
operation still retires the existing client session, with no automatic HUD reconciliation claim.

The explicit `inspect@1` profile now reads one integer cell through the same FIFO, native Run,
HTTP mailbox and server tick. A distinct closed `blockworld.cell@1` observation retains exact
coordinates, dimension, complete registry block state/properties and boot/actor/generation/time
provenance. Existing pose and action-envelope JSON shapes stay unchanged. Whole-cell bounds,
current actor/distance, original expiry, stop and identity history still apply; no block-entity
contents, inventory or chunk load is requested. Typed unloaded availability stays separate from
observed air, and mismatched/absent evidence becomes unknown without reposting. Bounded SK/CS/EN
feedback reaches the existing console/HUD path; current Graph implementation is `py.4` with
`companion-state-v4`, without migration of an older pinned Run.

Ninety-three new portable native/transport/feedback cases, thirty-one Java cases and the real
controller GameTest qualify this slice. The engine read a log's non-default axis, air and a
changed cell during following; a successful read under a short follow retained its original
expiry. Two isolated counterfactual worlds rejected false air and lease renewal, with owned
cleanup. The real unloaded-chunk branch remains unexecuted; its typed availability has transport
coverage. An empty local server received the exact built artifact and retained the same actor
after restart. Three real native Runs applied a 2.5-second idle and read grass with `snowy=false`
and air; reads preserved the active controller, its original limit ended, and one priority stop
closed the actor stopped. The service's earlier stop returned Java exit 143; process retirement
was reconciled before deployment, without attesting a graceful world save. No model, speech,
microphone, playback or game client was used. Building, material custody and human voice accuracy
remain unfinished; the maintained receipt preserves prior cohorts separately.

The host companion console now retains one fixed-stage monotonic timing envelope per accepted
voice occurrence, including pre-entry cancellation and disabled speech replies. The localized
foreground keeps local return/error/cancellation and unavailable native outcome distinct;
timing failure cannot change game results or audio custody. Thirty-two deterministic cases
cover waits, stop, failures and clock/custody faults. One actual synthetic Slovak `Čakaj` WAV
crossed CPU Whisper, the native Run and game bridge, then generated a Supertonic reply: local
elapsed time was 5,053 ms, with 2,511 ms transcription, 99 ms queue/native-result wait and
2,392 ms synthesis. The stages overlap and are not an additive decomposition or benchmark.
Input speech generation/resampling preceded the measured origin; recording and playback were
not attempted. The actor closed stopped. This qualifies host observations for the next human
test, without claiming physical microphone accuracy, hearing or native Echo timing.

The later resident CPU multilingual check retained twelve interleaved generated-WAV cases.
Four ordinary commands applied: English state, Slovak idle, English say and a Slovak/English
mixed say. Spoken stop applied; a negative Slovak instruction refused. Six other inputs refused,
including Slovak state, all three Czech examples, English idle and Slovak say. The six matched
expected kinds include stop and the expected refusal and are not a language-accuracy score.
Each original transcript and local timing remains separate from the native disposition; only
applied ordinary inputs generated spoken replies. The harness barred unexpected movement or
inspection, without correcting wording. Source speech used Supertonic M1 and explicit language;
Whisper small transcribed the prepared 16 kHz derivative. These coupled synthetic cases cannot
attribute a failure to TTS or STT. The actor closed stopped, with no physical recording/playback,
client, GPU, interpreter, hosted voice request, model install or provider change. Text control
remains the fallback while human recordings and listening are unqualified.

The host console also supports explicit `:language INPUT [REPLY]` selection among SK/CS/EN
without replacing a session. An omitted reply locale preserves the current setting, including
disabled replies; both profile declarations validate before either setting changes. Querying
has no game or speech request. Busy voice/native/reply ownership refuses changes instead of
queuing them, preserving earlier instruction identity, expiry and locales. Reader stop/age
fences, playback preference and an unknown-audio latch remain intact. Thirty-two portable cases
exercise these boundaries, ordered console input and separate Whisper/synthesis profile bindings.
This slice made no actual speech, game, device, GPU or interpreter request, changed no profile
file and does not improve or qualify the preceding synthetic language-quality results.

The separate opt-in `weather@1` profile adds clear/rain with one fixed 600-engine-tick timer
programme over shared `server_weather`, anchored at the overworld. Host policy and a distinct
`blockworld:weather` scope are checked before handoff; independent server permission defaults
off. Disabled weather advancement refuses without changing gamerules. A separate effect owner
uses the typed engine API beside the NPC controller. Only a matching `blockworld.weather@1`
readback confirms application; pose/cell substitutions, stale evidence and lost acknowledgement
remain unknown without replay. That weather cohort used Pattern revision `3`, implementation `py.5`, checkpoint
`companion-state-v5`; earlier closures were not migrated. Review found ambiguous weather wording
could enter optional interpretation; the repaired host path refuses it for text and transcripts.

Seventy-seven new portable cases and thirty-five Java unit cases cover the bounded change.
Two independently selected disposable GameTest profiles passed: actual engine timer progression,
natural transitions and restoration, and direct production-composite weather during real short
following with the original lease and queue controls preserved. The weather-only fixture's NPC
is explicitly fake; the real-controller continuity probe is direct dispatch, separate from HTTP.
The reviewed production JAR matched twenty-nine compiled classes and excluded test assets.
The owned empty lab received that artifact and retained its persistent actor after restart.
Three text native Runs applied idle, clear and rain, preserving the original 2.5-second controller
limit before a confirmed stop. Weather timer expiry does not promise restoration, wall-clock
duration or exclusion of subsequent natural thunder; priority stop does not undo applied weather.

Five coupled synthetic CPU voice cases retained all outcomes: English rain and Czech clear
applied and generated replies; three Slovak cases refused before native admission. Their source
speech used Supertonic M1, linear 16 kHz preparation and Whisper small. These observations neither
isolate one model's quality nor qualify human Slovak accuracy. Physical recording/playback,
human hearing, day/night, wake words, building and hosted speech remain outside this increment.
No GPU, interpreter, paid voice request or speech-provider/model change occurred. The maintained
weather receipt keeps this evidence separate from earlier cohorts.

The separate `time@1` profile advances the supported `minecraft:overworld` clock to the next
or equal day/night marker, with execution-time toggle selection and independent default-deny
host/server permission and native `blockworld:time` scope. It checks the current bound clock,
timeline, markers and dimension use before mutation. The exact typed readback binds requested
and resolved modes, forward delta, phases, cycles, fractional state and preserved rate/pause/
advancement settings. Equal markers skip the setter; overflow refuses. The Pattern is now `4`,
implementation `py.6`, checkpoint `companion-state-v6`, without older-closure migration.
Forward placement can advance calendar/moon counts and linked schedules outside the overworld;
it does not certify all datapack tracks, visible brightness or subsequent cycling. Stop cannot
undo an applied placement. Root review corrected post-mutation readback mismatch to terminal
`unknown`, with mailbox retention and no duplicate effect; it cannot claim pre-effect refusal.

The new portable host/CLI cases and forty-three Java unit cases passed. The standalone clock
GameTest checked 252 immediate placements across boundary phases and all selected rate/pause/
advancement combinations, with exact fractional/settings restoration and other-clock, simulation
and weather preservation. Constructed incompatible timelines/dimensions exercise the read-only
profile matcher; this does not replace runtime registries with a hostile datapack. The independent
real-controller fixture applied clock and weather through the production composite during the
original short follow and retained its original expiry oracle. Clock, controller and weather
profiles each passed both required tests; the default build started no GameTest server.
The reviewed production JAR matched thirty-four compiled classes and excluded fixture assets.

The owned empty lab received that artifact with separate clock permission enabled, retaining
its persistent actor after restart. Four native text Runs applied idle, day, night and toggle,
retaining the original 2.5-second NPC limit before confirmed stop. This live passage is separate
from the disposable engine fixtures and does not qualify human play.

Five generated-WAV CPU speech examples retained three applied commands with generated replies:
Slovak and Czech `Nastav noc`, and English `Make it day`. Slovak `Prepni deň noc` and `Nastav deň`
were misrecognized and refused before native admission, with unchanged original transcripts and
no invented Run. Successful host elapsed times were 4806–5849 ms, including transcription,
native waiting and reply generation, excluding source generation, microphone capture and playback.
These are individual coupled Supertonic/Whisper examples, not human accuracy or latency benchmarks.
The harness accepted only the expected clock mode without repairing words; all sessions closed
stopped. FIFINE appeared as the host's default source by read-only inventory, without recording
or routing changes. Human recognition, hearing, physical F8/F9, wake words, continuous listening,
player bodies and building remain unqualified or unfinished. No GPU, interpreter, hosted voice,
model install or speech-provider change occurred. The maintained clock cohort preserves earlier
weather and other evidence unchanged.

A separate publication-packaging check rebuilt both mods with the repository MPL terms and an
unofficial-integration/source-acquisition notice. Forty-three server and twenty-eight voice-client
Java cases passed; all thirty-four server and twenty client production classes matched the prior
qualified artifacts byte for byte. Both delivery JARs excluded fixture and foreign classes.
Gradle caches, game binaries and private profiles are excluded from the source candidate.
Public metadata and operation pages identify the project publisher/contact and its unofficial
relationship to Minecraft. This is an engineering publication check, not legal approval or new
gameplay/speech qualification. Distributing a compiled mod still requires identifying and providing
its exact corresponding source; a development version or mutable source URL alone is insufficient.

The explicit held-input increment adds a third unbound client mapping and host `--hold-seconds`
opt-in. It retains the fixed recording profile and original voice identity/deadline; release has
its own bounded forwarding window and worker. Release-before-start tombstones prevent delayed
capture, while stop remains independently reserved. Unreleased duration/sample limits, short or
invalid PCM, cancellation and unproved retirement discard the utterance before transcription.
Fifty-four held host cases and forty Java cases passed, with 344 affected host cases in total.
Independent review found and corrected unrelated-key collision and late-start-error HUD regressions.

The actual software client retained its original five-record/four-stop chain, then exercised two
synthetic Num Enter holds, one original-ID release and one menu cancellation without release or
replay. Final lifecycle evidence retained five fixed records, five total stops and retired workers
on Vulkan llvmpipe, without GPU or audio devices. Actual `arecord` 1.2.16 on ALSA `null` also passed
the production held helper with partial PCM, intentional SIGINT/status 1 and retired process group.
Separately, a real owned synthetic PCM feeder crossed local held-control HTTP, CPU Whisper,
native Run/Graph and the empty lab's night-clock action exactly once, then generated a Supertonic
reply and closed stopped. Physical keys/focus, FIFINE capture, playback, hearing and human Slovak
accuracy remain unqualified; wake words and continuous capture remain unfinished. The maintained
held-input cohort preserves the historical evidence rather than treating it as reexecuted. The combined dependency lock differs from this receipt; its freshness oracle refuses current qualification until a new live occurrence is recorded.

The dated CPU-only headless qualification records observed head turning and movement,
priority stop with queued cancellation, native event correlation, strict HTTP admission,
same-boot deduplication, a deliberately lost acknowledgement without repost, and a same-world
restart with stable actor identity and stale-boot refusal. Synthetic English and one Czech WAV
crossed speech, the native Graph and the game bridge; local reply WAV generation succeeded.
The original Parakeet profile misrecognized the tested Slovak command words and refused them.
An explicitly selected CPU whisper.cpp alternative applied a synthetic Slovak idle instruction
and English state request through the native Graph and game bridge, with generated Supertonic
replies. Its Slovak and Czech synthetic say examples still refused. Independent operation pins
and preservation of the original transcript framing were checked. These cases measure execution,
not human language accuracy. Source fingerprints bind the bounded critical
slice; the receipt does not attest an atomic transitive source closure or a clean checkout.
Private qualification records are referenced by random opaque IDs; their paths and raw content
digests remain local. Public source fingerprints identify the published code, not anonymized
operator material.

Fixed Slovak/Czech/English feedback distinguishes task start, refusal, client report and unknown
effect. Optional synthesis or settled player failure preserves the game outcome and marks the
reply stage separately. Unchanged idle ticks retain private evidence without repeated console
announcements. An explicit playback option validates PCM before a fixed local player invocation,
keeps capture closed, joins the owned process group on stop and records player exit rather than
human hearing. Failed player retirement ends the session. Synthetic tests cover launch expiry,
late process adoption, repeated cancellation, failed retirement and preservation of native game
outcomes; they do not qualify a physical speaker or microphone.

The same explicit local assembly can register finite idle and follow tick scores. A process-local
supervisor coalesces tick bursts, preserves operator priority and the shared action budget, and
settles interrupted effects before replacement. Idle observes without a command or model call;
follow uses a separately pinned query-only own-client pose feed, finite segments, freshness and
deadline guards, and an independent timeout cancellation path. After a client-reported follow
completion, a fresh healthy, idle, in-bounds bot observation must show at least 0.05 blocks of
progress from the final pre-command pose toward the original target sample before reporting
`moved`. Insufficient progress reports `no_progress`; unavailable, stale or unsafe post-observation
reports `movement_unverified`. Both stop the finite task without automatic retry and retain the
known client response separately. Portable tests exercise native checkpoints, admission races,
measured progress, post-observation failure, evidence publication, safe refusal, target loss and
unknown terminal effects. Remote world labels remain cosmetic observations, including an
explicitly pinned empty label; these ports establish neither authenticated server identity nor a
server world epoch.

The explicit voice assembly opts the concrete target observer into finite read settlement.
Cancellation joins the already started bounded observation and discards its late sample before
propagating the original cancellation. This preserves the same valid target feed for fresh task
admission without extending action authority or weakening freshness checks. Direct/default
cancelled reads, real observation failure and explicit closure retain permanent retirement.
Socket tests interrupt or expire native Runs during both state and status, require no late
action, and admit fresh follow on the same observer; failure cases retain timeout, changed
identity, disconnect and close fences. Read cleanup can outlast the behavior deadline within the
independent observation timeout and bounded connection closure.

An explicitly supplied build service additionally registers a finite one-cell/three-cell plank
score. Frozen plan bytes pin session, plot, mode, labels, inventory expectations, expiry and
budgets. Each cell uses a fresh native Run and one closed placement attempt, with before/after
client observations and expected consumption. The shared supervisor waits for native `DONE`
and the exact Run's result before admitting the next cell. Portable tests connect the Graph,
control socket and synthetic game, including query counts, final-budget confirmation, operator
priority, cancellation after report, unknown partial effects and no replay. An optional private
voice plan is admitted only by its exact phrase; speech does not invent a blueprint. The stock
client has no atomic expected-before placement primitive, so observed preconditions do not
exclude concurrent changes and these results remain client observations, not placement receipts.

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

Reach now has an effect-free preparation foundation: strict provider-neutral account, subject,
group and conversation policy, ordered request rules, content-free refusals and an explicit
`reach.prepare@1` native Graph. Its Discord interface compiles non-secret TOML and normalizes
selected guild mentions and commands before Intent creation. An offline helper validates policy
and previews an installation URL. Portable fixtures pass through real Run admission, worker and
Graph with empty guest scopes for both Discord-shaped and Telegram-shaped observations; the latter
proves shared preparation, not a Telegram adapter. The preparation profile is absent from normal
application assembly and does not implement the published public Discord conversation contract.

The separate Discord operator development profile adds an explicitly started SDK edge and an
OCI-only native documents worker. Shared eligibility precedes real memory Run admission,
serial Graph execution and exact settled-turn lookup. Bounded public Git-blob exports produce
deterministic cited search excerpts, with optional bounded context excerpts and no model call.
The host harness pins separate images, relays bounded private standard streams, and retires both
peers after failure or EOF; neither child receives an engine socket, checkout or the other's
credentials. A local server setup tool derives expiring snapshot-bound plans for roles,
categories, channels and explicit-id patches. Single-attempt REST and content-free fsynced effect
records fence uncertainty across restarts. Source tests cover policy, protocol, native execution,
SDK registration, plan ordering, concurrent custody, expiry, reconciliation and no blind retry.

An explicit private conversation profile now selects one static persona and exact local
`Qwen3.8-27B` binding while document search remains the default. An OCI-only native
`reach.operator_converse@1` Run/Graph obtains an exact Dispatcher Chat lease without tools.
A closed host relay performs fresh health/model observations and bounded generation against one
fixed loopback endpoint; it supplies no runtime lifecycle control. Same-channel history is
separately bounded and opt-in, including this bot's own prior replies in conversation mode.
The static profile is not Mirror identity or persistent memory. Independently selected local
publications carry already authorized producer text through a private queue to exact guild
channels. Only the edge receives that queue; model/chat output grants no publication authority.
Mock-HTTP and portable tests cover model/frame separation, current exact identity, cancellation,
queue custody, expiry and single-attempt publication. They do not qualify a live model or Discord.

**Boundary — Not yet:** Creation's one application selector supplies no general Composition or
Product catalogue, shared store, Suite execution or application scheduler. Other Portfolio members
have no domain/effect path enabled in normal application assembly. Blockworld's
managed mission has no server or bot deployment, authoritative game adapter, production route or
review producer registration. Horizon assist has no live-qualified multiplayer following or
shared-world building, speech playback, free-form model planner, broker delivery or restart continuation.
Its finite idle/follow/build supervisor is an opt-in local profile, not application scheduling or a
deployed companion. Its portable behavior evidence does not establish live two-client gameplay.
The Fabric companion lab has no qualified human microphone, physical playback, Prism join or
live player-follow session. Its fixed home chunk ticket does not establish ticking throughout
the whole control box. It supplies no inventory, mining, building, arbitrary console execution,
durable command recovery, normal-boot registration or qualified Windows operation.
Its controller lock and generation records are local fail-closed protection, not Phylactery
mission recovery or authenticated server proof. Its portable
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
The public Reach contract still supplies no default SDK connection, Ward enrollment, durable
application turn/outbox, recovery or deployable home/VPS profile. The explicit operator profile
has no persistent native history, automatic restart, installed service,
qualified live Discord session or actual server-setup receipt. A new worker generation refuses
older events and loses its memory Runs; its transport journal is not Phylactery. Its reviewed
local admin commands are separate from Discord chat and do not add native authority. Concurrent
Discord changes can race non-atomic remote effects; observed mismatches stop further writes.
The optional conversation path has no live-qualified Qwen/Discord dialogue, tools, Mirror
lineage, general-purpose provider routing or runtime activation. Its local publication queue
has no Ward producer enrollment, automatic coding-work integration, durable native outbox or
application release judgment. Uncertain publications require inspection rather than a new ID
or automatic resend. Learning, teaching, introspection and Comfy execution are not part of this
operator profile.
Public history/media and production deployment acceptance remain separate contract work.
[Reach connected work](./compositions/reach/connected-work/index.md) proposes a successor to the
public Discord contract for Gmail, Discord and GitHub correspondence, plus optional WhatsApp business
messaging and a separate owner–agent probe. Its account lifecycle, provider profiles, delivery policy
and recovery plan supply no implemented OAuth/installation flow, credential service, registered
operational correspondence Pattern, live provider transport, or deployed private-mail capability.
The separate explicit `reach.connect.prepare@1` profile now supplies immutable Email, Chat, Forge
and Social requests, exact connection/partition/target policy, provider-specific application payload
builders and finite WUPHF batch preparation through an inactive native serial Graph. Gmail and
Fastmail have distinct MIME/REST and JMAP preparation; Discord, Telegram bot, WhatsApp business,
GitHub timeline and Facebook Page/LinkedIn/X organic text plans preserve their provider semantics.
Radicle, unsupported history reads, attachments, social replies and paid campaigns refuse or remain
design work. Preparation performs no network, authentication, provider draft save, send or model
call, and its policy is not current effect authority. This does not implement the successor's
durable records/outbox, service attempts, required review, provider qualification or live deployment.
[Thorn](./compositions/thorn/index.md) remains a candidate whitehat security workbench for scoped
assessment, incident response, cooperative investigation, and reviewed reports/corrections.
General monitoring and system maintenance remain outside its case ownership. It supplies no
implemented case records, monitoring integration, response automation, peer investigation network,
actor attribution, or reporting adapter; deterrence remains unmeasured.

The Android screen supplies no device capture/playback, transport, persistence, credential
enrollment, or authoritative Companion records and receipts. Emulator evidence does not qualify
physical devices or every Android version allowed by the declared minimum SDK.

**Evidence**

- **Source:** [Connected request values and policy](https://github.com/hexanomicon/lychd/tree/main/src/lychd/compositions/reach/connected), [provider request builders](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/reach/connected/providers.py), and [offline connected helper](https://github.com/hexanomicon/lychd/blob/main/scripts/reach_connect_prepare.py)
- **Verification:** [Connected policy cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach_connected_policy.py), [provider wire fixtures](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach_connected_providers.py), [native connected Graph and WUPHF cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach_connected_workflow.py), and [connected CLI previews](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_reach_connect_prepare.py)
- **Topic:** [Connected preparation and journeys](./compositions/reach/connected-work/preparation.md) and [account, social and advertising assessment](./compositions/reach/connected-work/social.md)
- **Source:** [Shared Reach preparation](https://github.com/hexanomicon/lychd/tree/main/src/lychd/compositions/reach), [Discord interface](https://github.com/hexanomicon/lychd/tree/main/src/lychd/interface/discord), and [offline helper](https://github.com/hexanomicon/lychd/blob/main/scripts/reach_prepare.py)
- **Verification:** [Policy and native Graph cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach.py), [Discord wire cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_events.py), [configuration compilation](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_policy.py), and [offline CLI cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_reach_prepare.py)
- **Topic:** [Reachy preparation](./compositions/reach/preparation.md) and [provider-neutral boundary](./compositions/reach/architecture.md)
- **Source:** [Native documents score](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/reach/documents_workflow.py), [OCI worker](https://github.com/hexanomicon/lychd/blob/main/scripts/reach_worker.py), [Discord edge](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/discord/live.py), [local administration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/discord/admin.py), [REST effect journal](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/discord/rest.py), and [operator supervisor](https://github.com/hexanomicon/lychd/blob/main/scripts/reach_operator.py)
- **Verification:** [Native search cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach_documents.py), [worker protocol](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_reach_worker.py), [supervisor custody](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_reach_operator.py), [SDK edge cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_live.py), [administration plans](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_admin.py), and [single-attempt effects](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_rest.py)
- **Source:** [Native conversation score](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/reach/conversation_workflow.py), [frozen model contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/reach/operator_model_wire.py), [host model relay](https://github.com/hexanomicon/lychd/blob/main/scripts/reach_model_broker.py), and [local publication queue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/discord/publications.py)
- **Verification:** [Conversation Run and lease cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach_conversation.py), [model contract cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach_operator_model.py), [host HTTP and frame custody](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_reach_operator_model.py), and [publication custody and effects](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_publications.py)
- **Source:** [Optional Discord onboarding](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/discord/onboarding.py) keeps private drafts separate from explicitly confirmed public introductions and harmless baseline-role assignment. It does not provide Ward enrollment or native Graph execution.
- **Verification:** [Onboarding audience and actor binding](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_onboarding.py), [startup and member-event admission](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_onboarding_live.py), [role and introduction effect recovery](https://github.com/hexanomicon/lychd/blob/main/tests/unit/interface/test_discord_onboarding_rest.py), and [edge-only private profile custody](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_reach_operator_onboarding.py).
- **Topic:** [Discord operator profile](./compositions/reach/operator.md)
- **Source:** [Companion native score](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/companion.py), [operator session](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/companion_session.py), [HTTP effect adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/companion_bridge.py), [voice/text entry](https://github.com/hexanomicon/lychd/blob/main/scripts/companion_lab.py), and [Fabric delivery client](https://github.com/hexanomicon/lychd/tree/main/clients/minecraft)
- **Source:** [Reviewed dialogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/companion_dialogue.py), [private recipe store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/companion_memory.py), and [inactive Dump & Search score](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/companion_search.py)
- **Verification:** [Dialogue/recipe cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/blockworld/test_companion_dialogue.py), [console admission](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_companion_dialogue.py), [source-only PostgreSQL adapter and migration parity](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_companion_memory.py), and [injected catalogue workflow](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/blockworld/test_companion_search.py). These use offline substitutes. Live recipe persistence/migration and voice turns remain unqualified; the search score supplies no live game catalogue, foreign subagent, structure placement or summon adapter.
- **Verification:** [Companion native and transport cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_companion.py), [console/audio regressions](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_companion_lab.py), [dated CPU receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/blockworld/companion-cpu-runtime.json), and [historical integrity and freshness refusal](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/blockworld/test_companion_receipt.py)
- **Verification:** [Human console journey and failure cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_companion_human.py), [literal multilingual view](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_companion_view.py), and [query-only native status](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_companion_status.py)
- **Source:** [Local gesture control](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/companion_control.py) and [separate Fabric voice client](https://github.com/hexanomicon/lychd/tree/main/clients/minecraft-voice)
- **Verification:** [Real-socket/native control cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_companion_control.py), [control identity/quota/projection cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_companion_control.py), [pure Java input/transport cases](https://github.com/hexanomicon/lychd/tree/main/clients/minecraft-voice/src/test/java/org/lychd/voice), and [actual client GameTest](https://github.com/hexanomicon/lychd/blob/main/clients/minecraft-voice/src/gametest/java/org/lychd/voice/ClientControlGameTest.java)
- **Verification:** [Real controller GameTest](https://github.com/hexanomicon/lychd/blob/main/clients/minecraft/src/gametest/java/org/lychd/companion/gametest/ControllerGameTest.java) and [opt-in build and evidence limits](https://github.com/hexanomicon/lychd/blob/main/clients/minecraft/README.md)
- **Topic:** [Companion lab](./compositions/blockworld/companion-lab.md)
- **Source:** [Captured instruction and local profile](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/companion_intent.py) and [closed model response boundary](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/companion_intent.py)
- **Verification:** [Intent contract regressions](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/blockworld/test_companion_intent.py) and [response identity, completion and reasoning exclusion](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_companion_intent.py)
- **Source:** [Bounded companion feedback](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/companion_feedback.py)
- **Verification:** [Localized observed-state and uncertainty tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/blockworld/test_companion_feedback.py)
- **Verification:** [One-cell native, provenance and availability cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_companion_cell.py)
- **Source:** [Horizon assist score](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/horizon_assist.py), [explicit native Run assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/horizon_assist_runtime.py), and [bounded client adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/horizon_control.py)
- **Verification:** [Connected Run/Graph and client-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_horizon_assist.py) and [voice-to-Graph session tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_blockworld_voice.py)
- **Source:** [Outcome feedback](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/horizon_feedback.py)
- **Verification:** [Feedback and optional-reply failure cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_blockworld_feedback.py) and [voice/player integration cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_blockworld_playback.py)
- **Source:** [Finite behavior scores](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/horizon_behaviors.py), [local supervisor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/horizon_supervisor.py), and [query-only target feed](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/horizon_observer.py)
- **Verification:** [Native behavior and checkpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_horizon_behaviors.py), [supervisor race and containment tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_horizon_supervisor.py), and [exact-person query-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_horizon_observer.py)
- **Source:** [Finite client-observed build score](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/horizon_build.py)
- **Verification:** [Native build/checkpoint cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_horizon_build.py), [closed placement socket boundary](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_horizon_placement_control.py), and [connected build/supervisor/voice cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_horizon_build_supervisor.py)
- **Topic:** [Horizon assist](./compositions/blockworld/horizon-assist.md)
- **Source:** [Blockworld workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/blockworld/workflow.py), [placement custody](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/blockworld.py), [placement migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0011_blockworld_placement.py), [Workflow registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py), [client interaction model](https://github.com/hexanomicon/lychd/blob/main/clients/android/interaction/src/main/kotlin/org/lychd/companion/interaction/Interaction.kt), [Android screen](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/main/kotlin/org/lychd/companion/CompanionScreen.kt), and [Activity state](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/main/kotlin/org/lychd/companion/OfflineDraftViewModel.kt)
- **Verification:** [Portable placement workflow tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_blockworld_placement_vertical.py), [PostgreSQL placement tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_blockworld_pg.py), [PostgreSQL worker and review vertical](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_blockworld_postgres_vertical.py), [Workflow routing tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_router.py), [client interaction tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/interaction/src/test/kotlin/org/lychd/companion/interaction/InteractionTest.kt), [ViewModel tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/test/kotlin/org/lychd/companion/OfflineDraftViewModelTest.kt), [Activity tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/androidTest/kotlin/org/lychd/companion/CompanionScreenTest.kt), [production-lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/clients/android/offline/src/androidTest/kotlin/org/lychd/companion/CompanionLifecycleTest.kt), and [client check commands](https://github.com/hexanomicon/lychd/blob/main/clients/android/README.md)
- **Source:** [Scavenger finite values](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/scavenger/schemas.py)
- **Verification:** [Scavenger value and projection tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_scavenger_values.py)
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
absence. A historical consent record carries only a bounded syntactic Consent reference and an
exact Bridge destination. Bridge checks the requested id and Run against its authorized session
snapshot, reports unavailable requests without replacement, and focuses once per navigation.
The return link preserves the originating Orb Run and event; drafts and uncertain verdicts remain
in the existing shell workspace. This adds no current Consent status or review disclosure to Orb.
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

An optional, current-authority-checked Creation summary follows the selected Run's exact retained
admission link. A dedicated metadata query preserves custody even when a deadline has elapsed
and the slot remains encumbered. The client separates Run status, case status, constructor/verifier
adoption, native verdict, latest external assessment and current owner disposition. Historical
admissions explicitly display case-current outcome; absence discloses no case existence. Active
SSE polls refresh or clear this metadata without changing the evidence cursor. Later feedback
after terminal settlement requires explicit Refresh. No source, prompt, response, candidate,
report or free-text reason body enters the summary.

An optional two-route preference inspector shows the selected Run's immutable admission decision:
literal keys, unitless weights, dated phases, admission openness, exclusions and selected key,
with the policy digest and observation window. REST and settled SSE project the same allowlisted
metadata from the retained Run without refreshing readiness or applying current configuration.
The client identifies these as admission-time observations and marks fallback as unavailable;
legacy Runs omit the inspector. A keyboard-focusable table region contains overflow at narrow widths.

**Boundary — Not yet:** Loaded graph counts are not complete-history counts. The current manifest
supplies no nested subworkflow or parent-Run identity. There is no durable Oculus read model,
Sigma/Graphology adapter, cross-process completeness, health query, artifact custody, or annotation.
There is no wall-clock workspace replay, configurable retention, continuous model-call activity,
or historical Animator availability projection.
The shared renderer's cross-engine forced-collection qualification remains under verification.

The [trusted source-browser profile](#current-evidence-envelope) separately verifies the fixed
Bridge→Orb→exact Loom→Bridge route and retained failed/useful Runs across a normal reload.
It supplies no complete event capture, continuous runtime activity or general renderer receipt.

**Evidence**

- **Source:** [Orb controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/orb.py), [Run catalogue queries](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/ledger.py), [parallel field](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbField.svelte), and [selected-Run client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbView.svelte)
- **Verification:** [Orb API and stream tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb.py), [catalogue privacy and pagination tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb_catalogue.py), [parallel-field tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbField.test.ts), [folded coverage tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/graph/orb.test.ts), [selected-Run tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbView.test.ts), and [feed recovery tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/orb/live.test.ts)
- **Source:** [Retained preference projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/orb.py) and [preference inspector](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgePreferenceSummary.svelte)
- **Verification:** [Preference API and settled stream](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb_preference.py), [preference inspector controls](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgePreferenceSummary.test.ts), and [typed stream metadata](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/orb/live.test.ts)
- **Law:** [Observability](./adr/29-observability.md), [Altar projection](./adr/15-frontend.md#snapshots-streams-and-recovery), and [Creation summary](./compositions/creation/index.md#selected-run-summary)

### Structured logging configuration {#structured-logging}

**State:** Available

**Proved now:** One tested builder configures human and JSON stdlib/Structlog output for CLI and
Litestar while preserving stdout/stderr semantics, recovery-command fallback, and thread-stable
repeated bootstrap without an unused logging queue. Worker-thread stdlib exception records and
direct Structlog exceptions retain usable diagnostics as valid JSON on stderr; human console
exceptions remain readable.

**Boundary:** Shared configuration does not prove complete semantic audit coverage, trace storage,
OpenTelemetry export, redaction, retention, resource correlation, or Oculus.

**Evidence**

- **Source:** [Logging configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/logging.py)
- **Verification:** [Logging tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_logging.py) and [exception regression tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_logging_exceptions.py)
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

The opt-in `closed-diagnostic-recording@1` profile adds durable admission for those exact candidate
bytes under an independently pinned synthetic export binding. Acknowledged fresh claims consume
one use and the full candidate size against permanent host, purpose and Cut capacity, without
refund after refusal or uncertainty. Only the issuing process can activate a claim once and settle
its original completion. PostgreSQL custody retains restricted evidence rather than source or
candidate bodies. Concurrent claims, lost commit acknowledgement, service reconstruction, retained
Run/delivery checks, locked downgrade refusal and migrated-versus-ORM catalog parity have actual
disposable-PostgreSQL coverage, including a missing-CHECK negative control.

**Boundary — Not yet:** No governed SQL/tool/artifact adapters, end-to-end source lineage, semantic
Privacy Agent, general PII detector, reversible map/Vault, provider-specific sanitized wire branch,
general Context Egress Gate or Context/provider network transmission accounting, content-derived cumulative-disclosure
policy or deletion propagation ships. The local recorder is an accounting witness; it supplies no
peer identity, A2A transport, native peer wait or normal-boot egress integration.
An in-memory Cut neither survives restart nor grants disclosure. Normal private Context and
effectful delegated execution remain ineligible for remote use.
The separate [public-text peer profile](#a2a-intercom) admits explicitly authored public input;
it does not extend the recorder or make a private Context eligible.

**Evidence**

- **Source:** [Privacy preparation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/privacy/preparation.py), [independent verifier](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/privacy/verification.py), and [Context integration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/context.py)
- **Source:** [Recording owner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/privacy_disclosure.py), [durable disclosure store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/privacy.py), and [custody models](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/privacy.py)
- **Verification:** [Adversarial preparation fixtures](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/privacy/test_preparation.py), [Context influence tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_context_privacy.py), and [offline probe output](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/privacy/test_probe.py)
- **Verification:** [Recording authority tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/privacy/test_disclosure.py), [retained evidence tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_privacy_disclosure.py), [PostgreSQL concurrency and recovery](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_privacy_disclosure_pg.py), and [transactional migration and catalog tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_privacy_disclosure_migrations_pg.py)
- **Topic:** [Portal](./sepulcher/animator/portal.md)
- **Law:** [Context](./adr/21-context.md#privatization-and-the-privacy-cut), [Security](./adr/09-security.md#portal-privatization-and-egress), and [disclosure custody](./adr/06-persistence.md#closed-disclosure-accounting-custody)

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

**Proved now:** Generated host publication binds IPv4 loopback. The managed image selects fixed
internal `0.0.0.0:8000`; alternate listener, supervisor, reload and metrics configuration refuses.
Host-native `serve` is retired. Current source guards preserve this fixed container policy. Launch, Host, CORS, local schema assets, fixed root handlers,
and CSRF contracts are bounded and tested. Missing, wrong, malformed, or duplicate HTTP Basic
credentials fail before fixed-Sigil admission on protected HTTP/API/SSE paths; foreign-Origin
mutations fail even with valid credentials and CSRF. `lychd access` explicitly retrieves the
local credential without exposing it in generated commands or ordinary status. The raw SAQ
diagnostic UI configuration is refused while its workers remain available. The HTTP assembly
tests verify this security configuration against memory services without entering runtime lifespan.

**Boundary — Not yet:** Admitted requests still receive the fixed local Sigil. No hostile-browser receipt,
security-header contract, or remote principal exists. The developer fixture's configured loopback
Vite proxy has a bounded development exception. The [trusted source-browser profile](#current-evidence-envelope)
retains dated authenticated journey/security-refusal evidence for the retired native profile;
it does not qualify the current container/Vite fixture, rebuilt image, installed startup, hostile
browser or general browser security.
Production access through a proxy, tunnels, non-loopback access, and untrusted-browser use remain
unsupported.

**Evidence**

- **Source:** [Application composition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py), [server policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/server_policy.py), and [fixed Altar routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py)
- **Verification:** [Network policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py), [CLI and image-policy controls](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py), [HTTP boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_http_boundary.py), [Factory HTTP assembly tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_app_factory.py), and [Altar route tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
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

A separate `scout-rss-extract@1` profile now projects strict UTF-8 RSS 2.0 into immutable
channel/item observations in that same fixed child. It accepts three explicit XML media types;
the old static header and public-page media contract still refuse XML. Expat declarations,
entities, controls (including omitted attributes), element/depth/item/field bounds and the complete
return ceiling have independent behavioral tests. A fresh identified runtime proof joins the
current static confinement proof to 43 actual RSS/probe launches, ordinary and hostile inputs,
parent locator validation, pipe flooding, timeout and cancellation with observed cleanup.
Its maintained receipt fingerprints the worker, parent, domain, destination syntax and both proof
harnesses; ordinary CI checks source freshness and agreement with the maintained static runtime.
That receipt proves the RSS extraction mechanism. The separately selected finite-feed application
below joins it to native admission and receiving custody; recurring watching remains unfinished.

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

A maintained historical composed Linux receipt dated **19 October 2026** joined actual credential
admission, PostgreSQL native consent and a store-issued claim to the real current-authority
DNS/TLS/HTTP path and fixed supervised extraction child. The disposable database had no IP network
or published port; its dedicated pathname socket remained reachable from the isolated acquisition
namespace. The passage checked the exact request, all settled host/binding counters, reference-to-receipt
identity, ordinary answer retention and absence of transient source input from retained state,
history and settlement. Reconstructing the service could not refetch consumed material. Revoking
access during TLS prevented HTTP application bytes, extraction and the deterministic model call,
while retaining a refused settlement. Container, anonymous volume and socket-directory removal
were observed before the receipt passed. Nodes and services were invoked explicitly; queue,
dispatcher, events and model remained controlled adapters. Its sealed source closure differs from
the merged engine and ledger; this dated success does not qualify the combined revision. Fresh
merged-source qualification remains pending, and replacing fingerprints cannot supply it.

A separate opt-in Scavenger3 / `scavenger.observe_market@2` application now fixes one Bazoš PC
RSS locator and a model-free title/link projection. Its selected PostgreSQL/ASGI/native-worker test
parks and resumes the actual Graph through Core consent, then crosses real isolated DNS/TLS and
the fixed RSS child to a committed whole field. Read, literal filtering and identical admission
replay cause no further source request; no Bridge Session or model lease is created. Other
PostgreSQL cases cover exact terminal deletion/tombstones, lost commit acknowledgement, current
access changes, unknown claim custody, private driver failures, delayed exact retention replay
and cancellation withdrawing pending review. Queue publication uses a controlled port; unknown
custody is injected through the real store. This proves a synthetic development combination,
not public Bazoš contact, a SAQ worker process, whole-process restart or installed operation.

An [ordinary native public-feed observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/native-finite-feed-observation-2026-10-18.json) at source `577105de` used the production CLI and its in-process SAQ workers to retain 50 Bazoš PC RSS title/link occurrences and a local `RTX` view, with no model call. Its one acquisition succeeded; host and binding each record three connects, five transmissions and 1,876 outbound payload bytes. These are hierarchical counters for the same passage, not received RSS size. The first pilot failed its pre-restart closure guard on an adopted child whose historical state and exit were not captured. Separate external settlement removed its owned processes and container while retaining the volume.

A later, separately admitted native process authenticated afresh and read the exact whole document from that same volume. Canonical JSON equality and accounting checks before startup, after GET and after process closure show no new acquisition or budget reset. Its owned resources were independently reconciled and the volume remains retained and unattached. Source577 still logged two heartbeat-manager shutdown failures: OS process closure therefore does not qualify clean application shutdown or retroactively pass the first pilot. This dated observation establishes finite acquisition and retained readback; installed Scavenger, recurring watching and autonomous work selection remain unfinished.

A separate [after-fix ordinary native readback](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/native-queue-shutdown-readback-2026-10-18.json) used an exact frozen dirty candidate based on `577105de`, with the application-owned queue plugin and no batched heartbeat manager. It preserved the same 50 occurrences and permanent accounting in approximately 4.45 seconds, without submission, acquisition or inference. Complete ordinary CLI logs contain zero heartbeat crashes, tracebacks or error messages; two SAQ zero-grace cancellation warnings remain recorded. Independent outer settlement passed. This closes the observed heartbeat-thread regression for an idle readback, while active-work shutdown and the original pilot restart remain unqualified.

The separate [native owned-stop/restart case](#core-cli-rites) preserves the same field across
two production boots and signed stops, with full-row accounting equality. It adds idle lifecycle
evidence; it does not add another acquisition, recurring watching or automatic work selection.

The generated Altar application uses current protected reads and the existing native consent
card. It preserves uncertain action identities, freezes identical admission replay bodies, fences
stale selection responses and clears protected state on access refusal. Escaped item locators
remain inert. Component/transport tests and a desktop synthetic-browser inspection cover these
controls and keyboard access to the table; no Android or cross-engine qualification follows.

A [dated authenticated native Altar readback](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/native-altar-readback-2026-10-18.json)
on clean source `3bf598d9` now joins the ordinary CLI, retained PostgreSQL field and compiled
Altar in actual sandboxed Chrome. In approximately 7.76 seconds it verifies all 50 whole rows in
source order, acquired time, coverage, counts, disclosed attribution and inert locators. Actual
protected documents match the retained canonical baseline; four SQL accounting boundaries remain
identical, with no submission, acquisition, filter mutation, inference or reset. Independent
process/resource closure and complete log assessment pass. One error/traceback is the normal
initial Basic-authentication 401 challenge; two SAQ zero-grace cancellation warnings remain.
The explicitly trusted functional UI profile enforces time, stop and PID controls but qualifies
no hard CPU/memory ceiling, hostile-browser safety, installed lifetime or broad clean shutdown.
Earlier failed pilots remain failed.


A separate [native Altar filter session](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/native-altar-filter-2026-10-18.json)
on clean source `3e221f56` exercises the ordinary controls in actual Chrome through an explicitly
API-mediated, no-redirect/no-retry transport. In approximately 8.68 seconds, exactly two protected
CSRF POSTs show the retained field's legitimate zero `RTX` matches with a visible explanation,
then restore all 50 individually visible rows in source order through an empty-query submission.
The complete protected document and four permanent-accounting summaries remain equal; no new
acquisition, inference or reset occurs. Independent outcome review and resource closure pass;
17 captured process records represent 16 distinct identities. Two SAQ shutdown-grace warnings
remain. This bounded functional session qualifies neither Chrome-direct HTTP, a persistent
endpoint, hard browser CPU/memory containment nor clean application shutdown. Earlier failed
attempts remain failed; no new full-row SQL snapshot is claimed.

Separate [pinned SearXNG service fixtures](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/searxng-service-fixture-2026-10-18.json)
now cross actual authenticated local HTTP, the upstream web application, dispatch thread,
asyncio processor, host-sealed fixture TLS and engine parser. The unmodified dispatch baseline
refuses before exchange; a narrow context-propagation prototype returns two exact observations,
while a separate 303 case refuses before parsing or a follow-up request. All three independently
settle their owned resources. These are private one-use fixture experiments, not a shipped
service, live-engine qualification, repeated-use profile or native Search authority.

**Boundary — Not yet:** No SearXNG or Crawl4AI Rune/adapter, general Scout provider store,
effect-scoped Agent tool, download quarantine, website authentication/session custody, or Smith
ingestion path ships. No Search engine has passed qualification. The transport/extraction proof
uses a synthetic audit gate; the additional current-authority network proof uses fixture admission
data. The historical composed receipt records real PostgreSQL and extraction but does not exercise HTTP routing,
a SAQ worker process, durable Graph checkpoint/resume or model inference. The separate page worker test proves durable Graph continuation with substituted effects.
The model-free feed test joins its own selected HTTP/Graph execution to real isolated network and
extraction; no receipt joins page execution to the real inference service. These receipts do not prove a deployed combination
or arbitrary host compatibility. The first workflow accepts only its explicit public-page command, follows no
redirects, and requires a qualified local extractor and exact local model. Budget reset and
unknown-attempt reconciliation have no automatic operational path. Rendering remains separately
unimplemented outside the shared Pod.

**Evidence**

- **Topic:** [Scout](./sepulcher/extensions/scout.md)
- **Verification:** [Pinned SearXNG transport study](./sepulcher/extensions/scout-web-research.md#searxng-transport-cut) and its [dated offline observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/searxng-transport-cut-2026-10-18.json) establish controlled upstream retry and private one-use transport-cut behavior only. The separate [local service-fixture observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/searxng-service-fixture-2026-10-18.json) adds actual one-use authenticated service/parser evidence; no live engine, repeated service use, production egress boundary or native Search is qualified.
- **Source:** [Feed admission and protected API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/api/scavenger.py), [model-free Graph](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/observe_market.py), [application custody](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/scavenger.py), and [Altar application](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/ScavengerView.svelte)
- **Verification:** [Dated ordinary native public feed and retained readback observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/native-finite-feed-observation-2026-10-18.json) records successful finite custody, the failed original restart guard, separate fresh-process GET readback and unchanged permanent accounting; clean application shutdown remains unqualified.
- **Verification:** [After-fix ordinary native retained readback](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/native-queue-shutdown-readback-2026-10-18.json) binds the exact dirty source candidate, full captured log assessment, unchanged retained data/accounting and independent resource settlement. [Queue-plugin regressions](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime_queue_plugin.py) exercise actual installed workers, sole retirement ownership and partial-startup/failed-stop containment with inert transports.
- **Verification:** [Selected PostgreSQL and physical feed proof](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scavenger_feed_pg.py), [protected HTTP and logging tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_scavenger.py), [driver privacy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_scavenger_privacy.py), and [Altar lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/scavenger/observation.test.ts)

- **Law:** [Webcrawler](./adr/30-webcrawler.md)
- **Source:** [Pure destination preflight](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/scout/destination.py), [fixed extraction worker](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/scout_worker.py), and [Linux supervisor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_extraction.py)
- **Verification:** [Destination boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/scout/test_destination.py), [worker tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_scout_worker.py), [supervision and receipt-freshness tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_extraction.py), [live host proof](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_extraction_runtime.py), and [maintained qualification receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-extraction-runtime.json)
- **Source:** [Native acquisition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_fetch.py), [gated transport](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_socket.py), and [Run effect fences](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/cancellation.py)
- **Verification:** [RSS behavioral tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_scout_rss_worker.py), [RSS return validation and freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_rss_extraction.py), [RSS live child proof](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_rss_extraction_runtime.py), and [maintained RSS receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-rss-extraction-runtime.json)
- **Verification:** [Acquisition and freshness tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_fetch.py), [HTTP decoder tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_http.py), [Run fencing tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_cancellation.py), [isolated network proof](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_fetch_runtime.py), and [maintained transport receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-fetch-runtime.json)
- **Source:** [Current authority](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/scout/authority.py), [durable attempts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/scout.py), [owned coordinator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scout_workflow.py), and [public-page casting](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/scout_chat.py)
- **Verification:** [Authority contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/scout/test_authority.py), [PostgreSQL attempts](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_attempts_pg.py), [migration custody](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_migrations_pg.py), [coordinator boundaries](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scout_workflow.py), and [transient workflow projection](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_scout_chat.py)
- **Verification:** [Assembled PostgreSQL workflow](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_workflow_pg.py)
- **Verification:** [Worker and durable Graph continuation](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_graph_workflow_pg.py) and [consent checkpoint ownership](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_scout_consent_owner.py)
- **Verification:** [Composed isolated passage](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_scout_composed_runtime.py), [historical composed receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/linux-composed-runtime.json), and [historical integrity and stale-closure refusal](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/scout/test_composed_receipt.py)
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

An explicitly invoked local engineering probe's version 1 profile pins one literal-loopback audio.cpp batch endpoint,
runtime revision, separate model digests and declared languages. It sends inspected canonical WAV
and retains attributed transcript facts, or requests a stock voice and inspects bounded generated
PCM WAV. Its CLI keeps material in a private external workspace and refuses checkout overlap,
symlinks, overwrite, redirects, ambient proxies and automatic retries. An opt-in Linux helper
captures a finite 1–15 second utterance and retires its owned recorder group; substitute-process
tests do not qualify a physical microphone. Cancellation of HTTP waiting leaves server work
unknown. Profile declarations do not attest loaded model bytes or verify language quality.

Version 2 profiles independently bind the transcription and synthesis endpoint, runtime revision,
dialect, backend, device and model. Existing version 1 schemas and digests remain unchanged.
The whisper.cpp multilingual small dialect requires an explicit declared language and sends no
per-request model selector; Supertonic synthesis can remain on audio.cpp. Both operations retain
their own provenance. The companion entry checks both CPU/host bindings and removes only outer
ASCII speech framing before strict instruction parsing, retaining the original transcript.
Synthetic Slovak idle and English state crossed this alternate path; two misrecognized say
examples refused. No automatic provider fallback or native Echo admission is implied.

A separately selected local player helper accepts validated bounded PCM bytes through fixed
stdin invocation. It owns launch adoption and process-group retirement, keeps capture closed
through uncertain retirement, and reports player exit independently of generation or hearing.
Synthetic tests exercise this process boundary; no live listening receipt is established.

**Boundary — Not yet:** Structural inspection proves neither speech, consent nor provider
compatibility. Custody helpers remain separate from provider use; the engineering probe issues no
Animator grant and supplies no native Bridge audio admission, live device qualification, hosted provider,
streaming socket, resonance buffer, selectable Echo extension or Audio Coven.

**Evidence**

- **Source:** [Capability contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/capabilities.py), [Echo PCM inspection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/echo/material.py), and [trusted custody consumer](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/echo/custody.py)
- **Verification:** [Grant-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py)
  and [dispatch-refusal tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_dispatcher_scenarios.py), plus [real-byte PCM inspection tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_echo_material.py), [Echo custody refusal](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_echo_custody.py), and [retained-byte lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_artifact_custody.py)
- **Source:** [Explicit speech profile](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/speech_probe.py), [bounded batch adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/speech_probe.py), and [finite recorder helper](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/voice_capture.py)
- **Verification:** [Speech dialect and default-transport tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_speech_probe.py), [private CLI boundaries](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_voice_probe.py), and [recorder ownership tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_voice_capture.py)
- **Source:** [Explicit finite player](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/voice_playback.py)
- **Verification:** [Player ownership, expiry and cancellation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_voice_playback.py)
- **Topic:** [Local qualification](./sepulcher/extensions/echo-local-probe.md)
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

Authorized configuration discovery and finite metadata reads now support review after reload or
a lost mutation response. Profile discovery performs no storage, registration, model or Run work.
Lists expose at most 50 metadata records per page across all lifecycles, with an exact source-key
filter and stable timestamp/UUID cursor; exact-record reads recover the current lifecycle/version.
Both select only metadata columns, including revoked tombstones, and never hydrate source text,
search vectors or embeddings. Reads create no persistent namespace, note or receipt rows. A missing
namespace lists empty; changed retained bindings and storage failures refuse distinctly. Current
management authority is checked before storage, after namespace preparation and after session
cleanup. Inspection grants no recall eligibility or automatic lifecycle retry.

A separate authorized exact-Run read returns a bounded text-free Archive receipt only when the
retained supported Bridge3 Pattern, complete admitted/current profile and exact expected recall
request match. Current management authority is distinct from Run visibility and is rechecked after
ledger, namespace and session preparation. The response distinguishes unsupported history, absent
receipt, successful empty selection, budget omissions and failure. PostgreSQL tests execute the
worker with a substituted model, observe terminal Context release and then read the same receipt
through a fresh service and repeated HTTP reads without dispatch. Historical selection survives
source supersession, archival and revocation; inspection reads no source table and creates no rows.
Bridge3 uses live checkpoints; this is no durable-checkpoint deletion or crash-recovery proof.
Orb now exposes that separate read in an explicit **Archive selection** inspector. It performs no
request on mount or structural live updates; current failure clears protected metadata, and an
exact-Run keyed child aborts and fences old responses on navigation. Selected source metadata is
escaped and ordered, long digests use native disclosures, and read time stays separate from receipt
creation. Component/transport tests cover empty, absent, unsupported, refused and malformed results,
explicit retry, stale completion and preservation of Orb graph/history/SSE ownership.
Capture remains `matching_retained_request`: a caller can preseed an exact public recall before
workflow execution. It proves neither consumption nor provider transmission and reconstructs no
complete historical Context.

Bridge now supplies a **Public notes** focus at `/bridge?notes=manage|new|UUID`, using the generated
management transport. It shows configured profile and a separately authorized actual-default/full-
profile match, finite all-lifecycle pages and exact-record recovery. Explicit intake freezes the
UUID/body/submitted UTF-8 digest; promotion is separate. Correction fixes the source key and asks
for complete new text under a different revision; revocation requires exact consequence review.
Unknown intake and lifecycle outcomes remain distinct from observed current metadata. No refresh,
navigation or late response retries a write or takes over a newer focus. Current refusal/profile
change and teardown fence protected data and callbacks. Component/transport/controller tests cover
these paths, full-mode navigation races, escaped source identities and preservation of ordinary
Bridge drafts, unresolved offerings and Consent. These portable tests do not qualify a real-browser
or installed workflow.

A distinct **Recall public sources** focus at `/bridge?notes=recall` now composes the explicit
semantic API into a sources-only query and exact current-source read. It requires a user-supplied
finite threshold, shows numeric bounds and freezes the raw request with a fresh UUID. It displays
escaped ordered source/revision identities, similarity, coverage/omissions and distinct selection
and resolution-response times. Unknown Check uses the same frozen request for metadata only;
recovered selection needs an explicit current-source load. It never automatically retries a query,
activates a model, prepares derivations or admits an answer Run. Profile/generation/current-authority
and lifetime fences clear protected projections and reject late responses. Portable controller,
transport, component and route tests cover these paths and preserve the separate conversation
workspace. This does not qualify ordinary installed runtime preparation, real-browser interaction
or retrieval quality; configuration metadata alone establishes none of those prerequisites.

The exact-note detail also provides separate configured-generation registration, explicit
preparation Check and reviewed preparation of one promoted revision. It uses the existing typed
Archive ports; opening, navigation, promotion and completion never automatically register, derive,
activate a model or submit recall. Latest derivation row/attempt state does not attribute one HTTP
invocation or all compute spent; a lost preparation response remains unknown after Check, and a
further explicit attempt may repeat work. Local write guards, current-authority/profile/selection
and lifetime fences preserve management ownership and reject stale callbacks. These are portable
browser-controller/control tests, separate from the fixed native lifecycle below; ordinary
installed preparation and real-browser acceptance remain open.

A separate [19 October native operator observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/archive/native-public-notes-2026-10-19.json)
at source `c4d86be6` exercised ordinary Settings/Runes, database bootstrap, CLI, Granian TCP,
PostgreSQL and the existing shared Qwen3.8-27B runtime. Four fresh Sessions answered one frozen
synthetic lexical question: the candidate was excluded; promotion supplied revision 1; correction
supplied only revision 2; revocation restored explicit uncertainty. Independent review checked
source attribution, the conditional exception, exact receipt/wire bindings and lifecycle-caused
stale refusals. Four model POSTs used 2,356 prompt and 252 generated tokens. Root independently
settled the temporary service, process groups, listeners, database and anonymous volume while
preserving the warm model and retained data. The receipt retains raw native API responses and
model request bodies, but no raw model response stream or outgoing API headers. This is a dated
single-case observation, not a released live-test harness or general retrieval benchmark.

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

A separately enabled `archive.semantic = true` consumer uses that same configured derivation
generation. Its strict request requires an explicit cosine threshold. The authenticated
`/api/v1/archive/semantic/recalls` endpoint returns a text-free schema2 selection receipt and any
query execution incurred by this caller; exact completed replay performs no query inference.
Sibling POST inspection and receipt-resolution routes distinguish historical selection from
currently eligible source bytes. Source-attributed resolution rechecks the active exact generation
and every selected source/vector fence. Receipts report the final snapshot's promoted and eligible
note counts; partial derivation coverage is explicit. Existing lexical/schema1 and Bridge3 remain
unchanged.

Actual PostgreSQL tests cover filtered exact signed cosine, deterministic ties, coverage, bounded
whole-note selection, concurrent publication, lifecycle/generation races, corruption, transaction
timeouts and the existing restricted runtime role. Authenticated ASGI plus actual PostgreSQL tests
exercise the configured factories, real Core HTTP driver and shared leases with intercepted model
responses. HTTP numeric-coercion negatives use the production schema plugin. These tests do not
qualify real-model Archive composition, general retrieval quality, a browser semantic instrument
or semantic Bridge execution.

The separately boot-selected `bridge_chat@5` composes that semantic generation with one exact local
Soulstone Chat capability. Admission retains the complete manifest/reference, explicit threshold
and finite recall bounds; each node resolves the Archive subject from the persisted caller.
Component controls cover exact admission and checkpoint bindings, changed-service/receipt refusal,
current authority before chat, each outbound model count/request and settlement, and query cleanup
before chat acquisition. The transient `archive_semantic_recall` envelope carries the schema2
receipt, generation, coverage and source attribution. It supplies no instructions or tools, and
this casting excludes prior conversation history. The injected source envelope stays out of retained state and
model history; generated answers may quote source text and persist. Execution uses the existing shared
hardware lease path, without automatic generation registration, preparation or lexical fallback.

The final serialized response is checked before ordinary answer/history assignment. A known
normalized `length` finish refuses with `answer_output_limit`, even if the SDK returns nonempty
text. Component controls prove that the original code accepted this case, then exercise refusal,
normal/unknown completion metadata, final-response ordering, one provider call and lease closure.
Other or absent metadata retains adapter compatibility without certifying completeness. Streamed
text remains provisional evidence; this check adds no automatic retry or larger budget.

A successful current resolution with no selected sources instead returns a labelled deterministic
recall outcome before Chat, Context assembly, counting, forge or pump work. Component graph tests
distinguish no promoted notes, no searchable notes, a threshold miss and character-budget omissions,
with historical coverage and an explicit source-limited abstention. They retain actual query cleanup
and winning-receipt versus caller-work accounting. A real in-memory session store proves unchanged
prior SDK history, clearing of an unsettled SDK suffix, one visible outcome and replay without
another embedding. Authority revoked before or during answer/final resolution still refuses. This
branch also has the fixed native A/B/C observation below; the earlier SQL runs do not qualify its
new outcome. Earlier failed native attempts remain failed.

The separate [maintained native answer observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/archive/native-semantic-answer-runtime-2026-10-19.json)
qualifies one public synthetic `generated-answer-and-empty-recall-v2` occurrence through
authenticated in-process ASGI, actual PostgreSQL, the registered CPU embedding profile and warm
Qwen3.8-27B with `bridge_chat@5`. A returned the fixture's 14:20 opening time with its exact source
key/revision and normalized/provider `stop`. B retained typed `source_integrity` after revocation
with zero Chat or Context assembly. C returned a labelled source-limited deterministic recall
result with no selected/promoted/searchable notes, zero Chat, zero Context assembly and zero new
SDK messages; the normal terminal release was recorded. A and C recorded replay with no new
compute. Four embedding operations/eight POSTs used 118 input tokens; one Chat POST matched the
independent warm-counter delta of 1,029 prompt and 239 generated tokens. All observed clients
closed, no leases remained, and application SQL disposal returned once after service close.
An independent retained visible-output review passed these fixed cases and recorded operation
evidence; Root's separate 20 October terminal audit passed 23 physical checks and recorded 20 raw custody
pairs. These are attributed retained observations. Raw SDK text equality, retained input/state
exclusion, history equality, replay identity and revocation timing remain test-backed reports,
not independently reconstructed from the sanitized receipt. Its raw `semantic-answer-v1` outer
envelope permits two Chat calls; active v2 admission permitted one and observed one. The observed
source head and fixed Chat-profile fixture revision are recorded separately.

Actual PostgreSQL source-answer controls passed five cases in each of two bounded runs, with zero
failures, errors or skips and independently confirmed physical settlement. A fresh fixture drives
HTTP admission, retained idempotent binding and the actual worker through ordinary answer settlement.
Four separate cases explicitly persist and reconstruct the typed PostgreSQL snapshot: unchanged
state proceeds; revoked source, retired generation and changed composed service refuse before a
Chat grant, outbound request or settled agent turn. Ordinary revision 5 uses Live Stasis; these
manual reconstruction controls do not establish automatic worker-death recovery. Component
embedding substitutes, FunctionModel and a local Chat substitute replace native inference, and
the broker is captured. Both runs made zero real-model calls; they establish SQL custody and
settlement, not grounding, abstention, model usefulness or installed startup.

A further six-case PostgreSQL run preserves those cases and adds the actual worker failure path
for a nonempty output-limited FunctionModel stream. Its normalized metadata passes through the
original SDK and pump: the Run retains `FAILED` and the safe reason, with one provider attempt, no
normal settled answer or SDK history, and observed Context/lease cleanup. The recall receipt stays
inspectable; ordinary Live Stasis leaves no retained checkpoint in this case. All six cases pass
with zero real-model calls, and an independent terminal audit confirms resource and input custody.
This is an offline-provider SQL result, not native output-completeness qualification.

A separate [native composition test](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_semantic_native_runtime.py)
and [maintained observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/archive/native-semantic-runtime-2026-10-19.json)
qualify one fixed public synthetic lifecycle through authenticated in-process ASGI, current
factories, the shared lease ledger, actual PostgreSQL and the registered Qwen3-Embedding CPU
profile. Candidates are excluded; promoted notes can be derived, ranked and resolved. Correction
requires explicit rederivation and refuses the old current source; revocation clears source/vector
custody. Historical replay stays inspectable and adds no embedding operation. Eight actual
operations (five queries, three documents), 16 model POSTs and 177 input tokens completed with
all observed clients closed and no leases remaining. An independent operator audit confirmed
owned processes, groups, cgroups, containers, anonymous storage, listener and socket absence,
and unchanged source/model/selected SDK, unrelated work, warm services and retained storage.
Application startup also probes capabilities whose preloaded metadata has no readiness state,
before recovery starts; metadata never forces cold/error observations to warm. Focused lifespan
controls distinguish this real-adapter observation from metadata hydration or forcing warm state.
The test requires a separately admitted bounded outer unit and an independent terminal audit;
its [operation procedure](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md)
retains the trusted operator and fixed host/profile boundary. It does not activate a model through
the Orchestrator or exercise normal Settings database socket configuration.

**Boundary — Not yet:** Ordinary Bridge3 remains lexical RAG for explicit same-host public notes.
The separate semantic API has only the fixed native lifecycle qualification above; general retrieval
quality remains unqualified. Revision 5 additionally has the fixed native answer observation above;
general answer usefulness and grounding, installed startup and automatic crash recovery remain
unqualified. General `CandidateArchivePort`, automatic conversation retention, extraction, Curator,
GraphRAG, shared namespaces, remote IAM, private-material egress and training remain unqualified.
Public-note management controls
have no source-body preview or prefilled editing; real-browser keyboard/reflow/reload acceptance and
installed cutover remain unqualified. Ordinary revision 3 execution uses live Graph persistence; separately proved typed
checkpoint reconstruction does not establish automatic recovery after worker death. The portable
vertical receipt substitutes model/resource seams; the separate native observation qualifies only
its named model, configuration and trusted operator profile. Its native address-space/CPU limits
apply per process, not to the aggregate cgroup. Neither receipt qualifies an installed caged body,
private memory or autonomous improvement.
The derivation path has no background worker, automatic model activation, chunking or ANN index;
oversize notes refuse. The standalone live Core embedding proof remains transport evidence; the fixed native composition
above is the separate Archive/database/model qualification.
Generated answers can quote sources; later revocation does not erase earlier output or influence.

**Evidence**

- **Source:** [Archive contracts and service](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/archive), [PostgreSQL adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/archive.py), [migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0012_archive_public_notes.py), [Archive API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/archive.py), [transient projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/archive_context.py), and [public-note workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/archive_chat.py)
- **Source:** [Derivation service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/archive/derivation_service.py), [derivation store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/archive_derivation.py), [migration 0013](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0013_archive_derivations.py), and [configured derivation API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/archive_derivation.py)
- **Verification:** [Domain tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/test_archive.py), [PostgreSQL lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_pg.py), [migrations](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_migrations_pg.py), [runtime role](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_runtime_pg.py), [worker and typed continuation](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_vertical_pg.py), and [projection tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_archive_context.py)
- **Verification:** [Derivation races](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_pg.py), [configured HTTP and lease integration](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_http_pg.py), [migration rollback](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_migrations_pg.py), and [derivation runtime role](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_derivation_runtime_pg.py)
- **Source:** [Exact semantic values and service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/archive/semantic_service.py), [filtered PostgreSQL store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/archive_semantic.py), and [separate authenticated API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/archive_semantic.py)
- **Verification:** [Semantic protocol and numeric identity](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/test_archive_semantic.py), [retained schema and safe storage failures](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_archive_semantic.py), [actual PostgreSQL fences and runtime role](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_semantic_pg.py), [composed HTTP with intercepted model responses](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_semantic_http_pg.py), [transport denials](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_archive_semantic.py), and [exported contract](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_archive_semantic_openapi.py)
- **Source:** [Semantic source-answer workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/semantic_chat.py) and [immutable semantic admission binding](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/semantic_answer.py)
- **Verification:** [Component graph, current-authority and transient-source controls](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_semantic_chat.py), [semantic admission and effect-free composition](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_semantic_answer_admission.py), and [actual PostgreSQL worker custody and explicit typed reconstruction](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_semantic_answer_pg.py)
- **Verification:** [Initial readiness observations](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_lifespan_readiness.py), [fixed native answer profile](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_semantic_answer_native_runtime.py), [maintained native answer receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/archive/native-semantic-answer-runtime-2026-10-19.json), and [inert transport/result controls](https://github.com/hexanomicon/lychd/blob/main/tests/unit/support/test_semantic_answer_runtime.py) and [maintained receipt freshness controls](https://github.com/hexanomicon/lychd/blob/main/tests/unit/support/test_archive_semantic_runtime.py). This separate fixed A/B/C qualification does not extend the Archive lifecycle receipt.
- **Verification:** [Native semantic composition](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_archive_semantic_native_runtime.py), [owned runtime helper](https://github.com/hexanomicon/lychd/blob/main/tests/support/archive_semantic_runtime.py), [maintained native receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/archive/native-semantic-runtime-2026-10-19.json), and [inert admission/source freshness](https://github.com/hexanomicon/lychd/blob/main/tests/unit/support/test_archive_semantic_runtime.py)
- **Verification:** [Metadata authority, cursor and column-selection tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_archive_failures.py) and [guarded metadata HTTP tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_archive_metadata.py); the PostgreSQL lifecycle and vertical tests above include retained metadata recovery and no-write reads.
- **Source:** [Public-note focus](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/PublicNotes.svelte) and [framework-neutral recovery controller](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/archive/notes.ts)
- **Verification:** [Recovery and unknown outcomes](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/archive/notes.test.ts), [controls and late-focus races](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/PublicNotes.test.ts), [transport/CSRF](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/api/archive.test.ts), [closed route dispatch](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/routes/bridge/page.test.ts), and [ordinary Bridge workspace preservation](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeShellNavigation.test.ts)
- **Source:** [Explicit semantic source focus](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/PublicNoteRecall.svelte) and [plain recall controller](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/archive/semantic.ts)
- **Verification:** [Semantic request, recovery and source fences](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/archive/semantic.test.ts), [source focus and keyboard controls](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/PublicNoteRecall.test.ts), and the transport/route/workspace tests above.
- **Source:** [Exact-note preparation controls](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/PublicNotePreparation.svelte) and [preparation controller](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/archive/preparation.ts)
- **Verification:** [Latest-state and frozen-reference recovery](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/archive/preparation.test.ts), [preparation controls](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/PublicNotePreparation.test.ts), and the public-note management/transport tests above.
- **Source:** [Exact-Run Archive inspector](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/ArchiveRecallPanel.svelte); [inspector tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/ArchiveRecallPanel.test.ts) cover protected display and lifetime.
- **Verification:** [Exact-Run recall binding, preseed and current-authority HTTP tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_archive_run_recall.py); the PostgreSQL lifecycle and vertical tests above cover terminal and historical metadata reads.
- **Topic:** [Public-note answers](./divination/altar/bridge.md#public-note-answers), [explicit semantic sources](./divination/altar/bridge.md#recall-semantic-sources), [semantic generation answers](./divination/altar/bridge.md#answer-from-a-semantic-generation), and [matching Archive selection](./divination/altar/orb.md#inspect-a-matching-archive-selection)
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

Altar now offers a typed public-source Investigation focus within existing Bridge. Explicit
`?investigation=new` opens intake; a case UUID opens an operator-triggered protected Check. The
browser retains the exact request identity/body after any failed POST, including authorization
refusal, without inferring that admission did not occur. A 404 Check does not settle an in-flight
submission. Identical replay requires an explicit action and the original transient body; reload
or leaving this focus cannot reconstruct it. Valid mounted case selection retains transient work;
duplicate or invalid selection retains the departure warning. Explicit discard has separate
Keep/Discard controls and preserves keyboard focus during a pending Check. Ordinary Bridge
session/draft state stays separate.

The report renders validated retained sources, candidate and native verdict as text, with exact
admission Run links to Orb. **Load feedback** explicitly reads the existing protected historical
projection; mounting or selecting a case performs no feedback read. Current IDs select the
external assessment and owner decision, so a later assessment cannot inherit an older hold.
Native verdict, external assessment, owner disposition and feedback status have separate scalar
summaries; the current report, reason and supplied annotation coverage are escaped text. Refused,
unavailable, unassessed and external not-assessed states remain distinct. Selection and teardown
abort owned reads and fence late results; refusal clears protected feedback.

Detail GET, fresh POST and replay POST retain their existing current-authority rechecks after
awaited case reads; this adds no read-scope requirement to submit. Deterministic regressions
reproduce all three revoked-during-await cases. Integrated frontend checks pass 430 tests with
zero Svelte errors/warnings; the affected protected Creation web contract passes nine tests.
This UI adds no source editing, feedback mutation, automatic continuation or execution authority.

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
needs no current model readiness. Feedback intake itself publishes no successor Run; explicit successor admission is separate below.

Focused tests cover current credentials, scopes, Origin/CSRF, duplicate JSON, literal report and
canonical target bounds. The earlier feedback checkpoint qualified fourteen real PostgreSQL cases covering custody, restart attribution,
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

A separate protected local action now admits one new investigation from the exact latest
assessment and owner decision. Fresh operator authorization supplies a complete new request,
acceptance and bounded changed hypothesis. The child receives the current exact profile and its
own finite reservation. The implementation closure advances to `py.6` with unchanged role
instructions, packets and limits. One transaction retains its Session, child, admission and immutable lineage
before Run publication, permanently consuming the parent's one-child allowance. Parent custody,
feedback and deadline remain unchanged; a child cannot admit another descendant through this action.
Separate lineage projection preserves the historical CaseView shape. Identical replay returns
original attribution without model readiness or renewal; only the original still-current binding
may repair its exact held delivery. A fresh startup may read retained held custody without repair.

Current qualification passes 79 inert unit/API cases, 31 real PostgreSQL worker cases and the
complete 90-case migration module. Controls cover concurrent one-child admission, a one-connection
pool with exactly one Session, foreign-bind refusal, feedback freshness, revoked authority,
unresolved claims, settled delivery, bound-but-held recovery, historical restart and permanent debit.
Additive migration `0018` covers empty cycles and refuses downgrade while lineage remains.
Generated OpenAPI/TypeScript, 341 frontend tests and repository static checks pass; the final test-only
fixture repair passes focused static checks. Final non-container qualification passes 5,895 tests
with 15 explicit optional skips and 448 container deselections. Three actual Bridge baselines and
fresh extractor/composed Scout qualification preserve the maintained receipt oracles.

One [ordinary native successor observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-successor-admission-2026-10-17.json)
at source `a80d91d` uses ordinary CLI/configuration, protected API, SAQ and retained PostgreSQL.
A private bounded backup precedes ordinary bootstrap from `0017` to `0018`; restore remains unproved.
The explicit child retains two one-shot roles in 29.8 seconds (6,490 prompt / 675 generated tokens),
releases its slot and preserves all four historical cases and parent feedback. Protected replay before
and after a distinct-process restart preserves original lineage attribution with no extra inference;
changed-body and second-child requests refuse with 409. Independent settlement confirms exact task
process/unit/group/container/port closure, retained storage and unchanged installed bindings.

The child is natively accepted, but a fresh reviewer commits source-only expectations before seeing
its outputs and grades both roles ordering PASS / discrimination FAIL. Both answer the actual
implementation's success instead of the requested last-parked alternative; verifier acceptance is
unsupported. At that observation, this external report was not yet natively attached to the child
and no child owner decision was observed. Parent native acceptance, external partial assessment and
owner hold remained unchanged. No semantic improvement, autonomous work selection or executable
candidate verification was proved.

The earlier successor observation retains its historical unattached-review boundary. A later [native child feedback attachment](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-child-feedback-2026-10-17.json) at source `1777cbfb` attaches that exact 3,346-byte public report to child `701dcbed-1ddb-4b96-80bf-3cad32f13588`. Native `accepted`, Root-mapped external `partial` and owner `hold` remain separate; empty submitter annotations leave both criteria `not_assessed` in typed coverage. Exact protected replay and changed-body409 refusal preserve original feedback attribution across a normal restart. All six retained cases, prior feedback and lineage remain unchanged, with no new investigation, Run or inference. This records report custody and disposition, without semantic regrading, promotion or further child authority.

The wider SDLC law defines attributable request → candidate → verification → promotion-request →
target-owner-effect ownership. The Creation method and Ouroboros map connect work to separately
governed evaluation, memory, training and body change. The Development bootstrap procedure orders
operator-controlled work and incremental qualification; these methods introduce no general scheduler
or autonomous development service.

**Boundary — Not yet:** This investigation performs no source editing, executable workspace,
filesystem/command execution, safe Forge, autonomous repair, target-owner promotion, rollback or
self-extension. Its local credential role supplies no remote IAM or person-level tenancy; an
unknown issued inference has no automatic slot-release path. Explicit successor admission remains
operator-triggered; automatic task selection, correction and measured recursive improvement remain
unbuilt. There is likewise no instantiated
distributed repository identity or maintainer roster, executable key-custody/rotation mechanism,
governance-epoch ledger, quorum verifier, signed portable promotion envelope, independent
attestation plane, canonical source on Radicle, Radicle node topology or downstream-mirror cutover.

**Evidence**

- **Source:** [Investigation service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/services.py), [Pattern](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/creation/workflow.py), [PostgreSQL owner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/creation.py), and [protected API](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/api/creation.py)
- **Verification:** [Agent boundaries](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_creation.py), [successor intake/replay](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_creation_successor.py), [local API](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_creation.py), [PostgreSQL worker histories](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_creation_postgres_vertical.py), and [migration cycle/refusal](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_migrations_pg.py)
- **Verification:** [Dated native investigation outcomes](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/investigation-2026-10-17.json) retains the three distinct occurrences, exact public inputs/outputs, resource evidence and separate verdicts.
- **Verification:** [Ordinary native configuration observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-configuration-2026-10-17.json) retains the separate noncompletion, exact public packet/result, canonical-byte failure and bounded service/replay evidence.
- **Verification:** [Ordinary native two-role observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-configuration-guidance-2026-10-17.json) retains the distinct successful occurrence, exact public role packets/results, replay/custody observations and separate partial external judgment.
- **Verification:** [Ordinary native feedback observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-feedback-2026-10-17.json) retains the exact external report, separate native/external/owner dispositions, normal restart/replay and bounded resource observations.
- **Verification:** [Unfamiliar native noncompletion](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-successor-2026-10-17.json) retains the exact public role packet, unadopted output, separate schema/byte failures and attributed citation review.
- **Verification:** [Known-case source projection](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-source-projection-2026-10-17.json) retains both exact projected packets/results, native accepted, separate partial external judgments and normal restart/closure observations.
- **Verification:** [Native attachment of the later review](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/creation/native-source-projection-feedback-2026-10-17.json) retains the subsequent exact-report attachment, separate partial/hold, typed coverage, replay/restart and zero-inference settlement.
- **Verification:** [Current-authority read regressions](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_creation_read_authority.py), [intake lifecycle](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/creation/intake.test.ts), [Investigation UI](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/CreationInvestigation.test.ts), [feedback disclosure](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/CreationFeedback.test.ts), and [generated transport](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/api/creation.test.ts)
- **Topic:** [Creation investigation](./compositions/creation/index.md), [Smith](./sepulcher/extensions/smith.md),
  [Creation](./sepulcher/extensions/weaver/creation.md), and [Ouroboros](./sepulcher/extensions/weaver/ouroboros.md),
  with [Development bootstrap](./sepulcher/extensions/weaver/development-bootstrap.md) and
  [coding-runtime research](./sepulcher/extensions/weaver/coding-runtime-research.md)
- **Law:** [SDLC](./adr/16-sdlc.md), [Packaging](./adr/17-packaging.md#forge-neutral-source-trust),
  and [Evolution](./adr/18-evolution.md#future-quorum-roster)

### Remote IAM {#remote-iam}

**State:** Partial

**Proved now:** The inactive `host-opaque-candidate@1` Ward foundation and a separately composed closed native-candidate consumer have a dated combined disposable-PostgreSQL observation: 23 tests passed, comprising 18 Ward cases and five current-authority passage cases. Ward exercises the full real bootstrap/HBA and Alembic chain, including 0019↔0020 and restricted-runtime DML/DDL refusals. The native fixture instead creates isolated Ward/Creation tables through metadata DDL; its five passes qualify the declared authority/custody passage, not a second full migration-chain receipt. That passage binds exact retained candidate bytes and plan, an independent attributed assessment and inactive hold/reject decisions; it exercises actual Principal-lock waiting and committed revocation, database-clock expiry after real staging, serialized shutdown, exact retained-identity reconciliation after injected post-commit acknowledgement loss, and refusal of mapper/table/prebound-connection escapes before effects. Three cached PG objects and their anonymous volumes settled; Root separately recorded retained process/cgroup absence and protected warm/model-state preservation. The earlier Ward-only failed-then-passed receipt remains separate historical evidence. The whole old 66-input qualification is sealed history after the container-only correction. Its oracle preserves the original mechanism, migration and dependency inventory and rejects that dated receipt as current qualification of the combined source. It neither renews the historical observation nor reruns PostgreSQL. The 20 October OCI occurrence passed the same 23 tests in the explicit test image, with actual per-database kernel limits and independently verified container, anonymous-volume and cgroup cleanup. Its dated OCI receipt binds the named configuration, mechanism and test inputs; no model or activation effect was submitted.

The separate bounded outbound peer profile separates actual local operator authentication,
workload signing identity and enrolled immutable remote peer identity. Public credential versions,
current exact object/action policy, key retirement and durable revocation fence the outgoing task
and result-consumption path. Dedicated public-source classification requires its own current
permission. A persisted row or reconstructed marker supplies no live authority. The profile has
one control process and event loop.

**Boundary — Not yet:** The isolated trusted-host passage is unregistered in the application. It supplies no installed body/CLI, foreign-constructor execution or containment, general remote IAM/device enrollment, production activation, positive OwnerAdmission/promotion, repository write, general owned-content integration, genuine application/database-process restart, shared filesystem/database transaction, exactly-once effect or native/hostile aggregate containment. Reopening a service is not process-restart evidence. Acknowledgement faults are injected after actual commit; no physically broken database connection is proved. Ward's conservative eligible publication audit remains unknown. General remote human/device identity and activation remain Designed.

General incoming Ward, human accounts, remote sessions, delegated grants,
tenant isolation, cross-process revocation and hostile same-UID containment remain Designed.

The current remote/device trial has no second device, so that physical roundtrip is externally
blocked. This does not qualify general enrollment or remote IAM, and does not discharge the separate
implementation gaps above.

**Evidence**

- **Topic:** [Ward](./sepulcher/extensions/ward.md)
- **Law:** [IAM](./adr/38-iam.md), [Persistence](./adr/06-persistence.md), [Evolution](./adr/18-evolution.md)
- **Verification:** [20 October Ward OCI receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/runtime/container-only-2026-10-20.json), [OCI receipt controls](https://github.com/hexanomicon/lychd/blob/main/tests/architecture/test_container_only_receipt.py), [historical combined PostgreSQL receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/ward/ward-native-postgres-2026-10-20.json), [historical scope and current-qualification refusal](https://github.com/hexanomicon/lychd/blob/main/tests/architecture/test_ward_native_postgres_receipt.py), [Ward PostgreSQL cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_ward_pg.py), and [native authority cases](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_native_candidate_authority_pg.py)
- **Source:** [Peer authority](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/peer_authority.py) and [operator public-source contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/peer.py)
- **Verification:** [Authority and lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_intercom.py) and [durable peer custody](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_intercom_pg.py)

### A2A and Intercom {#a2a-intercom}

**State:** Partial

**Proved now:** The explicit `outbound-public-text@1` service and operator session submit a sealed
public task, retain the receiver's task identity, poll it and consume authenticated inline text
under separate read authority. A2A `1.0.1` JSON-RPC and a required RFC 9421 Ed25519 profile bind the
exact body, roles, peer, schema, physical attempt and pending request. Complete-wire gating uses
numeric-pinned TLS, explicit CA/hostname, one finite deadline and current same-loop authority.
Seven PostgreSQL tables retain enrollment, public credentials, source declarations, tasks,
outbox, physical transmissions and permanent capacity. Every attempt charges one use, its complete
application bytes and conservative network capacity before contact; observed bytes do not refund
charges. An uncertain submit is never resent. Fresh authentication can reconcile a known foreign
task after reconstruction. Local cancellation closes result adoption independently of foreign
execution observations, and the first admitted terminal remains readable under current authority.

The 22 October manual qualification against official SDK `1.2.3` exercised actual asynchronous task dispatch,
polling and cancellation with explicitly test-only signing middleware. Lost replies, altered body
bytes and missing extension evidence retained unknown execution without another submit. Fifteen
actual PostgreSQL tests cover concurrency, lost commit acknowledgement, restart, replay, retained
custody, transactional migration and complete catalog parity. The maintained receipt binds a
bounded source list; it does not claim a transitive source closure or general A2A certification.

The opt-in `native-public-peer@1` lab now joins the shared RunEngine, serial Graph and PostgreSQL
checkpoint/claim/delivery ledger. No-contact preparation precedes checkpoint and `AWAITING_PEER`;
one exact correlated terminal or explicit local unknown/expiry disposition admits one successor.
The immutable source, task, original expiry and Step/occurrence relation survive reconstruction,
while live permission requires fresh authentication and explicit same-task reauthorization.
Local cancellation closes adoption and awaits owned exchange/socket retirement; foreign execution
uncertainty stays visible. The 22 October native receipt records six actual SDK/PostgreSQL/process
cases covering fresh-authority restart,
post-claim/pre-wire process death without resubmit, credential rotation during a real Run lock
wait, lost submit reply, revoked-peer local cancellation and blocked TLS-read retirement. Eleven
native migration cases covered complete ORM catalog parity, refusal, locks and transactional rollback
under that receipt's original migration identities. The merged source now uses `0022` and `0023`;
the historical observation does not qualify this changed migration closure.
The lab's delivery queue is process-owned; these trials do not qualify a SAQ broker.

**Boundary — Not yet:** There is no incoming LychD A2A server, durable receiving inbox, discovery,
callback, artifact fetch, streaming, private-input Cut transport,
voice/Context anonymization, automatic fallback or normal-boot activation. An operator's public
assertion is neither PII detection nor proof text was never pasted. Unsigned stock SDK routes
cannot satisfy the required extension.

**Evidence**

- **Topic:** [Intercom operator session](./sepulcher/intercom.md)
- **Source:** [Task service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/intercom.py), [wire admission and HTTPS](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/intercom_http.py), [custody store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/intercom.py), and [operator entry](https://github.com/hexanomicon/lychd/blob/main/scripts/intercom_lab.py)
- **Verification:** [Protocol and receipt](https://github.com/hexanomicon/lychd/tree/main/tests/unit/domain/intercom), [real cryptography and parser](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_intercom_http.py), [authority and lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_intercom.py), [PostgreSQL custody](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_intercom_pg.py), and [migration](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_intercom_migrations_pg.py)
- **Verification:** [Bounded manual peer receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/intercom/operator-public-source.json)
- **Source:** [Native peer Run service](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/peer_runs.py), [Graph station](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/native_public_peer.py), and [explicit native lab](https://github.com/hexanomicon/lychd/blob/main/scripts/intercom_native_lab.py)
- **Verification:** [Native ownership and reentry](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_peer_native_wait.py), [native authority and recovery](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_peer_runs.py), and [native migration](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_native_peer_migrations_pg.py)
- **Verification:** [Bounded native peer receipt](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/intercom/native-public-source.json), [historical receipt integrity](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/intercom/test_native_receipt.py), and [operator outcome projection](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_intercom_native_lab.py)
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
