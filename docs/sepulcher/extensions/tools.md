---
title: Tools
---

# Tools

A Tool gives an Agent or Workflow a bounded operation. Define the inputs and result in the
service that owns the operation, then implement the handler there. A Workflow can call that
service directly. To offer the operation to a model, decide which Agents should see it.

## Offer a toolset to an Agent

Suppose an editor Agent can save a correction and a reader Agent can only inspect it. Give
the writing tools a named factory such as `writer`. In the call to
[`build_agent`](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py),
pass that factory in `toolset_factories` and include `"writer"` in `mutating`. The builder
relies on that explicit classification. The AgentSpec names the toolsets it requests.

The [factory test](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_factory.py)
requests `writer` in two otherwise identical specs. Find
`test_agent_construction_omits_mutating_toolset_without_write_authority`: the read-only Agent
receives no writer, and the Agent with `writes=True` receives it. The test also shows where
to supply the classification. A requested toolset with no registered factory fails construction.

## Check the correction when it is saved

Even when the editor can see the tool, the handler must check whether this caller may change
this record. Apply the same check when reading protected state. Use
[Permissions](permissions.md) for application actions and [Privileges](privileges.md) for host
effects.

There is no general Tool store in the current [extension registration
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py). Adding one
today means integrating and testing Core code. An accepted future seam does not make arbitrary
registered handlers executable or authorized. Emit execution evidence through the owner that
performs the operation; [Oculus](../aspects/oculus.md) describes the current observation boundary.
