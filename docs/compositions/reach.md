---
title: Reach
icon: material/hand-back-right-outline
---

# :material-hand-back-right-outline: Reach

Reach lets one revision-pinned Persona answer in an external social place without handing that
place the authority of LychD. A mention, command, or admitted presence event creates one finite
awakening; the platform account never becomes the Lich.

!!! note "Current material"
    Reach is a Native Reference Composition, not a live Discord resident today. No Reach Pattern,
    Discord adapter, Habitat ledger, remote Principal binding, or external delivery effect is
    registered. Mirror, remote IAM, and the required transport boundaries remain Designed.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `reach.discord` revision `1` |
| **Principal Patterns** | `reach.external_converse@1`, `reach.external_summon@1`, `reach.external_presence@1` |
| **Application begins with** | one allowlisted mention, guild command, or policy-admitted internal event |
| **Application can return** | `ReachTurn@1` and, when a reply is attempted, `ReachDelivery@1` |
| **Application stops before** | moderation, ambient surveillance, attachments, DMs, remote shell, deployment, or Discord-settled consent |

Reach owns Habitat purpose, Pattern policy, turn records, and delivery records. Mirror owns
Persona revision; Ward owns Principal enrollment, Sigils, Grants, and revocation; Context owns the
privacy cut; the Discord adapter owns session, event normalization, and message delivery.

## The reference Habitat

Revision `1` uses a private guild named **The Necropolis**, one channel named `the-reach`, and a
server-installed bot application named **Reach**. Its outbound Gateway session avoids exposing the
loopback Vessel through an ad hoc public endpoint.

| Discord surface | Exact profile |
| --- | --- |
| installation | `GUILD_INSTALL` with `bot` and `applications.commands` |
| permissions | `View Channel` and `Send Messages` in `the-reach` only; never `Administrator`, management, moderation, attachments, mass mentions, or voice |
| Gateway intents | `GUILDS` and `GUILD_MESSAGES`; no privileged intents |
| conversation | current message only when Reach is directly mentioned in `the-reach` |
| deliberate work | guild-scoped `/reach` commands on the same Gateway session |
| reply | bounded channel response or ephemeral command response with `allowed_mentions.parse: []` |
| ambient history | none; non-mention content is discarded before persistence |

## Event to bounded reply

1. **Admit one event.** Authenticate the Gateway session, verify application, guild, channel,
   trigger kind, size, and adapter revision, then deduplicate the provider event before cognition.
2. **Resolve the caller.** Platform identity remains evidence only. Ward maps an enrolled subject
   to a local Principal and rechecks current object Grants; an unlinked member receives guest
   conversation with no private records, tools, or effects.
3. **Assemble a privacy-cut Context.** Include only material explicitly eligible for this Principal
   and place. Nearby Discord history, Minecraft chat, Magus-private memory, credentials, and
   unrelated world state do not enter the turn.
4. **Perform one Pattern.** A direct mention runs `reach.external_converse@1`; `/reach ask` runs
   `reach.external_summon@1`; an admitted schedule or internal event may run
   `reach.external_presence@1` under audience, quiet-hour, budget, cooldown, expiry, and dedupe rules.
5. **Commit the turn.** `ReachTurn@1` records Habitat identities, trigger, external subject,
   resolved Principal when present, Persona and AgentSpec revisions, Context references, producer,
   Run correlation, output class, and terminal state.
6. **Project one bounded reply.** `ReachDelivery@1` binds target, effect id, payload digest,
   platform result, and known or unknown delivery. A committed turn remains authoritative even if
   Discord never receives its projection.
7. **End the awakening.** Model residency and Gateway presence are separate; an online bot does
   not prove that a Mind runs continuously.

`/reach link` and `/reach unlink` are Ward protocols, not Patterns. Enrollment uses a short-lived,
single-use, audience-bound code and atomically binds
`(discord, application_id, guild_id, user_id)` to a Principal. `/reach status` projects only
caller-owned or explicitly shared committed state; it never replays expired work.

## Cross-world continuity

| Continuity | Owner |
| --- | --- |
| voice, commitments, relationships, and Persona revision | Mirror |
| Discord place, event, member, and delivery state | Discord and the Reach adapter |
| eligible cross-world memory | explicit Phylactery relation with source, audience, purpose, retention, and revocation |
| caller identity and authority | Ward per Principal, object, Pattern, and effect |
| one admitted turn | Invocation, Run ledger, `ReachTurn@1`, and optional `ReachDelivery@1` |

The same Persona may later appear through [Blockworld Inhabitant](blockworld-inhabitant.md), but
identity continuity carries no shared Context, authority, or endless session. Every crossing names
its source world, destination audience, admitting Principal, policy revision, and provenance.

## Authority, custody, and recovery

Discord roles may narrow command visibility; they never create a Principal or Grant. Guest,
enrolled member, collaborator, and Magus authority all remain bounded by local object Grants and
the current Pattern. Deployment, repository mutation, host lifecycle, destructive deletion,
secrets, authority changes, and public publication park for authenticated LychD step-up. A message,
button, reaction, role, or fluent “yes” cannot settle consent.

Everything deliberately projected to Discord is considered obtainable by Discord or an attacker
who compromises it. Text is not end-to-end encrypted; channel privacy and ephemeral replies only
narrow the audience. Bot and adapter credentials are separate, never enter prompts or durable
records, and grant no database, repository, host, provider, or universal Intent access. The
adapter runs without those mounts or credentials.

Reach does not duplicate Discord message text locally merely because Discord already stores it;
local retention follows the declared purpose and evidence need. Export or deletion can govern the
local turn, delivery, and derived records, but cannot erase Discord-held messages or metadata.

Gateway reconnect and replay deduplicate by the external event id before creating an Invocation.
Slash interactions receive an immediate defer or correlation; after the interaction token expires,
authorized `/reach status` may retrieve committed state, but the work is never rerun to manufacture
a reply. A disconnect after send leaves delivery **unknown** until reconciled by effect identity
and payload digest; blind resend is refused.

Suspected compromise revokes the adapter service Principal, rotates the bot token, closes the
Gateway session, marks pending deliveries uncertain, preserves secret-free evidence, and restarts
from zero authority. Wrong application, guild, channel, event kind, command revision, Principal,
permission profile, or intent profile fails closed.

## Proving Habitat

Use deterministic Gateway and interaction fixtures with a fake text capability. Prove one admitted
mention and one command, zero records for ambient messages or other places, distinct guest/member/
collaborator/Magus authority, refusal of consequential requests, restart-safe deduplication,
quiet-hour and presence budgets, revocation, and no duplicate message after uncertain delivery.
Simulated token and adapter compromise must not reach history, another channel, private memory, an
unrelated Pattern, or authority beyond the Reach service admission. No live Discord or live model
belongs in this proof.

Related: [Mirror](../adr/32-identity.md) · [Ward / IAM](../adr/38-iam.md) ·
[Context](../adr/21-context.md#privatization-and-the-privacy-cut) ·
[Security](../adr/09-security.md) · [Workflow](../adr/28-workflow.md) ·
[Discord Gateway](https://docs.discord.com/developers/events/gateway) ·
[Discord interactions](https://docs.discord.com/developers/interactions/receiving-and-responding) ·
[State of Work](../state-of-the-work.md#mirror-identity) · [Composition portfolio](index.md)
