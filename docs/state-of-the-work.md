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
behavior, deployment planning, local runs and one-round consent, the current agent and dispatch
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

**State:** Available

**Proved now:** The `init`, `destroy`, `bind`, and `doctor` commands have focused repository tests
for their current orchestration and failure behavior. Initialization and destruction expose
side-effect-free dry runs over their execution planners. `destroy` removes only inactive exact
Scribe-owned bindings plus unchanged files and empty directories recorded as created by `init`;
foreign, pre-existing, mounted, durable-data, model, and secret state remains outside its deletion
authority. Real `init`, `bind`, and `destroy` serialize their effect boundary; binding generations
and init-created path identities are revalidated before removal.

**Boundary:** `animators` has command-registration coverage but no focused inspection test; the
end-to-end CLI placeholder contains no tests. Destruction refuses active or enabled units and
modified or unsafe recorded state; it is not package uninstallation and has no purge mode. No real
host, systemd/Podman lifecycle, or GPU execution is claimed here.

**Evidence**

- **Source:** [CLI command implementations](https://github.com/hexanomicon/lychd/blob/main/src/lychd/cli/commands.py)
  and [lifecycle planning and ownership](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/lifecycle/__init__.py)
- **Verification:** [Focused CLI command tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/cli/test_cli.py)
  and [lifecycle safety and round-trip tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_lifecycle.py)
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

**Proved now:** LychD can compile Soulstone and extension intent into validated Quadlet/systemd
plans and materialize the declared files through the Scribe boundary.

**Boundary:** Generated unit intent is not evidence that systemd or Podman started the workload on
a real host.

**Evidence**

- **Source:** [Deployment transmutation](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/transmute.py)
  and [Scribe materialization](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/scribe.py)
- **Verification:** [Transmutation contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute.py),
  [extension contribution contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/animation/test_transmute_contributor.py),
  and [Scribe rendering tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_scribe_render.py)
- **Law:** [ADR 08 — Containers](./adr/08-containers.md),
  [ADR 10 — Privilege](./adr/10-privilege.md), and
  [ADR 12 — Configuration](./adr/12-configuration.md)

### Mediated Host Reactor protocol {#host-reactor-protocol}

**State:** Available

**Proved now:** The software protocol covers inbox claim, validation, exact-prefix recovery,
cancellation/startup fences, terminal journaling, and readiness inversion.

**Boundary:** This is protocol evidence, not a real-host receipt. Arbitrary non-prefix physical
repair remains outside the contract.

**Evidence**

- **Source:** [Host Reactor](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/reactor.py)
  and [runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py)
- **Verification:** [Reactor recovery tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_reactor.py)
  and [runtime action tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py)
- **Law:** [ADR 10 — Privilege](./adr/10-privilege.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### systemd user and rootless Podman embodiment {#systemd-podman-embodiment}

**State:** Operator validation

**Proved now:** LychD has a generated unit contract and a mediated host actuator for its declared
Linux deployment shape.

**Receipt needed:** A maintained receipt naming Linux distribution and kernel, systemd and Podman
versions, generated units, startup result, and shutdown/recovery result. GPU and model validation
remain separate receipts.

**Evidence**

- **Source:** [Runtime actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/runtime.py)
- **Verification:** [Runtime protocol tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_runtime.py)
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
  [checkpoint adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/checkpoints.py),
  and [run ledger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/ledger.py)
- **Verification:** [Run-ledger contracts](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_ledger.py),
  [skipped PostgreSQL run-ledger receipt gap](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_db_run_ledger_pg.py),
  and [production-factory receipt gap](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_production_wiring.py)
- **Law:** [ADR 06 — Persistence](./adr/06-persistence.md)

### Topology-A local run execution {#topology-a-local-runs}

**State:** Available

**Proved now:** One Vessel process can admit, claim, execute, cancel, settle, and project live run
events with replay fencing inside the repository-test envelope.

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
  [ADR 24 — Graph](./adr/24-graph.md), and [ADR 28 — Workflow](./adr/28-workflow.md)

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

**Proved now:** Focused tests cover logical parking, one approval round, memory-profile simulated
restart, reconciliation, idempotent settlement, and graph re-admission.

**Boundary — Not yet:** This is not a Postgres Consent-plus-Checkpoint restart receipt. Multiple
approval calls in one model round remain unsupported; after verdict commit plus enqueue failure,
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

- **Source:** [Bridge consent projection](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py)
  and [consent sigil template](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/templates/altar/partials/consent_sigil.html.j2)
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

### Safe runtime transitions {#safe-runtime-transitions}

**State:** Available

**Proved now:** Admission closure, lease drain, serialized transition plans, readiness convergence,
typed hard-transition compensation, and fail-closed containment have focused software-protocol
tests.

**Boundary:** This does not prove a swap on a real GPU and does not claim capacity-optimal model
selection. A failed soft in-runtime model load has no trustworthy rollback and requires contained
operator recovery.

**Evidence**

- **Source:** [Orchestrator manager](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/manager.py),
  [actuator](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/actuator.py),
  and [arbiter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/arbiter.py)
- **Verification:** [Manager transition tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_manager.py),
  [actuator tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_actuator.py),
  [arbiter serialization tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_arbiter.py),
  and [orchestration integration tests](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_orchestrator.py)
- **Law:** [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Resource-aware VRAM and topology scheduling {#resource-aware-scheduling}

**State:** Designed

**Proved now:** ADR 23 provides a policy seam, and the current `EvictIdlePolicy` has deterministic
tests for its deliberately simple behavior.

**Do not expect yet:** The policy evicts all active dedicated non-residents for a cold target and
prices only their count. It does not know VRAM capacity, model footprint, load time, topology,
bandwidth, LRU, refit profiles, tier substitution, or transition peaks. `persistent_resident` is
not capacity admission.

**Evidence**

- **Source:** [Current eviction policy](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/policies.py),
  [transition schema](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/orchestration/schema.py),
  and [concurrency intent](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/schemas/concurrency.py)
- **Verification:** [Current policy tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/orchestration/test_policies.py)
  and [current matrix behavior](https://github.com/hexanomicon/lychd/blob/main/tests/integration/test_matrix_solver.py)
- **Law:** [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

## Altar and observability {#altar-and-observability}

### Bridge conversation and consent surface {#bridge-surface}

**State:** Partial

**Proved now:** Bridge supports local sessions, message submission, pending consent cards and
decisions, inspection, and process-local event streaming with focused web tests.

**Boundary — Not yet:** There is no complete production-factory receipt, durable cross-process
event delivery, general multi-approval round, Attention contract, or external notification channel.

**Evidence**

- **Source:** [Bridge controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/bridge.py)
  and [Bridge templates](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/web/templates/bridge)
- **Verification:** [Bridge behavior tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_bridge.py),
  [consent endpoint tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_consent_endpoint.py),
  and [event-stream tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_sse.py)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 25 — Human in the Loop](./adr/25-hitl.md)

### Nexus transition board {#nexus-transition-board}

**State:** Partial

**Proved now:** Nexus renders Coven state, transition plans, swap tickets, and settled outcomes
through concrete HTMX and JSON controller paths.

**Boundary — Not yet:** It has no general resource truth. Tickets wrap process-local tasks without
a durable owner, created/settled times, retention deadline, or abandoned-completion cleanup law;
the production lifespan also lacks a receipt.

**Evidence**

- **Source:** [Nexus controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/nexus.py)
  and [process-local ticket store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/tickets.py)
- **Verification:** [Nexus board and ticket tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_nexus.py)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 23 — Orchestrator](./adr/23-orchestrator.md)

### Loom workflow instrument {#loom-workflow-views}

**State:** Partial

**Proved now:** Loom renders registered workflow diagrams and plain-text Mermaid source through
full-page and HTMX routes.

**Boundary — Not yet:** It is a view over the fixed workflow registry, not a general Weaver editor,
workflow mutation surface, or production-lifespan receipt.

**Evidence**

- **Source:** [Loom controller](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/loom.py)
  and [workflow registry contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py)
- **Verification:** [Loom rendering tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_loom.py)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 28 — Workflow](./adr/28-workflow.md)

### Scrying instrument {#scrying-instrument}

**State:** Designed

**Proved now:** The Altar exposes an honestly marked Scrying route and shell.

**Do not expect yet:** The route renders an unbuilt skeleton; there is no useful trace query,
timeline, health read model, or native observability backend.

**Evidence**

- **Source:** [Altar shell routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py)
- **Verification:** [Unbuilt-instrument presentation tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
- **Topic:** [Scrying](./divination/altar/scrying.md)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md) and
  [ADR 29 — Observability](./adr/29-observability.md)

### Reliquary instrument {#reliquary-instrument}

**State:** Designed

**Proved now:** The Altar exposes an honestly marked Reliquary route and shell.

**Do not expect yet:** The route renders an unbuilt skeleton; there is no artifact upload, byte
custody, authorized retrieval, retention, or provenance backend.

**Evidence**

- **Source:** [Altar shell routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py)
- **Verification:** [Unbuilt-instrument presentation tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
- **Topic:** [Reliquary](./divination/altar/reliquary.md)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md)

### Bindings instrument {#bindings-instrument}

**State:** Designed

**Proved now:** The Altar exposes an honestly marked Bindings route and shell.

**Do not expect yet:** The route renders an unbuilt skeleton; there is no useful binding inventory,
grant control, lease control, or mutation backend.

**Evidence**

- **Source:** [Altar shell routes](https://github.com/hexanomicon/lychd/blob/main/src/lychd/interface/web/altar.py)
- **Verification:** [Unbuilt-instrument presentation tests](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_pages.py)
- **Topic:** [Bindings](./divination/altar/bindings.md)
- **Law:** [ADR 15 — Frontend](./adr/15-frontend.md)

### Structured logging configuration {#structured-logging}

**State:** Available

**Proved now:** The shared logging builder and direct bootstrap helper produce tested human-readable
and JSON stdlib/Structlog output.

**Boundary:** The CLI bootstrap does not currently invoke `apply_logging`; this record does not
prove CLI-wide or application-lifespan logging composition. It also does not prove trace storage,
OpenTelemetry export, capture-class redaction, retention, resource correlation, or Oculus.

**Evidence**

- **Source:** [Logging configuration and bootstrap helper](https://github.com/hexanomicon/lychd/blob/main/src/lychd/config/logging.py)
- **Verification:** [Logging configuration and output tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/config/test_logging.py)
- **Law:** [ADR 29 — Observability](./adr/29-observability.md)

### Native Oculus {#native-oculus}

**State:** Designed

**Proved now:** The observability law makes LychD's own evidence model and Altar surface canonical;
a telemetry class has a narrow direct unit test.

**Do not expect yet:** The telemetry class is not installed by current application or extension
composition. There is no native ingestion, durable query/read model, retention path, or HTMX
Scrying view.

**Evidence**

- **Source:** [Telemetry class](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/telemetry.py),
  [observability registration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/observability/register.py),
  and [current application assembly](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py)
- **Verification:** [Narrow telemetry capture test](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_telemetry.py)
- **Topic:** [Oculus](./sepulcher/extensions/oculus.md)
- **Law:** [ADR 29 — Observability](./adr/29-observability.md)

### Phoenix {#phoenix-eye}

**State:** External

**Proved now:** LychD can generate an optional Phoenix service contribution as a legacy
interoperability surface.

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
and the production application composes Litestar CSRF protection.

**Boundary — Not yet:** The hostile-browser contract fails. Production configuration permits
wildcard CORS, does not constrain the Host authority, and stamps ordinary requests with the fixed
`magus:*` bootstrap Sigil rather than authenticating a caller. Foreground `lychd serve` arguments
or environment can bypass the typed loopback host setting, while `/schema/scalar` loads mutable CDN
assets into the local browser origin. CSRF remains a useful unsafe-method layer, but it does not
protect GET or SSE confidentiality or stop DNS rebinding. Remote, proxied, tunneled,
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

**Proved now:** ADR 42 names the multi-node jurisdiction and the distinction between a cognitive
Master and resource-bearing nodes.

**Do not expect yet:** There is no node enrollment, expiring advertisement, local resource
reservation, fencing, artifact transfer, durable spool, cancellation, or settlement. ADR 42's
shared-Postgres and universal-Master-Sigil design must be replaced before implementation.

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
