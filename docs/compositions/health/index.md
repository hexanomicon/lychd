---
title: Health
icon: material/medical-bag
---

# :material-medical-bag: Health

A folder of photographed reports, remembered symptoms, prescriptions, and laboratory results is
not yet a clinical history. Health helps one consenting adult turn that material into an
attributable, corrigible profile, discuss one bounded health question, and carry a proposed
diagnostic or treatment plan to the right human decision. Unreadable evidence can remain unreadable;
uncertainty is a result, not a gap for a model to fill.

This Native Reference Composition is **Designed**. Its stable identity is `health.clinical`,
revision `1`. The [portfolio delivery record](../../state-of-the-work.md#composition-portfolio-delivery)
owns implementation status; these pages establish no clinical service, medical-device claim,
provider integration, database schema, or executable Pattern.

## Enter through the case

| Reader journey | Pinned Pattern | Primary records |
| --- | --- | --- |
| [Assimilate records into a reviewed profile](assimilation.md) | `health.assimilate_record@1` | `ClinicalSource@1`, `ExtractedClinicalClaim@1`, `HealthProfile@1` |
| [Consult the evidence and plan diagnostic work](consultation.md) | `health.review_case@1` | `HealthCase@1`, `DiagnosticProposal@1` |
| [Review treatment options and follow up](care.md) | `health.plan_care@1`, `health.follow_up@1` | `CareProposal@1`, `HealthFollowUp@1` |

Each Pattern is independently invocable. An Invocation ends with a committed record or reviewed
proposal, an emergency or qualified-professional handoff, an exact blocker, refusal, partial
result, cancellation, interruption, or explicitly unresolved evidence or external effect. A
longitudinal profile does not turn consultation into an endless Run.

## Contract

Health owns admitted clinical sources and their revisions; extracted claims and corrections;
profile revisions; case questions; patient-reported symptoms; clinician-authored assertions;
measurements and test results; competing explanations; diagnostic and care proposals; consent,
review, sharing, export, deletion, and follow-up receipts. It keeps source observation separate
from extraction, model interpretation, human confirmation, and externally established clinical
fact.

A Mind may summarize evidence, expose contradictions, ask discriminating questions, and propose
diagnostic or treatment options. It may not convert OCR into truth, silently reconcile conflicting
records, declare a diagnosis final, prescribe, order a test, administer treatment, or present
absence of a warning as proof of safety. Deterministic policy checks units, identity, source
coverage, duplicate intake, interactions represented in the admitted knowledge set, approval
bindings, and typed handoffs; passing those checks does not establish medical correctness.

Revision one supports personal clinical decision support for a consenting adult. Emergency care,
autonomous triage, pediatric care, pregnancy and perinatal care, psychiatric crisis response,
controlled substances, surgery, and unsupervised medication changes are outside its supported
treatment path. A red flag stops ordinary consultation and returns an emergency handoff; Health
does not monitor the person or contact emergency services.

## Authority and privacy

The patient, caregiver, clinician, prescriber, laboratory, and record custodian are distinct
principals. Consent to store a photograph is not consent to infer from it, disclose it, accept an
extracted claim, approve a plan, or perform a clinical effect. Human approval cannot create
competence, licensure, a prescription, or provider acceptance. [HitL](../../adr/25-hitl.md) binds
one exact eligible proposal; the applicable clinical and effect owner still rechecks authority at
execution time.

Clinical material is local and purpose-limited by default. Imports, remote inference, lookup,
retained media, sharing, research, export, and deletion have separate revocable permissions and
retention rules. The minimum necessary typed result may cross a boundary. A complete record,
credential, identifier, image, diagnosis, medication list, or genetic result never follows a
shopping, fitness, or household request merely because it might be useful.

[Wellbeing](../wellbeing/index.md) keeps ordinary eating, movement, and reflective check-ins. It may
receive an explicitly approved constraint such as a prohibited ingredient or movement limit,
without receiving its diagnosis or record history. Health may admit an exact patient-reported
observation from Wellbeing only with purpose-specific consent; neither owner rewrites the other.
Settled external clinician, laboratory, pharmacy, or health-record results enter as attributed
references. Live coordination with them would require a separately accepted Suite or integration
contract, not ambient access from this Composition.

## Recovery and falsification

Every accepted fact and proposal retains profile, case, source, policy, and Pattern revisions.
Corrections preserve earlier claims and invalidate dependent pending proposals. Restart resumes
only exact compatible work, never duplicates an import or approval, and never assumes an ordered
test, dispensed medicine, taken dose, or completed treatment from a request or missing
acknowledgement. Pending external effects settle by receipt, reconciliation, or qualified handoff.

The smallest falsifying fixture uses a wholly synthetic adult and fabricated photographs: a
two-page discharge note, a duplicated laboratory report, one illegible medication line, and a
typed new symptom. It must preserve page regions and extraction gaps, refuse a conflicting patient
identity, keep OCR separate from accepted facts, surface contradictory dates and units, stop on a
red flag, and produce a diagnostic proposal without declaring a diagnosis. A care proposal must
park for an exact authorized verdict, become stale after a relevant profile correction, survive
restart without duplicate approval, and support bounded export and deletion without erasing a
retention blocker. No real patient, provider, live health account, prescription, emergency call,
test order, purchase, or treatment enters the proof.

---

[Composition portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
