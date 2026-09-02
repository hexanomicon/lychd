---
title: Script
icon: material/script-text-play-outline
---

# :material-script-text-play-outline: Script

Script owns the canonical words: the article, narration, dialogue, title, description, and
formatted variants from which captions and spoken delivery are derived.

The editor selects claim revisions from the [ledger](sources.md), then writes each assertion with
its attribution, uncertainty, and disclosure intact. A sentence that combines several claims keeps
all dependencies. Formatting for another channel may change length or structure but cannot
silently change the claim, audience, or source meaning.

Narration and caption text are approved before audiovisual assembly can conceal uncertainty behind
voice, pacing, or imagery. `LanguageVersionRequest@1` may send the exact `ScriptRevision@1`,
locked source-media digest, target language and timebase, pronunciation and performance direction,
authority, and request digest to [Language Edition](../language-edition/index.md). A returned
`TimedLanguageAssetBundle@1` does not authorize Broadcast to substitute canonical words, extend
their use, or hide an attributed adaptation. Correcting the source script stales every dependent
Language Edition revision.

Review checks factual support, quotations, attribution, privacy, likeness, disclosures,
accessibility of language, and the intended audience. A finding points to the exact claim or text
revision. One bounded forward correction may answer it; an unsupported statement, unresolved
authority, or failed review leaves a draft, correction request, or refusal.

The accepted script passes to [Edit](edit.md) by digest. It remains readable and reviewable outside
the timeline, and later correction stales every narration, caption, cut, render, and publication
that depends on it.
