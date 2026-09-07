---
title: 35. Assimilation
icon: material/import
---

# :material-import: 35. Assimilation

!!! abstract "Context"
    Foreign craft crosses more than a code boundary: provenance, license, behavior, security,
    architecture, verification, maintenance, and promotion must survive. A model may propose the
    crossing; it cannot certify its own work.

## Status

The **Smith Extension Domain** and its reference Assimilation protocol are **Designed**. LychD
ships no candidate-author Agent, end-to-end Assimilation path, forge, autonomous repair loop, compatibility
gate, verified package promotion, rollback controller, or self-extension runtime. [State of
Work](../state-of-the-work.md#smith-forge-promotion) owns this boundary.

## Decision

**Assimilation** is the Smith Domain's governed protocol for re-expressing admitted foreign
pattern as attributable local LychD code. Its output is a candidate, never a live organ. The
protocol orders governance questions and settled handoffs; it does not coordinate or execute the
separately owned admissions and effects, and it is not a Portfolio Composition.

| Act | Meaning |
| --- | --- |
| Integration | Bind an external service/protocol through an adapter. |
| Delegation | Ask another runtime or sovereign node for bounded labor. |
| Assimilation | Study a pattern and implement an owned local expression. |
| Heritage import | Convert external user data into provenance-bearing Memory/Identity candidates. |

No act promises bit-for-bit reproduction, protocol or license compatibility, or freedom from
upstream maintenance without separate evidence.

### Execution has no second coordinator

There is no `assimilation.*` Pattern, end-to-end Graph, Suite, or Assimilation coordinator in this
decision. For one future application-owned job, that application's exact Pattern must admit the
purpose, Dossier, candidate-author Agent, ceilings, and terminal result; Spellweaver may validate
and execute its pinned Scroll but owns neither Smith's candidate semantics nor any promotion
effect. Each later receiving owner acts only from a settled typed request and re-admits its own
effect. If a reusable promise must actively coordinate several Composition-owned Invocations, it
requires a separately named and revisioned Suite before execution.

Until one of those exact application contracts is published, Assimilation remains a non-executable
governance protocol. Source/custody, Smith candidate authorship, verification, HitL, packaging,
migration, activation, and observation owners may each perform their own already-admitted action;
the protocol stages transfer no lifecycle authority and imply no ambient resume of the next action.

## Teaching a missing Spell

A peer may answer an unknown-Spell refusal with an attributed **teaching bundle**. The bundle is a
foreign pattern offered for study, not a Spell installed by Intercom. Its bounded,
content-addressed manifest binds the exact public contract revision and digest, examples,
source/artifact identities, provenance, license and notice duties, implementation requirements,
declared authority/effects, and claimed evidence. Every claim remains untrusted until local
admission and proof; intake never imports or executes its contents.

A candidate-author AgentSpec selected by an exact owning application Pattern may satisfy Smith's
role contract and re-express the lesson as a local Spell-contract or implementation candidate under an
Assimilation Dossier. Existing code may satisfy the contract, or the candidate may require new
code, an adapter, package, tool, or capability; each follows its own owner and verification path.
Spellweaver validates contract and Scroll candidates but does not coordinate the Assimilation
protocol. Where the candidate adds a Contribution, its receiving Core office or Extension Domain
retains its semantics; Extension law governs package admission; Creation, Packaging, Security,
Evolution, and effect owners retain implementation, promotion, and activation authority.

Policy may refuse teaching entirely, request it only from named peers and content classes, or
accept only an already trusted exact contract with a local implementation binding. No configuration
may turn a teaching bundle into ambient package installation or self-publication. Foreign claims
retain publisher/key attribution; learned contracts and implementations enter an operator- or
Crypt-owned namespace, never `core` or another canonical publisher's namespace. If future
promotion succeeds, a new immutable catalogue generation may make the unchanged exact Scroll
admissible to a later Invocation. The original refused peer task is never resumed under changed
catalogue truth.

Code or contribution changes activate through controlled [Evolution](18-evolution.md): close or
drain admission as required, preserve retained executable closures for pinned Runs, replace the
Vessel or process-built catalogue, reconcile durable state, verify readiness, and reopen. This is
not **Reanimation**, which reconstructs the same body from committed records after process death.
A whole-body restore additionally requires the exact sealed cut in [Snapshots](07-snapshots.md).
Declarative-only Scroll publication may avoid replacement only after an atomic durable catalogue-generation mechanism and
already-admitted implementations exist; neither is delivered now.

## Candidate author and admission

A **candidate-author Agent** is the future reference Agent role defined by the Smith Extension
Domain. A future exact owning application Pattern must select a registered AgentSpec satisfying
that role. The Agent may inspect admitted source and write candidate code, schemas, migrations,
tests, documentation, and packaging inputs inside a bounded Lab coordinate. It has no ambient authority
over active checkout/Vessel, locks, publication, database migration, lifecycle, secrets,
unrestricted network, or promotion; it submits typed requests to their owners. Authorship is not
authority.

Every candidate begins with an **Assimilation Dossier**: exact source identity/revision/digest/path,
license/notice duties, target behavior or defect, chosen local target/base revision,
transformations/generated files, model/tool/prompt/human authorship, expected effects/verification,
unresolved gaps, and maintenance owner. Absent identity, provenance, or license, material may be
studied but may not request promotion.

Source, manifest, documentation, examples, archive, comments, tests, issue text, and generated
configuration are hostile data, never instruction authority. Admission acquires only exact
material, retains provenance and classification, fences it outside stable instructions, denies ambient
credentials/home/undeclared egress, bounds size/recursion/decompression/parser/subprocess effects,
and records every transform. Typed candidate-author output constrains shape, not truth; prompt injection
can produce valid-looking schemas.

## Candidate law and Lab

Assimilation inherits [Creation](./16-creation.md)'s candidate/promotion contract: immutable
identity and exact base, permitted paths/effects, isolated workspace, budget, verification plan,
and terminal disposition. Lab is a location, not a sandbox. Untrusted analysis, build, or generated
command needs the [Tomb](../state-of-the-work.md#tomb-untrusted-execution) or another delivered
execution boundary before automation. Pre-v1 coupled Extensions may use internal imports, but are
tested body parts rather than public-API consumers; targets must use actual registration,
configuration, and runtime contracts. A versioned external package/ABI claim needs deliberate
tests.

Python, Rust/PyO3, WebAssembly, shell, and generated Quadlets are candidate materials with distinct
toolchains/effect surfaces. A compile, faster language, or foreign suite never bypasses admission.

## Verify, then promote separately

The Dossier selects evidence that can establish its particular claim:

- lint, types, tests, build and focused behavior;
- differential or conformance checks when equivalence is claimed;
- migration rehearsal, install, import and package checks;
- extension registration and startup;
- permission, egress, secret and hostile-input probes;
- license and notice review; and
- performance measurements only when performance is claimed.

Foreign tests establish foreign behavior. Generated tests cannot be the sole judge of generated
code, and heuristic review cannot override a failed deterministic gate. A bounded correction loop
ends verified or explicitly incomplete. Traces and failures may inform repair through their
Memory, Shadow, Riddle and consent owners.

The candidate-author Agent emits a **Promotion Request**, while owners decide and perform their own effects:

| Concern | Owner |
| --- | --- |
| candidate lineage/workspace | [Creation](./16-creation.md) |
| source/package/image construction | [Packaging](./17-packaging.md) |
| coupled extension-package admission | [Extension law](./05-extensions.md) |
| migration/persistence | [Phylactery](./06-persistence.md) |
| activation | [Evolution](./18-evolution.md) and lifecycle owners |
| human authority | [HitL](./25-hitl.md) |

At effect time each revalidates candidate identity, current base, evidence, authority, and its own
recovery. Merge cannot atomically make migration, restart, remote write, and publication. Failed or
indeterminate effects remain attributed; the candidate-author Agent cannot erase them by deleting its
workspace or changing its explanation.

## Heritage and correspondence

Cloud archives and historical conversations expose an unresolved **Heritage** ownership need
outside Smith. It remains a candidate study until distinct records, judgment, finish, recovery,
and independent use justify a Composition. The candidate-author Agent may propose a parser, but output remains
provenance-bearing candidate Memory—not Persona, instruction, preference, or training truth.
Assimilated capability and every learned Spell are private by default; A2A advertising,
Legion distribution, or public packaging needs its own authorization.

Assimilation is not consumption: the candidate-author Agent breaks foreign pattern on the anvil of local law
and offers a new organ. _Purpose is the hammer. Pattern is the anvil. Consent is the seal._ What
leaves the Forge may ask to live; it does not crown itself.

## Consequences

!!! success "What this gives us"
    One attributable, quarantined passage from foreign craft to locally verified candidate keeps
    provenance, license, authorship, test evidence, and promotion authority distinct.

!!! failure "What it costs"
    Serious work can require differential tests, migration rehearsal, supply-chain review,
    long-term maintenance, and retesting coupled Extensions; some behavior cannot be reproduced
    lawfully or reliably.

## Acceptance gates

No automated Assimilation path may ship until hostile-source ingestion, candidate isolation,
provenance retention, bounded execution, deterministic receipts, base-drift refusal, effect-time
authorization, target-owned promotion, and recoverable or explicitly forward-only failure are
proved.
