---
title: 16. SDLC
icon: material/source-branch
---

# :material-source-branch: 16. SDLC

!!! abstract "Context and Problem Statement"
    Software delivery begins with a need and continues through design, construction, verification,
    release, operation, and revision or retirement. File control protects one part of that passage;
    the software development lifecycle (SDLC) must also preserve intent, acceptance, evidence,
    authority, and recovery across its handoffs. Autopoiesis may eventually let LychD extend itself,
    but a candidate becomes part of the body only through its target owner's admitted effect.

## Requirements

- Bind the intended outcome, current-state evidence, scope, acceptance criteria, and affected
  owners before committing to construction; unresolved choices need bounded inquiry.
- Carry those decisions through candidate work, verification, delivery, and observed outcomes.
  Changed intent or acceptance requires an attributable revision and renewed affected checks.
- Candidate writes must not alter the active source tree or running package.
- A candidate must bind its base revision, patch or artifact digest, principal, tools and
  dependency inputs, declared effects, and resource budget.
- A workspace is not a sandbox: processes, network, credentials, databases, and host effects need
  separately admitted boundaries.
- Commands, versions, environment, result, and error class must be retained as verification
  receipts.
- The eventual target owner—not the creator—must recheck current state, authority, evidence, and
  recovery at promotion time.
- The target owner must compare a candidate with any base-revision Protected Region manifest;
  overlap requires an exact live human verdict and cannot use standing preauthorization.
- Lineage and terminal disposition must remain attributable, so interrupted work can resume or be
  discarded without touching the live body.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Live hot-reload | Rejected | It mixes candidate and active object graphs before promotion; cleanup can prove only mediated registrations, not restoration of process memory or external effects. |
| Ordinary pull request | Safe current route | Human review and merge remain a fallback, but do not encode admission, budgets, execution isolation, or receipts. |
| Shadow candidate and owned promotion | Selected design | It makes candidate failure external to the body and keeps the final effect with its proper owner. |

## Decision Outcome

LychD adopts an evidence-bearing SDLC with explicit handoffs between intent, candidate work,
verification, delivery, and subsequent change. **[Creation](../sepulcher/extensions/weaver/creation.md)**
is the practical workflow for carrying a software request through that lifecycle. This Covenant
owns the lifecycle invariants and candidate-to-effect boundary; the workflow supplies the
repeatable method, including Inquiry, task decomposition, review, and human decisions.

Its candidate-to-effect chain is:

`Creation Request → Candidate → Verification → Promotion Request → target-owner effect`

A candidate never mounts, imports, or executes as a plugin in the active Vessel, even as a
temporary trial. Removing callbacks or a module would not prove that its objects, tasks, caches,
foreign-library state, or emitted effects had vanished. Promotion therefore selects a new body
generation rather than trying to clean a candidate out of the current process; continuity crosses
that boundary only through owned durable records and explicit recovery semantics.

The lifecycle currently proceeds through ordinary operator-controlled development and review,
with checks run through development and CI. Verification authorizes only a request for promotion;
it does not execute the live effect.

`PATH_LAB_DIR` and its read-write Vessel mount support trusted preparation in the Lab; the image’s `/app` remains read-only. This writable directory supplies neither an operational code Forge nor execution isolation.

Creation has no implemented contract or state machine. The immutable request, candidate, custody, verification, compatibility, review, and promotion records described below are accepted design; naming them implies no workspace, executor, evidence-store, or promotion-effect implementation. There is no autonomous repair loop, Tomb executor, verified package promotion, compatibility gate, rollback controller, or self-extension runtime. [State of Work](../state-of-the-work.md#smith-forge-promotion) owns delivery status.

### Lifecycle and ownership

The lifecycle can return to an earlier question when evidence defeats its premise. Each return
retains the prior decision and outcome and identifies which checks must run again. Acceptance
criteria are established before the verification they judge; revising them creates a later
comparison rather than converting the previous failure into a pass.

| Passage | Required handoff | Owning law |
| --- | --- | --- |
| Need and design | Intended outcome, present evidence, alternatives, scope, acceptance, and a settled direction | This Covenant; [Doctrine](01-doctrine.md) governs documentation-first design. |
| Construction | Attributable candidate, exact base and inputs, bounded workspace and execution, declared effects | This Covenant; [Security](09-security.md) governs containment and [Workflow](28-workflow.md) governs an executable score. |
| Verification and review | Reproducible checks, independent findings, unresolved gaps, and an exact review target | This Covenant; [Quality](03-quality.md), [Testing](04-testing.md), and [Evaluation](34-evaluation.md) retain their separate gates. |
| Release and adoption | Verified artifact identity, current authority, compatibility, and recovery evidence | [Packaging](17-packaging.md) binds release artifacts; [Evolution](18-evolution.md) owns changed-body adoption; each effect remains target-owned. |
| Operation and revision | Attributed outcomes, failures, and proposed corrections for another admitted change | [Observability](29-observability.md) and [Evaluation](34-evaluation.md) supply evidence; this Covenant governs the next candidate. |
| Retirement | Explicit disposition of the capability, affected work, retained records, and outstanding effects | The capability and effect owners apply their shutdown and recovery law; [Persistence](06-persistence.md) governs retained state. |

Learning from delivery may change the next question, Context, procedure, or implementation.
[Memory](27-memory.md) and [Training](33-training.md) separately govern retained lessons and
weight changes; [Assimilation](35-assimilation.md) governs incorporating foreign craft. Closing
one software task neither initiates training nor authorizes another live change. The lifecycle
connects these decisions without creating a universal executor or absorbing their authority.

### The agentic Graph of Creation

The [Transmutation](../divination/transmutation/index.md) reading path connects the
[Tree of Life correspondence](../divination/transmutation/genesis.md#tree-of-life) for differentiated powers bringing purpose
into form with the operating methods below. LychD's **agentic Graph of Creation** is the engineering interpretation:
admitted intent and present evidence become alternatives, discriminated decisions, a verified
candidate, and an attributable owner effect. The sefirot do not prescribe ten Agents, replace the
four coequal offices of the inner instrument, or supply executable Graph contracts.

The [Creation workflow](../sepulcher/extensions/weaver/creation.md) applies bounded exploration,
independent evidence-sufficiency judgment, and Crucible first to direction and again to
construction where the decision warrants it. Its operation remains subject to the candidate,
verification, and promotion law below. An application must publish its exact Pattern before this
method becomes a LychD casting; the diagram alone registers no Pattern or coordinator.

[Ouroboros](../sepulcher/extensions/weaver/ouroboros.md) maps the return from outcomes and human
correction through evaluation to separately admitted memory, procedural change, or training.
Autopoiesis names the wider horizon of recurrent self-formation, not an exception to effect
ownership. Drift findings cannot mutate a candidate or score; Soulforge cannot promote its own
weights; a changed body follows Packaging and Evolution. Each successor retains lineage and its
own admission. The dependency map does not combine those owners into one hidden Run or make the
whole recurrent process a DAG. Immutable records of its unfolded occurrences may form a causal DAG.

### External workflow research

An independently operated workflow forge may supply candidate SDLC contracts and evaluation cases
for a future local implementation or explicit service integration. Its own owner retains scope and
delivery evidence; reuse does not require migration or retirement of that external project. Each
admitted reuse must separately prove this record's admission, candidate, verification and promotion
boundaries. No graph, trace export or favorable benchmark imports runtime behavior or grants LychD
effects by itself.

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
separate from heuristic review such as [Drift](34-evaluation.md). A qualitative verdict cannot
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
2. evaluate [Consent](25-hitl.md), or a narrowly bounded preauthorization; a
   [Protected Region](28-workflow.md#authorship-provenance-and-protected-regions) forbids
   preauthorization and binds live review to the exact candidate;
3. confirm that the evidence is current for this effect;
4. use its own transaction and recovery boundary; and
5. verify the resulting state or invoke rollback or compensation.

Source, package, and extension movement belongs to [Packaging](17-packaging.md),
[Evolution](18-evolution.md), and [Assimilation](35-assimilation.md). Database, credential,
host-lifecycle, and external-service effects remain separately owned; a VCS merge cannot make
them atomic.

### Changed state, conflict, and recovery

A changed base, changed source tree, or unresolved conflict fails closed. The candidate and its
evidence remain for diagnosis; they are neither silently discarded nor applied over operator work. Continuing means a
new base, resolved conflict, renewed invalidated checks, and fresh authorization when the effect
changed. An external effect already produced must be reconciled by its owner rather than hidden by
VCS cleanup.

An implementation must demonstrate candidate identity and workspace containment, refusal of
active-tree mutation, receipt capture, crash recovery, refusal after state changes, effect-time
authorization, target-owner promotion, and rollback or compensation. Untrusted execution additionally needs the
Tomb controls owned by Security.

## Consequences

!!! success "Positive"
    Candidate failure stays outside the active body, while identity, evidence, authorization, and
    disposition remain attributable.

!!! failure "Negative"
    Isolation, retained proof, revalidation, and owner-specific recovery cost time and storage;
    external effects still require compensation rather than one universal transaction.
