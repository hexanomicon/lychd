---
title: Echo
icon: material/waveform
---

# :material-waveform: Echo

> _A voice is not delivered when it is made, but when another body receives it._

**Echo** is the speech-lifecycle Extension Domain. It carries an utterance from deliberate capture
to actual reception without losing its origin, consent, or outcome.
Audio admission is **Partial**, but no working Echo package or speech path ships.
[ADR 37](../../adr/37-audio.md) owns the accepted design;
[State of Work](../../state-of-the-work.md#audio-admission) owns delivery truth.

## The organs of resonance

An Echo profile composes five roles independently. Audio is a modality, never a capability family.

| Role | Place in Echo |
| --- | --- |
| **Ear** | `stt` Animator for bounded transcription |
| **Voice** | `tts` Animator for synthesis |
| **Audio-capable Mind** | Audio-input or audio-output `chat` provider; it remains `chat` |
| **Listener** | Capture, push-to-talk, codecs, and optional voice activity |
| **Mind** | Ordinary reasoning provider; there is no separate voice intelligence |

## The resonance path

Record-and-send is the first accepted profile:

> visible bounded capture → immutable audio artifact → eligible Ear or audio-capable Mind →
> attributed transcript or native observation → ordinary Agent step → optional Voice → delivery
> evidence

Capture must be visible, bounded, and consented. Large bytes remain outside Graph checkpoints and
queues.

Three distinctions keep the path honest:

- Current `ArtifactRef` support is metadata only. The
  [artifact-reference boundary](../../state-of-the-work.md#artifact-reference-contract) proves
  neither a stored recording nor playable byte custody.
- In the accepted design, Reliquary custody preserves source and derivation. A transcript is an
  attributed interpretation, not a replacement for its recording.
- Synthesized audio is a new artifact. Generation proves neither delivery nor playback; receipts
  must state what actually reached the listener.

Later half- and full-duplex profiles must preserve one monotonic speech timeline through barge-in,
contested turn ownership, interruption, cancellation, and reconnect. A live socket cannot supply
those semantics.

Invalid audio, insufficient authority, and policy-ineligible remote egress are refused. Only an
otherwise eligible managed provider that is not warm may enter ordinary Stasis while the
Orchestrator readies it. Echo cannot silently fall back to a remote service, infer permanent
microphone authority, inflate priority, or revoke another grant or lease.

## The Emissary

A future Mobile Emissary may own device capture and playback as Echo's physical ear and mouth. A
private [Tether](tether.md) supplies reachability, not caller authority:
[Ward](ward.md) still authenticates and authorizes, while capture and consent remain visible. A
remote [Portal](../animator/portal.md) additionally requires eligible classification, egress
policy, consent where required, and bounded cost. These are laws of the accepted design, not
claims of delivered behavior.

Operationally, Echo preserves where speech began and whether the answer arrived.
