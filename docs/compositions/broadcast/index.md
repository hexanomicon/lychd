---
title: Broadcast
icon: material/broadcast
---

# :material-broadcast: Broadcast

A polished video can make a weak claim feel certain. Broadcast keeps the evidence behind each
claim and the exact words the editor approved. It prepares articles and finished media for
particular audiences and accounts for what each channel receives.

## The work

Begin with the sentence you want an audience to believe. [Sources](sources.md) binds its
claims to frozen spans. [Script](script.md) establishes the canonical words, preserving
uncertainty, attribution and disclosures as the story takes shape.

For a video, [Atelier](../atelier/master.md) makes and accepts the finished master.
[Distribution](distribution.md) admits those exact bytes, checks them against the editorial
brief and intended audience, and plans a package for each channel. If a destination needs a
vertical crop, different mix or shorter cut, the editor requests a successor master. Earlier
routes for [Edit](edit.md), [Picture-Bound Sound](sound.md) and [Render](render.md) lead to
their production owner.

The package can remain local. [Release](release.md) handles the separately authorized draft
upload or publication, correction and removal at a named destination.

## The local candidate

`broadcast.studio` revision `5` defines the principal Pattern
`broadcast.prepare_distribution@1`. A locally complete candidate binds exact content,
sources, claims and approved script, plus each channel's target, audience, copy, disclosures
and checks. A video candidate points to its settled `VideoMaster@1`. The candidate can be
approved, returned with findings or refused. Public availability requires its own destination
receipt. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery) records
which application Patterns can run.

## Revision continuity

??? info "Historical designs"

    Revision `4` selected `broadcast.build_local_package@3` and `broadcast.design_picture_sound@2`.
    It accepted the timeline, picture-bound sound and local render, returning `EditorialPackage@2`
    and `PublicationCandidate@2`. Its review and repair Patterns were `broadcast.review_package@2`
    and `broadcast.revise_from_correction@2`. Its effects were `broadcast.publish_draft@2`,
    `broadcast.publish_public@2`, `broadcast.correct_publication@2` and `broadcast.takedown@2`,
    returning `PublicationReceipt@1` for the exact destination. The producing authority for its generated picture sound was
    `broadcast.studio` revision `4`, declared before execution with a separate semantic receipt
    afterward. Revision `3` had introduced timed-language and picture-sound handoffs in
    `broadcast.build_local_package@2`. These records keep their exact historical meaning.
    Revision `5` prepares distribution around settled content. An older acceptance cannot serve
    as authority for an Atelier master or a new destination.

[Workflow](../../adr/28-workflow.md) · [Composition Portfolio](../index.md)
