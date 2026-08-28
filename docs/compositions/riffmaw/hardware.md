---
title: Audio hardware and host routes
icon: material/connection
---

# :material-connection: Audio hardware and host routes

This page binds the Riffmaw and Echo designs to the operator's Linux-first audio hardware. It is
an operational candidate map, not evidence that Echo or live Riffmaw audio is already delivered.
[ADR 37](../../adr/37-audio.md) remains the owner of capture consent, custody, transport,
interruption, and playback law.

## Current LychD boundary

The repository currently proves audio modality metadata and the `stt`/`tts` capability labels. It
does **not** yet ship an Echo capture worker, audio-byte custody, upload or streaming transport,
STT/TTS adapter, playback receipt, or a live Riffmaw graph. The hardware below therefore prepares
the host and the future adapter seams; it does not grant LychD permanent microphone access.

The ownership split is:

| Area | Owns | Does not own |
| --- | --- | --- |
| Echo | bounded speech capture, transcription, synthesis, delivery, interruption, and playback evidence | musical performance, arbitrary ambient recording, or an identity |
| Riffmaw | human takes, guitar/bass DI, music, voice performance, effects, sessions, and sonic lineage | speech lifecycle, visual generation, or publication |
| Avatar | an eligible voice reference inside a presentation profile and target projection | microphone authority, cloning permission, or proof that a voice was played |
| Familiar | the admitted physical body, mission, safety envelope, onboard sensors, and physical speaker | Avatar identity, LychD attention, or a promise that every sensor byte was retained |
| Tether/Portal | private reachability and an admitted remote-service boundary, respectively | caller authentication, recording consent, chronology, or device authority |

## Host receipt boundary

This page carries no receipt for a particular workstation. A useful host receipt must come from
the real desktop login that owns PipeWire and the audio devices; a restricted shell, container, or
coding-agent session without `/dev/snd`, D-Bus, or the user PipeWire socket proves only that the
session lacks access.

Before promoting a route, record the OS and kernel, exact board or USB-device identity, loaded
driver, ALSA capture/playback inventory, PipeWire/WirePlumber graph, selected sample format and
rate, mute and gain state, and one measured record/playback result. A planning note or a device
advertisement cannot substitute for that observation.

## Candidate device profiles

These named devices are replaceable examples, not a purchasing recommendation or compatibility
claim. Pin the exact model and revision, use a returnable evaluation path, and require the same
Linux receipt from every substitute; vendors commonly document Windows and macOS while basic Linux
operation depends on the device's actual USB Audio behavior.

| Use | Candidate example | Why it is worth a bake | Linux receipt required |
| --- | --- | --- | --- |
| PC voice at a desk | [FIFINE AM8](https://fifinemicrophone.com/products/fifine-ampligame-am8-microphone) | Dynamic cardioid USB/XLR microphone with mute and headphone monitoring; close placement can reduce room pickup | Prove capture, mute indication, monitoring, format/rate negotiation, suspend/resume, and reconnect without depending on FIFINE Genie. |
| Quiet-room desk alternative | [Razer Seiren V3 Mini](https://www.razer.com/streaming-microphones/razer-seiren-v3-mini) | Small USB condenser with tap-to-mute; the manufacturer documents plug-and-play use without Synapse | Prove its basic class-compliant path, mute state, negotiated format, and reconnect; Linux is not the advertised support target. |
| Shirt/mobile voice | [Hollyland LARK M2 USB-C](https://www.hollyland.com/support/lark-m2) | Compact 2.4 GHz transmitter/receiver route for a phone or nearby computer | Prove the exact receiver enumerates as the intended capture device, retains channel/rate facts, and settles disconnect and battery loss; do not infer Linux support from the connector shape. |
| Guitar and bass interface | [Behringer UMC202HD](https://www.behringer.com/en/products/0805-AAR) | Two inputs, instrument path, headphone output, direct monitoring, and 48 V for an eligible condenser microphone | Prove capture/playback channels, instrument impedance path, direct-monitor behavior, rate stability, xruns, and reconnect; the vendor page is not a Linux support promise. |
| Alternative two-input interface | [Audient EVO 4](https://audient.com/products/audio-interfaces/evo-4/overview/) | Two preamps, instrument input, headphone/output routing, and direct-monitor controls | Prove which controls work without the vendor app, then retain exact capture/playback, monitoring, rate, xrun, suspend, and reconnect facts. |

### What not to use as the main route

- **TWS earbuds:** good for listening, but their Bluetooth microphone normally falls back to the
  telephony HFP/HSP profile: lower bandwidth, more compression, and possible latency. Keep TWS as
  playback or emergency chat, not as the Riffmaw recording microphone.
- **Bluetooth lavaliers without a receiver:** they introduce profile negotiation and latency
  surprises. A small 2.4 GHz lavalier set with a USB-C receiver is more predictable on both phone
  and Linux.
- **Motherboard mic/line input for guitar:** an electric guitar or bass wants a high-impedance
  instrument input. The board's ALC4082 is useful for ordinary playback and headphones, not a
  substitute for a Hi-Z recording interface.
- **Cheap anonymous BM-800 kits:** they commonly need noisy adapters or phantom-power wiring and
  are a poor Linux-first foundation.

## Wiring that covers the whole desk

The most useful long-term arrangement is one USB audio interface for the instruments and, when
needed, one separate USB voice microphone:

```text
FIFINE AM8 (USB) ───────────────┐
                                 ├─ PipeWire/WirePlumber ─ Echo / Bridge later
UMC202HD (USB) ← XLR mic or DI ──┘
                     │
             guitar/bass 6.35 mm TS
```

For simultaneous speech and guitar, connect an XLR microphone to interface input 1 and the guitar
or bass to input 2. For the AM8, USB is simpler; XLR through the interface is the useful option
when one unified low-latency device is desired. Keep `48 V` **off** for a dynamic microphone and
for guitar/bass. Use `INST/Hi-Z` for the instrument input, start at low gain, and watch the clip
indicator.

For amp simulation, monitor through Guitarix or another native Linux effect chain and turn direct
monitoring off to avoid hearing both the dry DI and the processed signal. For clean practice or a
latency-sensitive take, turn direct monitoring on. Riffmaw must retain the dry DI separately from
the amp/cabinet print so a later mix can repair the sound.

The motherboard headphone output can remain the ordinary desktop playback route. For guitar
tracking, headphones connected to the interface are preferable because its direct-monitor path
avoids round-trip delay.

## Mobile, drone, and rover routes

### Mobile and body-worn

Use a USB-C receiver on the phone and a second compatible receiver or USB input on the Linux host.
The transmitter clips to the collar or shirt, roughly a hand-width below the mouth. Keep the
transmitter away from fabric rubbing, necklaces, and zippers. The recording policy is still
explicit: a paired transmitter does not mean that Echo may record continuously.

### Drone

Consumer camera drones usually cannot accept a useful external microphone, and propeller wash
dominates an exposed capsule. The preferred route is a small onboard recorder or digital camera
audio path, with the sound captured locally and transferred as an artifact after the flight. If
the drone needs live speech, put the lavalier on the person or use a dedicated radio link to a
body payload; do not hang TWS earbuds or a Bluetooth microphone on the airframe.

### RC car or rover

For a rover with an SBC or camera, use a protected MEMS/electret microphone close to the chassis
and record locally at 48 kHz. Isolate it mechanically from the motor and drivetrain. Send a
bounded low-rate preview only when the mission explicitly admits live audio; retain the full WAV
only when capture and retention are separately admitted. The Familiar mission owns the body and
its stop/signal-loss policy; Echo can later transcribe an admitted audio artifact.

## Tumbleweed readiness sequence

On openSUSE Tumbleweed, perform the checks in the real desktop login, not inside a restricted agent
terminal. First capture the read-only substrate report:

```bash
uname -r
grep '^PRETTY_NAME=' /etc/os-release
lsmod | grep '^snd_usb_audio'
ls -ld /dev/snd
aplay -l
arecord -l
wpctl status
```

Then prove the selected route:

1. Confirm PipeWire, WirePlumber, the needed ALSA/PipeWire compatibility packages, FFmpeg, and ALSA
   utilities are installed for this host revision.
2. Connect one USB audio device directly, not through an unpowered hub.
3. Confirm the exact device appears in `arecord -l`, `aplay -l`, and `wpctl status`.
4. Record a five-second dry sample with `arecord`; verify the file and playback before adding
   any model or DAW.
5. Add `qpwgraph` or `pavucontrol` only if the desktop mixer needs a visual routing surface.
6. Add Guitarix and Ardour/Reaper only after the interface is stable at 48 kHz; measure xruns and
   round-trip latency before calling the setup realtime-ready.

Do not fix missing onboard audio by blindly changing kernel parameters. Capture `lspci -nnk`,
`journalctl -k -b`, the firmware audio setting, and the board's rear/front jack wiring before
forming a board-specific hypothesis. A separately proved external USB interface can provide a
bounded guitar, bass, or voice route while the onboard path is investigated.

## LychD implementation order

Hardware is ready for these bounded software slices:

1. **Host adapter:** enumerate ALSA/PipeWire devices and retain route facts without granting
   capture. Device handles and PCM stay outside Graph state.
2. **Echo record-and-send:** visible push-to-talk, bounded capture, immutable source artifact,
   one admitted STT profile, transcript provenance, and explicit stop/cancel/retention receipts.
3. **Echo playback:** one admitted TTS profile, local delivery offer, playback start/completion,
   interruption, and unknown-outcome reconciliation.
4. **Riffmaw capture take:** dry guitar/bass DI, spoken or sung takes, device/clock/latency
   manifest, and a new `PerformanceSession@1` without mixing speech into the Echo identity.
5. **Mobile and Familiar body adapter:** USB-C wireless receivers, onboard drone/rover artifacts,
   signal-loss epochs, and mission-owned consent and emergency stop.
6. **Avatar projection:** Avatar selects an eligible voice artifact/profile; Echo owns synthesis,
   delivery, and playback truth.

The first implementation should remain push-to-talk and record-and-send. Wake words, full duplex,
echo cancellation, live jam response, voice cloning, and always-on microphones are separate bakes,
not features to smuggle into the first capture path.
