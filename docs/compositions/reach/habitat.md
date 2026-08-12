---
title: Habitat
icon: material/account-group-outline
---

# :material-account-group-outline: Habitat

This page owns Reach's social Habitat, first manifested as **The Necropolis**. It is related by
sovereignty, but not identical, to the designed [Necropolis A2A
topology](../../adr/26-a2a.md#legion-and-necropolis): joining the guild never enrolls a
peer, trusts a foreign node, creates a Principal, or grants LychD authority.

Revision one manifests the Habitat as one private Discord guild, **The Necropolis**, one channel, `the-reach`, and a
server-installed application named **Reach**. The outbound Gateway session avoids exposing the
loopback Vessel through an ad hoc public endpoint.

The bot receives only `View Channel` and `Send Messages` there, with `GUILDS` and
`GUILD_MESSAGES`; it receives no administrator, moderation, attachment, mass-mention, voice, or
privileged intent. Non-mention content is discarded before persistence. Replies disable automatic
mentions.

Platform identity is evidence, not local authority. Ward may map one enrolled subject to a
Principal and current object grants only when the selected adapter/profile supplies its admitted
proof; an unlinked member receives guest conversation with no private records, tools, or effects.
Discord roles may narrow visibility but never create a Principal, grant, or consent decision. In
the VPS-edge/home-core profile, relayed Gateway identity is forgeable by a compromised edge and is
therefore guest/public-only unless the human independently proves identity directly to home Ward.

Mirror retains Persona lineage. Discord and its adapter retain place, member, event, session, and
delivery state. A local turn records only purpose-limited material. The same Persona may later be
projected through [Avatar](../avatar/index.md) into this Reach Habitat, a
[Blockworld](../blockworld/index.md) inhabitant, or a [Spectre](../spectre/index.md) VR Habitat, but
that continuity carries no shared Context, authority, or endless session. An Avatar presence
cannot make Discord history private or grant the next turn.

Everything projected to Discord is obtainable by Discord or an attacker who compromises it.
Channel privacy and ephemeral replies narrow audience; they are not end-to-end encryption.

Discord is the first Habitat, not the permanent definition of the community. A later
forum, Reach surface, or self-hosted commons must preserve the same identity, privacy,
admission, and authority boundaries rather than inherit trust from the name.

The docs-aware, operator-controlled [deployment profiles](deployments/index.md) choose one durable
body: home-only, a non-authoritative VPS Discord edge with home authority, or an independent
standalone VPS. None inherits private continuity merely from Discord or network placement.

Continue with [Turn](turn.md) for admission and recovery.
