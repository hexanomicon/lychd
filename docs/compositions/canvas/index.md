---
title: Canvas
icon: material/draw
---

# Canvas

Draw an explanation while speaking to the people who need to understand it. Keep the rough
marks, select the part worth improving, and judge a proposed change before it replaces anything.
**Canvas** owns that visual board and its revision history. Its accepted Composition identity is
**`canvas.board`, revision `1`**.

The **project workspace** at `/canvas` starts with LychD's own Canvas and its curated static
architecture map. **Atlas** is the project catalogue. LychD remains separately pinned above the
loaded user collection, including after filters or pagination. The diagram describes selected
canonical relationships; it supplies no live status or proof that an illustrated capability runs.

**New Canvas** immediately creates a draft project and its blank primary board. Draw without
first naming or categorizing the idea. Keep it, rename it through its project record, or discard
an eligible draft. One primary board belongs to each project in this profile. Existing projects
retain their identities, judgments, decisions and references when a board is added.

Use the workspace save to retain the complete board and bounded undo/redo history on the server.
Read its result: an uncertain or conflicting save leaves the local document available to retry
or export. Project version checks protect against overwriting another view. Keeping and discarding
use that same versioned request contract. Discard hides a retained draft account; it cannot erase
planning records, a kept project, or the built-in LychD project. In-memory fixtures last only for
their process; the PostgreSQL profile supplies restart retention.

The **portable board profile** remains at `/canvas/local`. A browser draft can be
saved as a local document and opened again. A local download is independent of server save,
workflow publication, or evidence that the illustrated architecture is running. [State of Work](../../state-of-the-work.md#canvas-board-authoring)
owns the delivered evidence and its limits.

The Vite development preview opens `/canvas/local` in the Altar's offline workbench profile, so drawing
needs no sign-in and starts no protected status or Bridge request. The shell and dock controls
remain visible with the backend unavailable until explicitly connected. The compiled application
keeps the normal authenticated shell and API boundaries.

## Sketch, select, and judge

Begin with a blank board or the explicitly illustrative example. Draw actual freehand strokes,
add named nodes, and connect them. **Lasso** circles actual ink and selects whole intersecting
objects; the contour itself never becomes a source stroke. **Select** keeps rectangular selection,
and the Objects list supplies its keyboard alternative. Neither gesture cuts strokes. The
highlighted objects are the permitted edit scope.
Unselected objects supply context and keep their identities.

Capture the selection with an instruction. The portable packet contains the original selected
strokes and objects, the bounded scene, world bounds, exact scene revision, and a PNG crop of
that same paused revision when capture succeeds. Inspect the packet before taking it to a model.
Creating or downloading it performs no model transmission. Instruction and label text remain
data, never executable commands.

An imported model proposal names that packet's scene, revision and selected identities. Review
its new objects, labels, archived source strokes and positions before applying it. Existing
objects outside the selection cannot be changed. A changed scene makes the proposal stale;
capture a fresh packet. Acceptance applies the complete change once, preserves original ink,
and can be undone. A rejected or invalid proposal leaves the board intact.

The local **Tidy** helper regularizes geometry. It does not interpret an arbitrary spoken or
written request. A proposal authored by Codex and manually imported is attributed as manual
model transport; it does not establish a live LychD vision-provider integration.

## Keep the explanation steady

Nodes have editable text, optional symbolic artwork, stable identity and explicit connections.
Text is rendered separately from image pixels, including short overlays such as “DB”. Local PNG
artwork keeps its declared provenance; attaching it does not claim generated-media custody or
creative acceptance. World-fixed ink stays where drawn. This profile does not infer attachment
of handwriting to a nearby node.

An explicit arrangement settles movable nodes using their dimensions, existing positions,
connections and pinned obstacles. Drawing, selecting and dragging hold the scene steady.
Arrangement is one undoable change; simulation steps do not become revision history. Motion
respects reduced-motion preferences. The semantic object list offers selection and editing
without requiring a pointer or pan/zoom gesture.

## The board and its neighbors

| Canvas owns | Related owner |
| --- | --- |
| Board documents, source ink, visual objects, selection packets, proposal review and reversible edits | [Atlas](../../divination/altar/atlas.md) catalogues these projects; their retained records keep undertaking purpose, concerns and judgments. A board edit does not record a decision. |
| Visual workflow sketches and possible future exports | [Loom](../../divination/altar/loom.md) retains exact workflow meaning and admission. A drawn arrow is not an executable permission. |
| Illustrations of execution | [Orb](../../divination/altar/orb.md) projects recorded Run evidence. Diagram motion supplies no execution observation. |
| Placement of local symbolic artwork | [Atelier](../atelier/index.md) owns visual commissions and creative acceptance; [Prism Image](../../sepulcher/extensions/prism/image.md) owns designed technical image jobs. |
| Requests for optional generated assets | [ComfyUI](../../sepulcher/animator/soulstone/engines/comfyui.md) is a possible inference engine. Its graph does not become the board or a Loom Scroll. |

No relationship is inferred from proximity or a shared label. Future exact references may open
their owning instrument without transferring its records, permissions or execution authority.

## Save, stop, and return

Download the local document to retain the current scene and its bounded undo/redo snapshots
outside the browser; closing an unsaved draft can lose it. In the project workspace, confirm its
server save before leaving or retain an export. Save the current draft before opening
another document. Before an import replaces that draft, it validates format, byte and collection
bounds, finite geometry, unique identities, source-stroke references, image envelopes and edge
endpoints. Untrusted imports cannot contain remote images, SVG or executable code.

The portable size budget reserves the same fixed space for numeric values in the browser and
Python. This prevents differences in number formatting from changing acceptance, although the
conservative budget may be larger than the compact downloaded file.

Undo and redo preserve object identities and create fresh scene revisions so an old model response
cannot become current again accidentally. Board undo remains separate from durable project judgments.
The workspace retains immutable retry requests after uncertain writes and refuses stale aggregate
versions. A provider-backed profile still needs its own admission, custody and interrupted-effect
recovery before becoming supported.

The executable file and proposal contracts belong to
[`src/lychd/compositions/canvas/`](https://github.com/hexanomicon/lychd/tree/main/src/lychd/compositions/canvas).
The first profile does not register an executable Pattern or Invocation. Live microphone capture,
automatic model interpretation and image generation require separately proved integrations.

The [manual Codex example](https://github.com/hexanomicon/lychd/tree/main/examples/canvas)
provides a selection packet, a proposal bound to the untouched sample, and a reproducible
draw/select/review/save journey. It runs without a GPU or model service.

## Smallest falsifying journey

Draw two rough boxes and an arrow, select them beside an unrelated object, and capture the real
marks and crop. Import a proposal that makes editable nodes, preview it, apply it, rename and
move a node, then undo and redo. The unrelated object and original source ink survive. Change
the scene after capture and verify that the old proposal is refused. Save and reopen the local
document and repeat through the keyboard object list. Any lost geometry, silent out-of-scope
edit, partial acceptance or successful stale application defeats this profile.
