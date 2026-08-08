---
title: Communion
icon: material/account-voice
---

# :material-account-voice: Communion

Communion is the reference mobile route into an admitted LychD Pattern, not a Composition. It
carries one deliberate utterance from an enrolled client and returns committed text, optionally
spoken aloud. The destination application or Core owner keeps purpose, records, judgment, and
effects.

| | |
| --- | --- |
| **Profile** | `walking.communion` revision `1` |
| **Begins with** | foreground push-to-talk from one enrolled application and current Principal |
| **Carries** | bounded audio, one typed Intent, correlation, and a committed text result |
| **Stops before** | ambient capture, emergency monitoring, mobile administration, deferred effects, or voice-only consent |

Communion carries explicit or ordered input and output language preferences plus their fallback
policy; it does not choose a speech engine or infer translation. Echo resolves an eligible Ear and
Voice whose model profiles declare the requested languages, and only a baked language may be
presented as verified. The first local proof may use the planned audio.cpp profile, but that is an
Echo deployment choice rather than Communion application law.

Foreground push-to-talk remains the revision-1 activation contract. A future host-side
openWakeWord or device-side wake-word backend belongs to Echo's Listener and may only begin a new
bounded capture; it does not grant ambient recording, transcription, or Intent authority.

- [Utterance](utterance.md) follows capture, transcription, review, Intent, and optional speech.
- [Return](return.md) fixes divided authority, privacy, reconnect, revocation, and proof.

Continue with [Echo](../../sepulcher/extensions/echo.md), [Tether](../../sepulcher/extensions/tether.md),
[Ward](../../sepulcher/extensions/ward.md), or the [Composition Portfolio](../index.md).
