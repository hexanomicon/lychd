---
title: Telegram connection
icon: fontawesome/brands/telegram
---

# Telegram connection

Prepare a release notice for an admitted Telegram chat using a bot connection. The
[Chat](../chat.md) request retains the exact account, conversation and optional reply while
Telegram determines the payload and available operations.

This is the `reach.connect.prepare@1` request-building subset. It supplies no bot login,
update listener or personal-session integration.

## Bot message preparation

The target uses a numeric `conversation_id`, including a negative group/chat ID where applicable.
Usernames are not accepted as substitute identities. An optional numeric reply reference remains
bound to the request. The builder prepares `sendMessage` with exact text, disabled link previews
and no markup parser selected. Text exceeding 4,096 characters refuses rather than splitting one
preparation into multiple sends.

`telegram:/sendMessage` is a secret-free route selector. The bot token belongs to a later
credential owner that resolves the actual endpoint. A payload proves neither that the bot can
reach the chat nor that it may speak there. A bot cannot initiate arbitrary user chats; privacy
mode and administrator permissions affect what group content it can see.
[Bot introduction](https://core.telegram.org/bots) · [Bot API](https://core.telegram.org/bots/api)

## Intake is a separate operation

Telegram chat-history reads refuse in this subset. Bot-wide `getUpdates` is not a per-chat read:
its offset advancement confirms earlier updates and needs separately owned intake, deduplication
and cursor recovery. Webhook intake would likewise need its own authenticated custody contract.

Personal MTProto login uses an application identity and a user-authorized session, not a bot
token or mailbox OAuth grant. It is outside this profile. Telegram's content terms also constrain
AI use: the documented exception requires explicit, informed, affirmative and continued consent
from all relevant users for the specific content and context. The account owner's consent cannot
admit everyone else's chat history into a model.
[User authorization](https://core.telegram.org/api/auth) · [API terms](https://core.telegram.org/api/terms) ·
[Content licensing](https://telegram.org/tos/content-licensing)

The release WUPHF fixture in [connected preparation](preparation.md) prepares one Telegram notice
alongside Gmail and GitHub requests. No bot token, message send or model call is involved.

[Chat](../chat.md) · [Accounts](accounts.md) · [Delivery gates](delivery.md)
