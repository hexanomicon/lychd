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
| CLI bootstrap | **Partial:** grammar, dry-run plans, transactional `init`/`bind`, bounded inspection, and guarded deletion have repository evidence. | No maintained real-host lifecycle receipt. See [CLI](#core-cli-rites) and [embodiment](#systemd-podman-embodiment). |
| Local text chat | **Partial:** the Pydantic AI adapter, local Run engine, and Bridge contracts work in the repository-test envelope. | No inference-engine plus real-browser acceptance receipt. See [Bridge](#bridge-surface) and [persistence](#phylactery-first-light). |
| Browser safety | **Loopback only:** Host, CORS, CSRF, and generated bind policy are bounded locally. | The bootstrap Sigil is not authentication; remote and untrusted-browser use remain unsupported. |
| PostgreSQL lifecycle | **Repository receipt:** factory, PostgreSQL, SAQ, HTTP, shutdown, and second-boot projection recovery run together. | Live dispatch, orchestration, and Context are replaced after startup; no real-host or browser proof. |
| Major blockers | Authenticated caller authority, privacy-safe egress, artifact custody, real host/model receipts, native Oculus, and resource-aware scheduling. | Remote transport, federation, executable evolution, durable recall, and vision/audio bytes remain Partial or Designed. |

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

The strongest maintained conjunction uses the real application factory, disposable PostgreSQL,
in-process SAQ, HTTP, shutdown, and a second boot, while substituting offline collaborators after
startup. It proves wiring and durable projection recovery, not full composed runtime behavior.

- **Source:** [Application factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py)
- **Verification:** [Two-boot lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [Quality](./adr/03-quality.md) and [Testing](./adr/04-testing.md)

## Inscription and embodiment {#inscription-and-embodiment}

### Settings generations {#settings-generations}

**State:** Available

**Proved now:** Root Settings loads the core database password and web signing key once per
construction as excluded `SecretStr` values. Cached consumers and in-memory snapshot restoration
perform no credential I/O; JSON and generated TOML omit credentials. Explicit new Settings reads
fresh inputs. Host bootstrap tolerates unprovisioned default mounts; runtime components reject
missing credentials.

**Boundary:** This covers the core DB/web credentials, not every extension's credential handling
or live Podman provisioning. No automatic credential reload is delivered.

**Evidence**

- **Source:** [Settings](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/root.py), [Credential source](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/settings/sources.py)
- **Verification:** [Credential tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_credentials.py), [Settings tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_settings.py)
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
receipts, and explicit rollback or indeterminate outcomes.

**Boundary — Not yet:** Status omits full readiness and durable-run health; no run-operation command
or authenticated Vessel submission route is delivered; `stop` refuses an active Vessel without its
authenticated lifecycle port; deletion preserves objects whose creation provenance is not owned.
Unknown unit or mount truth blocks instead of guessing. No maintained real systemd/Podman lifecycle
or GPU receipt exists.

**Evidence**

- **Source:** [CLI assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__main__.py)
- **Verification:** [CLI tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py)
- **Law:** [CLI](./adr/19-cli.md)

### Public release artifact chain {#public-release-artifact-chain}

**State:** Designed

**Proved now:** Distribution, container, archive-audit, source-preflight, and non-publishing
candidate declarations exist and are tested without granting publish authority.

**Do not expect yet:** No maintained receipt pairs this revision as one anonymously installable
PyPI package and immutable GHCR image, and no clean-host install/start/reply/stop promotion gate
has run.

**Evidence**

- **Source:** [Package version](https://github.com/hexanomicon/lychd/blob/main/src/lychd/__about__.py)
- **Verification:** [Release artifact tests](https://github.com/hexanomicon/lychd/blob/main/tests/architecture/test_release_legal_artifacts.py)
- **Version:** [Distribution declaration](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
- **Law:** [Packaging](./adr/17-packaging.md)

### Deployment-plan compilation and materialization {#deployment-plan-materialization}

**State:** Available

**Proved now:** Soulstone and extension intent compile into validated Quadlet/systemd plans,
including Animator targets, conflict topology, and compatible Coven aggregates, and Scribe
materializes the declared files. A complete ownership manifest refuses distinct Quadlet/systemd
runtime-bearing sources that systemd would resolve to one runtime unit.

**Boundary:** Generated unit intent does not prove that systemd or Podman started it on a real host.

**Evidence**

- **Source:** [Deployment transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py) and [Scribe ownership manifest](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scribe/models.py)
- **Verification:** [Transmutation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute.py) and [Scribe tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scribe.py)
- **Law:** [Containers](./adr/08-containers.md)

### Runtime actuation and mediated Host Reactor protocol {#host-reactor-protocol}

**State:** Available

**Proved now:** The mediated Host Reactor validates and durably claims intent, attests the loaded
Scribe graph, performs one bounded target transaction, observes settlement, attempts
exact-prior-world compensation, resumes or contains interrupted journal work, and records outcomes
under the lifecycle lock.

**Boundary:** Protocol tests and an isolated private-systemd receipt use inert services, not the
operator's Quadlet/Podman/GPU host. `.restored` proves the prior world; `.contained` and unresolved
`.processing` fence later Reactor work. General repair remains the operator's responsibility.

**Evidence**

- **Source:** [Host Reactor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/reactor.py)
- **Verification:** [Reactor tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_reactor.py) and [private-systemd receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_target_transaction.py)
- **Law:** [Privilege](./adr/10-privilege.md)

### systemd user and rootless Podman embodiment {#systemd-podman-embodiment}

**State:** Operator validation

**Proved now:** LychD generates its declared Linux service shape and provides a mediated actuator;
Soulstone and Phoenix retain separate identities while sharing validated embedded Quadlet
configuration.

**Receipt needed:** Name the Linux, systemd and Podman versions, generated targets and conflicts,
loaded-source attestation, forward switch, compensation, crash recovery, startup, and shutdown.
GPU and model proof remains separate.

**Evidence**

- **Source:** [Quadlet configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/quadlet.py)
- **Verification:** [Runtime protocol tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py)
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
recovers a Bridge Run across two boots. Distinct production asyncpg codecs round-trip plain `json`
and versioned JSONB, while memory Run, consent, and Bridge-session stores detach mutable values at
the same public boundary as database reads.

**Boundary — Not yet:** PostgreSQL and SAQ are not one transaction; Step events lack an outbox;
memory-profile/PostgreSQL repository parity is incomplete; no general record-retention or
compaction path, partition policy, tablespace lifecycle, automatic capacity expansion, or sharding
path is delivered; persistent same-boot containment failure has no durable watchdog. The lifecycle
receipt substitutes offline collaborators and is not a checkpoint-plus-consent, real-host,
inference-engine, or browser receipt.

**Evidence**

- **Source:** [First-light migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0001_phylactery_first_light.py), [wait-owner migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0008_wait_owner_evidence.py), and [database factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/factory.py)
- **Verification:** [Run ledger tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py), [PostgreSQL run-ledger receipts](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py), and [two-boot lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [Persistence](./adr/06-persistence.md)

### Topology-A local run execution {#topology-a-local-runs}

**State:** Available

**Proved now:** One Vessel process admits, claims, executes, cancels, settles, resumes, and projects
Runs against immutable Pattern revisions. Durable publication intent, replay repair, external-wait
relays with capped restart backoff, terminal-evidence repair, bounded identity fencing, bounded
slow-reader resynchronization, and orderly shutdown are tested.
Unresolved child containment stays nonterminal rather than claiming false `FAILED` truth; a timed-
out cancellation remains `CANCELLING`. Registry boot derives a private one-to-one `legacy_inline`
contract, placement, implementation, and resolution lock for each executable v2 station without
changing its frozen Pattern snapshot or digest; exact revision lookup traverses that resolution.

**Boundary:** This does not prove automatic source compatibility, a transactional event outbox,
separate-worker truth, multi-process streaming, federation, or producer backpressure. The private
lock is not persisted on Run, portable, configurable, or projected by Loom/Orb; no public Spell or
Scroll contribution store is delivered.

**Evidence**

- **Source:** [Run engine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py), [event bus](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/events.py), [workflow resolution](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py), and [startup relay](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/lifespan.py)
- **Verification:** [Run engine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py), [event-bus tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_events.py), [workflow identity tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_state_serializable.py), and [lifespan tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/web/test_lifespan.py)
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

### Pydantic AI 1.107.5 cognitive adapter {#pydantic-ai-v1-adapter}

**State:** Available

**Proved now:** LychD constructs typed agents and runs Bridge through the exact
`pydantic-ai-slim==1.107.5` contract with serializable state and fail-closed provider profiles.

**Boundary:** This does not claim Pydantic AI v2 durability, stream events, GraphBuilder, automatic
usage propagation, or exact pre-request token counts for current OpenAI-compatible models.

**Evidence**

- **Source:** [Agent factory](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py)
- **Verification:** [Agent factory tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_factory.py)
- **Version:** [Dependency](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
- **Law:** [Agents](./adr/20-agents.md)

### Pydantic AI v2 migration {#pydantic-ai-v2-migration}

**State:** Designed

**Proved now:** Agent and Graph law records a future v2 migration while the lockfile remains on
1.107.5.

**Do not expect yet:** V2 messages, toolsets, deferred events, durability, and graph contracts are
not installed behavior.

**Evidence**

- **Current baseline:** [Dependency](https://github.com/hexanomicon/lychd/blob/main/pyproject.toml)
- **Law:** [Agents](./adr/20-agents.md)

### Graph stasis and consent re-admission {#graph-stasis-consent}

**State:** Partial

**Proved now:** Logical parking, bounded approval rounds, exact Consent ownership, simulated
restart, re-admission, idempotent settlement, and fail-closed substitution on resume are tested.
Post-park probe failure preserves `AWAITING_CONSENT`; uncertain cancellation containment leaves the
Run `CANCELLING` instead of manufacturing terminal truth.

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

- **Source:** [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py) and [Run engine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py)
- **Verification:** [Consent resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_consent_resume.py), [Run engine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py), [rehydration tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_rehydration.py), [offline recovery windows](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_offline_recovery_workflow.py), and [node-observer failures](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_graph_observer_failures.py)
- **Law:** [Graph](./adr/24-graph.md) and [Human in the Loop](./adr/25-hitl.md)

### Delegated agent execution {#delegated-agent-execution}

**State:** Partial

**Proved now:** Typed requests without credential or ambient-authority fields, artifact references, process-local job
submission/adoption/cancellation serialized with runtime-start acceptance, exact wait ownership,
terminal-evidenced Graph parking and re-admission, typed containment-profile intent, PostgreSQL
shapes, and a no-effect reference adapter exist.

The reference adapter reconstructs its deterministic projection for refresh and cancellation after
coordinator/runtime restart without replaying an external effect, retains it across failed durable
adoption, and retires it after terminal settlement.

An unclassified runtime-start exception now
records `LOST`; inert lost-acknowledgement tests prove exact-request replay cannot start again,
late success cannot replace that terminal, and cancellation still reaches the owning runtime.

**Boundary — Not yet:** No declared external provider launches. There is no lower-trust executor,
credential or egress isolation, process-tree containment, durable artifact custody, measured
budgets, real PostgreSQL/provider recovery receipt, or live-browser proof.
Request prompts are persisted verbatim; callers must apply the Privacy Cut and egress policy before
any future remote runtime receives them. Effectful runtimes still need durable provider identity,
definite-rejection evidence, and reconciliation of ambiguous start outcomes.

**Evidence**

- **Source:** [Delegation coordinator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/delegation/services.py), [delegated job store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/delegation.py), [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py), [reference runtime](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/reference.py), and [reference adapter catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/register.py)
- **Verification:** [Delegation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_coordinator.py), [ambiguous-start tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_start_outcomes.py), [restart-resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_delegate_resume.py), [delegation schema tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/db/test_delegation_schema.py), and [extension-policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py)
- **Law:** [Workers](./adr/14-workers.md)

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

A non-empty Soulstone `[[models]]`
catalogue is an ordered exact allowlist, concrete runtime leaves cannot claim a foreign adapter,
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
issue. Registry-level Portal issue is quarantined as well as both Dispatcher entry points.

Unregistered runtime aliases, including generic OpenAI-shaped labels, retain inert command planning
but cannot create a capability-bearing runtime; Bind and registry load reject their missing
capability coverage.

**Boundary:** This is the v1 `{animator}:{family}:{model_id}` catalogue with one chat-model/toolset
compatibility grant, not the general discriminated grant union. The catalogue has no in-process
hot reload; lease expiry is recorded but not enforced; current Soulstone/Portal inheritance and raw
Quadlet contribution remain. General interface/profile compilation, call/job/session grants,
`[[capabilities]]`, service-job attempts, per-dialect OpenAI-compatible drivers, and secret-vault
integration are not delivered.

**Evidence**

- **Source:** [Animator registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/registry.py),
  [Soulstone Rune schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/runes/animators.py),
  [OpenAI-compatible probe](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/shared.py),
  and [fixed-runtime projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/openai_compat.py)
- **Verification:** [Registry tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py),
  [runtime adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py),
  [unregistered-runtime admission tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_unregistered_runtime_admission.py),
  [catalogue tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_catalog.py),
  [endpoint-policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_soulstone_endpoint_policy.py),
  [declaration-compiler tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_declarations.py),
  and [Portal tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_portals.py)
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
branches, and fail-closed synchronous hooks.

**Boundary — Not yet:** Ownership is not projected into every live capability view. Package
installation, locks, upgrade/uninstall, migrations, lifecycle effects, Forge admission, and a stable
public SDK are absent.

**Evidence**

- **Source:** [Extension manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/manager.py), [registration context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py), and [assembly host](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/host.py)
- **Verification:** [Assembly tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_catalog.py), [activation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_admission.py), [delegation contribution tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py), and [generated bind-fileset tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_bind_fileset.py)
- **Law:** [Extensions](./adr/05-extensions.md)

### llama.cpp integration {#llamacpp-integration}

**State:** Operator validation

**Proved now:** Runtime planning, static and router connectors, discovery, capability derivation,
load/unload control, and contract tests exist. Known command/endpoint port conflicts fail during
declaration compilation. Runtime construction captures one preset catalogue and generation
profile; capability synthesis uses that captured generation even if the preset file changes.

**Receipt needed:** Name the image and revision, model and quantization, GPU and driver, flags,
systemd/Podman host, load, inference, and unload results.

**Evidence**

- **Source:** [llama.cpp adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/llamacpp.py)
- **Verification:** [Adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py) and [endpoint/preset generation tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_runtime_endpoint_contract.py)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### vLLM integration {#vllm-integration}

**State:** Operator validation

**Proved now:** A vLLM runtime plan, OpenAI-compatible connector, model/capability derivation, and
focused tests exist.

**Receipt needed:** Name the image and revision, model, GPU and driver, arguments, systemd/Podman
host, readiness, inference, and shutdown.

**Evidence**

- **Source:** [vLLM registration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/vllm/register.py), [vLLM Rune](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/soulstones/vllm.py), and [shared OpenAI-compatible runtime](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/openai_compat.py)
- **Verification:** [Adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py)
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

**Boundary:** Repository tests and a private user-manager receipt use inert services, not the
operator's Quadlet/Podman/GPU host. Declared coexistence is not measured capacity admission.

**Evidence**

- **Source:** [Conflict schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/concurrency.py) and [runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py)
- **Verification:** [Conflict tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_conflicts.py) and [private-systemd receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_systemd_target_transaction.py)
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

**Boundary — Not yet:** Dynamic shared-capacity admission, durable multi-process orchestration,
general repair, and a maintained real model/GPU transition receipt are absent. A failed soft
model-load has no trustworthy rollback and requires contained operator recovery; `.contained` and
unresolved `.processing` fence later work.

**Evidence**

- **Source:** [Orchestrator manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/manager.py)
- **Verification:** [Transition tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_manager.py), [runtime workflow scenarios](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_workflow_scenarios.py), [observer boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_observation_boundaries.py), and [Orchestrator API tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_api_orchestrator.py)
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
and Litestar delivery exist. Focused tests prove contracts and components, not a
production-factory browser receipt. No XYFlow/Svelte Flow, Sigma, or Graphology dependency and no
Loom or Orb graph canvas or shared graph-projection supply is delivered; ADR 15's renderer
directions and admission gates are law, not implementation evidence.
The [reading hierarchy and visual direction](./adr/15-frontend.md#reading-hierarchy-and-visual-direction)
and [instrument reading scenarios](./divination/altar/index.md#presentation-direction) record the
next presentation targets. Design studies and illustrative browser checks do not establish
production graph delivery, restart recovery, large-collection performance, or accessibility
acceptance; the instrument records below retain their existing evidence boundaries.
The document language and interface copy are English. There is no message catalogue, explicit
locale resolver or selector, Principal-preference binding, translated accessibility surface, or
right-to-left receipt. Browser-native date/time formatting may reflect a device locale, but that
incidental variation is not delivered localization support.
The compiled Altar has one fixed LychD Dark palette, dark browser metadata, dark native-control
colour scheme, and no light/system selector, system-scheme following, palette configuration,
runtime theme loader, or supported theme extension. Semantic CSS custom properties establish a
future refactoring seam, but hard-coded dark surfaces remain in the main background, Mermaid, and
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

**Boundary — Not yet:** There is no AI concern generation, automated coverage judgment,
autonomous continuation, project scheduler, implicit Context injection, inferred clustering, or
project-wide control over Run admission and cancellation. References identify related activity;
they do not freeze execution evidence. The surface has no delete action or complete edit audit.
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
Its per-turn run strip is the first thin projection of one Invocation's Circle. Dispatcher grant ids
rebind the Environment snapshot before inference and after consent re-entry. Browser-shell state
retains per-session drafts and immutable unknown-admission envelopes across instrument navigation;
later middleware refusals cannot replace an earlier uncertain identity. Late responses settle that
state even after view teardown, and admission overtaking a snapshot requires a newer read.
Definitely refused text is retained alongside a later draft. Hard unload warns; this state does
not survive browser termination. The shell's consent link opens a session chooser with server-owned
per-session counts; decisions update only their owning session's visible attention.

**Boundary — Not yet:** There is no production-browser plus inference-engine receipt, durable cross-process event/token
delivery, general multi-approval, Attention, or notification channel. Text is the only command
modality, and no focused Circle workspace composes Scroll, active Spell placement,
Context/authority, capability, and evidence projections.

**Evidence**

- **Source:** [Bridge controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py)
- **Verification:** [Bridge tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge.py) and [client recovery tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/BridgeView.test.ts)
- **Law:** [Frontend](./adr/15-frontend.md)

### Nexus transition board {#nexus-transition-board}

**State:** Partial

**Proved now:** Nexus renders typed state and plans, submits explicit transitions, fences
ambiguous request identities, follows bounded process-local tickets, and durably reserves the
first target request before launch.

**Boundary — Not yet:** Only request admission is durable. Transition observations lack a durable
owner, complete history, cross-process projection, restart recovery, and production-browser
receipt. Durable admission prevents duplicate launch, but a lost ticket cannot prove the outcome
or resume safely; retry refuses to relaunch it.

**Evidence**

- **Source:** [Nexus controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/nexus.py)
- **Verification:** [Nexus tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_nexus.py)
- **Law:** [Frontend](./adr/15-frontend.md)

### Loom workflow instrument {#loom-workflow-views}

**State:** Partial

**Proved now:** Loom browses exact immutable Pattern revisions, manifests, semantic station and
permission outlines, checkpoint schemas, implementation revisions, source, active/default state,
and retained revisions with stale-response-fenced client loading. Verified Orb origin links retain
the Run and selected event on return; mismatched context is reported without choosing another Run.

**Boundary — Not yet:** Loom is a view over the fixed registry, not a Spellweaver editor, mutation
surface, independent Spell identity or catalogue, compatibility or teaching surface, drafting
canvas, admitted graph-renderer dependency, inert unresolved-Spell projection, Suite executor, or
production-browser receipt.

**Evidence**

- **Source:** [Loom controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/loom.py), [Pattern registry contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py), and [Loom client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/LoomView.svelte)
- **Verification:** [Loom tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_loom.py) and [client lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/LoomView.test.ts)
- **Law:** [Workflow](./adr/28-workflow.md)

### Composition Portfolio {#composition-portfolio-delivery}

**State:** Designed

**Proved now:** The Portfolio publishes Native Reference Composition contracts and examples; the
boot catalogue contains only the Core `bridge_chat` lineage (revisions 1 and 2) and `delegated_rite@1`.

**Do not expect yet:** There is no Composition store or selector, Product catalogue or selector,
Portfolio Pattern registration, Suite execution, application scheduling, or delivered domain/effect
path for any Portfolio member or Product. Crucible is a designed Weaver choreography, not a
registered Pattern, parallel Graph, dossier schema, or Altar surface.

**Evidence**

- **Source:** [Workflow registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py)
- **Verification:** [Workflow routing tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_router.py)
- **Topic:** [Composition Portfolio](./compositions/index.md)
- **Law:** [Workflow](./adr/28-workflow.md)

### Orb instrument {#orb-instrument}

**State:** Partial

**Proved now:** Orb renders one Run as ordered, paginated evidence with Pattern revision, capture
durability, ledger boundaries, gaps, transition links, stable selection, bounded retry, and
teardown-cancelled snapshot reads. Its delegated-job projection applies newest-job and per-job
event limits at the store query boundary before rendering the public 32/64 suffixes. Shell
navigation retains the last selected Orb Run/event during the document lifetime. The Loom round
trip preserves that selection, and Bridge return focuses the exact Run's turn or reports its
absence.

**Boundary — Not yet:** There is no run list, live tail, graph field, durable Oculus read model,
Sigma/Graphology adapter, cross-process completeness, health query, artifact custody, annotation,
or multi-run view.

**Evidence**

- **Source:** [Orb controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/orb.py) and [Orb client](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbView.svelte)
- **Verification:** [Orb API tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb.py) and [Orb client tests](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/components/OrbView.test.ts)
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

**External owner and boundary:** [Arize owns Phoenix](https://github.com/arize-ai/phoenix). LychD
does not own its lifecycle or state, require it for Oculus, or prove application trace export. A
`latest` image is not a reproducible receipt.

**Evidence**

- **Source:** [Phoenix configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/phoenix/config.py)
- **Verification:** [Phoenix generation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py)
- **Law:** [Observability](./adr/29-observability.md)

## Authority and artifacts {#authority-and-artifacts}

### Context privatization and Portal egress {#context-privatization-and-portal-egress}

**State:** Designed

**Proved now:** Context and Security law define privatization labels, source lineage,
consumer-specific Privacy Cuts, independent verification, and a separate egress decision.

**Do not expect yet:** There is no label or lineage implementation, deterministic Censor,
transformation-receipt chain, verified Privacy Cut, sanitized Context branch, pseudonym map, Egress
Gate, transmission check, or deletion propagation.

**Evidence**

- **Topic:** [Portal](./sepulcher/animator/portal.md)
- **Law:** [Context](./adr/21-context.md#privatization-and-the-privacy-cut) and [Security](./adr/09-security.md#portal-privatization-and-egress)

### Local Sigil and scope authority {#local-sigil-authority}

**State:** Partial

**Proved now:** Typed Sigils, scopes, guards, consent preauthorization, transactional use-budget
consumption, policy synchronization, and digest-bound auto-grant revalidation are tested on the
loopback bootstrap surface.

**Boundary — Not yet:** The fixed `magus:*` Sigil is not caller authentication. There is no object
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
environment overrides, then publishes one effective `127.0.0.1` or `::1` TCP listener. Launch,
Host, CORS, local schema assets, fixed root handlers, and
CSRF contracts are bounded and tested.

**Boundary — Not yet:** Requests still receive the bootstrap Sigil. No hostile-browser receipt,
security-header contract, or remote principal exists; proxied, tunneled, non-loopback, and
untrusted-browser use remain unsupported.

**Evidence**

- **Source:** [Application composition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py), [server policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/server_policy.py), and [fixed Altar routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py)
- **Verification:** [Network policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py), [native launcher tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py), [HTTP boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_http_boundary.py), and [Altar route tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
- **Law:** [Security](./adr/09-security.md)

### Scout web acquisition {#scout-web-acquisition}

**State:** Designed

**Proved now:** Web-acquisition law separates search, fetch, render, extraction, destination
pinning, quarantine, authentication, and paid effects. The accepted design selects native static
Fetch + Extract, a SearXNG Search Soulstone, and a later isolated Crawl4AI renderer candidate;
Firecrawl remains deferred and paid web-acquisition Portals remain private-extension territory.

**Do not expect yet:** There is no Scout provider, browser service, endpoint, Agent tool,
acquisition receipt, download quarantine, authenticated session, or Smith ingestion path. There is
no SearXNG or Crawl4AI Rune/adapter, no Scout provider store or effect-scoped tool binding, and no
renderer containment outside the shared Pod.

**Evidence**

- **Topic:** [Scout](./sepulcher/extensions/scout.md)
- **Law:** [Webcrawler](./adr/30-webcrawler.md)

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

**Proved now:** Capabilities declare audio input/output modalities while speech services remain the
`stt` and `tts` families. Even when observed `WARM`, both v1 families fail closed at grant issue
because no typed transcription or synthesis call surface exists.

**Boundary — Not yet:** There is no audio-byte custody or transport, streaming socket, resonance
buffer, working STT/TTS adapter, or Audio Coven.

**Evidence**

- **Source:** [Capability vocabulary](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/capability_family.py)
- **Verification:** [Audio catalogue tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_catalog.py)
  and [grant-boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py)
- **Law:** [Audio](./adr/37-audio.md)

### Artifact reference contract {#artifact-reference-contract}

**State:** Partial

**Proved now:** `ArtifactRef` defines immutable artifact identity, digest, classification, size,
and media type. Delegated-agent requests and results carry those references; focused coordinator
tests pass input metadata to an inert runtime, and a PostgreSQL receipt covers reference
round-tripping through delegated-job creation and result adoption.

**Boundary — Not yet:** Intent and Bridge currently accept text prompts, with no artifact or
required-modality fields propagated through the Run ledger. `ArtifactRef` is not byte custody.
There is no upload/store adapter,
principal-bound retrieval, materializer, derivation provenance, retention/deletion, provider fetch
audit, or Reliquary backend.

**Evidence**

- **Source:** [Artifact reference](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/artifacts.py) and [Intent](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/router.py)
- **Verification:** [Delegated coordinator tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_coordinator.py) and [PostgreSQL delegated-artifact receipt](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py)
- **Law:** [Vision](./adr/36-vision.md)

## Evolution and federation {#evolution-and-federation}

### Archive intake and semantic memory {#karma-semantic-memory}

**State:** Designed

**Proved now:** Memory law defines authoritative Archive records, lineage, lifecycle, derived
representations, namespaces, and correction boundaries.

**Do not expect yet:** There is no `CandidateArchivePort`, intake adapter, runtime wiring,
PostgreSQL Archive adapter, semantic ingestion, embedding or retrieval, curation, promotion, RAG,
or training loop.

**Evidence**

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
collapse.

**Do not expect yet:** There is no runnable branch graph, MCTS engine, branch store, budgeted
simulation, collapse implementation, or reaper.

**Evidence**

- **Topic:** [Shadow](./sepulcher/extensions/shadow/index.md)
- **Law:** [Simulation](./adr/31-simulation.md)

### Riddle evaluation {#riddle-evaluation}

**State:** Designed

**Proved now:** Evaluation law defines adversarial evidence, capability comparison, and
calibration.

**Do not expect yet:** There is no runnable harness, maintained suite, scorer contract, benchmark
history, pass-at-k experiment, or routing update.

**Evidence**

- **Topic:** [Riddle](./sepulcher/extensions/riddle/index.md)
- **Law:** [Evaluation](./adr/34-evaluation.md)

### Soulforge training {#soulforge-training}

**State:** Designed

**Proved now:** Training law defines how consecrated examples may enter governed training.

**Do not expect yet:** There is no dataset harvest, training job, isolated trainer, checkpoint
evaluation, model registration, rollback, or production promotion.

**Evidence**

- **Topic:** [Soulforge](./sepulcher/extensions/soulforge/index.md)
- **Law:** [Training](./adr/33-training.md)

### Creation and Forge promotion {#smith-forge-promotion}

**State:** Designed

**Proved now:** Creation law defines an attributable request → candidate → verification →
promotion-request → target-owner-effect chain.

**Do not expect yet:** There is no Creation contract or process-local state-machine implementation,
workspace, filesystem or command executor, database recovery, safe Forge, autonomous repair,
target-owner promotion effect, rollback execution, or self-extension runtime. There is likewise no
instantiated distributed repository identity or maintainer roster, executable key-custody and
rotation mechanism, governance-epoch ledger, quorum verifier, signed portable promotion envelope,
independent attestation plane, canonical source on Radicle, Radicle node topology, or
downstream-mirror cutover.

**Evidence**

- **Topic:** [Smith](./sepulcher/extensions/smith.md)
- **Law:** [Creation](./adr/16-creation.md),
  [Packaging](./adr/17-packaging.md#forge-neutral-source-trust), and
  [Evolution](./adr/18-evolution.md#future-quorum-roster)

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

**Proved now:** Toll law separates local MANA accounting, external payment negotiation and
settlement, and future price discovery through dispatch without requiring x402 or a global asset.

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
- **Law:** [Legion](./adr/42-legion.md)

### VPN Tether {#vpn-tether}

**State:** Designed

**Proved now:** VPN law defines Tether as private reachability over WireGuard without application
authority, with exact peer and route intent and separate lifecycle ownership.

**Do not expect yet:** There is no Tether Domain contract, Rune or provider, generated service, UDP
publication, interface or enrollment effect, peer/key custody, live route policy, health,
reconciliation, revocation effect, or identity proof.

**Evidence**

- **Topic:** [Tether](./sepulcher/extensions/tether.md)
- **Law:** [VPN](./adr/39-vpn.md)

### Proxy Veil {#proxy-veil}

**State:** Designed

**Proved now:** Proxy law assigns edge proxy and TLS composition to Veil.

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
