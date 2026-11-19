---
title: A short video for a colleague
icon: material/movie-open-outline
---

# A short video for a colleague

Ada has the GPU. Lin has a script and would like a Slovak explainer by morning. Ada offers a
short-video service to enrolled colleagues. Lin chooses an offer, sends the script and can go
offline. Ada can inspect what her machine made. Lin can review and collect the exact cut on
return. **This is a worked design for two sovereign Liches.** Today Lin can send an
operator-declared public brief to Ada's private Intercom inbox. Ada can review it and return an
approved text reply. The [local cut](#try-a-local-cut) is a separate executable editorial step.
Automatic rendering and collecting a video from the receiver are later parts of this design.
[Intercom delivery record](../../state-of-the-work.md#a2a-intercom)

## What a colleague can order

For the working text exchange, the receiver selects `atelier.short-video-brief@1`. The following
public brief requests a twelve-second cut. After admission the receiver operator can review its
exact text, start it, reject it or record a public result. The sender can cancel an open request.
[Intercom operator session](../../sepulcher/intercom.md)

```json
{"recipe":"captioned-excerpt","script":"The observatory opens at dusk.","duration_seconds":12}
```

The three recipe names are `illustrated-story`, `animated-lesson` and `captioned-excerpt`.
The table describes the intended production work after the brief reaches Ada.

| Offer | Preparation the reviewer sees | Work after storyboard approval |
| --- | --- | --- |
| **Illustrated story** | An actual Qwen first-frame candidate for each shot, optionally an end frame, with the proposed action, camera, words and sound underneath. | Animate each selected image with its pinned LTX image-to-video preset. Probe the shots, then cut, caption, mix and render. |
| **Animated lesson** | A diagram, key poses, labels, camera path, narration and source for each factual claim. For example, start above a circular orbit, then move in on the radius while the label stays legible. | A local authoring step translates the approved scene into bounded, revisioned drawing and camera instructions. Prism renders a preview and full frames. Check clipped labels, camera timing and the approved lesson against the export. |
| **Captioned excerpt** | A finite set of Webcrawler results with source, use evidence, preview, selected in/out timecodes and proposed caption. An operator-supplied clip can enter at the same source-admission step. | Trim the selected frozen bytes, lay out captions, replace or retain only admitted audio, then render. The review records source credit and the permitted audience. |

All three offers share the same delivery limit of **180 seconds**. Compare requested time at
admission, the timeline end after accounting for transition overlaps at review, and measured picture
and audio end times at export. Reject an overlong request before allocating a model. An
overlong render goes back for correction. The operator selects which offers each colleague may
see and can withdraw one without withdrawing the other two.

For the lesson, the [RAEA study](motion.md#procedural-rendering-study) already identifies the
upstream Render Anything Engine. Start with an independently authored scene vocabulary for
labels, shapes, camera target and keyframes. Pin its revision, renderer, assets and timebase.
Generated code is a candidate for isolated evaluation with declared assets and finite frame
and resource limits. The peer sends a creative brief. The first qualification scene moves a
camera past a label, catches clipping at a known frame and verifies the repaired revision.
The integration or distribution of upstream code needs a separate license and Assimilation
decision. [Upstream camera example](https://raea.io/docs/guides/3d/)

For the excerpt, admit Webcrawler Search and Fetch separately with a finite source set,
timeouts and byte ceilings. Freeze the selected input by digest and retain its source URL,
attribution and evidence for the intended reuse, edit and delivery. For a film fragment with
unclear permission, request a licensed or operator-owned alternative before production.
Changed remote bytes reopen source selection. [Source admission](../broadcast/sources.md) ·
[Webcrawler](../../adr/30-webcrawler.md)

## What Nexus would show

An enrolled colleague might see **Ada · Ready**, **Illustrated story · up to 3 min** and
**Accepts tonight 20:00–23:00 Europe/Bratislava**. These are three independently sourced
facts. Today the [presence panel](../../divination/altar/nexus.md#see-which-colleagues-welcome-requests)
supplies the first one through an explicitly paired private replica. The proposed catalogue
adds the latter two via an authenticated peer-specific offer. Two installations need reciprocal
enrolment and current reports to show each other. Starting either application alone advertises
nothing. A stale report reads **availability unknown**.

Each offer pins the issuer, recipient audience, public task schema and revision, limits and
review modes, result types, offer revision and expiry. Advertise only the selected creative
service. Installed Scrolls, Comfy graphs, model files, calendar contents and live queue stay
local. Keep the signed offer separate from the existing fixed-format presence report. Withdrawal,
revision or expiry invalidates cached choices at admission. [Peer identity and discovery](../../adr/26-a2a.md#peer-identity)

For example, Lin selects **Animated lesson**, requests **12 seconds, 16:9, Slovak narration and
captions**, asks Ada to review both stages and chooses **private return to Lin**. The submitted
request pins that offer revision and those choices. Ada resolves them to her local preparation
and master scores. For the first receiving trial use a script explicitly cleared for this peer.
Restricted scripts, reference images and review previews need their own disclosure decisions
before they cross machines. [Intercom envelope](../../adr/26-a2a.md#envelope)

In the proposed rendering service Ada admits one active production at a time and allows one pending request
for a future window. Lin receives a durable task identity and a **waiting for window**
observation only after intake commits. A full pending slot produces an explicit busy response.
Peer inbox acceptance and the later admission of a rendering Invocation are separate events.
Ada can already bound new inbox admissions to a finite interval in the private invitation.
Lin can separately request a UTC first-start window in the brief. Ada's operator can start
the task during that window. A missed start remains available for rejection until task expiry.
[Evening submission and collection](../../sepulcher/intercom.md#receive-a-public-brief)
Nexus reports her separate availability choice. In the proposed service a current explicit Busy
would close new intake and expiry of a presence heartbeat would leave availability unknown.
Only a fresh authenticated receiver decision can confirm availability.
Existing admitted jobs follow their own cancellation and deadline policy.

Set the recurring window in Ada's civil time and publish finite UTC intervals with offset. For
example, 20:00–23:00 in Bratislava on 20 November 2026 is 19:00–22:00 UTC. In this example
skip a nonexistent spring firing and select the earlier fold of an ambiguous autumn firing.
Check `not_before <= admission_time < latest_start_at` against the receiver clock. If the PC
returns after the window without having admitted the Invocation, record a miss. A separate
`finish_by` is required for a promised delivery deadline. Changing an offer cannot silently
extend an accepted deadline. [Temporal admission](../../sepulcher/aspects/weaver/scheduling-and-service-classes.md)

## Two casts and two reviews

The first cast produces a reviewable storyboard. It can complete there. The second takes an
exact approved preparation as input and produces a final candidate. An explicitly coordinated
Run may also park between these placements. Both forms preserve the same artifact, review and
effect boundaries. The shared studio is a proposed [Suite](../products-and-suites.md#atelier-riffmaw-language-edition-and-broadcast)
when it must coordinate live work across crafts.

1. **Prepare.** Admit the brief, target, language, duration, audience, review mode, budget and
   return policy. Break the script into shots on one integer frame clock. The storyboard contains
   preview bytes and source digests, frame ranges, image prompts and seeds, movement and camera
   prompts, transitions, narration text and voice direction, caption cues and placement, music
   cues, picture-sound cues and deliberate silence. It identifies the proposed local profiles and
   remaining cost before the expensive render.
2. **Review the storyboard.** Open the exact frames beside the lines that will be spoken. A
   designated reviewer can approve this revision, request an edit to one shot or decline.
   Resequencing shots, changing a line, font, voice, prompt or reference creates a successor.
   Reuse unaffected bytes by digest and obtain a new verdict on the assembled revision. Retain
   reviewer, role, verdict and digest. Release the GPU and worker while waiting.
3. **Render the approved revision.** Resolve the exact assets and profiles again, render each
   approved shot and retain its attempt identity. Language Edition aligns speech and captions,
   Riffmaw accepts music, and Atelier chooses their placement, picture sound and final mix.
   Atelier assembles the approved timeline, probes all
   streams and produces a local, playable candidate and manifest. For joint LTX picture and
   sound, admit every requested role before generation and respect the
   [compound-facet contract](motion.md#clips-and-cues).
4. **Review the finished cut.** Play the actual candidate, read the captions, listen to narration
   over music and check the declared audience, credits and duration. Bind the verdict to the
   export digest, timeline revision and probe. A correction creates a successor and invalidates
   affected judgments. On acceptance Atelier seals the [videomaster](master.md). Returning it
   privately to Lin uses Intercom with a recipient-specific grant. If Lin later commissions a
   release, Broadcast reviews a package for each audience and destination. A separately
   authorized Reach adapter may deliver it. A vertical cut needs an Atelier successor.

For a **12-second lesson at 30 fps**, frames `[0,120)` establish the full orbit, `[120,270)`
move the camera toward the radius and `[270,360)` hold the labelled diagram. The middle
shot can propose the words “Polomer spája stred s bodom na kružnici”, a calm Slovak voice,
the approved frame as the first LTX image, and a slow push toward the line. The reviewer can
replace the push with a static shot before any animation of that revision. A caption preview
uses the target aspect, a locally pinned sans-serif font with Slovak glyphs, high-contrast
backing and a bottom safe margin. Preview the longest line and move it up if it covers the
label. Store font bytes by digest, size, alignment, safe area, line breaks and cue times.

Choose human storyboard and final review by default. A request can select an offered policy
that permits a local reviewing agent to pass a **quality** gate, or an explicitly preauthorized
straight-through sequence. The same mandatory human/effect consents and recipient restrictions
apply across these modes. With human review required, a model can only submit findings. An
unavailable reviewer, unsupported audio input, undecidable result or expired permission leaves
the relevant gate open or ends it by its declared timeout. A reasoned refusal settles it.
The caller may review only the exact previews the receiver is authorized to disclose. Current
native review cards carry textual facts. Media review needs an authorized preview bound to the
same revision. [HitL](../../adr/25-hitl.md#required-review-for-native-actions)

## Bind and swap local tools

| Placement | Candidate local binding and evidence required before advertising |
| --- | --- |
| First frames | Pin a reviewed Qwen Image preset, weights, dimensions, seed policy, model-facing prompt and returned image digest. [Qwen-Image-2512](https://huggingface.co/Qwen/Qwen-Image-2512) |
| Motion | Pin the LTX-2.5 preset and source-frame digest, supported frame counts and measured hardware limits. Split a long storyboard into admitted shots. [LTX-2.5 model card](https://huggingface.co/Lightricks/LTX-2.5) |
| Speech and captions | Echo supplies an admitted Slovak TTS voice or the operator supplies an authorized recording. Language Edition aligns words and cue times to the actual performance. Preserve voice identity, permitted use and pronunciation corrections. [Echo voice candidates](../../sepulcher/aspects/echo.md#first-engine-profile) |
| Music and sound | An optional Riffmaw MiniMax Music 3 profile takes musical direction. Place cues against the measured recording. Atelier selects picture effects, mix levels and ducking under speech. Silence is an explicit brief choice. [Music profiles](../riffmaw/studio.md) |
| Quality review | A separately admitted instruction-tuned Gemma 4 12B is a candidate. Bind findings to exact frames and audio intervals actually seen or heard. Segment longer work within measured model limits and record gaps. Deterministic probes cover transient clipping, duration and missing streams. [Google model card](https://huggingface.co/google/gemma-4-12B-it) |

On one GPU, first batch the admitted brief's still-image work, persist and validate the
results, release that grant, and park for review. On resume, request an LTX grant, observe
the actual ready instance, then animate. Release before loading a large reviewer or music
model. Group independent shots only while their individual identities and budgets hold. A warm
instance may be reused under the same Resolution Lock. An unavailable pinned profile can wait
within its budget or return partial work. Rebinding to a different model, language or paid
Portal requires a newly admitted plan. Bake peak VRAM, load/swap time, maximum shot length
and cancellation behavior on Ada's own PC before offering a turnaround time.
[Comfy profiles](../../sepulcher/extensions/animators/soulstone/engines/comfyui.md) ·
[Physical admission](../../adr/23-orchestrator.md#drain-change-and-observe)

## Try a local cut

The local operator probe takes one owned MP4 whose picture timeline starts at zero, a local
TrueType font, one line of up to 100 characters and an optional WAV narration. It requires
Python 3.11+, FFmpeg with a decoder for the actual source codec, drawtext, the MPEG-4 Part 2/AAC
encoders, and ffprobe. Start and
duration are whole seconds. Use absolute paths in stable, operator-controlled directories outside
the checkout on a filesystem that supports hard links.
The command below selects twelve seconds starting at second four. The narration begins at the
first output frame. The source audio is discarded. Omitting the WAV gives a silent cut.

```bash
python3 scripts/short_video_cut.py \
  --video /absolute/studio/source.mp4 --start 4 --duration 12 \
  --caption 'Polomer spája stred s bodom na kružnici.' \
  --font /absolute/studio/regular.ttf --voice /absolute/studio/narration.wav \
  --output /absolute/studio/radius-v1.mp4
```

The example burns the caption into the picture, pads short narration with silence and cuts
long narration at the end. It checks the resulting streams and decoded frame count at 30 fps,
then installs one new file. Output includes the file and font SHA-256. If acknowledgement was
lost and the path already exists, inspect and verify those bytes before selecting a new output.
This probe handles one local cut. Native storyboard gates, model execution, a timed caption
track and a multi-shot timeline still need their own integration.

The separate Comfy engineering runner lets the operator assign a UUID to one shot attempt with
`comfy prepare --occurrence UUID`. Persist it before preparation. If the preparation response
is lost, supply the same UUID, private workspace, profile and request to recover the same
attempt. A substantive edit gets a new UUID. After uncertain submission, reconcile that
occurrence. The [workbench](../riffmaw/workbench.md) describes its technical receipts and
limits. Neither command registers a peer offer.

## Collect the result after a disconnection

Lin uses the original sender task ID to poll after reconnecting. The sender must already
have recorded the receiver's identity from the authenticated acknowledgement. Ada's
inbox retains the submitted text, its digest, the original sender identity and the receiver's
own task ID. If the first acknowledgement is lost, Ada can use the local `find` command with
Lin's original request ID. Lin sees **unknown** and must keep the original occurrence. The
protocol supplies no remote lookup by sender ID or permission to submit the brief a second time.
[Durable task protocol](../../adr/26-a2a.md#durable-task-protocol)

For video delivery the receiver must also bind the offer revision, each render attempt and the
approved artifact to this task. Recovering a lost first acknowledgement remotely would require
a separately authorized lookup by sender and original request ID. Commit the terminal outcome
and delivery obligation before reporting completion. Return an immutable manifest with
media type, size, digest, duration and retention deadline. Fetch previews or final bytes through
separate bounded, authenticated grants. Write to local staging, verify length and digest,
inspect/quarantine the media, then commit adoption before acknowledging collection. Duplicate
delivery can yield one adopted result and one Graph continuation. If retention expires first,
report that the result is unavailable. Ada retains her own authorized local review history.
[Artifact custody](../../state-of-the-work.md#artifact-reference-contract)

| Fault to inject before offering the service | Acceptance condition on restart or reconnection |
| --- | --- |
| Receiver dies before/after inbox commit, sender misses acknowledgement, or two clients repeat the request | No phantom admitted job, one durable identity after commit, conflict on changed bytes. Receiver lookup reconciles the original. |
| Crash during Qwen or LTX submission, empty engine history, or model swap fails | Preserve the attempt and completed shots. A possibly submitted render stays unknown until reconciled. A missing model never selects an unapproved substitute. |
| Both peers restart at a review, or two reviewers race after an edit | Restore the exact preview and pending gate, release all scarce grants, reject stale digests, admit at most one decision and one continuation. |
| PC wakes late, deadline passes during review, or an offer is withdrawn | Apply the accepted window and deadline, recheck current authority, record missed/partial/expired work and retain attributable costs. |
| Export completes before receipt, bytes are truncated, or the result acknowledgement is lost | Reconcile the candidate and checksum locally. Interrupted transfer resumes from verified evidence or restarts only the bounded read. Never regenerate the job to retransmit it. |
| Peer is revoked during delivery or two machines reconnect after independent restarts | Deny further disclosure on revocation. For an authorized peer, prove the same verified bytes on both PCs and one successor after the lost acknowledgement. |

**Loom** would show the selected Patterns, inputs, review placements and parked/resumed station.
**Orb** would show observed attempt, lease, model-transition, review and delivery events linked
to the same Run. The receiver can open its local artifacts. The sender sees only disclosed peer
milestones and admitted previews. Show unknown progress or observed completed shots out of the
declared total. No remote queue inspection or guessed percentage is needed.

## Bring up two machines

1. Pair colleague presence and verify Ready, Busy, withdrawal and stale state in both directions.
   Keep the shared-folder key separate from either installation's A2A identity.
2. Repeat the [loopback inbox trial](../../state-of-the-work.md#a2a-intercom) across the actual
   private route with one enrolled colleague and the lost-acknowledgement cases above.
   Then qualify one video offer, artifact fetch, refusal on
   revocation and reconnect with real bytes on two PCs. Only promote offers qualified end to end.
3. For a future static-IP workstation deployment, point the chosen A record (and AAAA only
   with a qualified IPv6 path) to the intended edge. Use a certificate for the exact service
   hostname. With a workstation-only deployment, Veil shares the machine and forwards solely
   to the dedicated authenticated Intercom listener. A separate **Home Gateway** requires
   a second machine, an enforced network boundary and one authenticated backend route. Tether
   can supply that private route. Restrict ingress to the chosen listener and enroll the
   application peer independently. The existing outbound profile pins TLS hostname, numeric
   address, port and path explicitly. Keep the Altar, Comfy and model endpoints local.
   [Gateway placements](../../sepulcher/gateway.md) · [Veil](../../sepulcher/aspects/veil.md) ·
   [Tether](../../sepulcher/aspects/tether.md)

The current receiver accepts private IPv4 and loopback addresses. Public ingress requires its
own qualification. End-to-end video acceptance requires Lin to retrieve and verify the approved
cut after disconnecting through the evening render.
