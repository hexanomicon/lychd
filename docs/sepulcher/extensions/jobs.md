---
title: Jobs
---

# Jobs

A durable job needs an owned queue contract and a worker that can execute and recover it. Begin with
the existing [queue
services](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/services/queues.py), the
[Scout worker](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/scout_worker.py), and
their focused [queue
tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/services/test_queues.py) and
[worker
tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/system/test_scout_worker.py).
Define the payload, admission, completion and failure behavior in the owning service, then integrate
the worker into the host lifecycle. The [Workers Covenant](../../adr/14-workers.md) owns the durable
execution requirements.

This is currently Core integration. The [extension registration
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py) has no
generic job store; a `register` function is not a place to launch arbitrary background tasks. A
future extension seam does not establish queue admission or worker authority by itself.

Check authorization when a job is admitted and at any protected effect that requires current
authority. The worker and queue owners must provide evidence of actual execution and outcomes; a job
declaration does not prove activity. See [Oculus](../aspects/oculus.md) for the current observation
contracts and [Privileges](privileges.md) if the job invokes host effects.
