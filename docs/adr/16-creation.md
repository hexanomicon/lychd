---
title: 16. Creation
icon: material/creation
---

# :material-creation: 16. Creation

!!! abstract "Context and Problem Statement"
    Autopoiesis may eventually let LychD extend itself, but a candidate is not part of the body
    because a model wrote it or a check passed. Creation needs a route from proposal to a
    target-owned effect that keeps the active body, attribution, and recovery legible.

## Requirements

- Candidate writes must not alter the active source tree or running package.
- A candidate must bind its base revision, patch or artifact digest, principal, tools and
  dependency inputs, declared effects, and resource budget.
- A workspace is not a sandbox: processes, network, credentials, databases, and host effects need
  separately admitted boundaries.
- Commands, versions, environment, result, and error class must be retained as verification
  receipts.
- The eventual target owner—not the creator—must recheck current state, authority, evidence, and
  recovery at promotion time.
- Lineage and terminal disposition must remain attributable, so interrupted work can resume or be
  discarded without touching the live body.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Live hot-reload | Rejected | A candidate can damage the active process before review and has no promotion or rollback boundary. |
| Ordinary pull request | Safe current route | Human review and merge remain a fallback, but do not encode admission, budgets, execution isolation, or receipts. |
| Shadow candidate and owned promotion | Selected design | It makes candidate failure external to the body and keeps the final effect with its proper owner. |

## Decision Outcome

Creation is a designed chain, not an autonomous capability:

`Creation Request → Candidate → Verification → Promotion Request → target-owner effect`

Verification makes a candidate eligible to ask; it never performs the live effect. The current
`PATH_LAB_DIR` and its read-write Vessel mount support trusted preparation, while the image's
`/app` is read-only. They are neither a code Forge nor a sandbox. There is no autonomous repair
loop, Tomb executor, verified package promotion, compatibility gate, rollback controller, or
self-extension runtime. [State of Work](../state-of-the-work.md#smith-forge-promotion) owns that
delivery boundary.

The first delivered seam is deliberately inert: immutable contracts and a process-local state
machine bind an exact Git base and source-tree digest, path roots, budgets, tool and network declarations, quarantined
artifact metadata, custody, deterministic verification receipts, compatibility evidence, and an
explicit human review. It performs no filesystem, command, network, database, VCS, or promotion
effect. Its terminal product is only an idempotent `PromotionRequest(inert=True)` addressed to the
named owner, which must revalidate and implement any future effect through its own boundary.
Candidate, custody, verification, and review timestamps must form a possible chronology; timestamps
remain recorded assertions, not trusted-clock or signer proof.

Set-like `WorkPacket` inputs, effects, compatibility evidence, tool pins, and verification checks
are canonicalized before hashing, so transport order cannot create a second semantic packet. The
evidence manifest and promotion request each bind a `RecordBinding` to the full immutable
`CandidateArtifact` digest, including changed paths and declared effects, rather than only to its
artifact bytes. Candidate, custody, verification, compatibility, review, and promotion record ids
share one semantic collision domain; an id cannot be replayed as a different record kind.

### Admission and candidate identity

An immutable **Creation Request** names the principal and intent; exact base revision, admitted
source-tree digest, and allowed paths; tools, effect classes, credentials, network policy, and budgets; required verification and
retention; and the promotion owner and authorization class. It then receives a candidate identity
and workspace. Lab's writable directory conveys no subprocess or network containment.

Each Shadow branch retains the request and exact parent state, but has its own lineage, budget,
outputs, and disposition. Branches do not share a mutable workspace. The
[Shadow contract](31-simulation.md) owns branch records and collapse. A VCS revision—including a
Jujutsu change—proves comparison and provenance, not hidden model reasoning or execution
containment. [The Call](../sepulcher/lich/call.md) gives this opening its correspondence, not its
storage or authority rules.

### Candidate work and proof

Candidate work may write only its allocated workspace. Any command with process, package,
credential, port, database, or network effect needs its own admitted executor and policy; path
restriction alone is insufficient. Independent work may run in independent workspaces, with an
explicit merge boundary. Its output is an immutable patch or artifact reference with structured
observations and declared effects. [The Blade](../sepulcher/lich/blade.md) names discrimination
among possibilities; it is not an acceptance rule.

The request pins its verification plan: commands, tool versions, environment inputs, timeouts,
expected artifacts, and pass criteria. Lint, types, unit tests, build, and migration probes remain
separate from heuristic review such as [Riddle](34-evaluation.md). A qualitative verdict cannot
override a failed deterministic gate. A failure can consume a bounded repair attempt; exhausted
budgets or missing premises settle as noncompletion with retained evidence. Candidate-declared
database, package, install, and recovery checks use disposable state where appropriate and prove
the recorded execution, not production fitness.

Today those checks are operated through development and CI. Workers or Tomb may dispatch admitted
work only after their execution boundaries exist; this ADR does not claim that
[Ghouls](14-workers.md) verify generated code today.

### Promotion is an owned effect

A **Promotion Request** carries the exact candidate-record binding, current-base and source-tree preconditions, receipts, declared
effects, compatibility evidence, and rollback or compensation instructions. It neither moves Lab
into Crypt nor assumes a federated lockfile. At effect time the target owner must:

1. revalidate the live base, source tree, and candidate identity;
2. evaluate [Consent](25-hitl.md), or a narrowly bounded preauthorization;
3. confirm that the evidence is current for this effect;
4. use its own transaction and recovery boundary; and
5. verify the resulting state or invoke rollback or compensation.

Source, package, and extension movement belongs to [Packaging](17-packaging.md),
[Evolution](18-evolution.md), and [Assimilation](35-assimilation.md). Database, credential,
host-lifecycle, and external-service effects remain separately owned; a VCS merge cannot make
them atomic.

### Drift, conflict, and recovery

Base drift, source-tree drift, or an unresolved conflict fails closed. The candidate and its evidence remain for
diagnosis; they are neither silently discarded nor applied over operator work. Continuing means a
new base, resolved conflict, renewed invalidated checks, and fresh authorization when the effect
changed. An external effect already produced must be reconciled by its owner rather than hidden by
VCS cleanup.

An implementation must demonstrate candidate identity and workspace containment, refusal of
active-tree mutation, receipt capture, crash recovery, drift refusal, effect-time authorization,
target-owner promotion, and rollback or compensation. Untrusted execution additionally needs the
Tomb controls owned by Security.

## Consequences

!!! success "Positive"
    Candidate failure stays outside the active body, while identity, evidence, authorization, and
    disposition remain attributable.

!!! failure "Negative"
    Isolation, retained proof, revalidation, and owner-specific recovery cost time and storage;
    external effects still require compensation rather than one universal transaction.
