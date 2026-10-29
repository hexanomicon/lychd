---
title: Thorn
icon: material/shield-search
---

# :material-shield-search: Thorn

> _LychD has spikes._

Thorn is a proposed **whitehat security workbench**. It turns a scoped security question or attack
into supported findings, a bounded protective response, and an accountable report or correction.
It serves incidents affecting the operator and separately authorized engagements; the target
environment need not run LychD. Its lasting unit of work is the security case.

The intended deterrence is that targeting participating defenders can expose a campaign and
prompt intervention. Useful protection and findings do not require identifying a human controller.
Whether participation discourages attacks remains an unmeasured proposition.

This **candidate study**, opened **2026-09-22**, proposes **`thorn.defense`, revision 1**.
Portfolio acceptance and executable contracts remain open. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
owns delivery; [Workflow](../../adr/28-workflow.md#composition-identity-revision-and-retirement)
owns identity and revision law. The contract below is a proposal throughout.

## Purpose and boundary

Thorn keeps an investigation answerable: what may be examined, what the evidence supports, which
response is justified, what actually happened, and which obligations remain.

| Thorn owns | Adjacent responsibility |
| --- | --- |
| Security case, authorized targets/methods, leads, findings, and competing explanations | Logs, sensors, detectors, and analysis tools supply replaceable mechanisms and attributed observations. |
| Response decisions, scope, verification, and recovery follow-up | The target system and its action adapter execute under current authority and retain their effect records. |
| Security verification of a suspected weakness or remediation | Maintenance owners control code changes, migrations, activation, and operational recovery. |
| Recipient-specific reports, shared findings, challenges, and corrections | Each peer controls its own work and disclosure; external recipients own their intervention. |

[Autopoiesis](../../lexicon/iron-tongue.md#autopoiesis) names intended verified self-repair and
extension under operator authority. Routine database or workflow optimization, code maintenance,
backups, and whole-system restoration belong to that wider concern under existing owners. They
are outside Thorn's casework. A repair receipt can inform a security retest; a healthy service
does not by itself prove containment or close a security finding.

Tool availability supplies no permission. An assessment pins targets, methods, possible effects,
and stopping conditions. Receiving an attack supplies no right to enter suspected third-party
systems, coerce someone, expose private identities publicly, or retaliate.
[Security](../../adr/09-security.md) and [IAM](../../adr/38-iam.md) retain enforcement and authority.
Thorn introduces no general system administrator, scheduler, or self-authorizing agent.

Typed findings, requests, and settled receipts can cross these boundaries without transferring
ownership. A promise to coordinate separate Compositions' live Invocations needs the explicit
[Suite contract](../products-and-suites.md#compositions-relate-without-nesting).

## From encounter to result

A defender receives a suspicious message or an alert about unexpected account activity. Thorn
preserves permitted evidence, checks the signal's freshness and scope, and opens or links a case.
A human can instead begin with an authorized assessment question. Triage may also record a
non-incident, a gap, or a concrete refusal.

The case proceeds through five decisions:

1. What was observed, what is exposed, and what work is authorized?
2. Which immediate protective action is admitted, and how will its effect be verified?
3. Which optional lead could establish the next useful fact?
4. Do the findings justify a particular report or should the case abstain?
5. What needs correction, recovery, or further observation before the work can close?

Protection and investigation can proceed independently. Existing controls continue enforcing
their rules when Thorn, a model, or peers are unavailable. Immediate protection does not wait for
attribution or a completed inquiry. Detector interpretations remain distinct from observations
and case judgments. Duplicate or stale alerts confer no new authority; missing capture or a
failed sensor leaves a coverage gap rather than evidence of safety.

[Follow the campaign](investigation.md) develops the lead loop, peer sightings, supported activity
paths, and handling of hostile evidence. [Response policy](response-policy.md) independently
sets effort, automation, participation, attention, and cost. **Iron Shield** favors quiet
protection; **Guided Inquiry** proposes leads; **Hornet** pursues admitted leads persistently.
Their limits do not alter authority or the evidence needed for a claim.

## The case and its Patterns

The private case must explain both the investigation and its consequences. Retain its owner,
restricted subject/victim references, purpose, scope, effective policy revision and expiry,
budget allocations/consumption, leads, claims, contrary evidence, action attempts and receipts,
dispositions, and correction obligations.

For a reviewer to challenge a claim, its source references must preserve custody, method,
transformations and redaction lineage, original and UTC times with clock uncertainty, and
observed versus inferred status. Original bytes and local custody digests remain with their
owners. Each assessment records its reviewer, grounds for confidence, and review/expiry conditions.

| Proposed Pattern | Admitted input → accounted result |
| --- | --- |
| `thorn.open_case@1` | Scoped report, observation, or assessment question → triage and a new/linked private case, non-incident disposition, or refusal. |
| `thorn.investigate@1` | Admitted leads or assessment and source policy → supported claims, competing explanations, gaps, and disposition of each lead. |
| `thorn.protect@1` | Supported response and current authority → proposal or admitted action attempt, verified/unknown result, and recovery obligations. |
| `thorn.report@1` | Findings and recipient policy → exact reviewed packet and separately authorized handoff disposition. |
| `thorn.correct@1` | Changed or challenged evidence → successor claims, invalidated derivatives, and recipient-specific correction dispositions. |

These names are proposed, not registered Patterns. Their separation permits protection without
inquiry, inquiry without reporting, and correction after other work has ended. Tools remain
replaceable behind typed boundaries; the case and its judgment explain why Thorn is a Composition.

## Respond and verify

Before attempting a response, bind it to the target, evidence conditions and freshness, current
authority, impact, duration, limits, verification, and recovery plan. The effect boundary checks
that account independently of the worker proposing it. It must also prevent concurrent requests
from duplicating or conflicting over an effect. Assign an accountable owner who retains
verification and recovery even if the worker disappears.

Keep proposed, authorized, attempted, partially effective, maintained, and recovered states
distinct. An accepted command does not establish containment. Verification may reveal a failed
action, missing visibility, or an unknown effect. Reconcile uncertainty before retry so another
attempt cannot silently duplicate a change.

Account for false positives and service impact. Rollback or expiry requires the declared recovery
decision against current exposure; blindly restoring a still-compromised capability is not
recovery. An irreversible action needs an admitted recovery path. A maintenance outcome and the
security retest of that outcome remain distinct findings.

## Reports and corrections

A report separates facts from inference and retains contrary evidence, custody, gaps, affected
scope, and the requested response. Review whether the evidence supports that intervention and
its impact on unrelated users of shared infrastructure. Human acceptance records a decision;
it cannot make an allegation true. Narrow an unsupported request or abstain.

Independently verify the recipient and destination, accepted threat category, purpose, and
mandate/jurisdiction where applicable. A human accepts the exact packet, destination, and purpose;
changing them requires renewed acceptance. Preparation does not authorize sending or publication.
Outgoing evidence uses only recipient-permitted opaque references or scoped `EvidenceDigest@1`
under [Security's disclosure rules](../../adr/09-security.md#decision-identity-and-local-custody),
not raw canonical source digests. Peer exchange follows the same disclosure boundary through its
[own contract](investigation.md#ask-another-defender).

Once a report is admitted for handoff, persist its exact artifact, authority, attempt identity,
and receipts. Record whether it was **prepared**, **sent**, **acknowledged**, **refused**, **failed**,
or remains **unknown**. A successful transport proves neither guilt nor official action. If the
send may have happened but its acknowledgement was lost, reconcile that attempt before retrying.

Review equivalent allegations across visible collaborating cases, including differently worded
reports, while recording visibility limits. Cooperation must not become report flooding. A
correction is a separately admitted successor with its own recipient disposition, not another
copy of the allegation. Findings can remain useful when external reporting is unwarranted.

## Finish, stop, or return

Containment, operational recovery, investigation completion, and report delivery have separate
dispositions. **Actor unknown** and **insufficient evidence** are valid investigative findings.
Partial completion names remaining obligations and owners; refusal names the unavailable scope
or boundary; failure names the failed operation. Unknown effects keep overall settlement
unresolved even when analysis has finished.

Cancellation or revocation stops newly disallowed work and disclosure and initiates authorized
collection shutdown. It cannot undo delivered effects. Resume rechecks current permissions,
evidence freshness, sensor generation, and outstanding attempts. A stopped inquiry cannot erase
an unfinished action, delivery, or recovery obligation.

Corrections can outlive a closed case. Successor claims update dependent findings and affected
recipients; unresolved acknowledgements remain visible. Retention/deletion follows case and
custody policy while preserving only permitted lineage. Remote deletion or recall is not guaranteed.

## First proof

[Thorn Trials](trials.md) begins with a synthetic local attack and simulated response, then compares
the same case across three simulated defenders. A scoped assessment and repair retest separately
exercise security verification. The proposal must improve a supported decision or reduce total
work against competent simpler protection, within authority, privacy, recovery, and cost limits.
The trials page defines defeat conditions and advancement evidence; no trial result is claimed.

[Composition studies](../index.md#candidate-studies)
