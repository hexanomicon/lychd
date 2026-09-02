---
title: audio.cpp
icon: material/waveform
---

# :material-waveform: audio.cpp

**audio.cpp** is a candidate local audio inference engine. It belongs in the Soulstone engine
catalog because a pinned server or worker can become a local Animator, while its produced meaning
belongs to Echo for speech mechanics, Riffmaw for music, or the consuming application according to
the admitted operation and semantic role.

The current candidate route covers explicitly supported music, separation, and speech families;
it does not admit arbitrary model execution merely because the runtime is Apache-2.0. Model
weights, dependencies, family support, input/output bytes, and license terms remain separate
profile facts.

An audio.cpp Soulstone must eventually pin the runtime revision, model family, worker or server
shape, queue/lifecycle behavior, device topology, audio formats, cancellation boundary, output
custody, and measured receipt. A library or one-shot CLI that does not justify an independent
managed lifecycle remains a bounded `ToolProfile`, not a Soulstone.

The music candidate is recorded in [Riffmaw Studio](../../../../compositions/riffmaw/studio.md);
speech law and Language Edition's use of exact STT/TTS operations remain in the
[Audio covenant](../../../../adr/37-audio.md) and [Language Edition](../../../../compositions/language-edition/index.md).
Audio admission remains separate from the generic Soulstone engine catalog.

See [audio.cpp](https://github.com/0xShug0/audio.cpp) and the owning
[Echo](../../../extensions/echo.md), [Riffmaw](../../../../compositions/riffmaw/index.md), and
role-specific application contracts.
