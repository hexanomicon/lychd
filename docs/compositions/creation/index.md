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
profile requests no source edit, executable workspace, external acquisition, promotion or successor.
[State of Work](../../state-of-the-work.md#smith-forge-promotion) records implementation separately.

## Admit one question

Admission retains canonical request bytes, an explicit public-material declaration, literal UTF-8
source bytes and their relative names, lengths and digests. It pins the declared repository/base or
patch identity, question, non-goals, criterion IDs, omissions, exact role bindings and acceptance.
A filename or hash without its bytes is insufficient. Declared base identity is not an independently
observed live Git tree. Changed inputs require another request; an old report keeps its old target.

Revision 2 permits at most 8 sources and 4096 total source bytes, 512 question bytes and 4 criteria of
192 bytes each. Relative source names are bounded and cannot escape a root; duplicate keys/names,
malformed UTF-8 and inconsistent byte spans refuse. Canonical candidate and verdict each have a
1536-byte ceiling. Citations identify retained source bytes and valid spans; valid citations do
not make their interpretation correct.

Each role packet supplies deterministic per-source line counts using the same retained UTF-8 byte
line-splitting convention as citation validation. These inclusive, one-based limits guide the
model; original source/request bytes and strict span validation remain unchanged. A model result
never repairs, clamps or extends its own citation. Role instructions also state the existing
1536-byte total canonical-result ceiling and prefer concise output with a writing margin. This is
guidance for the model, not a new acceptance limit or an output-repair mechanism. Changed
instructions receive new instruction and implementation identities under the same captured-profile
fences.

The fixed `public-source-qwen@2` profile selects one exact configured shared, non-dedicated local
Soulstone/vLLM/Qwen3.8-27B Chat capability. Its captured generation is 4096 context, 512 output,
temperature 0 and `qwen3.8-non-thinking`. Missing or changed binding, unsupported profile, unavailable
WARM grant or fallback refuses. No model lifecycle request is admitted. Agent and SDK retries are 0;
only structured final output is available, with no executable toolsets.

Before construction, reserve one logical application slot, one constructor attempt, one verifier
attempt and 30 seconds per role, plus30 seconds for recovery, under a 180-second original lifetime.
One unresolved investigation occupies the slot. This reserves application allowances, not exclusive
GPU capacity or a hard aggregate quota. Recheck authority, expiry and grant at each stage.

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

Generic startup reconciliation remains unchanged: an orphan Run can become FAILED. A fresh current
local operator may explicitly admit at most one **new continuation Run** only while the original reservation
is live, the prior Run/delivery/lease is settled, the exact complete candidate is retained and the
verifier has never been claimed. Match source/base/question/criteria/profile and candidate identities;
retain the new authority generation and bind its Run before queue publication. It inherits the
original deadline and unused verifier/recovery allowance. The continuation also has a recovery
cutoff 30 seconds after its own admission, bounded by the original deadline; the verifier uses
only the remaining time and its single attempt. There is no renewed attempt or constructor replay. A cancelled, expired or ambiguous case cannot continue. No scanner submits replacement Runs.

[Workflow](../../adr/28-workflow.md) · [SDLC](../../adr/16-sdlc.md) · [Portfolio](../index.md)
