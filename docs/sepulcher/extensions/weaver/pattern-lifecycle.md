---
title: Pattern lifecycle
icon: material/source-branch
---

# :material-source-branch: Pattern lifecycle

> _To change the score is to name another revision. The admitted Run keeps its first seal._

Within [Weaver](index.md), a Pattern revision is never silently rewritten. Weaver selects one
revision from an admitted Intent; the Invocation names that performance, and the canonical Run
carries its identity. If the registered executable no longer matches, execution fails instead of
substituting another workflow. [Pattern identity](../../../adr/28-workflow.md#pattern-identity)
owns the complete law.

## Identity before motion

`PatternManifest` records a renderer-neutral snapshot: schema version; URL-safe key and revision;
checkpoint-schema identifier; semantic stations with key, label, and kind; permitted edges with
declared endpoints; and a deterministic SHA-256 digest. The workflow lookup name is persisted
separately, although the current `Workflow` binding requires it to equal the manifest key.

Executable stations bind one-to-one to Python Graph node types. The manifest is authored beside
that Python and fingerprints the declared score; it is not a canonical intermediate
representation from which all behavior is compiled. Edge parity and return semantics must still
be established by source review and tests.

The registry is immutable after construction. It rejects duplicate workflow names and duplicate
`(key, revision)` pairs, considers non-default routes in declaration order, then falls back to its
first entry. Its two source-defined manifests are `bridge_chat@1`, the default with checkpoint
schema `bridge-chat-state-v1`, and `delegated_rite@1`, the `/delegate` route with
`delegated-rite-state-v1`. Construction performs no package scan.

??? example "The fixed registry in source"
    ```python
    --8<-- "src/lychd/agents/workflows/__init__.py:114:120"
    ```

    [Open the owning registry source](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py#L114-L120)

## Admission happens once

[Admission and ownership](../../../adr/28-workflow.md#admission-and-ownership) orders four
operations:

1. Validate and select the Pattern.
2. Create the canonical Run with the workflow name and exact manifest snapshot.
3. Retain the caller-owned initiating record under that Run id.
4. Publish one queue job keyed by Run and enqueue sequence.

Retention or enqueue failure conditionally marks an unclaimed queued Run failed and terminates its
event channel. If a worker already claimed an ambiguously published job, compensation yields
rather than overwriting that execution. The database and broker have no transactional outbox;
compensation and reconciliation remain explicit.

Execution and resume look up the persisted workflow name rather than routing the Intent again.
Before running, the worker validates registry presence, checksum, and equality with the persisted
manifest. A missing workflow fails as `unknown workflow`. A corrupt checksum, drifted declaration,
or unavailable revision fails as `pinned Pattern unavailable`. No default or newer Pattern
replaces it.

Checkpoint and suspension mechanics belong to [Stasis and return](stasis-and-return.md).
`AgentJob` and provider boundaries belong to [Delegated agents](delegated-agents.md).

## A new score is a new revision

The current registry preserves one executable revision per workflow name. A saved manifest proves
what a Run admitted; it does not preserve historical Python. Continuing older work requires a
future multi-revision registry with declared compatibility, migration, drain, or refusal.

[Topology-A](../../../state-of-the-work.md#topology-a-local-runs) local runs are **Available** and
pin manifests. [Extension activation](../../../state-of-the-work.md#extension-activation-contributions)
is **Partial**, but no Pattern store or public contribution API is delivered.

Future publication follows the [Pattern contribution](../../../adr/28-workflow.md#pattern-contribution)
law: an inert candidate declares identity, contracts, continuity, and evidence; validation and
review may publish an immutable revision through a selected shaped store and freeze that process
generation. The current `Workflow` type remains internal and pre-v1, not a third-party ABI.

A future scheduler would create an Occurrence and submit it through ordinary revision-pinned
admission. Its timer never calls a Graph node, model, or container directly; no Occurrence service
is implemented.
