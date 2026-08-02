---
title: LychD Source Maintenance
icon: material/source-commit
---

# :material-source-commit: LychD Source Maintenance

**Candidate question:** can one exact defect or correction become a verified patch without giving
an Agent authority over the living source tree?

| Local maturity | Identity | Principal Pattern |
| --- | --- | --- |
| **Unaccepted Candidate study; architecture and delivery remain unchanged** | `lychd.source-maintenance` revision `1` | `lychd.prepare_file_candidate@1` |

## Purpose and ownership

The Composition would accept one admitted defect or correction and one exact Git base, then return
either a verified quarantined patch artifact or an honest non-completion. It would own that
application purpose, its application-specific candidate catalogue, its bounded repair policy, and
its Altar projections. Creation retains candidate identity and lineage; Weaver, Graph, and Workers
retain Invocation, station-occurrence, and delivery identity. The Composition would not own
workflow law, execution containment, persistence infrastructure, evaluation judgment, provider
authority, or promotion into the active body.

This study applies existing law rather than restating or amending it:

| Boundary | Owning law |
| --- | --- |
| candidate identity, isolation, verification, and target-owned promotion | [Creation (ADR 16)](../adr/16-creation.md) |
| immutable score, Invocation, Gates, effects, Stasis, and correction admission | [Workflow (ADR 28)](../adr/28-workflow.md) |
| hostile inputs, candidate admission, independent proof, and foreign craft | [Assimilation (ADR 35)](../adr/35-assimilation.md) |
| committed truth and transaction boundaries | [Persistence (ADR 06)](../adr/06-persistence.md) |
| Tomb/Coffin containment, provider egress, and return quarantine | [Security (ADR 09)](../adr/09-security.md) |
| exact human decisions and durable re-admission | [HitL (ADR 25)](../adr/25-hitl.md) |
| deterministic observations versus heuristic findings | [Evaluation (ADR 34)](../adr/34-evaluation.md) |

The tracked [Delegated Coding](https://github.com/hexanomicon/lychd/blob/main/.agents/workflows/delegated-coding.md)
playbook is current operator procedure and design input. It is not architectural law and yields to
the owners above.

The Pattern names an application score, not a public Pattern SDK or permission to extend the
current registry. No universal event ledger, world-state document, autonomous promotion service,
or live-source editor follows from this page.

## Exact Pattern score

```text
AdmitRequest [Gate]
→ PinGitBase
→ CollectDeterministicBaseline
→ SelectEligibleRoute
→ AssembleWorkPacketForRoute(proposal 1)
→ AuthorizeExactRemoteOccurrence? [Gates when remote]
→ ProposePatch [delegate]
→ QuarantineAndValidateReturn
→ ApplyToCandidateWorkspace [effect]
→ VerifyCandidate [effect]
→ ClassifyProposal
    ├─ verified → SealPatchArtifact → MagusReview [Gate]
    │    ├─ request promotion → PrepareInertPromotionRequest → PROMOTION_REQUESTED
    │    ├─ reject → RecordRejection → REJECTED
    │    └─ no verdict or defer → Durable Stasis at MagusReview
    ├─ correctable and proposal 1
    │    → RecordDiagnostics → AwaitRepairInstruction [Gate]
    │    → SelectEligibleRoute
    │    → AssembleWorkPacketForRoute(proposal 2)
    │    → AuthorizeExactRemoteOccurrence? [Gates when remote]
    │    → ProposePatch [delegate] → QuarantineAndValidateReturn
    │    → ApplyToChildCandidate [effect] → VerifyCandidate [effect] → ClassifyProposal
    │         ├─ verified → SealPatchArtifact → MagusReview [Gate] → settle as above
    │         └─ otherwise → RecordNonCompletion → NON_COMPLETION
    └─ denied, unsafe, unknown, stale, or exhausted → RecordNonCompletion → NON_COMPLETION
```

`PinGitBase` accepts a full immutable commit identity, never a bookmark or moving branch.
`ProposePatch` is a bounded delegated occurrence. Return validation checks declared paths, base
file digests, modes, size, shape, and patch applicability before a candidate write. Verification
records deterministic commands separately from any Riddle judgment. The second classification is
terminal: there is no third proposal, recursive repair, or hidden provider fallback.

Request admission, exact remote authorization, repair-instruction admission, and final review are
Gates. `ProposePatch` is one delegate occurrence; candidate application and verification are
separately receipted effects; `MagusReview` is a durable Gate. Before any durable wait, the
checkpoint pins request, base, proposal number, route, WorkPacket digest, candidate and artifact
references, verification state, Gate request identity, and any committed verdict identity.
Delegate and effect occurrences declare timeout, cancellation, idempotency, and illegal-repeat
boundaries. Cancellation with an unproved external outcome settles `LOST`; it never silently
replays.

## The just-in-time WorkPacket

A `WorkPacket@1` would be assembled for the selected route immediately before each proposal rather
than copied from an old chat or mutable agent memory. It pins:

- Invocation, Creation Request, proposal occurrence, exact Git base and parent candidate identities;
- the admitted defect or Invocation-opening `CorrectionRequest@1`, acceptance target, non-goals,
  allowed paths, effects, tools, network, retention, and finite budgets;
- content-addressed source and policy projections with their classifications and digests;
- attributed deterministic diagnostics: command, tool and environment revisions, structured
  findings, exit class, truncation, and evidence references;
- each admitted `RepairInstruction@1` as an immutable Magus-authored record bound to the exact
  candidate and verification evidence, with scope and revision;
- when foreign material informs the work, its `AssimilationDossier` reference covering source
  identity, license and notice duties, hostile-source handling, transformations, unresolved gaps,
  and maintenance owner; and
- the route, output contract, verification plan, terminal law, and permitted downstream use.

The packet is frozen and digested at dispatch. A changed base, source digest, policy, diagnostic,
repair instruction, route, or payload invalidates the packet and any egress decision. Diagnostics
remain verifier observations; Magus instructions remain human instructions. Neither is silently
blended into unattributed memory.

## Candidate and occurrence lineage

```text
Creation Request R at base B
└─ proposal occurrence A1 using WorkPacket W1
   └─ Candidate C1 with patch/tree digest
      └─ Verification V1
         └─ admitted diagnostics and optional RepairInstruction K1
            └─ proposal occurrence A2 using fresh WorkPacket W2, parent C1, base B
               └─ Candidate C2 with patch/tree digest
                  └─ Verification V2 and terminal disposition
```

The Composition introduces no independent `Attempt` identity. Each proposal occurrence is the
existing delegated `AgentJob` and station occurrence correlated to one Creation-owned Candidate.
A `RepairInstruction` creates a child Candidate path inside the same Invocation and never edits
C1's history. A Riddle `CorrectionRequest`, by contrast, may only open a new forward Invocation.
Every occurrence retains its packet, route, Agent/job and environment identities, receipts, cost,
error class, and terminal state.
Late results are inert, base drift refuses, and ambiguous external outcomes become `LOST` pending
reconciliation rather than permission to launch again.

## Custody and recoverable truth

| Surface | Candidate responsibility | Never authoritative for |
| --- | --- | --- |
| Tomb boundary | path-restricted candidate application and verification in disposable execution | Agent judgment, active checkout, promotion, provider or host authority |
| Coffin boundary | one foreign coding occurrence, bounded context and quarantined return | broad Crypt, PostgreSQL, authoritative VCS, promotion or host authority |
| Managed artifact custody in Crypt | quarantined bytes and immutable patch, log and receipt artifacts addressed by digest | verdicts, Run state, approval or provider authority |
| PostgreSQL / Phylactery | committed identities, lineage, gates, dispositions, artifact metadata, checkpoints and receipts | live processes or artifact bytes it cannot verify |
| Process memory | current handles, leases, streams and rebuildable projections | anything required for restart, review or settlement |

The study fixes no directory layout or database schema. Artifact custody must prove that published
digests exist and match; a missing or corrupt artifact fails closed. PostgreSQL records meaning and
transactional transitions, while immutable custody records bytes. A queue may deliver identities,
but does not become Run or candidate truth.

Custody follows one crash-legible order. Untrusted bytes enter quarantine; the custody owner
hashes, flushes, and seals them before PostgreSQL may commit their artifact metadata and candidate
reference. Orphaned bytes are inert and reclaimable; a committed reference whose bytes cannot be
re-attested becomes `custody_lost`. Parking atomically commits the Gate request, checkpoint, and
Run wait before projection. A first-writer-wins verdict commits separately. Re-admission then
consumes the decided wait through one compare-and-set and atomically creates the next durable
delivery identity. External broker publication follows the commit; failure leaves that exact queued
hop for relay rather than recreating the wait or reusing a key. Terminal disposition and evidence
commit before UI projection or best-effort cleanup. Publication or projection failure leaves
reconcilable committed truth and never authorizes duplicate candidate or provider effects.

## Gates, effects, and survival contract

Request admission, any exact disclosure, repair-instruction admission, and final review are durable
Gates. Provider calls, candidate filesystem mutation, and verifier commands are effects executed
only by their owning boundary with an idempotency identity and receipt. A Gate verdict never
performs the effect; the effect owner rechecks current identity, policy, authority, and limits.
Human waits hold no model, process, or scarce capability lease.

The Composition does not own Vessel or PostgreSQL shutdown order. It requires the body-owned
[Reanimation](../sepulcher/phylactery/reanimation.md) path to preserve committed Gates, Candidate
and artifact references, and declared Durable Stasis; reconstruct no authority from process
memory; and reopen admission only after migration and custody reconciliation. There is no memory
fallback.

After a crash, committed Gates and terminal occurrences survive. An uncommitted candidate write or
unprovable provider/process result is quarantined and classified unknown or `LOST`; restart does
not prove success and does not authorize replay. Promotion and any later source activation have
their own owner-specific drain, compatibility, effect, and recovery plan.

## The four Altar projections

| Instrument | Projection only |
| --- | --- |
| [Bridge](../divination/altar/bridge.md) | admit the defect or correction, show exact review calls, and return the artifact or non-completion |
| [Loom](../divination/altar/loom.md) | show the immutable Pattern revision, stations, branches, limits, waits, privacy boundaries, and pinned Invocation |
| [Orb](../divination/altar/orb.md) | show packets, transformations, occurrences, diffs, diagnostics, receipts, gaps, costs, and lineage without rewriting evidence |
| [Nexus](../divination/altar/nexus.md) | show PostgreSQL, workers, Tomb/Coffin, provider Gate, workspace and artifact readiness, containment, and restart progress |

Bridge supplies bounded intent and judgment; Loom shows declared logic; Orb shows what occurred;
Nexus shows whether physical prerequisites can act. No browser screen owns domain law, executes a
promotion, or turns a fluent Agent report into evidence.

## Provider and anonymization boundary

The Pattern requests a typed coding capability, not Codex, Anthropic, or another provider by name.
Cost or subsidized capacity may order otherwise eligible routes but grants no authority. Local work
may receive the admitted packet. Remote work receives only a newly built, content-addressed
[Privacy Cut](../adr/21-context.md#privatization-and-the-privacy-cut) after deterministic Censor
transformation, utility validation, a `TransformationReceipt`, and an exact `EgressDecision`.

The exact remote occurrence additionally requires a job-bound Coffin Provider Gate grant. It binds
the bearer, provider, model, route, expiry, revocation state, and monotonic request, token, and
spend budgets; it mediates the real credential. Its grant, the `EgressDecision`, and any admitted
transformation must agree without widening one another.

The raw checkout, secrets, authority records, and rehydration map stay local. Changed payload,
provider, model, occurrence, repair instruction, retry, destination, or budget requires a fresh
decision. Returned bytes remain quarantined; a trusted local, path-restricted step rehydrates and
applies them only to the disposable candidate. If anonymization removes information needed to edit
safely, the route refuses or stays local instead of pretending capability parity.

## Bounded feedback, inert promotion

Proposal one may return deterministic failures. Only their attributed structured form and an
optional admitted `RepairInstruction` enter the fresh packet for proposal two. Provider prose,
unverified blame, hidden reasoning, and the candidate's own confidence do not. Proposal two either
passes the pinned verification plan or ends honestly.

Magus review binds the exact candidate, patch/tree digest, evidence manifest, current base, and
declared effects. Approval produces only an inert `PromotionRequest`; it does not edit, merge,
commit, push, migrate, restart, or activate anything. Creation and each target owner retain those
later decisions and revalidation duties.

## Deferred consumers

Diagnostics, repair instructions, rejected candidates, and outcomes are not automatically Memory,
retrieval precedent, evaluation truth, or training data. A future RAG index may consume separately
admitted, attributed records under [Memory](../adr/27-memory.md) and remain a rebuildable derivative.
Training requires a separately consented corpus and the lineage, deletion, evaluation, and weight
promotion law of [Training](../adr/33-training.md). Neither consumer may feed results back into this
Pattern merely because the records exist.

## Smallest proving slice

Use one disposable fixture repository at one exact commit, one admitted defect in one existing
text file, a deterministic reference proposer, and a verifier restricted to pinned static checks.
Proposal one must fail one check; that attributed diagnostic plus one Magus `RepairInstruction`
enters a fresh second packet; proposal two must pass. Restart Vessel while the repair-instruction
Gate is parked, then prove exactly one re-admission.

The acceptance receipt must bind base, request, packets, occurrences, candidates, repair
instruction, commands and environment, patch and evidence digests, restart/reconciliation result,
and terminal disposition. It must show that the original repository stayed byte-identical and that
final review produced only an inert patch artifact and Promotion Request. This slice proves no
Tomb/Coffin containment, remote provider egress, live source promotion, RAG, or training; each
needs its own later effectful receipt before any delivery claim.

Return to the [Composition Portfolio](index.md).
