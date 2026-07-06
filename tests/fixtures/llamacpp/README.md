# llama.cpp `/models` capture fixture

`models_response.json` is the router-mode `GET /v1/models` response the A2 parser
(`facts_from_markers` + `_populate_router_models`) is exercised against.

## STATUS: UNVERIFIED-PENDING-LINUX

This Mac dev box cannot run the pinned `ghcr.io/ggml-org/llama.cpp` server image
under Docker/podman (no container runtime available here). The fixture was built
from the llama.cpp server's documented OpenAI-compatible `/models` response shape
(router mode: `object=list`, per-entry `id`/`status.value` plus a tolerant
`capabilities` marker list). It carries a plain GGUF chat model, an mmproj
multimodal model (`qwen3-vl-8b`), and an embedding model (`bge-m3`).

Because the A2 parser is tolerance-first (design risk 1), the wave does not hinge
on this capture. It must still be re-captured on Linux:

- Run the pinned image in router mode with a plain GGUF + an mmproj multimodal
  model + an embedding model.
- `curl http://localhost:PORT/v1/models` and replace this file with the raw JSON.
- Record the image digest below and drop the `UNVERIFIED-PENDING-LINUX` marker.
- Adjust the A2 marker table only if the real markers differ (they must not be
  edited without this re-capture evidence).

Image digest (fill on Linux capture): `ghcr.io/ggml-org/llama.cpp@sha256:<pending>`
