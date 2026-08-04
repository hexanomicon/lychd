---
title: Reach
icon: material/hand-back-right-outline
---

# :material-hand-back-right-outline: Reach

> _The Lich may inhabit more than one world. No world receives the keys to all the others._

**Candidate question:** can one revision-pinned LychD Persona inhabit an external social place,
hold bounded conversation, and accept differently authorized summons without turning a platform
account, role, token, or fluent sentence into LychD authority?

| Local maturity | Identity | Pattern catalogue | First Habitat |
| --- | --- | --- | --- |
| **Unaccepted candidate study; architecture and delivery remain unchanged** | `reach.discord` revision `1` | `reach.external_converse@1`, `reach.external_summon@1`, `reach.external_presence@1` | private Discord guild **The Necropolis** |

Reach is the Lich's hand into a social world. In Discord it appears as a resident application that
can be mentioned, can answer a slash command, and may speak because one admitted internal event
gave it reason. It is not a general moderator, ambient surveillance bot, remote shell, or Discord
account wearing a powerful local token.

## One Lich, more than one world

[Blockworld Inhabitant](blockworld-inhabitant.md) gives an Agent finite awakenings in a persistent
Minecraft world. Reach applies the same discipline to a social world: the platform persists
messages and membership, while LychD persists attributable purpose, admitted memory, authority,
Runs, and effects. Once [Mirror](../adr/32-identity.md) is delivered, both Compositions may bind the
same exact Persona revision. They do not become one endless session.

| Continuity | Owner and boundary |
| --- | --- |
| voice, commitments, relationships, and Persona revision | Mirror |
| Minecraft world, inventory, and embodiment state | Blockworld Inhabitant and its world custody |
| Discord place, message, member, and delivery state | Discord and the Reach adapter |
| eligible cross-world memory | explicit Phylactery relation with source, audience, purpose, retention, and revocation |
| caller identity and authority | [Ward](../adr/38-iam.md) per Principal and effect |
| one turn or action | one finite Invocation and Run |

A Discord conversation does not silently enter Minecraft memory; a block, sign, or Minecraft chat
does not silently enter Discord Context. Shared Persona is not shared authority, shared Context, or
proof of continuous consciousness. Every crossing names the source world, destination audience,
admitting Principal, policy revision, and retained provenance.

Mirror remains **Designed**. The current fixed `The First One` AgentSpec is not proof that the same
Lich already persists across worlds. [State of Work](../state-of-the-work.md#mirror-identity) owns
that delivery boundary.

## The External Habitat contract

Discord is the reference profile, not the constitutional API. A later Matrix, Slack, Telegram,
forum, game-chat, or other adapter may implement the same Habitat obligations only when it declares
its own identity evidence, custody, permissions, delivery semantics, compromise ceiling, and
recovery law. Similar text boxes do not make platforms interchangeable.

`HabitatEnvelope@1` normalizes one admitted external event:

- provider and adapter-profile revision;
- external habitat, place, subject, event, and optional parent identities;
- trigger kind: direct mention, application command, or admitted internal projection;
- bounded text and declared attachment absence;
- platform timestamp, receipt cursor, privacy/custody label, and correlation; and
- raw-evidence digest plus the authentication evidence the adapter actually observed.

Every Habitat adapter must:

1. authenticate its platform session or signed envelope and isolate provider credentials;
2. allowlist exact habitats, places, event kinds, and response effects;
3. deduplicate the provider event before cognition or effect;
4. preserve platform identity only as external evidence for Ward enrollment;
5. drop unadmitted ambient content before Context or durable storage;
6. produce one exact delivery receipt or an honest unknown/non-completion;
7. expose health, policy drift, revocation, rotation, and recovery state; and
8. declare the data and effects obtainable if the platform, account, token, or adapter is lost.

An Extension may contribute a Discord adapter, but [Extension law](../adr/05-extensions.md) does not
make that adapter a Pattern, Persona, Principal, memory owner, or source of authority. Reach owns
the application purpose and records; the adapter remains replaceable machinery.

## Discord reference inhabitant

The first profile uses one private guild named **The Necropolis**, one text channel named
`the-reach`, one server-installed bot application named **Reach**, and an outbound Gateway
connection. Outbound Gateway avoids publishing the current loopback-only Vessel through an ad hoc
HTTP endpoint. It introduces a long-lived bot token and persistent connection, so that token and
adapter process receive their own narrow compromise boundary.

| Discord surface | Revision `1` contract |
| --- | --- |
| installation | `GUILD_INSTALL` with `bot` and `applications.commands` |
| bot permissions | `View Channel` and `Send Messages` only in `the-reach` |
| forbidden permissions | `Administrator`, history, member/role/channel/webhook management, attachments, mass mentions, moderation, voice, and every unrelated channel |
| Gateway intents | `GUILDS` and `GUILD_MESSAGES` |
| privileged intents | no `MESSAGE_CONTENT`, `GUILD_MEMBERS`, or `GUILD_PRESENCES` |
| conversational ingress | current message only when Reach is directly mentioned in `the-reach` |
| deliberate work | guild-scoped `/reach` commands delivered on the same Gateway session |
| response | bounded channel reply or ephemeral command response; always `allowed_mentions.parse: []` |
| ambient history | none; non-mention message content is discarded before persistence |

Discord documents direct mentions as an exception to the privileged Message Content restriction:
an app without that intent can receive content in messages where it is mentioned. The profile
therefore needs no permission to read history and no right to consume ordinary channel chatter.
See the official [Gateway intent contract](https://docs.discord.com/developers/events/gateway) and
[message contract](https://docs.discord.com/developers/resources/message).

Online status proves only a healthy Gateway session. It is not proof that a Mind is continuously
running. A mention, slash command, or admitted presence event creates one finite awakening; the
model lease ends when that turn or Run ends.

## Three Patterns, one resident

### `reach.external_converse@1`

A member writes `@Reach <bounded text>` in `the-reach`. The adapter admits only that current
message, its platform attribution, and explicitly eligible LychD Context. It never fetches nearby
history to manufacture continuity. The Pattern binds the configured Persona revision, produces one
channel-shareable response, commits attribution and correlation, and ends.

An unlinked guild member may enter only a policy-declared guest conversation with no Principal-owned
records, private memory, tools, or external effects. An enrolled member may receive Context and
memory explicitly shared with that Principal or place. A public channel reply never reveals
Magus-private memory merely because the Magus authored the mention.

### `reach.external_summon@1`

The slash-command surface carries deliberate work rather than social inference:

| Command | Office | Authority and output |
| --- | --- | --- |
| `/reach link code:<opaque>` | Ward enrollment protocol, not a Pattern | one ephemeral success or refusal; never echoes the code or Grants |
| `/reach ask prompt:<text>` | admits `reach.external_summon@1` | one bounded Invocation; ephemeral correlation and result or non-completion |
| `/reach status run:<correlation>` | authorized projection, not a replay | only caller-owned or explicitly shared state |
| `/reach unlink` | Ward revocation protocol | revokes the binding without pretending to erase platform custody |

Revision `1` caps mention and command text at 2,000 characters and admits no attachments,
autocomplete, message target, modal, button, reaction, or emoji approval. The first summon asks for
one text capability. Broader typed Intents may be added only as new Pattern revisions with their
own objects, Grants, budgets, effects, and proofs.

### `reach.external_presence@1`

Presence is an admitted outbound act, not random model restlessness. A versioned policy may turn one
internal event—such as an attributable completed project milestone—or one bounded schedule into at
most one message in one configured place. It declares reason, audience, quiet hours, daily budget,
cooldown, content class, expiry, and deduplication key. It cannot read ambient Discord conversation
to decide that it “feels like speaking.”

The Pattern is disabled by default in the first proof. Enabling it requires delivery receipts,
quiet-hour and budget tests, restart deduplication, and a visible operator switch. Silence after
policy expiry is correct behavior.

## Principals, roles, and the Magus

An authenticated LychD Principal initiates enrollment. Ward issues a short-lived, single-use,
audience-bound code and stores only its verifier. `/reach link` atomically binds
`(discord, application_id, guild_id, user_id)` to that Principal. Reuse, expiry, wrong guild,
conflicting enrollment, or revoked Principal fails closed. Recovery begins from an authenticated
LychD surface; Discord cannot repair its own identity binding.

Discord membership and roles can reduce command visibility and contribute current evidence. They
never create a Principal, mint a Sigil, or become an object Grant. Every protected admission and
effect rechecks the local binding and current Ward policy.

| Caller posture | Maximum candidate authority |
| --- | --- |
| unlinked member | guest conversation over channel-shareable Context; no private records or tools |
| enrolled member | bounded conversation, own Run status, and explicitly granted safe Intents |
| enrolled collaborator | named project/object Grants; no authority inherited from a Discord role |
| Magus | broader but still named Grants, eligible private namespaces, and proposal of consequential effects |
| any caller at a live-only effect | durable park and step-up at an authenticated LychD surface |

The effective action is always narrower than every participating boundary:

```text
Discord channel and bot permissions
∩ current external-subject enrollment
∩ caller's object-specific Ward Grant
∩ current Reach service admission
∩ Pattern capability and budget
∩ current effect, consent, and privacy policy
```

If a member says “deploy it,” Reach refuses unless that exact Principal has an admitted Pattern and
object Grant—and revision `1` has neither. If the Magus says the same, broader identity may admit a
proposal, but deployment, repository mutation, host lifecycle, destructive deletion, secrets,
authority changes, and public publication still park for step-up and exact
[HitL](../adr/25-hitl.md) judgment. A Discord message, role, button, reaction, or fluent “yes” never
settles consent. Approval itself still is not a Grant; the effect owner rechecks current authority
on resume.

Remote IAM remains **Designed**. The current fixed loopback `magus:*` Sigil cannot authenticate a
Discord caller and must never cross into this adapter. [State of
Work](../state-of-the-work.md#local-sigil-authority) owns that boundary.

## The compromise ceiling

Everything deliberately projected into an external Habitat is assumed obtainable by that platform
and by an attacker who fully compromises it. Safety comes from making that set finite—not from
calling a server private.

```text
maximum external compromise
⊆ projected data
 ∪ platform permissions
 ∪ Reach service-admission ceiling
 ∪ still-valid remote caller Grants
```

| Lost boundary | Maximum intended consequence |
| --- | --- |
| Discord platform or linked account | Discord-held messages and metadata; the account's still-valid low-risk remote Grants until local revocation |
| bot token | impersonate Reach and observe whatever future events, metadata, and message content its configured Discord intents and channel permissions expose in admitted places; no Discord administration or LychD authority from the token itself |
| Discord adapter process | bot-token power plus the adapter service Principal's narrow admission/status/reply API; no database, host, model-provider, repository, or universal Intent credential |
| one channel | content explicitly projected there and channel-shareable LychD memory; no other place or private namespace |
| one reply token or effect identity | that bounded response only; no second Run or general posting authority |

The bot token and internal adapter credential are separate secrets. Neither enters prompts, message
content, logs, Run state, checkpoints, receipts, or model-visible errors. The adapter runs without
repository mounts, database credentials, host lifecycle access, provider keys, or broad internal
network reach. Suspected compromise revokes the service Principal, rotates the bot token, closes
the Gateway session, marks pending delivery uncertain, preserves secret-free evidence, and starts
again from zero authority.

Compromise containment cannot rescue content voluntarily pasted into Discord. Credentials, private
keys, bearer tokens, personal data, full host logs, and unreviewed secret-bearing source never enter
Reach Context or output. Every Discord-bound response is explicit external egress governed by
[Context](../adr/21-context.md#privatization-and-the-privacy-cut) and
[Security](../adr/09-security.md). Channel privacy and ephemeral responses narrow audience; they do
not create text E2EE, prove deletion, or remove Discord custody.

## Evidence discipline

Discord is a replaceable external projection, not a confidential or canonical store. Its
[privacy policy](https://discord.com/privacy) and
[retention notice](https://support.discord.com/hc/en-us/articles/5431812448791-How-long-Discord-keeps-your-information)
govern Discord custody independently of LychD retention. Deleting one copy does not rewrite or
erase the other.

The documented 2025 compromise of a Discord support provider is supply-chain evidence, not proof
that ordinary private-server messages were breached. A historical investor headline likewise is
not evidence that Tencent, China, or another investor controls Discord data. Reach records no
“Chinese leak” claim without an identified data flow and authoritative evidence, and it does not
claim that every private message trains a general model. The threat model rests on observable
platform custody, non-E2EE text, account and credential compromise, retained data, and revocable
API access—not nationality or rumor. See Discord's
[incident statement](https://discord.com/press-releases/update-on-security-incident-involving-third-party-customer-service)
and [company information](https://discord.com/company-information).

## Owners and records

| Concern | Owner |
| --- | --- |
| Habitat purpose, Pattern catalogue, policy, and domain records | Reach |
| Persona revision, cross-world identity binding, and eligible identity memory | [Mirror](../adr/32-identity.md) |
| Principal enrollment, Sigil, Grants, and revocation | [Ward / IAM](../adr/38-iam.md) |
| immutable Pattern, Invocation, and route admission | [Weaver](../adr/28-workflow.md) |
| bounded prompt and history assembly | [Context](../adr/21-context.md) |
| cognition, capability selection, readiness, and delivery | Agent, Dispatcher, Orchestrator, and Workers |
| Run state, receipts, memories, and durable Habitat records | Run ledger and Phylactery |
| Discord session, event normalization, and message delivery | Discord Gateway adapter |
| bearer secrets, egress, containment, and compromise response | [Security](../adr/09-security.md) |

`ReachTurn@1` records trigger and Habitat identities, external subject and resolved Principal when
present, Persona/AgentSpec/Posture revisions, admitted Context references, producer attribution,
Run correlation, output class, and terminal state. `ReachDelivery@1` separately records target,
effect id, payload digest, platform result, and known/unknown delivery state. Platform message text
is not duplicated into durable storage merely because Discord already holds it; retention follows
the Composition's declared purpose and evidence need.

## Delivery, rupture, and return

Gateway sequence and session state are volatile bridge state. An event becomes durable only after
allowlist, content-shape, subject, policy, and deduplication checks. On disconnect, the adapter may
resume the exact Discord session when its protocol permits, but every replayed event still resolves
through the same external event id. A reconnect never becomes a second Invocation.

Slash interactions require an initial response within three seconds and use an interaction token
valid for fifteen minutes. The adapter returns an ephemeral defer or correlation immediately; that
means only “received.” When a result commits inside the window, it edits the original response once.
After expiry, `/reach status` may retrieve authorized committed state; the adapter never reruns the
summon to manufacture a reply. See Discord's
[interaction response contract](https://docs.discord.com/developers/interactions/receiving-and-responding).

Mention and presence replies carry an exact effect identity. A committed turn outranks its Discord
projection. Disconnect after send but before acknowledgement triggers effect reconciliation; an
unknown message is never blindly resent. Edited or deleted external input cannot rewrite the
already admitted envelope. A new edit may become a new explicitly correlated event only in a later
Pattern revision.

Enrollment/revocation, bot-token rotation, Discord permission or intent drift, Gateway resume,
duplicate and out-of-order events, oversize input, adapter restart, rate limit, late result,
expired interaction token, quiet-hour change, and unknown delivery are explicit lifecycle cases.
Wrong application, guild, channel, event kind, command revision, or Principal fails closed.
Discord API, adapter profile, Habitat envelope, enrollment mapping, Pattern, Persona, result, and
delivery schemas version independently.

## Smallest proving slice

The first proof uses deterministic Gateway and interaction fixtures plus a fake text capability,
not live Discord or a live model. It establishes:

- a direct mention in `the-reach` admits one conversation turn, while ordinary ambient messages,
  history, attachments, other channels, DMs, and bot-authored loops leave no Context or record;
- identical content from an unlinked member, enrolled member, collaborator, and Magus produces
  different authorized Context and options without trusting Discord roles as Grants;
- a member's consequential request refuses, while the Magus receives at most a parked exact
  proposal and never a Discord-settled effect;
- duplicate/replayed events, reconnect, restart, rate limits, mention injection, revocation, and
  uncertain delivery create no duplicate cognition or message;
- an admitted presence event obeys audience, reason, quiet hours, budget, expiry, and deduplication;
  and
- stolen-token and compromised-adapter simulations cannot read history, reach another channel,
  access private memory, call an unrelated Pattern, or cross the current Reach service admission.

A later live receipt requires delivered remote IAM and Mirror; one private guild, configured
channel and non-administrator bot; the exact permissions and intents above; one enrolled member and
the Magus; one local text capability; isolated adapter credentials; and no attachments, DMs,
history, ambient Message Content, remote model-provider egress, or consequential effect. Until that
evidence exists, Reach remains a candidate design for a bounded social inhabitant—not a claim that
the Lich already lives in Discord.

Return to the [Composition Portfolio](index.md).
