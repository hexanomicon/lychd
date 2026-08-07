---
title: Pattern lifecycle
icon: material/source-branch-sync
---

# :material-source-branch-sync: Pattern lifecycle

> _To change the score is to name another revision. The admitted Run keeps its first seal._

Within [Weaver](index.md), a Pattern revision is never silently rewritten. Weaver selects one
revision from an admitted Intent; the Invocation names that performance, and the canonical Run
carries its identity. If the registered executable no longer matches, execution fails instead of
substituting another workflow. [Pattern identity](../../../adr/28-workflow.md#pattern-identity)
owns the complete law.

## Identity before motion

`PatternManifest` records a renderer-neutral snapshot: schema version; URL-safe key and revision;
opaque reviewed implementation revision; checkpoint-schema identifier; declared entry station; semantic stations with key,
label, and kind; permitted edges with declared endpoints; and a deterministic SHA-256 digest. The workflow lookup name is persisted
separately, although the current `Workflow` binding requires it to equal the manifest key.

Executable stations bind one-to-one to Python Graph node types, and the declared entry must bind the
actual Graph start node. The manifest is authored beside
that Python and fingerprints the declared score; it is not a canonical intermediate
representation from which all behavior is compiled. The implementation revision (`py.1` for both
built-ins) records a reviewed compatibility closure: change it or the public Pattern revision when
new behavior cannot safely resume old state. It does not automatically detect source edits. Edge
parity and return semantics must still be established by source review and tests.

The catalogue is immutable after construction. It rejects duplicate `(key, revision)` pairs,
requires an explicit active revision when one name has alternatives, requires explicit non-default
route precedence, and names its default. Its two current source-defined manifests are
`bridge_chat@1`, the default with checkpoint schema `bridge-chat-state-v1`, and
`delegated_rite@1`, the `/delegate` route with `delegated-rite-state-v1`. Construction performs no
package scan.

??? example "The fixed registry in source"
    ```python
    --8<-- "src/lychd/agents/workflows/__init__.py:191:202"
    ```

    [Open the owning registry source](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py#L191-L202)

## Admission happens once

[Admission and ownership](../../../adr/28-workflow.md#admission-and-ownership) orders four
operations:

1. Validate and select the Pattern.
2. Atomically create the canonical Run and initial durable delivery with the exact manifest snapshot.
3. Retain the caller-owned initiating record while that delivery is held, then release it.
4. Publish one queue job keyed by Run and enqueue sequence; relay the same key when unavailable.

Retention failure settles only an exact unreleased held generation. A release call that commits and
then raises is resolved from the delivery row and remains admitted; compensation cannot overwrite
`PENDING`. Broker failure leaves the admitted Run queued with its exact pending delivery. PostgreSQL and SAQ are not one distributed transaction;
startup reconciliation and the process-owned relay probe and republish the idempotent delivery key
without fabricating a new Pattern hop.

Execution and resume look up the exact persisted Pattern key and revision rather than routing the
Intent again; a retained revision need not remain active for new admission. Before running, the
worker validates checksum, workflow-name binding, implementation revision, and equality with that
exact registered manifest. A corrupt checksum, drifted declaration or implementation closure,
missing workflow, or unavailable revision fails as
`pinned Pattern unavailable`. No default or newer Pattern replaces it.

Checkpoint and suspension mechanics belong to [Stasis and return](stasis-and-return.md).
`AgentJob` and provider boundaries belong to [Delegated agents](delegated-agents.md).

## A new score is a new revision

The current catalogue can preserve multiple executable revisions per workflow name. Active routing
is explicit; a saved Run continues through its exact registered revision even after activation moves
forward. The catalogue is still source-built and preserves no historical Python by itself. Removing
old code makes that revision unavailable; automatic compatibility proof, durable publication,
migration, drain, or refusal remain future work.

[Topology-A](../../../state-of-the-work.md#topology-a-local-runs) local runs are **Available** and
pin manifests. [Extension activation](../../../state-of-the-work.md#extension-activation-contributions)
is **Partial**, but no Pattern store or public contribution API is delivered.

Future publication follows the [Pattern contribution](../../../adr/28-workflow.md#pattern-contribution)
law: an inert candidate declares identity, contracts, continuity, and evidence; validation and
review may publish an immutable revision through a selected shaped store and freeze that process
generation. The current `Workflow` type remains internal and pre-v1, not a third-party ABI.

A future scheduler would create an Occurrence and submit it through ordinary revision-pinned
admission. Its timer never calls a Graph node, model, or container directly. [Scheduling and
service classes](scheduling-and-service-classes.md) owns the designed temporal contract; no
Occurrence service is implemented.
