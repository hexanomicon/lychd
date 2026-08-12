---
title: Standalone VPS
icon: material/server-security
---

# :material-server-security: Standalone VPS

This page owns the standalone deployment and end-to-end profile for a docs-aware
[Reach](../index.md) on an operator-controlled VPS. [Turn](../turn.md) owns the compact application
sequence; [A2A](../../../adr/26-a2a.md), [Tether](../../../adr/39-vpn.md), and
[Veil](../../../adr/40-proxy.md) retain protocol, private-reachability, and hostile-ingress law.

!!! warning "Designed, not deployable"
    The [Composition Portfolio](../../../state-of-the-work.md#composition-portfolio-delivery) is
    Designed. No Reach/Discord adapter, corpus pipeline, local Ward guest admission/task Sigil,
    Mirror Persona binding, general Privacy Cut and Portal Egress Gate, durable Reach or
    `ServiceJobAttempt@1` records, A2A transport, remote IAM, deployment-manifest compiler, Tether
    provider, or Veil provider ships. This profile is an implementation and acceptance target, not
    permission to expose the current loopback application or send Discord material to a remote
    provider.

## One restricted deployment

`reach.vps.public@1` is a versioned reference deployment profile of the Reach Composition. The VPS
is a standalone, restricted LychD body with its own Vessel, Workers, local Ward, and deployment-
local [Phylactery](../../../adr/06-persistence.md) for required Core Run, Ward, queue, and Reach state.
It is not the operator's home Vessel and has no route to the home database, private Context, Altar,
model services, Podman socket, Reactor, host authority, reusable home credential, or ambient Sigil.
After admission, local Ward may mint one secret-free, task-scoped Sigil; that Sigil expires with
the task and never crosses a model or A2A call.

The first E2E profile is **outbound-only and guest/public-only**. It answers a question eligible
for public disclosure from one admitted Discord Habitat using one admitted public corpus. It has
no Tether, Veil, callback listener, inbound A2A, published Agent Card, private home data, enrolled
caller powers, or dynamic peer discovery. A request needing private Context, a missing privacy
boundary, or authority outside this profile refuses.

An enrolled/private Reach attachment is a separate later profile revision. It requires delivered
remote Ward IAM and an exact private backend contract; guild membership or account fluency cannot
activate it.

## Enforced service and secret split

Operator provisioning creates one non-root, non-login Reach host account and the platform floor.
The accepted [`ApplicationDeploymentManifest@1`](../../../adr/08-containers.md#versioned-application-deployments)
then pins every row as a distinct rootless unit/container identity with exact image, command,
dependency order, mounts, network namespace, resource ceilings, and secret files; Scribe alone may
materialize it. Host account creation and cross-user lifecycle are outside Reach authority. No
shared Pod, environment, credential bundle, or writable volume substitutes for a typed local
request, inbox, or outbox.

| Service | May hold or do | Must not receive |
| --- | --- | --- |
| **Discord edge** | bot token; outbound Gateway; outbound Discord REST; emit validated events; consume one-delivery intents | corpus, provider/peer credentials, policy authority, general database write, public listener |
| **Reach core** | turn policy; local task-scoped Sigil; read-only active corpus; typed Phylactery port | bot token, long-lived provider/peer bearer, arbitrary Internet, corpus staging |
| **Portal/A2A egress adapter** | exact provider/peer credentials and destinations; execute one egress-admitted attempt | bot token, Sigil, raw private Context, dynamic routing, general proxying |
| **Corpus refresher** | allowlisted public-source network; bounded staging; atomic snapshot publication | bot/provider/peer credentials, application records, content-directed network |
| **Local Phylactery** | Core Run/Ward/queue plus Reach records, outboxes, dedupe, checkpoints, and admitted migrations | public or Tether listener, home-database replication, ambient service access |
| **Intercom ingress, separate later profile** | hostile decode; peer authentication; replay fence; bounded durable inbox | bot/provider credentials, Discord delivery path, direct work or effect authority |
| **Veil, separate later profile** | TLS, canonical ingress, exact route and coarse limit | application bearer, database, corpus writer, delivery authority |
| **Tether, separate later profile** | exact WireGuard peer and routes | default route, application credential, authorization decision |

Each egress-adapter instance serves one provider or peer trust class and receives only its own
credential reference and short-lived occurrence grant. The Reach core supplies the admitted
payload and decision identity, never its Sigil or another adapter's bearer.

Every local request uses an exact typed port over mutually authenticated transport. The manifest
pins distinct service Principals and credentials, audience, message/object types, expiry, replay
fence, and receiver authorization; caller-supplied identity is discarded. Unauthenticated
loopback, a shared bearer, container DNS, or possession of a network route is never workload
identity. Cross-service impersonation must fail even after one non-owning service is compromised.

The host firewall reinforces those edges and denies cloud metadata and private-network egress
except declared local service paths; another profile must declare any future Tether route. This split limits ordinary
lateral movement; it does not defeat root, VPS-control-plane, or operator-account compromise.
Those failures can expose every secret and retained payload on the machine.

## Public corpus contract

Reach owns source eligibility, interpretation, evidence selection, and citation judgment. The
acquisition adapter follows the bounded destination and hostile-data law of
[Web Acquisition](../../../adr/30-webcrawler.md#destination-and-data-boundary); the static site and a
read-only checkout alone are not retrieval.

A refresh admits only Git repositories addressed by canonical HTTPS URLs or canonical HTTPS
static origins; `git://`, SSH/SCP, local/file origins, credential helpers, and ambient credentials
are refused. Source policy binds allowed paths, an operator-admitted commit or verified immutable
release provenance, content digests, builder/parser/index revisions, and file, byte, expansion,
depth, and work ceilings. Movement of a mutable branch is candidate discovery, never activation
authority. Checkout and build disable hooks, submodules, smudge/LFS processing, and content-directed
network access. They reject escaping symlinks, unsupported media, malformed encodings, and archive,
decompression, or parser bombs. Index construction is network-free. Failure leaves the previous
snapshot active; only a completely validated and admitted staging generation activates atomically.

`PublicCorpusSnapshot@1` records source identities, immutable revision and content digests,
accepted paths, tool revisions, build receipt, activation time, and freshness state. Retrieved
passages remain attributed, instruction-fenced data—never prompt instructions, executable policy,
or proved truth. `reach.vps.public@1` sets `fresh_until` to 24 hours after activation. After it
passes, Reach settles `DEPENDENCY_UNAVAILABLE` rather than silently treating the last snapshot as
current. An operator may separately admit a frozen historical snapshot only for an explicitly
historical question whose answer displays that revision.

`CorpusEvidenceBundle@1` binds one snapshot; passage identifiers and digests; canonical URLs and
sections; and retrieval, passage-count, token, and total-size ceilings. Only this bounded bundle,
not the checkout or index, may enter a remote task. A claimed citation must bind to one selected
passage; an absent, altered, or unbound citation refuses validation.

## First E2E contract: one public Discord question

1. **Receive.** Discord edge accepts an outbound-Gateway event and validates application, guild,
   channel or thread, trigger, byte limit, and adapter revision.
2. **Reserve.** Reach atomically inserts `DiscordEventAdmission@1` under `(platform, adapter
   revision, application id, event kind, external event id)` plus payload digest before cognition.
   Exact replay under the same Habitat/owner partition returns its existing turn or terminal
   status; changed-content or cross-partition reuse is a security fault.
3. **Admit.** Local Ward assigns guest/public-only authority under `(platform, application, guild,
   channel-or-thread, external-subject)`. A guest receives no retained personal history. Ward mints
   a task-scoped local Sigil only after this mapping.
4. **Ground.** Reach selects one active `PublicCorpusSnapshot@1`, retrieves bounded attributed
   passages, and seals one `CorpusEvidenceBundle@1`.
5. **Form.** The exact Pattern and Run assemble labelled Context. When policy requires a
   [Privacy Cut](../../../adr/21-context.md#privatization-and-the-privacy-cut), missing lineage, the
   Cut, its verifier, or its receipt refuses remote formation.
6. **Admit egress.** Immediately before the first outbound byte, Security's trusted Portal Egress
   Gate issues a fresh exact `EgressDecision` binding Principal/Sigil, Run and attempt, provider or
   peer, destination, purpose, canonical payload digest, labels, policy and transformation receipt,
   expiry, and budgets. Retry, fallback, redirect, resume, payload, actor, model, peer, or
   destination change requires another decision.
7. **Call.** The egress adapter persists `ServiceJobAttempt@1` for a model call, or uses the
   Intercom task/outbox record for one enrolled, authenticated, task-authorized A2A peer. It moves
   the record to `SUBMITTING` before transmission and receives no local Sigil or undisclosed raw
   Context.
8. **Quarantine.** The return is attributed untrusted input. Reach checks protocol/schema, size,
   terminal status, task correlation, citations, privacy, and output class before adoption.
9. **Commit.** One Phylactery transaction commits `ReachTurn@1` and
   `DiscordDeliveryIntent@1(PENDING)` with effect id, payload digest, and deterministic nonce. Over
   its authenticated claim port, Discord edge obtains one generation-fenced lease; the ledger
   persists `CLAIMED`, then `SUBMITTING`, before the edge performs Discord REST with
   `enforce_nonce=true`. The edge has no database credential.
10. **Settle.** Reach records `ReachDelivery@1` with effect id, payload digest, platform status,
    nonce, claim generation, and Discord message id when known through the authenticated settlement
    port. A pre-`SUBMITTING` expired claim may be reclaimed under the same intent. After a lost
    acknowledgement, an exact retry with the same nonce is permitted only inside Discord's
    documented uniqueness window; outside that window or without matching payload it becomes
    `UNKNOWN` and is not resent.

```text
DiscordEventAdmission
  -> Run / Pattern revision
  -> PublicCorpusSnapshot + CorpusEvidenceBundle
  -> Context lineage + Cut receipt + EgressDecision
  -> ServiceJobAttempt or Intercom task/outbox
  -> ReachTurn + DiscordDeliveryIntent
  -> ReachDelivery
```

The chain correlates external event, turn, Run/station attempt, provider request or A2A
task/message/idempotency identities, delivery effect, payload digest, and Discord message id. A
provider completion string, HTTP success, or fluent answer cannot replace any committed edge.

| Record | Terminals |
| --- | --- |
| `ReachTurn@1` | `SUCCEEDED`, `REFUSED`, `DEPENDENCY_UNAVAILABLE`, `EXPIRED`, `FAILED`, `INDETERMINATE` |
| `ReachDelivery@1` | `NOT_ATTEMPTED`, `KNOWN_SENT`, `KNOWN_REJECTED`, `UNKNOWN` |

`DiscordDeliveryIntent@1` uses `PENDING -> CLAIMED -> SUBMITTING -> KNOWN_SENT |
KNOWN_REJECTED | UNKNOWN`. Claim identity, generation, lease, and attempt history remain durable.
Crash after `SUBMITTING` is possible external effect, never a reclaimable unsent claim.

## Outbound A2A without an inbound edge

The first A2A path pins one A2A 1.0 adapter and binding, enrolled peer identity, authentication,
task schema, destination, and budgets. Public or registry Agent Cards are advertisements, not
enrollment, current authority, destination admission, or availability truth.

The first independent interoperability receipt closes one polling case:

| Field | `reach.vps.public@1` A2A receipt |
| --- | --- |
| protocol | A2A `1.0`, HTTP+JSON binding, adapter and schema fixture digests pinned |
| peer | one pre-enrolled Principal, canonical HTTPS origin, Agent Card digest, server certificate identity, and task authorization named by the receipt |
| authentication | mutual TLS with distinct audience-bound client credential; no bearer in payload |
| task | `reach.public_corpus_answer@1`; one text query plus one `CorpusEvidenceBundle@1`; text/structured response only; files, artifact URLs, tools, teaching, and continuation refused |
| operations | non-blocking `POST /message:send` returning a Task, then `GET /tasks/{id}` only; a direct Message, stream, or push notification is outside this receipt |
| polling | every 2 seconds, at most 20 polls, 45-second absolute task deadline; transport retry never creates another message/task identity |
| ceilings | one task; 32 KiB request; 256 KiB response; eight evidence passages; 2,000-character query; profile-pinned token and spend ceilings |
| adoption | authenticated expected task/context identity, current peer authorization, first terminal, quarantine, schema/citation validation |

The receipt must replace every peer value with an observed independent endpoint; a placeholder or
same-process fake proves only conformance. A model Portal is a separate E2E case using the same
Context, egress, `ServiceJobAttempt@1`, quarantine, and delivery boundaries.

Reach commits the task and outbox before send, then parks the calling Invocation in Durable
Stasis. The client uses the outbound response, polling, or an outbound stream; push callbacks are
disabled. Every update is authenticated, correlated, checked against current peer/revocation
policy, and adopted first-terminal-wins before quarantine. `SUCCEEDED`, `REFUSED`, `FAILED`,
`EXPIRED`, `REVOKED`, `CANCELLED`, and `LOST` remain distinct; silence is not success and an unknown
post-submit effect is never silently repeated.

The 1.0 adapter maps `TASK_STATE_COMPLETED`, `TASK_STATE_REJECTED`, `TASK_STATE_FAILED`, and
`TASK_STATE_CANCELED` to `SUCCEEDED`, `REFUSED`, `FAILED`, and `CANCELLED`. The one-shot public task
refuses `TASK_STATE_INPUT_REQUIRED` or `TASK_STATE_AUTH_REQUIRED` without sending new user
credentials. Local deadline, current peer revocation, and irreconcilable remote loss settle
`EXPIRED`, `REVOKED`, and `LOST`; transport silence maps to none of them by itself.

Later inbound profiles stay separate:

| Profile | Exact boundary |
| --- | --- |
| **Callback-only client** | Veil may route a notification only to isolated Intercom ingress; it may update one existing outbound task after authentication, replay fencing, task/token correlation, current authorization, and durable admission. |
| **Full A2A server** | A distinct server profile needs Veil, Ward, Intercom durable inbox/outbox, Workers, quotas, and its own result path. A new peer task is not a Reach/Discord turn. |

Incoming peer work never creates a Discord delivery. In particular, publishing an Agent Card or
opening a task route cannot grant a foreign peer use of the bot identity.

## Destination and abuse boundary

Every corpus, Portal, artifact, and A2A destination is admitted as a canonical HTTPS origin, port,
path, and purpose without ambient proxy or credentials. Resolution rejects loopback, private,
link-local, multicast, unspecified, cloud-metadata, and mixed public/private results. The admitted
address stays pinned through connection; connected peer, TLS certificate, SNI, and `Host` must
match. Each redirect and new connection is independently resolved and admitted.

Before any provider or peer response reaches Reach core, its egress adapter enforces status and
content-type policy; header, wire-byte, expanded-byte and expansion-ratio bounds; chunk count and
size; stream duration and idle time; JSON depth/items; parse/token work; and total result limits.
Violation closes the response and returns a typed dependency failure without parsing further.

The initial profile also bounds Gateway events per application/guild/channel/subject, concurrent
turns, evidence bytes, provider/A2A response bytes, tokens, time, retries, and spend. Later ingress
adds pre-auth connection, header, compressed and expanded body, JSON depth/item, signature-work,
and time limits; per-IP, peer, route, and global quotas; bounded durable queues and streams; and
separate CPU, memory, process, disk, and connection ceilings. Overload refusal cannot evict Gateway
heartbeat, committed Discord delivery, or recovery work.

## Retention and provider custody

The initial profile uses these maximums; an operator may shorten them. Longer retention is a new
declared policy decision, not a logging default.

| Material | Maximum and retained form |
| --- | --- |
| raw Discord event/query | 24 hours after terminal; up to 7 days only while reconciliation is unresolved, then digest and minimum admission fields |
| caller/admission evidence | 30 days; partition, policy, decision and abuse facts without copied profile content |
| evidence bundle and every terminal turn | 30 days; structural terminal record plus exact selected public passages or their independently retrievable digests and refs |
| raw egress payload or quarantined return | 24 hours after terminal; up to 7 days for `INDETERMINATE`, then decision/result digests and receipts |
| delivery and external idempotency identities | 90 days; event/effect ids, payload digest, status, and Discord message id |
| edge address and coarse abuse log | 7 days, access-controlled and minimized |
| corpus snapshots | active plus previous generation; evidence retained with a turn remains separately bounded above |

General telemetry contains no raw prompts, passages, results, credentials, or pseudonym maps.
Provider-side storage, training, region, subcontractor, and deletion behavior is part of destination
policy and must be admitted before egress; local deletion cannot erase a provider's copy.

These maximums bind replicas, exports, encrypted backups, VPS snapshots, journals, swap, and crash
dumps as well as live rows. Raw payloads and credentials are disabled in core dumps and service
journals; swap is encrypted or disabled. The deployment manifest either disables backups and
declares total Phylactery loss unrecoverable, or pins an encrypted off-host backup/expiry/restore
profile whose decryption key remains offline. Unrecoverable ledger loss disables Reach until
external effects within the idempotency horizon are reconciled; a fresh database cannot declare
old Discord or A2A effects absent. Decommission destroys volumes and expires every secondary copy.

## Restart, uncertainty, and compromise

A replay returns the committed admission or turn. Failed corpus refresh keeps the previous active
snapshot and degrades freshness. Failure proved before submission may create a fresh attempt and
fresh `EgressDecision`; possible post-submit failure is `INDETERMINATE` until reconciled. Parked A2A
work survives restart as protocol identities and checkpoint, never as a provider SDK object.
Unknown Discord delivery is not retried without independent effect evidence.

Suspected service compromise revokes its leases and credentials, quarantines outputs, taints
related tasks and deliveries, and preserves only bounded secret-free correlation evidence. Root,
operator-account, or VPS-control-plane compromise instead requires:

1. stop Reach and withdraw Veil routes, callback DNS, and any Agent Card;
2. revoke Discord, provider, A2A signing/authentication, Tether, Veil/ACME, operator/session, and
   source/deployment credentials that could have crossed the host;
3. mark in-flight calls, callbacks, and deliveries tainted or uncertain and reconcile their
   external ids with Discord, providers, and peers;
4. destroy and reprovision from a trusted pinned image rather than restart the compromised host;
5. restore only independently verified non-secret records, rebuild the corpus from admitted
   origins, issue disjoint credentials, and re-enroll from zero authority.

## Acceptance gates

Repository tests must prove event and payload identity collision, replay, partition isolation,
Privacy Cut and `EgressDecision` binding, destination/redirect rebinding attacks, malicious corpus
paths and parser bombs, malicious chunked/compressed/deep provider responses, provider/A2A timeout
at each commit boundary, quarantine, task revocation at every lifecycle edge, restart, overload
separation, and Discord claim/nonce reconciliation and expiry without duplication.

A live-host receipt must name exact source and image revisions, OS/systemd/Podman, service users,
the selected `ApplicationDeploymentManifest@1` and compiler receipt, units, mounts, local mTLS
Principals/credentials and cross-service impersonation refusals, networks, firewall and DNS, secret
projections, resource ceilings, corpus generation, Mirror/Ward binding, external adapter revisions,
reboot, credential absence across services, backup/restore or declared-loss behavior,
reconciliation, shutdown, and a clean rebuild/rotation drill. None of those gates promotes delivery
by prose; only the evidence owners and [State of Work](../../../state-of-the-work.md) may do that.

[Deployment matrix](index.md) · [Reach turn](../turn.md)
