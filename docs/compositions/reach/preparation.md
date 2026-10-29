---
title: Prepare Reachy
icon: fontawesome/brands/discord
---

# Prepare Reachy while it stays offline

Prepare a private Discord application named **Reachy**, invite its bot to your own server, and
validate local policy while the bot remains offline. You need your own Discord account and a
server where you can install an application.

The separate offline profile **`reach.prepare@1`** checks a prospective request. It does not
change **`reach.discord@1`** or deliver live **`reach.external_converse@1`**.
[State of Work](../../state-of-the-work.md#composition-portfolio-delivery) owns delivery status;
[architecture](architecture.md) explains the preparation boundary and the remaining live path.

## 1. Create the private application

Sign in to the [Discord Developer Portal](https://discord.com/developers/applications) with your
own Discord account. Choose **New Application**, name it **Reachy**, and create it. On **General
Information**, copy the **Application ID**. This identifier is not a credential.

Open the application's **Bot** page and turn **Public Bot** off. Only the application owner can
then add the bot to a guild. Portal labels and placement may change; Discord's
[bot authorization flow](https://docs.discord.com/developers/topics/oauth2#bot-authorization-flow)
defines the behavior.

**Do not generate, reset, copy or paste a bot token during this preparation.** The local helper
never consumes credentials. A token needed by a later live adapter belongs outside the
repository, with its credential owner. Use an application bot; never obtain an ordinary user's
account token.

## 2. Configure installation and invite the bot

On **Installation**, enable **Guild Install** for this server installation. Use the scopes
`bot` and `applications.commands`, with only **View Channel** and **Send Messages** as the
initial bot permissions. The installing account needs **Manage Server** (`MANAGE_GUILD`) in
the destination server. [Discord installation contexts](https://docs.discord.com/developers/quick-start/getting-started#choosing-installation-contexts)

Use the portal's installation link if available. If a private application cannot retain a default
link, keep it private and use **OAuth2 → URL Generator** with those same scopes and permissions.
The local `--install-url` preview below is another way to construct the intended authorization URL.
Opening and authorizing the URL installs the bot; printing it does not.

Select your own test server in the authorization page and approve the installation. Reachy will
appear in the member list **offline**: no bot process is running. No public callback,
**Interactions Endpoint URL**, or public port is needed for the planned outbound Gateway.
The command scope alone does not register any slash commands.

You may use a small private server with a channel such as `#the-reach` and an optional role for
people allowed to ask questions. Channel and role names are conveniences; the policy uses IDs.
Keep the bot's channel permissions limited to the intended place. Do not grant Administrator,
moderation or voice permissions for this preparation.

## 3. Copy stable IDs

In the Discord client, enable **User Settings → Advanced → Developer Mode**. It adds ID-copy
actions to context menus. Discord's [ID guide](https://support.discord.com/hc/en-us/articles/206346498)
shows the user, server and channel actions.

| Policy value | Where to obtain it |
| --- | --- |
| `application_id` | Developer Portal → application → General Information → Application ID. |
| `bot_user_id` | Right-click the invited Reachy bot → Copy User ID. |
| `guild_id` | Right-click the server icon → Copy Server ID. |
| `allowed_channel_ids` | Right-click each intended text channel → Copy Channel ID. |
| Rule `user_ids` | Right-click each allowed person → Copy User ID. |
| Optional rule `role_ids` | Server Settings → Roles → the role's context menu → Copy Role ID. |

Copy the actual bot user ID separately; do not assume it equals the Application ID. Keep IDs as
quoted decimal strings in TOML. Display names, tags and a rule's `name` label do not authorize
anyone. Record a real server's policy in your private operator workspace outside the checkout;
keep the tracked examples synthetic.

## 4. Understand the example policy

Complete the repository setup in
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md), then work from
the repository root. Open
[`examples/reach/policy.toml`](https://github.com/hexanomicon/lychd/blob/main/examples/reach/policy.toml).

Use schema version `1` to describe the place where you intend Reachy to respond: one application,
bot user and guild, an allowed channel list, and ordered `rules`. Each rule lists `user_ids`,
`role_ids` and `actions`. The supported actions, `answer_docs` and `summarize_context`, name the
work you want to allow; the preparation helper only evaluates their admission.

The adapter compiles these Discord values into a platform-neutral Reach policy. Consequently,
the shared evaluator and Graph need no knowledge of Discord guilds, snowflakes or slash-command
payloads.

The first rule matching a user ID **or** one of the event's role IDs owns the allowed actions.
If that rule lacks the requested action, admission is denied without falling through to another
rule. Application, bot, guild, channel, trigger, event age and question length must also pass.

The example allows `mention` and `slash`, sets `event_ttl_seconds = 300` and
`max_question_chars = 2000`, and keeps `context_message_limit = 0` with
`context_max_age_seconds = 600`. Keep surrounding history disabled at zero. These fields bound
future context use; no history fetcher runs here.

Leave privileged **Message Content**, **Server Members**, and **Presence** intents off now.
Direct bot mentions can expose their own content without general Message Content access; that
exception does not expose arbitrary surrounding conversation. A later history feature needs
explicit policy enablement, **Read Message History**, and the **Message Content** intent for
surrounding guild content. Checking the triggering member's roles alone does not require member
or presence intents. [Message Content rules](https://docs.discord.com/developers/events/gateway#message-content-intent),
[member information without a cache](https://discordpy.readthedocs.io/en/stable/intents.html#member-cache)

## 5. Validate policy locally

Run the supplied synthetic policy:

```bash
uv run --locked python scripts/reach_prepare.py --policy examples/reach/policy.toml
```

Correct any reported policy errors before continuing. To preview an installation URL:

```bash
uv run --locked python scripts/reach_prepare.py --policy examples/reach/policy.toml --install-url
```

The example IDs do not identify your application. For an actual invitation, copy the policy to
your private workspace, replace its IDs with the values you recorded, and pass that file's path
to `--policy`. Confirm the Application ID before following the resulting URL. For the initial
invitation, the portal's URL generator avoids needing a completed local policy first.

The helper validates configuration and previews locally. It never authenticates, connects to
Discord, sends a message, answers a question, or logs the question.

## 6. Inspect a synthetic event

Optionally exercise event admission:

```bash
uv run --locked python scripts/reach_prepare.py --policy examples/reach/policy.toml --event examples/reach/event.json
```

Read the fixture as already normalized synthetic input. It uses shared Reach names: `account_id`
for the Discord application, `space_id` for the guild, `conversation_id` for the channel,
`subject_id` for the person, and `group_ids` for roles, with `platform` set to `discord`. These
IDs and roles prove no Discord identity and grant no local authority. To try a private policy,
copy the fixture outside the checkout too, then make its IDs match that policy.

The fixture has a fixed historical `occurred_at` and expires under the five-minute TTL. To
demonstrate admission, update it to the current UTC timestamp with its timezone, or run policy-only
validation instead. On Linux, `date -u +%Y-%m-%dT%H:%M:%SZ` prints a suitable timestamp. Keep the
TTL enabled. A refusal for an expired event is the intended result, not a bot connection failure.

Preparation ends with Reachy invited and offline, IDs recorded without secrets, a validated policy,
and an understood synthetic admission or refusal. Continue with the separate
[operator development profile](operator.md) for an explicitly started docs-search bot and local
server setup. The [architecture frontier](architecture.md#acceptance-before-deployment)
identifies the integrated evidence needed before live answers or deployment.

[Reach](index.md) · [Habitat](habitat.md) · [Turn](turn.md)
