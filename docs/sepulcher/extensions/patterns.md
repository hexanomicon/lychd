---
title: Patterns
---

# Patterns

A Pattern names a workflow across revisions. Each immutable **Scroll** fixes one score.
Choose the contribution by what its reader should be able to do.

**To execute the score**, define the manifest and graph binding using Core's
[Workflow types](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py).
The binding checks the graph against the declared stations and edges. Include the exact
revision in the [Workflow registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py)
and decide separately which revision may receive new admissions. Follow the
[semantic chat Workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/semantic_chat.py)
and its [tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_semantic_chat.py).
[Spellweaver](../aspects/weaver/index.md) explains how a Run keeps its admitted score.

**To show the score**, an extension can add an
[`InspectionContribution`](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/weaver/inspection.py)
to the [inspections store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py).
Duplicate identities and conflicting descriptions of one exact revision are refused. A reader can
inspect an accepted score without being able to cast it. Evidence that a performance took place
comes from the executing owner. See [Oculus](../aspects/oculus.md).
