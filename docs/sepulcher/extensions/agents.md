---
title: Agents
---

# Agents

A Workflow calls an Agent when a step needs model judgment and the caller can say what kind of
result it will accept. The Bridge Agent, [The First One](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/the_first_one.py),
is small enough to follow from its declaration into a running turn.

Start with `THE_FIRST_ONE_SPEC`. It declares the identity instructions and two possible
results, a `BridgeReply` or a deferred tool request. Its builder attaches `stable_floor`,
which reads the Context assembled for the current Run. The Workflow supplies the model when
the turn runs. If the model needs another capability, first decide which part of the system
can authorize that operation. The Bridge Agent deliberately has no tool for replacing the
model it is using. A replacement could wait for the very lease the turn is holding.

To add an Agent in Core, declare an [`AgentSpec` and its builder](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py),
register the builder with the Forge and have the owning Workflow request that spec.
The Forge looks up the builder by name and caches the
constructed Agent by its complete spec. One [factory test](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_factory.py)
makes the distinction visible by changing only `max_tokens` and getting another Agent.
An unregistered builder name or a toolset name with no factory raises an error.

If you declare a mutating toolset, the builder includes it only for a spec with `writes=True`.
The handler still checks who is calling and whether they may perform this operation on this
resource. Follow [Tools](tools.md) for the operation and [Permissions](permissions.md) for the check.

The [Agent Covenant](../../adr/20-agents.md) owns this design. Agents are assembled in Core.
The current [extension registration stores](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)
have no Agent store. To find out whether a particular Agent ran, start with its Workflow and
the evidence available through [Oculus](../aspects/oculus.md).
