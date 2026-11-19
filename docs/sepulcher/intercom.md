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
adds an explicit Run/Graph lab below. To accept a colleague's brief, start the
[paired receiver](#receive-a-public-brief) on the receiving installation. Private Context,
voice input and automatic fallback remain separate work.

To see whether a colleague welcomes a request, use [Nexus colleague presence](../divination/altar/nexus.md#see-which-colleagues-welcome-requests).
Presence pairing and enrollment of a receiving task endpoint have separate credentials.
The [short-video design](../compositions/atelier/short-video.md#what-nexus-would-show) works
through a colleague's evening offer, storyboard review and result collection after reconnect.

## Prepare the two identities

Prepare operator identity and workload identity separately. The installation's dedicated
local-access credential authenticates the operator; a configured Ed25519 signing key identifies
the local workload. Trusted host configuration must also enroll the remote peer's immutable
identity and public verification key. Reachability, a TLS certificate, or an advertised Agent
Card cannot perform that enrollment.

The peer must implement this profile's required signing extension. An unsigned stock A2A SDK
route is useful for baseline protocol testing, but cannot satisfy the protected session. The
qualification used the official SDK's real dispatcher and task store with explicitly test-only
signing middleware; the middleware is not an upstream SDK feature.

Apply the normal database migration gate before using the session. Revision `0022` adds the
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

Capacity survives changes to configuration labels, task ids, and credentials. Changed ceilings
refuse rather than resetting it. A new policy generation immediately invalidates old live
authority; before a later startup activates the new generation, trusted host composition must
establish the matching durable policy. The session supplies no policy-update command.

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

Cancellation first closes local result adoption, then asks the peer to cancel. Read its local
disposition separately from the authenticated foreign observation. An acknowledgement establishes
neither rollback nor process containment. If a task already reached an admitted terminal, it
remains readable under current authority and refuses late cancellation.

`rotate` takes the exact target and a new remote key record; the old key version is retired before
the persistence wait. `revoke` fences local handoffs before awaiting durable revocation. An
uncertain authority mutation remains fenced. No session command deletes history, refunds capacity,
fetches artifacts, streams, discovers endpoints or selects another peer, provider or language.

This profile has one control process and event loop. Cross-process revocation, hostile same-UID
containment, general remote IAM and private-input anonymization are outside its delivered boundary.

## Receive a public brief

Lin can submit a public script this afternoon for Ada to review and start this evening. Both
installations need a migrated PostgreSQL database, a dedicated local operator credential and
their own Ed25519 workload signing key. Migrate the receiver through revision `0028`. Ada
also needs a TLS certificate for the enrolled hostname and its corresponding private key.
Lin needs the CA certificate that issued it. Each operator sets `LYCHD_INTERCOM_DATABASE_URL`
for their own database and `LYCHD_INTERCOM_SIGNING_KEY_FILE` to their own signing key.

**On Ada's PC**, keep the invitation and private keys outside the checkout. On Linux use a
directory owned by Ada with mode `0700`, and mode `0600` for the invitation and private keys.
Select exact loopback or RFC 1918 IPv4 addresses. In this example Ada listens on
`192.168.10.20` and admits the connection from Lin at `192.168.10.21`. Substitute the actual
addresses, workload UUIDs, enrolled Ed25519 public PEMs, file paths and UTC dates. The TLS
hostname must match the certificate and Lin's enrollment.

```json
{
  "receiver_id": "00000000-0000-4000-8000-000000000002",
  "sender_id": "00000000-0000-4000-8000-000000000001",
  "hostname": "atelier.example.test",
  "port": 8443,
  "listen_address": "192.168.10.20",
  "peer_address": "192.168.10.21",
  "task_schema": "atelier.short-video-brief@1",
  "sender_key_id": "lin-1",
  "sender_public_key_pem": "REPLACE WITH LIN'S PUBLIC PEM",
  "signing_key_id": "ada-1",
  "receiver_public_key_pem": "REPLACE WITH ADA'S PUBLIC PEM",
  "valid_until": "2026-11-21T10:00:00Z",
  "accept_from": "2026-11-20T12:00:00Z",
  "accept_until": "2026-11-20T17:00:00Z",
  "tls_certificate": "/absolute/private/atelier-server.pem",
  "tls_key": "/absolute/private/atelier-server-key.pem"
}
```

```bash
uv run --locked python scripts/intercom_receive.py --config /absolute/private/pair.json serve
```

**On Lin's PC**, use the [sender session](#prepare-the-two-identities). Enroll Ada's UUID
and public workload key, the numeric address `192.168.10.20`, hostname `atelier.example.test`,
port `8443`, path `/a2a/jsonrpc` and an absolute CA file. Select the same purpose in every
sender command, for example `atelier-production`, the category `public-task` and Ada's exact
task schema. For an evening job, set the explicit sender policy's `task_seconds` before
enrollment, for example to `64800` for 18 hours. The default is 900 seconds and the upper
bound is 86400. Allow time for review, completion and collection within the task lifetime
and keep the peer credentials and invitation valid through collection.

??? example "Lin's first enrollment"

    Save this public sender configuration after substituting both workload UUIDs and the
    endpoint. The example budgets sixteen physical operations for the session's selected
    scopes. Capacity already spent survives restart.

    ```json
    {
      "workload_id": "00000000-0000-4000-8000-000000000001",
      "signing_key_id": "lin-1",
      "policy": {
        "generation": 1,
        "actions": ["enroll", "classify_public", "submit", "poll", "read", "cancel"],
        "purposes": ["atelier-production"],
        "categories": ["public-task"],
        "task_schemas": ["atelier.short-video-brief@1"],
        "peers": ["00000000-0000-4000-8000-000000000002"],
        "endpoints": ["https://atelier.example.test:8443/a2a/jsonrpc"],
        "task_seconds": 64800,
        "limits": {
          "host": {"uses": 16, "application_bytes": 1048576, "network_bytes": 8388608},
          "purpose": {"uses": 16, "application_bytes": 1048576, "network_bytes": 8388608},
          "peer": {"uses": 16, "application_bytes": 1048576, "network_bytes": 8388608},
          "task": {"uses": 16, "application_bytes": 1048576, "network_bytes": 8388608}
        }
      }
    }
    ```

    Run `uv run --locked python scripts/intercom_lab.py --config /absolute/private/sender.json`
    and authenticate. For the first enrollment, send this line with Ada's real workload public
    PEM, trusted CA path and key-validity interval. Use JSON newline escapes inside the PEM.

    ```json
    {"operation":"enroll","peer_id":"00000000-0000-4000-8000-000000000002","purpose":"atelier-production","task_schema":"atelier.short-video-brief@1","endpoint":{"address":"192.168.10.20","hostname":"atelier.example.test","port":8443,"path":"/a2a/jsonrpc","ca_file":"/absolute/private/ca.pem"},"key":{"key_id":"ada-1","public_key_pem":"REPLACE WITH ADA'S PUBLIC PEM","issuer":"00000000-0000-4000-8000-000000000002","protocol":"rfc9421-ed25519@1","audience":"00000000-0000-4000-8000-000000000001","assurance":"operator-enrolled","valid_from":"2026-11-20T10:00:00Z","expires_at":"2026-11-21T10:00:00Z"}}
    ```

The following is one input line for the sender. `source.text` holds the brief encoded as
a JSON string. Follow `declare-public` with `submit` using the returned declaration ID.

```json
{"operation":"declare-public","peer_id":"00000000-0000-4000-8000-000000000002","purpose":"atelier-production","task_schema":"atelier.short-video-brief@1","endpoint":"https://atelier.example.test:8443/a2a/jsonrpc","source":{"public_assertion":true,"text":"{\"recipe\":\"animated-lesson\",\"duration_seconds\":12,\"script\":\"Show how a radius connects the centre to a circle.\",\"not_before\":\"2026-11-20T18:00:00Z\",\"latest_start_at\":\"2026-11-20T19:00:00Z\"}"}}
```

The three recipe names are `illustrated-story`, `animated-lesson` and `captioned-excerpt`.
Each accepts 1–180 seconds and a nonblank script. In this example Ada can receive a new brief
from noon until 17:00 UTC. The brief asks Ada to start it at or after 18:00 and before 19:00
UTC. An early or missed first start leaves the task submitted for a later eligible start
or local rejection. Omit both brief timestamps to allow an immediate start. Omit both invitation intake
timestamps to accept submissions throughout the invitation. An already admitted task can be
reviewed and collected after the intake window closes. Starting a task records Ada's decision.
The local [Atelier recipe](../compositions/atelier/short-video.md) describes the production steps.

**Review and return.** In a second terminal on Ada's PC, run the commands below with the
receiver UUID printed by `pending`. The final line approves the exact standard-input text
for return to Lin. The local credential prompt uses the controlling terminal.

```bash
receiver=(uv run --locked python scripts/intercom_receive.py --config /absolute/private/pair.json)
"${receiver[@]}" pending
"${receiver[@]}" review RECEIVER_TASK_UUID
"${receiver[@]}" start RECEIVER_TASK_UUID
printf '%s' 'Storyboard reviewed. The radius demonstration runs for 12 seconds.' |
  "${receiver[@]}" complete RECEIVER_TASK_UUID --public-result-stdin
```

Ada may also `reject RECEIVER_TASK_UUID`. Lin uses the original **sender** task ID for
`poll`, `read` and `cancel`. After restart, authenticate again on both sides and use the same
enrollment, database and IDs. If the first acknowledgement was lost, Ada can run
`find SENDER_TASK_UUID` to reconcile her local receipt with Lin. Lin's sender keeps the outcome
unknown until it has an authenticated receiver identity. This profile has no remote lookup by
sender ID. A second submission could commission the work twice. The current sender also
records an unknown outcome if a submit returns a signed protocol error, including refusal
at intake. An accepted task that Ada later rejects has a pollable rejected state.

Each pair retains up to 64 task records across configurations and has up to 128 unexpired
physical replay fences. Intake allows 8192 UTF-8 bytes per brief and returns up to 4096 bytes
of approved public text. Work and remote result disclosure expire 24 hours after admission.
Expiry preserves the records and their capacity charge. Up to eight established TLS clients
can run application requests at once. Change or withdraw the invitation to retire the active
session. For a later intake window, restart with fresh local authentication. Preserving the
same identities, signing key bindings, road and schema keeps the same work visible. Reconcile
outstanding tasks before rotating those bindings. A colleague's Nexus Ready status is a
separate presence signal. Artifact transfer, scheduled rendering and public internet ingress
have separate acceptance gates. [Paired receiver contract](../adr/26-a2a.md#paired-incoming-public-text)

## Native public peer Run

Apply revision `0023` through the normal migration gate. It binds a peer task to its exact Run,
station, request, pinned Pattern and actual Step/occurrence. It refuses inconsistent legacy wait
owners and refuses downgrade while native task, Run, closure or reauthorization evidence remains.
The existing `0022` retention rule still applies to all seven Intercom tables.

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

After restart, the lab restores durable evidence but needs fresh authentication and live peer
permission. Call `reauthorize-run` with `run_id`, the returned `task_id` and `binding_digest`, and
the exact `actions` selected from `submit`, `poll`, `read`, `adopt`, and `resume`. An unclaimed
first submit also needs `reaffirm_public_source: true`.

Reauthorization preserves the original task, body, and expiry. It cannot refresh the request or
replace an uncertain submit. If a claimed task lacks a foreign identity, reconcile its local
exchange before following the explicit unknown failure route.

The lab has no incoming peer, automatic relay loop, private-input producer, voice command path or
Blockworld effect. Its process restart and local cancellation checks do not prove remote process
containment, broker recovery or cross-process revocation.
