---
title: Utterance
icon: material/microphone-message
---

# :material-microphone-message: Utterance

One deliberate utterance starts a bounded foreground route. It can settle a request handoff even when the destination has not yet admitted work.

The client creates a fresh utterance identity, frame sequence, codec, byte/duration limits, and expiry when push-to-talk opens. Tether may provide reachability; Ward independently proves application, device, Principal, scopes, and object authority. Echo admits the frames, retains an attributed transcript, and drops raw audio under the chosen retention. Low confidence returns clarification; required preview lets the person review the words before submission.

`companion.submit_turn@1` commits an idempotent `CompanionTurnHandoff@1` binding exact Intent, requested Pattern, Principal, device/session/utterance identities, expiry, disclosure, and correlation. That submission action then ends. Spellweaver independently decides whether to admit the exact registered destination; its owner handles clarification, consent, work, cancellation, and recovery.

```text
push-to-talk → authenticate → transcribe → preview or clarify
→ typed Intent → settled CompanionTurnHandoff@1
                     || independently admitted destination Invocation
settled terminal-result reference → Companion presentation → optional speech
```

When a terminal-result reference has settled elsewhere, a fresh authorized `companion.present_result@1` can present it against this utterance/device. Committed text survives synthesis or playback failure. Companion owns no wait, cancellation, retry, or recovery for that destination Invocation.

The two handoffs therefore promise separate settled results. A Product needing one coordinated round trip must pin a named Suite with aggregate wait, cancellation, recovery, and settlement. [Return](return.md) explains what reconnect can retrieve without replaying the request.
