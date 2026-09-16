---
title: Health record assimilation
icon: material/file-document-plus-outline
---

# Health record assimilation

The Magus can photograph a finite medical record, attach an existing document, or describe a
health event in their own words. `health.assimilate_record@1` turns that bounded intake into
reviewable claims and, only after admission, a new `HealthProfile@1` revision.

## Keep the source and the claim apart

`ClinicalSource@1` binds the person claimed by the source, source kind and custodian, capture and
clinical dates, page order, digest, purpose, consent, privacy and retention policy, and permitted
processing. A crop, rotation, contrast change, transcription, OCR pass, translation, or structured
extraction creates a traceable derivative. Imported content is data, never an instruction or a
grant of wider access.

OCR records text, page and image regions, confidence, extractor and configuration revisions,
coverage, unsupported regions, and transformations. It does not replace the image. A model may
propose document type, field meaning, units, code expansion, chronology, and likely duplicates,
but each `ExtractedClinicalClaim@1` points to the exact source region and says whether it is:

- patient reported, document extracted, clinician authored, laboratory reported, model proposed,
  deterministically derived, or human confirmed;
- verbatim, normalized, translated, or inferred;
- accepted, rejected, disputed, superseded, or unresolved.

Illegible text, cropped values, missing pages, uncertain decimals, mixed identities, conflicting
dates, and incompatible units remain explicit. The pipeline cannot complete a medication name,
dose, allergy, diagnosis, or test result from plausibility. Duplicate detection links acquisition
paths without deleting distinct originals or silently merging people.

## Build a corrigible profile

The reviewed profile can organize demographics needed for care, allergies and intolerances,
medications, conditions, procedures, immunizations, family and social history, measurements,
laboratory results, clinician instructions, patient testimony, attachments, and unresolved
questions. These are typed views over attributed claims, not one flattened biography. Sensitive
categories such as genetics, reproductive health, mental health, substance use, and identity
documents require explicit category and purpose admission.

An operator accepts, corrects, or rejects proposed claims in a bounded review. Corrections append
new attributed revisions and identify dependent cases and proposals that became stale. A newer
report can supersede a value without rewriting what an earlier report said. Silence confirms
nothing.

## Partial completion and departure

Intake may finish with accepted claims plus an exact list of unread, unsupported, disputed, or
unreviewed regions. Cancellation stops new processing and retains only material allowed by intake
policy. On restart, source digest, acquisition identity, processing revision, and completed-region
receipts prevent duplicated work while changed sources remain new evidence.

Export names the exact profile and source revisions included. Deletion stops new processing and
sharing, removes permitted originals and derivatives, and returns a content-free receipt; legal or
clinical retention obligations remain named blockers rather than being bypassed. Restored backups
must reapply deletion tombstones before reopening material.

---

[Health](index.md) · [Consultation](consultation.md)
