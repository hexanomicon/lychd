---
title: Discord operator profile
icon: material/console
---

# Discord operator profile

`reach.discord.operator@1` is an explicit Linux development profile for a small server: a
credential-bearing Discord edge, a networkless native documents worker, and a local operator
tool for reviewed server setup. It does not activate `reach.discord@1` or any public deployment
profile. Document search is the default; an explicit private profile can instead select bounded
local-model conversation and, separately, catalogue research. Independently enabled owner
publications use a local queue. These options supply no Ward enrollment, durable Phylactery,
or restart continuation.

The two processes have different dependencies and custody. The edge runs **discord.py 2.7.1**
on Python 3.14.8 with its own lockfile. The worker runs Python 3.15.0 in the explicit OCI development
image and executes a real native Graph with a generation-local memory Run ledger. A host supervisor
relays bounded JSON over their standard streams; neither container receives an engine socket,
checkout, HOME or the other's credentials.

For document search, the worker receives a compiled policy and an immutable export of selected
public documents, then returns deterministic excerpts and source links. The optional conversation
profile adds one frozen static persona and model binding to that worker. Its model HTTP remains
in a closed host transport.

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

Export the committed public documents selected by `examples/reach/public-docs.txt`. The maintained
selection names 19 public pages, including the Lich's identity, Transcendence and Inner Tongue
owners alongside setup and extension material:

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

To offer the public project's documentation, roadmap, source, tests and supported configuration
instead of the small default selection, explicitly choose the project export:

```bash
uv run --locked python scripts/reach_operator.py export-corpus \
  --project-files --revision HEAD \
  --output "$REACH_ROOT/project-corpus-01"
```

This selects eligible regular text blobs from the pinned Git tree under the exporter's public
path policy. Review that selection as material permitted in the configured conversations;
being tracked or text does not itself prove that arbitrary content is public. The export does
not follow symlinks or include ignored files, `.git`, local credentials or installed dependencies.
Its manifest records bounded omissions. It admits at most 8,192 selected and omitted entries,
64 MiB of admitted text and 512 KiB per source, with a separate bounded manifest. The same
`--corpus-dir` launch option mounts and verifies this detached export read-only in the worker.
The mount is a revision snapshot; working-tree edits require a new export and explicit launch.

Research discovery offers at most sixteen local descriptors. Exact source references and numbered
targets retain precedence; a verified named parent with matching authored units ranks before ordinary
path, title and content overlap. Its optional `section_match` string has at most 320 characters and
shows authored parent and sampled child headings or anchors, without inventing a range. It is
untrusted discovery metadata, never acquired body evidence or source authority. The model selects from that same offered
set at planning, validation and acquisition. It can read at most three local excerpts per plan.
Ordinary excerpts retain a 4,000-character bound; an explicitly requested multi-section or
complete-quotation Markdown read may admit up to 16,000 characters from the selected scope. Neither proves exhaustive
inspection of the repository.
Implicit Markdown reads skip link-only navigation. A kickoff favors welcome or getting-started
content and retains nearby parent/date context; an explicit source fragment still selects that
section. Implicit nested lexical reads retain the nearest non-title parent with meaningful selected
content inside the existing excerpt bound. A source whose required contiguous section context cannot
fit is refused rather than presenting the child without its owner. Numbered section labels and
adjacent authored anchors participate in selection. The current
question's explicit targets take precedence over the acknowledged research plan, which supplies focus for an elliptical
follow-up such as a filename. Inspect the projected excerpt bounds when source relevance matters.
The complete catalogue is not injected into the prompt, and an oversized fixed input still
refuses under the normal Context budget. These files supply evidence, not instructions or
permission to execute code, edit files or search private mounts.

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

A matching name lets the planner retain a resource without writing only when its desired fields
and permission overwrites already match exactly. Duplicate names, incompatible role permissions
or incompatible channel settings refuse planning. The first policy channel is different because
its explicit ID allows the reviewed plan to patch that exact resource. The planner cannot rename
or reconfigure arbitrary name-matched channels. Keep the existing channel ID in policy after
setup, even if the plan changes its name or category.

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

The optional community onboarding profile starts from a public welcome channel, a separate public
introduction channel, an existing bot-owned welcome message, and two zero-permission baseline
roles. The welcome channel may stay read-only. Its persistent button opens a private form for
optional interests and introduction text; only explicit publication confirmation creates or
updates that member's one public introduction. Those choices grant no Contributor, Maintainer,
Admin, native identity, or capabilities.

For membership, humans receive the configured Magus baseline unless they already hold an explicitly
configured elevated community role; bot accounts receive the common Bot role. When using these
exemptions, keep one community role per human—Magus, Contributor, or Maintainer—with Admin as a
separate add-on. An authorized human promotes a member by replacing the previous community role.
Onboarding itself never removes roles or grants an elevated role.

This automation requires Server Members Intent. It uses no member/presence cache and backfills at
most 1,000 existing members once per process generation. A private draft expires after five
minutes or restart.

Select it with `--onboarding-profile /absolute/private/onboarding.json` on `run`. The strict
JSON object contains `guild_id`, `channel_id`, `introduction_channel_id`, `panel_message_id`,
`magus_role_id`, and `bot_role_id`. Optional `elevated_human_role_ids` is an array of at most two
exact role ID strings for Contributor and Maintainer; omission defaults to an empty array and
preserves the baseline behavior of existing profiles. IDs must be distinct from one another,
the everyone role, Magus and Bot. Keep Admin outside this list. Role names do not
select exemptions. Startup requires each exempted role to exist and be unmanaged; these
read-only checks confer no authority to assign it. Join and startup backfill skip Magus for
humans holding either configured role, including after restart. Existing duplicate community
memberships require a separate reviewed human cleanup.

The two channel IDs must differ. The host freezes this bounded private file and mounts it only
into the Discord edge. Startup verifies both public text channels, welcome author, baseline
role authority and hierarchy before registering controls. Attaching the controls to the welcome
message is a separate reviewed operator edit. Role additions preserve other memberships; public
introductions use the content-free effect journal to retain their message identity across
restarts. Unknown
creation or update outcomes fence further publication until operator reconciliation. These
are Discord presentation and membership effects, not Ward enrollment or native Graph runs.

## Enable bounded surrounding history only when intended

The default policy keeps `context_message_limit = 0` and the run command omits `--history`.
Direct mentions and slash questions do not require general surrounding-history access. Leave
Message Content, Server Members and Presence privileged intents off for that default.

To opt into history, stop the instance, choose a positive `context_message_limit` (at most 50)
and `context_max_age_seconds` (at most 172800, or two days) in the private policy, grant **Read Message History**
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

### Nadir conversation evolution

The explicit operator conversation profile may opt into one-to-one DMs. In the private
`policy.toml`, add the exact sender to top-level `allowed_dm_user_ids` and include that sender in
`user_ids` on the first matching rule with `converse`. Both are required: a guild role rule cannot
admit a DM, and the allowlist alone grants no action. The following IDs are synthetic; replace
them locally and update the existing matching rule rather than appending a competing rule:

```toml
allowed_dm_user_ids = ["111111111111111111"]

[[rules]]
name = "conversation-owner"
user_ids = ["111111111111111111"]
role_ids = []
actions = ["converse"]
```

A DM has no guild, inherited roles or parent conversation. Only `converse` is admitted there;
`allowed_triggers` continues to govern guild mentions and slash commands. DMs require the
conversation profile and remain separate from guild channels and other people's DMs. The edge
verifies the observed one-to-one recipient before sending. That message binding grants no
channel administration authority.

Conversation mode sends no automatic textual acknowledgement or echo of the question. It may
mark receipt with the optional 👀 reaction below. When research is needed, the first substantive
reply is the model's interpreted plan; a short ordinary question can receive its answer directly.
Documentation-only mode retains its fixed receipt. Plans and each final answer part have separate
stable delivery identities; a plan is not completion. Answers are frozen into at most six parts of at most 1,900
UTF-16 units each before the first final send. Text exceeding that delivery budget is refused
instead of silently cut off. A failed or uncertain part stops later parts. Slash answers use the
same bounded splitting with ephemeral followups.

Model-authored answers, research plans and clarification questions follow the reply language
explicitly requested in the current question, otherwise that question's language. Earlier history,
quoted evidence and persona preferences do not choose a different reply language. Fixed transport
acknowledgements, readiness/refusal messages and context-limit notices use English; this profile
does not implement automatic localization of operational copy.

Adaptive context is separately opt-in: add `"adaptive_context": true` to the private conversation
JSON shown below. Omission retains the single-call behavior. Without catalogue research, the model
returns only an `answer`, `read_more` or `clarify` text decision, never an executable tool call.
Without catalogue research or checkback, at most three model calls share one turn deadline; each uses a fresh
generation-local native Run. Only a settled request for more context admits the exact next round, preserving the event,
reply reference and earlier evidence. Terminal results cannot open another round.

History still requires the explicit policy/`--history` opt-in above. The edge reads only the same
conversation, at most three pages of six recent messages, or sixteen per page when research is
enabled, within the policy's total count and
age limits and a shared 16 KiB text budget. A same-place reply anchor consumes those same count
and byte budgets. Disabled history, exhaustion, a spent budget and unavailable history remain
distinct observations; a missing needed source can produce a concrete clarification question.
DM history admits only that sender and this bot. Cached excerpts last for the bounded request;
they supply no durable memory, private Archive ingestion, cross-place identity or publication
authority.

### Quiet replies and adjacent continuations

Explicit mentions and opted-in DMs retain their existing admission. To consider unmentioned
continuations, select exact existing text channels in the private Discord policy:

```toml
allowed_reply_channel_ids = ["111111111111111111"]
allowed_adjacent_followup_channel_ids = ["111111111111111111"]
adjacent_followup_window_seconds = 60
```

Both lists default empty and must be subsets of `allowed_channel_ids`; allowed thread parents
do not activate this feature. Conversation mode, adaptive context and positive bounded history
are required. Existing person, group and action rules still apply. The edge retains at most 512
own final-message excerpts in its current generation, after every text part was delivered
successfully. Plans, failed or uncertain multipart sends, error notices and GIFs create no invitation.

A reply without a ping must reference one of those retained bot finals in the same channel.
An adjacent candidate must be the next observed message, from the original human, within the
configured window (at most 120 seconds). Each completed final permits one adjacent candidate.
Other activity closes the invitation; delayed Gateway echoes of any part of that same final
or its acknowledged successful GIF preserve an open invitation but cannot reopen a closed one.
GIF IDs share the 512-entry bound and never become reply targets. An echo arriving before the
REST acknowledgement is known still closes adjacency. Restart discards this temporary state.

Metadata, selected channel and worker availability checks precede reading an ambient candidate's
body. Native Reach then judges only that candidate and its attributed bot-answer anchor as
`addressed` or `ignore`, before history paging, document selection, research or acknowledgement.
Before a research plan is confirmed delivered, uncertain, malformed, unavailable or ignored
candidates stay silent, including reactions and generic error replies. Once an addressed
candidate's interpreted plan has been confirmed delivered, a later worker refusal or failure
permits one bounded terminal-notice attempt in that same audience. A failed or uncertain final
send cannot trigger another final attempt. The edge tracks this only for the
active event and clears it on settlement or cancellation; another event cannot inherit it.
Error notices create no continuation invitation or decorative expression. Failed or uncertain
plan delivery does not establish this visible commitment. Actual platform replies keep `reply_anchor`; adjacency has a distinct
`continuation_anchor` and does not invent a reply reference. Both share the existing age, count
and 16 KiB history bounds and remain fixed across admitted context rounds. This opt-in supplies
bounded continuation candidates, not general channel surveillance or durable ambient memory.

### Check an answer before settlement

Add `"checkback": true` to an adaptive private conversation profile to opt into a finite
self-check. Ordinary terminal answers and clarification candidates, and researched synthesis,
receive a fresh no-tool review posture before adoption. History requests are not terminal
candidates. The reviewer receives the current question, attributed context and reply target,
acknowledged plan, host-approved persona name, proposed answer and the exact source projections
already used for synthesis. The host calculates request, evidence and candidate digests and binds
the strict judgment to that exact model call; the model never transcribes these hashes.
Review resolves references and chronology against the current question and actual anchors, checks
each requested time horizon, and distinguishes optional suggestions from source-scheduled work.
The literal current question is also supplied as a separate review task; a model's interpreted plan
cannot replace it. This task is budgeted and bound with the frozen envelope for review and correction.
When correcting a prior reply, formation and review also require acknowledging its visible error
and answering a requested explanation without inventing hidden execution causes.
An optional `checkback_invalid_retry = true` profile admits one additional review call across both
candidate versions, requiring checkback. Omitted or false preserves the previous profile digest,
review behavior and budget. Only typed model-output failures `review_shape` and `coverage_binding`
may spend its process-local token, before dispatch. The retry receives the identical frozen evidence,
candidate, approved persona and raw task, plus one concise host-owned reason/control; it receives
no invalid output or suggested verdict. Valid adverse verdicts use the existing correction or
clarification path. Runtime-claim validation, candidate/source quotation guards, host invariants,
authority, budget, transport, timeout, cancellation and finish failures do not authorize recovery.
A second malformed review fails normally, including after the one correction. There are still at
most two candidate versions and one correction. The maximum retry control and unchanged review
recipe are reserved on character, UTF-8 payload and escaped-frame axes before context freezes;
the actual retry envelope is checked again without trimming evidence or raising limits.

Candidate `attempt` remains 0 or 1. Separate `review_attempt` 0 through 2, `retry_ordinal` 0 or 1,
closed invalid reason and retry-control digest preserve each failed and settled review observation;
invalid verdicts and private response bodies never enter structural trace. These optional fields are
absent when the retry flag is false. Model relay calls keep
fresh call IDs and the existing held no-tool lease, deadline and one-request SDK allowance. The
probe retains one shared twelve-operation ceiling across probes, generations, correction and
re-review. This is a harness limit, not an existing native broker turn counter. With interpretation
and addressing, the bounded maximum is seven ordinary or eight research generations; additional
context/probe operations may exhaust the harness earlier. No restart recovery or hidden replay is
added. Pattern revision 8 rejects prior manifests; checkpoint schema 8 is unchanged because the
retry token is transient.

A conservative controller guard can veto an accepted answer that demonstrably repeats complete
sentences from the actual reply or continuation anchor despite an unambiguous English request to
rephrase, simplify or explain in practice. Literal quotation/repetition requests and ambiguous forms
do not activate it; quotation followed by a substantive explanation is not an unchanged answer.
The raw model verdict remains unchanged in trace. A separate Core control receipt records the
guard observation and effective outcome. A veto uses the existing single correction allowance;
it cannot adopt a model-rejected draft or obtain additional evidence or calls beyond that ceiling.

Research reviews also report up to four exact candidate-text clauses asserting current operational
availability or unavailability, at most 240 characters each and 512 UTF-8 bytes for the serialized
array. Oversized observations refuse rather than being truncated. The field is required in both reviews, independently of the raw
verdict. The host checks each bounded contiguous excerpt against that exact candidate; omitted or
invented observations refuse rather than becoming an empty list. Documented capabilities, qualified
dated observations, future plans, conditional advice and explicitly unknown state are not current
runtime assertions. When this public-text path supplies no runtime observation, a nonempty claim
observation returns the draft for same-evidence correction through a separately attributed authority
guard, including when the model requests proof for those draft assertions. Repair must qualify or
retract them, or produce a concrete clarification for an actually unavailable requested fact. It
receives the same exact clauses and frozen evidence within the existing single correction allowance;
the rejected draft is never adopted. Trace
keeps only the candidate-bound count and digest. The bounded serialized observation and correction
metadata cost is reserved before freezing context, accounting separately for Unicode input
characters, UTF-8 payload bytes and escaped pipe-frame bytes under the existing limits. This
allocation allowance is not a guarantee that every schema-valid answer fits: each actual review
and correction is checked again before its model call, and oversized envelopes refuse.
An empty list means no claim was observed, not that
the answer is grounded; extraction remains fallible model judgment.

Bounded reference hints may resolve coordinated ordinal references from one explicit numbered list
or sibling-heading sequence in the actual anchor. They preserve observed item order, labels, aliases
and spans rather than doing arithmetic on printed numbers. Ambiguous, conflicting or incomplete
sequences yield no hint. These transient observations identify referents, not factual proof or new
tasks. Their exact labels may guide selection inside already admitted documents before generic
ordinal inference; explicit current-question names retain precedence and source grants/caps do not change.
One narrow English relational form can additionally observe an explicit opening period and its
named next period in the actual anchor. It preserves the next period's literal label, alias and
spans; it does not translate labels or infer numbering. Ambiguous, quoted, fenced, incomplete or
conflicting forms abstain. These successor observations do not change document selectors. If the
visible admitted source contains that literal target or its observed alias, a terminal clarification
asking only for a different numbered target may be returned for the existing one correction. The
original `needs_evidence` judgment remains visible; no rejected candidate is adopted, and the new
candidate still requires a final accepted review. A clarification about the actual target retains
its ordinary missing-evidence behavior.

Adding `"request_goals": true` requires checkback and adds one fresh no-tool interpretation before
planning. It sees the current question, exact anchors and bounded recent messages, with no source
catalogue, plan or candidate answer. Up to eight short requested outcomes are frozen for that Run.
Decision schema version 4 freezes one transient `TaskRequirements` version 1 object: one to eight
content goals, zero to four presentation constraints, quotation presentation `none`, `abbreviated`
or `full`, and zero to two essential context handles. Constraints remain review obligations and
do not create independent content-coverage excerpts. Only `full` selects whole-quotation source
acquisition and projection; no goal prose, plan, focus or acquired source can select this mode.
Explicit `context_projection_version = 2` requires typed request interpretation and adaptive context.
Omitted/default `1` preserves the prior whole-handle offerings, source model view and profile digest.
Version 1 also retains the original document-discovery score. Version 2 discounts corpus-common
terms, saturates repeated lexical matches and normalizes body length; a path reused as a display
label does not receive authored-title credit. Exact current and admitted-context references,
kickoff routing, numbered targets and authored structure retain precedence. The maximum sixteen
offered identities, manifest bindings, no-query authored order and delivered-plan acquisition gate
remain unchanged. Better selection opportunities do not establish relevance, successful reading
or answer completeness.
Revision 2 offers each admitted history body once, its whole-message handle,
and at most eight complete paragraph-unit handles in source order, with an omitted-unit count.
Blank lines split paragraphs outside fenced blocks; lists, quotations and fenced blocks remain
intact. Only ordinary history receives paragraph offers: independent reply/continuation anchors,
and history entries with either anchor's event identity, retain whole handles only. A long mandatory
anchor can therefore still refuse the budget.

The host resolves handles only through the exact offer map that survived interpretation trimming.
Unknown, duplicate, overlapping, omitted or stale-parent handles refuse. A whole handle excludes
paragraphs of that event; two distinct nonoverlapping paragraphs may share the existing two-handle
ceiling. Selected partial messages contain exact attributed bytes, their handle and an explicit
partial indication. Complete parent digests and exact character/UTF-8 ranges remain with the host
and bind the requirements digest. No free offsets, model summary or parent reinsertion follows.
Interpretation chooses the smallest sufficient units while preserving every referent, contrast and
visible earlier error needed for a WHY request; it may need a whole message or a budget refusal.
 Selected entries remain mandatory alongside
the byte-for-byte current question and complete requirements when optional history is trimmed;
an overflow refuses within the same input, frame and time ceilings. Their exact identities and
the complete object bind the Run digest and frozen review context. They grant no source authority.
The current question, including cancellations and shortening requests, remains authoritative over
this fallible interpretation. They guide planning, synthesis and review, and establish no factual truth or additional authority.
These outcomes can retain requested components when later source packing omits older messages;
they do not supply evidence about why a historical response was produced.
Every goal must receive a coverage status; an accepted answer requires complete coverage and a
short matching visible answer excerpt for each goal. Coverage matching ignores whitespace and
only a conservative presentation subset: strictly flanked paired bold/italic at up to two nesting
levels and balanced one- or two-backtick inline code. Code bodies remain literal. Ambiguous,
escaped, crossing, deeper or unmatched markup, fenced regions and indented code stay literal.
Fence closers allow at most three ASCII leading spaces; tab or non-ASCII indentation cannot close them. Letter case,
Unicode, punctuation and method underscores remain exact; only the candidate or its exact selected
outputs can supply fulfillment evidence. An exact
frozen goal name may be mapped by the host to its index; unknown or ambiguous references refuse.
Missing, duplicate or unsupported coverage cannot
adopt the candidate. An incomplete goal may quote the exact candidate phrase being assessed;
that does not make it complete. Repair receives the missing-goal statuses without acquiring new evidence.
Goal text and quoted fulfillment evidence do not enter structural trace; counts, digests and
closed coverage statuses do. This remains model judgment rather than a semantic proof.
This optional interpretation needs profile-specific semantic qualification: valid goal syntax does
not prove that it preserved the user's scope. Leave it disabled when it introduces unrequested work;
direct checkback still reviews the actual question, anchors, plan and frozen evidence.

`accept` adopts the checked candidate. `revise` permits one correction using that same evidence,
then requires a final accepted review. `needs_evidence` returns a bounded concrete clarification
in the requested reply language. An unresolved second review produces a fixed honest limitation;
malformed or mismatched judgments and timeouts follow the existing failure path. Neither review
nor repair can acquire a new source, change tools or expand authority. A self-check is model
judgment, not independent verification or proof of completeness.

Checkback adds at most two reviews and one correction: at most four formation calls for an
ordinary terminal Run, or five including research planning and synthesis. A continuation
candidate can add one initial addressing call. Request-goal interpretation adds one call per Run,
including each admitted history round. Existing three-round, request, whole-turn and
event-expiry ceilings remain unchanged; additional calls do not guarantee that a slow turn can
finish within them. Each formation call retains its profile generation cap and exact byte bounds.

These are observed phases inside the shared `generate` or `research` Graph station, before
`settle`, rather than separate checkpoint stations carrying source bodies. Source projections
remain transient and identical through all review/repair calls. Structural trace records verdicts,
closed issue codes, attempts and input digests, without candidates, source bodies or reasoning prose.

### Optional reactions and GIFs

The private conversation JSON may enable `expressions` alongside `adaptive_context`:

```json
{
  "adaptive_context": true,
  "expressions": {
    "enabled": true,
    "acknowledge": true,
    "gifs": []
  }
}
```

These are fields to merge into the complete profile below. Omission keeps expressions disabled.
The edge may add 👀 to the exact admitted incoming mention or DM without a textual receipt.
A completed answer may select one additional reaction from 👀, 👍, ❤️, 😂, ✨ and
🤔. These effects never target another message or observe unmentioned channel traffic.
A cosmetic failure preserves the text answer; a failed or uncertain final part prevents later
decorations. Slash responses remain text-only and ephemeral.

To offer GIF choices, add at most eight entries to `gifs`, each with a unique lowercase `id`,
a short `description`, and an exact HTTPS GIPHY media `url` of the form
`https://media.giphy.com/media/VERIFIED_ID/giphy.gif`. Replace `VERIFIED_ID` with a real verified
media ID. The model receives only IDs and descriptions; the edge resolves the selected ID
against the generation's frozen catalogue. Arbitrary model URLs, live GIF search, attachments,
custom emoji and animation generation are not part of this option.

After all text parts succeed, the edge may send one selected GIF as a separate silent reply
with previews enabled and mentions disabled. Ordinary text still suppresses previews.
Reaction and GIF slots have stable attempt identities, so changing a choice cannot bypass an
uncertain earlier effect. The bot needs Discord's Add Reactions and Embed Links permissions
where used; this option does not grant or change permissions. Discord client settings and
provider availability still determine whether the GIF animates.

This option requires an already running, warm local `Qwen3.8-27B` at the fixed literal endpoint
`http://127.0.0.1:28000`. The host transport checks fresh `/health` and `/v1/models` observations
for the exact model. It cannot start, activate, evict or replace an engine. An absent or unsuitable
model refuses the turn; document search and another model are not fallbacks.

The default `--model-transport host` reads that loopback endpoint on the operator host.
When the already-running model is inside the native Podman pod, explicitly select
`--model-transport podman`. Its bounded transport executes only a fixed Python HTTP helper
in the exact `lychd-night-qwen38` container and reads the same loopback endpoint there.
Request text crosses standard input, never shell arguments. The helper cannot select a
different container, URL, command, model, or runtime transition; it publishes no host port.
Both roads retain the exact health/model and generation-payload checks.

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

The default combined instruction/input allowance remains 20,000 characters. An explicitly prepared
profile may select `max_input_chars` up to 32,000, with the same per-message ceiling; this is still
bounded by the selected context, 49,152-byte model payload and 65,536-byte escaped pipe frame.
Unicode and JSON escaping can exhaust the byte limits before the character allowance. The
4,096-token completion ceiling, 60-second per-call maximum, existing call limits and review reserves
remain unchanged. A larger explicit allowance changes the profile digest and needs its own
qualification; it does not make every mandatory context or answer fit.

The profile is a static instruction and exact model binding, not Mirror identity, Persona
lineage or lasting memory. The supervisor freezes its validated bytes for one generation and
mounts that snapshot read-only into the worker. Only its validated expression catalogue reaches
the Discord edge through readiness; the persona and model frames do not. Changes require a new
explicit launch.

The private profile may opt into `"enable_thinking": true` for the same already-running local
model. Omitted or false retains the existing request mode and logical profile digest; true is
included in the binding. Native and host relays require the one exact profile-selected
`chat_template_kwargs.enable_thinking` value and refuse conflicting or expanded settings. This
closed private binding does not add a generic generation policy or model lifecycle authority.
The existing model server must already support separated reasoning output; no server change or
automatic fallback follows. Qualify the exact profile and backend before using it.

Reasoning and final content share the profile's completion allowance, bounded to 4,096 tokens,
which must remain below its declared context window, and its existing timeout. A known length
finish refuses, and the thinking profile additionally requires an explicit natural stop. It gains
no retry, extra correction or bypass of the remaining limits. SDK thinking parts stay transient, outside adopted
text, checkpoint state and settled message history. Private probes may record reasoning presence
and bounded counts, never thought text. Mode selection and observable final-answer quality remain
separate evidence; thinking is not independent verification or a correctness certificate.

With structured output enabled, `"thinking_phases": ["checkback"]` can enable reasoning only for
selected trusted phases. The tuple permits the seven known phase names below, with no duplicates;
a nonempty tuple requires `json_object_output`. The global `enable_thinking` flag enables every
phase; otherwise only listed phases use it. Nonempty selections join the immutable binding, while
an omitted or empty tuple preserves prior digests. Both relays derive the expected mode from the
exact validated grammar carrier, and natural-stop enforcement uses that actual per-call mode.
This adds no model, call, completion allowance, timeout or lifecycle authority. Qualify the complete
selected profile; a useful isolated review replay does not qualify conversation or repair behavior.

An adaptive profile may also opt into `"json_object_output": true`. Its immutable binding then
selects `decision_schema_version = 4` and includes the exact compact-grammar bundle digest. Version
3 profiles refuse explicitly; they are not silently migrated. Profiles enabling `request_goals` or
`json_object_output` must explicitly declare `decision_schema_version = 4`; omission refuses.
Disabled legacy profiles retain their omitted-version behavior. This contract requires a separately
prepared profile and matching image. The explicit interpretation/context projection revision binds the derived profile and requirements
digests. The Pattern is revision 8 with checkpoint version 8 in either mode; older version 7
checkpoints cannot resume under this implementation. The outer decision schema remains version 4:
controller output fields and their fixed grammar are byte-identical, while offered-handle meaning
and model input projection are separately versioned. A new paired image/binding is required even
when the non-secret profile JSON retains its explicit decision version 4. The
seven semantic phases are research planning, ordinary conversation, terminal correction,
synthesis, addressing, checkback and requested goals. Planning has three fixed grammar variants:
documents, web or mixed sources. One trusted selector uses the actual offered catalogue for both
prompt accounting and execution; an empty catalogue selects ordinary conversation. All planning
variants share the `planning` thinking policy. Goal-enabled checkback selects a separate fixed
`checkback_goals` carrier requiring nonempty coverage and a nonnull matching answer excerpt for
each complete coverage entry. Native admission still checks the exact goal set, references and
evidence. Public-text synthesis selects separate host-owned checkback variants requiring a nonnull
`current_runtime_claims` array on every verdict, including `needs_evidence`; an empty array is valid.
These variants make twelve source-owned grammars. A goals-enabled binding refuses the
ordinary checkback carrier; a goals-disabled binding refuses `checkback_goals`. Both checkback
variants retain the same semantic phase and thinking policy.
Both relays accept only exact members of that fixed bundle through `structured_outputs.grammar`;
missing or conflicting settings refuse rather than acquiring a default format. Planning excludes
synthesis-only citation fields, and terminal correction excludes new research or history requests.
No phase is inferred from user text, model output or provider metadata. Closed object branches
exclude input envelopes and host-owned receipts. Research source arrays retain the native limits of three documents, two web sources
and four sources overall, including valid mixed-source plans. Exact catalogue membership and
uniqueness remain native admission checks. Accounting charges the selected grammar and any
review/correction carrier delta before freezing context, within the existing byte and frame limits.
The compact EBNF strings are generated offline from ordered source schemas by
[`generate_reach_decision_grammar.py`](../../../scripts/generate_reach_decision_grammar.py),
with the pinned XGrammar converter and conversion options. A versioned generator normalization
uses nonempty, recursive JSON strings so escaped newlines, quotation marks and backslashes remain
representable without expensive bounded-repeat token masks. It excludes raw control characters
and isolated surrogate escapes. Provider string maxima are an approximation: native parsers
enforce the existing field maxima and refuse oversized results before adoption. The source schemas,
native limits, completion allowance, transport limits and turn deadlines remain unchanged.
Serving requires no XGrammar dependency in Core. The bundle binds the source schemas, converter
version and options, generator normalization, and exact generated strings.
Compact object and array separators bound structural whitespace without changing string content.
Declaration order is preserved by generation and cannot be changed by outer request encoding.
The profile cannot supply a schema or schema hash. Conflicting carriers or modified grammars
and unbound format fields refuse. Omitted or false preserves the previous profile digest and request
dialect, excluding the unused schema version. This requests provider-side structural constraints;
the native phase parser, field checks, source authority and semantic review still apply. A valid
object can still be the wrong decision or contain false prose. Qualify this setting against the
selected backend, including separated reasoning. Ordinary formation has no format-repair retry. Only explicit `checkback_invalid_retry` admits the
closed malformed-review re-review described above; native parsing never repairs or coerces malformed JSON.

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

Omit `--history` when the policy limit is zero. The corpus is still required and supplies bounded
public-document excerpts where relevant. The model receives recent messages and excerpts as
attributed untrusted data, with oldest history omitted first to meet the input bound.

For each admitted context round, the native worker creates a generation-local Run, executes
`reach.operator_converse@8`, and acquires an exact Dispatcher Chat lease without tools. An ordinary
Run makes one bounded model request; the optional research branch below makes one planning and
one synthesis request in the same Run. Optional checkback and addressing add only the bounded
calls described above. Adaptive context can admit up to three Runs for one turn.
The relay supplies no retry, proxy, redirect, arbitrary endpoint or model override. Its reply
grants no publication or host authority. Model output remains bounded; this profile does not
qualify general answer quality.

The public slash-command group defaults to `reach`. Select an alias with `--command-name example`
and deliberately repeat `--sync-commands` when changing guild registration. Names accept a
lowercase initial letter followed by lowercase letters, digits or underscores, at most 32
characters. The alias changes the displayed commands, not the Reach Composition or permissions.

### Opt into public catalogue research

Research requires `adaptive_context` and a separate `research` object in the private conversation
profile. It offers verified local documents as `doc:<manifest-path>` selectors and at most eight
operator-authored public web entries. Each web entry has a unique lowercase `id`, `title`, exact
canonical HTTPS `url`, and optional bounded `focus` phrases. The operator authorizes each complete
public locator before launch; a question, pasted link or model decision cannot add a destination.
The [research profile law](../../adr/30-webcrawler.md#explicit-reach-operator-research-profile)
keeps that standing authority separate from native Bridge consent and Discord identity.

For a conversation request, web metadata becomes eligible when its current question or an
actually bound reply/continuation anchor names a configured URL or `web:id`, or shares normalized
topic terms with configured IDs, titles or URL paths. The last two admitted history entries may
also contribute exact configured references, but cannot activate web through topic words alone.
Any signal offers the complete standing web catalogue in its authored order, retaining readable
alternatives; no signal offers none. Catalogue inspection without a request still lists all entries.
This is approximate retrieval, not a factual or semantic relevance check. A recent explicit link
may retain eligibility during a topic change, while an unmatched paraphrase may need an exact
source reference. The standing authority, source limits and native offered-set checks remain
unchanged. Source `focus` phrases continue to select excerpt positions, not catalogue eligibility.

An admitted mention or one-to-one DM may select at most four sources: at most three documents
and two web entries. The first model call returns an interpreted plan of at most 500 characters.
It also supplies a separate bounded `focus` read query naming resolved sections, units or code
identifiers. The structured planning grammars require a nonempty focus. The planning input contract asks for
one concise sentence of focus keywords or section labels within 500 characters and exposes the
same 500-character maximum for the public plan text. Native bounds remain authoritative; no
formatting recovery or output-limit increase follows. Only the natural plan text
is delivered publicly. The focus selects local evidence; it grants no source authority. Explicit
current section references, numbered ranges, code identifiers, resolved ordinals and whole authored
heading names retain precedence. A resolved focus can replace an incidental partial-word heading
match. Legacy unstructured plans without focus retain the existing fallback. The bounded selector and optional requested outcomes are
checkpointed under conversation schema v8, while acquired source bodies remain transient.
With projection revision 2, the synthesis model view contains only each source's `id`, `title`, `status`, exact projected `text`,
`truncated` and `projection_truncated`, plus `reason` for a non-success result. The host retains the
original source, URL, digests, read offsets, projection allocation and exact span proof for citations
and independent reconstruction. Source focus, corpus digest and research request identity remain
host bindings rather than repeated model-input keys. The delivered plan, task requirements,
attributed context and evidence scope remain model-visible. This changes no source packer, reading
ceiling, call count or transport budget and does not promise every mandatory selection will fit.
The edge must deliver that plan as a separate reply to the same incoming message and acknowledge
successful delivery before any selected document read or web acquisition. Slash commands cannot
acknowledge a research plan and therefore cannot acquire sources through this branch. The usual
optional 👀 receipt remains separate from this interpreted plan; conversation mode sends no
earlier mechanical text.

An ordinary answer or clarification ends its Run; its text schedules no later work. The model
instructions require source-dependent follow-ups, including corrections for omitted evidence,
to select the research branch rather than promise a later lookup in a final answer. Synthesis
must address the current request and acknowledged plan using the acquired excerpts, distinguish
exact quotations from paraphrases, and state missing or clipped evidence. Adoption rejects a
final text that repeats the acknowledged plan after whitespace normalization, before rendering
citations. That narrow check does not detect differently worded promises or prove semantic
completeness. The structural trace records observed plan, source-read and final-delivery events
under its reported capture limits.
A failed native plan parse may emit a separate `research_plan` observation with `operation = validation`
and `status = failed`, its closed error code and actual string-field character counts for text/focus.
It grants no plan-delivery or acquisition evidence. The Core worker distinguishes its exact trusted
local `conversation_budget` refusal as `budget`; arbitrary error text and subclasses do not gain that
classification. Host terminal model-call observations may retain only finite provider finish-reason
and content-state categories from a parsed single-choice completion. Missing observations remain
unknown; no model body, private reasoning or exception text is added. These optional fields may
produce explicit protocol gaps in older closed readers; paired readers must match the staged cohort.
Planning and review interpret the current correction rather than repeat a historical acknowledgement.
An incidental typo must not block the otherwise clear requested result; essential missing context
still uses the bounded history handoff or a concrete clarification.

The native `research` station obtains its exact no-tool Chat lease, waits for the delivered-plan
gate, then consumes bounded source excerpts and makes one synthesis call. Web sources remain bounded
to 4,000 characters; selected multi-section or complete-quotation local Markdown reads may admit
up to the existing 16,000-character maximum. Oldest
history is omitted before source projections are shortened to fit the unchanged combined persona
and JSON input budget. Trimmed multi-section local Markdown distributes that projection across
authored siblings even when the acquired excerpt is shorter than 4,000 characters, retaining exact
source-relative spans. Original and projected digests, allocated projection budgets and omitted
material remain explicit.
The model view omits the internal `projection_spans` array. The host projector retains it transiently.
Projection revision 2 emits at most four text-free `source_projection` observations, each within the
existing 2 KiB trace-event limit. They record the actual allocation, mode, rendered length,
truncation, digests and span count; complete span lists remain in transient local receipts. The
probe independently reconstructs the complete projection and compares the exact reduced model
view, then matches its allocation and proof digests to the native observations. That receipt is
labelled matched reconstruction, never captured model payload. Missing best-effort observations
remain explicit capture gaps. Paired current readers accept these optional observations. Older
closed readers may record protocol-error capture gaps and continue; no live Orb/Nexus consumption
is established here. Core and edge readers must be updated together. Read, model input, review
reserve, payload and frame limits remain unchanged.
The host supplies an `evidence_scope` record beside those attributed sources and preserves it in
the same frozen synthesis, review and repair context. This public-text path establishes which
source bytes were obtained; it supplies no observation of the operator's running installation.
Describe capabilities as documented, retain the dates, inputs and qualification limits of recorded
occurrences, and describe future targets as plans. A milestone establishes neither present
availability nor present unavailability. Successful source acquisition is not successful runtime
execution. An optional exploration suggestion needs no readiness claim. If installed-state
verification is itself requested, identify the missing observation instead of treating unknown
state as absent, broken or working. Unsupported positive or negative availability claims require
correction from the same evidence when a qualified answer suffices; this remains model judgment,
not an additional deterministic veto or runtime inspection facility.
When a long quotation would consume a child's share, at most three spans preserve its opening,
authored attribution and following narrative. One projection has at most 48 spans; tighter budgets
still yield partial evidence, never reconstructed quotation text. The explicit synthetic marker
`[omitted]` distinguishes gaps from authored source words and counts toward the same projection budget.
That balanced mode remains the default for ordinary explanations. An explicit request to give
quotations selects `complete_quotes`; explicitly shortened quotations or quotation summaries retain
balanced mode. The current request owns this choice, never source text or the model's focus.
Complete mode reserves intact quotation bodies, their section identity and authored attribution
before distributing remaining space to explanation. A quotation that cannot fit remains omitted
with explicit gaps. For that mode, synthesis, review and correction require the requested visible
quotations intact, rather than silently replacing them with prefixes or ellipses. This is a model
fulfillment instruction, not an independent guarantee of exact reproduction. Markdown and verse-label
styling may change while words, punctuation and endings remain intact. The mode joins the transient projection metadata and the probe independently
recomputes it; character, UTF-8, frame and span limits remain unchanged.
Numbered ranges and coordinated lists in the current question select the available matching sections
without expanding the numeric interval. Qualified opening/first/second/third units use authored source
order; following requires an opening/first unit of the same kind in that query. An exact document
fragment retains precedence. Ordinals stay within a uniquely named parent section; rejected named
scopes are refused. Only an elliptical relative reference may use acknowledged focus to resolve it.
Requested complete quotations
must be visible in full, even when a shorter prefix matches the source.
Source bodies are transient data attached only to detached outbound model messages; checkpoint
state retains the plan and selectors, and neither native history nor cached Context retains the
acquired bodies. The final model selects citation IDs; the host renders links only through
admitted successful sources and appends explicit unavailable-source notices. After validating the
original closed answer shape and 8,000-character text limit, Reach renders complete simple inline
HTTP(S) Markdown links as their exact visible labels, preserving attribution words while discarding
model-selected destinations. Images, escaped, nested, code and other complex links are not reduced.
Reduction allows one blockquote or list prefix with at most three ordinary spaces after its marker.
It refuses tabs or four leading spaces, tabs or four spaces after that marker, nested containers,
and answers containing HTML `pre` or `code` tags. These conservative
container checks do not implement a complete Markdown parser;
any remaining HTTP(S) URL refuses the answer. Structured citations still name only admitted
successful source IDs, and the host citation footer supplies the clickable HTTP(S) links. This
presentation step leaves the raw candidate, its review binding, and source/projection evidence
unchanged. A blocked page does
not become a page that was read. If every selected web source fails, the host returns a fixed
clarification and its unavailable-source notices, without adopting the model's unsupported comparison.
Persona, humour, multipart replies and optional GIFs retain the same evidence and delivery bounds.

The current research assembly requires Docker for the edge, Core worker and separate source
worker, with `--model-transport podman` for the already-running native model. Build the paired
images using `ENGINE="docker"`; images built in Podman's store do not supply that Docker record.
The source image adds Bubblewrap and a dedicated public CPython 3.15 runtime closure to the exact
Core image. Prepare that closure outside every checkout, with no credentials or private material,
then build a new private image record:

```bash
uv run --locked python scripts/reach_research_image.py \
  --core-images "$REACH_ROOT/images-01.json" \
  --python-root /absolute/public/runtime/python \
  --output "$REACH_ROOT/research-images-01.json"
```

Replace the synthetic runtime path with the complete dedicated interpreter tree. The builder
bounds and fingerprints it, verifies copied bytes, and retains an exact `research` image ID.
It does not qualify a new host or runtime merely by building the image.

Create a separate owner-only authority directory containing exactly one `0600` `profile.json`,
and a distinct `0700` research-state directory; neither may contain or nest inside the other.
The strict `ResearchRuntimeProfile` names `source_kind = "operator_public_catalogue"`,
`public_catalogue_authorized = true`, policy/revocation generations, an aware expiry, a `catalogue`
exactly matching the conversation profile's `research` object, exact subject/channel/DM selectors,
a numeric resolver address and its custody statement, and cumulative attempt/contact ceilings.
Keep these files outside every checkout. Add the following selections to the conversation run
command, replacing the image placeholder with the exact `research` value from the new record:

```text
--engine docker --model-transport podman
--research-profile "$REACH_ROOT/research-authority/profile.json"
--research-state-dir "$REACH_ROOT/research-state"
--research-image sha256:REPLACE_WITH_THE_RECORDED_RESEARCH_IMAGE_ID
```

The source worker receives only the public catalogue authority, its private attempt partition
and bounded event/source metadata. Discord credentials, model credentials, conversation text,
checkout mounts and engine sockets do not enter it. It reserves each stable event/source attempt
before contact and rechecks current authority at network and consumption boundaries. Redirects,
retries, discovered links, general web search, browser rendering and durable source storage are
outside this profile. Restart uncertainty cannot authorize another source attempt.

With research enabled, the native request deadline is 300 seconds, the edge waits at most 310
seconds for that result, and the whole adaptive turn has a 480-second ceiling. The research relay
has 150 seconds, including a 20-second delivered-plan gate and a 70-second source-worker bound
plus cleanup. Ordinary conversation retains its 90-second request and 180-second turn limits;
each model call retains the selected profile timeout. These ceilings do not extend event
eligibility: the default 300-second event lifetime can still refuse late consumption or settlement.
Live Discord/model/source deployment and host-specific extraction qualification remain separate
operator evidence obligations in [State of Work](../../state-of-the-work.md#composition-portfolio-delivery).

### Reuse from another chat transport

The native research Pattern is shared Reach application code. The
[conversation session](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/reach/conversation_session.py)
also owns context-round admission, the three-page ceiling and the adaptive paging/clarification loop. The
[operator client](https://github.com/hexanomicon/lychd/blob/main/src/lychd/compositions/reach/operator_client.py)
owns the bounded private-pipe protocol, including progress delivery acknowledgements. Discord
supplies its SDK pager, audience verification, progress sender and final rendering. Another
transport consumes those shared contracts rather than copying the conversation controller.

Acknowledging the interpreted plan records delivery to the admitted audience, not a human
verdict. The standing research authority remains separate. The current source profile and
attempt partition belong to one exact Reach policy; a multi-account successor must qualify its
authority and attempt identities and explicitly migrate retained claims. The extraction does
not make bare subject/event IDs portable authority.

[Provider-neutral acceptance cases](https://github.com/hexanomicon/lychd/blob/main/tests/unit/compositions/test_reach_portability.py)
exercise the same native Pattern, broker, pipe client and context driver with a synthetic second
transport. They qualify reuse of that choreography, not a Telegram adapter. [Workbench ownership](architecture.md#workbench-ownership)
keeps the finite research path distinct from tool execution and inspection UI integration.

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

After an attempt, a private queue receipt retains the publication ID, body digest, outcome and
any returned remote ID. A known settlement removes queued body and request files. An unknown
result retains them and blocks automatic repetition of that publication; the REST journal also
continues to fence uncertainty independently.

Inspect the uncertain external result before taking any further authorized action. A new UUID
cannot bypass that uncertainty. The receipt witnesses this local transport path, without
establishing a durable native outbox, cross-process producer authority or application-level
release acceptance.

## Test a turn without Discord

The headless helper runs the same native operator conversation Pattern in a disposable,
networkless Core container with an explicitly selected persona, verified corpus and already
running local model. It submits a synthetic normalized mention or DM instead of connecting a
Discord edge. The plan-delivery receipt is simulated and labelled as such. Local document reads,
native Run/station events and model HTTP calls remain real observations.

Select the exact Core image ID from your retained image record as `CORE_IMAGE`, and copy one
scenario into the private operator workspace:

```bash
install -m 600 examples/reach/probes/kickoff.json "$REACH_ROOT/kickoff-probe.json"
uv run --locked python scripts/reach_probe.py \
  --engine "$ENGINE" --core-image "$CORE_IMAGE" \
  --conversation-profile "$REACH_ROOT/conversation-01.json" \
  --corpus-dir "$REACH_ROOT/project-corpus-01" \
  --scenario "$REACH_ROOT/kickoff-probe.json" \
  --output "$REACH_ROOT/probe-kickoff-01" \
  --model-transport podman
```

The output must be a new absolute directory outside every Git checkout. Inputs are frozen for
the occurrence, and the output retains their distinct image identity, persona digest and corpus
revision/digest. Those pins do not establish parity with a live bot unless its selected inputs
have been compared separately. The helper starts one bounded Core worker; it neither changes
model lifecycle nor obtains Discord credentials, starts a web worker or sends a message.
Model-selected web sources are refused rather than supplied with invented evidence.
Use a Core image built with the matching helper/source contract: projection validation also
checks the worker's excerpt against the selected verified corpus.

The supplied scenarios cover a roadmap kickoff, an English DM after Slovak history, and an
uncertain plan-delivery receipt. The kickoff requires the roadmap/current-status source IDs and
the `so_it_begins` GIF in the selected profile. Choose a suitable corpus and expression catalogue
before using those assertions. `plan-not-delivered.json` expects a failed native turn and checks
that no source read or synthesis followed the uncertain receipt. A passing negative scenario
means the refusal boundary held; it does not turn that native failure into a successful answer.

The private `report.json` separates scenario assertions, native status, synthetic receipt,
capture health and cleanup. `turn.json` contains the plan, final answer/GIF selection, exact
Pattern descriptors, acquired-source observations and metadata from the actual synthesis
request, including its projection bounds and digests. The acquired excerpt and the shorter
model-input projection remain distinct. Source bodies and persona/provider payloads are omitted;
`--capture-model-output` separately opts into bounded synthetic model-decision text for diagnosis.
`report.md` gives a readable view. Structural observations use the existing private trace archive:

```bash
uv run --locked python scripts/reach_trace.py show \
  --archive-dir "$REACH_ROOT/probe-kickoff-01/traces" --latest
```

Each scenario file can assert an expected native status, required successful source reads,
an exact GIF ID and bounded `required_text`/`prohibited_text` terms with explicit `text_case`.
A failed assertion returns a nonzero exit code. Inspect the answer and its
supporting evidence as well: structural checks and one local-model occurrence do not certify
every future response. Trace capture remains bounded best-effort observation, with gaps and
failures reported; it is not a durable native Run ledger, source receipt or proof of model
attention. This probe qualifies neither Discord delivery nor the full live research host path.

For up to six linked turns, use `scripts/reach_dialogue_probe.py` with the same CLI flags and
a private scenario such as:

```json
{
  "direct": true,
  "turns": [
    {
      "id": "explanation",
      "question": "Explain request versus response in two points named First and Second.",
      "expected_status": "conversation",
      "required_text": ["First", "Second"]
    },
    {
      "id": "followup",
      "question": "Explain the second point in one simpler sentence.",
      "reply_to": {"turn": "explanation", "part": 0},
      "expected_status": "conversation"
    }
  ]
}
```

Later questions receive the actual prior user text and production-split final answer parts,
with at most twenty recent entries and an exact selected anchor. `reply_to` identifies a real
synthetic delivered part; a non-DM `followup_to` tests a distinct adjacent-continuation candidate.
Future or missing targets refuse. Each turn uses a fresh Core, so this tests explicit transcript
continuity rather than persistent worker state or the live Discord invitation detector. Reports
keep structural/literal acceptance separate and leave `semantic_review` as `needs_review` until
an independent assessment is recorded; a fluent answer or successful source read alone is insufficient.

## Handle refusals and uncertain effects

The harness intentionally emits fixed diagnostics such as `reach_operator_refused`, and its
children expose bounded diagnostic codes. A refusal does not print credentials, Discord bodies
or a detailed foreign exception. Check the selected file paths, owner-only permissions, policy,
image record, expected digest and engine first. Do not work around a refusal by widening mounts,
passing the token in an environment variable, or starting the native worker on the host.

The isolated Core also attempts a bounded structural diagnostic for each admitted Run to stderr.
It correlates the worker generation, request and Run with the returned status, fixed reason and
processing stage. A failed station is named only when a retained native node event explicitly
records its failure; absent or incomplete capture remains visible. These records exclude question,
answer, source and provider bodies and arbitrary exception text. The supervisor accepts this record
only from its Core child, separately from the Edge's fixed diagnostic codes. Diagnostic writes
drop on backpressure so a stalled log consumer cannot withhold the Run's answer.

Each running supervisor retains typed structural observations in the owner-only
`$REACH_ROOT/state/traces/trace.sqlite3` archive. Platform message IDs link adaptive request rounds;
each request links its native Run and exact model/research call identities. History counts, graph
stations, model HTTP status and timings, source outcomes and local excerpt ranges/digests,
acknowledgements and individual final
delivery parts remain searchable after restart. An HTTP status is present only when observed;
missing data never means success. No question, answer, history, source body, URL, provider body,
arbitrary exception text or credential enters this archive.

The archive retains at most 30 days and 100,000 observations, with a 128 MiB database page ceiling
and bounded rollback-journal overhead. Queries return a bounded retained suffix, omissions and
capture counters. Structural producer sequences expose dropped observations separately from native
sequences, whose missing token events are expected. A missing session close remains an unclosed
observation, not evidence that every Run failed. Corruption, unsafe paths or unknown schemas refuse
without erasing the archive. Preserve the original files before manual diagnosis; there is no
automatic reset or repair command.

Inspect the most recent retained Run, failures, or one Discord message from the repository:

```bash
uv run --offline --locked python scripts/reach_trace.py show --archive-dir "$REACH_ROOT/state/traces" --latest
uv run --offline --locked python scripts/reach_trace.py recent --archive-dir "$REACH_ROOT/state/traces" --failures
uv run --offline --locked python scripts/reach_trace.py show --archive-dir "$REACH_ROOT/state/traces" --platform-event-id MESSAGE_ID
```

`show` also accepts an exact `--run-id`, `--request-id` or `--call-id`; `query` accepts generation,
aware `--since`/`--until` times and a result limit of 1–1000 (default 100). These are local,
read-only metadata queries. Capture is `durable_best_effort`: queue overflow, interruption or disk
failure can leave gaps, and retained observations never authorize replay or settle an effect.
The archive is never mounted into either child. Core and Edge container logging is disabled to
avoid incidentally retaining raw private wire bodies in the container engine.

The RunLedger and event bus themselves remain in memory. The diagnostic archive does not provide
Oculus ingestion, native Run recovery, conversation memory, or a replacement for the journals below.

### Publish structural observations to Orb and Loom

The separate `run --observation-dir /explicit/private/directory` option publishes a bounded
`snapshot.json` for the common Oculus source contract. Select the same directory explicitly in
the receiving Vessel's [observability configuration](../../sepulcher/extensions/oculus.md#connected-components-and-activity).
Use `source_id = "reach.operator"` and host attribution `registrant_id = "operator:reach"`.
The directory is owner-only, outside Git checkouts, and independently admitted to the reader's
deployment. This feature neither exposes nor reads the diagnostic SQLite archive.

The host publishes Core/edge/host and external service descriptions, exact worker Pattern
descriptors and a finite window of structural observations. A five-second heartbeat updates the
source snapshot. Producer restart changes its generation; a stopped snapshot becomes stale.
The native Run's terminal state does not close runtime observation, so final Discord delivery
can remain visible with its explicitly supplied Run reference.

Actual custom REST requests and Discord SDK HTTP requests use shared driver observations.
Cached journal results and refusal before transport produce no outgoing attempt. API, gateway
handshake and CDN classifications use fixed safe target identities; URLs, tokens, platform
message IDs, bodies and arbitrary exceptions are absent. SDK attempts identify each observed
header dispatch, before serialization or socket write, including repeated dispatches inside one
logical request. They do not prove transmitted bytes. Pre-header failures, WebSocket frames and
full body consumption are not supplied; SDK completion means observed response headers.
Model HTTP observations retain their existing completion-only coverage, without inventing an
unobserved start or drawing the synthetic SDK relay URL as an external destination. Status-absent
broker or IPC failures create no external model activity. Native station/entered-Step identities
and exact admitted Pattern references remain structural metadata; a bounded Run-reference map
can attach late delivery to that same score without choosing a current or latest Run.

Transport attempts live in `$REACH_ROOT/state/effects`. Their private JSON records contain
method, target class, hashed effect/payload/scope identities, status, and an optional remote ID
or fixed code. They do not retain the token, message text or response body. `attempting` after
an interruption and `unknown` both mean that Discord **may already have performed the write**.
The journal refuses unresolved effects in the same scope even under a newly generated plan.

To investigate, stop the instance and retain its plan and journal. Inspect the actual Discord
server and relevant audit trail manually, comparing the reviewed resource intent and recorded
remote IDs with what exists. Do not bypass the fence by rerunning an uncertain create, deleting a
possible new resource, editing/removing journal records, choosing an empty state directory, or
regenerating a plan.

This profile has no public journal reset or automated reconciliation command. Inspection may
establish what happened, but further recovery requires explicit manual reconciliation outside
the automatic apply path. Leave the effect unknown if the evidence stays inconclusive. The journal
witnesses attempts; it does not retain native Runs or durable conversations.

[Preparation](preparation.md) · [Architecture](architecture.md) · [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
