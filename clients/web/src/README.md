# Altar source map

Start from the instrument being changed. [ADR 15](../../../docs/adr/15-frontend.md) owns browser
architecture and [reading hierarchy](../../../docs/adr/15-frontend.md#reading-hierarchy-and-visual-direction);
[State of Work](../../../docs/state-of-the-work.md#altar-and-observability) owns delivery. This map
routes to the implementation and its operating guide rather than duplicating either contract.

| Reading or interaction | Source entry | Interpretation |
| --- | --- | --- |
| Project concerns, judgments, references, and continuation | [AtlasView.svelte](lib/components/AtlasView.svelte), [Atlas link hints](lib/atlas/navigation.ts) | [Atlas](../../../docs/divination/altar/atlas.md) |
| Conversation, consent, and offering recovery | [BridgeView.svelte](lib/components/BridgeView.svelte), [shell-lifetime workspace](lib/bridge/workspace.svelte.ts) | [Bridge](../../../docs/divination/altar/bridge.md) |
| One Run's retained records and gaps | [OrbView.svelte](lib/components/OrbView.svelte) | [Orb](../../../docs/divination/altar/orb.md) |
| Observed capability, preview, ticket, and physical request | [NexusView.svelte](lib/components/NexusView.svelte) | [Nexus](../../../docs/divination/altar/nexus.md) |
| Exact registered score and optional static diagram | [LoomView.svelte](lib/components/LoomView.svelte), [MermaidGraph.svelte](lib/components/MermaidGraph.svelte) | [Loom](../../../docs/divination/altar/loom.md) |

[The layout](routes/+layout.svelte) supplies browser-document context;
[AltarShell](lib/components/AltarShell.svelte) projects navigation and global attention.
[Instrument links](lib/navigation/instruments.ts) carry bounded selection hints. Destination
loaders still validate identity and relationships; a URL does not prove ownership or Run/Pattern
equivalence. Focused component tests live beside their components; navigation has its own
[identity tests](lib/navigation/instruments.test.ts).

[API contracts](lib/api/models.ts) alias [generated transport types](lib/api/openapi.d.ts).
Their Python owners are [Altar controllers](../../../src/lychd/interface/web/) and
[web-domain contracts](../../../src/lychd/domain/web/). Regeneration, checks, and builds follow
[CONTRIBUTING](../../../CONTRIBUTING.md#quality-checks); do not hand-edit generated descriptions.

The planned reading sections in the five guides are future presentation work. No shared
Loom/Orb graph supply or canvas is present here yet; [the renderer
gate](../../../docs/adr/15-frontend.md#decision-lock-and-reopening-gate) owns that later seam.
The client still uses its fixed English interface and LychD Dark palette. Native CSS lives in
[app.css](app.css); the existing welcome scene's [notice](lib/assets/altar/NOTICE.txt) and
[generation prompt](lib/assets/altar/working-altar.prompt.md) retain asset provenance.
