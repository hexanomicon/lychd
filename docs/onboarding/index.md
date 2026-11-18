---
title: Developer onboarding
---

# Developer onboarding

LychD is a local-first system for putting models and tools to work on a machine you control.
To see why that control matters, imagine editing a video. You hear the speaker say “might.”
The caption says “will.” The render looks finished. Would you publish it?

## Follow the disputed word

Start with **who gets to decide**. In [Broadcast](../compositions/broadcast/index.md#the-work),
the application for editorial work, an editor can follow a claim back to the speaker's words
and return the cut for correction. Even an approved cut can stay on disk. Sending it to an
audience is a [separate decision](../compositions/broadcast/release.md). When the Prophecy
calls the person at the machine the *Magus*, that power to correct or refuse is part of what
it means. [Transcendence](../divination/transcendence/index.md) asks what the Lich could learn
from that correction while the editor keeps the power to refuse its next answer.

Now ask **how the work reaches the editor**. Sketch the route from the source recording to the
cut. Where would you look for the instructions the machine followed? Where would you look for
what actually happened on this attempt? Compare your sketch with the
[request in the Overview](../map.md#one-body-in-one-breath). A **Scroll** fixes one revision
of the instructions. A **Run** identifies one attempt to carry them out. Two attempts can
follow the same Scroll and have different outcomes.

Finally, **could you try it today?** Broadcast describes an accepted application design.
The [Portfolio record in State of Work](../state-of-the-work.md#composition-portfolio-delivery)
identifies which workflows have executable paths and under what conditions. For something
you can inspect now, [trace one failed Run](explore/one-run.md). You can do the exercise
from the source or open the developer preview alongside it.

## Where would you make a change?

Try turning a bug report into a testable question. A teammate says, “I saved a quotation in
Memory. When I came back, it was gone.” [Work through the report](explore/a-missing-quotation.md)
before deciding which part of the system to change.

| Your next question | Where to look |
| --- | --- |
| Which part receives the request, does the work, or keeps the result? | Find the organ in the [Sepulcher](../sepulcher/index.md#the-anatomy). |
| When does an action need my approval? | Follow the consent question in the [Covenants](../adr/index.md#agency-memory-and-consequence) to the decision a change must preserve. |
| If the process dies, which parts of my work survive? | Follow the earlier conversation and its Run through [Reanimation](../sepulcher/phylactery/reanimation.md). |
| Where should a new application or tool live? | For an application, start with [Choosing a Home](../compositions/choosing-a-home.md). For an operation an agent should be able to call, start with [Tools](../sepulcher/extensions/tools.md). |
| I know what I want to change. Which files and tests do I start with? | Pick your area in the [contribution guide](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#find-the-part-you-want-to-change). |
| How do I get a checkout ready and claim my first task? | Follow [setup and commands](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#setup-and-commands), then [coordinate with the team](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#coordinate-before-starting-work). |
