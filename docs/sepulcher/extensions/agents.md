---
title: Agents
---

# Agents

An Agent performs typed cognition within an explicitly assembled capability. For a current Core
contribution, define an
[AgentSpec](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py) with
instructions, output types and the toolsets it needs, then arrange its builder and use through the
owning Workflow. [The First
One](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/the_first_one.py) is a concrete
specimen; its [factory
tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_factory.py) cover
construction and refusal.

The Forge caches by the complete specification and requires a registered builder for its name.
Construction refuses unknown toolset names. A mutating toolset is included only when the spec
permits writes, but this construction choice is not an authority grant: handlers must check the
actual caller and operation. See [Tools](tools.md) and [Permissions](permissions.md).

This is Core integration, not an Agent registration store exposed to extensions. The [Agent
Covenant](../../adr/20-agents.md) defines the architectural boundary; the current registration
context exposes the separate stores shown in
[source](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py). For
execution evidence, follow the owning Workflow and [Oculus](../aspects/oculus.md), not an Agent
description alone.
