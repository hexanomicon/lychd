---
title: Spells
---

# Spells

A Spell names an action by what it should accomplish. The implementation might call an Agent,
compute a result directly or cause an effect. Consider a Bridge request to answer a question
from Archive notes. What answer can the caller expect when recall finds nothing it can use?

In the [semantic chat Workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/semantic_chat.py),
`RecallSemanticNotes` keeps the recall receipt. `AnswerSemanticNotes` checks which notes can
still be used. With an empty selection it prepares an explanation without calling the chat
model. With selected notes it requests a local model grant and supplies the source material.
`SettleSemanticAnswer` checks the recall again before saving the reply. Follow the
[semantic chat tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_semantic_chat.py)
for the case where permission is withdrawn between recall and settlement. Even an empty result
cannot be saved as a reply once access has been revoked.

When adding an executable action, define its inputs, its result and when the caller must be
refused. Implement it in Core and bind the owning Workflow through the
[Workflow registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py).
The registry checks active revisions and route precedence. Extensions have no Spell registration
store today. If an action produces an effect, check [permission](permissions.md) or the relevant
[host privilege](privileges.md) where the effect is performed.

For an action with several steps, [Patterns](patterns.md) explains how to describe their order.
[Weaver](../aspects/weaver/index.md) executes the score. To find out which steps actually ran,
follow the executing owner's observations through [Oculus](../aspects/oculus.md).
