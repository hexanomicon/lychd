---
title: Turn
icon: material/message-reply-outline
---

# :material-message-reply-outline: Turn

1. Authenticate the Gateway session; verify application, guild, channel, trigger, size, and adapter
   revision; deduplicate the provider event before cognition.
2. Resolve guest or enrolled caller authority and assemble a privacy-cut Context for this person
   and place only.
3. Run one exact Pattern: direct mention, deliberate `/reach ask`, or bounded presence under
   audience, quiet-hour, budget, cooldown, expiry, and dedupe policy.
4. Commit `ReachTurn@1` with Habitat, trigger, caller evidence, Persona and AgentSpec revisions,
   Context references, Run correlation, output class, and terminal state.
5. Project at most one `ReachDelivery@1`, binding target, effect identity, payload digest, platform
   result, and known or unknown delivery. End the awakening.

`/reach link` and `/reach unlink` belong to Ward. `/reach status` projects only caller-owned or
explicitly shared committed state. A message, button, reaction, role, or fluent “yes” cannot settle
consent or authorize deployment, repository mutation, host lifecycle, destructive deletion,
secrets, authority changes, or publication.

Gateway replay deduplicates by external event id. After an interaction token expires, status may
retrieve committed state; work is never rerun to manufacture a reply. Disconnect after send leaves
delivery **unknown** until reconciled by effect identity and payload digest.

Compromise revokes the adapter Principal, rotates the bot token, closes the Gateway session, marks
pending deliveries uncertain, preserves secret-free evidence, and restarts from zero authority.

## Proving one turn

Use deterministic Gateway fixtures and a fake text capability. Prove one mention and one command,
zero records for ambient messages, guest/member authority separation, refusal of consequential
requests, restart-safe dedupe, quiet-hour budgets, revocation, and no duplicate after uncertain
delivery. No live Discord or live model enters the proof.

References: [Mirror](../../adr/32-identity.md) · [Ward](../../adr/38-iam.md) ·
[Context](../../adr/21-context.md#privatization-and-the-privacy-cut) ·
[Discord Gateway](https://docs.discord.com/developers/events/gateway)
