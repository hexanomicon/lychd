---
title: Trace one failed Run
---

# Trace one failed Run

The text of a sample reply in the developer preview says the Run failed. A teammate opens
the workflow diagram, points to a model step and says, “That's where it failed.” What
evidence would convince you that the model was called at all?

## Follow one identity

To see the example in the browser, open the default read-only preview using the
[fixture setup and sign-in instructions](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#browser-development-and-its-backend).
You can also follow the same records in the
[fixture test](https://github.com/hexanomicon/lychd/blob/main/tests/web/test_developer_fixture.py).
Find `test_fixture_bridge_orb_and_loom_share_one_registered_revision` and read from the first
Bridge request.

1. In **Bridge**, expand the **Circle** beside the synthetic reply labelled **Retained reply**.
   It gives you the Run ID for this turn. The Run status reads **Not retained in this reply**.
2. Open the reply’s **…** menu and choose **View run in Orb**. Match the Run ID, read the status and look at the evidence
   attached to it. In the test, find the assertions on `status` and `summary`. What does
   the sample itself tell you was executed?
3. Follow **Exact Pattern** into **Loom**. Match the workflow name and revision to the ones
   recorded for the Run. The diagram tells you which steps this revision permits. Which
   record would you need to say that a particular step took place?

## Account for the failure

Open [the code that prepares the sample](https://github.com/hexanomicon/lychd/blob/main/src/lychd/developer.py)
and find `_seed`. It creates a Run, writes `RunStatus.FAILED` to the ledger and attaches
that Run ID to the conversation. The fixture supplied the status itself. No model ran.

Try the same reasoning on a harder case. Suppose a real Run is marked failed, its Scroll
contains a model step, and the event for that step is missing. You know how the Run ended.
Whether it reached the model is still an open question. The
[Orb guide](../../divination/altar/orb.md#establish-the-account-you-are-reading) explains how
to tell what the system captured, what the current view loaded and where the record has a gap.
