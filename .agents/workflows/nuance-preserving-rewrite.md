# Nuance-Preserving Rewrite

## Trigger and acceptance

Use this playbook when documentation must be rewritten from first principles, compacted, or split
without laundering away technical distinctions, authored myth, etymology, humor, compatibility
anchors, or recovery law.

Success is not a target percentage. The result must be easier to enter, smaller where repetition
permits, correctly routed to its owners, and at least as precise as the material it replaces.

## Human voice calibration

Use the operator-finished [README](../../README.md) and
[Prophecy](../../docs/index.md) as approved voice references. Preserve them during this campaign.
This brief records the operator's 2026-09-19 calibration for mythic reader-facing pages; it does
not prescribe the register of every technical contract or ADR. The Sepulcher epigraph below is
the first result of this calibration; the following paragraph and the rest of the pilot have not
yet received human approval.

The opening quotation must create atmosphere. The first paragraph should carry that touch into
the page. Seek an evocative association that belongs to the place, with cadence that makes the
line worth saying. The technical correspondence may be implicit. Do not immediately flatten
the atmosphere into a runtime inventory.

The operator's next Sepulcher correction starts the prose immediately with what the place is:
the Linux pod, managed by systemd, in which LychD's services live. Keep that concrete opening,
with accurate Podman/systemd terminology. The atmospheric quotation can lead straight into a
plain definition; it does not require another metaphor or a page-tour announcement first. This
feedback settles the opening direction, not approval of the rest of the paragraph or page.

The anatomy introduction exposed a second reader-entry problem. The operator rejected “The
whole, its law, body, and memory” as a heading, and “The First Invocation brings Caller and
Called face to face” because a new reader knows none of those terms. Introduce the thing and
what it does in familiar words before relying on its lore vocabulary. Links provide depth;
they do not excuse a sentence that requires several other pages to understand. Keep the mythic
names, but give each a readable meaning where it first matters.

### Anchor policy for this campaign

The operator explicitly wants renamed sections to drop their old anchors. During this rewrite,
use the current heading anchors and update maintained inbound links directly. Do not retain
legacy IDs, compatibility aliases, or redirects solely to keep old URLs working; those old
URLs are intentionally allowed to break. This campaign instruction overrides the generic
compatibility-preservation steps below for the renamed sections.

### Discover the line through variations

The operator explicitly describes this as an evolving discovery process. Try phrases, notice
what resonates, use those associations to clarify what the passage wants to become, then try
further variations. The subject and the language develop together. Preserve the promising
fragments and vary what remains unresolved; as the image sharpens, make the next set closer
rather than restarting broad brainstorming. Do not freeze an early interpretation into a
permanent style rule or claim that an analytical explanation makes a phrase good.

### Sepulcher calibration result

The operator selected **“Align the stones and summon your destiny.”** Paired with the opening they
had developed, the page now reads:

> Within these walls, the Lich slumbers. Align the stones and summon your destiny.

**Stones** was the productive discovery: the operator explicitly recognized the allusion to
**Soulstones**. **Align** carries the geometric arrangement. The ending evolved through
awakening, Will, and fate before the operator settled on **“summon your destiny.”**
Keep that selected wording. Its suggestive meaning belongs in the epigraph; do not append an
explanation of the metaphor there or replace it with a literal instruction about the software.

The earlier kingdom/home images helped discover a place the reader inhabits and shapes. The
arrangement of Soulstone containers within the Sepulcher gave those images substance. **“In their
courses”** was explicitly rejected even though **“Set the stones”** had opened the right route.
**“Sire”** and the attendant-welcoming-a-visitor interpretation were also rejected: the desired
effect became an inscription, without a servant announcing the reader's arrival.

This is a record of how this particular line emerged. Use its discovery process on other pages;
do not distribute stones, slumber, destiny, or the same sentence rhythm across the whole grimoire.

### What the exploration taught

- **“Sealed in its grave, it awakens”** connects enclosure/security and awakening, but its
  cadence and effect did not satisfy the operator. Technical correspondence alone is insufficient.
- **“All eyes shall be opened”** has the desired resonance, but the operator rejected borrowing
  a recognizable N'Zoth line. Seek original language with evocative associations.
- **“In the dark, he awaits”** was an exploration of a spooky presence, not an approved line.
- **“Here lies the kingdom of the undead, arrange it to your will”** connected the place,
  its myth, and its use in a promising way. “The chambers are empty” and “Your kingdom awaits”
  also helped the operator identify the desired feeling.
- **“This is the place Sire! Let us begin”** was an early promising trial. The later explicit
  rejection of “Sire” and staged personal address supersedes that direction.
- The operator rejected **“Even a daemon needs a body”** and **“We have a Lich to keep undead.
  Best learn its anatomy before reaching for the scalpel.”** Do not recycle them or assume
  that adding a joke creates the desired atmosphere.

Offer a small set of variations during calibration. Preserve the distinction between exploratory
seeds, rejected candidates, and selected wording. The writer's explanation is not reader
acceptance. Carry the method across pages while preserving each page's subject and authored
differences; do not make one successful phrase or sentence pattern a universal template.

## Roles

| Role | Context | Responsibility |
| --- | --- | --- |
| **Campaign owner** | Corpus map, global voice, topology, and final diff | Orders packages, resolves cross-page ownership, and runs corpus gates |
| **Page Lead** | Old page, parent index, owning law, State, inbound links, anchors, and smallest evidence slice | Builds the semantic packet, decides page shape, and performs informed synthesis |
| **Blind Writer** | Packet only; no repository and no old prose | Produces a genuinely new rhetorical structure |
| **Critics** | Final package or corpus plus one narrow rubric each | Defend nuance and myth; prosecute slop, duplication, semantic divergence, and broken routes |

Page Leads may be pooled. Blind Writers require a fresh stateless worker or runtime-attested
context reset; a prompt saying “reset” is not that attestation.

A warm Package or Page Lead must spawn its own bounded Drafters: their candidate returns into the
same informed context that assembled the packet. A sibling writer can relay text, but cannot
return the authority, protected material, or global voice held by that Lead. Use at most two
descendants per package; their filesystem access makes them **packet-isolated Drafters**, not Blind
Writers.

## 1. Establish the page's office

Read the selected scope completely, then enter through the public index chain. Inspect the smallest
set that can establish:

- the page's one primary question;
- its architectural and delivery owners;
- exact local operation, refusal, failure, and recovery;
- canonical terms and authored images;
- inbound fragment links and deliberate compatibility anchors; and
- neighboring pages that could duplicate or contradict it.

Do not inventory the corpus merely because the campaign is broad.

## 2. Run the shape gate

Ask before drafting:

1. Does this page still perform one coherent office?
2. Does it already contain at least two stable workflows with distinct inputs, returns,
   refusal/recovery, and owner handoffs?
3. Would separate leaves answer different reader questions without repeating the same law?
4. Can every proposed leaf be written from present contracts, rather than predicted growth?

Choose one verdict:

- **LEAF** — one journey; keep it whole.
- **DIRECTORY NOW** — several stable journeys; make `index.md` a map and give each leaf one office.
- **DIRECTORY LATER** — likely growth, but a split today would create promise-pages or ceremony.

Concept count, heading count, or a long ADR is not evidence for a directory. An index routes; it
does not summarize every leaf. Record the evidence for every verdict. For **DIRECTORY LATER**, also
name the missing contract and the observable event that should reopen the decision; “this will
probably grow” is not a trigger.

## 3. Build the semantic packet

Classify each claim:

- **KEEP_LOCAL** — needed to use or interpret this page.
- **SUMMARIZE_AND_LINK** — one local sentence is useful; another owner holds the depth.
- **OWNER_ONLY** — remove from the page and route directly.

Then give the Blind Writer a closed packet containing:

- target genre, audience, primary question, and hard word envelope;
- exact facts, sequences, records, states, limits, and recovery behavior;
- maturity and links to law and State;
- protected terms, etymologies, quotations, anchors, and deliberate humor;
- neighboring distinctions and forbidden authority;
- opening brief: desired effect, not a generic slogan template;
- banned habits specific to the package; and
- expected route or heading shape.

The packet must contain enough truth to write the page without archaeology. It must not quote the
old body as a hidden outline.

## 4. Draft blind

The Blind Writer receives no filesystem, old prose, diff, or sibling drafts. Before invocation,
retain a small launch receipt: packet digest, target, worker/session identity, exposed roots,
callable tools, and whether context reset is runtime-attested. Any repository root or read tool
disqualifies the worker from the blind role. A packet-isolated Drafter may inspect its exact
filesystem subset and edit there directly, but has lower authorship assurance and must never be
described as blind. Ask for one complete Markdown candidate and a word estimate. Its job is
authorship: fresh sequence, varied cadence, plain footholds, one earned image, and concrete nouns
and verbs.

Reject as a draft-level failure when it:

- invents a term, delivery claim, owner, or recovery guarantee;
- turns an ADR into a shorter ADR;
- reproduces the packet as a catalogue;
- uses repeated constitutional antithesis as cadence;
- hides the page behind status boilerplate; or
- meets the word target by deleting distinctions.

## 5. Synthesize informed

The Page Lead compares the old page, packet, owners, and blind draft. The Lead is the decisive
editor, not a pass/fail clerk:

1. keep the new structure when it reads better;
2. restore every supported nuance the draft lost;
3. correct terms, maturity, authority, sequence, and recovery;
4. collapse duplicated law into a link;
5. preserve exact anchors and protected lines;
6. make the opening specific enough that its title could be guessed; and
7. stop when another cut would cost clarity or meaning.

Do not send ordinary corrections back through another generation. Use a repair turn only when the
draft's architecture is unusable or the packet itself was incomplete.

## 6. Review at the right scale

Page-local review checks semantic parity, owner alignment, links, fragments, and word shape.
Package review checks:

- repeated openings and adjacent sentence templates;
- term and role collisions;
- index coverage and leaf duplication;
- chronology, handoffs, and relative-link breakage; and
- whether a directory was expanded too early or too late.

Corpus critics should have separate briefs:

- a **Defender** protects myth, etymology, humor, and authored asymmetry;
- a **Compressor** finds deletions that lose no distinction;
- a **Prosecutor** identifies synthetic cadence, disclaimers, vague abstractions, and duplicated
  doctrine;
- a **Navigator** checks ownership, routes, anchors, and build output.

Agreement among critics is not truth. The campaign owner resolves findings against canonical
owners.

## Context economy and scheduling

- One warm Package or Page Lead performs archaeology once, then feeds closed packets to no more
  than two of its own descendants.
- Several Leads may research independently while one writer is active, but sibling drafts return
  through a lossy relay and do not replace the package Lead's synthesis.
- Serialize blind Writer turns when concurrency is scarce; never mix two packets.
- Keep global voice and topology with the campaign owner, not in every page prompt.
- Retain only short receipts: counts, protected material, routes, verdict, checks, and unresolved
  owner conflicts.

The campaign handoff or review receipt must expose each writer's packet digest, child/session
identity, filesystem roots and callable tools, context-reset attestation, and any lower-assurance
classification. A reviewer must be able to distinguish blind authorship from packet-isolated
drafting without trusting the campaign narrative.

If an agent limit prevents a new Writer and the runtime cannot attest a cleared context, the
campaign may use that worker only as a **packet-isolated Drafter**, never call it blind, and record
the lower assurance. The Page Lead must check the draft for phrases and structures leaked from
earlier assignments, and package review must run a cross-page similarity pass. For work where
authorship independence is itself acceptance evidence, pause until a fresh worker is available.
If an owner conflict appears, stop that page and repair or escalate the owner; fluent
reconciliation is forbidden.

## Interruption and migration recovery

Before moving a page into a directory, record a compact migration manifest: old path, new paths,
all inbound links and fragments, navigation entry, parent index, and required compatibility
anchors. Create and verify leaf candidates before removing the old route.

If work stops between file creation, index movement, and route updates:

1. treat the package as incomplete and do not publish or build it as accepted;
2. recover the manifest from the task receipt, then inspect `git status` and search every old path;
3. resume from the first unmatched route without deleting either side; and
4. finish path, navigation, index coverage, links, fragments, and build in one closure.

Do not use destructive reset as migration recovery. The working diff and manifest are the
checkpoint.

## Verification

For each page:

- resolve every local link and required fragment;
- search inbound links before moving a path or heading;
- run `git diff --check` on the exact target; and
- compare before/after claims, not only words.

For a migrated package:

- update every old path, parent index, Lexicon/State/ADR route, and navigation entry atomically;
- ensure the directory index covers every direct child; repeat a child link only when distinct
  reader routes need exact anchors; and
- preserve deliberate compatibility anchors.

For the campaign, run the matching scope gates, a clean Zensical build for published pages, and
the State architecture test when delivery prose or routes move. Report compression as an outcome,
never as evidence that the rewrite is good.
