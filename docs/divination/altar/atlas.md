---
title: Atlas
icon: material/map-outline
---

# :material-map-outline: Atlas

A conversation can end while the undertaking continues. **Atlas** keeps its brief, concerns,
judgments, and proposed next step available across conversations and Runs. Begin with a software
release, a record, or the continuing care of a home; an existing conversation, Pattern, or Run
is unnecessary.

The current surface gathers this material in a **Project**. Its concerns name what deserves
attention, and its judgments retain your reasons for accepting, disputing, or questioning the
work. The guide below follows that Project from its first brief to a later review.

The wider map begins with a question or an idea before it has a Project. It asks what each Concern
means, how it breaks down, where it is addressed, and what supports a judgment. A Concern need
not come from a Covenant. [Independent Concerns and their relations](#concerns-before-a-project)
remain the designed direction.

[Owned Technology Map](technology-map.md) explores a candidate undertaking across devices,
software, firmware, and services: prefer more openness, retain exact evidence and unknowns, and
distinguish understanding from the ability to modify, replace, or recover a component.

## Put an undertaking on the map

Open **Atlas** in the [Altar](index.md#bring-one-intent) navigation. Create a project with a name and a brief: describe the
desired outcome or the responsibility you intend to keep. Add a proposed next step when you know
one. Saving records your plan; it does not submit an Intent or start execution.

The board lists retained projects and their lifecycle. Open one to work with its brief, concerns,
decisions, and related activity. `Active`, `Paused`, and `Closed` describe your planning choice.
You can reopen a closed project. Pausing or closing leaves admitted Runs alone and does not
promise to prevent new work through other instruments.

The proposed next step offers the project's explicitly linked conversations and **Choose or start
a conversation**. Each conversation appears once here even when it is linked to several concerns;
those evidence relationships remain separate. The chooser keeps a return link to the project and
lets you select or create a séance deliberately. Opening it does not send the brief or next step
to a model; you decide what to offer in Bridge.

## Make a concern answerable

A concern states a question, risk, requirement, or condition that needs judgment. Its optional
criteria explain what would make an answer adequate. Prefer something you can inspect, such as
“The export must preserve the original audio,” with criteria naming the comparison you will make.

Assess a concern when you can explain a judgment about it. Record **Sufficient**, **Insufficient**,
or **Disputed**, with your reason and any linked activity you cite. Until then, it remains
unassessed. Atlas retains the brief and concern text you judged, your local Sigil attribution,
and the assessment time. This preserved basis makes the judgment reviewable: a successful Run
alone cannot award sufficiency, and a linked Run does not show that every criterion was tested.

Changing the brief or a concern makes earlier assessments **need review**. The earlier judgment
and its original requirements remain readable. Record a fresh assessment after examining the new
basis. Atlas does not silently reinterpret what an older assessment meant.

On a stale latest assessment, **Compare with judged basis** shows the brief, concern and criteria
as judged beside their current values. This is a read-only comparison; a new judgment still needs
an explicit assessment save.

Use **Find a concern** and the **Assessment** filter to reach a question or judgment in a longer
project. The assessment form opens beside the concern and its history. Cited activity opens in a
new tab, letting you inspect it without leaving your draft.

The board filters its loaded page. It counts unassessed concerns, assessments needing review,
and current insufficient or disputed judgments separately. A stale judgment belongs under
needing review, rather than among current judgments. These counts answer different questions;
they do not combine into a measure of project health. Inside a project, the four count controls
select those same groups. **Clear concern filters** restores the full list and returns focus
to **Find a concern**.

Decisions retain a statement and reason. When a decision changes, record a replacement that
supersedes it. The earlier decision stays under **Earlier decisions**.

## Connect the work already done

Choose **Link to project** in Bridge or Orb, select a project in Atlas, and review the prefilled
activity before saving. You may associate it with a particular concern and add a context note.
This path can also create a new project before reviewing the link. Atlas's **Link activity** form
still accepts the identity from an Altar URL. References open the original
[Bridge conversation](bridge.md) or [Orb evidence](orb.md); those instruments retain their own
authority and show the Project association back to Atlas.

A session reference relates that conversation. It does not silently add all of its Runs. A Run
reference opens the currently retained evidence, with Orb's capture limits and gaps; Atlas does
not freeze a copy of that evidence. If the target becomes unavailable, the retained reference
does not become a successful result.

To inspect why an assessment reached its judgment, follow concern → assessment → cited reference →
conversation or Run. Each citation names an Atlas reference record by its own identity. Linking
activity to a concern is a separate relation and does not automatically cite it as evidence.
A relation view must keep uncited references recognizable and preserve each reference's scope
and note, even when several references lead to the same target.

Linking does not feed the whole project into a model, change the selected conversation's Context,
or authorize another act. Use Bridge's ordinary admission and consent when you decide to carry
out a proposed next step. Loom continues to own the reusable score; Nexus continues to show
readiness and physical transitions.

## Return after a failed save

Atlas saves through the Vessel. In the PostgreSQL profile, projects survive browser and Vessel
restarts. The test-only memory profile retains them only for its process lifetime.

Retry the same pending change when a save's outcome is uncertain. Its identity prevents duplicate
concerns, assessments, decisions, and references.

If another view changed the project, Atlas refuses the overwrite. Load the latest saved version
and compare the differing fields beside your draft. **Use saved…** adopts the saved value of one
field; **Use reviewed values** enables a new explicit save of the values now in the form. Review
fields the other editor changed, including those you left untouched. If the read fails, Atlas
shows that failure rather than an empty map.

The initial surface retains records when a project closes; it has no delete action. Existing
installations need the normal database migration before opening Atlas. Migration `0009` refuses
to remove its schema while projects remain.

[Frontend](../../adr/15-frontend.md#atlas-and-continuity-across-invocations) owns the design,
[Persistence](../../adr/06-persistence.md#atlas-records) owns retention, and
[State of Work](../../state-of-the-work.md#atlas-projects) records the implementation evidence
and remaining boundary.

## Reading direction

For interface review and design, use the following composition and acceptance case.

The current Project view puts concerns before secondary context. Wide screens keep the brief
and proposed next step beside them; narrow screens follow the concern list with that context.
The brief starts collapsed when concerns exist, while continuation links remain available.

The planned composition gives Concerns their own entrance and one readable detail. Meaning,
decomposition, where each part is addressed, criteria, judgment, original basis, attribution, and
cited references belong together; older assessments and decisions can unfold beneath them.
Inside a Project, its brief and proposed next step frame that same account. Keep unassessed,
stale, insufficient, and disputed counts distinct. A compact portfolio row helps compare
undertakings without turning planning lifecycle into a health score.

Start relations as an exact list for the selected concern. A small diagram is useful only if it
makes a decomposition, addressing relation, or citation chain easier to follow, with the kind of
relation stated and shared identities preserved. Neither similarity tags nor visual clustering
create Project membership or automatic coverage.

Acceptance case: return to a project with fifty concerns, find an assessment whose criteria
changed, inspect its cited Run, and reconcile a conflicting edit while retaining the draft and
judged basis. A shared conversation appears once as a continuation destination while its concern
relations remain distinct. Larger collection limits and catalogue-wide search need an explicit
server contract; hiding rows cannot create that support. This composition and its scale checks
are targets under [Frontend](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction), not
additional delivered controls.

## Concerns before a Project

Begin with “Can someone trust this answer?” even if the surrounding idea has no name. Break that
Concern down into “Can its sources be inspected?”, “Is uncertainty visible?”, and “Can a mistake
be corrected?” Each deserves its own meaning and criteria. The parent still asks whether these
parts are enough; three sufficient judgments need not settle the original question.

As an application takes shape, map where those Concerns are addressed:

| Concern | Possible place addressing it | What still needs judgment |
| --- | --- | --- |
| Sources can be inspected | A source record and the answer's citation view | Whether the cited material supports the actual claim |
| Uncertainty is visible | An answer policy and its presentation | Whether the reader can distinguish evidence, inference, and missing knowledge |
| Mistakes can be corrected | A correction procedure and revision history | Whether an earlier answer and its correction remain understandable |

In this proposed design, a part can address several Concerns, and a Concern can need several
parts. An empty addressing list exposes an unresolved need. The map would show how an application
answers its Concerns while leaving adequacy to judgment and testing. If the idea later becomes a
Project, its existing Concerns would be associated with it without recreation. These relations
are still a design direction, not existing Atlas records or controls.

The idea or Project can author its own Concerns and Covenants. Its questions may lead to an adopted
decision, whose consequences suggest further Concerns. It may draw inspiration from LychD, another
document, or an existing Concern; none is a required template. A source-inspired proposal keeps
the passage and exact version used, why it applies, and the meaning proposed here. Review and
accept that interpretation; a later source revision should invite comparison rather than replace
what was written locally.

Acceptance case: start a Concern without a Project, give it three children, and reuse one child
under another Concern. Map two children to exact parts of a proposed application and leave the
third visibly unaddressed. Inspect the source of a suggested child, distinguish inspiration from
an adopted rule, and associate the questions with a Project later. Change a part used by an
assessment and verify that its original basis survives while the affected judgment needs review.

[Frontend](../../adr/15-frontend.md#independent-concerns-decomposition-and-addressing)
owns this contract. [State of Work](../../state-of-the-work.md#atlas-projects) records the current
Project-bound surface and the missing independent records, decomposition, addressing, and seeding.
