---
title: Audio Hardware and Host Routes
icon: material/connection
---

# :material-connection: Audio Hardware and Host Routes

A microphone route must be proved on the host before Echo can transcribe speech or Riffmaw can
keep a take. Begin with the real desktop's device and signal evidence, connect one bounded route,
then decide which application may arm and retain it. The same audio hardware can serve several
owners without combining their permission or chronology.

ALSA device interfaces and PipeWire's audio-routing nodes, USB devices, finite host helpers, and
in-process libraries are attachments
or tool routes. Animator manages an independently resident, queued, shared, or remote service when
its lifecycle warrants that contract. This page supplies the hardware map;
[Audio](../../adr/37-audio.md) owns capture consent, custody, transport, interruption, and playback
law.

## Current LychD boundary

The repository currently proves audio modality metadata and the `stt`/`tts` capability labels.
Capture, recorded-byte custody, audio transport, inference, and playback remain Designed under
[State's audio-admission boundary](../../state-of-the-work.md#audio-admission). Use this page to
plan and test a host route; it supplies neither a host receipt nor an operational application path.

| Office | Owns | Does not own |
| --- | --- | --- |
| [Echo](../extensions/echo.md) | bounded speech capture, transcription, synthesis, delivery, interruption, and playback chronology | musical performance, arbitrary ambient recording, or identity |
| [Riffmaw](../../compositions/riffmaw/index.md) | instrumental and musical-vocal takes, music production, sessions, and music lineage | ordinary speech, dialogue, picture sound, or publication |
| [Companion](../../compositions/companion/index.md) | mobile capture/playback controls, disclosure indicators, local interaction state, and reconnect | speech-attempt custody, transcription, synthesis, or playback chronology |
| [Avatar](../../compositions/avatar/index.md) | an eligible voice reference inside a presentation profile and target projection | microphone authority, cloning permission, or proof of playback |
| [Familiar](../../compositions/familiar/index.md) | admitted physical body, mission, safety envelope, onboard sensors, and physical speaker | Persona identity, Avatar presentation, attention, or retention of every sensor byte |
| [Tether](../extensions/tether.md) / [Portal](portal.md) | private reachability / admitted remote-service boundary | caller authority, recording consent, chronology, or device authority |

One physical device may participate in several independently armed routes. Shared ALSA or PipeWire
mechanics do not merge their grants, records, retention, or acceptance.

## Host receipt boundary

A useful host receipt must come from the real desktop login that owns PipeWire and the audio
devices. A restricted shell, container, or coding-agent session without `/dev/snd`, D-Bus, or the
user PipeWire socket proves only that the session lacks access.

Before promoting a route, record the OS and kernel, exact board or USB-device identity, loaded
driver, ALSA capture/playback inventory, PipeWire/WirePlumber graph, selected sample format and
rate, mute and gain state, and one measured record/playback result. Planning prose or a device
advertisement cannot substitute for that observation.

## Tumbleweed readiness sequence

On openSUSE Tumbleweed, run checks in the real desktop login, not a restricted agent terminal.
Capture the read-only substrate report first:

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

1. Confirm PipeWire, WirePlumber, required ALSA/PipeWire compatibility packages, FFmpeg, and ALSA
   utilities for the exact host revision.
2. Connect one USB audio device directly rather than through an unpowered hub.
3. Confirm its exact identity in `arecord -l`, `aplay -l`, and `wpctl status`.
4. Record a five-second dry sample with `arecord`; validate the file and playback before adding a
   model or DAW.
5. Add `qpwgraph` or `pavucontrol` only when the desktop mixer needs a visual routing surface.
6. Add Guitarix and Ardour or Reaper only after the interface is stable at 48 kHz; measure buffer underruns or overruns (xruns)
   and round-trip latency before calling the setup realtime-ready.

Do not answer missing onboard audio by blindly changing kernel parameters. Retain `lspci -nnk`,
`journalctl -k -b`, firmware audio settings, and rear/front jack wiring before forming a
board-specific hypothesis. A separately proved USB interface may provide a bounded guitar, bass,
or speech route while onboard audio remains under investigation.

## Bounded implementation order

1. **Host attachment/tool adapter:** enumerate ALSA/PipeWire devices and retain route facts without
   granting capture; handles and PCM remain outside Graph state, and this finite path is not an
   Animator.
2. **Echo record-and-send:** visible push-to-talk, bounded capture, immutable source artifact, one
   admitted STT profile, transcript provenance, and stop/cancel/retention receipts.
3. **Echo playback:** one admitted TTS profile, local delivery offer, playback start/completion,
   interruption, and unknown-outcome reconciliation.
4. **Riffmaw capture take:** dry direct-input (DI) instrument signal or musical vocal under an exact device/clock/latency
   manifest, producing `PerformanceTake@1` without absorbing ordinary speech.
5. **Mobile and Familiar adapter:** exact USB-C or onboard routes, signal-loss epochs, mission-owned
   consent, and independently reachable stop behavior.
6. **Avatar projection:** Avatar selects an eligible voice reference; Echo retains synthesis,
   delivery, and playback chronology.

The first speech slice remains push-to-talk and record-and-send. Wake words, full duplex, echo
cancellation, live jam response, voice cloning, and always-on microphones require separate bakes.

## One desk, separate routes

The same PipeWire graph may expose both devices while the host arms their semantic routes
independently:

```text
FIFINE AM8 (USB) ───────────→ PipeWire/WirePlumber ─→ Echo speech route

UMC202HD (USB) ← XLR mic ───→ PipeWire/WirePlumber ─→ Riffmaw musical-vocal route
                ← guitar/bass 6.35 mm TS ───────────→ Riffmaw instrument route
```

For simultaneous voice and guitar, input 1 may receive an eligible XLR microphone and input 2 the
guitar or bass. Keep `48 V` **off** for a dynamic microphone and for guitar/bass; use `INST/Hi-Z`
for the instrument input, start at low gain, and watch the clip indicator. Which application may
retain each channel is still decided before capture.

For amp simulation, monitor through Guitarix or another native Linux effect chain and turn direct
monitoring off to avoid hearing both dry DI and processed signal. For clean practice or a
latency-sensitive take, turn it on. Riffmaw keeps the dry DI signal separate from the amp/cabinet print so a later mix can repair the
sound. The motherboard headphone output may remain ordinary desktop
playback; interface headphones are preferable for latency-sensitive tracking.

## Candidate device profiles

These devices are replaceable examples, not purchasing recommendations or compatibility claims.
Pin the exact model and revision, use a returnable evaluation path, and require the same Linux
receipt from every substitute; a connector shape or vendor claim for another OS proves nothing on
the target host.

| Use | Candidate example | Why it is worth a bake | Linux receipt required |
| --- | --- | --- | --- |
| PC speech at a desk | [FIFINE AM8](https://fifinemicrophone.com/products/fifine-ampligame-am8-microphone) | Dynamic cardioid USB/XLR microphone with mute and headphone monitoring; close placement can reduce room pickup | Prove capture, mute indication, monitoring, format/rate negotiation, suspend/resume, and reconnect without depending on FIFINE Genie. |
| Quiet-room desk alternative | [Razer Seiren V3 Mini](https://www.razer.com/streaming-microphones/razer-seiren-v3-mini) | Small USB condenser with tap-to-mute; its maker describes plug-and-play operation | Prove the basic class-compliant path, mute state, negotiated format, and reconnect; Linux is not the advertised support target. |
| Shirt/mobile speech | [Hollyland LARK M2 USB-C](https://www.hollyland.com/support/lark-m2) | Compact 2.4 GHz transmitter/receiver route for a phone or nearby computer | Prove exact receiver enumeration, intended channel/rate facts, disconnect, and battery-loss settlement; do not infer Linux support from USB-C. |
| Guitar and bass interface | [Behringer UMC202HD](https://www.behringer.com/en/products/0805-AAR) | Two inputs, instrument path, headphone output, direct monitoring, and 48 V for an eligible condenser microphone | Prove capture/playback channels, instrument impedance, direct monitor, rate stability, xruns, and reconnect; the vendor page is not a Linux support promise. |
| Alternative two-input interface | [Audient EVO 4](https://audient.com/products/audio-interfaces/evo-4/overview/) | Two preamps, instrument input, headphone/output routing, and direct-monitor controls | Prove which controls work without the vendor app, then retain capture/playback, monitoring, rate, xrun, suspend, and reconnect facts. |

### Weak primary routes

- **TWS earbuds** are useful for listening, but their Bluetooth microphone commonly falls to a
  lower-bandwidth telephony profile with more compression and latency. Keep them as playback or an
  emergency speech route, not primary musical capture.
- **Bluetooth lavaliers without a receiver** add profile negotiation and latency uncertainty. A
  separately proved 2.4 GHz set with a USB-C receiver is usually the more bounded candidate.
- **Motherboard mic/line input for guitar** does not replace a high-impedance instrument input.
  Onboard audio may remain useful for ordinary playback and headphones.
- **Cheap anonymous BM-800 kits** commonly add noisy adapters or ambiguous phantom-power wiring;
  they are a weak Linux-first foundation.

## Mobile, drone, and rover routes

### Mobile and body-worn

Use an exact USB-C receiver on the phone and a separately proved compatible receiver or USB input
on the Linux host. Keep a body-worn transmitter clear of fabric, jewelry, and zippers. Pairing
does not authorize continuous recording; Companion owns physical controls and indicators while
Echo owns each admitted speech attempt and its chronology.

### Drone

Consumer camera drones rarely accept a useful external microphone, and propeller wash dominates
an exposed capsule. Prefer a small onboard recorder or digital-camera path whose bounded artifact
is transferred after flight. For live speech, put the lavalier on the person or use a dedicated
radio/body payload; do not hang TWS earbuds or a Bluetooth microphone on the airframe.

### RC car or rover

For a rover with an SBC or camera, a protected MEMS/electret microphone near the chassis may record
locally at 48 kHz after a real bake. Isolate it mechanically from the motor and drivetrain. Send a
bounded low-rate preview only when the mission admits live audio, and retain full WAV only when
capture and retention are separately admitted. Familiar owns the body and signal-loss policy;
Echo may later transcribe an admitted artifact.
