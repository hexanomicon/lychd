---
title: Compositions
icon: material/source-branch
---

# :material-source-branch: Compositions

A Composition is a job the Magus can recognize from beginning to end. It owns the purpose,
application records, policies, and finish condition; versioned Patterns carry that purpose through
LychD's common machinery.

This distinction keeps the Portfolio useful. Search, email, audio, a tunnel, a model, and a
container can all help an application, but none becomes an application merely by being reusable.

## The application test

A page belongs in the Portfolio when all three answers are concrete:

1. **What human purpose finishes here?** The result is more specific than “send,” “search,”
   “generate,” or “run a model.”
2. **Which truth does it own?** Its records and judgments have a domain home rather than living in
   chat history or a generic helper.
3. **How can it stop honestly?** Refusal, partial completion, unknown effects, restart, and recovery
   are part of the contract.

| Term | Office |
| --- | --- |
| **Composition** | operator-visible application purpose, records, policies, projections, effects, and Pattern catalogue |
| **Native Reference Composition** | first-party supported application contract and worked example |
| **Pattern** | one immutable executable score owned by a Composition |
| **Invocation** | one admitted performance of an exact Pattern revision |
| **Suite** | versioned coordination of separate Compositions through typed handoffs |
| **Extension** | a governed way for implementation to enter LychD; never an application by itself |

Portfolio membership accepts an application contract; it does not claim executable delivery. Every
leaf summarizes its current material under the canonical
[State of Work Portfolio boundary](../state-of-the-work.md#composition-portfolio-delivery).

A Composition identity is a URL-safe key plus a separate revision, written here as
`example.application` revision `1`. Pattern identity remains separately versioned, for example
`example.perform_work@1`.

## The Portfolio

### Creative work

| Composition | It finishes with |
| --- | --- |
| [Voidlight Studio](voidlight-studio.md) | an attributable, rights-aware creative asset bundle |
| [Riffmaw](riffmaw.md) | an original musical-work bundle and picture-cue map |
| [Game Foundry](game-foundry.md) | a reproducible, playtested local build candidate |
| [Broadcast Studio](broadcast-studio.md) | a source-grounded local publication candidate |

### Personal life and place

| Composition | It finishes with |
| --- | --- |
| [Health, Food & Movement](health-food-and-movement.md) | an editable plan or honest infeasibility result, never a medical judgment |
| [Lifestyle Steward](lifestyle-steward.md) | corrected household evidence, a reviewable trip or cart, or an acknowledged, refused, or unknown checkout outcome |
| [Home Seeker](home-seeker.md) | an explainable shortlist and due-diligence packet |
| [Homestead](homestead.md) | a legible resource plan, bounded work order, or safely refused physical intent |

### Research, trade, and professional work

| Composition | It finishes with |
| --- | --- |
| [Tech Scavenger](tech-scavenger.md) | a qualified candidate or seller thread, commitment decision, expected parcel, inspection outcome, or closed campaign slot |
| [Bazaar Haggler](bazaar-haggler.md) | attributable negotiated terms, refusal, or timeout under an exact mandate |
| [Broker Office](broker-office.md) | a client answer, prepared act, human handoff, or exact blocker |

### Presence and inhabited worlds

| Composition | It finishes with |
| --- | --- |
| [Blockworld Inhabitant](blockworld-inhabitant.md) | one finite mission whose world effects are verified and recoverable |
| [Reach](reach.md) | one bounded social turn, summon, or admitted presence effect |

## Reference route

One application route remains beside the Portfolio because it demonstrates how several Patterns
can share an ingress without turning that ingress into another application.

| Route | Its actual office |
| --- | --- |
| [Walking Communion](walking-communion.md) | mobile voice ingress and result projection into an admitted Pattern |

Keeping the route here preserves the worked example without inventing an application identity,
Pattern owner, or delivery claim for a channel.

## Reuse without a universal helper

| Mechanism | What remains with the Composition |
| --- | --- |
| Scout search, fetch, render, or crawl | source policy, interpretation, ranking, and consequence |
| mail or platform delivery | recipient purpose, disclosure, approval, reply meaning, and follow-up |
| audio or vision processing | admitted source, domain interpretation, retention, and creative or operational judgment |
| Tether or Veil | application identity, object grants, and every consequential effect |
| Legion node or embedded body | task purpose, while the body keeps fresh safety admission and refusal |
| model or tool provider | application truth, decision policy, and authority |

Typed requests, observations, artifact references, and receipts may cross those seams. Ambient
database access, credentials, Sigils, provider sessions, and domain judgment do not.

Some applications deliberately resemble one another. Home Seeker and Tech Scavenger may share
source snapshots, scheduling, deduplication, and explainable scoring without sharing property or
hardware judgment. Tech Scavenger may issue an exact `NegotiationMandate@1` to Bazaar Haggler, then
must revalidate the returned terms before reserving money or a parcel. A shared sender never creates
a shared right to negotiate.

## Suites do not dissolve their members

A Suite pins eligible Composition and Pattern revisions, declares typed ArtifactRef or Intent
handoffs, carries correlation and aggregate ceilings, and states partial-completion policy. It owns
no member records, secrets, Sigils, provider grants, consent, or effect authority.

```mermaid
flowchart LR
    B["Creative brief"] --> V["Voidlight Studio"]
    V --> A["CreativeAssetBundle@1"]
    A --> G["Game Foundry"]
    A --> P["Broadcast Studio"]
    G --> GB["Playable build"]
    P --> PC["Publication candidate"]
```

The diagram is a designed handoff, not an executor. Weaver must still settle child identity,
revision closure, budgets, cancellation, Stasis, retry, effect receipts, compensation, and honest
partial completion before a Suite can run.

## How a leaf should read

Every Composition leaf answers the same practical questions without reproducing an ADR:

- identity, representative or default Pattern catalogue, application inputs, possible outcomes,
  and stopping line;
- one representative journey rather than a catalogue of imagined features;
- the records and typed handoffs that make the result attributable;
- the few authority, privacy, effect, and recovery boundaries that shape this application;
- current material stated against tracked evidence; and
- the smallest fixture that could prove the contract.

There is no Crypt `compositions/` loader and no Markdown discovery path. The current source
registry and Loom prove only the bounded material recorded in
[State of Work](../state-of-the-work.md#loom-workflow-views); a live Portfolio store, application
selection, Suite execution, and scheduling remain designed.

Continue with [Workflow](../adr/28-workflow.md), then choose the application whose finish condition
matches the work.
