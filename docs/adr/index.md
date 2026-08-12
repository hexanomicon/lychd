---
title: Covenants
icon: material/pillar
---

# :material-pillar: Architecture Decision Records (Covenants)

> _Prophecy names the destination. A Covenant decides what may be built._

The Covenants are LychD's technical law. Each one owns a decision, the forces that shaped it, and
the invariants that later work must preserve. They are living contracts: the current text states
the current architecture, while version history records how that law changed.

Use this page to find the smallest decision that owns a question. Follow related Covenants only
where the boundary crosses more than one office.

[State of Work](../state-of-the-work.md) answers a different question: what current evidence
supports. An accepted Covenant can govern an organ that has not yet entered matter.

## The Return from Myth to Law

The Great Work supplies constitutional pressure, never technical proof. Its images return through
engineering invariants that can be implemented, tested, refused, and repaired:

| Constitutional pressure | Engineering return | Owning Covenants |
| --- | --- | --- |
| A boundary creates perspective without claiming the whole | explicit scope, isolation, and least authority | [Security](09-security.md), [Layout](13-layout.md), [IAM](38-iam.md) |
| A name makes an act answerable | stable identity, attribution, and consequence | [Graph](24-graph.md), [Identity](32-identity.md) |
| Memory must remain corrigible | provenance, retention, correction, and recovery | [Persistence](06-persistence.md), [Memory](27-memory.md) |
| Imagination cannot write reality by itself | isolated simulation and an explicit promotion gate | [HitL](25-hitl.md), [Simulation](31-simulation.md) |
| Another center remains real | consent, refusal, revocation, and bounded delegation | [HitL](25-hitl.md), [IAM](38-iam.md), [A2A](26-a2a.md) |
| Coherence must not require one planetary throne | operator-controlled runtimes, node-local refusal, and bounded federation | [Containers](08-containers.md), [Orchestrator](23-orchestrator.md), [A2A](26-a2a.md), [Legion](42-legion.md) |
| A changed form does not erase its source | privacy lineage, local transformation, and exact declassification | [Security](09-security.md), [Persistence](06-persistence.md), [Context](21-context.md) |
| Power must meet consequence | correlated evidence and adversarial evaluation | [Observability](29-observability.md), [Evaluation](34-evaluation.md) |
| Repair may change the vessel | versioned creation, rollback, evolution, and promotion | [Creation](16-creation.md), [Evolution](18-evolution.md), [Assimilation](35-assimilation.md) |

The full cosmology lives in [Transcendence](../divination/transcendence/index.md). A Covenant may
name the telos it serves, but its decision must stand on technical requirements and consequences.

## Foundation and Governance

| Question | Covenant |
| --- | --- |
| Which reciprocal boundary and contribution terms govern covered code and separate work? | [00 — License](00-license.md) |
| How do lore, evidence, code, and the current documentation topology govern one another? | [01 — Philosophy](01-doctrine.md) |
| Which historical stack and register discipline formed the Hexanomicon? | [02 — Documentation](02-documentation.md) |
| Which tools and gates define repository quality? | [03 — Quality](03-quality.md) |
| Which tests prove which kinds of behavior? | [04 — Testing](04-testing.md) |
| How may native and external organs extend the body? | [05 — Extensions](05-extensions.md) |

## Body, Host, and Runtime

| Question | Covenant |
| --- | --- |
| Where does committed state live? | [06 — Persistence](06-persistence.md) |
| What must a recoverable snapshot bind together? | [07 — Snapshots](07-snapshots.md) |
| How are rootless service bodies manifested? | [08 — Containers](08-containers.md) |
| Which trust boundaries protect the host, data, and network? | [09 — Security](09-security.md) |
| How are privileged effects proposed, authorized, and recovered? | [10 — Privilege](10-privilege.md) |
| Which application architecture governs the Vessel? | [11 — Backend](11-backend.md) |
| How are Settings and Runes loaded, composed, and validated? | [12 — Configuration](12-configuration.md) |
| Which paths does LychD own, preserve, or refuse to delete? | [13 — Layout](13-layout.md) |
| How are durable jobs executed and recovered? | [14 — Workers](14-workers.md) |
| Which browser architecture and transport boundary govern the Altar? | [15 — Frontend](15-frontend.md) |
| How does a candidate organ move from Lab to promoted matter? | [16 — Creation](16-creation.md) |
| How are source, packages, images, and receipts bound into a release? | [17 — Packaging](17-packaging.md) |
| How may the body alter itself without severing recovery? | [18 — Evolution](18-evolution.md) |
| Which command grammar and destructive safeguards govern the Pulse? | [19 — CLI](19-cli.md) |

## Agency, Memory, and Consequence

| Question | Covenant |
| --- | --- |
| What is an Agent and how is its capability assembled? | [20 — Agents](20-agents.md) |
| How is bounded Context assembled and governed? | [21 — Context](21-context.md) |
| How are capability demand, state, and grants resolved? | [22 — Dispatcher](22-dispatcher.md) |
| How are physical readiness and scarce resources converged? | [23 — Orchestrator](23-orchestrator.md) |
| How do graphs checkpoint, pause, resume, and delegate? | [24 — Graph](24-graph.md) |
| How does human consent survive pause and re-admission? | [25 — HitL](25-hitl.md) |
| How may sovereign Liches address one another? | [26 — A2A](26-a2a.md) |
| How are Seeds admitted, retrieved, corrected, and reanimated? | [27 — Memory](27-memory.md) |
| How do Products package Compositions, how are Spells woven into immutable Scrolls and attributable castings, and how do human-attested regions stop for live review? | [28 — Workflow](28-workflow.md) |
| Which evidence makes an execution legible without granting authority? | [29 — Observability](29-observability.md) |
| How are search, fetch, render, and extraction effects contained? | [30 — Webcrawler](30-webcrawler.md) |
| How are speculative worlds isolated, judged, and promoted? | [31 — Simulation](31-simulation.md) |
| How are Persona, Sigil, attribution, and revision bound? | [32 — Identity](32-identity.md) |
| How are training corpora admitted and resulting weights promoted? | [33 — Training](33-training.md) |
| How are capabilities tried, calibrated, and compared? | [34 — Evaluation](34-evaluation.md) |
| How does foreign craft pass through Lab, test, and promotion? | [35 — Assimilation](35-assimilation.md) |

## Senses, Network, and Federation

| Question | Covenant |
| --- | --- |
| How are visual artifacts transformed with provenance intact? | [36 — Vision](36-vision.md) |
| How are speech and audio transported, retained, and interrupted? | [37 — Audio](37-audio.md) |
| How do Sigils, roles, grants, and revocation enforce identity? | [38 — IAM](38-iam.md) |
| How does the Tether admit remote peers and routes? | [39 — VPN](39-vpn.md) |
| How does the Veil terminate transport without becoming application authority? | [40 — Proxy](40-proxy.md) |
| How are paid effects reserved, signed, committed, and reconciled? | [41 — X402](41-x402.md) |
| How may many physical nodes serve one sovereign control plane? | [42 — Legion](42-legion.md) |

## Changing a Covenant

The numbered Covenant register is closed at **42**. New architecture amends or rewrites the
smallest existing Covenant that owns the decision; it does not add another Covenant number.
Version history keeps displaced law legible when a decision is reversed.

Every change preserves three seams:

1. **Law:** the Covenant states the decision and its invariants.
2. **Operation:** the owning Sepulcher, Altar, or Composition page shows how that law is used.
3. **Evidence:** State and its linked source, tests, lockfiles, or receipts show what has entered
   matter.

Authoring mechanics and verification commands belong in
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#implementation-conventions).
