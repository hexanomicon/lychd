---
title: Scroll and Pattern lifecycle
icon: material/source-branch-sync
---

# :material-source-branch-sync: Scroll and Pattern lifecycle

> _The ink has dried. Write the next score on fresh parchment._

A casting keeps the score it was admitted to perform. Within [Spellweaver](index.md), a Scroll
is one immutable Pattern revision: admission selects it from the Intent, the Invocation names
the casting, and the canonical Run retains its identity. If the registered executable stops
matching, execution fails rather than substituting another workflow. A Scroll is never silently
rewritten. [Pattern identity](../../../adr/28-workflow.md#pattern-identity) owns the full law.

## Identity before motion

`PatternManifest` records a renderer-neutral snapshot: schema version; URL-safe key and revision;
opaque reviewed implementation revision; checkpoint-schema identifier; declared entry station; semantic stations with key,
label, and kind; permitted edges with declared endpoints; and a deterministic SHA-256 digest. The workflow lookup name is persisted
separately, although the current `Workflow` binding requires it to equal the manifest key.

Retained v2 snapshots must pass the shared declarative checks as well as their checksum: typed
station and edge fields, known kinds and permission relations, unique keys and semantic edges,
one executable entry, and declared endpoints. A recomputed digest cannot make malformed score
data valid. Blockworld admission refuses it before freezing, and Orb withholds Pattern exactness.
Those checks do not resolve executable implementations; execution still requires exact registry
equality. Additional top-level metadata remains outside the v2 checksum and prevents that equality.

Every executable station binds one-to-one to a Python Graph node type, and the declared entry
must bind the actual start node. The manifest lives beside that Python and fingerprints the
score; it is not an intermediate representation that compiles all behavior. Its implementation
revision (`py.1` for original built-ins, `py.2` for configured Bridge) records a reviewed
compatibility closure. Change that revision or the public Pattern revision when new behavior
cannot safely resume old state. Neither detects source edits automatically, so source review
and tests must still establish edge parity and return semantics.

The [private v2 adapter](../../../adr/28-workflow.md#private-v2-adapter) derives a Scroll-private
`legacy_inline` identity for each executable station and fingerprints its Python node binding in
a boot-local `internal-v0` lock. Exact lookup refuses a binding that differs from that assembly.
The terminal remains Graph `End`, and the frozen v2 manifest snapshot and digest stay unchanged.
This lock is neither persisted on Run nor exposed by Loom/Orb. It does not establish source
equivalence or compatibility across boots; the portable Spell catalogue remains a separate contract.

The catalogue is immutable after construction. It rejects duplicate `(key, revision)` pairs,
requires an explicit active revision when one name has alternatives, requires explicit non-default
route precedence, and names its default. Construction performs no package scan. The current
source-defined manifests retain these routes:

| Pattern revision | Admission route | Checkpoint schema |
| --- | --- | --- |
| `bridge_chat@1` | Unconfigured default | `bridge-chat-state-v1` |
| `bridge_chat@2` | [Configured exact capability](index.md#choose-a-bridge-capability) | `bridge-chat-state-v2` |
| `bridge_chat@3` | Configured public Archive and exact capability | `bridge-archive-state-v1` |
| `bridge_chat@4` | [Configured Scout](../scout.md#public-page-answers), authenticated command and exact local capability | `bridge-scout-state-v1` |
| `delegated_rite@1` | Exact `/delegate` command token | `delegated-rite-state-v1` |
| `delegated_rite@2` | Configured exact runtime and `/delegate` command token | `delegated-rite-state-v2` |

[The owning registry source](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py)
defines the retained revisions and their activation policy.

## Admission happens once

[Admission and ownership](../../../adr/28-workflow.md#admission-and-ownership) orders four
operations:

1. Validate and select the Pattern.
2. Atomically create the canonical Run and initial durable delivery with the exact manifest snapshot.
3. Retain the caller-owned initiating record while that delivery is held, then release it.
4. Publish one queue job keyed by Run and enqueue sequence; relay the same key when unavailable.

A failed retention can settle only the exact held generation that has not been released. If a
release commits and then raises, the delivery row resolves the uncertainty: the work remains
admitted, and compensation cannot overwrite `PENDING`. Broker failure likewise leaves the Run
queued with its exact pending delivery. PostgreSQL and SAQ do not share a distributed transaction;
startup reconciliation and the process-owned relay probe and republish that idempotent key without
inventing a new Pattern hop.

Execution and resume look up the exact persisted Pattern key and revision rather than routing the
Intent again; a retained revision need not remain active for new admission. Before running, the
worker validates checksum, workflow-name binding, implementation revision, and equality with that
exact registered manifest. A corrupt checksum, changed declaration or implementation closure,
missing workflow, or unavailable revision fails as
`pinned Pattern unavailable`. No default or newer Pattern replaces it.

Checkpoint and suspension mechanics belong to [Stasis and return](stasis-and-return.md).
`AgentJob` and provider boundaries belong to [Delegated agents](delegated-agents.md).

## Portable contracts and configuration

Each semantic station currently behaves like a legacy inline Spell placement: key, label, kind,
implementation closure, and edges are bound only inside its Scroll. There is no independent Spell
identity or portable catalogue. A future portable Scroll pins exact authority-qualified Spell
contract revisions and digests; a receiver-owned Resolution Lock separately binds each placement
to an exact local implementation. Admission reports every unknown, unavailable, incompatible,
revoked, or unauthorized placement instead of substituting a similar name or newer revision. A
future Loom may show the absence only in an inert resolution report; an unresolved placement never
enters an executable Graph.

Configuration follows the closed spine in [ADR 28](../../../adr/28-workflow.md#configuration-to-casting-spine):
TOML selects exact registered identities and bounded policy only. Never place import paths, node
classes, graph edges, prompts, source bytes, credentials, or live handles in a Scroll selector.
Unknown ids and missing exact revisions are refusal, not cues for package scanning or nearest-name
fallback.

## Human-attested material stops at a Gate

Spellweaver does not infer human authorship from a commit name, account, writing style, or a human
approval. A future trusted authoring surface records an [Authorship Attestation and Protected
Region](../../../adr/28-workflow.md#authorship-provenance-and-protected-regions) against the exact
artifact revision, stable region id, and content digest. Existing material remains `unknown` until
a human attests its current form.

```text
base artifact + protected-region manifest + candidate
                         |
                  target-owner diff
                    /          \
             no overlap       overlap
                 |               |
          ordinary gates    exact live HitL
                                 |
                         target-owner promotion
```

An Agent may prepare a replacement in its candidate workspace. It cannot change the active region,
remove protection by deleting a source marker, or reuse a verdict from another base or patch. The
live review names every touched region, old and replacement digests, and an authorized exact-diff
artifact. A changed base or candidate, a newly touched region, or a changed target effect
invalidates the call and requires another verdict.

Promotion preserves the distinction between approval and authorship. A wholly Agent-written
replacement remains `agent_generated`; interleaved retained human text and Agent work is `mixed`.
An approved move may preserve the origin of unchanged human-attested content. A rewritten exact
digest becomes `human_attested` only through a fresh human authorship attestation.

Visible comments, front matter, and Loom decoration are projections of the target-owner manifest,
not enforcement. A compliant effectful Agent therefore works through Creation's candidate surface;
a direct writer with authority over the active checkout bypasses Spellweaver and cannot claim this
protection. No attestation store, protected-region resolver, authoring UI, or exact diff review card
is delivered. [State of Work](../../../state-of-the-work.md#smith-forge-promotion) owns that
boundary.

## A new score is a new revision

A new Invocation can vary a prompt, source `ArtifactRef`, requested language, target profile,
or finish boundary only when the existing Scroll's typed schema already admits that value.
Changing the score itself—adding a station, edge, Spell contract, authority ceiling, or required
model—creates a new immutable revision. If one Invocation finishes at an accepted intermediate
boundary, continuing from its artifact starts a new forward Invocation. It never resurrects the
terminal Run.

The current catalogue can preserve multiple executable revisions per workflow name. Active routing
is explicit; a saved Run continues through its exact registered revision even after activation moves
forward. The catalogue is still source-built and preserves no historical Python by itself. Removing
old code makes that revision unavailable: affected Runs fail as `pinned Pattern unavailable`.
Automatic compatibility proof, durable publication, drain, and migration remain future work.

[Topology-A](../../../state-of-the-work.md#topology-a-local-runs) local runs are **Available** and
pin manifests. [Extension activation](../../../state-of-the-work.md#extension-activation-contributions)
is **Partial**, but no Pattern store or public contribution API is delivered.

Future publication follows the [Pattern contribution](../../../adr/28-workflow.md#pattern-contribution)
law: inert Scroll and Spell-contract candidates declare identity, continuity, and evidence;
executable Spell implementations register through a separate owner. Validation and review may
publish an immutable revision, bind an implementation, and activate a new process generation only
as distinct effects. An A2A teaching bundle reaches this path only through
[Assimilation](../../../adr/35-assimilation.md#teaching-a-missing-spell). The current `Workflow`
type remains internal and pre-v1, not a third-party ABI.

Current code or contribution changes require controlled Evolution and Vessel/catalogue
replacement; this is not Reanimation. A future declarative-only Scroll may activate without a
restart only after all required implementations already exist and an atomic durable catalogue
generation mechanism is proved.

A future scheduler would create an Occurrence and submit it through ordinary revision-pinned
admission. Its timer never calls a Graph node, model, or container directly. [Scheduling and
service classes](scheduling-and-service-classes.md) owns that temporal contract and routes its
implementation evidence.
