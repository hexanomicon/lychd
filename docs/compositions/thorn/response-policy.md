---
title: Thorn Response Policy
icon: material/tune
---

# Choose your response

One operator wants protection and an uninterrupted afternoon. Another wants to follow useful
leads until the case is understood. Thorn's proposed response policy lets both choose their
effort, automatic actions, and participation independently.

These are editable presets within the [candidate Composition](index.md), not delivered settings,
additional Compositions, or global Agent Postures.

## From Iron Shield to Hornet

| Preset | Intent and behavior |
| --- | --- |
| **Iron Shield** | “Protect me; I am concentrating on my work.” Use admitted local protection, retain bounded permitted evidence, and surface actionable exceptions. No automatic lead expansion or peer inquiries. |
| **Guided Inquiry** | “Find out whether this deserves my attention.” Add bounded local triage/correlation and propose leads for the operator to select. |
| **Hornet** | “If you attack me, I follow the trail.” Proactively pursue admitted leads, ask eligible peers, reconstruct supported campaign activity, and prepare findings within finite limits. |

Iron Shield is the proposed initial selection. Every preset preserves configured protection,
evidence handling, and outstanding recovery/correction duties. Hornet increases persistence;
anger, attack volume, or a peer's urgency cannot change its permissions or attribution standards.
Within an admitted inquiry, agents need no new approval for each reasoning step. External reports
still require acceptance of the exact packet, destination, and purpose under the
[report contract](index.md#reports-and-corrections).

## Set each control on its own

| Control | Operator choice |
| --- | --- |
| Response automation | Notify, propose a change for acceptance, or execute an exact preauthorized response. Existing enforcement keeps its own policy. |
| Pursuit | Protection only, proposed leads, or proactive admitted investigation; eligible incident categories and repeat-incident triggers. |
| Effort | Time, lead depth/count, concurrent cases, model/tool calls, compute/spend, peer fan-out, evidence storage and retention. |
| Task priority | Spare capacity, a time window, or bounded foreground attention while reserving essential defense resources. |
| Human attention | Critical-only notices, summaries, or case updates; consequential failures and unresolved decisions remain visible under the selected policy. |
| Participation | Separately permit peer replies, specific observation sharing, investigation/review effort, or a collector. |
| Explanation | Concise results or technical evidence, hypotheses, coverage, and controls. Both show consequential permissions, costs, disclosures, and unknown effects. |

An expert may choose Iron Shield; a newcomer may choose a thorough inquiry. Expertise supplies no
grants or trust. Private Hornet work need not share anything. An Iron Shield user may contribute
one permitted observation without investigating. A preset never enrolls peers, deploys a collector,
enables export, or inherits a tool's sharing defaults.

## Authorize the response separately

Iron Shield can execute prompt preauthorized protection. Hornet can investigate extensively while
requiring acceptance for every service change. Automation preference alone grants neither one
permission to act.

For preauthorization, state which action may run against which eligible targets and under what
evidence conditions/freshness. Bind current authority, impact limit, duration, rate/concurrency
ceiling, verification, and recovery rule. The effect boundary checks this envelope independently
of the proposing worker; “Defend me” and a model's severity label cannot supply it.

When several actions could affect one resource, retain an accountable owner for resolving
conflicts. A changed target still falls under the aggregate limits.

Preserve accepted, effective, partially effective, and unknown outcomes. Reconcile ambiguity before
retry; account for service impact and current exposure before rollback. An irreversible action
needs a separately admitted recovery path. Human, model, or peer unavailability cannot silently
promote a proposal into an automatic action or disable existing controls. Apply only an explicitly
admitted fallback when a required decision is unavailable, and expose the unresolved condition.

## Bound the cost of defense

Per-case ceilings sit inside aggregate period budgets and concurrency limits. Intake, parsing,
rejected requests, retries, parallel workers, peer requests, reviewer time, and correction work
all consume the applicable allowances. New cases cannot replenish them. Zero optional inquiry
budget means pursuit is disabled.

Reserve bounded capacity for essential protection and outstanding reconciliation/corrections
before optional investigation. If that reserve is insufficient, expose the backlog and stop new
optional obligations. Account for coalesced, deferred, and dropped work without retaining unlimited
hostile input. Exhaustion leaves a gap, not an examined lead or a completed correction. Collector
connection and containment limits remain separate; quiet notifications cannot prove healthy coverage.

Choose leads by expected contribution to a supported decision, with uncertainty and cost visible.
Use bounded sampling and aging so cheap or familiar cases cannot consume all capacity. Claimed
urgency, novelty, and repetition alone cannot set priority. Full review capacity means a bounded
pending lead or an explicit stop, not more unreviewed reports.

Priority resolves through [Workflow service classes](../../adr/28-workflow.md#compositions-products-suites-and-schedules).
Thorn introduces no queue or scheduler; Hornet can use spare capacity. Those facilities retain
their existing delivery boundary.

## Change the policy without losing the case

An operator may override a persistent default for one case with an owner, purpose, expiry, and
budget. Show the effective choices and their origins before admission. Missing limits or
conflicting policy produces a concrete refusal. New methods, destinations, or disclosures need
their own admission even when more effort is available.

At admission, each occurrence pins its effective policy revision and budget allocation. Changing
the default governs later admissions while preserving historical Runs and the existing limits of
open cases.

To apply a downgrade, expiry, or revocation to current work, stop newly disallowed optional work,
recheck queued effects, and account for work already underway. Raising an allowance instead needs
a newly admitted allocation. Retrying never resets what the work has consumed.

Switching to Iron Shield leaves separately admitted protection and collectors in place; stopping
a collector has its own control. Corrections and uncertain deliveries survive. Returning to a
default cannot resume cancelled work or authorize an automatic resend.

[Configuration](../../adr/12-configuration.md#future-selectors) owns typed loading, validation,
precedence, and generation. Thorn would own this policy's application meaning; the proposal adds
no executable switch or configuration schema. [Policy trials](trials.md#compare-response-policies)
must first establish the intended behavior.

[Thorn](index.md)
