---
title: 18. Evolution
icon: material/refresh
---

# :material-refresh: 18. Evolution

!!! abstract "Context and Problem Statement"
    Evolution governs adoption of upstream source while retaining deliberate local changes. An
    update can alter source, dependencies, configuration, schemas, artifacts and services together.
    Each affected owner needs compatibility evidence and a recovery plan before the changed body
    can be activated.

## Requirements

- Bind installed and upstream revisions, local delta, locks, configuration, extension set, schema
  head, and platform.
- Build, merge, migration rehearsal, and verification occur in an inactive candidate.
- Test the selected built-ins and private in-process extensions with the candidate Core; pre-v1
  internal imports are not a stable API.
- Keep source, package, database, runtime, and external recovery with their own owners.
- Changed state, conflict, missing evidence, and exhausted repair budgets block promotion; every live
  effect rechecks state and authority.
- Keep source selection, verification evidence, collective promotion authorization, and each
  target owner's live effect as distinct decisions even when the same humans participate.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Upgrade the active environment in place | Rejected | Acquisition, resolution, migration, and activation share a running body without recovery proof. |
| Hot-replace modules inside the Vessel | Rejected | Old and new object graphs can coexist while only mediated effects can be unwound; process memory is not a recovery coordinate. |
| Never update | Rejected | An immutable artifact need not abandon reviewed security and compatibility work. |
| Inactive candidate with owned promotion | Selected design | Local work survives only when it still verifies; activation remains separately authorized. |

## Decision Outcome

This update law applies [SDLC](16-sdlc.md) and [Packaging](17-packaging.md) to a Core update.
[Illumination](../divination/transcendence/illumination.md#i-the-ouroboros) keeps the wider meaning
of Ouroboros; the [operating map](../sepulcher/extensions/weaver/ouroboros.md) connects that return
to SDLC, evaluation, training and separately owned activation. The update passage is:

`Update Request → Inactive Candidate → Verification → Promotion Request → owned effects`

Candidate verification is not activation. The repository audits source-bound wheel and sdist
candidates, renders an Alembic one-shot before Vessel start, and has a mediated Host Reactor for
typed Animator transitions. It does not acquire upstream, orchestrate updates, rebase local work,
repair compatibility, checkpoint or restore a whole body, promote a package, replace a body, or
restart through Ouroboros. The [public release chain](../state-of-the-work.md#public-release-artifact-chain),
[whole-body recovery](../state-of-the-work.md#whole-body-snapshot-restore), and
[Smith/Forge promotion](../state-of-the-work.md#smith-forge-promotion) remain Designed.

This law concerns LychD and coupled local extensions, not the release process of an external
service or peer. Built-ins and private in-process extensions that import internal modules are
structural dependants of the exact Core: imports, registration, configuration, and behavior may
break. The selected set must build and test with the candidate; no Smith repair guarantee exists.
[Extension law](05-extensions.md#7-extension-compatibility-tiers) owns the tiers. An
external-service Animator is decoupled only where its declared protocol and adapter remain
compatible.

### One lineage, many developer-owned projects

Evolution governs the next generation of one declared software lineage; it does not require every
developer-owned project to become part of Core. A separately named Extension Domain, Composition,
or external service may keep its own purpose, release cycle, and ownership while using LychD as its
upstream substrate. A private coupled extension or local Core delta remains part of the selected
body and must verify with that body's candidate; an independent boundary receives only the
compatibility its versioned public contract proves. [Extension law](05-extensions.md) owns those
forms and promises.

A derivative that selects its own canonical source policy, promotion authority, or incompatible
contracts becomes a separately governed lineage. It may continue to study or reconcile later LychD
changes, but the LychD source-selection and promotion rosters govern only the shared LychD Core,
not that derivative's source or activation. The derivative must own its exact upstream or base,
local delta, evidence, recovery, and maintenance; common ancestry grants neither automatic
compatibility nor an upstream repair obligation.

Returning work to the shared line is a separate decision from updating a local body. A developer
may propose a generally useful change through [SDLC](16-sdlc.md), source governance, and
[Packaging](17-packaging.md); once admitted into canonical upstream, each downstream body chooses
and verifies its adoption through its own Evolution. A foreign pattern instead enters through
[Assimilation](35-assimilation.md), which yields an attributable local candidate; activating that
candidate still passes through Evolution. Assimilation is therefore neither an upstream update nor
an automatic contribution channel.

### Reconcile concurrent contributors and recurring candidates

Each contributor's candidate binds its admitted upstream/base and local input closure. Independent
candidates may be developed concurrently in separate surfaces; integration is an attributable
successor candidate. Verify that combined object rather than inferring compatibility from the
individual branches' receipts. Base, dependency, configuration, schema or selected-extension
changes invalidate the affected evidence and authorization. Neither an automated conflict repair
nor a clean textual merge proves semantic compatibility.

An idle-development coordinator may prepare candidates under SDLC admission but gains no
source-selection vote, promotion credential or activation authority. Current branch, review and
exact-object promotion procedure remains in
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#branches-and-everyday-collaboration).
Future quorum and target-owned activation retain their separate eligibility and recovery gates.
Downstream adoption never silently overwrites operator changes or makes upstream maintainers
responsible for repairing a separately governed lineage.

### Synchronic Syncretizer {#synchronic-syncretizer}

!!! quote "Synchronic Syncretizer — continuity through synthesis"
    The Arbiter of Evolution asks what deserves to survive, what may end, and which differences
    can coexist or form a better successor. Continuity preserves attributable consequence and
    answerable obligations; it does not require every old implementation to remain executable.

**Synchronic Syncretizer** names Evolution's bounded adoption judgment. It consumes verification
receipts, [Drift's findings](34-evaluation.md) when available, required owner verdicts and retained
history; it does not become a second evaluator or take the target owners' effects. A proposal
for changed selection criteria or an evaluator is a separately reviewed candidate, never a
candidate author's permission to rewrite a failed comparison.

A comparison binds the installed and candidate closures, exact base and local delta, selected
extensions, predeclared acceptance and policy revisions, and the history selected for this
question. Its history manifest identifies predecessor decisions, obligations, failures and
unresolved effects, with selection reasons and omissions. It retains supporting evidence,
contradictions, dissent and uncertainty rather than compressing them into one quality score.

Each affected obligation receives an attributable disposition:

| Disposition | What must remain explicit |
| --- | --- |
| **Retain** | The behavior or boundary to preserve, its consumer and evidence against the exact candidate. |
| **Reconcile** | The incompatibility and proposed successor combining the chosen parts; that combined candidate needs its own verification. |
| **Replace** | What deliberately ends, why its retirement is justified, affected consumers and unresolved work, and their authorized transition or refusal. |
| **Reject** | Why the proposed change is refused and which evidence or changed condition could reopen it. |

A known harmful baseline does not become acceptable merely because a candidate is blocked.
Security revocation may forbid an old executable closure while its history remains attributable.
Plurality also permits independent lineages, policies or capabilities to coexist: synthesis
cannot require one universal agent, paradigm or canonical body for every participant.

Missing mandatory evidence, an unresolved required owner verdict or an unowned transition blocks an
eligible Promotion Request. Changed base, candidate, relevant environment, policy or evaluation
invalidates the affected comparison and requires a new attributable decision. Identical
redelivery must preserve the admitted comparison identity; a new semantic attempt cannot erase
the earlier failure. The result is a retained disposition and, only when eligible, an **inert
Promotion Request**. Source selection, collective promotion approval and each target owner's
fresh effect-time checks remain separate. A recorded judgment neither migrates nor activates.

### Start the changed body as a new generation {#replace-the-generation-not-its-memory}

A promoted Core or coupled extension change activates as a new Vessel process generation.
Evolution never imports replacement modules into the live Vessel and never carries its
process-local object graph across that boundary. Listeners, caches, coroutines, dependency
handles, and other volatile objects belong to the old generation and die with it.

The old generation closes admission and drains, parks, or resolves owned work according to its
domain contracts. The new generation reconstructs its volatile world from the attested manifest,
validated configuration, and compatible Phylactery records. Unresolved work and already-emitted
external effects remain subject to the [Graph](24-graph.md), [Workers](14-workers.md), and
[Reanimation](../sepulcher/phylactery/reanimation.md) rules; process replacement does not pretend
to rewind them.

This boundary optimizes for coherent recovery, not uninterrupted availability. Death of a Vessel
running the same body is Reanimation. Deliberately starting a changed body is Evolution. In both
cases durable truth, rather than surviving process memory, is the continuity substrate.

### Record the recovery coordinate

The update record captures the exact installed artifact or image, source revision, dependency
locks, configuration identity, selected extension revisions, schema head, active topology,
requested upstream revision, and local delta. Before promotion, every affected owner supplies a
tested recovery coordinate or declares forward-only risk and obtains authority for it. A future
[whole-body checkpoint](07-snapshots.md) may bind them; VCS history plus a database backup is not
one atomic snapshot.

### Reconcile into a candidate

An inactive candidate starts from an immutable upstream commit and reapplies admitted local
changes with provenance. Jujutsu implementations record hexadecimal commit IDs for identity;
mutable change IDs and branch names are annotations only. The installed body need not contain a
source repository. Any conflict or changed base blocks promotion. Bounded repair produces a new
candidate and repeats invalidated checks and authorization. [Shadow](31-simulation.md) and
[Assimilation](35-assimilation.md) provide future branch and repair law, not a delivered rebase
service.

Its pinned dependencies and platform manifest require Core tests, typing, lint, build, archive
audit, and isolated install; each manifest-bound built-in or private extension; configuration and
registration; migration rehearsal from every declared source head; startup, readiness, and
affected behavior; and changed external protocol/adapter boundaries. “All active extensions” is
this manifest-bound set, not runtime discovery. A tested external protocol proves that contract
only; deterministic failure rejects the candidate regardless of review or repair proposals.

### Promote across the temporal boundary

Only an immutable, verified artifact with a request naming each live effect may promote. Under the
lifecycle boundary, owners revalidate revision, schema, configuration, and authorization; close
or drain admission; stage without changing the active body; migrate through the
[Phylactery](06-persistence.md); activate through an attested [Privilege](10-privilege.md)
boundary; verify schema, readiness, registration, and affected behavior; then reopen only after
success or proved recovery. A migration declares an expand/contract path, tested downgrade, or
forward-recovery plan compatible with activation and rollback. The Host Reactor can transition
typed Animators, not replace the Vessel or accept `INTENT_RESTART_VESSEL`.

Before any live effect, retention policy may discard or retain a failed candidate. Afterwards,
each owner invokes tested rollback, compensation, or forward recovery: a source selection cannot
undo a committed migration or external effect. Terminal evidence retains the request, candidate,
effects, checks, traces, recovery attempts, and observed final state. An indeterminate result is
contained for the operator; a revised attempt has a new identity and repeats relevant gates.

### Trust split

Humans and CI currently acquire, build, and review. The designed coordinator owns identity,
policy, evidence, promotion requests, and recovery orchestration. Untrusted build, test, and
repair commands belong in [Tomb](../state-of-the-work.md#tomb-untrusted-execution) only after that
plane exists, without signing keys, migration credentials, durable workflow ownership, or host
lifecycle authority.

### Future quorum roster and promotion envelope {#future-quorum-roster}

The proposed future **quorum roster** is a versioned roster of active human maintainers, open to
contributors who demonstrate care for the shared Core through extensions, implementation,
compatibility work, review, and sustained community discussion. It has no founding headcount or
reserved employment seats. A maintainer receives individually scoped credentials through an
explicit admission decision; Discord membership or message volume alone grants no key.
It is not a delivered LychD runtime object, remote identity service, or reason to share credentials.
A seat belongs to one accountable person, not to each of that person's devices; automation, seeds,
mirrors, runners, and agents receive no seat.

The roster's source-selection law and key separation live in
[Packaging](17-packaging.md#forge-neutral-source-trust). Evolution adds a separate promotion
decision. Each governance epoch explicitly fixes the promotion roster and threshold before use,
with no prescribed initial number; changing the paid team cannot change them. Its policy requires
independent approval from multiple people and tolerates its declared maintainer absences,
including the founder, without a personal veto or unilateral promotion credential. The same humans
and threshold may select the canonical source reference, but those
signatures are not interchangeable: selecting a Git object does not approve its artifacts,
evidence, recovery plan, or activation. Quorum removes the single-absent-founder bottleneck
without creating a shared key, founder veto, or unilateral recovery key.

#### The signed candidate and its effects

A future portable promotion envelope is the signed representation of Creation's Promotion
Request. It binds the governance epoch and replay boundary; exact source object and artifact
closure from [Packaging](17-packaging.md); versioned verification plan and receipt digests;
required Protected Region and owner verdicts; intended migrations, restarts, publications, and
other effects; and tested rollback, compensation, or forward-recovery coordinates. Each trustee
signs those exact bytes with a promotion credential distinct from source, CI-attestation, seed,
deployment, migration, and lifecycle credentials. CI and builders may produce evidence but never
hold quorum or effect authority.

The epoch's required signatures make an unchanged candidate eligible; they do not make a failing candidate true.
Missing mandatory evidence, deterministic failure, an adverse required verdict, stale state, or a
target owner's failed precondition blocks the Evolution regardless of votes. Every target owner
still authorizes and records its own live effect at the temporal boundary. Rewriting a Jujutsu
change, changing the Git object, artifacts, plan, or bound inputs invalidates affected evidence and
authorization.

#### Eligibility at the first effect

The envelope carries a unique promotion-attempt identity and monotonic sequence. Immediately
before the first live effect, the verifier rechecks the current epoch, every signer's eligibility,
quorum, replay and expiry state, withdrawal, and conflicts with another envelope for that attempt.
An unexecuted envelope from a replaced epoch or revoked seat loses eligibility unless the successor
epoch explicitly carries it forward; its signatures remain historical audit evidence.

Before the first effect, a trustee may withdraw and quorum is recomputed. A seat's conflicting signatures for
different candidate closures or effect sets under one attempt count toward neither once the
conflict is observed; pending eligibility is recomputed and the affected credentials enter
containment and governance review. The designed promotion coordinator and ledger atomically claim
the attempt and sequence before admitting the first effect, reject a stale or competing envelope,
and order later effect admission without taking any target owner's authority.

#### Recovery after an effect

Recovery, rollback, or compensation already bound into an active authorized attempt remains an
owner-executed recovery effect and cannot be delayed waiting for a new quorum vote. Withdrawal or an
epoch change after the first effect cannot erase the emitted effect, its audit record, or the bound
owner recovery authority. A conflict discovered only after that boundary cannot retroactively undo
the effect; it triggers credential containment and governance review, while every remaining
planned effect revalidates and may block. Deliberately selecting an older body as a later steady
state is a new governed Evolution, not a mutable-ref rewind.

#### Roster recovery and adoption

Key loss, compromise, or loss of quorum fails closed. Promotion-key rotation and roster membership
changes create a new governance epoch through the preceding epoch's threshold authorization. An
exceptional roster-recovery rule is valid only if that preceding epoch already authorized and
bound it; it is limited to reconstructing membership under declared failure conditions and cannot
approve a candidate or live effect. Revocation does not erase evidence that was valid in its
historical epoch. Founder absence, the epoch's declared tolerated unavailability, compromised-key
removal, total mirror loss, stale-envelope replay, conflicting signatures, and an unrecoverable
quorum must be rehearsed before this design can move from Designed to Delivered.

During early development, maintainers continue to collaborate through branches and reviews on
GitHub while exact-object checks and human approval remain procedural. The future protocol should
be implemented only after the forge-neutral gates in Packaging pass. Radicle can be added later
without changing candidate identity or Evolution semantics; adopting it early merely as an
experimental replica confers no canonical or promotion authority.

## Consequences

!!! success "Positive"
    Local change remains attributable, compatibility and recovery are candidate-bound, and failure
    can be contained before activation. The future threshold path permits maintainer continuity
    without making one forge, runner, shared key, or permanently present founder sovereign.

!!! failure "Negative"
    Rehearsal, coupled testing, and recovery checks add latency; schemas and external effects may
    demand forward recovery, and no autonomous update exists until all promotion boundaries exist.
    Governance epochs, separated credentials, portable receipts, and quorum-loss recovery add substantial
    operational and human ceremony before they can safely replace the early GitHub workflow.
