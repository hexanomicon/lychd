---
title: Standalone VPS
icon: material/server-security
---

# :material-server-security: Standalone VPS

One public Discord question is enough to test the entire restricted VPS body: event admission, corpus evidence, cognition, committed answer, external send, and recovery. `reach.vps.public@1` owns that standalone deployment profile and end-to-end acceptance target.

The [worked question](#first-e2e-contract-one-public-discord-question) also states the common turn and delivery chain used by the [home-only](home-public.md) and [edge/home](vps-edge-home-core.md) profiles. Those profiles keep their own placement, custody, and recovery boundaries.

The profile requires the separate service and authority boundaries below. Before deployment, check their [implementation evidence](../../../state-of-the-work.md#composition-portfolio-delivery); the current loopback application cannot be exposed as this VPS body. Exporting Discord material requires its own admission.

## One restricted deployment

The VPS has its own Vessel, Workers, local Ward, and [Phylactery](../../../adr/06-persistence.md) for Core Run/Ward/queue and Reach truth. It has no road to home database, private Context, Altar, model services, Podman, Reactor, host authority, reusable home credentials, or ambient Sigils. Ward may mint a secret-free task-scoped Sigil after admission; it expires with the task and never crosses to a model or peer.

The baseline is outbound-only and guest/public-only, using one admitted Habitat/corpus and a question eligible for disclosure. It has no Tether, Veil, callback, inbound A2A, Agent Card, private home data, enrolled caller powers, or dynamic discovery. Private Context, missing privacy boundaries, and greater authority refuse. Enrolled/private attachment is a later profile requiring delivered remote Ward and an exact private backend, never guild membership.

## First E2E contract: one public Discord question

1. **Receive:** edge validates application, guild, channel/thread, trigger, bytes, and adapter on an outbound-Gateway event.
2. **Reserve:** atomically insert `DiscordEventAdmission@1` under `(platform, adapter revision, application id, event kind, external event id)` and payload digest. Exact replay in the same Habitat/owner partition returns committed status; changed-content/cross-partition reuse is a security fault.
3. **Admit:** Ward maps guest scope under `(platform, application, guild, channel-or-thread, external-subject)`, with no retained personal history, then mints the task Sigil.
4. **Ground:** select the active snapshot, bounded passages, and sealed evidence bundle.
5. **Form:** exact Pattern/Run assembles labels and required [Privacy Cut](../../../adr/21-context.md#privatization-and-the-privacy-cut); missing lineage/verifier/Cut/receipt refuses remote formation.
6. **Admit egress:** immediately before bytes, the trusted gate issues fresh `EgressDecision` binding Principal/Sigil, Run/attempt, provider/peer/destination/purpose, payload digest, labels, policy, transformation receipt, expiry, and budgets. Retry, fallback, redirect, resume, payload, actor, model, peer, or destination change needs another decision.
7. **Call:** persist `ServiceJobAttempt@1` or the enrolled/task-authorized Intercom task/outbox, then `SUBMITTING` before transmission. Adapter receives no Sigil or undisclosed Context.
8. **Quarantine:** validate attributed return protocol/schema, size, terminal, correlation, citations, privacy, and output class before adoption.
9. **Commit:** one transaction writes `ReachTurn@1` and `DiscordDeliveryIntent@1` in `PENDING` with effect, digest, and deterministic nonce. Authenticated claim grants a generation-fenced lease; ledger persists `CLAIMED`, then `SUBMITTING`, before edge REST with `enforce_nonce=true`. Edge holds no database credential.
10. **Settle:** authenticated settlement writes `ReachDelivery@1` with effect/digest, platform status, nonce, claim generation, and known message id. Expired pre-submit claims may be reclaimed under the same intent. After possible send, keep `UNKNOWN` and do not resend until independent evidence reconciles the effect.

Discord's [Create Message reference](https://docs.discord.com/developers/resources/message#create-message) describes nonce uniqueness only for “the past few minutes”; it supplies no bounded safe retry deadline. A future adapter may admit same-nonce, matching-payload retry only under an exact platform guarantee that excludes duplication for that attempt.

```text
DiscordEventAdmission
  -> Run / Pattern revision
  -> PublicCorpusSnapshot + CorpusEvidenceBundle
  -> Context lineage + Cut receipt + EgressDecision
  -> ServiceJobAttempt or Intercom task/outbox
  -> ReachTurn + DiscordDeliveryIntent
  -> ReachDelivery
```

This binds event, turn, Run/station attempt, provider/A2A request/task/message/idempotency identities, effect, digest, and Discord message. HTTP success or provider prose replaces none of those committed edges.

Keep the outcome of the turn separate from the outcome of sending it. `ReachTurn@1` terminates as `SUCCEEDED`, `REFUSED`, `DEPENDENCY_UNAVAILABLE`, `EXPIRED`, `FAILED`, or `INDETERMINATE`; `ReachDelivery@1` returns `NOT_ATTEMPTED`, `KNOWN_SENT`, `KNOWN_REJECTED`, or `UNKNOWN`.

The intent follows `PENDING -> CLAIMED -> SUBMITTING -> KNOWN_SENT | KNOWN_REJECTED | UNKNOWN`, with durable claims/generations/leases/attempts. A crash after submission may have left an external effect, so recovery cannot reclaim that work as unsent.

## Enforced service and secret split

Provision a non-root, non-login host account and platform floor separately from Reach. `ApplicationDeploymentManifest@1` pins every role as a distinct rootless unit/container with exact image, command, ordering, mounts, namespaces, ceilings, and secret files; Scribe alone materializes it. Shared Pods, environment, credentials, or writable volumes cannot replace typed ports/inboxes/outboxes.

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

Each egress instance serves one provider/peer trust class with only its credential reference and short-lived occurrence grant. Core supplies payload and decision id, never Sigil or another bearer's credential.

Authenticate both ends of each local port using the manifest-pinned service Principals, credentials, audience, object/message types, expiry, replay fences, and receiver authorization. Discard identity supplied by the caller itself: loopback, shared bearers, DNS, and possession of a route establish no workload identity. This boundary must still reject cross-service impersonation when a non-owning service is compromised.

Firewall policy denies metadata/private-network egress except exact local service roads; later Tether needs another profile. This limits lateral movement without claiming resistance to root, operator-account, or VPS-control-plane compromise, which can expose all resident secrets and payloads.

## Public corpus contract

Reach judges source eligibility, interpretation, selection, and citations. Acquisition follows [Webcrawler](../../../adr/30-webcrawler.md#destination-and-data-boundary); a checkout or static site alone is no retrieval system.

Start acquisition from canonical HTTPS Git/static sources only. Refuse git/SSH/SCP/local/file origins, credential helpers, and ambient credentials. Bind the source to pinned paths, an operator-admitted commit or verified immutable release provenance, digests, builder/parser/index revisions, and file/byte/expansion/depth/work ceilings. A moving branch may reveal a candidate but cannot activate it.

Process that candidate without hooks, submodules, smudge/LFS, or content-directed network. Reject escaping symlinks, unsupported media, malformed encoding, and archive/parser bombs. Build the index offline and validate all staging before atomically activating the snapshot. If any stage fails, keep the previous snapshot.

Record the admitted source in `PublicCorpusSnapshot@1`, retaining source/revision/digests, accepted paths, tools, build receipt, activation, and freshness. Its passages remain attributed, instruction-fenced data. The snapshot's `fresh_until` is 24 hours after activation; after expiry, return `DEPENDENCY_UNAVAILABLE`. An explicitly historical question may instead use a separately admitted frozen historical source, with that revision displayed.

`CorpusEvidenceBundle@1` pins one snapshot, passage ids/digests, canonical URLs/sections, and retrieval/count/token/size limits. Only the bounded bundle can travel remotely. Missing, altered, or unbound citations refuse validation.

## Outbound A2A without an inbound edge

The first independent interoperability receipt pins one A2A 1.0 binding/adapter, enrolled peer, authentication, task, destination, and budgets. Advertised Agent Cards prove none of enrollment, authority, destination admission, or availability.

| Field | `reach.vps.public@1` A2A receipt |
| --- | --- |
| protocol | A2A `1.0`, HTTP+JSON binding, adapter and schema fixture digests pinned |
| peer | one pre-enrolled Principal, canonical HTTPS origin, Agent Card digest, server certificate identity, and task authorization named by the receipt |
| authentication | mutual TLS with distinct audience-bound client credential; no bearer in payload |
| task | `reach.public_corpus_answer@1`; one text query plus one `CorpusEvidenceBundle@1`; text/structured response only; files, artifact URLs, tools, teaching, and continuation refused |
| operations | non-blocking `POST /message:send` with `configuration.returnImmediately=true`, returning a Task, then `GET /tasks/{id}` only; a direct Message, stream, or push notification is outside this receipt |
| polling | every 2 seconds, at most 20 polls, 45-second absolute task deadline |
| ceilings | one task; 32 KiB request; 256 KiB response; eight evidence passages; 2,000-character query; profile-pinned token and spend ceilings |
| adoption | authenticated expected task/context identity, current peer authorization, first terminal, quarantine, schema/citation validation |

A2A 1.0 makes [Send Message idempotency optional](https://a2a-protocol.org/v1.0.0/specification/#331-idempotency); `messageId` alone does not prove deduplication. Before retrying an ambiguous initial POST, the receipt must admit the selected peer's guarantee that the exact same message and payload resolve to the original Task without duplicate work for that redelivery. Without that guarantee, preserve the uncertain task for reconciliation and do not resend. An admitted retry preserves the exact envelope and message/task identities; every physical attempt, including retries and polls, needs a fresh byte-time `EgressDecision` and consumes its transmission budget.

Replace each peer field with an observed independent endpoint; placeholders or same-process fakes prove conformance only. A model Portal is a separate E2E case under the same egress/attempt/quarantine/delivery law.

Commit the task/outbox before sending, then park in Durable Stasis while waiting. The baseline obtains updates through outbound response/polling and disables push callbacks. Authenticate and correlate each update against current authorization/revocation, and record the first authenticated protocol terminal. Even then, keep the returned content quarantined until validation and Composition adoption.

Preserve the distinction between `SUCCEEDED`, `REFUSED`, `FAILED`, `EXPIRED`, `REVOKED`, `CANCELLED`, and `LOST`. Silence alone establishes none of these outcomes and cannot authorize a blind repeat.

Map `TASK_STATE_COMPLETED`, `TASK_STATE_REJECTED`, `TASK_STATE_FAILED`, and `TASK_STATE_CANCELED` to their respective success/refusal/failure/cancellation. One-shot work refuses `TASK_STATE_INPUT_REQUIRED`/`TASK_STATE_AUTH_REQUIRED` without new credentials. Local deadline, current revocation, or irreconcilable loss settles expiry/revocation/loss with evidence.

| Profile | Exact boundary |
| --- | --- |
| **Callback-only client** | Veil may route a notification only to isolated Intercom ingress; it may update one existing outbound task after authentication, replay fencing, task/token correlation, current authorization, and durable admission. |
| **Full A2A server** | A distinct server profile needs Veil, Ward, Intercom durable inbox/outbox, Workers, quotas, and its own result path. A new peer task is not a Reach/Discord turn. |

An incoming peer task never creates a Discord delivery. Cards and task routes grant no foreign use of the bot identity.

## Destination and abuse boundary

Admit canonical HTTPS origin/port/path/purpose without ambient proxy or credentials. Reject loopback, private, link-local, multicast, unspecified, metadata, and mixed-resolution addresses. Pin the admitted address through connection; peer, TLS, SNI, and Host must match. Re-admit each redirect/new connection.

Before Core sees a return, the egress adapter bounds status/type, headers, wire/expanded bytes and ratio, chunks/count/size, stream/idle time, JSON depth/items, parsing/tokens, and total result. Violation closes response and returns dependency failure without further parsing.

Set limits on platform events per application/guild/channel/subject, as well as concurrency, evidence/results, and tokens/time/retries/spend. A later ingress profile must additionally bound pre-auth connections, headers/compressed/expanded bodies, signature work, per-IP/peer/route/global quotas, durable queues/streams, and CPU/memory/process/disk/connections. Apply those limits so overload cannot displace heartbeat, committed delivery, or recovery work.

## Retention and provider custody

These are maximums; shorter policy is allowed, longer retention needs a declared decision.

| Material | Maximum and retained form |
| --- | --- |
| raw Discord event/query | 24 hours after terminal; up to 7 days only while reconciliation is unresolved, then digest and minimum admission fields |
| caller/admission evidence | 30 days; partition, policy, decision and abuse facts without copied profile content |
| evidence bundle and every terminal turn | 30 days; structural terminal record plus exact selected public passages or their independently retrievable digests and refs |
| raw egress payload or quarantined return | 24 hours after terminal; up to 7 days for `INDETERMINATE`, then decision/result digests and receipts |
| delivery and external idempotency identities | 90 days; event/effect ids, payload digest, status, and Discord message id |
| edge address and coarse abuse log | 7 days, access-controlled and minimized |
| corpus snapshots | active plus previous generation; evidence retained with a turn remains separately bounded above |

Telemetry excludes raw prompts/passages/results, credentials, and pseudonym maps. Admit provider storage/training/region/subcontractor/deletion policy before egress; local deletion cannot erase its copies. Limits also cover replicas, exports, encrypted backups, VPS snapshots, journals, swap, and dumps. Disable raw payload/credential dumps/logs and encrypt or disable swap.

The manifest must choose a recovery policy: either disable backups and declare loss unrecoverable, or pin encrypted off-host backup/expiry/restore with an offline key. If Phylactery is lost, disable Reach until effects inside the idempotency horizon have been reconciled. Starting with an empty database proves nothing about old Discord/A2A effects. On decommission, destroy volumes and expire secondary copies.

## Restart, uncertainty, and compromise

On replay, return the committed admission/turn. A failed corpus refresh preserves the earlier snapshot with degraded freshness. Recover remote work according to what the attempt record proves: a proved pre-submit failure may create a new attempt/egress decision, while possible post-submit failure remains `INDETERMINATE` until reconciliation. Parked A2A survives through protocol identities/checkpoints, never SDK objects. An unknown Discord delivery needs independent evidence before any retry.

For a service compromise, revoke leases/credentials, quarantine output, mark tasks/deliveries as tainted, and preserve bounded secret-free correlation. A root/operator/VPS-control-plane compromise requires rebuilding the body. Stop Reach and withdraw routes/callback DNS/cards, then revoke every potentially exposed Discord/provider/A2A/Tether/Veil/ACME/operator/source/deployment credential. Mark and reconcile uncertain external effects before destroying and reprovisioning from a trusted pinned image.

Restore only independently verified non-secret records. Rebuild the corpus, issue disjoint credentials, and enroll from zero authority before returning the body to service.

## Acceptance gates

Tests cover identity/digest collision, replay/partition isolation, Cut/egress binding, destination/redirect rebinding, malicious corpus/path/parser and compressed/chunked/deep return cases, timeout at each commit, quarantine/revocation, restart/overload, and nonce/claim expiry without duplication.

To assess the deployed body, the live-host receipt must identify source/images, OS/systemd/Podman/users, manifest/compiler, units/mounts, local mTLS Principals/credentials and impersonation refusals, network/firewall/DNS, secrets/resources, corpus, Mirror/Ward, and external adapters. It must also account for reboot, secret isolation, backup/restore or loss, reconciliation, shutdown, and clean rebuild/rotation. Only the evidence owners and State can use that evidence to promote delivery.

[Deployment matrix](index.md) · [Reach turn](../turn.md)
