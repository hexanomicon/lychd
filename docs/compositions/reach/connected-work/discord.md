---
title: Discord connection
icon: fontawesome/brands/discord
---

# :fontawesome-brands-discord: Discord connection

A server administrator installs Reach, selects allowed text channels, and permits slash commands
and direct bot mentions. One admitted question can yield one response under the selected Persona.
The visible speaker is the bot, not an automated ordinary user account.

The proposed `reach.discord.correspondence@1` profile belongs to the
[successor study](index.md). The accepted [Discord Habitat](../habitat.md), public deployment
profiles and historical `reach.discord@1` remain separately pinned.

## Installation and access

Use a guild-installed application with `bot` and `applications.commands`; the installing member
needs `MANAGE_GUILD`. A user install supports commands but does not replace guild event reception.
A publisher-operated app offers one install link. A customer-owned app requires its own Developer
Portal registration and token. [Installation contexts](https://docs.discord.com/developers/quick-start/getting-started#choosing-installation-contexts)

Bot tokens belong to the application, **not each guild installation**. One shared bot therefore
needs per-guild/channel policy and shares credential exposure across its installations. Never ship
that shared token in a customer's self-hosted package. [Bot authorization](https://docs.discord.com/developers/topics/oauth2#bot-users)

Request `View Channel` and `Send Messages` in selected channels. A referenced reply additionally
needs `Read Message History`; this does not authorize ambient history ingestion. Use `GUILDS` and
`GUILD_MESSAGES`, without privileged `MESSAGE_CONTENT`. Direct mentions are exempt from general
content suppression; arbitrary surrounding conversation is not. No administrator permission,
DMs, attachments, mass mentions, moderation or voice enter this first profile.
[Message permissions](https://docs.discord.com/developers/resources/message),
[content intent](https://docs.discord.com/developers/events/gateway#message-content-intent)

Application verification and privileged-intent review are separate provider processes. Their
thresholds have changed; the first profile avoids privileged intents and must recheck current
[verification](https://support-dev.discord.com/hc/en-us/articles/23926564536471-How-Do-I-Get-My-App-Verified)
and [intent-review rules](https://support-dev.discord.com/hc/en-us/articles/40281523410967-Changes-to-Privileged-Intent-Access-for-Discord-Apps)
before wider distribution.

## Intake, reply and interruption

The first deployment receives mentions and interactions over an outbound Gateway. On reconnect,
resume with the session id, resume URL and sequence. If resume fails, record the gap rather than
claiming complete history.

For each event, deduplicate by application/connection plus interaction or message identity and
content version. A session sequence describes transport order and cannot replace object identity.
Commit admitted work before advancing its processing checkpoint; discard non-trigger content before
persistence and apply explicit policy to ignore self/bot/webhook loops.
[Gateway resume](https://docs.discord.com/developers/events/gateway#resuming)

Interactions require an acknowledgement or deferral within **three seconds**, and their tokens
last **15 minutes**. Defer promptly without running cognition first. Commit known response identity
and token expiry; store the secret token only with its short-lived credential owner. Expired tokens
lead to local status or a separately authorized bot message, not another execution of the work.
[Interaction responses](https://docs.discord.com/developers/interactions/receiving-and-responding)

For normal messages, persist the exact response/target and deterministic nonce before send;
use `enforce_nonce` and retain the returned message id. Discord's uniqueness check covers an
unspecified recent interval, so it does not supply durable exactly-once sending. Gateway echo and
provider reads may reconcile `UNKNOWN`; otherwise keep uncertainty and block blind replay.
Use restrictive `allowed_mentions` on creates and edits and enforce the platform text limit.
[Create Message](https://docs.discord.com/developers/resources/message#create-message)

Honor dynamic route buckets, major-resource partitions and global limits, with `Retry-After` and
bounded backoff. Permission loss or an invalid token suspends the affected path rather than
spinning retries. [Rate limits](https://docs.discord.com/developers/topics/rate-limits)

## Commands and authority

The initial command set is `/reach ask`, `/reach status`, and Ward-owned link/unlink entry points.
Status is caller-owned or explicitly shared. Linking requires an independent authenticated Ward
flow; a guild role, slash command, reaction or ordinary “yes” cannot settle local native review or
broaden standing policy. Public guest answers remain an explicit restricted mode.

A later HTTP interaction profile must verify timestamp/raw-body Ed25519 signatures before intake,
protect against replay and answer provider validation requests. It needs an exact callback/ingress
manifest; selecting it replaces Gateway delivery of interactions, not Gateway reception of other
events. [Interaction verification](https://docs.discord.com/developers/interactions/overview#validating-security-request-headers)

Ordinary service updates preserve the app and installations. Command changes update definitions
through the API; wider bot permissions, channel access or privileged data require administrator
action or provider review as applicable. [Command updates](https://docs.discord.com/developers/interactions/application-commands#updating-and-deleting-a-command)

## Workflow interactions in Orb (Proposed)

This section extends the **candidate successor study**, not the delivered operator profile.
[Orb](../../../divination/altar/orb.md) should show a workflow's actual Discord intake and
external attempts: provider mark, incoming or outgoing direction, permitted channel detail and
recorded outcome. Reach contributes the meaning and static presentation metadata. Orb projects
it through its existing shared renderer and accessible evidence list. Loom continues to show the
declared score; it does not become the delivery feed.

The current [operator profile](../operator.md) has a separate, generation-local memory Run ledger
in its networkless worker. The ordinary Vessel's Orb reads its own ledger. Native reply formation,
a later Discord send and an owner-queued publication therefore have separate witnesses. Neither
a completed conversation Run nor a queue receipt proves that the main Orb observed a delivery.
The local publication queue remains an owner-supplied transport interface; it is no native outbox
or general workflow publication capability.

### Typed observations and presentation

Propose `ReachInteractionObservation@1` as a Composition-owned, immutable observation. These
are proposed record and port names, not existing Python types or a registered `ReachComposition`
service. Its native envelope carries:

| Field | Meaning and bound |
| --- | --- |
| Identity | Schema version, exact Composition/profile revision, opaque observation and owning application-record identities; the outer Run event supplies Run, event, sequence and timestamp. |
| Correlation | Exact Run and supplied station occurrence; admitted intake, communication, delivery intent and physical attempt references as applicable. References resolve under the same owner and connection. |
| Provider and direction | Closed `discord` provider key and `ingress` or `egress`; neither is inferred from station names. |
| Phase | `received`, `admitted`, `attempting`, `sent`, `rejected`, `expired`, `cancelled`, `unknown` or `reply`, with a validated direction/phase matrix. |
| Outcome | A fixed classification and optional bounded reason code, at most 64 ASCII characters. `sent` means provider acceptance, never human reading or agreement; `unknown` preserves possible transmission. |
| Place and audience | Exact qualified connection/conversation references and admission-time audience evidence in the protected Reach record. Default Orb detail contains no platform account, channel, user or role identities. |
| Receipt | Exact intake or delivery receipt reference, with no message body, prompt, token, raw error or canonical private-content hash in structural evidence. |

The phases describe observations at specific boundaries. `received` witnesses intake before
policy admission, while `admitted` follows a successful native gate. On egress, record `attempting`
only after committing a fenced physical-attempt claim and before transmission. A matching
transport receipt is then required for `sent`, `rejected` or `unknown`.

Use `reply` only when a received message passes the exact outstanding-question correlation and
admission. It says nothing about the truth of the answer's assertions. Later cancellation cannot
turn an earlier provider acceptance into an unsent message. If an observation is malformed, missing
or unsupported, leave it unclassified or unavailable instead of inferring a phase.

Reach's proposed pure presentation contribution maps validated records to a closed Discord icon,
an ingress/egress arrow, fixed phase/outcome text and optional authorized channel label. The browser
cannot supply an icon URL, HTML, phase or destination. Channel labels are bounded to 80 characters
and rendered as text; absent disclosure authority yields a generic channel label. Run-read access
alone does not disclose private channel names or resolve protected participant references.

Carry only the authorized decoration and opaque correlation in the Orb DTO. Show that same
decoration on the retained evidence row, selected-event inspector and folded graph record, using
shape, direction and text together and respecting reduced motion. These views must preserve Run
sequence, gaps and occurrence membership; playback shows only records through its supplied cursor.
A glow marks the observation itself. It cannot imply continuous connectivity or successful delivery,
and synthetic edges must not imply causality.

### Ask a named maintainer from Bridge (Proposed)

A Lich working in Bridge may propose one bounded question to explicitly designated knowledgeable
maintainers. Selection uses operator-maintained expertise and exact admitted participant mappings;
a Discord name, role, model guess or previous helpful reply cannot grant that authority.

To prepare the question, Reach retains its originating Run/occurrence, purpose, exact connection,
guild/channel/thread, recipient set, question bytes, disclosure class, expiry and finite answer
budget. Before sending, a current authenticated Sigil must authorize that audience and effect.
Bind the exact review or standing policy according to
[HitL](../../../adr/25-hitl.md#required-review-for-native-actions-designed), then recheck it against
current account, policy and revocation generations immediately before the physical attempt.
Preparing this question grants no ability to enqueue the operator's local publication queue.

The admitted workflow commits its delivery intent/outbox before the credential owner sends. It
then retains the outstanding question in a declared durable wait and releases model/worker leases.
When an answer arrives, match its selected connection, exact channel/thread and sent message
reference, admitted responder, deadline and unconsumed question generation. Specify refusal or
revision semantics for duplicate, late, edited, wrong-person and wrong-thread returns; Gateway
replay cannot consume the answer budget twice.

Even a matching Discord answer remains evidence. It is neither a Consent verdict nor a peer task,
and it cannot instruct an unrelated Run to resume.

Give the exact waiting work the accepted reply as bounded, attributed, hostile source material.
Preserve its source identity and permitted audience through Context assembly, and recheck current
Sigil and disclosure during native re-admission before resuming. Acceptance does not automatically
turn the reply into Memory, a teaching operation or authority to publish elsewhere.

If the original send remains unknown, retain that uncertainty and reconcile it without asking
another automatic question. An unanswered question, model confidence or the contents of a reply
cannot start a follow-up loop.

### Implementation order and falsifying checks

1. **Close native custody first.** Refine this successor's existing intake, communication, outbox
   and receipt contracts through [the delivery plan](delivery.md). Define the typed observation
   and a host-enrolled intake/receipt port with current authority and exact correlation. A shared
   native ledger or an authenticated, deduplicated handoff into its owner must exist before the
   ordinary Orb can observe an operator worker. Discord credentials remain exclusively at the
   transport edge; filesystem queue/journal scans are not that port.
2. **Emit only actual observations.** Reach owns the bounded validator and pure presentation
   contribution, proposed under `src/lychd/compositions/reach/`. Its workflow producers can use
   `WorkflowServices.events`; the Run event schema/emitter is in
   `src/lychd/domain/cortex/events.py`. Choose a typed semantic event contract before adding an
   event kind; do not disguise interactions as fabricated station traversal or raw LOG messages.
   Native intake and committed outbox/attempt owners emit their own observations. A replayed
   receipt retains one observation identity, and an observer failure cannot decide Run truth.
3. **Project through the existing read seam.** Add a bounded authorized decoration to
   `EvidenceItem` in `src/lychd/domain/web/contracts.py`. Enrich it through the exact Reach read port
   at `src/lychd/domain/web/orb.py` and `src/lychd/interface/web/orb.py`, following the existing
   protected Composition projection pattern. Snapshot and retained SSE must share validation,
   recheck disclosure after awaited reads, clear revoked metadata and leave capture limits visible.
   Reading Orb never creates an event or changes an outbox entry.
4. **Render the supplied meaning.** Regenerate OpenAPI/client types. Extend the closed runtime
   decoder in `clients/web/src/lib/orb/live.ts`, ordinary projections in
   `clients/web/src/lib/graph/orb.ts` and `graph/model.ts`, and the shared graph adapter plus Orb
   row/inspector. Reach supplies static provider semantics; Orb owns presentation, selection and
   folding. No renderer state, station name or terminal Run status manufactures an interaction.
5. **Prove the question lifecycle separately.** Add inert-port and disposable-database fixtures
   for exact review, audience and expiry, crash before/after submission, racing claims, revoked
   authority, unknown transmission and duplicate/late replies. Prove one reply resumes only its
   owning wait, no scarce lease survives waiting, and no provider body enters broad evidence.
   Only then qualify the Discord transport with an explicitly authorized live question.

The first projection proof needs retained ingress, provider-accepted egress and unknown-attempt
fixtures plus forged owner/reference, unsupported version, overlong label, private-name leakage,
revocation-during-read, duplicate receipt, pagination/reconnect and playback cases. Extend the
existing `tests/web/test_orb.py`, Reach composition/transport tests,
`clients/web/src/lib/orb/live.test.ts`, `graph/orb.test.ts` and Orb component tests. Run focused
Python checks through the source-bound OCI harness, then `make frontend-check` and
`make frontend-build`; complete the required Svelte documentation/autofixer workflow before any
Svelte edit. Published documentation changes also require a clean Zensical build. These are
implementation gates, not evidence that this candidate or its backend ports are delivered.

[Chat](../chat.md) · [Accounts and updates](accounts.md) · [Acceptance and delivery](delivery.md)
