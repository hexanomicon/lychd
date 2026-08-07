---
title: Utterance
icon: material/microphone-message
---

# :material-microphone-message: Utterance

1. The foreground client opens push-to-talk and binds a fresh utterance identity, frame sequence,
   byte and duration ceilings, codec profile, and expiry.
2. Tether may provide private reachability. Ward separately proves application, device, Principal,
   scopes, and object authority; either key proves only its own boundary.
3. Echo admits bounded frames, produces an attributed transcript, and drops raw audio under the
   selected retention policy. Low confidence asks for clarification.
4. The client previews the transcript when required, then submits one idempotent Intent.
5. Weaver routes it to an exact registered Pattern. The owning application handles domain-specific
   clarification, consent, work, and recovery.
6. Committed text becomes the durable answer. Synthesis or playback may fail without erasing it.

```text
push-to-talk → authenticate → transcribe → preview or clarify
→ typed Intent → admitted Pattern → committed text → optional speech
```

The route owns no application Pattern. Speaking can carry several purposes without becoming a
universal application or granting administrative, purchase, or approval authority.

Continue with [Return](return.md) for reconnect and custody.
