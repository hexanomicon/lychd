# Blockworld companion delivery client

**Unofficial Minecraft integration. Neither Mojang nor Microsoft approves or is associated with this project.**

Publisher: LychD contributors · Contact: [hexanomicon@proton.me](mailto:hexanomicon@proton.me).

Experimental dedicated-server Fabric actuator for the [Companion lab](../../docs/compositions/blockworld/companion-lab.md).
LychD owns interpretation and native Runs. The protocol-1 envelope carries state, look, goto,
follow, idle, say and stop, plus the explicit `inspect@1` read profile. Existing operation and
pose JSON shapes remain unchanged; inspection has revision-1 integer arguments and a distinct
closed `blockworld.cell@1` observation. `applied` acknowledges controller
activation, including a follow controller waiting nearby; it does not establish movement or
destination completion.

The separately authorized `weather@1` operation sets shared server weather to clear or rain
with a fixed 600-tick timer programme. Its closed `server_weather` scope is global to
weather-capable dimensions; the overworld is an observation anchor. It requires explicit host
`--allow-weather`, native `blockworld:weather` scope and independent server `allow_weather`.
All defaults deny it. A separate weather owner dispatches beside the wolf controller: it does
not replace or renew NPC control. The engine weather-advancement rule must be enabled; the
operation never changes it. A dedicated `blockworld.weather@1` readback confirms flags and
timers. Queued weather is cancelled by stop; already applied weather is not rolled back.
Natural weather cycling after the programmed timer can include thunder. This is neither a
wall-clock duration nor a promise to restore earlier conditions.

The independent `time@1` operation places the `minecraft:overworld` clock at the next or equal
day marker (1000) or night marker (13000). Toggle selects night below phase `12000` and day otherwise.
Host `--allow-time`/`blockworld:time` and server `allow_time` are separate, default-deny grants.
The current clock, timeline, markers and dimension profile must match before mutation. Numeric
time values, console commands and gamerule changes are not accepted. Existing rate, pause and
advancement settings survive; an equal marker preserves the fraction, while a positive placement
resets it to zero. A dedicated `blockworld.clock@1` readback confirms placement and its settings.
An uncertain readback remains `unknown`, with no duplicate execution. NPC leases, simulation ticks
and weather remain separate. Stop cancels queued placements and cannot undo an applied one.
This forward policy can advance calendar/moon counts: day at phase `1001` advances `23999` ticks;
linked schedules outside the overworld can also change. It does not guarantee future cycling
or visible brightness for every datapack.

`inspect` reads one complete integer-addressed block state in an already loaded chunk, including
its registry identifier and properties. Both cell corners must lie in the box, and its integer
origin must lie within 16 blocks of the current owned actor. The server checks build height and
world border, then uses `getChunkNow` without requesting a load. A typed unavailable observation
and `refused` result distinguish an unloaded cell from observed air. Inspection preserves valid
active controller identity and expiry; it grants no building or inventory capability. Old servers
may refuse this new operation; clients must not substitute state or replay it after uncertainty.

The fixed build tuple is Minecraft 26.3, Fabric Loader 0.19.5, Fabric API 0.163.0+26.3,
Loom 1.18.4, Gradle 9.7.1 and Java 25. The wrapper validates the Gradle distribution's
SHA-256. Build and test with a dedicated Java 25 installation:

```sh
./gradlew --no-daemon --max-workers=2 test build
```

Install the built mod jar and the exact Fabric API in an ordinary dedicated Fabric server.
There is no client mod, custom entity, renderer, inference dependency or GPU requirement.
Dedicated-server startup and actual movement/restart need a separate live receipt; unit tests
and compilation alone do not qualify those behaviors.

The real controller has a separate opt-in server GameTest profile:

```sh
./gradlew --no-daemon --max-workers=2 -PcontrollerGameTest=true test build
```

This adds a test-only mod/source set and runs one sequential fixture in a new disposable world
under `build/run/controller-gametest/<random-id>/` on every invocation. The production mod jar
contains neither the fixture nor its accessor Mixin. The profile needs no renderer, client,
private bridge configuration, HTTP listener or model. It uses two JVM processors and at most
1536 MiB of GameTest heap. It does not auto-accept the Minecraft EULA.

The fixture creates a safe flat arena in one home chunk in the engine's active test region,
then registers a synthetic player through Minecraft's actual player list. It drives the unchanged
production controller and mailbox at `START_SERVER_TICK`, with real navigation and wolf physics.
Its assertions distinguish accepted follow from displacement, approach, waiting and resuming;
challenge unreachable navigation, non-replacing state/chat/cell reads, queued and active expiry, excess
target distance, target loss/death and priority stop with correlated acknowledgement. Lease time
is an explicit synthetic clock advancing 50 ms at each controller tick: GameTestServer sprints
ticks, so this profile does not measure real-time server latency. The controller's ordinary
bounded supporting chunk halo remains an engine requirement.

The fixture also reads a real log with a non-default axis, air, and a changed target state during
following. It challenges a distant read without a chunk load, cancelled/expired queued reads,
and retained duplicate identity. The loaded-world fixture does not exercise the unloaded-cell
branch; the typed availability contract has separate transport tests.

The real-controller fixture also applies weather directly through the production composite
during the existing short follow. It checks engine readback, unchanged follow identity and the
original expiry oracle, then restores weather and its advancement rule. This direct-dispatch
continuity probe is separate from weather HTTP/mailbox qualification.

Run the separate global-weather fixture with `-PweatherGameTest=true test build`. Select one
GameTest profile per invocation; selecting multiple profiles refuses. Its fresh world and sole weather
entrypoint exercise exact clear/rain timer readback, 600-tick advancement and natural transitions,
disabled capability/rule refusals, retained duplicates and queued versus applied stop semantics.
Its NPC is explicitly fake. It restores all five weather fields and the advancement rule on
terminal cleanup; the production artifact contains neither fixture.

Run the independent clock fixture with `-PclockGameTest=true test build`. Its fresh world uses
the actual engine clock with explicitly fake NPC control. It checks day/night/toggle boundaries,
equal-marker fractions, negative/overflow refusal, disabled permission, incompatible read-only
timeline/dimension profiles, all combinations of rate `1`/`0`/`-0.5`, pause and advancement settings,
mailbox deduplication, stop and expiry. Other clocks, simulation and weather stay unchanged;
fixture cleanup restores the complete clock snapshot, fraction, rate, pause and advancement rule.
The real-controller fixture also applies clock placement directly through the production composite
during the original short follow, preserving its identity and original expiry oracle. This
continuity probe is separate from clock HTTP qualification. The production JAR excludes fixtures.

`controller-observations.json` in that run directory retains finite ticks, time, coordinates,
identities, generation, navigation and cleanup observations. Per-test terminal listeners cover
success, failure and timeout, with server stopping as a fallback; owned players and the exact
wolf are removed and the controller ticket released, while the world reservation is retained.
This qualifies synthetic server-side follow only. Authenticated-human joining/following,
wrong-dimension transfer, navigation across chunks, microphone, playback and listening need
separate evidence. Existing saved worlds and operator configuration are never test inputs.

## Private configuration

Without `config/lychd-bridge.json`, the bridge registers no server callbacks, creates no actor
and starts no listener. Invalid configuration fails startup with a value-free error.
Keep this file and its randomly generated private bearer token outside the checkout:

```json
{
  "protocol": 1,
  "token": "REPLACE_WITH_64_LOWERCASE_HEX_CHARACTERS",
  "port": 18184,
  "actor_id": "REPLACE_WITH_A_CANONICAL_UUID",
  "spawn_actor": true,
  "spawn_x": 0,
  "spawn_z": 0,
  "radius": 24,
  "max_actions": 256,
  "follow_stop_distance": 2,
  "follow_resume_distance": 3,
  "allow_weather": false,
  "allow_time": false
}
```

The placeholders deliberately form invalid configuration. Generate the real values privately;
never place a working token in documentation, logs or command-line arguments. The only binding
is IPv4 `127.0.0.1`. Request bodies are at most 8192 bytes, responses at most 65536 bytes,
the ordinary FIFO at most eight entries and retained ordinary identities at most 256 per boot.
Stop identities have a separate history of 256 entries, independent of `max_actions`. Neither
history evicts identities: identical request bytes return their retained result, changed content
and action/stop identity collisions return HTTP 409, including after capacity is exhausted.
Records are process-local and never authorize replay after uncertain acknowledgement or restart.

The follow distances are optional private server settings in blocks; omitted values default
to `follow_stop_distance = 2` and `follow_resume_distance = 3`. Both must be original finite
JSON numbers satisfying `0.5 <= follow_stop_distance < follow_resume_distance <= 8`. Unknown
configuration keys still refuse startup, and validation errors never include private values.
`allow_weather` is an optional original JSON boolean and defaults false. Enabling it grants only
the typed weather operation; it supplies no administrator, console, building or clock authority.
`allow_time` is a separate optional original JSON boolean, default false, granting only the closed
clock operation. Neither setting grants the other capability.

The bridge uses JDK HttpServer with two bounded workers and a finite dispatch queue. The JDK
exposes its connection/header/time limits process-wide. This opt-in profile sets five-second
request/response defaults, 32 connections, four idle connections and bounded headers before
creating its server. When another mod initializes JDK HttpServer first, configure the same
properties at JVM startup: `sun.net.httpserver.maxReqTime=5`,
`sun.net.httpserver.maxRspTime=5`, `jdk.httpserver.maxConnections=32`,
`sun.net.httpserver.maxIdleConnections=4`, `sun.net.httpserver.maxReqHeaders=32` and
`sun.net.httpserver.maxReqHeaderSize=8192`. The JDK timer has implementation-defined granularity.
Priority stop bypasses ordinary action retention and FIFO capacity. The HTTP service is not a
protection against a local process deliberately exhausting its listener or worker capacity.

## Actor and lifecycle

The actor is a named persistent vanilla Wolf in the overworld with the configured UUID.
Protocol 1 `yaw` and `pitch` report NPC head gaze; body heading is not exposed.
The bridge owns one transient entity-ticking ticket anchored at the fixed home chunk, with
Minecraft's bounded supporting halo. Vanilla entity ticking needs the radius-two support window
and normal chunk-generation dependencies; this is not a promise that only one chunk is loaded.
The ticket uses a private per-controller type with loading, simulation and keep-dimension-active
flags, without persistence. It is installed before home loading, removed on constructor or bridge
initialization failure, and released after stopping the controller on server shutdown. No persistent
forced-chunk entry is created, and unrelated tickets remain untouched. The anchor never follows
the actor or searches arbitrary chunks. The created reservation lives in the world at
`data/lychd-companion-created.marker`, containing that UUID. It is created and forced to disk
before initial spawn. Keep it with the world: removing it grants first-create eligibility again.
A crash between reservation and entity persistence can leave an unavailable actor; the bridge
refuses to create a replacement under the retained reservation. A changed/malformed reservation
fails startup. A wolf unloaded outside the retained home support remains unavailable until normally loaded.

The owned wolf's vanilla goals are cleared on creation and reattachment. Minecraft 26.3 exposes
a public movement-goal API but no public target-selector accessor, so one focused Mixin accesses
only `Mob.targetSelector`. Owner/anger targets are cleared to prevent competing combat or owner
teleport behavior. Ordinary navigation and physics stay enabled. This grants no immunity from
falling, damage, unloading or death. No blanket `NoAI` or invulnerability is used.

Requests bind protocol, boot, actor, Run, identity, stop generation and a deadline at most 60
seconds away. Identical full request bytes return the retained result; changed content conflicts.
Point requests are checked against the cached issuance position and configured box, then checked
again on the server tick. Paths must stay inside the control box; following requires an exact
online player UUID in the overworld, within 16 blocks and inside the box. Path queries use the
existing loaded chunk cache; no exploration/teleport is admitted. A finished goto or failed path
returns to quiet idle without claiming destination success.

Following starts waiting when the target is within the resume distance, without requiring a path
to the player's exact position. A pursuing companion stops its navigation at or inside the stop
distance, then waits until separation exceeds the larger resume distance. Between those distances
it retains its prior pursuing or waiting state. Waiting preserves the active follow identity,
target and finite lease, so a short walk can resume navigation. Target loss, excess separation,
actor/bounds checks and lease expiry still end the controller; the distance band widens none of
those limits. Human multiplayer follow remains a separate live qualification.

Stop advances the generation under the admission lock, cancels ordinary queued work and reserves
one entry in its independent stop history. Its server-thread barrier clears navigation/controller
before any ordinary mailbox work and only then records `applied`. A later fresh generation command may run
on that same tick. The stop observation captures the barrier; final cached state can therefore
already show that explicitly new command. A newer stop superseding a pending barrier settles
the earlier stop as `cancelled`, with no applied observation; both identities remain queryable.
Stop admission bypasses a full ordinary FIFO or ordinary identity history.

Admitting the 256th stop permanently seals new ordinary admission for that server boot. That
final stop still runs its priority barrier and receives its tick acknowledgement. Further unknown
stop or ordinary identities receive HTTP 503, while retained identities remain queryable and
identical requests remain idempotent. An explicit server restart starts a new boot identity and
fresh histories; no automatic eviction or reopening occurs. Server shutdown closes admission,
stops the owned controller and releases its transient home ticket.

The production JAR includes `META-INF/LICENSE` and `META-INF/MINECRAFT-NOTICE.txt`.
Source publication excludes Gradle caches, game engines/assets, model weights and private
profiles or recordings. Before distributing a compiled mod, provide and identify its exact
corresponding source revision; the development version alone is insufficient.
