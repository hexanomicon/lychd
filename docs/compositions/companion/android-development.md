---
title: Companion Android Development
icon: material/android
---

# :material-android: Companion Android Development

The first implementation lives in [the Android client](https://github.com/hexanomicon/lychd/tree/main/clients/android).
It provides a native Kotlin/Compose development screen, a schema-derived Bridge fixture, and
bounded foreground microphone capture with local replay. [State of Work](../../state-of-the-work.md#companion-android-client)
owns its delivery boundary. [Android Foundation](android-foundation.md) retains the researched
live-client direction and its host prerequisites. [Access and Views](access-and-views.md) applies
the accepted account and working-interface rules to this client.

## Running the slice

Follow the client [build and installation instructions](https://github.com/hexanomicon/lychd/blob/main/clients/android/README.md).
The debug application has a separate `.dev` identity. Open Companion, type words, mark them
reviewed, and send. The reply explicitly identifies itself as a development fixture. Refresh reads
the fixture conversation; New conversation starts a separate local fixture session. These actions
exercise the current Bridge JSON dialect without performing a native Companion handoff or
admitting host work.

Start recording requests Android microphone permission. Stop recording finishes a mono PCM16
WAV at 16 kHz. Capture stops automatically at 15 seconds, with a second byte cap of 512 KiB
including the WAV header. Replay plays that local recording through Media3; Discard removes it.
The words editor is manual: recording does not fill it, and replay is not synthesized speech.

On `onStop`—including the normal background/lock route—the client stops capture and replay,
attempts to discard its current recording, and fences late callbacks. Activity destruction closes audio
resources. Rotation may retain the ViewModel's draft while discarding audio. This boundary is
`onStop`; the implementation does not claim capture ends merely on `onPause` or against every
Samsung-specific lifecycle condition before a handset probe.

## Local device status

Local diagnostics are independent of host working views and remain available in debug and
release. They sample Android API level, microphone hardware and this app's permission, available
space on the app-data filesystem, battery level/charging, and power-save mode. Refresh runs on
foreground return or an explicit request. Backgrounding marks the snapshot stale and fences
late reads; one failed probe leaves its field unknown without discarding the other observations.
Snapshots stay in memory on the phone and are not uploaded or logged.

Troubleshooting distinguishes reported facts from operational proof. Microphone permission does
not establish working capture or the global Mic access setting. Available filesystem space does
not inventory media or guarantee a later write. Low-space and battery notices are local advice,
using 32 MiB and 15 percent thresholds. An explicit app-settings button can help restore this
app's microphone permission; checking status never requests permission or starts recording.
Unavailable settings navigation leaves a visible local message.

The pure JVM diagnostics model and lifecycle monitor belong to `core`; Android reads and the
status card belong to `app`. These local observations are not a Familiar admission record, Ward
projection, remote diagnostic service, or phone-administration interface. New integrations must
add their own bounded observations and admitted actions rather than turning a status check into
an automatic repair.

## Code and contract ownership

| Path | Responsibility |
| --- | --- |
| `clients/android/app` | Compose views, lifecycle and permission handling, testable handset interaction, AudioRecord capture and Media3 replay adapters. |
| `clients/android/core` | Local Bridge state, bounded Ktor transport, explicitly in-process HTTP fixture, local presentation offers, local diagnostics/advice and foreground sampling lifecycle. |
| `clients/android/tools/generate_wire.py` | Deterministic Kotlin wire models and JSON token-shape checks from the current Altar OpenAPI export. |
| `clients/web/openapi.json` | Existing host-owned transport schema; Android does not own a second copy. |
| `clients/android/gradle/libs.versions.toml` | Pinned direct build and library versions. |

One pure JVM `core` module permits protocol tests without an Android SDK; it does not introduce
a shared Android/iOS UI or a new domain authority. The generated fields preserve required
nullable fields and supplied defaults. Optional fields with no schema default use nullable local
representation; generated token-shape checks run before decoding so quoted numbers and explicit
null cannot stand in for their schema-owned types. Object/array error extras stay opaque.
Generated shape evidence does not establish authentication, authorization, valid state transitions,
or recovery.

The HTTP fixture uses Ktor MockEngine at a reserved `.invalid` origin. No live-engine factory,
URL editor, cookie store, credential, Internet permission, analytics SDK, retry plugin, or audio
upload exists. CIO is a candidate for a later tested TLS/Keystore transport. The host's current
loopback possession credential must not be copied into the client or exposed over LAN/VPN.

## Local state and custody

Bridge state and fixture records live only in memory. A submission uses a fresh request UUID;
review binds the exact current words and presentation context. An edit invalidates it even when
the text later returns to the same string; withdrawing and granting review again requires a new
Send. Rendered work controls retain their originating presentation generation, so an old control
cannot edit, review, submit, record or replay in a replacement context.

After a successful submission, the client reads the session snapshot. If acknowledgement is missing or malformed,
mark the outcome unknown and block further sends in that session. Matching text during Refresh
cannot prove the missing outcome. An explicit new session clears this local latch, but the fixture
has no durable request lookup.

Cancellation, background invalidation, new session and close fence stale responses. Explicit
presentation-context replacement also clears history, draft and review state from the local
projection. Disposing of that state does not settle the original external outcome, and there are
no automatic retries.
Caller cancellation propagates through transport and local interaction while an unacknowledged
submission remains unknown. The transport's own 15-second deadline is a bounded request failure;
it does not turn a cancelled caller into a successful return.

Drafts are limited to 100,000 characters and 256 KiB of UTF-8, responses to 512 KiB, session
history to 128 turns and each HTTP action to 15 seconds. The fixture caps its memory holdings and
HTTP history; reaching its development limit requires restarting the app. It checks serialized
acknowledgement and full snapshot bounds before admitting a new fixture message, including JSON
escaping and accumulated history. Request UUID spelling does not create a second admission.
These are local bounds, not host admission policy.

## Access-aware presentation

The accepted IAM design already permits different working views for different accounts and
contexts. The client now has a closed local policy for Conversation, Words and Local recording,
with separate open, refresh, edit, review, send, record and replay offers. Compose and interaction
handlers consult the same policy. Missing policy offers no work. A read-only offer cannot create
a conversation through startup or the Refresh fallback; an offered screen alone grants no action.
Queued actions and callbacks must still belong to the current presentation generation.

The debug build uses explicitly labelled development offers; release starts unavailable. There
is no account picker, Role parser or live Ward projection adapter. Replacing the policy disposes
of the old local context and stops audio. Stop, discard and cleanup retry remain callable after
work offers disappear. This is a client integration seam and does not deliver remote identity,
object authorization or profile management.

## Audio custody

Keep audio only in the app's `noBackupFilesDir/companion-recordings` directory. The manifest
disables backup and explicitly excludes cloud/device transfer. During capture, cancellation
closes the recorder and attempts to remove partial or unclaimed completed files. A bounded retry
guard blocks another capture if disposal fails. Successful stop transfers file cleanup to the
interaction controller.

Background/discard then attempts deletion of that transferred recording. Make a failed deletion
visible, retain it for bounded retry, and prevent another recording until cleanup succeeds.
Overflow asks for a process restart so startup cleanup can recover the abandoned directory.
At process startup, the recorder's IO initialization removes abandoned `capture-*.wav` files
from an earlier process; the first recording waits for cleanup. This is ordinary file deletion,
not a secure-erasure or flash-forensics guarantee. Partial/unclaimed and transferred-file cleanup
share the visible capture guard. Cleanup failure survives adapter destruction and late start
cancellation or storage failure; releasing the recorder does not discharge its byte custody.
No recording supplies training permission.

The controller observes capture completion and early failure directly rather than waiting for the
display timer or a user stop. Playback callbacks distinguish a replay request from Media3's
playing state and clear it on end/error. These are local adapter facts, not physical delivery or
remote voice settlement.

Process death may clear the draft/conversation and leave audio until the next successful startup
cleanup. The app has no retained conversation database or reboot recovery. Its local microphone
and replay facts are not Echo transcription, synthesis or delivery receipts.

## Verification and remaining probes

Core tests exercise the fixture's actual JSON routes, duplicate/conflicting request behavior,
invalid input, bounded bodies, malformed/null/enum replies, framework errors, lost acknowledgement,
local state races and stale responses. The WAV tests exercise sample/header correctness, byte and
duration bounds, empty capture, cancellation, completion races and custody transfer. Generator
tests exercise required/null/default fidelity, reference closure and unsupported schema refusal.
Presentation and controller tests exercise unavailable/read-only offers, direct-call denial,
queued actions, context loss, early audio failures, late callbacks and cleanup across adapter
destruction. Cleanup retry cannot erase a current recording-failure message or resurrect a closed
owner's recorder.
Android lint and an APK build verify platform compilation; they do not operate a microphone.
The initial reviewed aggregate passed **31 Bridge tests, 12 presentation tests, 24 controller tests,
17 audio tests, five deletion-recovery tests and nine generator tests**—98 client tests in total—
Android lint with no issues, and the debug APK build. Lockfiles retain the
resolved dependency graph. These checks do not prove supply-chain provenance or reproducible
APK bytes across machines.

The current locked JDK 17 `core:check` passes 70 JVM tests, including 18 local-diagnostics and
foreground-refresh tests, and the nine generator tests. These exercise unknown readings, advisory
boundaries, permission changes on resume, cancellation and late-read fencing. Review-token and
render-generation regressions are covered by the 32 controller tests within 54 passing Android
debug JVM tests. Debug lint reports no issues, and both debug and unsigned release APKs build.
These current compilation receipts include the Android status adapter, UI and callback wiring;
they do not establish actual microphone, storage or battery readings, settings navigation, or
Samsung lifecycle behavior without the handset probe.

The wrapper verifies its distribution SHA-256 and Gradle verification metadata retains artifact
hashes observed during this first build. This establishes a baseline for detecting artifact changes,
not independent provenance. Keep library license resources in the APK. The merged manifest
includes Media3's network-state/wake-lock permissions and AndroidX's initialization/profile
components alongside microphone permission; it has no Internet permission. The app owns its
source and local behavior while Samsung's system software and hardware remain separate layers.

Before treating the client as handset-validated, record the S20 FE's exact model and Android/API
version and test permission refusal/revocation, repeated recording, the automatic cap, lock,
background, rotation, process kill/relaunch cleanup, audio focus, wired/Bluetooth route changes,
and stop/discard while finishing or replaying. A local completed WAV is not evidence of a remote
voice journey. This first slice contains no instrumented-device test receipt.

## Resume the current campaign

The **29 October 2026 checkpoint** leaves local status and reviewed-input fencing in the native
Android project. [State of Work](../../state-of-the-work.md#companion-android-client) owns the
current checks, build evidence and undelivered boundaries; [the client README](https://github.com/hexanomicon/lychd/blob/main/clients/android/README.md)
owns reproducible setup and commands. [Phone Workspace](phone-workspace.md) retains the full
operator goal, both device directions, proposed authority ladder, app delivery, photos and cleanup.
Neither the build nor this continuation procedure broadens Companion revision 3.

The **30 October priority clarification** is install once, manage from the PC, and initiate a
verified Companion update with one PC action. Begin the next integration campaign with
[that lifecycle](phone-workspace.md#install-once-manage-from-the-pc); the MP3 player is its first
useful feature, not a prerequisite for proving update delivery. Current local diagnostics and
the debug APK do not yet implement pairing, PC management or remote updating.

Start a later campaign here rather than treating an earlier APK or temporary tool directory as
the source. Inspect the current checkout, preserve unrelated changes, read the current State
record, and identify the smallest next acceptance. Reuse an operator-local development environment
and signing key if retained; otherwise follow the README and make the changed signing identity
explicit before proposing an update. Keep APKs, key material, environment paths and raw receipts
outside the checkout. The tracked source and ordinary build route must suffice when old local
artifacts are unavailable.

Local construction and handset qualification can proceed alongside one another; retain separate
acceptance for the build and for behavior observed on the phone.

| Work package | Next acceptance | Stopping line |
| --- | --- | --- |
| Installed lifecycle and PC Update | Settle the receiving owner/contract, install/pair version A, show its observed state on the PC, request a signed compatible B through Update, handle Android action, reconnect and verify version/data/health. | Preserve exact attempt identity across app replacement; cover revoked access, interruption, unknown result, storage/migration failure and changed signer. Do not promise silent install or automatic binary rollback. |
| Handset qualification | On the selected S20 FE, record exact model/Android/API/build, install the reviewed APK, and exercise status refresh, permission denial/revocation/settings return, background/lock, recording stop and cleanup. | Do not infer handset behavior from compilation or JVM tests; do not uninstall an existing app to hide a signing conflict. |
| Local folder player | Select a music folder explicitly, browse/play a useful offline library and queue, and observe playback through background, lock and headset controls. Cover revoked access, missing files, storage limits and interruption. | Keep persistent media and the background player separate from foreground reply replay; settle any new durable ownership before expanding it. |
| Reviewed app delivery | Retain exact source/build/checks, signed APK/package/version/permissions, verified received bytes, explicit Android installation and installed-identity readback. Prove offline MP3 playback. | Manual or available authorized KDE Connect delivery is operator evidence, not native enrollment or automated construction. A separate requested app has its own package and signing identity. |
| Native phone connection | Resolve operation/material ownership first; publish the accepted contract, then protected ingress, Ward → Familiar → Companion admission, exact request lookup and the selected bounded phone operation, beginning with the admitted update lifecycle. | Test unpaired peer, wrong object/action, expiry/revocation, changed context and lost acknowledgement without repeating an effect. Do not expose the existing loopback Altar. |
| Photos before cleanup | Export selected representations to verified destination custody; subsequently review exact eligible local items and a separate system trash request. | Preserve provider/cloud limits, changed-source refusal, per-item outcomes and the URI/content race. Permanent deletion is another live decision. |
| Later reach and interaction | Repeat an already admitted journey through VPN; connect speech or further observations through their exact owners. | A new route, model or microphone supplies no additional effect authority. |

The installed-lifecycle and local-player/delivery campaigns can proceed independently of live speech. The Bridge and Voice
release still needs its own live Communion acceptance. For remote troubleshooting, use
[the observation-to-repair passage](phone-workspace.md#grow-observation-into-troubleshooting)
and admit each new action rather than a generic phone command executor. Stop when the next step
requires a missing owner, authority, recovery contract or unobserved physical premise; retain the
specific gap and the smallest probe that could settle it.

## Next integration

The next useful work is a protected host-owned mobile API with enrolled device identity,
object-scoped grants and exact retained handoff/result lookup. It needs the accepted
Ward → Familiar → Companion order and a separately settled submission/presentation contract.
Then qualify the chosen live Ktor engine on the handset, wire the exact generated contract,
and connect Echo's bounded transcription/synthesis custody through the proposed Communion Suite.
Only that sequence can establish the capture → reviewed words → host work → settled reply journey.

Before replacing the fixture with a live connection, establish how the host reports uncertain
admission. Current Altar Bridge can fail after admission while constructing its acknowledgement.
That acknowledgement also omits the request identity, which the current client attaches locally.
Neither an HTTP status nor that local attachment establishes an exact retained host outcome.

The fixture's known-refusal classification therefore cannot become live recovery policy. The
owning host contract needs tests for pre-admission refusal, post-admission failure, lost
acknowledgement and lookup in the original account/context.

| Review follow-up | Required evidence |
| --- | --- |
| Remote account and view integration | Ward enrollment, application-owned filtered projection, exact object/action grants; two accounts, sharing, revocation, expiry and context-switch tests. |
| Live Bridge recovery | Protected mobile ingress and retained request/handoff/result lookup; transport failures cannot cause duplicate admission or retargeting. |
| Remote voice journey | Echo custody and bounded capture/transcription/review/synthesis settlement, followed by handset delivery evidence. |
| Android operation | The S20 FE lifecycle, permission, microphone, cleanup, focus and route probes listed above. |

Folder-first offline music can reuse the platform/lifecycle project but requires its own library
selection, media session and background playback behavior. Selected photos and explicit copy sync
follow the [Phone Workspace](phone-workspace.md) study. Those features do not turn client modules
into host-owned extension execution or confer broad control of the phone.

[Companion](index.md) · [Return](return.md) · [Android Foundation](android-foundation.md)
