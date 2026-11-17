---
title: Spells
---

# Spells

A Spell names a semantic action: what is being done and its intended result. Its implementation may
be an Agent, a deterministic operation, or an effect. Choose that implementation from the action's
needs rather than assuming every Spell is a model call.

Today, adding an executable action means changing Core. Start with an existing
[Workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/semantic_chat.py),
define the inputs, output and refusal at the owning boundary, and bind its implementation through
the source-defined [Workflow
registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py).
Exercise the actual behavior and failure paths, as in the [semantic chat
tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_semantic_chat.py). The
registry validates its active revisions and routing; an unbound description does not make an action
executable.

For a composed action, [Patterns](patterns.md) describe the score and
[Weaver](../aspects/weaver/index.md) owns its execution. Runtime evidence comes from the executing
owner; a declared graph alone proves no activity. [Oculus](../aspects/oculus.md) describes the
current inspection and observation boundaries. An extension registration store for Spells is not
currently shipped. The accepted extension seam does not itself grant permission to perform an
effect; check the relevant [permission](permissions.md) or [privilege](privileges.md) at the effect
boundary.
