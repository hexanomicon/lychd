---
title: Atlas
icon: material/map-outline
---

# :material-map-outline: Atlas

Atlas is the map you return to when the work outlives one conversation. A project keeps what you
are trying to make or care for, the concerns that deserve attention, the judgments already made,
and a proposed next step. A software release, a record, and the continuing care of a home all fit.
You can begin before there is a conversation, a Pattern, or a Run.

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

An unassessed concern has no recorded judgment. When you assess it, record **Sufficient**,
**Insufficient**, or **Disputed**, and explain why. You may cite linked activity as part of the
reason. Atlas retains the brief and concern text that you judged, your local Sigil attribution,
and the time of the assessment. These are recorded judgments; a successful Run does not award
sufficiency, and a linked Run is not proof that every criterion was tested.

Changing the brief or a concern makes earlier assessments **need review**. The earlier judgment
and its original requirements remain readable. Record a fresh assessment after examining the new
basis. Atlas does not silently reinterpret what an older assessment meant.

Use **Find a concern** and the **Assessment** filter to reach a question or judgment in a longer
project. Assessment forms open beside the concern and its history. Cited activity opens in a new
tab so you can inspect it while keeping your draft. The board's filters apply to its loaded page;
unassessed concerns, assessments needing review, and current insufficient or disputed judgments
have separate counts and filters. Stale judgments count as needing review rather than as current
judgments. These are separate observations, not a complete measure of project health.

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

An assessment cites an Atlas reference record by its own identity. Merely linking the same
activity to a concern does not make it cited evidence. The useful reading chain is concern →
assessment → cited reference → conversation or Run. A relation view must distinguish uncited
references and retain each reference's scope and note when several lead to one target.

Linking does not feed the whole project into a model, change the selected conversation's Context,
or authorize another act. Use Bridge's ordinary admission and consent when you decide to carry
out a proposed next step. Loom continues to own the reusable score; Nexus continues to show
readiness and physical transitions.

## Return after a failed save

Atlas saves through the Vessel. In the PostgreSQL profile, projects survive browser and Vessel
restarts. The test-only memory profile retains them only for its process lifetime.

If a save's outcome is uncertain, retry the same pending change. Its identity prevents duplicate
concerns, assessments, decisions, and references. If another view has changed the project, Atlas
refuses to overwrite it. Load the latest saved version and compare the differing fields beside
your draft. **Use saved…** adopts a saved value for that field; **Use reviewed values** enables a
new explicit save using the values now in the form. Check fields another editor changed even
when you did not edit them. A failed read is shown as a failure, rather than an empty map.

The initial surface retains records when a project closes; it has no delete action. Existing
installations need the normal database migration before opening Atlas. Migration `0009` refuses
to remove its schema while projects remain.

[Frontend](../../adr/15-frontend.md#atlas-and-continuity-across-invocations) owns the design,
[Persistence](../../adr/06-persistence.md#atlas-records) owns retention, and
[State of Work](../../state-of-the-work.md#atlas-projects) records the implementation evidence
and remaining boundary.

## Reading direction

The planned composition puts the brief and proposed next step before a concern index and one
readable concern detail. Criteria, judgment, original basis, attribution, and cited references
belong together; older assessments and decisions can unfold beneath them. Keep unassessed,
stale, insufficient, and disputed counts distinct. A compact portfolio row helps compare
undertakings without turning planning lifecycle into a health score.

Start relations as an exact list for the selected concern. A small diagram is useful only if it
makes that same citation chain easier to follow, without merging reference identities or drawing
an ambiguous arrow between groups. Neither similarity tags nor visual clustering create Project
membership or automatic coverage.

Acceptance case: return to a project with fifty concerns, find an assessment whose criteria
changed, inspect its cited Run, and reconcile a conflicting edit while retaining the draft and
judged basis. A shared conversation appears once as a continuation destination while its concern
relations remain distinct. Larger collection limits and catalogue-wide search need an explicit
server contract; hiding rows cannot create that support. This composition and its scale checks
are targets under [Frontend](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction), not
additional delivered controls.
