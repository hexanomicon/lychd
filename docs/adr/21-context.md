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

Layers 1–4 make the **Stable Floor**. A designed `prefix_digest` witnesses ordered content known
to LychD; it neither proves provider KV-cache reuse nor attention or latency improvement.

## Blocks and assembly

A complete designed Block has layer, key, text, and SHA-256 content hash, and the orchestrator
derives `prefix_digest` from ordered stable blocks. The current `Block` carries layer, key, and text;
the current `AssembledContext` exposes those blocks, bounded settled history, an indivisible
continuation, query, and known active context window, but no content or prefix digest. The First One
binds layer 1 as static instructions and its dynamic hook renders non-empty layers 2–4. State
becomes model history and Query the user prompt, so the six-layer account does not duplicate them
as instructions.

Assembly detaches nested history and continuation values from their callers. Cache reads and
model-history projections also detach mutable messages, so downstream edits cannot change the
retained assembly or the input against which its budget was checked. Immutable Blocks may be shared.

Context preserves its declared semantic order. Exact append-only transcript groups may extend a
reusable prefix for a compatible connector while all earlier wire serialization remains
byte-identical; rewritten summaries and replacement
[Execution Projection](28-workflow.md#execution-projections-for-procedural-agent-placements-designed)
values do not preserve that identity. Cache remains a connector/provider optimization, never a
Context source, authority, or receipt; Context does not reorder or pad admitted input merely to
obtain cache eligibility.

The run-id assembly cache lasts only for the process and releases after terminal Run settlement,
not when the session turn is written. Layer 3 snapshots are shared by exact environment key while
any referencing Run remains active; terminal settlement releases that Run's leases and evicts a
snapshot after its final reference. Durable conversation belongs to the session ledger and durable
suspension to [Graph](./24-graph.md).

## Grant-aware rebinding

Bridge first assembles enough field to enter its workflow, then assembles again inside `Converse`
after [Dispatcher](./22-dispatcher.md) grants the actual capability. Consent continuation also
reassembles after grant acquisition. The resolved generation profile's `max_context` takes priority
over the capability specification's discovered maximum.

Environment records only granted capability key (or `none`) and sorted warm/active capability keys.
Its key is `(session, capability binding, grant epoch)`. Bridge uses the Dispatcher-issued grant id
as the epoch in both `Converse` and consent continuation, so every fresh grant observes a fresh
warm-Coven snapshot even when it selects the same capability binding. Reassembly within the same
grant remains byte-stable; exact same-key snapshots can be shared, one Run cannot evict another's
lease, and the final referencing terminal settlement releases the snapshot. VRAM, power,
connectivity, and Sigil scope are absent; the Sigil belongs in
[`LychDDeps`](./20-agents.md#run-dependencies), where tools can enforce it rather than prompt prose.

## Governors

The present governors are twenty complete message groups by default and a 96,000-character cap.
With a grant window, the effective cap is the smaller configured cap or three characters per model
token: deliberately conservative, not tokenizer accounting. Assembly reserves layers 1–4, query,
and complete continuation before history. If they overflow, `ContextBudgetExceededError` stops the
run. Continuation never splits; remaining space retains newest complete groups, up to the turn
window, never cutting a request from response to keep an older fragment. A nonpositive turn window
retains no settled history and leaves required continuation intact.

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

Source influence and disclosure risk are separate facts. Transformation never relabels ancestry as
public; a residual-disclosure assessment says only what one exact recipient may receive for one
purpose under one threat model. Pseudonymized material remains private while a reversal or likely
linkage path exists. A distinctive private repository, diagnostic, or relationship graph may be an
authorized sanitized disclosure without being anonymous.

A **Privacy Cut** forms a new recipient- and purpose-specific sanitized branch without mutating raw
material or reusing continuation, serialized history, tool bodies, attachment projections, or
provider prefix-cache identity. Its `DisclosurePlan@1` binds the consumer kind and identity, purpose,
minimal-projection manifest digest plus an opaque restricted local ref, semantic invariants,
threat-model and retention profiles, maximum transmission/disclosure uses, and proposed remote
target; it does not embed source bytes or identities in broadly retained evidence. Every
transforming stage emits immutable non-authorizing
`TransformationReceipt` evidence. When stages compose, receipts form an ordered digest-bound chain
whose terminal receipt binds the exact final candidate and all parent receipts. A semantic Privacy
Agent proposes findings and typed operations only; a deterministic applicator creates any changed
candidate and terminal receipt. An independent local verifier emits `CutVerification@1`; Context
seals a `PrivacyCut@1` only when source, final candidate, plan, complete receipt chain, verifier
verdict, policy, and expiry all match. Security alone admits the exact wire/export branch.

Designed receipts retain digests, revisions, typed operations and safe category summaries—not raw
spans, credentials, subject names, filenames, material-parent identities, or reversal data. A Cut
that destroys the identifiers, dependency relations, citations, or diagnostics needed for its
declared task refuses that road rather than call privacy alone a success.

An irreversible Cut has no reversal map and promises no rehydration. A reversible Cut stores the
map only through an encrypted local `PseudonymMapLease@1`: the map itself enters no prompt, log,
checkpoint, receipt, or remote request; a checkpoint may retain only an opaque lease reference.
Context owns the lease lifecycle and a narrow rehydration port; a deployment-local Privacy Vault
alone holds encrypted map bytes and their per-lease data-encryption keys. The lease binds Cut, Run,
attempt, target/purpose, an unpredictable keyed token namespace,
source/candidate digests, key epoch, authorized rehydration station, expiry, and cryptographic
erasure. If its durability cannot cover the remote deadline and return window, a Pattern that
requires rehydration remains local or refuses. A missing, expired, or unrecoverable lease never
licenses reconstruction from raw history or retransmission under a new namespace.

The non-bearer lease's success path is `ACTIVE -> CLAIMED -> CONSUMED`. Expiry or revocation can
terminate either nonterminal state as `EXPIRED` or `REVOKED`; every terminal enters key destruction.
Claim is an idempotent compare-and-set over authorized
Principal/Sigil, Run, attempt, station, and quarantined-return digest; callers never receive the
map. Rehydration recognizes only exact lease-issued tokens that appeared in the disclosed candidate
and only at output-schema paths explicitly marked for their category, cardinality, and purpose. It
rejects invented, altered, cross-namespace, cross-category, wrong-path, over-cardinality, or
replayed tokens and never scans arbitrary prose for placeholder-shaped strings.

The port returns a candidate plus `RehydrationReceipt@1` binding Cut/lease, quarantined-return and
final digests, typed substitution counts, verifier/policy revisions, and the restored influence-
label digest without raw values. The result regains its original label, remains local, is validated
again, and cannot flow directly into an executable field, effect, public delivery, or another
remote call. Its `purge_at` is no later than the earliest source expiry, Cut expiry, or Composition
retention maximum. Mapping ciphertext uses a per-lease data key excluded from backup; cleanup
destroys that key and proves restored backup material is undecryptable rather than claiming every
physical backup byte was erased. If no accepted Vault profile is available, every durable remote
wait uses an irreversible Cut.

The accepted Vault profile must also contain plaintext during transformation and rehydration:
mapping pages are locked against swap or host swap is disabled; core/crash dumps and debugger
attachment are disabled; bounded buffers are zeroized; and traces, allocator diagnostics, and
support bundles exclude the map. Acceptance tests exercise crash and memory-pressure paths. Failure
to prove this profile disables reversible Cuts rather than weakening the erasure claim.

Current `Block` and `AssembledContext` carry no labels or source-lineage records. Conservative
aggregate labels, deterministic Censor, governed SQL/tool/artifact source adapters, immutable
end-to-end lineage, transformation receipts, semantic Privacy Agent, secret-free receipt
projection, Disclosure Plan, Cut Verification, pseudonym-map vault, sanitized Context branch, and
trusted Egress Gate remain undelivered.

## Typed Codex material projections (Designed)

Layer 2 will accept only explicit, attributed material references selected for one Run and Spell
placement. Each contribution binds an immutable artifact or contained workspace-relative source,
its content digest, normalized file kind/media type, classification and lineage, required/optional
status, byte/character budget, and an exact registered projection-profile revision. Typed local
configuration may select only already registered projection profiles, rules, and bounds. The
digest-bound material reference itself comes from the authorized Invocation or Scroll placement,
not global TOML; neither path carries source bytes or raw prompt text.

The first closed projection modes are `structure` and `verbatim`:

- `structure` is a deterministic parser-owned view, not an Agent summary. A Python profile may
  expose the module docstring, import facts, declared public symbols, class/function signatures,
  and stable source locations only when its exact profile says so. Parser and projection revisions
  participate in identity. Parse failure yields an explicit unavailable contribution or fails a
  required placement; it never falls back to full text.
- `verbatim` is an explicit request for exact decoded material under pinned encoding, newline, and
  line-provenance rules plus hard byte and character bounds. Truncation is declared by the profile
  and visible in the Block lineage, or the contribution refuses; it is never silently substituted
  for `structure`.

Rules are keyed by an admitted normalized file kind or media type, not by ambient package scans,
environment inference, arbitrary globs, Python import paths, or caller-supplied formatter code.
Content is read through the owning artifact/workspace boundary after digest and scope validation.
The resulting Blocks remain ordered, labelled, and attributable at the exact placement that asked
for them. A Reader projection grants no filesystem mutation; a Writer still needs a separate typed
tool/effect contract and Sigil authority.

Compression is also an explicit derived-material operation, never a hidden governor. A Compressor
cannot rewrite Identity, omit the non-negotiable Stable Floor, or turn missing fit into an
apparently complete answer. Its output is a new labelled Block and receipt linked to its sources,
profile, budget, retained invariants, and declared omissions; the uncompressed attributed material
remains owned by its source. If required material cannot fit without violating that contract,
assembly fails before inference.

Deterministic, non-model projection compaction may be part of an exact projection profile. Semantic
model compression is different: it is a separately resolved `AgentSpec`/Posture and Spell placement
with its own capability grant, typed result, budget, lineage, and explicit omissions. The
`ContextOrchestrator` never hides a recursive model call inside a formatter. A semantic summary
inherits its sources' privacy and instruction non-authority and cannot replace canonical source or
history truth.

## Execution Projection input (Designed)

At one explicitly declared procedural Agent placement, a Composition-owned and Pattern-pinned
[Execution Projection](28-workflow.md#execution-projections-for-procedural-agent-placements-designed)
may replace settled message history for that model call. Context receives the exact bounded,
attributed projection and fresh admitted observation projections from their owners; it preserves
their lineage, classification, revisions, declared omissions, and required/optional status, then
orders and budgets them with the Stable Floor and exact Query. Context does not infer the
projection schema from Graph state, decide domain truth, apply Agent operations, or silently
summarize missing material. Required state or observation input that cannot fit refuses before
inference.

Exclusion from one model call never deletes or relabels canonical sources, conversation history,
events, receipts, artifacts, or audit evidence. The Stable Floor, exact Query, and any indivisible
provider/tool or consent continuation remain governed inputs; the state-centric mode cannot replace
them. The delivered Layer 5 still carries governed complete Pydantic AI message groups. Execution
Projection rendering, observation envelopes, and a history-free procedural Agent call remain
Designed rather than current source behavior.

## Designed extensions

Codex may hydrate the typed material projections above; Karma may admit governed Archive results;
exact tokenization may replace character estimation; measured policy may select corpus, retrieval,
or iterative aggregation; richer Environment may record admitted hardware; and typed bounded
formatters may gain explicit layer placement. No projection profile, automatic CAG/RAG threshold,
dataset ingestion, repository-path inference, quality-drift injector, Compressor Agent, VRAM
estimator, or formatter extension surface currently exists.

## Correspondence

Context is the present surface of **the Spirit**: Identity, Codex, Environment, and Karma form the
floor; State carries movement; Query disturbs it. Selected memory is **Seed** and changing field
is **Flux**. The image explains shape; hashes, budgets, groups, and focused tests establish law.

## Consequences

!!! success "Positive"
    Stable material has one ordered receipt, history keeps whole logical groups, continuation stays
    intact, and capability can change the budget before inference.

!!! failure "Negative"
    Character estimates can underuse a window; snapshots vanish after their final active Run or a
    restart, process death loses the cache, and a stable prefix helps only when the provider actually
    supports it.

## Verification

`tests/unit/domain/cortex/test_context.py` covers newest complete groups, grant-bound environment
replacement, same-key sharing and release bounds, generation-window precedence, floor overflow,
and continuation. Bridge graph tests prove grant-id epoch binding and retain Context through graph
completion; worker tests prove release only after terminal Run settlement. Consent-resume tests cover
two-stage assembly and re-entry.
[State](../state-of-the-work.md) owns the public delivery boundary.

The full Privacy Cut profile additionally requires governed-source lineage; direct, quasi-, and
semantic identifier fixtures; isolation/linkage/inference and utility verdicts; transformer/
verifier disagreement; consumer and target substitution; secret-free receipt projection; fresh
namespace per new semantic attempt; bounded exact transport redelivery retaining the sealed
namespace while a fresh EgressDecision consumes its disclosure-use ceiling; and two-boot
`PseudonymMapLease@1` access, expiry, key rotation, loss, and verified purge without map material in
checkpoints, logs, backups, or remote payloads.
