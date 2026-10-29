---
title: vLLM
icon: material/rocket-launch
---

# :material-rocket-launch: vLLM

**vLLM** is a resident model-serving engine behind an OpenAI-compatible connector. The Soulstone
adapter binds one declared model service to a Rune, derives its model capability, probes the live
inventory, and exposes it only when the exact declared model is ready.

A server pinned to one model produces `is_dynamic=False` capabilities. Reachability establishes
link liveness; a capability becomes `WARM` only when the validated live `/models` inventory also
contains its exact declared model id. Malformed inventory or a missing id becomes `ERROR`.
Focused tests cover current planning and connector behavior.

vLLM framework arguments come from the operator-owned `exec` list, which the adapter passes
through verbatim. Image, devices, mounts, ports, and environment remain typed Soulstone and
Quadlet fields. Keep the command's served model id and endpoint consistent with the Rune;
these declarations do not synthesize vLLM flags.

The `exec` arguments follow the selected image's entrypoint. The generated example expects
`["vllm", "serve"]` and begins with the model path; adding another `serve` would repeat the
subcommand. Inspect and pin the actual image entrypoint before adapting a recipe. A different
entrypoint needs its matching argument vector; the adapter does not rewrite it. The example's
environment uses an ordinary TOML table and remains inactive until deliberately edited.

## Bring one service to a first reply

For an already running local service, the standalone acceptance probe exercises explicit built-in
registration, exact Dispatcher grants, AgentForge text output, and one harmless in-memory tool
round. It reads no installation Settings or Runes and cannot start, stop, or load a runtime:

```bash
timeout --signal=TERM --kill-after=5s 40s \
  uv run --locked --no-sync python -m scripts.local_model_probe \
  --base-url http://127.0.0.1:20000/v1 \
  --model-id YOUR-SERVED-MODEL-ID \
  --source-revision "$(git rev-parse HEAD)"
```

Point the probe at the endpoint and exact served model you want to test. Only literal loopback
HTTP with an explicit port is admitted. It sends synthetic inputs and runs the two cases
sequentially with finite request/output limits and a cooperative deadline. One JSON result goes
to stdout; diagnostics go to stderr.

A passing tool round must return a fresh marker from the actual tool call and leave no live
capability lease. Before the Agent processes a response, that response must identify the declared
model and carry an explicit wire finish reason of `stop` or `tool_call`. The SDK's default for an
absent wire reason cannot supply this evidence. Filtered, truncated, errored, or unknown endings
fail even if the marker appears. Failure retains any response metadata already observed.

A failed or cancelled call leaves the externally operated server's outcome unresolved. Shielded
client cleanup may outlast the cooperative deadline, so the outer process timeout bounds the
command. If forced termination prevents a final JSON receipt, cleanup and server outcome remain
unknown and the probe cannot pass.

Retain the JSON outside the checkout with the independently observed image/model/host identities.
The supplied source revision is a declaration, not a clean-checkout or artifact attestation.
This probe qualifies neither an installed Vessel nor Bridge, streaming, persistence, managed
activation, runtime-contributed tools, capacity, shutdown, or recovery.

Choose the boundary being tested before adapting an existing serving recipe:

| Boundary | What the observation must establish |
| --- | --- |
| Connector and Agent | The exact declared model appears at the configured `{base_url}/models` endpoint (`/v1/models` for the standard base URL); a real request passes through Dispatcher and its grant is released after success, failure, and cancellation. |
| Managed activation | The owned runtime starts through Orchestrator, reaches exact-model readiness, and shuts down or reports a contained failure. |
| Composed first light | Bridge receives the reply, the settled Run and conversation remain inspectable after restart, and the operator can stop the same installation. Interrupted-work recovery needs its own trial. |

A working external server is useful input to the first boundary. It does not transfer ownership
of that container or establish the other two. `dedicated = false` withholds lifecycle authority;
it does not adopt an existing container, supply capacity admission, or make a cold service
startable. Retain the existing recipe until its replacement has its own acceptance and recovery
evidence, and do not run competing model copies on the same devices.

Bind the image digest, model artifact and served id, command, environment, mounts, devices,
context/output limits, and tested concurrency to the receipt. The generated Rune sample is an
editable example, not a benchmark-qualified recipe. Check the endpoint **from the Vessel's
network namespace**: host loopback and the loopback inside its pod are different destinations.
An endpoint override alone does not prove reachability or admit a new network route.

To repeat the trial through Bridge, configure revision 2 with the [exact capability selector](../../../extensions/weaver/index.md#choose-a-bridge-capability)
and a capability declaring chat and tools. Confirm the Run's pinned Pattern revision in Loom
and its recorded capability dispatch in Orb. Keep model-byte and runtime-generation identities
in the receipt as well: a capability key does not pin either.

Begin with one admitted request at a time. Before increasing concurrency, measure waits, timeouts,
cancellation, and useful completed work on that exact serving profile. Engine sequence count and
LychD lease count constrain different things.

Use [Summoning's host and first-light checks](../../../../summoning.md) for the surrounding body.
Its worked model recipe is llama.cpp; a vLLM trial must substitute its own qualified declaration
and record the actual runtime names and shutdown path. A connector smoke test cannot stand in for
that composed receipt.

The exact model, quantization, GPU topology, image digest, arguments, readiness, inference, and
shutdown still require an operator receipt. The current delivery boundary is recorded under
[vLLM integration](../../../../state-of-the-work.md#vllm-integration).

## Join one reply to durable Bridge

The former warm-model TestClient, sequential-spawn and source-native TCP selections are frozen
historical observations, retired on 2026-10-20 at base `7057210a`. They recorded one actual
structured Bridge reply and identical retained turns/model history after a second lifespan or
process boot, with explicit test Settings/Runes and refusing host actuation. Their raw receipts
and historical validators remain; no old source hash is refreshed to claim current qualification.

The host Core test deployment and source-native TCP launcher have been removed, leaving no host
pytest fallback. New evidence must run Core in the explicit OCI test image or, for installed
acceptance, in the rebuilt Vessel image with its declared PostgreSQL and security boundary.

That new proof needs fresh admission for external warm-model use, daemon/socket authority,
profiles, resource bounds, and terminal cleanup. The ordinary wrapper does not forward arbitrary
external profile files or proof environment. No replacement container runtime receipt is claimed.

The frozen trusted browser and installed-hybrid observations retain their original private
manager, plain Docker, inert model-unit and borrowed warm-vLLM limits. They do not qualify the
current fixture, production image, managed-model lifecycle or active container stop/start.
[State of Work](../../../../state-of-the-work.md#current-evidence-envelope) owns the exact
historical envelope and current proof gaps.
