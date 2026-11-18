---
title: Investigate a missing quotation
---

# Investigate a missing quotation

“I saved a quotation in Memory yesterday. Today it's gone.” What would you ask the person
who reported this before opening the database code?

## Reconstruct what they did

Open the [Memory panel guide](../../divination/altar/memory.md#choose-what-you-are-working-with).
Which of its controls might the reporter mean by *saved*? Suppose they selected a turn in a
conversation, marked it **Open question**, wrote a note, and closed the tab. Where did the note
live? Which parts could they find again by reopening the original conversation?

The conversation can retain the words they selected. The selection and their annotation lived
in the open browser document. To take those away, they needed to copy or export them. Suppose
instead they submitted a **public note**. Now you'd want the intake result and the identity of
the record. The [public-note procedure](../../divination/altar/bridge.md#manage-public-notes)
explains how to check an uncertain submission.

## Find a change you can test

The reporter follows up. “I did export it. The words are there, but the link to the Run is
missing.” Read the first [quotation export test](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/seances/material.test.ts).
Look at the input as well as the assertions. Does the example turn carry a Run ID? What path
does the next test expect when that ID is absent?

Compare the source turn’s Run ID with the `Source:` line in the export. In the first test,
the quotation comes from the **user**. On the Altar where the real conversation took place,
a link with a usable Run ID asks Bridge to focus the **reply** for that Run. To identify
the quoted turn itself, compare the role, timestamp and words in the export. Without a usable
Run ID, the link opens the source séance. If a valid ID still gives only a séance path,
reproduce it in the export test, then follow the link construction in
[`sourceHref`](https://github.com/hexanomicon/lychd/blob/main/clients/web/src/lib/seances/material.ts).

“Keep every quotation after I close the tab” would raise a different design question.
Who could read it later, and who could erase it? [Archive law](../../adr/27-memory.md#namespaces-and-authority)
spells out what storing material for later use would commit the project to. The [Archive
delivery record](../../state-of-the-work.md#karma-semantic-memory) identifies which kinds of
material the current system can admit.
