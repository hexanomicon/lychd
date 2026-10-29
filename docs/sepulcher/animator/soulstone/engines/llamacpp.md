---
title: llama.cpp
icon: material/chip
---

# :material-chip: llama.cpp

**llama.cpp** is a local model-serving engine with two materially different Soulstone shapes:

- `single` starts with one declared model and serves one stable alias;
- `router` starts without a model and activates declared models in process.

## Launch and identity

First decide whether the adapter or the operator owns the command. Explicit `exec` supplies the
whole command. For a managed command, `startup_mode` chooses `single` or `router`. With `auto`,
argument and environment inference comes first; otherwise a `model_path` selects `single`, and
its absence selects `router`. Typed `extra_args` append last.

A forced mode must remain true after all inputs are considered. Forced modes therefore refuse
known main-model source controls in `extra_args`, including shortcuts and token lookalikes in
value positions. Use `model_path` for forced `single`, or model directories and presets for
forced `router`. Forced `router` also refuses model-source environment controls. Forced `single`
refuses a main Hugging Face repository in the environment because a remote preset can clear its
model path. Both checks include variables projected from `secret_env_files`.

These checks establish the supported command shape without reproducing all upstream option
grammar. GPU/CPU offload remains a fact of the exact profile; the launch mode supplies no universal
VRAM promise.

Mode metadata follows the final command and its projected environment, including
`secret_env_files`. For main-model and router source options, environment values apply first;
a CLI value replaces the same source option even when it is empty. A nonempty main model path or
Docker repository selects `single`; model directories and presets do not override that main source. Without a main source the server is a
router. For managed `auto` planning, router argument or environment inputs still take precedence
over an otherwise unused typed `model_path`.

An effective main Hugging Face repository or a built-in main-model shortcut is refused: remote
preset contents can change the server's mode, so local declaration cannot establish it. Use an
explicit local model or router directory/preset. A model URL, HF filename, draft model, or
`--spec-default` alone does not establish a main model or its provider identity.

Write source, router, and alias controls with separate positional values. Empty values are
retained; missing values, dash-leading values, and equals-form values fail validation. The adapter
normalizes known underscore aliases for interpretation without rewriting their passthrough bytes.

Place these controls before options whose arity LychD does not know. Otherwise a later source or
alias token could be an unknown option's value, making its meaning ambiguous and causing refusal.
Unknown trailing options remain operator-owned. This boundary prevents a consumed value from
being mistaken for a source control without claiming a complete upstream parser.

With passthrough `exec`, the operator must keep its listening port and served alias aligned with
the declared endpoint and model identity. Declaration compilation rejects a known `--port` or
`LLAMA_ARG_PORT` value that conflicts with the resolved endpoint, including a final `extra_args`
override of a managed command. LychD does not rewrite passthrough commands or infer unknown wrapper
syntax; declare the endpoint and command consistently for a runnable profile.

Keep engine idle sleep disabled. Readiness probes and `autoload=false` cannot fence the engine's
automatic wake, so that mode falls outside the supported profile. Managed arguments begin with
`--sleep-idle-seconds -1`; omit `sleep_idle_seconds` or set it to `-1`. No sleep control may
appear in `extra_args`.

Passthrough `exec` must begin with the exact disabling pair: either
`["--sleep-idle-seconds", "-1", ...]` for an image entrypoint, or
`["llama-server", "--sleep-idle-seconds", "-1", ...]` for a complete command. The executable token
must be nonempty and cannot begin with `-`; admitted bytes are not rewritten.

Validation rejects later sleep controls, duplicate disabling flags, underscore aliases, equals
spellings, and misplaced or malformed disabling arguments. It needs a known command shape because
a flag consumed as another option's value cannot disable sleep. Custom wrappers unable to honor
this shape remain outside the supported llama.cpp profile.

This contract was checked against upstream revision
[`434ddbbc0e30522e897670681e503b797c12b7c1`](https://github.com/ggml-org/llama.cpp/commit/434ddbbc0e30522e897670681e503b797c12b7c1):
the router [overlays CLI arguments on every model preset](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/tools/server/server-models.cpp#L531),
while [sleeping children still count as running](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/tools/server/server-models.h#L93)
for router autoload admission. The default is disabled, but the explicit command value also
overrides sleep enabled in global, model, directory, or cached presets. Command validation does
not attest an already-running service or external changes; operator validation must check the
actual image revision and arguments.
The pinned [argument parser](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/common/arg.cpp#L816)
normalizes underscore option names and consumes values positionally; equals-form sleep flags are
not accepted by that engine revision.

The same revision [selects router mode only after resolving the main model sources](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/tools/server/server.cpp#L110-L127).
A later empty `--model` can clear an earlier path, and a
[Hugging Face remote preset clears the main-model settings](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/common/arg.cpp#L631-L636).
The forced-mode refusals prevent those inputs from contradicting the selected launch shape.

Aliases accumulate across `LLAMA_ARG_ALIAS` and every `--alias` or `-a` occurrence. Each value
supplies comma-separated names; the supported profile trims ASCII whitespace and discards empty
entries. An empty CLI alias does not clear an environment alias. The lexicographically first name
in the combined set identifies the single model in the engine's inventory. Without any alias,
single-model identity is the exact Docker repository or model path, including its directory and
suffix. These rules follow the pinned [alias handler](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/common/arg.cpp#L2899-L2909)
and [inventory identity](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/tools/server/server-context.cpp#L1263-L1273);
locale-dependent treatment of non-ASCII whitespace is not attested by this profile.

When managed planning selects `single`, it generates an alias. Explicit argument or environment
aliases take precedence; otherwise `served_model_id` supplies it, followed by the generated model path's stem
(basename without its final suffix), a Docker repository, or the Soulstone name. An explicit
`[[models]]` catalogue does not disable alias generation. Without that catalogue, the adapter
infers capability identity from the final launch inputs. Default model selection uses the first
entry of the captured catalogue, including an explicit catalogue when supplied. An `auto` plan
that omits the typed model and becomes single-model through an environment source does not add
an alias; its identity follows the final inputs above.

Declared model ids must match the engine's live inventory; a healthy process alone cannot grant
an absent model. The single-model probe validates `/v1/models` after `/health`, following the
upstream [Model Info API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#get-v1models-openai-compatible-model-info-api).
A preset path projected through `secret_env_files` is not opened locally for catalogue or
generation-default discovery. Declare the model catalogue when using that source; its actual
contents and runtime behavior remain operator validation.

## Context allocation

Use the generated command, including final `extra_args`, to determine managed context metadata.
The catalogue divides positive total `-c` context by positive `-np` parallel slots, then applies
any smaller explicit `--kv-unified-per-slot` cap. For example, `-c 8192 -np 4` admits a conservative
2048-token request bound even if unified KV could give one request more.

Generated flags take precedence over environment and presets. Explicit `exec` leaves the derived
bound unknown unless positive context and slot counts are known. Automatic or malformed command
or environment inputs cannot silently fall back to a lower-priority value. These flags follow the
upstream [server parameters](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#server-specific-params).

This measures configured allocation, not the model's training context or live hardware. Explicit
generation overlays set request policy without resizing the engine's allocation.

## Readiness and control

Inspect each router model's own inventory status. Clean `unloaded` permits activation; `loading`
is `WARMING`; `loaded` together with ready health supplies warmth. A missing declared model or
malformed inventory fails closed. Failed, sleeping, downloading, or unknown statuses cannot
authorize activation, and one model's health cannot establish a sibling's readiness.

Activation checks inventory again and does not repeat a load in progress. Inference and targeted
health requests use `autoload=false`. With idle sleep disabled, losing a loaded model therefore
cannot silently load or evict another. Runtime-native activation leaves the process running;
reclaiming a conflicting physical runtime remains an Orchestrator transition.

The current repository proves planning, discovery, capability derivation, and model-load control.
Model unloading is not a separate adapter operation; whole-runtime shutdown belongs to Orchestrator.
A real engine/GPU/model result remains [operator validation](../../../../state-of-the-work.md#llamacpp-integration).

Control receipts are intentionally literal: model-load succeeds only on JSON boolean `true`, not
`1` or `"true"`.
Known numeric preset keys use their canonical integer or floating type; boolean words are ignored
rather than silently becoming `0` or `1`. Treat those refusals as malformed provider/configuration
evidence, not as successful control.

See [Soulstone Disciplines](../disciplines.md#iii-the-titan-llamacpp),
[llama.cpp](https://github.com/ggml-org/llama.cpp), and the
[repository support files](https://github.com/hexanomicon/lychd/tree/main/examples/llamacpp).
