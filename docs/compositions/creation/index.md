---
title: Creation investigation
icon: material/creation
---

# Creation investigation

An engineer asks whether a test proves the change it claims to prove. Keep the exact source,
question and acceptance beside the answer, then ask a separate reviewer to challenge it. The
investigation should remain intelligible when its conversation and worker have ended.

## Contract

**`creation.investigation` revision `2`** publishes **`creation.investigate@2`** for bounded
public-source software investigation. It owns the immutable request, source bundle, role
reservations, inference attempts, candidate and attributed verdict. Run owns execution and delivery;
Dispatcher owns grants. The wider [Creation method](../../sepulcher/extensions/weaver/creation.md)
still guides design, editing and delivery under [SDLC law](../../adr/16-sdlc.md).

The return is a retained report and an accepted, rejected, partial or incomplete review, or exact
noncompletion. A complete response and a DONE Run do not establish semantic correctness. This
profile requests no source edit, executable workspace, external acquisition, promotion or automatic successor.
[State of Work](../../state-of-the-work.md#smith-forge-promotion) records implementation separately.

## Admit one question

Begin by preserving exactly what the investigation will examine. Admission retains canonical
request bytes, an explicit public-material declaration, literal UTF-8 source bytes and their
relative names, lengths and digests. It pins the declared repository/base or patch identity,
question, non-goals, criterion IDs, omissions, exact role bindings and acceptance.

The retained bytes let another reviewer reconstruct the question. A filename or hash alone is
insufficient, and the declared base identity is not an independently observed live Git tree.
Changed inputs require another request; an old report keeps its original target.

Revision 2 permits at most 8 sources and 4096 total source bytes, 512 question bytes and 4 criteria of
192 bytes each. Relative source names are bounded and cannot escape a root; duplicate keys/names,
malformed UTF-8 and inconsistent byte spans refuse. Canonical candidate and verdict each have a
1536-byte ceiling. Citations identify retained source bytes and valid spans; valid citations do
not make their interpretation correct.

Each role packet binds the canonical full request digest and its metadata, then projects ordered
sources as their original names, literal-byte digests and explicitly numbered lines. Line text
preserves its original UTF-8 bytes and terminators using the same byte-splitting convention as
citation validation. Rejoining those lines reconstructs each source and the canonical original
request exactly. Source text is not duplicated within the packet. Original request/source custody
stays unchanged; the model sees an attributed projection, not replacement source truth.

Deterministic line counts retain the inclusive, one-based citation limits. Both roles are guided
to cite the operative statement that supports a claim rather than an adjacent check. Explicit
numbers aid selection; neither valid addresses nor this presentation prove semantic entailment.
The model never repairs, clamps or extends its own citation. Projection overhead remains inside
the unchanged packet and verifier-candidate reservation limits: a dense short-line source may
refuse admission even within the source-byte maximum. No truncation makes it fit.

Role instructions state the existing per-field character maxima and 1536-byte total canonical
result ceiling, prefer concise findings and a short summary where present, and retain a writing
margin. These are model guidance; strict schema, source-span and byte validation remain the
acceptance boundary. Output schemas, hard limits, zero retries and original evidence stay
unchanged. Changed projection and instructions receive new instruction and implementation
identities under the same captured-profile fences; historical packets are not converted.

The fixed `public-source-qwen@2` profile selects one exact configured shared, non-dedicated local
Soulstone/vLLM/Qwen3.8-27B Chat capability. Its captured generation is 4096 context, 512 output,
temperature 0 and `qwen3.8-non-thinking`. Missing or changed binding, unsupported profile, unavailable
WARM grant or fallback refuses. No model lifecycle request is admitted. Agent and SDK retries are 0;
only structured final output is available, with no executable toolsets.

Reserve the work before construction: one logical application slot, one constructor attempt,
one verifier attempt and 30 seconds per role, plus 30 seconds for recovery, all within the
180-second original lifetime. An unresolved investigation continues to occupy that slot. These
are application allowances; they reserve neither exclusive GPU capacity nor a hard aggregate
quota. At each stage, recheck authority, expiry and grant.

The complete serialized role packet includes instructions, source, question, criteria and output
schema. Its 12288-byte envelope reserves the verifier's maximum candidate before construction.
Never truncate source, criteria or candidate to make it fit. Use supported pre-counts and the
existing per-request context/output guard. This local Chat profile has no pre-transmission token
counter: record that absence and check observed usage before adoption. Its observed input ceiling
is 3584 tokens, reserving 512 of the 4096 context tokens for output. A byte envelope does not prove
a hard 4096-token transmission bound or future provider availability. Invalid or over-budget
complete output settles as retained noncompletion, without a repair call.

## Construct, challenge and retain

The serial score is `PrepareInvestigation` → `ConstructInvestigation` → `VerifyInvestigation` →
`ProjectInvestigation`. Preparation may go directly to verification only for the exact continuation
below; known noncompletion goes to projection. Graph state contains owned references, not live
clients or a second copy of application truth.

Persist the stage's exact input binding and inference claim before its call. Retain the complete
provider response (at most 65536 canonical UTF-8 bytes) before interpreting or adopting it. Keep response identity, actual
usage, participant/capability identity and failure class. Immutable candidate bytes cannot be
replaced by a later answer.

Constructor and verifier have distinct AgentSpecs and fresh messages. The verifier receives the
original source, question, criteria and exact candidate; it receives no constructor conversation,
private deliberation or unrelated history. Record shared model/infrastructure and exposures.
Context separation is attributable review, not proof of a different sovereign or infallible judge.
A verdict links findings, contradictions and unknowns to criteria. No recursive judging or automatic
repair follows. [Tree faculties](../../sepulcher/extensions/weaver/creation.md#tree-relations-in-practice)
recur in framing, making, challenge and return; they do not require ten Agents or one universal score.

## Current local authority

The local profile has one credential-backed `local-operator` role. An actual current
`LocalOperatorAccess` marker plus the required Sigil scopes authorizes submit, read and cancel of
this application's local cases. Creation implements that explicit object/action policy; a scope
guard alone supplies none. This is not person-level tenancy or remote Ward identity.

Retained subject/generation fields are attribution, never credentials. Check the actual current
marker at each HTTP action, and the admission's current binding, exact case/action policy and Run
fence before inference claim and adoption. Revocation or startup change ends old authority. A new
credential holder reads historical cases under fresh current-role policy. Original initiator and
all later admission records remain immutable.

Explicit opt-in assembly selects revision 2 and its exact capability:

```toml
[weaver.creation]
revision = "2"
capability_key = "<exact configured public-source-qwen capability key>"
```

PostgreSQL and current local operator credentials are required. The capability must satisfy the
profile above; this selection cannot make a cold model ready. The protected local API exposes:

| Action | Route | Body |
| --- | --- | --- |
| Submit or replay | `POST /api/v1/creation/investigations` | Immutable request, including its request UUID, public declaration and literal sources. |
| Read retained state | `GET /api/v1/creation/investigations/{case_id}` | None. |
| Cancel adoption | `POST /api/v1/creation/investigations/{case_id}/cancel` | None. |
| Admit eligible continuation | `POST /api/v1/creation/investigations/{case_id}/continue` | New admission UUID and exact request, candidate and profile digests from retained state. |

Responses project the case, original request, admissions, attempts, candidate, verdict and exact
noncompletion. Generated OpenAPI owns the transport schema. Authentication, Origin and CSRF remain
server gates. The browser and callers do not create durable truth by display.

## Ordinary Altar intake and report

Bridge may offer this existing protected contract through an investigation focus at `/bridge`,
with only a case UUID in navigation. It submits the immutable public-source request and links
the returned exact admission Run to Orb; it does not convert an ordinary chat message or Atlas
next step into an investigation. The fixed profile, source/packet bounds and all server gates
remain unchanged. The [Bridge guide](../../divination/altar/bridge.md#investigate-public-source)
owns the ordinary interaction.

Browser sources and the submitted body remain transient. If submission is ambiguous, keep its
UUID and exact body without automatic retry. An explicit Check cannot turn an in-flight 404 into
proof of non-admission. Identical replay requires the original body, which reload does not recover.

Reading the protected detail can perform existing expiration and returns retained operational
records. The report renders validated request/candidate/verdict text. After awaited storage, it
still requires current read authority and fences a changed selection.

Use **Load feedback** for the separate protected historical projection; this read does not expire
execution. Current assessment/decision IDs select the displayed judgments. A later assessment
leaves an earlier owner hold historical. **Reload feedback** is explicit, and a refused read
clears protected feedback.

Distinguish Run completion from the native verdict, external assessment, and owner decision.
These are four separate facts. Report/reason text and server annotation coverage cannot establish a semantic
pass. Viewing authorizes no continuation, feedback mutation, successor, source edit or promotion;
explicit Refresh is needed to see later case changes.

## Selected-Run summary

The existing Orb selected-Run snapshot and retained-evidence feed may include an authorized
Creation summary. Its identity comes only from the retained exact admission-to-Run relationship;
workflow names, adjacent Sessions and browser state cannot establish it. Each read checks current
local-role authority, including every active stream poll. Missing metadata establishes neither the
existence of a case nor whether Creation is configured.

This dedicated metadata read does not expire or settle a case, release its execution slot, adopt a
response or load source, provider response, candidate or report bodies. It can report an elapsed
deadline while the slot remains encumbered. It separates constructor/verifier retention and
adoption, native status/verdict, latest external assessment and current owner decision. A historical
admission remains linked to its original Run while the summary explicitly describes the case's
current outcome, which may include later admissions. A newer assessment makes an older decision
non-current according to the feedback contract below.

Orb labels these details separately from Run execution status and its recorded-evidence playback.
The feed still closes when retained terminal evidence drains; later assessment and owner updates
need Refresh. This projection grants no Creation action or source-edit authority.

## External assessment and owner hold

The first feedback contract appends an external report and explicit local owner `hold` or `reject`
to a completed revision 2 case. It preserves the original CaseView, candidate, native verdict,
execution status, deadline and reservation. Implementation is recorded separately in
[State of Work](../../state-of-the-work.md#smith-forge-promotion).

An assessment UUID binds the retained request, profile, candidate and canonical native-verdict
digests. Derive its source identity from the canonical ordered list of `{name, digest}` entries,
where each digest covers the literal UTF-8 source text; derive criterion identity from the
canonical original ordered `{id, predicate}` list. Retain exact report UTF-8 bytes and digest
separately from the canonical intake body. Claimed reviewer label
and revision are bounded attribution, not authenticated external identity. Record actual current
submitting Sigil and authentication generation separately, with disclosed exposure and limitations.
External disposition is `accepted`, `rejected`, `partial`, `incomplete` or `not_assessed`.
Optional criterion/citation annotations belong explicitly to the submitter; absent criteria remain
not assessed rather than acquiring invented reviewer judgments. Citations resolve only to the
original sources and valid byte spans; they do not prove semantic entailment.

The report is at most 8192 UTF-8 bytes; reviewer label and revision are each at most 128 bytes.
Exposure and limitation lists each hold at most four 192-byte items. At most four annotations
identify distinct original criteria and use the existing bounded finding/citation shape. Canonical
assessment and decision bodies each fit 16384 bytes. Duplicate JSON keys, mismatched target,
unknown criterion/source, invalid spans and missing candidate/verdict refuse.

Feedback appends require an unencumbered completed case, all its inference claims resolved,
each bound Run terminal and its current delivery settled, and no corresponding active local Run
lease. Check these conditions and current local authority while holding the case lock, without
expiring or altering execution. Retained revision 2 closures need no current model/profile readiness
merely to receive feedback. Revision 1 writes remain refused.

To record the owner's judgment, bind a new decision UUID to the exact assessment id/digest and
target. Choose `hold` or `reject`, with a non-empty reason of at most 1024 UTF-8 bytes and an
optional distinguishing observation of at most 512 bytes. New decisions target the latest
assessment. All appends share one per-case sequence, and the latest decision for that assessment
is current. Another assessment makes earlier decisions historical and projects `review_required`
until the owner addresses it separately.

Replay preserves the original record. Before latest-target or capacity checks, an identical
canonical body returns its original row; changed or cross-case identity refuses. Every replay
still requires fresh current authority, and original attribution is never overwritten. The case
admits at most 16 assessments and 16 decisions, while identical replay continues to work at
capacity. There is no update or delete. Additive persistence preserves original custody, and
downgrade refuses while feedback exists.

The protected local routes use the same actual operator marker, object/action policy, Origin and
CSRF gates. Append requires `runs:submit`; read requires `altar:read`.

| Action | Route |
| --- | --- |
| Append or replay assessment | `POST /api/v1/creation/investigations/{case_id}/assessments` |
| Append or replay owner decision | `POST /api/v1/creation/investigations/{case_id}/decisions` |
| Read attributed feedback | `GET /api/v1/creation/investigations/{case_id}/feedback` |

The separate feedback view projects `unassessed`, `review_required`, `hold` or `rejected`, with
native status and external judgments alongside it. Native `accepted`, external `partial` and owner
`hold` can therefore remain visible together. A hold records this application's disposition; it
claims no global block on unrelated submissions or effects. Intake has no inference, queue,
continuation, profile renewal or execution-state mutation path. A next evaluation, source edit,
Atlas projection, training and promotion require their own contracts and admission. This first
attachment establishes neither a complete feedback handoff nor measured recursive improvement.

## Explicit successor admission

A separate current local operator may authorize **one new investigation** from exact settled
feedback. This is a new evaluation with its own immutable sources, question, criteria, acceptance,
current profile and reservation. It is not continuation of an expired case or retry of an inference
attempt. The parent keeps its deadline, candidate, verdict, feedback and disposition unchanged.
[State of Work](../../state-of-the-work.md#smith-forge-promotion) records implementation evidence;
this contract alone does not deliver a native handoff.

`POST /api/v1/creation/investigations/{case_id}/successor` requires current local authority,
`runs:submit`, Origin and CSRF. Its typed body retains a fresh complete `InvestigationRequest`,
`authorize_one_child: true`, the exact parent `FeedbackTarget`, latest assessment and current
owner-decision UUIDs and canonical-body digests, and a non-empty `changed_hypothesis` of at most
512 UTF-8 bytes. The operator supplies the new acceptance; report text and a hold or rejection
cannot authorize it. Raw and canonical intake each fit 16384 bytes; the nested request and both
role packets also satisfy all ordinary investigation bounds. No truncation or inferred fields
make an intake admissible.

The parent must satisfy the existing settled-feedback conditions, including resolved inference
claims, terminal bound Runs, settled delivery and absent active local leases. Its retained revision
2 contract may differ from the current execution profile, and its original deadline may have
passed: neither is renewed. Match the exact retained target and latest assessment/decision while
holding its case lock. An existing child cannot be retroactively attached. A case admitted as a
child cannot itself become a parent through this operation. Ordinary unrelated submissions remain
separately governed; this is not a global execution prohibition.

Before publishing the new Run, atomically retain the fresh child case, admission, exact lineage
body/digest and authenticated attribution. This commit permanently consumes the parent's one-child
allowance, even if publication later fails. There is no refund, second child, replacement UUID,
automatic retry or descendant chain.

The child needs its own authorized reservation: the existing one application slot, 180-second
lifetime and one constructor/verifier attempt, under the current exact profile and WARM
capability check. It neither renews nor reuses the parent's budget, and reserves no exclusive GPU
capacity or hard aggregate quota. Recheck actual authority after awaited preparation and lock
acquisition, at commit, and before releasing held Run publication.

Identical canonical-body replay under fresh current submit authority returns the original
lineage and child identities before freshness, capacity or model-readiness checks. Preserve the
original admission attribution. Repair may only reconcile that exact held delivery through the
existing Run idempotency path, under its original still-current execution binding; replay never
creates another admission, session, role attempt or reservation. Changed body, parent or child
identity refuses. A newer assessment before admission commit refuses the stale request; a newer
assessment after commit makes that lineage historical without rewriting or silently revoking the
already-admitted child. Revocation and normal Run/adoption fences still apply.

`GET /api/v1/creation/investigations/{case_id}/lineage` requires current local authority and
`altar:read`. It projects the retained incoming and outgoing lineage separately from the unchanged
CaseView and feedback views. Additive durable custody survives restart and refuses downgrade while
lineage exists. A successful child report is an observation, not evidence of semantic improvement,
independent task choice, source-editing authority, foreign-runtime containment or promotion.

## Revision continuity

Revision 2 is the only current selector and Pattern. Its exact `public-source-qwen@2` profile
raises the per-role output allowance from 256 to 512 tokens; the two-role aggregate ceiling is
1024 generated tokens. The context remains 4096, with 3584 reserved for observed input. Source,
packet, response and canonical output byte bounds, deadlines and one-shot attempts are unchanged.

The initial revision 1 live prototype retained a constructor response ending at its 256-token
limit and adopted no candidate or verdict. Keep that failed occurrence and its original bindings.
Current-role GET may read historical revision 1 cases. Creation write actions through selector 2
refuse their submit replay, cancellation and continuation; it never rewrites or executes those
records. Cancellation of a current revision 2 case checks its retained contract identity and
current local authority, not model availability or a freshly resolved capability. It grants no
execution or renewed reservation. Full profile matching remains required for admission,
continuation and stage adoption.
A later reviewed implementation closure (`py.3`) adds only this citation-coordinate guidance and
changes its instruction identities. Composition, Pattern and profile revisions stay 2: requests,
results, budgets, authority and recovery law are unchanged. Exact captured manifest/profile equality
refuses historical-closure execution or continuation; historical read and current-revision
cancellation retain their existing policy. The earlier implementation's invalid-span response remains
a failed occurrence. A new case may test the new closure; it never repairs or renews that occurrence.

A new profile requires a separately admitted case and reservation, not renewal of the old one.
Same-profile identical replay retains its existing identities without another inference.

## Interruption and continuation

Identical replay returns retained identities/results; conflicting replay refuses. Cancellation
fences application adoption before requesting Run cancellation; the actual Run state also wins
races. Late complete bytes may remain attributed evidence without accepted disposition.

A claimed call without a complete durable response remains incomplete/unknown. Timeout, cancellation,
expiry or startup cannot make it unclaimed or release its encumbered slot. Revision 2 has no automatic
unknown-outcome release. Known terminal completion or proved not-issued failure may release capacity.

Generic startup reconciliation remains unchanged: an orphan Run can become FAILED. Continuation
requires a separate decision by a fresh current local operator. At most one **new continuation
Run** may be admitted, and only while the original reservation is live, the prior Run/delivery/lease
is settled, the exact complete candidate is retained, and the verifier has never been claimed.

Match source/base/question/criteria/profile and candidate identities, retain the new authority
generation, and bind the Run before queue publication. It inherits the original deadline and
unused verifier/recovery allowance. It also has a recovery cutoff 30 seconds after its own
admission, bounded by the original deadline. The verifier therefore gets only the remaining time
and its single attempt. There is no renewed attempt or constructor replay. Cancelled, expired or
ambiguous cases cannot continue, and no scanner submits replacement Runs.

[Workflow](../../adr/28-workflow.md) · [SDLC](../../adr/16-sdlc.md) · [Portfolio](../index.md)
