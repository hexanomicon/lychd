---
title: Transmuter
icon: material/flask-outline
---

# :material-flask-outline: Transmuter

A conversation archive contains your words, a model's suggestions, abandoned ideas, and decisions
that may have changed. Transmuter would work through that material with its attachments, identify
what each source actually says, and prepare grounded proposals for what the Lich could remember
or use to develop its identity.

The name **Transmuter** and its two internal responsibilities are settled in this candidate study,
reviewed **2026-09-11**. Portfolio acceptance and executable contracts remain open; [State of
Work](../../state-of-the-work.md#composition-portfolio-delivery) owns delivery.

## From sources to proposals

The operator selects a source, purpose, permitted destinations, and processing bounds. Transmuter
keeps a processing dossier while two internal stages work through the material:

| Stage | Reader question | Result |
| --- | --- | --- |
| [Extractor](extractor.md) | What is here, who produced it, and how should it be named and classified? | Source-located units with attribution, proposed names, labels, and uncertainty. |
| [Synthesizer](synthesizer.md) | How does this relate to what is already known, and what could be adopted? | Evidence-linked knowledge and proposals for separately admitted use. |

For a first personal intake, a smaller model could identify and prioritize material from a bounded
chat export or supplied phone history before a larger model synthesizes selected units. That split
is a possible implementation of the two stages. Selection would need to account for deferred
material and bring relevant corrections and contradictions into synthesis with the earlier claims.

Extractor and Synthesizer are internal parts of Transmuter, not nested Compositions, Extension
Domains, fixed Agent identities, or independent coordinators. Naming and labeling belong to
Extractor; no separate Labeler is introduced.

A chat archive and its images can yield a proposed preference, a project history, and a possible
Persona revision. The operator's words remain distinct from the model's interpretations. A
contradiction stays visible. [Archive](../../adr/27-memory.md) or
[Mirror](../../adr/32-identity.md) decides whether to accept the exact proposal, and Transmuter
records that outcome alongside what it prepared. In the designed memory path, Archive retains
admitted records in the [Phylactery](../../sepulcher/phylactery/index.md); its Curator separately
decides which revisions are eligible for recall.

## Learn through Transmutation

[Transmutation](../../divination/transmutation/index.md) gives the two stages a method for
learning from what they transform. Suppose an archive contains “keep answers short,” followed
months later by “explain this design fully.” A model has summarized both as “the operator always
prefers brevity.” The useful result must recover whose words support which claim, what their
contexts permit, and how a later correction could reach the proposed lesson.

| Chapter | Question within this intake |
| --- | --- |
| [Genesis](../../divination/transmutation/genesis.md) | Could the statements express a general preference, a task-specific request, or a changed preference? Form alternatives from attributed units before settling their relation. |
| [Trial](../../divination/transmutation/trial.md) | Compare each interpretation with the exact source passages and authorized surrounding context. Include the inconvenient statement; unprocessed material remains a gap. |
| [Canon](../../divination/transmutation/canon.md) | Declare before extraction and synthesis what would support the proposed use: correct speaker, preserved scope, traceable evidence, and the receiving owner's requirements. More extracted claims or a smoother summary cannot substitute for these conditions. |
| [Revelation](../../divination/transmutation/revelation.md) | Separate the observed requests from the diagnosis that their contexts differ and the proposal for a scoped preference. The model's universal summary is another attributable claim to examine. |
| [Distillation](../../divination/transmutation/distillation.md) | Carry the supported distinction with its conditions, counterevidence, and proposed next use. A later correction should reopen the affected preference rather than erase unrelated history. No adoption may be the warranted result. |

These chapters can recur within either stage; they add no five-stage execution pipeline.
**Canon precedes the attempt.** A later statement does not automatically defeat an earlier one:
changed context, changed preference, and unresolved contradiction require different conclusions.

The Tree's [relations](../../divination/transmutation/genesis.md#relations-within-relations)
sharpen the method. Chokhmah opens interpretations and Binah asks what supports their structure.
Chesed gives a neglected source room to matter; Gevurah limits what may be inferred from it.
Tiferet seeks a useful composition that preserves disagreement where it remains unresolved.
Netzach sustains the search; Hod can acknowledge that the available material cannot support the
desired conclusion. Their interaction matters more than assigning a separate Agent to each name.

The [receiving relation](../../divination/transmutation/genesis.md#repair-the-relation) reaches
the handoff itself. “Prefers brevity” loses the condition that made the lesson usable; a scoped
proposal carries that condition to Archive or Mirror. Likewise, an archive's description of the
Lich may inform a Persona proposal without establishing what it should become. Distillation
preserves a way back to correction within the dossier's privacy and retention bounds; the
receiving owner still decides what may enter memory, identity, or training.

## Sources and machinery

The candidate scope includes mobile shared items, conversation exports such as ChatGPT or Claude
archives, social exports and links such as Facebook material, documents, images, recordings, and
supplied system-inventory snapshots. These name intended inputs, not delivered adapters or current
platform access. A device inventory remains a dated observation; live discovery and host control
are separate work.

Reliquary would retain original bytes under its custody contract. Scout can supply admitted
acquisition, while [Prism](../../adr/36-vision.md) and [Echo](../../adr/37-audio.md) supply media
processing. Synthesizer's [receiving-owner map](synthesizer.md#receiving-owners) distinguishes
Memory, Persona, training, and code candidates. Each job selects the branches its purpose needs.

Using several Extension mechanisms does not make Transmuter a Suite. A promise that actively
coordinates separate Composition-owned Invocations requires a [Suite](../products-and-suites.md#compositions-relate-without-nesting).
This study supplies no general installation, self-extension, or autonomous evolution coordinator.

## The processing dossier

The proposed durable dossier lets the operator see what was admitted, what each stage produced, and what remains
unresolved. It owns the processing purpose and scoped authorization, source manifest and fixed
revisions, privacy/retention/resource bounds, and stage implementation and configuration revisions.
As work proceeds, it keeps progress, extracted units, corrections, knowledge candidates, and their
dependencies together.

For each proposed handoff, retain the exact payload, attempt identity, receiving receipt, and
separate outcome. The dossier references original artifacts so a reader can return to the
evidence; it does not become their byte-custody owner.

Completion means the admitted scope was processed and every proposed handoff has an accounted
disposition. It does not require every proposal to be accepted. Partial work identifies unfinished
sources or proposals; refusal names the blocker; cancellation stops new work. An unknown receiving
effect remains unresolved until reconciled and cannot be reported as successful completion.
Committed receiving-owner effects survive local cancellation.

The stage pages specify how their attempts can be retried or corrected. Deletion must follow
the policies of artifacts, Archive, and Mirror, retain only permitted lineage, and mark dependent
material invalid where required. That process can account for stored records and proposals; it
cannot promise to remove influence from already trained weights.

## What would establish the application

A bounded historical chat import and ongoing mobile captures are two independently useful cases
for the same dossier and judgment. Each mobile arrival remains bounded; connecting a source grants
no unlimited background collection. The candidate must establish exact schemas, Patterns,
admission and custody, implementation, and receiving contracts before execution.

The first network-disabled synthetic fixture should include duplicate imports, changed source
content, a model claim misattributed to the operator, conflicting preferences, an uncertain image
label, a denied destination, cancellation and resumption, and an unknown downstream outcome. It
must demonstrate provenance-preserving reuse, correction, honest partial completion, and refusal
to repeat an unresolved effect. This is proposed acceptance work, not an implemented test or source
scaffold.

[Composition studies](../index.md#candidate-studies) · [Extractor](extractor.md) · [Synthesizer](synthesizer.md)
