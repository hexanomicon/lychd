# llama.cpp `/models` capture fixture

`models_response.json` is an illustrative router-mode `GET /models` payload awaiting capture
from a real engine. It contains chat, multimodal, and embedding examples; its capability markers
are not a verified engine contract.

## STATUS: UNVERIFIED-PENDING-LINUX

No image digest or live capture is recorded below. The current
[control-plane parser](../../../src/lychd/extensions/builtin/animator/llamacpp/control_plane.py)
reads model ids and `status.value` to distinguish available and loaded models. It does not derive
capabilities from this fixture's marker list. The
[control-plane tests](../../unit/domain/animation/test_llamacpp_control.py) construct their own
payloads inline; they do not load this JSON file.

To replace the illustration with an attributed capture:

- Run an exact image in router mode with a plain GGUF, an mmproj multimodal model, and an
  embedding model. Record the resolved image digest and model/configuration identities.
- Read the local engine's `GET /models` endpoint at its actual port and save the raw response
  in `models_response.json`.
- Compare its ids, status fields, and any capability markers with the parser and focused tests.
  Record disagreements as findings; do not invent markers to make the capture fit the example.
- Record the capture date and host alongside the digest, then remove `UNVERIFIED-PENDING-LINUX`
  only after that evidence exists.

Image digest (fill on Linux capture): `ghcr.io/ggml-org/llama.cpp@sha256:<pending>`
