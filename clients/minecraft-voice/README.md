# Optional local voice client

**Unofficial Minecraft integration. Neither Mojang nor Microsoft approves or is associated with this project.**

Publisher: LychD contributors · Contact: [hexanomicon@proton.me](mailto:hexanomicon@proton.me).

This separate Fabric **client-only** artifact projects the experimental Companion lab's private
local control protocol. The dedicated-server actuator remains a different installation. This
client sends no credentials, recognition text or audio through Minecraft packets or chat; it
does not record audio itself. The separately opted-in local console owns finite recording,
interpretation, native work, playback and their evidence.

The pinned tuple is Minecraft 26.3, Fabric Loader 0.19.5, Fabric API 0.163.0+26.3, Loom 1.18.4,
Gradle 9.7.1 and Java 25. Reuse the adjacent server project's wrapper; this project has no wrapper:

```sh
../minecraft/gradlew --project-dir . --no-daemon --max-workers=1 test build
```

Dependency locks bind that exact tuple; checksum verification uses the same reviewed dependency
trust as the adjacent server project. Build and pure-Java tests establish no runtime
qualification. The separate [software-client receipt](../../tests/fixtures/blockworld/companion-cpu-runtime.json)
records actual initialization and synthetic GameTest keys/menu transitions on Vulkan llvmpipe.
Physical keys/focus, human microphone capture, playback and hearing remain unqualified. The
current multiline HUD was checked at 640×480 (320×240 scaled GUI) with the default font: five
display cases cover three mixed-result payloads, SK/CS/EN labels and a 400-character unbroken
feedback fixture. Full screenshots were inspected after initial vanilla join toasts retired.
Other fonts and visibility beneath transient overlays remain unqualified.

Without `config/lychd-voice.json` inside the chosen Minecraft instance, the client registers no
effective controls or lifecycle callbacks, starts no workers and makes no HTTP requests. A
present invalid profile fails initialization with a value-free error. The file is read once;
restart the client after changing it. Keep real profiles and tokens outside this repository.
The following deliberately invalid placeholders are an example shape, not a working profile:

```json
{
  "protocol": 1,
  "endpoint": "http://127.0.0.1:18186",
  "token": "REPLACE_WITH_A_NEW_64_LOWERCASE_HEX_CONTROL_TOKEN",
  "server_address": "127.0.0.1:25572",
  "player_id": "REPLACE_WITH_THE_LOCAL_PLAYER_CANONICAL_UUID",
  "record_seconds": 3
}
```

This is the separately generated **console control** token, never the dedicated actuator token.
The local console must explicitly opt into the same control profile. Held input additionally
requires a local speech profile and an explicit console maximum: `--hold-seconds 15` enables
a fifteen-second hold. The option accepts 1–15 whole seconds without changing the six-field
profile or `record_seconds`. The endpoint permits only literal IPv4 `127.0.0.1` and an explicit
port, with no URL path, userinfo, query or fragment.
`server_address` is only an exact local context comparison with Minecraft's current server
address; it never chooses the HTTP destination or the console's follow target. `player_id`
must equal the actual local player's UUID. Remote multiplayer capture remains unqualified.

Linux/POSIX file custody is required: the regular non-symlink profile is owned by the current
user, has no group/other permission bits and is at most 4096 bytes. Its direct config directory
must be a non-symlink current-user-owned directory without group/other write permission. The
read uses no-follow open and before/after identity, size and modification checks. Custody does
not defend against a malicious process running as that same user; Windows custody is unqualified.

All three mappings start **unbound**: fixed-duration recording, held push-to-talk and stop.
Select each key under normal Controls → LychD local voice in the private Minecraft instance;
no particular key is a universal default. Existing chosen record and stop bindings keep their
meanings. Choose a keyboard function key, Pause, Print Screen or Scroll Lock for stop if it
must work inside menus/text entry. Other keyboard keys can stop while gameplay has no
screen/overlay. Mouse bindings use vanilla mapping state only during gameplay. Stop keeps
priority over capture, including a shared stop binding.

A fresh fixed-record press requests one finite capture using the profile's 1–15 second duration.
A held-input press requests capture; release finishes that same voice occurrence for
transcription and native admission. It needs at least 250 milliseconds of usable captured PCM.
A release before capture arms, or the maximum duration reached without release, discards the
utterance. Neither capture key repeats while held. Continuous listening and wake words remain
unimplemented; the client needs no global keyboard hook or administrator privileges.

Recording additionally needs the matched server/player, active window, unpaused current world,
no screen or overlay and a control view no older than 1500 ms that allows recording. Menu,
pause, focus, world, session or observed host-context changes suppress the held release and
require releasing all three controls before another fresh edge. A press made while ineligible
is never replayed later. Remapping while held is not a supported way to produce a fresh physical
edge; release first. The console's `:target` selects later input; an already-owned hold retains
its captured target. A host-context change can trigger client cancellation only after the
client observes it.

Each gesture gets its original UUID, session/context/generation and deadlines before any worker
wait. A queued record is cancelled when its original client epoch is invalidated; delayed work
never renews its 3 second admission window or instruction expiry. The full instruction lifetime
must fit the remaining session at both press and dispatch; it is never shortened to fit.
Menu, pause, focus, world or observed host-context boundaries with an outstanding dispatched
gesture make one best-effort stop request through the independently reserved worker. This does
not establish that a disconnected console or microphone stopped; the host's hard finite
capture still bounds the attempt.

Ordinary work, held release and stop use separate single-worker, one-entry-queue lanes. A blocked
start exchange cannot occupy the reserved release or stop lane. A release keeps the original
hold envelope and UUID, with a separate three-second forwarding window capped by the original
instruction expiry. Neither phase can renew the instruction, and a release received before its
start leaves a bounded tombstone that prevents delayed capture. HTTP uses fresh direct
IPv4 sockets, exact Host and bearer headers, a 2 second complete-exchange budget, bounded framing
and typed JSON, and no proxies, redirect following or mutation retries. Unknown acknowledgement
only permits lookup of the original UUID. One poll is in flight at a time and polls start at most
twice per second. A record attempt's lookup window is capped by session expiry and its original
instruction expiry plus 60 seconds; timeout seals new recording and retains unknown settlement.
Session expiry also ends context polling. Fresh stop can still use the last known original
session after expiry to retire already-owned audio; its own lookup window is bounded to 60
seconds from the original stop press. Neither deadline is renewed. A changed console session
requires restarting this client, preventing automatic reconnection/replay. A retired unknown
stop seals further stop attempts; it never authorizes repeating that mutation with a new UUID.
After stop, a fresh capture additionally needs its known retained result and a current state
containing that exact known stop. Exhausted finite client histories also prevent new admission.

The local multiline HUD shows a short gesture UUID and closed Slovak, Czech or English stages,
using English for other languages. `requested` and HTTP 202/pending do not mean that the
microphone is active or the game applied an action. Held `recording` reports the host's first
observed PCM; `finishing` reports recorder retirement after release. These are separate from
physical microphone and hearing proof. Game result, reply generation, playback and
evidence results remain separate, including when a known game result has a failed spoken reply.
Host-fixed feedback is bounded, checked for control/formatting characters and rendered literally.
No transcript is available. Playback-player exit does not establish that a person heard audio.
Missing reported outcome fields say “not reported”; they do not imply success. The panel wraps
with the current game font and scaled GUI dimensions. If the complete result cannot fit, an
own-ID notice asks for more display space and points to the foreground LychD console; it never
shows only a successful subset. Below the notice's own minimum space, it draws nothing. Vanilla
HUD hiding and menus hide the panel. The view reads only the currently owned controller result;
a context/focus transition clears the old projection. Client shutdown disables ingress, drains the
reserved best-effort stop lane within a finite budget, closes network channels and joins workers
within a finite budget; a timeout makes no device-off or applied-stop claim.

The pure Java regression sources cover strict protocol/profile parsing, bounded HTTP framing,
original gesture identity/deadlines, focus/menu/context edge suppression, same-binding stop
priority, independent bounded workers, queued-record cancellation, lost response lookup and
separate HUD outcome labels. They need no Minecraft renderer, audio, GPU or external service.

## Actual-client fixture

The explicit `-PclientControlGameTest=true` property adds the separate official Fabric client
GameTest source set and `runClientGameTest` task. Compile the fixture without starting a game:

```sh
../minecraft/gradlew --project-dir . --no-daemon --max-workers=1 \
  -PclientControlGameTest=true gametestClasses
```

Runtime needs a controlled launcher: both working directory and game directory must be disposable,
with a fresh private synthetic profile present before the production initializer. Use username
`LychdProbe`, its offline UUID `23b3ecc2-026f-3a15-a197-ac0e44cdc79f`, profile server address
`localhost:25573`, and the fixture's loopback control port 18186. The default GameTest preparation
deletes its run directory; prepare the profile after that step and before Java starts. The fixture
does not provision a real operator profile or replay initialization. The lab's private qualification
launcher and platform isolation are separate from this source fixture.

The sequential test observes the original initialized controller, registered mappings and untouched
ticks. It holds synthetic F8/F9 input across actual polling, checks menu/context release barriers,
same-binding stop priority, independent stop ingress during a blocked ordinary exchange, an own-ID
panel and real world disconnect. Five complete display cases use actual font wrapping, passive
text-submission bounds and inspected screenshots, with fresh observations after language changes
and F1 recovery. F1/menu absence windows also require GUI extraction progress. Its local protocol
fixture returns synthetic mixed game/reply/playback/evidence results; it makes
no native host command, microphone, synthesis or playback request. Success requires the completed
scenario chain, normal framework exit and a new `lychd-client-control-audit.json` from the actual
client-stopping event, registered by a passive production-init observer after production's stop hook.
The original five-record/four-stop chain completes before a separate reconnect exercises synthetic
Num Enter: one hold across polls, one original-ID release and a second hold cancelled by menu entry
without release or replay. The final audit requires five fixed records, two holds, one release,
five total stops including one held cancellation, and retired workers. Test classes/resources are absent
from the default binary and source jars. Fabric replaces input/focus handling for this test, so
its result cannot qualify physical keys, focus, a human microphone or hearing.

The production JAR includes `META-INF/LICENSE` and `META-INF/MINECRAFT-NOTICE.txt`.
Source publication excludes Gradle caches, game engines/assets, model weights and private
profiles or recordings. Before distributing a compiled mod, provide and identify its exact
corresponding source revision; the development version alone is insufficient.
