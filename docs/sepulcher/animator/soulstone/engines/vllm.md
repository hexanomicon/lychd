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

Supply the endpoint and exact model id you intend to test. The probe accepts only literal
loopback HTTP endpoints with an explicit port. It sends synthetic inputs, runs the two cases
sequentially with finite request/output limits and a cooperative deadline, and writes one JSON result
to stdout; diagnostics use stderr. Success requires the model to return a fresh marker obtained
from the actual tool call and leave no live capability lease. Each response must identify the
declared model and carry an explicit provider finish reason matching `stop` or `tool_call`
before the Agent may process it. The SDK's default for an absent wire reason does not qualify.
Filtered, truncated, errored, or unknown completion states fail even if their text contains the
marker. A failed case retains any response metadata already observed by the probe. A failed or
cancelled call does not prove that the externally operated server has finished its work. Shielded
client cleanup can outlast the cooperative deadline; the outer process timeout bounds the command.
A missing final JSON receipt after forced termination leaves cleanup and server outcome unknown
and blocks a pass.

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

For a repeatable Bridge trial, use the [exact capability selector](../../../extensions/weaver/index.md#choose-a-bridge-capability)
with revision 2 and a capability declaring chat and tools. Verify the Run's pinned Pattern
revision in Loom and its recorded capability dispatch in Orb. Capability-key pinning does not pin model bytes or the runtime generation;
keep those identities separately in the receipt. Start with one admitted request at a time.
Before increasing concurrency, measure waiting, timeouts, cancellation and useful completed work
on the exact serving profile; engine sequence count and LychD lease count are different bounds.

Use [Summoning's host and first-light checks](../../../../summoning.md) for the surrounding body.
Its worked model recipe is llama.cpp; a vLLM trial must substitute its own qualified declaration
and record the actual runtime names and shutdown path. A connector smoke test cannot stand in for
that composed receipt.

The exact model, quantization, GPU topology, image digest, arguments, readiness, inference, and
shutdown still require an operator receipt. The current delivery boundary is recorded under
[vLLM integration](../../../../state-of-the-work.md#vllm-integration).

## Join one reply to durable Bridge

After the warm connector passes, a separate opt-in test joins the production application factory,
source-registered vLLM, real Dispatcher, Graph, Context, SAQ and disposable PostgreSQL. It submits
one synthetic Bridge turn through authenticated HTTP with CSRF, requires a streamed structured
`BridgeReply`, then checks the same settled turns and model history after a second application
boot. The host actuator is an explicitly refusing fixture; the external model stays running.

Use the [container-test setup](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#setup-and-commands)
with a compatible Docker backend and cached `pgvector/pgvector:pg18-trixie` plus the configured
Ryuk image when enabled. The test refuses image pulls. Create a JSON profile outside the checkout
with `base_url`, `model_id`, `source_revision`, `context_tokens`, `max_tokens` and
`deadline_seconds`, using the same explicit inputs as the standalone probe. The admitted ceilings
are 4096 context tokens, 256 output tokens and 30 seconds; at most three model POSTs may enter the
real transport. Confirm an idle or otherwise declared load window before invoking:

```bash
LYCHD_REQUIRE_LOCAL_BRIDGE_PROOF=1 \
LYCHD_LOCAL_BRIDGE_PROFILE=/absolute/path/local-bridge-profile.json \
timeout --signal=TERM --kill-after=5s 210s make test-containers N=0 \
  CONTAINER_TEST_TARGETS=tests/integration/test_local_bridge_runtime.py
```

Without explicit opt-in this case skips. Missing prerequisites under opt-in are not a qualified
result. The model deadline is cooperative; use an outer process budget and retain uncertain
cleanup as unknown. Copy `local-bridge-runtime/receipt.json` from the test's basetemp outside the
checkout before a clean docs build clears `.cache`. It contains metadata, not credentials or
conversation text.

This proves two application lifespans over one disposable database through TestClient HTTP.
For clean restart across independent Python processes, replace the selector in the same command
with `CONTAINER_TEST_TARGETS=tests/integration/test_local_bridge_process_restart.py`. This
Linux-only test starts two sequential `spawn` children over one parent-owned PostgreSQL. The
first must finish application cleanup and exit before the second starts; the second must recover
identical settled turns and model history without another model POST. Missing child metadata,
nonzero exit, forced termination, an unreaped child or incomplete database cleanup blocks a pass.
Both children still use TestClient HTTP, rather than a Granian TCP listener.

Crash recovery, the real browser, installed Vessel, model bytes, managed activation/shutdown,
shared load and general tool execution require their own trials.
The [maintained result](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-runtime.json)
and the separate [clean process-restart result](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/animator/local-bridge-vllm-process-restart.json)
have source/dependency freshness checks. Copy the latter's `local-bridge-process-restart/receipt.json`
from basetemp before cleaning the documentation cache as well.

See [Soulstone Disciplines](../disciplines.md#i-the-kinetic-vllm), [vLLM](https://docs.vllm.ai/),
and the [OpenAI-compatible connector boundary](../../connectors.md#openai-compatibility-is-per-dialect).
