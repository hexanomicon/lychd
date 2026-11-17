---
title: Tools
---

# Tools

A Tool gives an Agent or Workflow a bounded operation. Start from the operation's owning service,
define its input and result, and implement the handler there. For Agent use, supply a named toolset
factory to [Agent
construction](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/factory.py) and name
it in the AgentSpec. The [factory
tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_factory.py) cover missing
toolsets and write gating. A Workflow can also call an owned operation without making it an Agent
tool.

Treat model-facing availability as a capability boundary, not proof of authority. A handler that
reads or changes protected state must recheck the actual caller and operation at the effect
boundary. A spec's `writes` flag controls which mutating toolsets are included; it does not confer a
grant. Use [Permissions](permissions.md) for application actions and [Privileges](privileges.md) for
host effects.

There is no general Tool store in the current [extension registration
context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py). Adding one
today means integrating and testing Core code. An accepted future seam does not make arbitrary
registered handlers executable or authorized. Emit execution evidence through the owner that
performs the operation; [Oculus](../aspects/oculus.md) describes the current observation boundary.
