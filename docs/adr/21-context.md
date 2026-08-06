---
title: 21. Context
icon: material/text-box-multiple-outline
---

# :material-text-box-multiple-outline: 21. Context

!!! abstract "Context"
    An Agent cannot receive all LychD knows. It receives a bounded, ordered field in which stable
    law, present environment, completed history, required continuation, and query survive changing
    model limits. If its non-negotiable material does not fit, assembly fails before inference; it
    never hides truncation in an attractive answer.

## Requirements

- Context is typed, ordered, bounded, and attributable rather than a hidden mutable prompt bag.
- Stable material has a reproducible digest, while history and query remain explicitly volatile.
- The Dispatcher-selected capability must rebind context before inference; a Privacy Cut must not
  reuse raw history, provider cache identity, or declassification authority.

## Considered Options

| Option | Decision | Why |
| --- | --- | --- |
| One mutable accumulated prompt | Rejected | It hides order, limits, lineage, and authority behind incidental text. |
| Static global context limit | Rejected | The executing grant, not a guess, determines the usable window. |
| Layered assembly with conservative governors | Selected | It makes floor, history, continuation, and query independently inspectable and bounded. |

## Decision

`ContextOrchestrator` owns the active field as typed, hashed `Block`s:

| Layer | Name | Current content |
| ---: | --- | --- |
| 1 | Identity | The First One's fixed instructions. |
| 2 | Codex | Reserved and empty. |
| 3 | Environment | Granted capability and observed warm Coven. |
| 4 | Karma | Session-keyed, reserved and empty. |
| 5 | State | Governed complete Pydantic AI message groups. |
| 6 | Query | Current request. |

Layers 1–4 make the **Stable Floor**. Its `prefix_digest` witnesses ordered content known to
LychD; it neither proves provider KV-cache reuse nor attention or latency improvement.

## Blocks and assembly

Every Block has layer, key, text, and SHA-256 content hash. The orchestrator sorts stable blocks
by `(layer, key)`, hashes ordered hashes into `prefix_digest`, then adds State and Query. The First
One binds layer 1 as static instructions and its dynamic hook renders non-empty layers 2–4. State
becomes model history and Query the user prompt, so the six-layer account does not duplicate them
as instructions.

`AssembledContext` exposes all blocks, digest, bounded settled history, an indivisible continuation
when present, query, and known active context window. The run-id assembly cache lasts only for the
process and releases after settlement. Layer 3's separate environment snapshot cache lasts for the
process with no current eviction. Durable conversation belongs to the session ledger and durable
suspension to [Graph](./24-graph.md).

## Privatization and the Privacy Cut

Designed `PrivatizationLabel` and immutable source lineage attach to every Block. A label carries
class (`public`, `internal`, `private`, `restricted`), policy weight, categories, known subject or
namespace, material parents, and handling constraints; it does not substitute for factual trust,
instruction authority, Sigil scope, consent, or quarantine.

`AssembledContext` joins labels for exact blocks, history groups, continuation, query, tool
material, and artifact projections entering one model call. It preserves highest class and weight
plus the union of categories, subjects, and material parents. Copying, summary, aggregation,
embedding, captioning, transcription, and model transformation do not lower influence. A producer
may identify exact contributors to avoid unrelated overtaint; unknown lineage is `restricted` at
egress.

A **Privacy Cut** forms a new sanitized branch without mutating raw material or reusing
continuation, serialized history, tool bodies, attachment projections, or provider prefix-cache
identity. Its pseudonym map is restricted, local to one Run and attempt, and never enters prompt,
log, checkpoint, receipt, or provider request. Its `TransformationReceipt` binds source and
candidate digests, transformer/policy revisions, operations, removed categories, residual label,
uncertainty, utility loss, and expiry without raw spans. A Cut that destroys the identifiers,
dependency relations, or diagnostics needed for its declared task must refuse remote formation
rather than call privacy alone a success. Transformations provide evidence; only Security's egress
decision admits that exact branch to a Portal.

Current `Block` and `AssembledContext` carry labels and a conservative aggregate join. Present
query, history, or continuation material without supplied lineage defaults to `restricted` and
`local_only`; empty placeholders do not taint the call. A deterministic local Censor rebuilds
bounded JSON-like values, redacts the first typed identifier set, and issues digest-, revision-,
count-, residual-label-, and expiry-bound evidence that is explicitly ineligible for egress and
claims no removed category. Governed SQL/tool/artifact source adapters, immutable end-to-end
lineage, semantic Privacy Agent, pseudonym map, sanitized Context branch, Privacy Cut verifier, and
Portal Egress Gate remain undelivered.

## Grant-aware rebinding

Bridge first assembles enough field to enter its workflow, then assembles again inside `Converse`
after [Dispatcher](./22-dispatcher.md) grants the actual capability. Consent continuation also
reassembles after grant acquisition. The resolved generation profile's `max_context` takes priority
over the capability specification's discovered maximum.

Environment records only granted capability key (or `none`) and sorted warm/active capability keys.
Its key is `(session, capability binding, grant epoch)`, but the Bridge presently supplies neither
grant id nor changing epoch: both paths use `0`. A later grant to the same binding can reuse an
older warm-Coven snapshot, and snapshots accumulate for the process lifetime. Fresh-grant rebinding
and cleanup remain gaps. VRAM, power, connectivity, and Sigil scope are absent; the Sigil belongs
in [`LychDDeps`](./20-agents.md#run-dependencies), where tools can enforce it rather than prompt
prose.

## Governors

The present governors are twenty complete message groups by default and a 96,000-character cap.
With a grant window, the effective cap is the smaller configured cap or three characters per model
token: deliberately conservative, not tokenizer accounting. Assembly reserves layers 1–4, query,
and complete continuation before history. If they overflow, `ContextBudgetExceededError` stops the
run. Continuation never splits; remaining space retains newest complete groups, up to the turn
window, never cutting a request from response to keep an older fragment.

Bridge separately gives Pydantic AI the actual window remaining after output reservation.
Pydantic AI pre-counts only for models implementing `count_tokens`; current OpenAI-compatible
models instead enforce provider-reported input usage after a response. The character governor and
usage limit are therefore independent bounds, not exact cross-provider token equivalence or a
universal pre-request fence.

## Stable history

Completed messages group by LychD `run_id`; legacy messages fall back to request boundaries. A
consent pause holds the current logical-turn suffix apart from settled history. Resume re-bounds
settled history under the new grant and provides its required continuation unchanged. Thus an old
provider's live objects and assumptions do not cross the park. ADR 25 owns consent record and
verdict order; this ADR owns only field shape and budget after re-entry.

## Designed extensions

Codex may later hydrate path-selected law/task material; Karma may admit governed Archive results;
exact tokenization may replace character estimation; measured policy may select corpus, retrieval,
or iterative aggregation; richer Environment may record admitted hardware; and typed bounded
formatters may gain explicit layer placement. No automatic CAG/RAG threshold, dataset ingestion,
repository-path inference, quality-drift injector, prompt compressor, VRAM estimator, or formatter
extension surface currently exists.

## Correspondence

Context is the present surface of **the Spirit**: Identity, Codex, Environment, and Karma form the
floor; State carries movement; Query disturbs it. Selected memory is **Seed** and changing field
is **Flux**. The image explains shape; hashes, budgets, groups, and focused tests establish law.

## Consequences

!!! success "Positive"
    Stable material has one ordered receipt, history keeps whole logical groups, continuation stays
    intact, and capability can change the budget before inference.

!!! failure "Negative"
    Character estimates can underuse a window; caches vanish on restart, snapshot epochs can go
    stale, and a stable prefix helps only when the provider actually supports it.

## Verification

`tests/unit/domain/cortex/test_context.py` covers newest complete groups, grant-bound environment
replacement, generation-window precedence, floor overflow, and continuation. Bridge graph and
consent-resume tests cover two-stage assembly and re-entry. [State](../state-of-the-work.md) owns
the public delivery boundary.
