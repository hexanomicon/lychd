---
title: Patterns
---

# Patterns

A Pattern is a score lineage; a Scroll is an immutable revision of that score. To add an executable
revision today, work in Core: define its manifest and graph binding using [Workflow and Pattern
types](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/base.py), then
include the Workflow in the source-defined
[registry](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/__init__.py).
The binding validates the graph against its declared stations and edges. Study an existing [semantic
chat
Workflow](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/semantic_chat.py)
and its [tests](https://github.com/hexanomicon/lychd/blob/main/tests/agents/test_semantic_chat.py)
before changing the score. [Weaver](../aspects/weaver/index.md) owns authoring and execution
details.

Extensions can contribute an `InspectionContribution` through the inspections store for a bounded,
exact score description. [Its
contract](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/weaver/inspection.py) and
[store](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py) distinguish
that catalogue from execution: it does not register a Workflow or permit a cast. Duplicate
identities and conflicting exact revisions are refused. [Oculus](../aspects/oculus.md) explains what
inspection exposes; execution owners produce runtime events, rather than activity being inferred
from the score. The current executable registry is fixed and source-defined, even when an extension
supplies an inspection.
