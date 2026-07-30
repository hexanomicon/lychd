---
title: 18. Evolution
icon: material/refresh
---

# :material-refresh: 18. Evolution

!!! abstract "Context and Problem Statement"
    Ouroboros is the contract for adopting upstream source while retaining deliberate local
    changes. An update can alter source, dependencies, configuration, schemas, artifacts, and
    services; replacing files proves neither compatibility nor recovery. The name does not assert
    an autonomous updater.

## Requirements

- Bind installed and upstream revisions, local delta, locks, configuration, extension set, schema
  head, and platform.
- Build, merge, migration rehearsal, and verification occur in an inactive candidate.
- Test the selected built-ins and private in-process extensions with the candidate Core; pre-v1
  internal imports are not a stable API.
- Keep source, package, database, runtime, and external recovery with their own owners.
- Drift, conflict, missing evidence, and exhausted repair budgets block promotion; every live
  effect rechecks state and authority.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| Upgrade the active environment in place | Rejected | Acquisition, resolution, migration, and activation share a running body without recovery proof. |
| Never update | Rejected | An immutable artifact need not abandon reviewed security and compatibility work. |
| Inactive candidate with owned promotion | Selected design | Local work survives only when it still verifies; activation remains separately authorized. |

## Decision Outcome

**Ouroboros** applies [Creation](16-creation.md) and [Packaging](17-packaging.md) to a Core update:

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
source repository. Any conflict or base drift blocks promotion. Bounded repair produces a new
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

## Consequences

!!! success "Positive"
    Local change remains attributable, compatibility and recovery are candidate-bound, and failure
    can be contained before activation.

!!! failure "Negative"
    Rehearsal, coupled testing, and recovery checks add latency; schemas and external effects may
    demand forward recovery, and no autonomous update exists until all promotion boundaries exist.
