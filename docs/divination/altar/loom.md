---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom

The Loom is the Altar surface for the **[Weaver](../../sepulcher/extensions/weaver.md)**.

The Weaver does not weave rites. It weaves workflow **Patterns**: graph-shaped ways of moving intent through agents, workers, memory, evaluation, and approval gates.

The Loom shows:

- available workflow Patterns
- their graph shape
- required capabilities
- expected inputs and outputs
- pause points and approval gates
- Mermaid or Pydantic AI graph renderings when available

A Pattern becomes an Invocation only when the Magus offers it at the Altar.

## Surface Shape

The Loom is the design-time workflow surface. Its first form may be a Pattern browser with rendered Mermaid or Pydantic AI graph diagrams, input/output contracts, required capabilities, and expected approval gates.

As Weaver matures, the Loom is the natural home for a richer graph island. Svelte Flow may be used here for node/edge creation, selection, layout, and editing, in the spirit of workflow tools such as n8n. Even then, the browser edits only draft Pattern structure. The Vessel and Weaver remain responsible for validation, persistence, capability resolution, and the moment a Pattern becomes an Invocation.
