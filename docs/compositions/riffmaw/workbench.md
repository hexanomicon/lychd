---
title: Workbench
icon: material/piano
---

# :material-piano: Workbench

An agent and a musician should be able to make a short arrangement, hear it, change notes or
instrument parameters, compare versions, and recover the selected work. This construction plan
starts with a finite offline worker and a local ComfyUI probe. It creates no new Composition.

## Ownership and requirements

Riffmaw owns musical plans, arrangement revisions, instruments, candidate mixes, listening judgment
and musical acceptance. Atelier retains visual commissions, candidates, accepted revisions and
bundles. A future shared view may audition exact settled visual references alongside music.
Broadcast retains final audiovisual placement and acceptance. Coordinating several owners' live
Invocations requires a separately admitted Suite. The unresolved cross-craft project lifecycle
remains explicit in [Products and Suites](../products-and-suites.md#atelier-riffmaw-language-edition-and-broadcast).

| Requirement | Observable acceptance |
| --- | --- |
| One musical meaning | Preview identifies its exact recipe; export uses the same recipe and backend. |
| Shared authoring | Agent and human eventually use identical typed operations; stale expected revisions refuse and earlier state remains recoverable. |
| Editable material | Notes, clips, gain, pan and admitted instrument controls survive save/reload. Generated stereo audio remains a source, not invented synth tracks or native stems. |
| Attributed output | Recipe, source, implementation, engine, processor and output digests accompany each candidate. |
| Correct cache | Every relevant input enters the key; incomplete or corrupt output never counts as a hit. |
| Bounded generation | One operator-reviewed immutable Comfy API workflow pins nodes, models, mutable inputs, output nodes and formats. |
| Honest interruption | Lost submit acknowledgement remains indeterminate; reconciliation queries the same identity without blindly repeating generation. |
| Separate judgment | Technical success and numerical checks never imply musical, visual, editorial or publication approval. |
| Preserved custody | Private sources, working files and generated media stay outside the checkout; bounded descriptors and verified digests determine consumed bytes. |

## Approachable interaction

Riffmaw should let a musician make small changes without DAW expertise, using simple controls or
ordinary-language requests such as “add a little reverb” or “turn this part down.” The longer-term
direction is an assistant that can listen to admitted takes or mixes when helping shape the music,
and eventually hear and respond during live playing. Live interaction follows the separate
[capture and Jam contracts](sessions.md#the-realtime-stopping-line).

The interaction follows a small loop: name the part and desired change, prepare a candidate,
hear it against the selected version, then keep, revise or discard it. A request such as
“turn the bass down” and the corresponding track control use the same typed edit and revision
rules. The response identifies the changed part and the version available to hear. Earlier work
remains available for comparison.

AI assistance may interpret a brief, propose a bounded edit or compare candidates. An unclear
target needs clarification; an unavailable effect returns a finding rather than a claim that
it was applied. Listening observations retain their source and uncertainty. A rendered WAV or a
loudness measurement alone does not establish that an assistant listened to the music.

## Next bounded increments

Keep the first native increment focused on one short edit-and-listen task:

1. Connect the existing finite worker to a native musical revision and candidate. A human and
   agent must see the same revision, apply one guarded change, hear the exact result, and recover
   the candidate after restart. The authoring, admission and custody requirements in
   [Native implementation stages](#native-implementation-stages) still apply.
2. Add one ordinary-language edit over those same typed operations. Show the affected track or
   region and the proposed change; preserve comparison and the musician's selection.
3. Qualify one generation or separated-source profile for a concrete musical task, then connect
   its verified output to the same revision-and-listening loop. Keep the exact tool and model
   proof with [Studio](studio.md#minimum-first-proofs).

Choose a Rust component only when a measured DSP, timing or device requirement needs it. The
first feedback loop can use the existing Python adapters and offline renderer. Capture and live
Jam retain their separate proofs; they are not prerequisites for this offline increment.

## Construction decision

Python owns validation, compilation, adapters and technical receipts. The first offline trial
uses DawDreamer with finite source-owned FAUST instruments, following the dated
[Studio map](studio.md#current-candidate-map). Optional development dependencies stay separate
from Vessel dependencies. A bounded subprocess isolates the native library from the trusted
Vessel; imported plug-ins, arbitrary DSP programs and ambient discovery are excluded.

SuperCollider remains a candidate for a later measured live/offline proof, not an automatic
fallback or second interpretation of the recipe. Rust may supply a demonstrated missing DSP or
timing component. Neither choice establishes compatibility or realtime delivery by itself.

## Finite engineering worker

Give the worker an immutable, schema-versioned technical recipe describing bounded notes, PCM
sources, clip frames, gain, pan and admitted synth controls. It returns aligned stems, a candidate
mix, format/peak observations and digest receipts. This recipe JSON describes the finite trial;
it is not executable Python, a Scroll, `MusicProductionPlan@1`, or a canonical native project.

Admission bounds tracks, events, frames, bytes and process time. It permits at most 32 concurrent
events and uses a conservative graph-buffer estimate, though native RSS has no cgroup limit.
Unsupported formats or missing processors refuse rather than silently substitute. The source-owned
trial instruments make no production-quality claim.

An operator development runner can exercise this mechanism without the Vessel, a background
service, a new public Pulse command, or invented Run/Invocation identities. External workspaces
hold immutable probe inputs and technical receipts. These are not a shadow Phylactery and claim
no native musical state, acceptance, scheduling or Composition recovery.

Comfy is a separate finite external-engine attempt. Its profile pins a literal local endpoint,
classic-server dialect, workflow digest, reviewed node-class declarations, declared model digests,
mutable input openings and expected outputs. Those declarations do not attest runtime closure or
verify the server's loaded model files. Persist exact probe/request identity before submit and
the acknowledged provider identity before retrieval. Music and visual outputs name their
separate intended receiving owners; the
adapter supplies technical results and cannot commission or accept another owner's work.

Client-supplied UUIDs establish correlation, not proven atomic submission replay. Targeted
cancellation is deployment-dependent; the probe must not globally interrupt a shared service.
Empty history never proves no submission occurred. Verify the exact
[classic routes](https://docs.comfy.org/development/comfyui-server/comms_routes) and runtime before
a real model trial. HTTP acknowledgement alone does not establish containment or useful output.

Once fetched, bytes become immutable for that occurrence. Repeating retrieval verifies and reuses
the retained files; if a later file fails, preserve the earlier files and their technical receipts.

To publish a file, first retain deterministic staging and pin its digest, then install the final
file. An interruption after the pin can be repaired from that exact local stage. Normal load
still refuses a missing final file. Unpinned staging, lost or damaged bytes, and conflicting final
files refuse and require manual reconciliation. Repair cannot replace bytes from the server or repeat
generation. Even a matching extension and digest cannot establish that the bytes are a valid
image, video or audio format.

## Development operations

Install the optional profile using
[Contributing](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md). Choose an absolute,
operator-owned workspace outside the checkout, then use the source development runner:

```bash
uv run --locked --group music-probe python scripts/music_probe.py schema recipe
uv run --locked --group music-probe python scripts/music_probe.py demo --output /absolute/work/recipe.json
uv run --locked --group music-probe python scripts/music_probe.py validate /absolute/work/recipe.json
uv run --locked --group music-probe python scripts/music_probe.py render /absolute/work/recipe.json --workspace /absolute/work
uv run --locked --group music-probe python scripts/music_probe.py audition /absolute/work/recipe.json --workspace /absolute/work --output /absolute/work/audition.html
uv run --locked --group music-probe python scripts/music_probe.py edit /absolute/work/recipe.json --expected-digest DIGEST --track bass --cutoff 900 --output /absolute/work/variant.json
```

`edit` requires the digest returned by `validate`, preserves the earlier recipe and refuses to
overwrite the destination. `render` uses only finite sine, saw and kick programs, gain/pan/lowpass,
and non-stretched PCM clips. Import exact mono/stereo 16/24/32-bit integer WAV at the recipe rate
as `assets/SHA256.wav`; no resampling or arbitrary plug-in loading occurs. Its receipt points to
`renders/CACHE_KEY/`, containing the mix and aligned stereo 16-bit WAV stems. Independently
quantized stems and mix can differ by integer rounding when summed. Peaks above full scale refuse.

`audition` renders or verifies the same exact recipe and writes a standalone read-only timeline
with mix/stem selection and playback. It embeds verified PCM bytes, with a separate 20 MiB media
ceiling, and makes no network requests. Seeking is a browser listening aid, not a realtime clock
proof or musical edit. Controls remain typed recipe edits through the runner; this preview is not
the native studio editor.

A cache hit must identify the same computation. The key binds exact recipe, processor,
renderer/model source, installed DawDreamer/NumPy executable artifacts, their versions and runtime
platform. Repeats on that pinned runtime are verified; cross-platform bit identity is not promised.
Publication uses exclusive hard links, fsync and a receipt committed last. Interrupted or incomplete
entries refuse, under the assumption that directories are stable and operator-owned rather than
hostile mutable mounts.

Execution has its own stopping checks. A 30-second child deadline bounds native execution, followed
by a separate one-second cleanup budget to kill the owned process group and observe its stopped
state through Linux `/proc`. Unavailable or unresolved observation refuses completion. Descendants
that escape into a new session are outside that check, so the worker establishes process separation
rather than Coffin containment.

`schema comfy-profile` and `schema comfy-request` expose the actual Comfy inputs. Supply reviewed
profile and request files, then run `comfy prepare --profile PROFILE --request REQUEST --workspace
WORKSPACE`. `comfy attempt submit UUID --profile PROFILE --workspace WORKSPACE` crosses the submit
fence once; later `reconcile` queries the same occurrence and `fetch` retains its reviewed outputs.
The workspace must already exist. After interrupted file installation, `comfy attempt repair UUID
--profile PROFILE --workspace WORKSPACE` verifies pinned staging and installs only matching bytes.
It makes no HTTP requests, leaves receipt identity unchanged, and can be repeated. A pre-pin stage
blocks further fetching until manually reconciled; old receipts whose bytes were lost cannot be
repaired by this command. No live profile, model, server launch or MiniMax generation is supplied
by these commands. Unknown submission stays unknown; cancellation refuses.

## Native implementation stages

The complete native application still needs these boundaries after the worker proof:

1. Riffmaw musical authoring and immutable edits in PostgreSQL, including concurrent-edit,
   request replay, retention and restart rules.
2. Owner-qualified Composition/Pattern publication, typed RunEngine admission, exact tool or
   capability binding, durable attempts and admitted media custody.
3. One local Comfy music profile proved against the operator's blueprint, exact model/workflow,
   formats, cancellation and restart behavior.
4. A static Svelte view over the same APIs: tracks, timeline, note/clip editing, knobs, waveforms,
   audible revision, candidate comparison, job status and explicit musical selection. Litestar
   retains authorization, mutation and persistence.
5. Exact settled visual-reference audition and owner-qualified handoffs. Live cross-owner
   production, final audiovisual editing and cross-craft undo retain their own owners.

Keyboard/MIDI input, guitar capture, direct monitoring and Jam require separate arming,
clock/route epochs, measured latency, dry takes, xrun evidence and stale-output fences. Offline
playback proves none of those. Paid fallback, arbitrary workflows/plug-ins, autonomous acceptance
and publication are outside this worker trial.

## Acceptance evidence

Retain audible synthesis/import proofs, source trims, aligned stems/mix, deterministic repeats on
the pinned runtime, changed-control and corrupt-cache negative controls, bounded malformed
inputs, cleanup and subprocess interruption. Comfy protocol tests must cover unknown submission,
changed workflow/input rejection, output bounds, empty history and cancellation refusal. Such
tests do not prove real generation or musical quality. A four-bar 145 BPM recipe has rendered
211,862 frames at 32 kHz through DawDreamer 0.9.0 on the development host, with kick/bass/lead stems
and a mix. The changed bass-control recipe and repeat cache are separate technical proofs.
A model receipt follows only after the
blueprint and exact profile are available. [State](../../state-of-the-work.md#composition-portfolio-delivery)
keeps worker, native application and live evidence separate; the
[engineering probe record](../../state-of-the-work.md#music-comfy-engineering-probes) owns this subset.
