---
title: Delegation
---

# Delegation

To contribute an external planner or tool-loop runtime for an `AgentJob`, implement the delegated
runtime contract and register a `DelegatedRuntimeDefinition` through
`context.delegated_runtimes.add`. The
[reference registration](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/register.py)
and [adapter](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/builtin/delegation/reference.py)
show the receiving store and start, poll, and cancel operations. The reference runtime is
deterministic, process-local, and effect-free. Test job identity, terminal results and cancellation;
[delegation tests](https://github.com/hexanomicon/lychd/blob/main/tests/unit/extensions/test_delegation.py)
exercise those boundaries.

This route is distinct from an [Animator](animators/index.md), which addresses typed service
capabilities. [Delegated agents](../aspects/weaver/delegated-agents.md) owns the job envelope,
wait, return, and execution method. Foreign CLI execution and containment are not delivered by
the reference adapter; consult that page and [State of Work](../../state-of-the-work.md) before
claiming a runtime can perform effects.
