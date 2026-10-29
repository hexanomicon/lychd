---
title: Utterance
icon: material/microphone-message
---

# :material-microphone-message: Utterance

One deliberate utterance starts a bounded foreground route. It can settle a request handoff even when the destination has not yet admitted work.

When push-to-talk opens, the client creates a fresh utterance identity and fixes its frame sequence, codec, byte/duration limits, and expiry. Tether may make the host reachable, but Ward independently proves application, device, Principal, scopes, and object authority.

Echo then admits the frames, retains an attributed transcript, and drops raw audio under the chosen retention. Low confidence returns clarification. Where preview is required, the person reviews the words before submitting them.

`companion.submit_turn@1` commits an idempotent `CompanionTurnHandoff@1` binding exact Intent, requested Pattern, Principal, device/session/utterance identities, expiry, disclosure, and correlation. That submission action then ends. Spellweaver independently decides whether to admit the exact registered destination; its owner handles clarification, consent, work, cancellation, and recovery.

```text
push-to-talk → authenticate → transcribe → preview or clarify
→ typed Intent → settled CompanionTurnHandoff@1
                     || independently admitted destination Invocation
settled terminal-result reference → Companion presentation under its admitted output policy
```

Once a terminal-result reference has settled elsewhere, a fresh authorized `companion.present_result@1` may present it against this utterance/device. The presentation has its own finish. Committed text survives synthesis or playback failure, but text alone cannot complete a presentation that requires speech.

Text-only fallback counts as completion only when the admitted configuration explicitly accepts it. Otherwise return exact partial or non-completion for the presentation. This leaves the independently settled destination result unchanged: Companion cannot reopen or relabel it and owns no wait, cancellation, retry, or recovery for that destination Invocation.

The two handoffs therefore promise separate settled results. A Product needing one coordinated round trip must pin a named Suite with aggregate wait, cancellation, recovery, and settlement. [Return](return.md) explains what reconnect can retrieve without replaying the request.
