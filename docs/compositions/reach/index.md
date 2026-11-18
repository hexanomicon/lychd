---
title: Reach
icon: material/hand-back-right-outline
---

# :material-hand-back-right-outline: Reach

Reach prepares correspondence for a selected external place. Its provider families share typed
requests and exact account/target policy while retaining different audiences, protocols and
operation limits.

## Provider families

| Family | Concrete providers | Shared concern |
| --- | --- | --- |
| [Email](email.md) | Gmail, Fastmail | Mail account, sender, recipients, subject and reply references. |
| [Chat](chat.md) | Discord, Telegram, WhatsApp Business | Exact conversation and optional reply under the selected bot/business account. |
| [Forge](forge.md) | GitHub; Radicle remains a future profile. | Repository issue/PR correspondence, separate from software-changing authority. |
| [Social](social.md) | Facebook Page, LinkedIn, X | Original public post, exact publishing actor and provider-specific payload. |

The explicit [`reach.connect.prepare@1`](connected-work/preparation.md) profile prepares these
requests through a native serial Graph, including finite WUPHF plans. It performs no account
authentication or delivery. The families organize contracts and discovery within Reach; they add
no separate Composition or provider authority. [State of Work](../../state-of-the-work.md#reach-operator-profiles)
keeps the shared evidence boundary.

## Public Discord profile

A mention in the Necropolis wakes one bounded turn. Reach admits the event, forms an answer under a pinned Persona, and records whether the external place received it. The platform account remains a way to appear there, without becoming the Lich.

[Habitat](habitat.md) defines who and what may enter that social place. [Turn](turn.md) follows a question through committed answer and delivery. [Deployment profiles](deployments/index.md) choose where its durable authority and transport custody live.

For the configurable Discord foundation, start with [operator preparation](preparation.md)
and its [implementation boundary](architecture.md). That offline preparation profile selects
platform-qualified participants, groups, conversations and permitted requests before an explicit
native Graph. The Discord interface translates its own ids into that shared contract. It does
not activate the public Discord contract below or supply a connected bot.

The separate [Discord operator profile](operator.md) supplies an explicit development edge,
networkless native document-search worker and local reviewed server setup. It preserves the
same generic preparation policy, while retaining its own effects, generation and hosting limits.

Under `reach.discord` revision `1`, an allowlisted mention, guild command, or policy-admitted internal event may return `ReachTurn@1` and optional `ReachDelivery@1`. The contract publishes `reach.external_converse@1`, `reach.external_summon@1`, and `reach.external_presence@1` for those bounded uses.

This public profile excludes cross-place identity/continuity, moderation, ambient surveillance, attachments, DMs, shell, deployment effects, and consent settled by the platform. [Avatar](../avatar/index.md) may bind presentation, while Reach retains responsibility for the event, audience, turn, delivery, and receipt. A later projection must obtain its own authority; the result of this turn cannot supply it.

## Connected work

[Reach Connected Work](connected-work/index.md) (`reach.correspondence`, revision `1`) is the
accepted successor for bounded correspondence across accounts. It owns the communication,
audience and delivery judgment for Gmail, Discord and GitHub, with an optional WhatsApp business
profile and a separate owner–agent probe. Public Discord records and grants retain their
`reach.discord@1` identity. The separately executable preparation profile can build provider
requests today. Connected account access and durable delivery still require implementation.

The [account lifecycle](connected-work/accounts.md) and [delivery plan](connected-work/delivery.md)
specify how a connected account is authorized and how an uncertain send is recovered. [Social accounts and advertising](connected-work/social.md)
distinguishes organic publishing from later paid campaigns.

## Reference questions

Choose one provider operation from the [connected-work contracts](connected-work/index.md).
These are starting points for a [reference study](../../sepulcher/aspects/weaver/assimilation.md#find-reference-implementations).
Each question tests a different assumption about correspondence.

| Target | Implementation to inspect | Question for Reach |
| --- | --- | --- |
| [GitHub issue conversation](connected-work/github.md) | [GitHub CLI issue view](https://github.com/cli/cli/blob/acee710547dcf7dfb6490afea77972187e74b819/pkg/cmd/issue/view/view.go) | When a reader asks for comments, how does it identify the issue and its speakers? How would Reach expose a partial page of comments? |
| [Gmail reply draft](connected-work/gmail.md) | [Google's create-draft sample](https://github.com/googleworkspace/python-samples/blob/afb9e229ef04ad714a5166685eed0bf0e44abfe3/gmail/snippet/send%20mail/create_draft.py) | Which MIME bytes are prepared locally, when does a draft first exist in the mailbox, and what identifier comes back? What if that response is lost? |
| [Discord mention](operator.md) | [Mercury's Discord adapter](https://github.com/cosmicstack-labs/mercury-agent/blob/7b0d6c0d6acf03fd7d0df0d9f0421aafca2496a9/src/channels/discord.ts) | Compare the handling of a guild mention and a DM with the existing operator profile. Which audience and sender checks happen before either reaches the agent? |
| [Telegram reply](connected-work/telegram.md) | [Mercury's Telegram adapter](https://github.com/cosmicstack-labs/mercury-agent/blob/7b0d6c0d6acf03fd7d0df0d9f0421aafca2496a9/src/channels/telegram.ts#L624-L661) | How does the adapter identify a message for later edits? If the initial send may have succeeded, what evidence would Reach need before sending again? |

[Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
