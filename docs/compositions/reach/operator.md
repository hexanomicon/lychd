---
title: Discord operator profile
icon: material/console
---

# Discord operator profile

`reach.discord.operator@1` is an explicit Linux development profile for a small server: a
credential-bearing Discord edge, a networkless native documents worker, and a local operator
tool for reviewed server setup. It does not activate `reach.discord@1` or any public deployment
profile. Document search is the default; an explicit private profile can instead select bounded
local-model conversation. Independently enabled owner publications use a local queue. Neither
option supplies Ward enrollment, durable Phylactery, or restart continuation.

The edge runs **discord.py 2.7.1** on Python 3.14.8, with its own lockfile. The worker runs
on Python 3.15.0 in the explicit OCI development image, with a generation-local memory Run
ledger and real native Graph. A host supervisor relays
bounded JSON over the two containers' standard streams. Neither container receives an engine
socket, checkout, HOME or the other's credentials. The worker receives a compiled policy
and an immutable export of selected public documents. Default answers are deterministic excerpts
and source links. The optional conversation profile also mounts one frozen static persona and
model binding into that worker; model HTTP stays in a closed host transport.

The existing generic Reach policy selects people, groups, conversations and actions. Discord
administrator permission does not grant a native Sigil, shell or host operation. Administrative
writes are separate local operator commands; Discord chat cannot approve a setup plan.

Server setup uses a fresh snapshot and an exact, expiring plan. It can create bounded roles,
categories and channels, and patch explicitly named existing channel ids. It does not delete,
ban, assign memberships, change the everyone role or grant administrator. A private operations
category and read-only orientation channels belong to the proposed developer layout.

SDK connection management and command dispatch remain at the edge. Administrative/message
writes use a single-attempt REST adapter because the pinned SDK retries some POST failures.
The edge retains content-free, fsynced attempt metadata. An unknown result fences repetition;
the journal witnesses transport effects and is not a canonical Run or conversation ledger.
An uncertain create is inspected, never blindly retried or automatically deleted.

Each launch creates a new generation. Old events are refused; process failure stops both peers.
The operator effect journal survives, while memory Runs and conversations do not. This is an
explicit development limitation, not Phylactery recovery or production hosting acceptance.

## Prepare the server and private workspace

Start with [Prepare Reachy](preparation.md): create a private application, install its bot with
`bot` and `applications.commands`, copy its stable IDs, and validate the policy. That tutorial
ends with the bot offline. The steps here deliberately continue into this separate operator
profile. The [public Discord contract](index.md) and the Designed
[home and VPS profiles](deployments/index.md) keep their existing boundaries.

The optional community onboarding profile binds one public text channel, an existing bot-owned
welcome message, and two zero-permission baseline roles. A persistent welcome button opens a
private form with optional interests and introduction text. Only an explicit publication
confirmation creates or updates that member's one public introduction. Choices do not grant
Contributor, Maintainer, Admin, native identity, or capabilities. Every human receives the
configured Magus baseline; bot accounts receive the common Bot role. This automation requires
Server Members Intent, uses no member/presence cache, and backfills at most 1,000 existing members
once per process generation. Private drafts expire after five minutes or restart.

Select it with `--onboarding-profile /absolute/private/onboarding.json` on `run`. The strict
JSON object contains `guild_id`, `channel_id`, `panel_message_id`, `magus_role_id`, and
`bot_role_id`. The host freezes this bounded private file and mounts it only into the Discord
edge. Startup verifies the exact public channel, welcome author, role authority and hierarchy
before registering controls. Attaching the controls to the welcome message is a separate
reviewed operator edit. Role additions preserve other memberships; public introductions use
the content-free effect journal to retain their message identity across restarts. Unknown
creation or update outcomes fence further publication until operator reconciliation. These
are Discord presentation and membership effects, not Ward enrollment or native Graph runs.

Use a Linux host with the repository's host tooling installed as described in
[CONTRIBUTING](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#setup-and-commands)
and a working rootless Podman engine. Docker is an explicit alternative supported by the harness;
its build requirements remain those in CONTRIBUTING. Run the following commands from the
repository root, in one terminal. They run the host wrapper; the native documents worker itself
runs only inside its OCI image.

Choose a **new absolute directory outside every Git checkout**. Its existing parent must be a
real directory owned by you. Replace the example path and synthetic `USER_ID` below before
continuing. `USER_ID` must be the destination server's actual owner for server planning; it is
also used as the optional inspection allowlist entry at startup.

```bash
REACH_ROOT="/absolute/private/path/reach-operator-01"
USER_ID="555555555555555555"
ENGINE="podman"
umask 077
mkdir -m 700 "$REACH_ROOT"
cp -n examples/reach/policy.toml "$REACH_ROOT/policy.toml"
```

Keep this terminal's variables for the later commands. Set `ENGINE="docker"` before building if
you intentionally use Docker. The harness rejects relative paths, symlink ancestors and paths
inside a Git checkout, including ignored directories. It requires private owner-only state
folders and token/image/plan files. Token, image record and plan outputs must not exist already;
use a new filename for each new artifact. An exported corpus needs a new or empty directory.

Open `$REACH_ROOT/policy.toml` with your local text editor. Replace every synthetic application,
bot, server, channel, user and role ID using the table in [preparation](preparation.md#3-copy-stable-ids).
For a first launch, keep one existing text channel in `allowed_channel_ids`, allow your own user
ID through the first rule, and keep `context_message_limit = 0`. Remove the example developers
rule until you have recorded a real role ID, or replace it with the actual intended role ID.
The first matching user-or-role rule owns the permitted actions; a later rule cannot supply an
action missing from that first match. Keep `answer_docs` enabled for the user who will try the
bot and inspect it.

The server plan below has a fixed developer layout. Its Reach channel is exactly the **first**
ID in `allowed_channel_ids`: it preserves that channel's ID and may rename it to `the-reach`,
move it into `DEVELOPMENT`, and update its topic. If it is currently named `general`, the plan
renames it before creating the separate community `general` channel. Verify that this is the
intended existing text channel before planning. Other policy channels are not added to the
server layout by this CLI.

For setup, grant the bot **Manage Channels** and **Manage Roles** in the destination server and
check its role hierarchy in Discord. The planner requires those existing permissions or an
already present Administrator permission; it never grants Administrator itself. Prefer the two
specific permissions. The bot still needs access to the intended channel for ordinary operation.
Creating `Core`, `Developer` or `Contributor` does not assign those roles to anyone; an authorized
human manages membership in Discord and records any resulting rule role IDs in the private policy.
Discord server authority does not grant native or host authority.

## Capture the bot token locally

On your application's Bot page in the Developer Portal, obtain the **bot** token yourself. Keep
it out of chat, screenshots, tracked files, command history and environment variables. This is
the credential step omitted by offline preparation. Run:

```bash
uv run --locked python scripts/reach_operator.py token \
  --file "$REACH_ROOT/discord-token"
```

The command prompts through `getpass` in your local terminal and writes a private `0600` file.
Paste the token only at that hidden prompt. The token value is never a CLI argument; later
`--token-file` arguments contain only the file's path. No ordinary Discord user token is used.
If the token file already exists, the command refuses to overwrite it. A replacement credential
needs a deliberately selected new file, followed by explicit use of that file at startup.

## Export public documents and build both images

Export the committed public documents selected by `examples/reach/public-docs.txt`:

```bash
uv run --locked python scripts/reach_operator.py export-corpus \
  --revision HEAD \
  --output "$REACH_ROOT/corpus-01"
```

The result reports the resolved commit. Each exported file has a manifest hash and a source link
pinned to that commit. Dirty working-tree changes and private local material do not enter this
export. The worker verifies the manifest and file bytes. To change the documents, export a
new committed revision into a new corpus directory and select it on a later explicit launch.
Do not edit the exported files in place.

Build the paired development images and retain their exact image identities:

```bash
uv run --locked python scripts/reach_operator.py build \
  --engine "$ENGINE" \
  --images "$REACH_ROOT/images-01.json"
```

This creates the Python 3.15.0 native check image and the separately locked Python 3.14.8
Discord edge image. The image record contains their `sha256:` identities; startup selects these
exact local images with pulling disabled. A failed build or unavailable engine stops the step.
There is no host worker fallback. This build command does not run the bot or apply server changes.

The edge's credential-bearing process talks to Discord. The native worker has `--network=none`
and receives the compiled shared policy and corpus read-only. The edge never receives the corpus
or Core runtime; the worker never receives the token or constructs a Discord client. The
development check image includes the SDK as a test dependency. Both containers have a
read-only root, bounded resources, and a private temporary filesystem. Neither receives the
checkout, host HOME, an engine socket, provider credentials or published ports. The host wrapper
owns engine calls and relays bounded JSON between their standard streams.

## Review an exact server plan

Stop any running instance before planning or applying against the same state directory. The
harness holds one exclusive instance lock across each operation. Planning contacts Discord to
verify the application, bot, server owner and current server snapshot. It writes a private plan;
it does not create or patch Discord resources.

```bash
uv run --locked python scripts/reach_operator.py admin-plan \
  --engine "$ENGINE" \
  --policy "$REACH_ROOT/policy.toml" \
  --token-file "$REACH_ROOT/discord-token" \
  --state-dir "$REACH_ROOT/state" \
  --images "$REACH_ROOT/images-01.json" \
  --owner-id "$USER_ID" \
  --output "$REACH_ROOT/server-plan-01.json"
```

The terminal reports the plan's digest and path. Open the plan JSON locally and review its
`layout`, `snapshot`, `existing`, `operations`, and expiry. In particular, confirm all application,
bot, guild and owner IDs, the existing Reach channel ID, and every planned patch. The CLI offers
this fixed layout rather than an arbitrary layout-file option:

| Resource | Intended layout |
| --- | --- |
| Roles | `Core`, `Developer`, `Contributor`, each created with zero permission bits. |
| `START` | Text channels `start-here` and `announcements`; everyone may view/read history, while sending is denied to everyone and allowed to `Core`. |
| `DEVELOPMENT` | Text channels `dev`, `help`, and the existing channel selected as `the-reach`. |
| `COMMUNITY` | Text channel `general`; voice channels `Coworking` and `Meeting`. |
| `OPERATIONS` | Text channel `ops`; category and channel deny everyone view access and explicitly allow the named owner, `Core`, and the bot to view, send and read history. |

Existing Discord Administrator access still follows Discord's own permission semantics. The
private operations overwrites do not revoke it. The setup does not change the everyone role,
assign members, moderate, ban, delete channels or delete roles. Creating voice channels does not
provide a voice connection, transcription or other media feature.

Names only identify exact compatible existing resources: the desired fields and permission
overwrites must already match before a name-only match can be retained without writes.
Duplicate names, incompatible role permissions or channel settings refuse planning. The first policy channel has an explicit ID,
so its reviewed plan may patch it; the planner does not rename or reconfigure arbitrary
name-matched channels. Preserve the old channel ID in the policy after setup even if its name
or category changes.

A plan expires after fifteen minutes. Copy the digest you actually reviewed into `PLAN_DIGEST`;
the placeholder below must be replaced with that exact 64-character lowercase hexadecimal value.
Applying is the explicit authorization for the reviewed Discord writes:

```bash
PLAN_DIGEST="REPLACE_WITH_THE_REVIEWED_PLAN_DIGEST"
uv run --locked python scripts/reach_operator.py admin-apply \
  --engine "$ENGINE" \
  --policy "$REACH_ROOT/policy.toml" \
  --token-file "$REACH_ROOT/discord-token" \
  --state-dir "$REACH_ROOT/state" \
  --images "$REACH_ROOT/images-01.json" \
  --plan "$REACH_ROOT/server-plan-01.json" \
  --expect-digest "$PLAN_DIGEST"
```

The digest covers the exact plan, including the original snapshot. Apply obtains a fresh
snapshot and refuses if it has changed, the plan expired or the reviewed digest differs. It
checks expiry before each write, checks each applied effect against the observed server, and
stops on expiry, rejection or uncertainty while retaining earlier completed results.
A stopped apply can leave earlier operations in place; it is not a transaction or a rollback.
If a plan simply expired or became stale before any write, create a new plan at a new output
path and review its new digest. If an effect may already have occurred, follow the uncertainty
procedure below first.

## Start Reachy and try its commands

On the first launch, explicitly register commands for **this policy's guild** and allow your
admitted user to run the read-only inspection command:

```bash
uv run --locked python scripts/reach_operator.py run \
  --engine "$ENGINE" \
  --policy "$REACH_ROOT/policy.toml" \
  --token-file "$REACH_ROOT/discord-token" \
  --state-dir "$REACH_ROOT/state" \
  --images "$REACH_ROOT/images-01.json" \
  --corpus-dir "$REACH_ROOT/corpus-01" \
  --sync-commands \
  --admin-user "$USER_ID"
```

Keep this process in the foreground. It verifies the logged-in bot and application, guild
membership and all policy channel IDs before connecting. `--sync-commands` performs guild-scoped
registration only. It never performs a global command sync. On later launches with unchanged
commands, omit that flag; repeat it deliberately when guild registration needs updating.
`--admin-user` may be repeated for additional inspection users, and each must still pass the
same Reach admission policy. It grants no setup apply command and no host permission.

In an allowed channel, use an admitted account to try:

- `/reach status` for this connection's readiness.
- `/reach ask` with a documentation question, or a direct bot mention followed by the question.
- `/reach admin-inspect` for counts of server roles and channels, if your user ID was included
  with `--admin-user` and your policy permits `answer_docs`.

Slash responses are ephemeral. A mention answer is sent to its allowed channel with mentions
disabled. Replies and owner publications suppress automatic link previews; links remain
clickable. An unlisted person, channel, trigger or action is refused or ignored. The edge and
native worker both evaluate the same compiled policy; Discord Administrator status is no bypass.
Default answers contain deterministic public-document excerpts and pinned source links. Opting
into [local conversation](#enable-local-conversation) changes `/reach ask` and direct mentions to
model replies under a separately permitted `converse` action. Administrative
writes remain the separate local `admin-plan`/`admin-apply` workflow; Discord chat cannot approve
a plan.

Press **Ctrl+C** in the foreground terminal to stop. The supervisor retires both peers and removes
only its validated container identities. A child exit, EOF or process failure also stops both.
The SDK may reconnect its Gateway connection within a running generation, but the harness does
not install a service, auto-restart failed processes, or resume native Runs. A new invocation is
a new generation, refuses pre-generation events, and starts with empty memory Runs and
conversations. Keep the same state directory so the durable transport attempt journal continues
to fence uncertain effects.

## Enable bounded surrounding history only when intended

The default policy keeps `context_message_limit = 0` and the run command omits `--history`.
Direct mentions and slash questions do not require general surrounding-history access. Leave
Message Content, Server Members and Presence privileged intents off for that default.

To opt into history, stop the instance, choose a positive `context_message_limit` (at most 50)
and `context_max_age_seconds` (at most 3600) in the private policy, grant **Read Message History**
in the allowed channel, and enable **Message Content** for the application in the Developer
Portal. Then add `--history` to the same run command. The policy setting and flag must agree;
a positive limit without the flag, or the flag with a zero limit, refuses startup. Member-list
and presence intents remain unnecessary.

To use `/reach context`, also add `summarize_context` to the **first matching rule's** `actions`,
for example `actions = ["answer_docs", "summarize_context"]`. Enabling history alone does not
authorize that action. The result is selected context excerpts, explicitly labelled as having
**no AI summary**. History can also inform document matching for admitted questions.

The edge fetches only bounded recent messages from the admitted channel before the triggering
event, skips webhooks, other bots and empty text, truncates each message to 2,000 characters, and caps
the history payload at 16 KiB. The worker checks its conversation, age, count and byte bounds.
Conversation mode may also include this bot's own recent replies with its configured display name.
This is per-request context, not durable native conversation history. Do not enable it in a
channel whose surrounding content you did not intend to admit.

## Enable local conversation

This option requires an already running, warm local `Qwen3.8-27B` at the fixed literal endpoint
`http://127.0.0.1:28000`. The host transport checks fresh `/health` and `/v1/models` observations
for the exact model. It cannot start, activate, evict or replace an engine. An absent or unsuitable
model refuses the turn; document search and another model are not fallbacks.

Create a private `0600` file at `$REACH_ROOT/conversation-01.json` with your local editor. This
synthetic example uses the admitted defaults:

```json
{
  "schema_version": 1,
  "persona_name": "Example",
  "persona_instructions": "Answer clearly and state uncertainty when evidence is missing.",
  "animator_id": "night-qwen38",
  "model_id": "Qwen3.8-27B",
  "max_context": 16384,
  "max_tokens": 384,
  "temperature": 0.6,
  "max_input_chars": 20000,
  "timeout_seconds": 60
}
```

The profile is a static instruction and exact model binding, not Mirror identity, Persona
lineage or lasting memory. The supervisor freezes its validated bytes for one generation and
mounts that snapshot read-only into the worker. It does not pass the profile or model frames to
the Discord edge. Changes require a new explicit launch.

Add `converse` to the first matching rule's actions. Keep `answer_docs` if you use
`admin-inspect`; keep `summarize_context` if you use the excerpt-only context command. To admit
recent surrounding conversation, first enable history using the preceding section. Then run:

```bash
uv run --locked python scripts/reach_operator.py run \
  --engine "$ENGINE" \
  --policy "$REACH_ROOT/policy.toml" \
  --token-file "$REACH_ROOT/discord-token" \
  --state-dir "$REACH_ROOT/state" \
  --images "$REACH_ROOT/images-01.json" \
  --corpus-dir "$REACH_ROOT/corpus-01" \
  --conversation-profile "$REACH_ROOT/conversation-01.json" \
  --model-endpoint http://127.0.0.1:28000 \
  --history
```

Omit `--history` when the policy limit is zero. The corpus remains required and supplies bounded
public-document excerpts when relevant. Recent messages and excerpts enter the model as
attributed untrusted data. Oldest history is omitted first to meet the profile's input bound.
The native worker admits a generation-local Run, executes `reach.operator_converse@1`, and
acquires an exact Dispatcher Chat lease without tools. One bounded generation request crosses
the host relay; it has no retry, proxy, redirect, arbitrary endpoint or model override. A model
reply supplies no publication or host authority. Model and Discord response limits can truncate
an answer; this profile does not qualify general answer quality.

The public slash-command group defaults to `reach`. Select an alias with `--command-name example`
and deliberately repeat `--sync-commands` when changing guild registration. Names accept a
lowercase initial letter followed by lowercase letters, digits or underscores, at most 32
characters. The alias changes the displayed commands, not the Reach Composition or permissions.

## Publish owner-supplied updates

Publication is independent of conversation. A trusted local producer supplies the finished text
and is responsible for authorizing its exact content and audience before queueing it. Neither a
chat message nor a model result can enqueue a publication. This queue is a local operator
interface, not a Ward grant, general scheduler or automatic link from completed coding work.

Add these arguments to the selected run command, using a private queue outside every checkout:

```text
--publications-dir "$REACH_ROOT/publications" --publication-channel 444444444444444444
```

Replace the synthetic channel ID with an intended text channel in the configured guild. Repeat
`--publication-channel` for each exact destination. The edge verifies the guild channel binding
at startup; chat policy does not broaden this separate host-selected destination set. Only the
edge receives the queue's writable mount. The native worker and model receive no queue access.

Using a local editor, save the finished message as a private `0600` UTF-8 file outside every
checkout, for example `$REACH_ROOT/update-01.txt`. Queue it from a separate local terminal with
the same `REACH_ROOT` value:

```bash
uv run --locked python -m lychd.interface.discord.publications queue \
  --queue-dir "$REACH_ROOT/publications" \
  --body-file "$REACH_ROOT/update-01.txt" \
  --channel-id 444444444444444444 \
  --publication-id 12345678-1234-4234-8234-123456789abc \
  --ttl-seconds 3600
```

Use a fresh UUID for each separately authorized publication; retain it for inspection. The
message body stays out of argv and environment variables. The queue admits at most 32 pending
entries, 1,900 characters per body and a lifetime of at most one hour. A running edge scans the
queue and makes one REST attempt with mentions disabled. It does not ask the model to rewrite
or decide whether to publish.

Private queue receipts retain the publication ID, body digest, outcome and any returned remote
ID. Known settlement removes queued body and request files; an unknown result retains them and
blocks automatic repetition of that publication. The REST journal remains an independent
uncertainty fence. Inspect an uncertain external result before any further authorized action;
new UUIDs must not be used to bypass uncertainty. These receipts do not establish a durable
native outbox, cross-process producer authority or application-level release acceptance.

## Handle refusals and uncertain effects

The harness intentionally emits fixed diagnostics such as `reach_operator_refused`, and its
children expose bounded diagnostic codes. A refusal does not print credentials, Discord bodies
or a detailed foreign exception. Check the selected file paths, owner-only permissions, policy,
image record, expected digest and engine first. Do not work around a refusal by widening mounts,
passing the token in an environment variable, or starting the native worker on the host.

Transport attempts live in `$REACH_ROOT/state/effects`. Their private JSON records contain
method, target class, hashed effect/payload/scope identities, status, and an optional remote ID
or fixed code. They do not retain the token, message text or response body. `attempting` after
an interruption and `unknown` both mean that Discord **may already have performed the write**.
The journal refuses unresolved effects in the same scope even under a newly generated plan.

Stop the instance, retain the plan and journal, and inspect the actual Discord server and its
relevant audit trail manually. Compare the reviewed resource intent and any recorded remote IDs
with what exists. Do not rerun an uncertain create, delete the possible new resource, edit/remove
journal records, switch to an empty state directory, or regenerate a plan to bypass the fence.
There is no public journal reset or automated reconciliation command in this profile. Inspection
can establish what happened; any further recovery needs an explicit manual reconciliation
outside this automatic apply path. If evidence remains inconclusive, leave the effect unknown.
The journal is an attempt witness, not a native Run ledger or durable conversation store.

[Preparation](preparation.md) · [Architecture](architecture.md) · [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
