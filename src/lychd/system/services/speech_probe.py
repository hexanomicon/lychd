"""Finite local speech requests; no capture, playback, fallback or native grant."""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import Any, cast

import httpx

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.speech_probe import (
    MAX_AUDIO_BYTES,
    STOCK_VOICES,
    LocalSpeechBinding,
    LocalSpeechProfile,
    SpeechModel,
    SpeechProbeError,
    StockVoice,
    SynthesisObservation,
    TranscriptObservation,
    WavFacts,
    content_digest,
    load_speech_profile,
)
from lychd.extensions.builtin.echo.material import inspect_pcm_utterance

_HEADER_BYTES = 44
_MAX_DURATION_SECONDS = 120
_MIN_SAMPLE_RATE = 8000
_MAX_SAMPLE_RATE = 192000
_MAX_JSON_BYTES = 65_536
_FIRST_PRINTABLE = 32


def inspect_generated_wav(content: bytes) -> WavFacts:
    """Accept canonical PCM WAV with bounded duration, independently of Echo input.

    This dialect supports one/two channels, 8..192 kHz, 8/16/24/32-bit integer
    PCM. Ancillary chunks, compression and implicit conversion are refused.
    The caller bounds response acquisition before this inspection.
    """
    if type(content) is not bytes or not _HEADER_BYTES <= len(content) <= MAX_AUDIO_BYTES:
        msg = "Generated audio must be canonical PCM WAV."
        raise SpeechProbeError(msg)
    if (content[:4], content[8:16], content[16:20], content[36:40]) != (
        b"RIFF",
        b"WAVEfmt ",
        b"\x10\x00\x00\x00",
        b"data",
    ):
        msg = "Generated audio must be canonical PCM WAV."
        raise SpeechProbeError(msg)
    encoding = int.from_bytes(content[20:22], "little")
    channels = int.from_bytes(content[22:24], "little")
    rate = int.from_bytes(content[24:28], "little")
    byte_rate = int.from_bytes(content[28:32], "little")
    alignment = int.from_bytes(content[32:34], "little")
    bits = int.from_bytes(content[34:36], "little")
    if (
        encoding != 1
        or channels not in (1, 2)
        or bits not in (8, 16, 24, 32)
        or not _MIN_SAMPLE_RATE <= rate <= _MAX_SAMPLE_RATE
    ):
        msg = "Generated PCM profile is outside the probe bounds."
        raise SpeechProbeError(msg)
    width = bits // 8
    data_size = len(content) - _HEADER_BYTES
    if (
        alignment != channels * width
        or byte_rate != rate * alignment
        or int.from_bytes(content[4:8], "little") != len(content) - 8
        or int.from_bytes(content[40:44], "little") != data_size
        or data_size % alignment
        or not 1 <= data_size // alignment <= rate * _MAX_DURATION_SECONDS
    ):
        msg = "Generated WAV lengths, rates or duration are invalid."
        raise SpeechProbeError(msg)
    return WavFacts(
        sample_rate_hz=rate, channels=channels, sample_width_bytes=width, frame_count=data_size // alignment
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            msg = "Provider JSON contains duplicate fields."
            raise SpeechProbeError(msg)
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    msg = "Nonfinite JSON values are refused."
    raise SpeechProbeError(msg)


def _valid_text(text: str, limit: int, *, allow_empty: bool) -> bool:
    if len(text) > limit or (not allow_empty and not text.strip()):
        return False
    try:
        text.encode("utf-8")
    except UnicodeError:
        return False
    return not any(ord(char) < _FIRST_PRINTABLE and char not in "\n\t\r" for char in text)


def _response_length(response: httpx.Response, limit: int, expected_type: str) -> int | None:
    if response.status_code != HTTPStatus.OK:
        msg = "Speech request refused by HTTP status; server work is unconfirmed."
        raise SpeechProbeError(msg)
    if response.headers.get("Content-Encoding", "identity").strip().lower() != "identity":
        msg = "Encoded speech responses are refused."
        raise SpeechProbeError(msg)
    length = response.headers.get("Content-Length")
    if length is not None and (not length.isascii() or not length.isdecimal() or int(length) > limit):
        msg = "Speech response exceeds its declared bound."
        raise SpeechProbeError(msg)
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != expected_type:
        msg = "Speech response has an unexpected media type."
        raise SpeechProbeError(msg)
    return int(length) if length is not None else None


class SpeechProbe:
    """Each call submits one explicit request, with no automatic resubmission.

    A profile records operator-declared identities; this HTTP dialect cannot
    attest which binary or weights the server actually loaded. Cancellation
    propagates to the caller and stops local waiting, not proven server work.
    """

    def __init__(self, profile: LocalSpeechProfile, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Revalidate even copied profile objects before admitting an endpoint."""
        self.profile = load_speech_profile(profile.model_dump_json())
        self._transport = transport

    async def _request(
        self,
        binding: LocalSpeechBinding,
        route: str,
        *,
        json_body: dict[str, Any] | None = None,
        audio: bytes | None = None,
        form_fields: dict[str, str] | None = None,
    ) -> bytes:
        files = {"file": ("utterance.wav", audio, "audio/wav")} if audio is not None else None
        limit = (
            min(_MAX_JSON_BYTES, self.profile.max_response_bytes)
            if audio is not None
            else self.profile.max_response_bytes
        )
        try:
            async with (
                asyncio.timeout(self.profile.total_timeout_seconds),
                httpx.AsyncClient(
                    transport=self._transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=httpx.Timeout(self.profile.transport_timeout_seconds),
                    headers={"Accept-Encoding": "identity"},
                ) as client,
                client.stream(
                    "POST",
                    binding.endpoint + route,
                    json=json_body,
                    data=form_fields if audio is not None else None,
                    files=files,
                ) as response,
            ):
                expected_type = "application/json" if audio is not None else "audio/wav"
                length = _response_length(response, limit, expected_type)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(chunk) > limit - len(body):
                        msg = "Speech response exceeds its byte bound."
                        raise SpeechProbeError(msg)
                    body.extend(chunk)
                if length is not None and len(body) != length:
                    msg = "Speech response length does not match its header."
                    raise SpeechProbeError(msg)
                return bytes(body)
        except asyncio.CancelledError as exc:
            exc.add_note("Local speech waiting cancelled; server inference outcome is unknown. No retry was attempted.")
            raise
        except (httpx.HTTPError, TimeoutError):
            msg = "Speech transport failed or expired; server work is unknown. No retry was attempted."
            raise SpeechProbeError(msg) from None

    async def transcribe(
        self, source: ArtifactRef, content: bytes, *, language: str | None = None
    ) -> TranscriptObservation:
        """Inspect exact supplied audio and preserve provenance for its interpretation."""
        inspect_pcm_utterance(source, content)
        language = self.profile.language_for_transcription(language)
        binding = self.profile.transcriber_binding
        fields = (
            {"response_format": "json"} if binding.dialect == "whisper.cpp-batch-v1" else {"model": binding.model.model}
        )
        if language is not None:
            fields["language"] = language
        raw = await self._request(binding, "/v1/audio/transcriptions", audio=content, form_fields=fields)
        try:
            value: Any = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        except (ValueError, UnicodeError, RecursionError):
            msg = "Transcription response is not valid unambiguous JSON."
            raise SpeechProbeError(msg) from None
        if not isinstance(value, dict):
            msg = "Transcription response must contain a text object."
            raise SpeechProbeError(msg)
        response_object = cast("dict[str, Any]", value)
        if type(response_object.get("text")) is not str:
            msg = "Transcription response must contain text."
            raise SpeechProbeError(msg)
        text = cast("str", response_object["text"])
        if not _valid_text(text, self.profile.max_text_chars, allow_empty=True):
            msg = "Transcription text exceeds the probe bounds."
            raise SpeechProbeError(msg)
        return TranscriptObservation(
            source=source,
            profile_digest=self.profile.digest,
            runtime_revision=binding.runtime_revision,
            model=binding.model,
            requested_language=language,
            text=text,
        )

    async def synthesize(self, text: str, *, language: str, voice: StockVoice) -> tuple[SynthesisObservation, bytes]:
        """Generate bounded WAV with a stock voice; never play the returned bytes."""
        language = self.profile.language_for_synthesis(language)
        if type(text) is not str or not _valid_text(text, self.profile.max_text_chars, allow_empty=False):
            msg = "Synthesis text is empty or outside the probe bounds."
            raise SpeechProbeError(msg)
        if voice not in STOCK_VOICES:
            msg = "Only a declared stock voice is supported."
            raise SpeechProbeError(msg)
        binding = self.profile.synthesizer_binding
        content = await self._request(
            binding,
            "/v1/audio/speech",
            json_body={
                "model": binding.model.model,
                "input": text,
                "language": language,
                "voice": voice,
                "seed": 1234,
                "response_format": "wav",
            },
        )
        facts = inspect_generated_wav(content)
        observation = SynthesisObservation(
            profile_digest=self.profile.digest,
            runtime_revision=binding.runtime_revision,
            model=cast("SpeechModel", binding.model),
            requested_language=language,
            voice=voice,
            text_digest=content_digest(text.encode()),
            audio_digest=content_digest(content),
            size=len(content),
            wav=facts,
        )
        return observation, content
