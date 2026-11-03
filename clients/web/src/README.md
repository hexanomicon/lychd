# Altar source map

Start from the instrument being changed. [ADR 15](../../../docs/adr/15-frontend.md) owns browser
architecture and [reading hierarchy](../../../docs/adr/15-frontend.md#reading-hierarchy-and-visual-direction);
[State of Work](../../../docs/state-of-the-work.md#altar-and-observability) owns delivery. This map
routes to the implementation and its operating guide rather than duplicating either contract.

| Reading or interaction | Source entry | Interpretation |
| --- | --- | --- |
| Canvas Project catalogue, retained concerns, judgments, references, and continuation | [AtlasView.svelte](lib/components/AtlasView.svelte), [Atlas link hints](lib/atlas/navigation.ts) | [Atlas](../../../docs/divination/altar/atlas.md) |
| Project board retention/recovery, portable authorship and reviewed selection transformations | [CanvasWorkspace.svelte](lib/components/CanvasWorkspace.svelte), [CanvasView.svelte](lib/components/CanvasView.svelte), [Canvas engine](lib/canvas/engine.ts) | [Canvas](../../../docs/compositions/canvas/index.md) |
| Conversation, consent, and offering recovery | [BridgeView.svelte](lib/components/BridgeView.svelte), [shell-lifetime workspace](lib/bridge/workspace.svelte.ts) | [Bridge](../../../docs/divination/altar/bridge.md) |
| Finite dictation, transcript review and private correction/vocabulary controls | [BridgeVoiceInput.svelte](lib/components/BridgeVoiceInput.svelte), [capture](lib/bridge/voice/capture.ts), [draft coordinator](lib/bridge/voice/dictation.ts), [DictationFeedback.svelte](lib/components/DictationFeedback.svelte) | [Bridge dictation](../../../docs/divination/altar/bridge.md#dictate-and-review) |
| Exact instrument work destination and inert Canvas command proposals | [work-command registry](lib/bridge/work-commands.ts), [Canvas command planner](lib/canvas/commands.ts) | [Canvas commands](../../../docs/compositions/canvas/index.md#give-a-bounded-command-through-bridge) |
| Public-note intake, lifecycle review and metadata recovery within Bridge | [PublicNotes.svelte](lib/components/PublicNotes.svelte), [recovery controller](lib/archive/notes.ts) | [Public notes](../../../docs/divination/altar/bridge.md#manage-public-notes) |
| Spatial Run field, tab observation history, and one Run's retained records and gaps | [OrbField.svelte](lib/components/OrbField.svelte), [OrbTimeline.svelte](lib/components/OrbTimeline.svelte), [OrbView.svelte](lib/components/OrbView.svelte) | [Orb](../../../docs/divination/altar/orb.md) |
| Admitted runtime topology, actual call attempts, source coverage and inspection-only scores | [Runtime evidence](lib/components/RuntimeEvidence.svelte), [runtime reader](lib/orb/runtime.ts), [generic projection](lib/graph/runtime.ts) | [Connected components](../../../docs/sepulcher/extensions/oculus.md#connected-components-and-activity) |
| Exact-Run matching Archive selection and capture limits | [ArchiveRecallPanel.svelte](lib/components/ArchiveRecallPanel.svelte) | [Archive selection](../../../docs/divination/altar/orb.md#inspect-a-matching-archive-selection) |
| Capability ownership map/list, selected properties, preview, ticket, and physical request | [NexusView.svelte](lib/components/NexusView.svelte), [native map](lib/components/NexusMap.svelte), [projection](lib/nexus/map.ts), [properties](lib/components/NexusProperties.svelte) | [Nexus](../../../docs/divination/altar/nexus.md) |
| Exact registered score and computed graph | [LoomView.svelte](lib/components/LoomView.svelte), [shared canvas](lib/components/graph/GraphCanvas.svelte) | [Loom](../../../docs/divination/altar/loom.md) |

[The layout](routes/+layout.svelte) supplies browser-document context;
[AltarShell](lib/components/AltarShell.svelte) projects navigation, global attention and the
shell-lifetime [Bridge dock and full-focus page](lib/components/BridgeDock.svelte). Its layout
preferences contain only bounded width, side and open state; conversation and recovery remain in
their existing owners.
[Browser-local pins](lib/bridge/pins.ts) retain bounded session identities only.
[Instrument links](lib/navigation/instruments.ts) carry bounded selection hints. Destination
loaders still validate identity and relationships; a URL does not prove ownership or Run/Pattern
equivalence. Focused component tests live beside their components; navigation has its own
[identity tests](lib/navigation/instruments.test.ts).

[API contracts](lib/api/models.ts) alias [generated transport types](lib/api/openapi.d.ts).
Their Python owners are [Altar controllers](../../../src/lychd/interface/web/) and
[web-domain contracts](../../../src/lychd/domain/web/). Regeneration, checks, and builds follow
[CONTRIBUTING](../../../CONTRIBUTING.md#quality-checks); do not hand-edit generated descriptions.

Loom and Orb share [graph projections](lib/graph/) and one [canvas adapter](lib/components/graph/GraphCanvas.svelte),
with semantic views over the same identities. [The renderer
gate](../../../docs/adr/15-frontend.md#decision-lock-and-reopening-gate) owns qualification;
[State](../../../docs/state-of-the-work.md#orb-instrument) records its remaining limits.
The client still uses its fixed English interface and LychD Dark palette. Native CSS lives in
[app.css](app.css); the existing welcome scene's [notice](lib/assets/altar/NOTICE.txt) and
[generation prompt](lib/assets/altar/working-altar.prompt.md) retain asset provenance.
