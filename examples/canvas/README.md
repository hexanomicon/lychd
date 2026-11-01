# Canvas selection example

These synthetic files illustrate a manually transported model proposal. They do not describe
running LychD infrastructure or invoke a model, Comfy workflow, GPU, or executable Pattern.

1. Start the source client with `make frontend-dev` and open `/canvas/local`. The development preview
   is an offline board and needs no backend sign-in.
2. Choose **Example**. Select the two rough boxes and arrow, leaving **Illustrative context**
   outside the selection. The Objects list can select **Stroke 1**, **Stroke 2** and **Stroke 3**
   without a pointer gesture.
3. Enter the instruction from [selection-packet.json](selection-packet.json), then choose
   **Capture selection packet**. Inspect its object count and PNG dimensions. Downloading the
   packet performs no model call.
4. Choose **Import proposal** and select [codex-proposal.json](codex-proposal.json). The proposal
   is bound to the untouched example at revision 1 and those exact three stroke identities.
5. Review **Vessel**, **PostgreSQL** and the **database access** connection. Choose **Apply change**,
   edit a node label through Objects, and use Undo/Redo. The unrelated note remains unchanged;
   all three original strokes remain retained in the document.
6. Download the board and open that local file again. A changed board needs a fresh selection
   packet and a newly bound proposal; the example response cannot be silently retargeted.

Codex authored this response from an actual browser-captured PNG and original stroke packet
during the CPU-only campaign of 27 October 2026. The checked-in packet omits the embedded PNG to
keep the example inspectable; capture produces the image from the current scene. This is manual
model transport, not delivered live LychD inference. Tidy remains a separate local geometry helper.

The owning [Canvas contract](../../docs/compositions/canvas/index.md) explains portable documents,
proposal scope and the boundaries with Loom, Atlas, Orb and optional image engines.
