---
title: State of Work
icon: material/list-status
---

# State of Work

LychD is **pre-alpha**. This is the canonical revision-wide delivery index: architecture lives in
the Covenants, operation in topic pages, application design in the Composition Portfolio, and
executable proof in tracked source, tests, lockfiles, and maintained receipts.

The proved envelope is local, loopback-oriented, single-user, and one control process in the
repository-test profile. A disposable PostgreSQL receipt covers the real application factory,
in-process SAQ, one Bridge Run, shutdown, and a second boot. It does not prove a real
systemd/Podman/GPU/model/browser conjunction, remote use, or multi-tenancy.

## Outcome matrix

| Scenario | Answer now | Decisive limit |
| --- | --- | --- |
| CLI bootstrap | **Partial:** grammar, dry-run plans, transactional `init`/`bind`, bounded inspection, and guarded deletion have repository evidence. | No maintained real-host lifecycle receipt. See [CLI](#core-cli-rites) and [embodiment](#systemd-podman-embodiment). |
| Local text chat | **Partial:** the Pydantic AI adapter, local Run engine, and Bridge contracts work in the repository-test envelope. | No inference-engine plus real-browser acceptance receipt. See [Bridge](#bridge-surface) and [persistence](#phylactery-first-light). |
| Browser safety | **Loopback only:** Host, CORS, CSRF, and generated bind policy are bounded locally. | The bootstrap Sigil is not authentication; remote and untrusted-browser use remain unsupported. |
| PostgreSQL lifecycle | **Repository receipt:** factory, PostgreSQL, SAQ, HTTP, shutdown, and second-boot projection recovery run together. | Live dispatch, orchestration, and Context are replaced after startup; no real-host or browser proof. |
| Major blockers | Authenticated caller authority, privacy-safe egress, artifact custody, real host/model receipts, native Oculus, and resource-aware scheduling. | Remote transport, federation, executable evolution, durable recall, and vision/audio bytes remain Partial or Designed. |

## How to read this page

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

### Rune configuration loading {#rune-configuration-loading}

**State:** Available

**Proved now:** Typed TOML Runes load from their declared hierarchy with validated, immutable
filesystem provenance.

**Boundary:** Configuration parsing and topology do not prove a CLI rite, generated host unit, or
running service.

**Evidence**

- **Source:** [Rune loader](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/runes/loader.py)
- **Verification:** [Rune tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/runes/test_loader.py)
- **Law:** [Configuration](./adr/12-configuration.md)

### Core CLI rites {#core-cli-rites}

**State:** Partial

**Proved now:** The closed command grammar, dry-run planners, journaled `init` and `bind`,
bounded `status` and `logs`, guarded lifecycle control, run discovery, and receipt-gated deletion
are tested. Mutating paths use revalidation, no-follow identity checks, lifecycle locking, durable
receipts, and explicit rollback or indeterminate outcomes.

**Boundary — Not yet:** Status omits full readiness and durable-run health; `run` cannot submit
without an authenticated Vessel route; `stop` refuses an active Vessel without its authenticated
lifecycle port; deletion preserves objects whose creation provenance is not owned. Unknown unit or
mount truth blocks instead of guessing. No maintained real systemd/Podman lifecycle or GPU receipt
exists.

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
materializes the declared files.

**Boundary:** Generated unit intent does not prove that systemd or Podman started it on a real host.

**Evidence**

- **Source:** [Deployment transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py)
- **Verification:** [Transmutation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute.py)
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
with sequence-fenced claim and settlement, owner-specific resume gates, startup reconciliation, and
PostgreSQL migration checks. A real factory receipt completes and recovers a Bridge Run across two
boots.

**Boundary — Not yet:** PostgreSQL and SAQ are not one transaction; Step events lack an outbox;
adapter parity is incomplete; persistent same-boot containment failure has no durable watchdog. The
lifecycle receipt substitutes offline collaborators and is not a checkpoint-plus-consent,
real-host, inference-engine, or browser receipt.

**Evidence**

- **Source:** [First-light migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0001_phylactery_first_light.py) and [wait-owner migration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/migrations/versions/0008_wait_owner_evidence.py)
- **Verification:** [Run ledger tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py) and [two-boot lifecycle](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [Persistence](./adr/06-persistence.md)

### Topology-A local run execution {#topology-a-local-runs}

**State:** Available

**Proved now:** One Vessel process admits, claims, executes, cancels, settles, resumes, and projects
Runs against immutable Pattern revisions. Durable publication intent, replay repair, external-wait
relays, terminal-evidence repair, bounded identity fencing, and orderly shutdown are tested.
Unresolved child containment stays nonterminal rather than claiming false `FAILED` truth; a timed-
out cancellation remains `CANCELLING`.

**Boundary:** This does not prove automatic source compatibility, a transactional event outbox,
separate-worker truth, multi-process streaming, federation, or governed subscriber backpressure.

**Evidence**

- **Source:** [Run engine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/engine.py)
- **Verification:** [Run engine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_engine.py)
- **Law:** [Workers](./adr/14-workers.md)

### Pydantic AI 1.25.1 cognitive adapter {#pydantic-ai-v1-adapter}

**State:** Available

**Proved now:** LychD constructs typed agents and runs Bridge through the exact
`pydantic-ai-slim==1.25.1` contract with serializable state and fail-closed provider profiles.

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
1.25.1.

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

**Boundary — Not yet:** There is no PostgreSQL Consent-plus-Checkpoint restart receipt. Multiple
approval calls in one model response are rejected, and no production toolset currently originates
approval.

**Evidence**

- **Source:** [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py)
- **Verification:** [Consent resume tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_consent_resume.py)
- **Law:** [Human in the Loop](./adr/25-hitl.md)

### Delegated agent execution {#delegated-agent-execution}

**State:** Partial

**Proved now:** Typed secret-free requests, artifact references, process-local job
submission/adoption/cancellation, exact wait ownership, Graph parking and re-admission, policy-only
Coffin/Gate admission, PostgreSQL shapes, and a no-effect reference adapter exist.

**Boundary — Not yet:** No declared external provider launches. There is no lower-trust executor,
credential or egress isolation, process-tree containment, durable artifact custody, measured
budgets, real PostgreSQL/provider recovery receipt, or live-browser proof.

**Evidence**

- **Source:** [Delegated job store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/delegation.py), [Graph runner](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/graph_runner.py), and [reference adapter catalogue](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/register.py)
- **Verification:** [Delegation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/delegation/test_coordinator.py), [delegate stasis tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_delegate_stasis.py), and [extension-policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py)
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

**Proved now:** Catalog hydration, matching, probe publication, grant issue and settlement, and
lease-aware dispatch are tested with duplicate attribution, snapshot isolation, cancellation
invalidation, and strict loopback Soulstone endpoint policy. Every issue re-probes the exact chosen
record rather than trusting cached warmth. Fixed OpenAI-compatible local and opt-in Portal probes
validate `/models` inventory and warm only an exact returned model id; malformed or missing
inventory fails closed, and inventory count and id length are bounded before retention. A
`served_model_id` Rune field pins the provider-facing identity when it differs from a path or
Soulstone name. The v1 grant exposes no Animator or Connector: `chat` admits a hydrated model and
only declared agent-loop toolsets, `tool_execution` requires a non-empty toolset, and all
metadata-only families fail closed. Registry-level Portal issue is quarantined as well as both
Dispatcher entry points.

**Boundary:** This is the v1 `{animator}:{family}:{model_id}` catalogue with one chat-model/toolset
compatibility grant, not the general discriminated grant union. Registry ownership remains broad;
lease expiry is recorded but not enforced; current Soulstone/Portal inheritance and raw Quadlet
contribution remain. General interface/profile compilation, call/job/session grants,
`[[capabilities]]`, service-job attempts, per-dialect OpenAI-compatible drivers, and secret-vault
integration are not delivered.

**Evidence**

- **Source:** [Animator registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/registry.py),
  [Soulstone Rune schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/runes/animators.py),
  [OpenAI-compatible probe](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/shared.py),
  and [fixed-runtime projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/adapters/runtimes/openai_compat.py)
- **Verification:** [Registry tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_registry.py),
  [runtime adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py),
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

**Proved now:** Dependency-first built-in assembly supplies Rune, Portal, runtime, Quadlet,
delegation, and Run-operation contributions under provider-bound registration, sealed membership,
owned schema branches, and fail-closed synchronous hooks.

**Boundary — Not yet:** Ownership is not projected into every live capability view. Package
installation, locks, upgrade/uninstall, migrations, lifecycle effects, Forge admission, and a stable
public SDK are absent.

**Evidence**

- **Source:** [Extension manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/manager.py)
- **Verification:** [Extension tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_catalog.py)
- **Law:** [Extensions](./adr/05-extensions.md)

### llama.cpp integration {#llamacpp-integration}

**State:** Operator validation

**Proved now:** Runtime planning, static and router connectors, discovery, capability derivation,
load/unload control, and contract tests exist.

**Receipt needed:** Name the image and revision, model and quantization, GPU and driver, flags,
systemd/Podman host, load, inference, and unload results.

**Evidence**

- **Source:** [llama.cpp adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/llamacpp.py)
- **Verification:** [Adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### vLLM integration {#vllm-integration}

**State:** Operator validation

**Proved now:** A vLLM runtime plan, OpenAI-compatible connector, model/capability derivation, and
focused tests exist.

**Receipt needed:** Name the image and revision, model, GPU and driver, arguments, systemd/Podman
host, readiness, inference, and shutdown.

**Evidence**

- **Source:** [vLLM adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/vllm.py)
- **Verification:** [Adapter tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_adapters.py)
- **Law:** [Dispatcher](./adr/22-dispatcher.md)

### SGLang integration {#sglang-integration}

**State:** Operator validation

**Proved now:** An SGLang runtime plan, OpenAI-compatible connector, model derivation, and focused
tests exist.

**Receipt needed:** Name the image and revision, model, GPU and driver, arguments, systemd/Podman
host, readiness, inference, and shutdown.

**Evidence**

- **Source:** [SGLang adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/animator/runtimes/sglang.py)
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
topology are covered by focused protocol tests.

**Boundary — Not yet:** Dynamic shared-capacity admission, durable multi-process orchestration,
general repair, and a maintained real model/GPU transition receipt are absent. A failed soft
model-load has no trustworthy rollback and requires contained operator recovery; `.contained` and
unresolved `.processing` fence later work.

**Evidence**

- **Source:** [Orchestrator manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/manager.py)
- **Verification:** [Transition tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_manager.py)
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
production-factory browser receipt.

### Bridge conversation and consent surface {#bridge-surface}

**State:** Partial

**Proved now:** Bridge supports typed sessions, text admission, consent, inspection, semantic SSE,
closed GenUI descriptors, durable request identity, authoritative snapshot recovery, lifecycle
fencing, and bounded reconstruction against server-owned Run and Pattern identities. Its per-turn
run strip is the first thin projection of one Invocation's Circle.

**Boundary — Not yet:** There is no real-browser receipt, durable cross-process event/token
delivery, general multi-approval, Attention, or notification channel. Text is the only command
modality, warm Environment caching lacks a changing grant epoch, and no focused Circle workspace
composes Scroll, active Spell placement, Context/authority, capability, and evidence projections.

**Evidence**

- **Source:** [Bridge controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py)
- **Verification:** [Bridge tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge.py)
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
and retained revisions with stale-response-fenced client loading.

**Boundary — Not yet:** Loom is a view over the fixed registry, not a Spellweaver editor, mutation
surface, independent Spell identity or catalogue, compatibility or teaching surface, drafting
canvas, inert unresolved-Spell projection, Suite executor, or production-browser receipt.

**Evidence**

- **Source:** [Loom controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/loom.py), [Pattern registry contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py), and [Loom client](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/LoomView.svelte)
- **Verification:** [Loom tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_loom.py) and [client lifecycle tests](https://github.com/hexanomicon/lychd/blob/main/frontend/src/lib/components/LoomView.test.ts)
- **Law:** [Workflow](./adr/28-workflow.md)

### Composition Portfolio {#composition-portfolio-delivery}

**State:** Designed

**Proved now:** The Portfolio publishes Native Reference Composition contracts and examples; the
boot catalogue contains only `bridge_chat@1` and `delegated_rite@1`.

**Do not expect yet:** There is no Composition store or selector, Portfolio Pattern registration,
Suite execution, application scheduling, or delivered domain/effect path for any Portfolio member.

**Evidence**

- **Source:** [Workflow registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py)
- **Verification:** [Workflow routing tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_router.py)
- **Topic:** [Composition Portfolio](./compositions/index.md)
- **Law:** [Workflow](./adr/28-workflow.md)

### Orb instrument {#orb-instrument}

**State:** Partial

**Proved now:** Orb renders one Run as ordered, paginated evidence with Pattern revision, capture
durability, ledger boundaries, gaps, transition links, stable selection, and bounded retry.

**Boundary — Not yet:** There is no run list, live tail, graph field, durable Oculus read model,
cross-process completeness, health query, artifact custody, annotation, or multi-run view.

**Evidence**

- **Source:** [Orb controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/orb.py)
- **Verification:** [Orb tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_orb.py)
- **Law:** [Observability](./adr/29-observability.md)

### Structured logging configuration {#structured-logging}

**State:** Available

**Proved now:** One tested builder configures human and JSON stdlib/Structlog output for CLI and
Litestar while preserving stdout/stderr semantics and recovery-command fallback.

**Boundary:** Shared configuration does not prove complete semantic audit coverage, trace storage,
OpenTelemetry export, redaction, retention, resource correlation, or Oculus.

**Evidence**

- **Source:** [Logging configuration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/logging.py)
- **Verification:** [Logging tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_logging.py)
- **Law:** [Observability](./adr/29-observability.md)

### Native Oculus {#native-oculus}

**State:** Designed

**Proved now:** Observability law makes LychD's evidence model canonical; a dormant Phoenix export
adapter has narrow tests but is not composed.

**Do not expect yet:** There is no native ingestion, durable query/read model, retention path, or
Oculus-backed Svelte service. Orb is a bounded Run projection, not Oculus.

**Evidence**

- **Source:** [Dormant telemetry adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/telemetry.py)
- **Verification:** [Telemetry tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_telemetry.py)
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

**State:** Partial

**Proved now:** Context labels, local Privacy Cut semantics, separate transformation and
declassification authority, a deterministic local redactor with lineage evidence, and fail-closed
Portal dispatch exist.

**Boundary — Not yet:** Not every producer supplies governed lineage; redaction evidence is not
declassification or a sanitized Context branch. There is no semantic Privacy Agent, verified
Privacy Cut, Egress Gate, pseudonym map, transmission check, or deletion propagation.

**Evidence**

- **Source:** [Privacy contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/privacy.py)
- **Verification:** [Privacy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_privacy.py)
- **Law:** [Security](./adr/09-security.md)

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

**Proved now:** Generated ports and uncaged service policy bind IPv4 loopback; launch, Host, CORS,
local schema assets, fixed root handlers, and CSRF contracts are bounded and tested.

**Boundary — Not yet:** Requests still receive the bootstrap Sigil. No hostile-browser receipt,
security-header contract, or remote principal exists; proxied, tunneled, non-loopback, and
untrusted-browser use remain unsupported.

**Evidence**

- **Source:** [Application composition](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py), [server policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/server_policy.py), and [fixed Altar routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py)
- **Verification:** [Network policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_golden.py), [HTTP boundary tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_http_boundary.py), and [Altar route tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
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
- **Law:** [Web Acquisition](./adr/30-webcrawler.md)

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

**Proved now:** Intent preserves an immutable artifact digest, classification, size, media type,
and required modality through the Run ledger.

**Boundary — Not yet:** `ArtifactRef` is not byte custody. There is no upload/store adapter,
principal-bound retrieval, materializer, derivation provenance, retention/deletion, provider fetch
audit, or Reliquary backend.

**Evidence**

- **Source:** [Artifact reference](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/router.py)
- **Verification:** [Artifact tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py)
- **Law:** [Vision](./adr/36-vision.md)

## Evolution and federation {#evolution-and-federation}

### Candidate Archive intake seam {#karma-semantic-memory}

**State:** Partial

**Proved now:** A process-local `CandidateArchivePort` admits attributed raw candidates and
derivatives with collision checks, lineage, anti-reingestion keys, monotonic retries, current-attempt
visibility, and stale-write fencing.

**Boundary — Not yet:** There is no runtime wiring, authorization, PostgreSQL adapter, semantic
ingestion, embeddings, retrieval, consecration, correction/retention policy, vector store, automatic
capture, RAG, promotion, or training loop.

**Evidence**

- **Source:** [Candidate Archive](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/memory/ports.py)
- **Verification:** [Archive tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/memory/test_archive.py)
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

### Inert Creation promotion envelope {#smith-forge-promotion}

**State:** Partial

**Proved now:** A process-local, effect-free Creation state machine binds source and tree digests,
paths, budgets, tools, network declaration, custody, deterministic verification, compatibility,
human review, chronology, and an idempotent inert promotion request.

**Boundary — Not yet:** There is no workspace, filesystem/command executor, database recovery,
safe forge, autonomous repair, target-owner promotion effect, rollback execution, or self-extension
runtime.

**Evidence**

- **Source:** [Creation contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/creation/contracts.py) and [state machine](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/creation/machine.py)
- **Verification:** [Creation contract tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/creation/test_contracts.py) and [state-machine tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/creation/test_machine.py)
- **Law:** [Creation](./adr/16-creation.md)

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

**State:** Partial

**Proved now:** A transport-neutral envelope, verified-admission evidence, local policy, bounded
value/artifact payload, sender replay fences, explicit lifecycle, first-terminal-wins adoption, and
a process-local ledger exist. Exact replay is inert; conflicting task, message, idempotency, or
nonce identity fails closed. This foundation performs no network or Run effect.

**Boundary — Not yet:** There is no peer/key custody, discovery, cryptographic verifier, transport,
durable inbox/outbox, callback or artifact fetch, Run/Graph bridge, restart recovery, effect receipt,
Spell compatibility/teaching negotiation, or interoperability profile.

**Evidence**

- **Source:** [Intercom contracts](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/intercom/models.py)
- **Verification:** [Intercom tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/intercom/test_services.py)
- **Law:** [Agent-to-Agent](./adr/26-a2a.md)

### x402 payments {#x402-payments}

**State:** Designed

**Proved now:** Payment law assigns negotiation and settlement to Toll and future price discovery
to dispatch.

**Do not expect yet:** There is no quote, reservation, authorization, signer, payment, settlement,
reconciliation, budget enforcement, or safe HTTP 402 response.

**Evidence**

- **Topic:** [Toll](./sepulcher/extensions/toll.md)
- **Law:** [x402](./adr/41-x402.md)

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

**State:** Partial

**Proved now:** Pure Domain contracts validate public interface and peer intent, secret references,
WireGuard public keys, endpoint grammar, peer/route uniqueness, active-route overlap, forward
revisions, and retained revocation tombstones. They perform no host or network effect.

**Boundary — Not yet:** There is no Tether Rune or provider, service generation, UDP publication,
interface/enrollment/key effects, live route policy, health, reconciliation, revocation effect, or
identity proof.

**Evidence**

- **Source:** [Tether intent](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/tether/models.py) and [reconciliation policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/tether/policy.py)
- **Verification:** [Tether intent tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/tether/test_models.py) and [reconciliation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/tether/test_policy.py)
- **Law:** [VPN](./adr/39-vpn.md)

### Proxy Veil {#proxy-veil}

**State:** Designed

**Proved now:** Proxy law assigns edge proxy and TLS composition to Veil.

**Do not expect yet:** There is no provider, certificate lifecycle, generated edge policy, remote
ingress hardening, or proof that a proxy substitutes for application authorization.

**Evidence**

- **Topic:** [Veil](./sepulcher/extensions/veil.md)
- **Law:** [Proxy](./adr/40-proxy.md)

## Human ruling queue

This page does not own a backlog. These unresolved choices remain hard gates until their owning
Covenant records a ruling:

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
