---
title: Jobs
---

# Jobs

A queued Run can arrive at its worker twice. The first challenge in adding durable work is
to decide which delivery owns the right to execute it, and what remains recoverable if the
worker dies. In Core, [Ghouls](../vessel/ghouls.md) shows how one Run moves from admission to
claim, settlement, and restart.

Follow [`perform_run`](https://github.com/hexanomicon/lychd/blob/main/src/lychd/ghouls/runs.py)
and the [worker tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/domain/cortex/test_perform_run.py).
Look for `test_concurrent_redelivery_executes_graph_exactly_once` and
`test_stale_delivery_sequence_is_skipped_before_claim`. The worker claims the admitted Run
and its exact delivery sequence before executing the graph. For broker connection, enqueue,
and abort behavior, follow the [queue services](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/queues.py)
and their [tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_queues.py).

Define the payload, admission, failure, recovery, and terminal evidence with the owner of the
new work. Integrate worker startup and shutdown with the host lifecycle. Check current authority
again at protected effects, including any [host operation](privileges.md).
[Workers](../../adr/14-workers.md) owns those obligations. The current
[extension context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
offers no generic job store.
