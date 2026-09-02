---
title: Language Edition
icon: material/subtitles-outline
---

# :material-subtitles-outline: Language Edition

Language Edition turns one admitted timed-media work into an attributable language edition. It owns the
language-edition project, source-aligned words, target-language judgment, casting and performance
direction, dialogue timing, captions, and the acceptance of a constrained language-track
replacement. Speech engines, generic translation, Persona identity, music, visual authorship,
editorial recutting, and publication remain with their own offices.

The target language may equal the source language for replacement dialogue, narration, repair, or
accessibility. Translation is therefore an optional semantic act inside the Pattern, not the
definition of dubbing and not a reason to create an ownerless Translation Composition.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `language_edition.timed_media` revision `1` |
| **Principal Pattern** | `language_edition.build_language_version@1` |
| **Begins with** | a `LanguageVersionRequest@1` binding an immutable admitted source-media reference and timebase; source and target language facts; localization brief, glossary, audience, rights and disclosure posture; exact eligible performer, voice, or capability references; and timing, caption, format, accessibility, and acceptance criteria |
| **Can return** | immutable `DialogueTranscriptRevision@1`, `LanguageEditionScriptRevision@1`, `DialoguePerformanceRevision@1`, `DialogueConformMap@1`, or `TimedLanguageAssetBundle@1` records; a constrained `LanguageVersionCandidate@1`; `LanguageEditionFindingSet@1`; or exact partial/non-completion |
| **Stops before** | acquiring a source locator, granting voice or likeness rights, changing Persona identity, composing music, authoring picture-bound effects, changing the locked editorial cut, publishing, or claiming that generated audio was heard |

Language Edition qualifies as a Composition because the project survives any one engine or Product. Segment
identity, source/target correspondence, glossary choices, casting, pronunciation, timing,
disclosure, review findings, accepted performance revisions, unresolved regions, and recovery all
remain durable application truth. A Product may package Language Edition by itself, but need not reuse its
technical name as the market name. Reusing Echo, Prism, Scout, or a translation implementation
does not turn those Extension Domains into the application.

## One bounded language-edition road

```text
optional upstream acquisition (outside Language Edition)
→ source locator
→ Scout Fetch/Download + separate Artifact Admission
→ immutable source master + exact timebase handoff
Language Edition Invocation begins
→ bounded demux/probe
→ Echo Ear transcript, diarization, and timing observations
→ source-aligned DialogueTranscriptRevision@1
→ optional attributed Translation Spell + human or admitted review
→ LanguageEditionScriptRevision@1
→ casting from exact performer/voice eligibility references
→ human takes or Echo Voice synthesis
→ DialoguePerformanceRevision@1
→ dialogue edit, alignment, captions, and DialogueConformMap@1
→ intelligibility, linguistic, timing, rights, and disclosure acceptance
→ TimedLanguageAssetBundle@1
→ optional constrained language-track mux against the locked master
→ probe and back-check → LanguageVersionCandidate@1 or an exact finding
```

Every arrow is separately admitted. A URL is not media custody, STT is not a canonical script,
detection is not permission to translate, translated prose is not an accepted performance, TTS
generation is not playback, and a successful mux is not publication. A provider failure never
authorizes another language, voice, model, road, or paid service.

The Language Edition mux may replace or add only the declared dialogue, narration, caption, subtitle, and
language-metadata tracks against an exact locked source master. It records preserved and replaced
stream digests, timebases, codecs, channel maps, offsets, loudness and intelligibility probes, and
the resulting digest. A new cut, reordered scene, changed claim, newly authored picture sound, or
different music is editorial work for [Broadcast](../broadcast/index.md), not a convenient mux
option.

`TimedLanguageAssetBundle@1` is the accepted downstream handoff: exact source and edition-script
revisions, performance and dialogue-track artifacts, captions, conform map, rights/disclosure
posture, findings, lineage, and admission criteria. It is not a recut or final picture container.
`LanguageVersionCandidate@1` is an optional restricted derivative made by muxing that exact bundle
against one locked master while preserving every non-language stream. Broadcast or another
consumer may admit the bundle into its own assembly without treating the candidate as canonical.

## Translation is a Spell, localization is the judgment

[Spellweaver](../../sepulcher/extensions/weaver/index.md) can validate and place a versioned
Translation Spell, but it does not own linguistic truth. The Spell's authority-qualified publisher
owns its generic transformation semantics and revision; the placement pins original text, source
and target languages, glossary and protected spans, implementation revision, detection and
fallback policy, review requirements, and declared loss. Language Edition retains both source and derivative
and decides whether the result is fit for this speaker, scene, audience, duration, and edition.

Another Composition may reuse the same exact Translation contract while retaining its own records,
criteria, and finish judgment. Website and Altar chrome localization remains a Frontend catalogue
concern; documents, product copy, and other untimed writing remain with their content owner. Language Edition
owns captions, subtitles, scripts, and on-screen-language cue sheets only when they are part of its
timed language edition. The FOSS reference Altar can therefore remain English-only without making
multilingual media impossible or baking English grammar into canonical identities.

## Voices belong to no shortcut

[Echo](../../sepulcher/extensions/echo.md) owns speech capture, transcription, synthesis, delivery,
and their chronology. An Animator profile names the exact engine, model or acoustic voice,
languages, formats, licence, and measured limits. Performer consent and source rights remain exact
inputs; neither an attractive result nor a profile name grants them.

Language Edition owns only the casting of an eligible reference to a role in this edition, its direction,
pronunciation, timing, disclosure, and performance acceptance. [Avatar](../avatar/index.md) may
reference an eligible voice in a Lich presentation profile or supply that exact eligibility as an
external precondition when the Lich is being dubbed. Language Edition cannot revise the Persona, broaden the
voice use, mint identity from resemblance, or make one approved line authorize arbitrary later
words. Riffmaw retains sung performance and music production rather than general speech.

## Neighbours keep their truth

| Neighbour | What Language Edition may consume | What remains there |
| --- | --- | --- |
| [Scout](../../sepulcher/extensions/scout.md) | an exact admitted source artifact and acquisition receipt | destination policy, web contact, download, quarantine, and Artifact Admission |
| [Echo](../../sepulcher/extensions/echo.md) | attributed transcript/timing observations and speech artifacts | capture, STT/TTS capability, voice-profile facts, synthesis and playback chronology |
| [Prism](../../sepulcher/extensions/prism/index.md) | source-grounded OCR, regions, frames, motion or lip-alignment observations, and bounded technical derivatives | visual/spatial effect contracts and provenance |
| [Voidlight](../voidlight/index.md) | an immutable accepted visual/VFX master or forward correction | visual commission, creative direction, picture and motion acceptance |
| [Riffmaw](../riffmaw/index.md) | immutable music masters, stems, and cue maps | composition, musical performance, production, mix, and musical acceptance |
| [Avatar](../avatar/index.md) | an exact eligible presentation or voice reference when applicable | Persona-linked presentation envelope, Morphe, and projection membership |
| [Broadcast](../broadcast/index.md) | a locked editorial master and exact language-edition request | canonical claims and words, picture sound, recut, final editorial timeline, release and correction |

An already-settled reference crosses each seam without a Suite. A Suite is needed only when one
promised result must actively admit, await, cancel, retry, recover, or jointly settle new Language Edition,
Voidlight, Riffmaw, Avatar, or Broadcast Invocations.

## Failure, restart, and the first proof

Each segment has a stable identity against the exact source digest and timebase. Transcript,
translation, performance, alignment, dialogue mix, restricted mux, and review attempts retain
their own revisions and terminal dispositions. Unsupported language, ambiguous speaker, missing rights, excessive timing
loss, failed intelligibility, stale source, exhausted budget, or indeterminate provider/write
effect returns a finding, refusal, partial edition, or `unknown`; none is silently repaired by
substitution. Restart resumes only from reconciled immutable artifacts and settled attempts.

The smallest proof is local, synthetic, and network-disabled: one short two-speaker video with a
known timebase and separate picture, dialogue, music-and-effects, and caption fixtures. Produce one
same-language replacement and one translated edition through fake Ear, Translation, and Voice
implementations; preserve the locked picture and non-language stream digests; prove segment
lineage, glossary protection, one human correction, timing pressure, caption alignment, partial
speaker refusal, crash recovery, deterministic mux, export, and deletion. It proves the
Composition contract—not translation quality, a real voice model, performer rights, publication,
or delivery.

Related: [Workflow](../../adr/28-workflow.md) · [Audio](../../adr/37-audio.md) ·
[Vision](../../adr/36-vision.md) · [Composition Portfolio](../index.md)
