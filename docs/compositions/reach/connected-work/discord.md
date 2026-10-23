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

Receive both mentions and interactions over an outbound Gateway for the first deployment road.
Gateway resumes use session id, resume URL and sequence, but can fail; record an explicit gap
rather than promise complete history. Deduplicate by application/connection plus interaction or
message identity and content version; session sequence is transport evidence, not a replacement
for object identity. Commit admitted work before advancing its processing checkpoint. Discard
non-trigger content before persistence, and ignore self/bot/webhook loops under explicit policy.
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

[Accounts and updates](accounts.md) · [Acceptance and delivery](delivery.md)
