---
title: Script
icon: material/script-text-play-outline
---

# :material-script-text-play-outline: Script

The canonical sentence must remain readable before it is spoken over an image. Script owns the article, narration, dialogue, title, description, and formatted variants from which spoken delivery and captions derive.

Open the [claim ledger](sources.md#build-the-claim-ledger) beside the script. If an interviewee
says a result is possible, a shorter caption must leave that uncertainty intact. Keep the exact
claim revision, attribution and disclosure behind the line. When one sentence joins several
claims, keep each link so that a reviewer can check all of them. A channel edit can shorten
the wording within the same audience and claim scope.

Approve narration and caption words before assembly. For a timed language version, `LanguageVersionRequest@2` can send [Language Edition](../language-edition/index.md) the exact `ScriptRevision@1`, locked media digest, target language/timebase, pronunciation/performance direction, authority, and request digest. The returned `TimedLanguageAssetBundle@2` cannot replace the canonical words and must keep any adaptation visible. If the source script is corrected, its dependent editions become stale.

Review the words for factual support, quotation, attribution, privacy, likeness, disclosures, accessible language, and audience. Tie each finding to the exact claim or text revision so a bounded forward repair can answer it. Where support or authority remains unresolved, keep the result as a draft, correction request, or refusal.

[Edit](edit.md) receives the accepted script by digest. Later correction stales dependent narration, captions, cuts, renders, and publications, preserving the original words and review history.
