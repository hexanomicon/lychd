---
title: Transmuter
icon: material/flask-outline
---

# :material-flask-outline: Transmuter

A conversation archive contains your words, a model's suggestions, abandoned ideas, and decisions
that may have changed. Transmuter examines that material and its attachments, identifies
what each source actually says, and prepares grounded proposals for what the Lich could remember
or use to develop its identity.

**Transmuter** (`transmuter.intake`, revision `1`) is the Native Reference Composition for
interpreting imported material. It owns the processing dossier, the judgment that a proposal is
supported by its sources, and the record of each receiving owner’s decision. The contract is
design-only. [State of Work](../../../state-of-the-work.md#composition-portfolio-delivery) tracks delivery.

## From sources to proposals

A `TransmuterRequest@1` binds the operator’s scoped authority, purpose, admitted source
references and revisions, permitted comparison material and destinations, and privacy, retention
and resource bounds. The selected Pattern fixes the work. A correction also identifies the
earlier dossier, affected source or unit revision, and attributable correction. Both Patterns
use the same two internal stages where needed.

| Stage | Reader question | Result |
| --- | --- | --- |
| [Extractor](extractor.md) | What is here, who produced it, and how should it be named and classified? | Source-located units with attribution, proposed names, labels, and uncertainty. |
| [Synthesizer](synthesizer.md) | How does this relate to what is already known, and what could be adopted? | Evidence-linked knowledge and proposals for separately admitted use. |

For a first personal intake, a smaller model could prioritize material from a bounded chat
export or supplied phone history before a larger model synthesizes selected units. Whatever
the model arrangement, record deferred material and include relevant corrections and contradictions
when interpreting the earlier claims.

Extractor owns naming and labeling. Synthesizer owns interpretation of the selected evidence.
The Composition owns coordination and recovery across both stages. An implementation may assign
their work to different Agents.

A chat archive and its images can yield a proposed preference, a project history, and a possible
Persona revision. The operator's words remain distinct from the model's interpretations. A
contradiction stays visible. [Archive](../../../adr/27-memory.md) or
[Mirror](../../../adr/32-identity.md) decides whether to accept the exact proposal, and Transmuter
records that outcome alongside what it prepared. In the designed memory path, Archive retains
admitted records in the [Phylactery](../../../sepulcher/phylactery/index.md); its Curator separately
decides which revisions are eligible for recall.

## Learn through Transmutation

[Transmutation](../../../divination/transmutation/index.md) gives the two stages a method for
learning from what they transform. Suppose an archive contains “keep answers short,” followed
months later by “explain this design fully.” A model has summarized both as “the operator always
prefers brevity.” The useful result must recover whose words support which claim, what their
contexts permit, and how a later correction could reach the proposed lesson.

| Chapter | Question within this intake |
| --- | --- |
| [Genesis](../../../divination/transmutation/genesis.md) | Could the statements express a general preference, a task-specific request, or a changed preference? Form alternatives from attributed units before settling their relation. |
| [Trial](../../../divination/transmutation/trial.md) | Compare each interpretation with the exact source passages and authorized surrounding context. Include the inconvenient statement; unprocessed material remains a gap. |
| [Canon](../../../divination/transmutation/canon.md) | Declare before extraction and synthesis what would support the proposed use: correct speaker, preserved scope, traceable evidence, and the receiving owner's requirements. More extracted claims or a smoother summary cannot substitute for these conditions. |
| [Revelation](../../../divination/transmutation/revelation.md) | Separate the observed requests from the diagnosis that their contexts differ and the proposal for a scoped preference. The model's universal summary is another attributable claim to examine. |
| [Distillation](../../../divination/transmutation/distillation.md) | Carry the supported distinction with its conditions, counterevidence, and proposed next use. A later correction should reopen the affected preference rather than erase unrelated history. No adoption may be the warranted result. |

These chapters can recur within either stage; they add no five-stage execution pipeline.
**Canon precedes the attempt.** A later statement does not automatically defeat an earlier one:
changed context, changed preference, and unresolved contradiction require different conclusions.

The Tree's [relations](../../../divination/transmutation/genesis.md#relations-within-relations)
sharpen the method. Chokhmah opens interpretations and Binah asks what supports their structure.
Chesed gives a neglected source room to matter; Gevurah limits what may be inferred from it.
Tiferet seeks a useful composition that preserves disagreement where it remains unresolved.
Netzach sustains the search; Hod can acknowledge that the available material cannot support the
desired conclusion. Their interaction matters more than assigning a separate Agent to each name.

The [receiving relation](../../../divination/transmutation/genesis.md#repair-the-relation) reaches
the handoff itself. “Prefers brevity” loses the condition that made the lesson usable; a scoped
proposal carries that condition to Archive or Mirror. Likewise, an archive's description of the
Lich may inform a Persona proposal without establishing what it should become. Distillation
preserves a way back to correction within the dossier's privacy and retention bounds; the
receiving owner still decides what may enter memory, identity, or training.

## Sources and machinery

The source scope includes mobile shared items, conversation exports such as ChatGPT or Claude
archives, social exports and links such as Facebook material, documents, images, recordings, and
supplied system-inventory snapshots. Each input requires an admitted adapter or an explicitly
supplied artifact. A device inventory remains a dated observation. Live discovery and host control
require separate authority.

The dossier references original bytes held under [Reliquary’s custody contract](../../../adr/06-persistence.md#reliquary-custody). Webcrawler can supply admitted
acquisition, while [Prism](../../../adr/36-vision.md) and [Echo](../../../adr/37-audio.md) supply media
processing. Synthesizer's [receiving-owner map](synthesizer.md#receiving-owners) distinguishes
Memory, Persona, training, and code candidates. Each job selects the branches its purpose needs.

Using several Extension mechanisms does not make Transmuter a Suite. A promise that actively
coordinates separate Composition-owned Invocations requires a [Suite](../../products-and-suites.md#compositions-relate-without-nesting).
Installation, self-extension and autonomous evolution retain their own authority and recovery.

### Computer-session capture without a service API

A local recording can supply a call or working session as an input without
integrating the meeting service's API. The operator would select microphone input and playback
output as separate synchronized tracks, with optional video of one window or monitor. On Linux,
[PipeWire](https://docs.pipewire.org/group__pw__keys.html) supports playback capture, while the
[ScreenCast portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html)
offers desktop-approved screen sources. This records the selected local experience; it does not
supply participant identities, separate remote-speaker streams, chat history, or undisplayed
content. Whole-output audio may also contain unrelated applications and notifications.

The proposed recorder would run as an explicitly authorized helper in the logged-in desktop
session. Routine capture generally needs the user's session permissions rather than root;
[PipeWire access control](https://docs.pipewire.org/page_access.html) still applies to each client.
A containerized or remote Vessel would need a narrow typed device integration under the
[host-effect boundary](../../../adr/10-privilege.md), without acquiring a general shell or ambient
desktop access. Audio and visual permissions remain separately scoped.

An Altar control or CLI Intent could request the same bounded capture, optionally associated with
a Project or call. The proposed controls would select sources, a private destination outside the
checkout, retention, duration and storage limits, and expose active state and explicit stop.
Finalization would return exact artifact references and locations, with gaps or partial results
preserved; an unconfirmed stop remains unknown. Saved presets or later event triggers would
reuse this contract under current authority rather than grant permanent recording permission.
The recorder, Altar control and CLI remain proposed integrations.

Recording and interpretation remain separate. Original tracks would retain their common timeline
and acquisition facts; admitted speech transcription and visual extraction would produce
source-located derivatives for Extractor and Synthesizer. Summaries, decisions and proposed tasks
would link back to exact time intervals. Echo retains its speech boundary, and recording alone
authorizes neither analysis, remote transmission nor adoption into memory.

## The processing dossier

The durable `TransmuterDossier@1` identifies what was admitted, what each stage produced,
and what remains unresolved. It owns the processing purpose and scoped authorization, source manifest and fixed
revisions, privacy/retention/resource bounds, and stage implementation and configuration revisions.
As work proceeds, it keeps progress, extracted units, corrections, knowledge candidates, and their
dependencies together.

For each proposed handoff, retain the exact payload and its disposition. A dispatched handoff
adds its attempt identity and any observed receiving receipt. Refusal or a missing acknowledgement
retains the explicit unsent or unknown outcome. The dossier references original artifacts so a reader can return to the
evidence; it does not become their byte-custody owner.

An operator may revisit a dossier that preserves conflicting attributed sources and their
interpretations even when no downstream proposal is made. That useful result needs no receiving
admission; any handoff actually attempted still needs its own accounted disposition.

A `TransmuterOutcome@1` identifies the dossier revision, processed units and coverage gaps,
knowledge or proposal revisions, handoff attempt references and dispositions, and any blocker or
next action. Completion means the admitted scope was processed and every proposed handoff has an
accounted disposition. It does not require every proposal to be accepted. Partial work identifies unfinished sources or proposals.
Refusal names the blocker. Cancellation stops new work. An unknown receiving
effect remains unresolved until reconciled and cannot be reported as successful completion.
Committed receiving-owner effects survive local cancellation.

The stage pages specify how their attempts can be retried or corrected. Deletion must follow
the policies of artifacts, Archive, and Mirror, retain only permitted lineage, and mark dependent
material invalid where required. That process can account for stored records and proposals; it
cannot promise to remove influence from already trained weights.

## Pattern catalogue

| Pattern | Work and finish |
| --- | --- |
| `transmuter.interpret_sources@1` | Process one bounded source manifest. Return its dossier, attributed units, gaps and proposals. A complete dossier can conclude that no adoption is warranted. |
| `transmuter.revise_dossier@1` | Trace a correction from an exact predecessor to the units and proposals that depend on it. Retain earlier judgments, invalidate affected pending proposals, and account for any separately authorized correction sent to a receiving owner. |

## Verification

A bounded historical chat import and ongoing mobile captures are two independently useful cases
for the same dossier and judgment. Admit each mobile arrival within its current collection scope.
Preserve both acquisition paths when a historical import and a later mobile arrival contain the
same material.

A network-disabled synthetic fixture must include duplicate imports, changed source
content, a model claim misattributed to the operator, conflicting preferences, an uncertain image
label, a denied destination, cancellation and resumption, and an unknown downstream outcome. It
must demonstrate provenance-preserving reuse, correction, honest partial completion, and refusal
to repeat an unresolved effect. A receiving-owner correction requires the original proposal and
receipt, a new attributable proposal and the owner’s separate disposition.

[Composition Portfolio](../../index.md) · [Extractor](extractor.md) · [Synthesizer](synthesizer.md)
