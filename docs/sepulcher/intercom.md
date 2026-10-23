---
title: Intercom
icon: material/account-switch-outline
---

# Intercom public-task session

Intercom asks another sovereign agent to perform a public task. The receiving peer owns its
models, tools and execution. Its reply is attributed foreign data; it cannot authorize a local
tool, game action or another task.

[State of Work](../state-of-the-work.md#a2a-intercom) owns delivery. The bounded
[`outbound-public-text@1` profile](../adr/26-a2a.md#peer-task-jsonrpc-1) provides an explicit operator
session. The separate [`native-public-peer@1` profile](../adr/26-a2a.md#native-public-peer-station)
adds an explicit Run/Graph lab below. Private Context, voice input and automatic fallback remain
separate work. Neither session starts a Minecraft client, model or incoming A2A server.

## Prepare the two identities

The session authenticates its operator against the installation's dedicated local-access
credential. Its separately configured Ed25519 signing key identifies the local workload. Enroll
the remote peer's immutable identity and public verification key through trusted host
configuration. A reachable URL, TLS certificate or advertised Agent Card cannot enroll a peer.

The peer must implement this profile's required signing extension. An unsigned stock A2A SDK
route is useful for baseline protocol testing, but cannot satisfy the protected session. The
qualification used the official SDK's real dispatcher and task store with explicitly test-only
signing middleware; the middleware is not an upstream SDK feature.

Apply the normal database migration gate before using the session. Revision `0016` adds the
seven Intercom custody tables. It refuses downgrade while any retains a row, including unused
capacity. The session itself has no migration or reset command.

Keep database credentials and signing-key bytes with their trusted host secret owners. Supply
`LYCHD_INTERCOM_DATABASE_URL` and an absolute `LYCHD_INTERCOM_SIGNING_KEY_FILE` in the process
environment. Put only public configuration in the file passed below:

```bash
uv run --locked python scripts/intercom_lab.py --config /absolute/public-config.json
```

The file contains `workload_id`, `signing_key_id` and `policy`. The policy is the exact
`PeerPolicy.record()` shape: `generation`, explicit `actions`, `purposes`, `categories`,
`task_schemas`, `peers`, `endpoints`, four `limits`, and bounded
`declaration_seconds`, `task_seconds`, `network_seconds`. Each limit, keyed by `host`, `purpose`,
`peer` or `task`, supplies `uses`, `application_bytes`, `network_bytes`. Empty selectors deny;
there are no wildcards. The eight independent actions are `enroll`, `classify_public`, `submit`,
`poll`, `cancel`, `read`, `rotate`, `revoke`.

Changing a configuration label, task id or credential cannot reset capacity. Changed ceilings
refuse. A changed policy generation immediately invalidates old live authority; matching durable
policy must be established through trusted host composition before a new startup can activate it.
The session does not expose a policy-update command.

## Author, submit and read

Each input line is one JSON object. `enroll` takes `peer_id`, `purpose`, `task_schema`, optional
`category` (default `public-task`), a `key` record, and an `endpoint` object with `address`,
`hostname`, `port`, `path`, `ca_file`. The numeric address and explicit CA file are mandatory.
The key supplies `key_id`, `public_key_pem`, `issuer` (peer UUID),
`protocol: "rfc9421-ed25519@1"`, `audience` (workload UUID),
`assurance: "operator-enrolled"`, and timezone-aware `valid_from` and `expires_at`.
The service independently pins its actual workload key binding; changing that key on restart
cannot silently reuse the enrollment.

After enrollment, target-bearing commands use the exact HTTPS URI, including its configured
port, as `endpoint`. They also carry `peer_id`, `purpose`, `task_schema` and optional `category`.
For example, with identities and selectors already admitted in public configuration:

```json
{"operation":"declare-public","peer_id":"00000000-0000-0000-0000-000000000002","purpose":"public-summary","task_schema":"public-text@1","endpoint":"https://peer.example:443/a2a/jsonrpc","source":{"text":"Summarize this public task description.","public_assertion":true}}
```

This dedicated field is an attributed human assertion of authored, public text. It is not PII
detection or proof that text was never pasted. Known restricted influence, unknown lineage,
local-only data and other source kinds refuse. Chat, microphone input, model output, files and
private Context do not enter this producer automatically.

`declare-public` returns a `declaration_id` whose exact live declaration belongs to this startup.
Use it once:

```json
{"operation":"submit","declaration_id":"the-returned-declaration-uuid"}
```

Submit returns status and the local `task_id`. `poll`, `cancel` and `read` carry that `task_id`
plus the same exact target selectors. Submit and poll return status only. Use the separate `read`
action to consume a retained result. The result remains `authenticated-foreign-data`.

Every physical operation is separately charged before contact: one use, its complete application
request size and a conservative 512 KiB network allowance. Actual accepted network bytes are
recorded separately and do not refund the reservation. Stable scopes are the host, exact purpose,
peer identity and peer-plus-schema task family.

## Uncertainty, cancellation and restart

An uncertain intent commit, claim commit, send acknowledgement or response authentication returns
`{"error":"unknown","task_id":"..."}`. Retain that identity and inspect it under fresh read
authority. A truly uncommitted task can be absent. Never automatically declare or submit a new
task to replace an unknown one: the peer may already be executing it.

A known foreign task id permits a fresh, authorized poll. An unknown id cannot be invented or
discovered by silently resending. Restart restores neither declarations nor live transmission
claims; it can explicitly reconcile known tasks with fresh authentication and current policy.

Cancel closes local result adoption before asking the peer to cancel. Its local disposition and
authenticated foreign observation remain distinct. A cancellation acknowledgement proves neither
rollback nor process containment. A task that already reached an admitted terminal remains
readable under current authority and refuses late cancellation.

`rotate` takes the exact target and a new remote key record; the old key version is retired before
the persistence wait. `revoke` fences local handoffs before awaiting durable revocation. An
uncertain authority mutation remains fenced. No session command deletes history, refunds capacity,
fetches artifacts, streams, discovers endpoints or selects another peer, provider or language.

This profile has one control process and event loop. Cross-process revocation, hostile same-UID
containment, general remote IAM and private-input anonymization are outside its delivered boundary.

## Native public peer Run

Apply revision `0017` through the normal migration gate. It binds a peer task to its exact Run,
station, request, pinned Pattern and actual Step/occurrence. It refuses inconsistent legacy wait
owners and refuses downgrade while native task, Run, closure or reauthorization evidence remains.
The existing `0016` retention rule still applies to all seven Intercom tables.

Use the same dedicated operator credential, workload key and exact public configuration:

```bash
uv run --locked python scripts/intercom_native_lab.py --config /absolute/public-config.json
```

Native policy additionally selects `admit`, `adopt`, `resume` and `inspect`. These are independent
actions; they do not grant `submit`, `poll` or `read`. Existing enrollment commands remain available.
This lab uses the actual RunEngine, Graph, worker function and PostgreSQL checkpoints with an
explicit process-owned delivery queue. It supplies no SAQ broker, capability or hardware transition.

`submit-public-run` takes the existing public `source` and exact target selectors plus a stable
`request_id` UUID. Supply an existing `session_id` when retrying that same admission; omitting it
creates a new session. The Run prepares one immutable task without contact, checkpoints it and
parks as `awaiting_peer`. Reusing a request with changed text or target refuses.

`tick` takes `run_id`, performs at most one submit or poll, and executes any admitted successor.
Repeat it explicitly while the task is pending. A correlated terminal can resume the Graph once;
the reply remains foreign data. `status` exposes local status, task identity and binding selectors.
A completed reply additionally requires current independent read authority. `cancel-run` closes
local adoption and awaits local exchange retirement; visible remote uncertainty is retained.
Commands are serial and network operations have their configured finite deadline.
An already settled unknown, expiry or remote noncompletion returns an explicit `outcome` with
local status; the next operator command remains usable. Other worker and authority failures are
not converted into a successful settlement.

Restart restores durable evidence without live peer permission. After fresh authentication,
`reauthorize-run` takes `run_id`, the returned `task_id` and `binding_digest`, plus the exact
`actions` selected from `submit`, `poll`, `read`, `adopt`, `resume`. An unclaimed first submit also
requires `reaffirm_public_source: true`. This reuses the original task, body and expiry; it cannot
refresh the request or replace an uncertain submit. A claimed task without a foreign identity
takes an explicit unknown failure route after its local exchange has been reconciled.

The lab has no incoming peer, automatic relay loop, private-input producer, voice command path or
Blockworld effect. Its process restart and local cancellation checks do not prove remote process
containment, broker recovery or cross-process revocation.
