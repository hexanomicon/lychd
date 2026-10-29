---
title: Language Edition
icon: material/subtitles-outline
---

# :material-subtitles-outline: Language Edition

Two speakers share a short scene. One edition replaces a line in its original language; another
gives the scene translated dialogue and captions. Both must return to the same locked source.
Someone must answer for the words, casting, performance, timing, disclosure, and accepted result.
**Language Edition** keeps that work together.

A language edition need not translate. Same-language replacement, narration, repair, and
accessibility belong to the same durable project. Its passage ends in an attributable set of
timed-language assets, with a constrained track replacement when requested.

## Contract

The Composition is `language_edition.timed_media` revision `2`; its principal Pattern is
`language_edition.build_language_version@2`. A `LanguageVersionRequest@2` states:

- **Source:** an immutable media reference and timebase, or an exact locator with source-eligibility
  criteria and requested custody posture.
- **Meaning:** source and target languages, localization brief, glossary, and intended audience.
- **Performance:** exact eligible performer, voice, and capability references, with rights and
  disclosure requirements.
- **Finish:** timing, captions, format, accessibility, and acceptance conditions.

The request gives every later revision a common task. Generic translation, speech engines,
network acquisition, byte custody, Persona identity, music, visuals, editorial recutting, and
publication retain their own owners. Crossing into their work requires separate admission.

??? info "Revision 2 and the earlier design"

    Revision `2` supersedes revision `1` of the Composition and its `@1` Pattern,
    request, and result family. It admits source locators without acquiring Scout or custody
    authority and requires source-dialogue attestation before source-aligned wording becomes
    canonical. No registry or Run used revision `1`, so there is no executable migration. The
    earlier meanings remain part of the design history.

## One bounded language-edition road

**Establish the source.** Language Edition judges whether the source fits the request. A locator
may require a separately granted Scout Fetch or Download. Scout owns Search, Fetch, Download,
destination and contact policy, quarantine arrival, and acquisition receipts. After bounded
quarantine, separately granted, custody-owned Artifact Admission validates retained bytes and
establishes the immutable source master. A URL cannot stand in for that master; an acquisition
receipt cannot settle custody.

**Establish what was spoken.** Bounded demux and probe precede Echo Ear's transcript, diarization,
and timing observations. The proposed `DialogueTranscriptRevision@2` remains observation;
an authorized source-language reviewer must judge it. That reviewer creates `SourceDialogueAttestation@1`, binding the exact
source and timebase, stable segment identities, speakers, words, timing, uncertainty and
corrections, and the reviewer's Principal and evidence. Ambiguity stays unresolved. Only then may
source-aligned wording become canonical. When Broadcast's `ScriptRevision@1` supplies canonical
words, the attestation binds them to spoken segments without revising or taking ownership of
that script.

**Prepare and review the edition.** The attested source enters an optional attributed Translation
Spell and mandatory review, producing `LanguageEditionScriptRevision@2`. A same-language edition
can proceed without translation. Language Edition judges the wording in its scene; the
[translation contract](#translation-is-a-spell-localization-is-the-judgment) keeps the
transformation inspectable.

**Perform and conform.** Eligible casting selects human takes or Echo Voice synthesis for
`DialoguePerformanceRevision@2`. Preserve performer and voice eligibility: selecting them creates
no grant and copies no Persona authority. Dialogue editing, captions, and `DialogueConformMap@2`
align the performance to the source. Review linguistic fit, intelligibility, timing, rights, and
disclosure before acceptance.

**Hand over the assets.** `TimedLanguageAssetBundle@2` binds exact source, attestation, and script
revisions; performance and dialogue artifacts; captions and conform map; rights, disclosure,
findings, lineage, and admission criteria. A consumer can admit this bundle on its own. It is
neither a final picture container nor an editorial recut.

**End where the evidence ends.** If requested, restricted track mux and probes with back-check
may produce `LanguageVersionCandidate@2` under the [locked-picture contract](#preserve-the-locked-picture).
`LanguageEditionFindingSet@2` carries the findings. Each edition retains its attested source,
its own language and performance revisions, and every artifact actually produced. Partial,
incomplete, and unknown outcomes remain exact; an optional mux does not become canonical merely
because it exists.

## Translation is a Spell, localization is the judgment

The authority-qualified publisher of a versioned Translation Spell owns its transformation semantics;
[Spellweaver](../../sepulcher/extensions/weaver/index.md) validates its placement. The request pins
attested text, languages, glossary and protected spans, implementation, detection and fallback,
review, and declared loss. Retain original and derivative so the edition's reviewer can judge
speaker, scene, audience, duration, and fit.

Language detection grants no translation permission. Provider failure grants no substitute
language, voice, model, execution road, or paid service. Another Composition can reuse the exact
Spell while retaining its own judgment.

Language Edition owns captions, subtitles, scripts, and on-screen-language cue sheets as parts
of a timed edition. Content owners retain untimed writing; Frontend retains web and Altar chrome
catalogues. English-only Altar reference chrome requires neither English media nor translated
canonical identities.

## Voices belong to no shortcut

[Echo](../../sepulcher/extensions/echo.md) owns capture, STT, TTS, voice-profile facts, delivery,
and playback chronology. The Animator profile identifies the exact engine, model and acoustic
voice, supported languages and formats, licence, and measured limits. Performer consent and
source rights must independently cover the exact inputs.

Language Edition casts and directs pronunciation and performance, then accepts timing and
disclosure. [Avatar](../avatar/index.md) may supply exact eligibility for a Lich voice while
retaining Persona-linked presentation and Morphe. Resemblance establishes neither identity nor
rights; approval of one line does not authorize arbitrary later words. Riffmaw retains sung
performance and music. Across every road, generated sound proves neither playback nor hearing.

## Preserve the locked picture

The optional mux may add or replace only declared dialogue, narration, caption, subtitle, or
language-metadata tracks. Preserve every non-language stream. Record the preserved and replaced
digests, timebases, codecs, channels, and offsets, the loudness and intelligibility probes, and
the result digest. These records let a reviewer check what survived and exactly what changed.

Changed cuts, scene order, claims, picture sound, or music return to
[Broadcast](../broadcast/index.md). A constrained language replacement cannot quietly become a
new edit. The asset bundle remains a valid handoff without the optional mux; each receiving
owner judges the exact result for its own use.

### Model-native timed-language facet

A `VideoJob@2` may emit synchronized language only when its pre-execution
`MediaFacetAuthoritySet@1` declares `timed_language`, `language_edition.timed_media` revision `2`,
and the exact `LanguageVersionRequest@2` digest. Before execution, resolve the exact Echo speech
interface and profile, performer and acoustic voice, language support, consent, rights,
disclosure, and retention. Native video audio has the same obligations.

Technical settlement by Prism is followed by independent Language Edition admission. Its
`SemanticFacetAdmissionReceipt@1` binds child and compound digests, source attestation and script,
speaker and language role, use, rights, timing, findings, decision maker, and disposition. Retain
that receipt and parent in both the bundle and any optional mux.

Quarantine or delete undeclared speech or text. Demux, labels, or another owner's receipt cannot
admit this facet, and an inseparable compound requires every necessary owner's acceptance of
the exact digest and use.

## Neighbours keep their truth

The source and the result pass through distinct kinds of judgment:

| Neighbour | Contribution it continues to own |
| --- | --- |
| Prism | Attributed OCR, regions, frames, motion, lip-alignment observations, and technical derivatives. |
| Atelier | Accepted visuals. |
| Riffmaw | Music masters, stems, and cues. |
| Avatar | Eligible presentation. |
| Broadcast | Locked editorial source and requests; canonical claims and words; picture sound, recut, final edit, release, and correction. |

Settled exact references need no Suite. A promised result that actively admits, awaits, cancels,
retries, recovers, or jointly settles new work across those owners requires one. A Product may
package a language edition without taking its records; the technical Composition name does not
thereby become the market name.

## Failure, restart, and the first proof

Use stable segment identities to keep every stage tied to the exact source and timebase.
Transcript, attestation, translation, performance, alignment, dialogue-mix, mux, and review attempts
must retain independent revisions and dispositions. This preserves where work stopped when a
language is unsupported, a speaker is ambiguous, rights are missing, timing is lost, intelligibility
fails, the source becomes stale, the budget is exhausted, or provider/write effects are
indeterminate. Return the appropriate findings, refusal, partial result, or `unknown` outcome.
Restart must use reconciled immutable artifacts and settled attempts, without silent substitution.

The first falsifying proof remains a target: run a network-disabled synthetic two-speaker video
with separate picture, dialogue, music-effects, and caption streams on a known timebase. Fake
Ear, Translation, and Voice should build both a same-language and a translated edition. Check
preserved picture and non-language digests, lineage, attestation after human correction, glossary
protection, timing pressure, caption alignment, partial speaker refusal, crash recovery,
deterministic mux, export, and deletion. This would prove the contract's passage. It would not
prove translation quality, real-voice performance, rights, publication, or delivered operation.

[Workflow](../../adr/28-workflow.md) owns the score and its admissions;
[Audio](../../adr/37-audio.md) and [Vision](../../adr/36-vision.md) own the media boundaries.
Return to the [Composition Portfolio](../index.md) for the applications that may receive the
edition.
