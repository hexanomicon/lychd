---
title: Speech provider study
icon: material/microphone
---

# Speech provider study

This study compares local and hosted candidates for Slovak, Czech and English. The first
declarations were checked on 21 October 2026, with the focused additions below checked on
23 October. It is not a language-quality bake or an admitted provider catalogue. [Echo](echo.md) owns selection
and [local qualification](echo-local-probe.md) owns the first experiment.

## Local first

| Role | Candidate | Language and license facts | Qualification limit |
| --- | --- | --- | --- |
| STT | [Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) through audio.cpp | Declares `sk`, `cs`, `en` among 25 languages; automatic detection; CC BY 4.0 weights. | Names, numbers, short fragments, noise and language switching require independent recordings. |
| TTS | [Supertonic 3](https://huggingface.co/Supertone/supertonic-3) through audio.cpp | Declares `sk`, `cs`, `en` among 31 languages; stock `M1`–`M5` and `F1`–`F5` voices; OpenRAIL-M weights. | Original upstream [development and support ended](https://github.com/supertone-oss-archive/supertonic); stock voices still require listening and pronunciation review. |

Treat the runtime and weights as separate selections. The runtime uses Apache 2.0, while each
model has its own license; running locally does not make those weights unrestricted open source.
Neither selected profile requires voice cloning.

Another local TTS candidate is [OHF Piper](https://github.com/OHF-Voice/piper1-gpl), whose engine
uses GPL-3.0. Its [voice guide](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md)
requires an ONNX model and JSON configuration per voice. Actual
[Slovak Lili](https://huggingface.co/rhasspy/piper-voices/blob/main/sk/sk_SK/lili/medium/MODEL_CARD)
and [Czech Jirka](https://huggingface.co/rhasspy/piper-voices/blob/main/cs/cs_CZ/jirka/medium/MODEL_CARD)
medium cards each declare one speaker and 22,050 Hz. These are separate language assets,
not one multilingual preset. This qualification did not install, select, time or listen to
these Piper candidates.

Both cards label their target datasets CC0 but also declare fine-tuning from US English Lessac
medium. Its [card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD)
links [research-use source-data terms](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html).
This study does not resolve the terms' effect on distributed weights or output; repository
metadata alone cannot complete that provenance assessment. Engine, target dataset and model
lineage remain distinct.

The first qualification pins audio.cpp release
[`v0.9.2-drama3-base-small`](https://github.com/0xShug0/audio.cpp/releases/tag/v0.9.2-drama3-base-small),
commit `507495611b22dc4590e0e5609e05e8096384e33f`. The CPU portable archive has SHA-256
`d5e6110daae50800429680a277b70557d333d552c4a130a8f1d0e56181fa8697`.
This permits measuring speech without changing GPU drivers or allocating another GPU runtime.
It is not a claim that CPU is the fastest backend.

Compatible standalone GGUF packages are pinned to audio-cpp/audio.cpp-gguf revision
`beb00ab19f10ca33e8a8983a43410527da3f5601`:

| Package | Published bytes | SHA-256 |
| --- | ---: | --- |
| [Parakeet Q8_0](https://huggingface.co/audio-cpp/audio.cpp-gguf/blob/beb00ab19f10ca33e8a8983a43410527da3f5601/Parakeet-TDT-0.6B-v3-GGUF/parakeet-tdt-0.6b-v3-q8_0.gguf) | 915,735,760 | `6fa498f10f8cb606f041aa9512733cfee842a932359b00b0c45b9b723c4f4f4b` |
| [Supertonic original precision](https://huggingface.co/audio-cpp/audio.cpp-gguf/blob/beb00ab19f10ca33e8a8983a43410527da3f5601/Supertonic-3-GGUF/supertonic-3-orig.gguf) | 454,076,228 | `ceede06706a11590dd055220152b44c37a5fb8ac33bb61e19a334e5258901b09` |

The [release model specifications](https://github.com/0xShug0/audio.cpp/tree/v0.9.2-drama3-base-small/model_specs)
define loaders and embedded assets. A similarly named GGUF for another engine is not interchangeable.
The [Parakeet runtime study](https://github.com/0xShug0/audio.cpp/blob/v0.9.2-drama3-base-small/docs/models/parakeet_tdt.md)
supplies useful parity and precision evidence, rather than a measurement of this deployment.

## Explicit CPU transcription alternative

The second candidate, checked on 22 October 2026, is
[whisper.cpp v1.9.5](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.5), pinned to
`d1be6fde11ac6e0407606b4e42fe72d34add8037`, with multilingual
[`ggml-small.bin`](https://huggingface.co/ggerganov/whisper.cpp/blob/80da2d8bfee42b0e836fc3a9890373e5defc00a6/ggml-small.bin).
The MIT model is about 488 MB and has SHA-256
`1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b`.
This is a separate transcription runtime; Supertonic synthesis can retain its existing audio.cpp
binding. It is an explicit alternative, not an automatic fallback or a quality promotion.

The pinned [server implementation](https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/examples/server/server.cpp)
accepts multipart `file`, `language` and `response_format=json`. Its startup `--inference-path`
can select `/v1/audio/transcriptions`. The model loads at startup; a multipart `model` field
does not select weights. The [language table](https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/src/whisper.cpp)
uses `sk`, `cs` and `en`. The engineering profile requires an explicit declared language rather
than relying on the server's default English setting. A CPU build disables accelerator backends
and starts with `--no-gpu`; short-command latency still needs local measurement.

Use the candidate to run a matched comparison before deciding whether to replace a recognizer.
Give both recognizers the same immutable recordings, retain refusals, and test server text framing
separately from word recognition. That separates a change in transport formatting from a change
in what speech the model recognizes. [State of Work](../../state-of-the-work.md#audio-admission)
owns measured delivery and the remaining human checks; this candidate alone cannot justify a
global replacement.

## Hosted alternatives

| Service | STT | TTS | Integration consequence |
| --- | --- | --- | --- |
| Azure Speech | [Fast Transcription](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/fast-transcription-create) supports Slovak, Czech and English locales. | [Voice catalogue](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt) includes `sk-SK-ViktoriaNeural`, `sk-SK-LukasNeural`, `cs-CZ-VlastaNeural`, `cs-CZ-AntoninNeural` and English voices. | Own multipart transcription dialect and [SSML synthesis dialect](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech); select region, locale and voice explicitly. |
| ElevenLabs | [`scribe_v2`](https://elevenlabs.io/docs/overview/capabilities/speech-to-text/) declares all three languages with detection or an optional hint. | [`eleven_flash_v2_5`](https://elevenlabs.io/docs/overview/models) declares all three; [TTS request](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) can bind `language_code`. | Distinct STT and voice-ID TTS routes; `language_code` enforcement is unsupported for `eleven_multilingual_v2`. |
| Google Cloud Speech-to-Text V2 | [`chirp_3`](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3) lists `sk-SK` and `cs-CZ` as Preview; selected English locales are GA. Streaming, synchronous and batch recognition are separate methods. | Not evaluated in this study. | Check the exact method, locale and region; transcription coverage does not imply diarization coverage or local weights. |

These are candidate dialects, not drop-in substitutes for audio.cpp. Hosted weights and service
behavior are provider-managed. A language-identification feature does not by itself promise
reliable code switching within one utterance. Vendor accuracy and latency figures do not qualify
the target microphone, accent or game environment.

The [ElevenLabs model matrix](https://elevenlabs.io/docs/overview/models) distinguishes file
`scribe_v2` from `scribe_v2_realtime`; measurements of one do not qualify the other.
Flash **v2.5** and Multilingual v2 list Slovak, Czech and English; a similarly named model is
not interchangeable. Voice ID, model ID and language enforcement are separate selections.
Google describes automatic recognition of the dominant language, while
[Azure continuous language identification](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-identification)
explicitly does not detect word-by-word language changes within one sentence. Neither declaration
establishes reliable Slovak/English game-term mixing. Keep single-language, between-utterance
switching and within-sentence switching as different tests.

Select a paid service only after a matched recording comparison. Check current
[Azure region/tier pricing](https://azure.microsoft.com/en-us/pricing/details/speech/) or
[ElevenLabs API pricing](https://elevenlabs.io/pricing/api); no fixed cost or free-tier promise is
assumed here. Credentials, destination, retention, voice consent and per-attempt cost bounds need
their own admission. No purchase or hosted voice transmission is implied by this study.
Google's separate [processed-audio pricing](https://cloud.google.com/speech-to-text/pricing)
also needs its exact method/SKU and channel accounting; no effective bill is inferred.

## What to measure

Interleave Slovak, Czech and English recordings, then include one mixed-language case. Score
intent, negation, item identity, count and coordinates separately from punctuation. Include stop,
silence, clipped speech, player names and ordinary game noise. A TTS→STT round trip tests
execution and transport, while independent human recordings and listener review test different
boundaries. An ambiguous transcript must not become an inferred world action.

Measure cold and warm latency separately. Keeping the two small local models resident may avoid
cold loading during play; thread count, idle unload and GPU placement still need host measurements.
Optimize the whole path, including capture duration, Graph scheduling and game response, rather
than reporting inference time as microphone-to-action latency.

When a command fails, distinguish three stages: the generated voice may pronounce the word
poorly, the recognizer may misread it, or a correct transcript may fall outside the companion's
declared fixed-word grammar. Preserve the original transcript and refusal so those causes remain
investigable; do not map a similar-sounding word to a world action.

The current [synthetic command qualification](../../state-of-the-work.md#composition-portfolio-delivery)
includes failed SK/CS/EN examples. Its TTS→STT round trips cannot identify one model as the cause
or establish human accuracy. The next human comparison should therefore reuse exact recordings
across recognizers and exact text across synthesizers. A listener scores pronunciation separately
from parsing and local elapsed time.