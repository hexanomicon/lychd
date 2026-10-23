---
title: Horizon assist
icon: material/gamepad-variant
---

# Horizon assist

**Unofficial Minecraft integration. Neither Mojang nor Microsoft approves or is associated with this project.**

Publisher: LychD contributors · Contact: [hexanomicon@proton.me](mailto:hexanomicon@proton.me).

An operator speaks a short instruction while playing; a separately controlled Horizon client
performs one bounded action and reports what that client observed. This experimental attached
profile develops that interaction before the managed inhabitant fixture is available.
[Playing with a companion](horizon-play.md) turns that boundary into user stories, experience
criteria and a staged playtest, including useful feedback and quiet idle behavior.

## Execution contract

`blockworld.horizon_assist@1` is a separate experimental score, not an implementation or migration
of `blockworld.bounded_mission@2`. Its records cannot satisfy `PlacementReceiptV1`. The managed,
online-mode, dedicated non-operator bot fixture and its server-authoritative receipts remain the
proving target for the bounded mission.

Admission pins one explicitly supplied local control endpoint, expected client/world identity,
finite permitted actions, coordinate and time bounds, and an external private workspace. One
session exclusively owns that endpoint and permits only one active action. A human player's
endpoint is not implicitly a companion. A companion needs its own client, identity and endpoint;
the pinned Horizon client's authentication limits must be reported before connecting it.

An explicit `singleplayer_lab` binding may qualify the control mechanism in a disposable local
world. It requires the pinned process/socket and exact world/dimension with no remote server;
it supplies no second player or multiplayer evidence. A `remote` binding instead requires the
exact remote client/server observations. The two modes must refuse each other's state.

The `world` field pins the client's reported cosmetic label. A fresh remote Horizon client can
report an empty string; an explicitly pinned empty label is accepted as that observation, never
replaced with an invented server world name. The exact server address, client process generation,
own-client name, dimension and loaded/joined state remain required. These observations do not
authenticate a server world or detect every server-side world replacement at the same address.

The first action passage is attributed transcript or explicit text, a closed typed command,
validation, one serial Graph action, and a client-observed result. Unrecognized or ambiguous
instructions refuse. Text never becomes an arbitrary control command, shell command, administrator
command or MCP tool name. Speech capture, transcription and synthesis retain their own
[Echo](../../sepulcher/extensions/echo.md) boundary.

The adapter exposes `status` as a closed operational projection: client screen/dimension,
creative mode, frame/tick/chunk counters and finite performance measurements, selected renderer
identity/memory fields, and the pinned server's address/name/joined/loaded fields. Each exposed
leaf keeps its expected scalar or fixed-size numeric shape; an allowed key cannot carry an
arbitrary nested payload. Missing server data remains missing and malformed server identity
cannot become a single-player null binding. The raw status reply's debug/clipboard, keyboard
state, name tags and unrecognized fields never become returned observations, Graph state or
events. Binding checks and explicit status queries use the same projection boundary.

The adapter checks current session authority immediately before sending. It records an attempt
before the physical send, never automatically replays an action, and distinguishes refusal,
client-reported completion, cancellation and unknown outcome. A lost reply or process crash does
not prove that an effect failed. Process-local execution supplies no restart continuation,
durable Phylactery custody or server-authoritative world proof.

Every Run permits one attempt and no successor worker claim. Fencing any claim permanently
retires that Run identity in this adapter, including a nonzero delivery sequence; resuming or
replaying a failed claim requires a different profile with an explicit claim-aware handoff.

Local ownership records persist a fail-closed client-generation disposition. An interrupted or
unknown generation cannot be reopened merely by starting another controller or changing its
socket path. Admission of a successor requires that the prior client process generation has
ended, or explicit external reconciliation. These records prevent unsafe reuse; they do not
resume a Run, reconstruct a lost world outcome, or turn observations into placement receipts.

Cancellation fences new sends and uses a separate control connection to stop the owned client's
active action and release movement. Closing a waiting socket alone does not stop Horizon.
Cancellation completes only after the stop boundary is observed; otherwise the outcome remains
unknown. Stopping cannot undo a block already placed or movement already performed.

## Following and building

Following requires a separately bound, read-only position feed for the exact person being followed,
finite duration and distance bounds, and stop-on-lost-target behavior. An unordered list of player
positions cannot establish that identity. Building requires an admitted finite placement plan,
plot and inventory limits, and honest per-action outcomes; a spoken request for a house is not a
blueprint or proof of completion.

The first building qualification is `blockworld.horizon_build_step@1`: an explicitly admitted,
immutable one-cell or three-cell plan of ordinary `minecraft:oak_planks`, with exact integer
coordinates, plot, session, expected client labels/dimension, mode, expiry, placement and read
budgets, and a canonical content digest. Each cell is one fresh native Run. It shares the assist
service's session authority and attempt budget; a plan grants no selection, inventory rearrangement,
item creation, movement, administrator command or arbitrary material.

The initial plan read budget counts logical composition calls: eight per cell and at most 24
for three cells. A cell/inventory inspection performs one fresh state/status pair and its fixed
query under a combined timeout. Together with the effect's binding checks, a successful cell can
issue 26 read query lines; three cells can issue 78, plus admission reads. The adapter exposes
physical query counts separately. Containment has its own finite priority path and is never
refused because the plan used its read budget.

Preflight requires a loaded exact-air target, plain stone immediately below, an idle healthy
client in the admitted mode, the shared session's maximum distance and conservative eye reach,
and already selected ordinary planks with
enough held inventory. Offhand and carried stacks must be empty. The adapter emits only
`place X Y Z`, omitting `--item` because Horizon changes selection before some placement checks.
Survival requires the expected one-item consumption; explicitly admitted creative mode requires
the corresponding zero-consumption observation. A fresh cell/inventory/state read must agree with
the intended material and expected delta before the plan cursor advances. Existing blocks are
refusals, never credited as this bot's work. Any failed, changed, cancelled or unknown step stops
the plan without automatic replay or repair.

Horizon's stock placement primitive has no atomic expected-before/material/support comparison.
Its click is consumed on a later game tick, and its `ok` means any target state change. These
preflight reads therefore refuse **observed** changed conditions; they cannot exclude every
concurrent world change or interaction. The first live proof requires a dedicated controlled
disposable fixture without concurrent human input or entities around the cell. Records retain
client observations and partial effects honestly; they are not server receipts or an atomic
placement guarantee. A shared-world house plan needs further qualification or a guarded upstream
primitive. The explicit local assembly now registers this score only when supplied its shared
build service. Portable native-Run tests and real synthetic-game socket tests exercise one and
three cells, expected query counts, the last shared action slot, uncertain partial effects and
cancellation. Live placement remains a separate qualification.

The supervisor admits a successor cell only after the preceding native delivery reaches `DONE`
and its exact Run has a known build result. A report may have observed a cell before native
settlement; cancellation in that gap fences the whole plan. Operator instructions and capture
invalidate building authority synchronously, then settle the previous Run and effect before
continuing. A missing or unknown result disarms the controller. No cell resumes after restart.

## Perception and model proposals

The current action and behavior graphs use deterministic policy, without a planning model.
Speech recognition and synthesis do not observe the game. A future Mind passage must receive
explicitly attributed game observations; a model being available does not give it sight or
action authority. This passage can use the existing Animator, Dispatcher and Agent contracts
without adding a second model runtime or changing the Core execution contract.

The first perception target is a bounded structured sample: pinned client generation, session,
sample identity, observation interval, pose, health, held item and exact queried cells. Select
only required fields; a raw diagnostic status document may include unrelated host data. Missing
cells, unloaded terrain and unobserved players remain unknown. Exact cell queries must also
respect the dimension's vertical bounds: a horizontally resident chunk does not establish valid
height. Separate state and status replies are observations over an interval, not an atomic world
snapshot or authenticated server proof.

A finite reasoning step leases one exact capability and returns a typed proposal tied to the
provided sample. It receives no game effect tools, arbitrary command grammar or runtime lifecycle
authority. Hostile world labels, chat and other game text remain data. Missing, old or changed
observations require fresh observation rather than invented facts. Schema validity establishes
shape only; the proposal still needs independent session, freshness, bounds, material and action
admission. A model response never calls the effect port directly.

Qualification separates structured perception from pixel vision. A screenshot needs an owned
private destination, bounded capture and image validation, including the renderer's actual pixel
format. Seeing a captured image during an operator test does not establish native agent image
materialization. Before any broader autonomy, test observe, propose, validate, act and observe
again, including stale samples, unknown terrain, misleading game text, cancellation and a game
reply that reports success without the expected change. Measure reasoning separately; planning
does not belong in every idle or follow tick.

## Behavior graphs and idle

The intended supervisor selects finite behavior scores from explicit operator policy: handle a
spoken instruction, observe while idle, follow the bound target, or advance an admitted building
plan. Each invocation pins its trigger, session, deadline, action budget and stop conditions.
World events are observations, not instructions or authority. A missing or stale observation
stops the dependent behavior; it cannot justify invented player identity or world facts.

Idle means bounded observation or waiting for an admitted event. It grants no exploration,
building, inventory use or open-ended model loop. Effects during idle require a separately
selected finite task. Follow and build yield to explicit stop and new operator instructions;
replacing a task first settles or reconciles its active effect.

Scheduling coalesces repeated observations, uses bounded cadence and cooldowns, and avoids model
calls when deterministic policy can wait or select a known command. At most one effect owns the
client. Each tick or action receives a deadline and freshness bound, with finite retry policy for
reads and no replay of uncertain effects. Logs distinguish time waiting, speech inference,
reasoning, Graph execution and game response. Optimizations must preserve cancellation, authority
and outcome semantics, and be supported by measurements of the exact runtime profile.

The first behavior cut uses separate `blockworld.horizon_idle_tick@1` and
`blockworld.horizon_follow_tick@1` scores. Each tick is a fresh native Run with a pinned typed
trigger and at most one physical command, using the same assist policy and action budget as
operator commands. Nodes never submit a nested Run. The process-local supervisor owns cadence;
an in-memory timer is not a durable Graph wait or restart schedule.

An initial directive lasts at most 60 seconds and 60 ticks, at a cadence of at least one second.
One session admits at most 20 directives by default, with an explicit ceiling of 100.
Idle reads the bound bot and reports changes without movement, inventory use or model calls.
Follow additionally reads the exact target client's own pose through a query-only port; that
port has no action, stop or arbitrary-command operation. Both clients must have distinct pinned
processes and endpoints, and explicit `remote` bindings to the same server. Integrated-host LAN
and single-player associations are outside this first follow profile.

The engineering voice assembly explicitly opts its concrete target observer into owned read
settlement. If a tick expires or is interrupted during an already started target read, the
observer joins that read under its independent observation timeout, discards the late sample
and propagates the original cancellation. Replacement waits for settlement; neither the sample
nor cleanup extends effect authority. Whole-read timeout is twice the binding timeout, with
bounded connection cleanup, so teardown can finish after the behavior deadline.

Default direct observation still retires on cancellation. In both modes, actual timeout,
invalid identity, disconnect, malformed response or explicit closure permanently retires the
observer. It never reopens itself, discovers another player or reuses a cancelled sample.

Follow uses a stop-distance deadband and segments of at most four blocks, with a game action
timeout of at most one second. A target sample carries a local monotonic time, sequence and task
generation. Stale samples, health loss, loading, changed world/dimension/server, excessive
separation, elapsed task authority or exhausted budgets fence the task. Freshness and generation
are checked again immediately before action bytes are sent. A deadline watcher cancels an action
that outlives its sample or task; a command already handed off still requires containment.

One arbiter owns operator admission and ticks. Repeated tick requests coalesce to one pending
request; there is no catch-up backlog. Replacing a behavior invalidates its generation before
yielding, then settles the previous Run and owned effect before admitting a successor. Operator
commands take priority and clear the prior behavior. Unknown outcomes disarm the controller
instead of advancing a task. Explicit stop ends the session. Logs retain tick decisions, native
Run events, action/observation counts and monotonic timing; deterministic idle and follow use zero
model calls.

The stock `goto` dialect stops within 1.5 blocks of its waypoint. Follow accounts for that radius
when selecting a waypoint and requires a segment ceiling greater than 1.5 blocks; an already
reached waypoint cannot serve as evidence of movement toward the target. A successful response
remains a client report, including when pathfinding made no displacement.

After a client-reported follow completion, the tick reads the bot again before reporting progress.
The comparison starts at the pose validated immediately before the command was sent, and uses
the tick's original target sample. `moved` requires at least 0.05 blocks of observed progress
toward that sample, with a current in-bounds, healthy, idle client in the same world/dimension.
It does not establish that the target stayed there or that this command caused the displacement.
No progress stops the finite task rather than spending its remaining budget on repeated segments.
Missing, stale or changed post-observation stops while preserving the known client response and
leaving movement unverified. Counts include this extra logical read. A later operator instruction
requires ordinary fresh admission; no automatic retry follows.

The explicit local assembly registers these finite behavior scores only when supplied the shared
behavior service. Portable tests cover their native checkpoints and the supervisor's arbitration;
live two-client following remains a separate qualification. The initial one-action score alone
establishes neither following nor autonomous building. The separately supplied finite build
service starts with one-cell and three-cell qualification before a house blueprint.

## Qualification

The explicit checkout tools run as `python -m scripts.horizon_assist` for one typed/text action,
or `python -m scripts.blockworld_voice` for a supplied WAV or an Enter-to-record session. Their
help owns the exact option grammar. Normal application boot selects neither profile.

The private game profile binds `binding`, `policy`, `workspace` and nonempty `checkout_roots`.
The workspace is disjoint from every declared checkout in both directions; its profile and
evidence stay inside it. The speech entry additionally receives an exact local speech profile.
Both profiles must refer to the same private evidence workspace. The operator pins the actual
client PID/start ticks, socket, world/dimension, mode, finite bounds, action budget and expiry.

The initial command grammar supports `state`/`stav`, `status`, `goto`/`choď X Y Z`,
`look-at`/`pozri X Y Z`, and `say`/`povedz TEXT`. Coordinates must be explicit finite numbers;
unknown wording refuses. This parser uses no LLM and promises no free-form language understanding.
`stop`, `quit` or SIGINT ends the voice session and fences future sends. A new explicit session
is required afterward. Spoken stop supplements the independent keyboard/control stop; transcription
quality is not a guarantee that an emergency word will be recognized.

The behavior-enabled voice entry additionally recognizes exact `idle`/`čakaj`/`čekej` and
`follow me`/`nasleduj ma`/`následuj mě` phrases. A finite `--behavior-seconds` duration defaults to
30 seconds. Idle can observe the explicit single-player lab. Follow requires an additional
`--target-profile` inside the same private workspace: a closed JSON object with only `binding`,
using the same binding fields as the bot profile. It grants query access only. Both bindings must
be remote with matching expected world labels, dimension and server address, and different clients
and endpoints. Starting
capture interrupts and settles a previous behavior before the microphone opens.

An optional `--build-plan` supplies a private JSON `BuildPlan` inside that same workspace.
Duplicate keys, nonfinite numbers and oversized documents refuse. The exact phrase
`build approved plan` or `postav schválený plán` admits those frozen bytes once; it cannot generate
coordinates or materials from speech. The plan pins the existing session and expires within its
authority; its finite duration is at most 60 seconds. The game policy must explicitly permit
`place`, and the binding timeout must be at least six seconds for Horizon's fixed five-second
placement task. `place` remains absent from the general typed/text action grammar. The voice
source-file mode joins the finite build before closing; interactive capture interrupts it.

The voice entry writes source WAV, attributed transcript, native events and a monotonic stage
timing receipt privately. It presents fixed Slovak/Czech/English wording for the retained outcome:
task start, client report, refusal and unknown effect remain distinct. Unchanged idle ticks keep
their private events and records without repeated console announcements. Pre-capture settlement
has its own timing field. For a one-action command, the Graph stage includes native admission,
game work and event custody. For a background behavior or build, it measures only acceptance and
scheduling; each tick or cell has separate native events, elapsed time and process CPU in its
supervisor record. Reply generation can overlap that accepted background work. Source-file mode
joins the finite task before closing, but the utterance's Graph timing is not its completion time.

Optional replies produce a WAV and generation facts with playback `not_attempted`. Explicit
`--play-replies`, together with `--reply-language`, additionally invokes a fixed local player on
those validated bounded bytes after capture has closed. Player exit is recorded separately as
`player_exited`, not human hearing. Playback has its own timing. Stop joins the owned process
group; a late process launch is adopted and retired without audio even after its work deadline.
Required OS ownership settlement may exceed that deadline. Unproven player retirement ends the
session and keeps capture closed. This helper is not native Echo playback admission or a physical
speaker qualification.
The shared [local player](../../sepulcher/extensions/echo-local-probe.md#probe-contract) uses
the host's ALSA `default` output unless `pulse` is explicitly selected at its helper boundary.
There is no device fallback, routing change or volume adjustment.

An optional synthesis or settled player failure preserves the game result and records the failed
reply stage without replay. Synthesis observations remain generation facts; later playback is a
separate observation. Capture starts only after the person explicitly requests that finite
recording, with active/off indicators. Continuous microphone listening, conversational barge-in
and automatic music ducking are outside this profile.
The shared recorder distinguishes a failed recording with proved group retirement from unknown
ownership. The former permits a fresh explicit gesture; the latter reports unknown and fences
this session before another capture or reply. Cancellation during final retirement still
propagates after settlement. An uncertain recorder never produces a normal off indication.

Portable tests must cover command refusal, endpoint exclusivity, identity and bounds changes,
cancel-before-send, stop during a waiting action, lost replies and absence of automatic replay.
Live qualification uses a disposable world and a dedicated client. The operator verifies
microphone capture, transcript meaning, audible playback, movement, interruption and later
collaborative play. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
owns delivery evidence; this contract alone does not establish a working adapter.
