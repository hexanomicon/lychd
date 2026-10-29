---
title: Chat
icon: material/message-outline
---

# Chat

Prepare a notice or reply for one conversation. A channel, bot chat and business recipient can
share that intent while retaining different audiences, identifiers and access rules.

`ChatTarget` names the local connection, exact `conversation_id` and optional `reply_to_id`.
`ConnectedPolicy` closes the selected account, target allowlist, operation and bounds. A provider
user, role or chat ID does not become local authority.

| Provider | Conversation | Prepared operations |
| --- | --- | --- |
| [Discord](connected-work/discord.md) | Numeric channel under the selected bot connection. | Bounded channel-message reads and text sends, with mentions suppressed and exact reply references. |
| [Telegram](connected-work/telegram.md) | Numeric chat addressed by the selected bot. | Text sends with previews disabled and no markup parser selected. No chat-history read. |
| [WhatsApp](connected-work/whatsapp.md) | Recipient addressed from the selected business phone. | Free-form business text candidates. No personal-chat access, history read or automatic template substitution. |

A Discord reply fails if its referenced message has disappeared. Its nonce binds the complete
preparation: exact retries retain it, while changed text, reply or preparation time changes it.
This bounded provider correlation is not a durable delivery guarantee.

Telegram's bot-wide update stream cannot implement a conversation-scoped read. WhatsApp's current
service window, recipient permission, opt-out, AI-market eligibility and spend remain prerequisites
for later transport, not facts established by constructing a payload.

The existing [Discord operator profile](operator.md) keeps its own development scope.
[Connected preparation](connected-work/preparation.md) supplies the shared serial Graph and finite
WUPHF plan; neither transfers an account's permissions to another conversation.

[Reach](index.md)
