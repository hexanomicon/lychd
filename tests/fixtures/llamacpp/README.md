# llama.cpp `/models` capture fixture

`models_response.json` is the router-mode `GET /v1/models` response used to
exercise the A2 parser (`facts_from_markers` + `_populate_router_models`).

## STATUS: UNVERIFIED-PENDING-LINUX

This Mac development box has no container runtime and cannot run the pinned
`ghcr.io/ggml-org/llama.cpp` server image through Docker/Podman. The fixture
uses the documented OpenAI-compatible router `/models` shape: `object=list`,
per-entry `id`/`status.value`, and a tolerant `capabilities` marker list. It
carries a plain GGUF chat model, an mmproj multimodal model (`qwen3-vl-8b`), and
an embedding model (`bge-m3`).

The tolerance-first A2 parser (design risk 1) does not depend on this capture,
but Linux must re-capture it:

- Run the pinned image in router mode with a plain GGUF, an mmproj multimodal
  model, and an embedding model.
- `curl http://localhost:PORT/v1/models` and replace this file with the raw JSON.
- Record the image digest below and drop the `UNVERIFIED-PENDING-LINUX` marker.
- Change the A2 marker table only if real markers differ; do not edit it before
  this re-capture evidence.

Image digest (fill on Linux capture): `ghcr.io/ggml-org/llama.cpp@sha256:<pending>`
