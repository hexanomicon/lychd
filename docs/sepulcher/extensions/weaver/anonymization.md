---
title: Anonymization, taint, and egress
icon: material/eye-lock-outline
---

# :material-eye-lock-outline: Anonymization, taint, and egress

> _Let the message cross the sea wearing a borrowed name._

A workflow can copy sensitive material before it ever reaches a Portal Spell placement.
Spellweaver therefore carries privacy lineage through the whole Pattern and creates a new,
sanitized branch before remote inference. [Context](../../../adr/21-context.md#privatization-and-the-privacy-cut)
owns labels and the Privacy Cut; [Security](../../../adr/09-security.md#portal-privatization-and-egress)
owns declassification and refusal. This page follows that material through the score, from its
local source to a checked return.

!!! warning "Egress remains closed"
    Context Blocks now carry conservative influence labels. A bounded offline diagnostic profile
    can redact, independently verify, and seal an irreversible candidate in memory. It cannot
    anonymize arbitrary private context or authorize its transmission. The semantic Privacy Agent,
    provider-specific sanitized branch, and Portal Egress Gate remain undelivered. Dispatcher
    still quarantines both family and direct-key Portal dispatch.

## Run the bounded offline proof

From a development checkout with its dependencies installed:

```sh
uv run --locked python scripts/privacy_probe.py --show-candidate
```

The probe uses only a public synthetic fixture, touches all six outbound lanes, verifies the
sealed candidate, and prints an opaque event identifier and the sanitized fixture. Omitting
`--show-candidate` prints only the identifier. It reads no private files, runs no model and sends
nothing. It is an engineering probe outside Pulse's closed command grammar.

The `closed-diagnostic@1` API accepts one sensitive owner-value slot inside an exact public
diagnostic grammar. Every character must be covered; dependency, diagnostic, status and citation
positions must survive. Lineage metadata is bounded without dropping ancestry. Unknown lineage,
forbidden categories, uncovered text, altered evidence or expired seals
refuse preparation. A caller cannot substitute a successful detector scan for these checks.
The raw branch stays unchanged and labelled; the authority and its seals are process-local.
Restart, real provider serialization, transmission budgets and semantic privacy need their
separate owners. [State of Work](../../../state-of-the-work.md#context-privatization-and-portal-egress)
records the tested boundary.

## Labels begin at the source

Classification must accompany values as they leave storage. Domain and repository ports attach
table and column defaults, row- or subject-specific policy, and query lineage before values reach
Context; SQL itself is not the classifier. Computed fields inherit the values that formed them.
Unknown or raw access is restricted at the governed boundary.

Tools declare whether output introduces a sensitive source, inherits or joins inputs, remains
local-only, proposes sanitization, or enters quarantine. A `sensitive` annotation warns the
contract; it does not become a prompt hint that the model may ignore.

The same rule covers screenshots, filenames, EXIF, OCR, transcripts, captions, embeddings, model
summaries, checkpoints, and delegated results. A derivative does not launder its source.

## One cut, two contexts

The handoff proceeds in this order:

1. **Governed inputs** — query · SQL · tools · memory · artifacts.
2. **Join labels and lineage.**
3. **DisclosurePlan@1** — consumer · purpose · minimum projection.
4. **Deterministic Censor** — candidate + TransformationReceipt.
5. **Local Privacy Agent** — proposal/findings only.
6. **Deterministic applicator** — final candidate + chained receipt.
7. **Independent verifier** — CutVerification@1.
8. **Privacy Cut** — new Context branch.
9. **Security Egress Gate** — exact target and wire payload.
10. **Portal · A2A · remote delegate.**
11. **Quarantined return.**

The raw branch remains local and labelled. The Privacy Cut rebuilds every field that will reach the
consumer/target: Portal instructions/history/query/tools/options, A2A values/envelope/ArtifactRefs,
or delegated workspace/artifact metadata and content. It never reuses raw continuation objects,
ambient workspace state, or a prefix-cache key.

The Cut may keep a lease-minted opaque telephone token stable within that branch; `<phone_1>` is
only explanatory notation, never an accepted token format. An irreversible Cut retains no reversal
map and cannot promise rehydration. A reversible Cut puts the map in an encrypted local
`PseudonymMapLease@1`; only an opaque lease reference may survive a checkpoint. The lease is bound
to Cut, Run, attempt, consumer/purpose, keyed token namespace, digests, key epoch, authorized
rehydration station, expiry, and cryptographic erasure. Another Cut receives another namespace. If
that lease cannot survive the declared remote deadline and return window, the Pattern stays local
or accepts a redaction-only result explicitly.

## The leverage of a local boundary

The **local anonymizer** combines a deterministic Censor, local Privacy Agent, verifier, and
Privacy Cut. The **local bastion** combines Coffin supervision, the Portal Egress Gate, and Provider
Gate. Together they can make inexpensive or subsidized remote reasoning admissible for a delegated
coding agent: one named runtime receives a useful sanitized task projection under job, destination,
model, time, token, and spend bounds.

The raw checkout, credentials, identity and pseudonym maps, and promotion authority remain local.
Returned candidates enter quarantine before local rehydration, testing, and admission. This economy
depends on both utility and an attested exit: if the Cut cannot preserve enough program structure
and diagnostic meaning, or the bastion cannot attest the exact crossing, the work stays local. No
single model may certify its own sanitization.

## Preserve the question through the Cut { #preserve-the-coding-question }

To prepare [Creation's delegated branch](creation.md#cli-delegation-branch), first identify the
distinctions the recipient needs to solve the task. A minimal module interface, dependency
relation, synthetic failing fixture, and expected behavior may suffice. The projection need not
include the whole repository, its history, or the parent's conversation. Exact spelling or bytes
can themselves be part of a defect, however. If replacing an identifier destroys the question,
use an adequate synthetic reproducer or keep that work local.

Independent Cut verification examines the same candidate projection for disclosure and utility,
keeping its findings separately attributable. Disclosure asks what the declared recipient could
identify, link, infer, or learn about credentials. Utility asks whether the coding question is
still answerable. Each finding names the exact offending or missing relation and a bounded
proposed repair. These are distinct obligations, not a requirement for two more agents on top of
the independent verifier. The admitted plan may add adversarial reviewers when warranted;
independence from the transformer remains required. A repaired candidate receives renewed
verification, including both findings where affected. Agreement cannot compensate for either
failed obligation or replace the Egress Gate.

For the dossier exporter, replacing every record ID with one category label can hide names while
merging distinct records. Giving every occurrence a different token can instead sever repeated
references to the same record. A useful projection preserves the required equality and inequality
relations inside its scoped namespace, and keeps accepted, unresolved, and unknown states distinct.
The receiving coding agent sees only that admitted projection. A local verifier checks the result
against the original preservation criteria after any permitted rehydration.

The return can stay small too: a repair to the synthetic reproducer, or a structured proposal
that a local worker applies to the real base under Creation's checks. Returning reversible source
changes requires more. The format must declare substitution positions and provide a validated
mapping to that base; whole-patch search-and-replace is not that contract. When the requested
return cannot meet those conditions, choose the proposal route or keep construction local.

Prepare synthetic Cases before admitting a remote road:

| Case | Required observation |
| --- | --- |
| Repeated identifier and two distinct identifiers | Required references remain consistent; distinct source records are not merged. |
| A path or diagnostic carries an identifying value | The whole outbound envelope is assessed, including metadata and errors. |
| Redaction removes the premise of a failing test | Utility review refuses that projection; narrow the task or keep it local. |
| A returned placeholder belongs to another Cut or an undeclared field | Rehydration refuses it without exposing the local map. |
| A returned patch attempts to reinterpret instructions or invoke an effect | Quarantine retains it as candidate data; it grants no action. |

Compare the declared local and sanitized task forms on these obligations as well as cost and
repair quality. A cheaper answer that lost the defect or disclosed a protected relation is not a
successful offload. These are proposed acceptance Cases, not executed privacy or utility receipts.

Presidio's [anonymizer operators](https://presidio.dataprivacystack.org/anonymizer/) provide a
concrete external comparison: replacement defaults can use one entity-type label, and maintaining
relations across transformations needs explicit handling. That motivates the identity Cases above;
it does not establish LychD's Cut, map lease, or declassification. Detector/operator choice remains
a future implementation decision under the existing owners.

## Transformations are evidence

| Act | Result |
| --- | --- |
| Redact | Remove a value without a reversal map |
| Pseudonymize | Replace it with a scoped token while a local map exists |
| Generalize | Reduce precision while preserving useful meaning |
| Anonymize | Meet a declared residual-risk policy and threat model |

None grants egress by itself. The [ordered Cut sequence](#one-cut-two-contexts) preserves an
exact transformation-receipt chain and independent `CutVerification@1` before Context seals the
branch and Security decides its exit. No component upgrades its own claim into permission; the
[Context contract](../../../adr/21-context.md#privatization-and-the-privacy-cut) keeps their exact
roles separate.

The source's influence survives a successful disclosure assessment. That success does not
relabel a private source or its derivatives as public. Pseudonymized material remains private
while reversal or likely linkage is possible. Private code can therefore qualify for an
authorized sanitized disclosure without becoming anonymous.

Deterministic work runs first in the designed sequence. A future Censor rebuilds bounded JSON-like
values and redacts secret-shaped fields, JWTs, PEM private keys, emails, telephones, IPv4 addresses,
and UUIDs with typed placeholders. That general detector-backed Censor is not delivered; the
current closed diagnostic profile uses explicitly partitioned spans. Bank and payment identifiers,
IPv6, long numeric ids, suspicious high-entropy strings, normalization policy, and semantic
combinations remain later detector work. Typed placeholders matter: an amount, date, telephone,
and order id do not carry the same meaning.

Presidio's [official FAQ](https://github.com/data-privacy-stack/presidio/blob/main/docs/faq.md)
explicitly identifies false negatives and makes no promise to find every sensitive value. Its
detectors and operators can inform later profiles; a detector result cannot certify this whole
disclosure boundary.

A local Privacy Agent handles semantic and quasi-identifiers that rules may miss. It can say
“this combination still identifies a household” and propose a narrower representation. It cannot
lower a label, call a Portal, or treat its own confidence as permission.

## Test the recipient's threat model

Masking visible identifiers is not a sufficient privacy claim. The `DisclosurePlan@1` names every
relevant entity that may reasonably use auxiliary information: provider and subprocessors, A2A
peer, delegated runtime, configured gateway or storage custodian, and intended later recipients.
The verifier evaluates the exact candidate from each relevant perspective under the declared
disclosure policy:

- **singling out (isolation):** can a person, account, household, organization, repository, or record still be
  singled out inside the supplied material?
- **linkage:** can remaining values, structure, timing, paths, quotations, commits, or outside
  data reconnect it to its source?
- **sensitive inference:** can the candidate reveal a protected fact even without recovering a
  name?
- **no credentials:** are secrets, bearer material, private keys, session state, and authority-
  bearing references absent rather than merely renamed?
- **sufficient utility:** do the exact identifiers, relationships, citations, imports, diagnostics,
  and invariants required by the task still survive?

Record which disclosure claim the evidence supports. [Context](../../../adr/21-context.md#privatization-and-the-privacy-cut)
permits an authorized sanitized disclosure that remains private; an anonymity claim must separately
meet its stronger declared policy. Task-essential internal references do not themselves establish
either permission or anonymity: their structure may still identify the source to this recipient.
The verifier must assess the permitted relations and residual risk, including related disclosures.
A synthetic reproducer likewise retains its source influence. Prohibited categories, credentials,
failed mandatory conditions, and unresolved required evidence cannot be waived for utility.

[NIST SP 800-188](https://csrc.nist.gov/pubs/sp/800/188/final) similarly requires a declared data-
sharing model, measurable de-identification performance, and re-identification study rather than
assuming masking is enough. The EDPB's July 2026
[anonymisation consultation draft](https://www.edpb.europa.eu/public-consultations/guidelines-022026-on-anonymisation_en)
uses isolation, linkage, and inference as its practical test and makes the relevant entity's
perspective material. These sources guide the threat model; this page is engineering law, not a
claim of legal compliance.

| Material | Default treatment before remote eligibility |
| --- | --- |
| credentials, tokens, cookies, private keys | remove; never pseudonymize; rotate and quarantine if prior exposure is possible |
| direct identifiers | redact, or pseudonymize only when stable relation is task-essential |
| quasi-identifiers such as exact time, place, role, rare event | generalize, suppress, or keep local after linkage assessment |
| filenames, URLs, repository names, commits, stack traces, unique strings | treat as potentially identifying and proprietary; a secret-free checkout is not anonymous |
| relationships and ordering | retain only the minimum dependency structure required by the task |
| task-critical semantics | validate independently; if transformation breaks them, choose a local road or refuse |

## Seal the exact exit

Every remote path has two checks:

1. Before road admission or reservation, policy verifies that the aggregate label, purpose,
   destination, and required transformation path are eligible.
2. Before the first outbound payload byte, transmission verifies the canonical payload digest,
   tagged Portal/A2A/delegated-runtime target, Principal and Sigil identities, policy revision,
   expiry, and exact `DisclosureBasis`: either `RawEligible`, or `CutEvidence` with the terminal
   transformation-receipt-chain and `CutVerification@1` digests.

Every physical transmission gets a fresh EgressDecision. Exact same-envelope transport redelivery
within one admitted road-owned attempt retains its sealed bytes, target, idempotency identity, road
decision, and Cut/token namespace only when the adapter profile permits it and a bounded disclosure
use remains. A semantic retry, fallback, resumed stream with changed body, delegated child call, or
change of content, model, target, actor, policy, or custody route creates a fresh road decision. If
that new attempt requires transformation, it also forms a fresh recipient-specific Cut and, when
reversible, a fresh unpredictable namespace and lease. Consent can authorize only an eligible exact
disclosure; it cannot make a credential safe or repair missing lineage.

The provider, peer, or delegate's response remains attributed, tainted by the disclosed source
influence, and untrusted. Rehydrating pseudonyms is a separate local presentation act after
quarantine and schema validation. It accepts only exact tokens actually disclosed by that Cut at
schema-declared category/path positions; invented, altered, replayed, cross-field, or arbitrary-
prose placeholders refuse. The Context rehydration port emits `RehydrationReceipt@1` over the
quarantined-return and final digests, typed substitutions, lease/Cut, and restored influence label;
the final candidate is validated again. Rehydrated material cannot flow directly to an executable
field, effect, public/Discord delivery, or another remote call—each later audience or effect needs
its own authorization. Tool effects, Archive admission, publication, and training re-check their
own authority.

```text
CAPTURED → CLASSIFIED → MINIMALLY_PROJECTED
→ TRANSFORMED → SEMANTICALLY_ASSESSED → VERIFIED → CUT_SEALED
  ├─ EGRESS_ALLOWED → SUBMITTING
  │                    ├─ IN_FLIGHT → RETURN_QUARANTINED
  │                    └─ INDETERMINATE → reconcile | terminal non-completion
  │  RETURN_QUARANTINED → VALIDATED → REHYDRATED? → ADOPTED | terminal non-completion
  ├─ REVIEW_REQUIRED → new plan | terminal non-completion
  └─ REFUSED → local fallback | terminal non-completion

reversible map: ACTIVE → CLAIMED → CONSUMED | EXPIRED | REVOKED → KEY_DESTROYED
```

The sequence coordinates records owned by different components: service attempts, Intercom
tasks, AgentJobs, Context receipts, and Security decisions each retain their own authoritative
states. It describes Pattern law, not one mutable record. Cut candidate/map cleanup is a
separate obligation. Refusal, failed review, cancellation, failure, expiry, revocation, adoption,
and an indeterminate attempt reaching its retention deadline all enter key destruction. That
cleanup removes only ephemeral Cut/vault custody; it never purges the Composition's separately
admitted authoritative result.

## Let Loom show the boundary

A future Pattern contribution declares boundary metadata separately from Graph mechanics:

- execution plane and eligible local or Portal providers;
- egress, local-only, write, delegation, and quarantine behavior;
- label propagation or admitted declassification;
- required receipt, Gate, consent, and failure edge.

Loom may derive badges such as `PORTAL-ELIGIBLE`, `EGRESS`, `SANITIZES`, `DELEGATE`, `WRITES`,
`QUARANTINED OUTPUT`, and `HITL`. The manifest shows what may happen; occurrence evidence records
the provider, decision, payload digest, receipt, and result that actually happened. A hand-authored
`dangerous = true` flag is not enough.

Spellweaver rejects a contributed Scroll/Pattern whose remote Spell placement has no exact road
policy, whose declassification edge has no transformer and verifier evidence, or whose A2A,
delegated, retry, or fallback branch can bypass the parent boundary.

## Refusal is part of the score

| Failure | Pattern result |
| --- | --- |
| Missing or unknown lineage | Treat as restricted; remain local |
| Detector, Privacy Agent, or verifier uncertainty | Deny or route to declared review |
| Isolation, linkage, inference, credential, or utility test fails | Narrow the projection, remain local, or refuse |
| Receipt does not match payload | Deny before transmission |
| Policy or consent expired | Re-evaluate; never reuse the old decision |
| Provider fails or changes | No silent fallback; create a new attempt |
| Pseudonym lease is lost or expires | Do not reconstruct it; follow the declared no-rehydration/refusal path |
| Return proposes an effect | Keep quarantined until the effect owner reauthorizes it |

Restricted local receipts may retain canonical digests; logs, Loom, exports, and broadly visible
evidence use only opaque ids or Security's domain-separated keyed `EvidenceDigest@1`. Neither form
is anonymization. Both omit raw sensitive spans and the pseudonym map. Memory, embeddings, training
data, backups, and shared artifacts retain lineage and deletion obligations after the Run ends.

[Portal](../../animator/portal.md) owns provider declaration and operation.
[Execution roads](execution-roads.md) owns local/Portal/A2A/coding selection;
[Pattern lifecycle](pattern-lifecycle.md) owns revision pinning;
[Stasis and return](stasis-and-return.md) owns durable waiting; and
[Delegated agents](delegated-agents.md) owns the opaque child boundary. The [State of
Work](../../../state-of-the-work.md#context-privatization-and-portal-egress) records what exists.
