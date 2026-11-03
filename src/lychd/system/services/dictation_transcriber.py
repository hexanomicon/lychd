"""One bounded local dictation submission, without retries or Dispatcher admission.

The caller owns authenticated custody, qualification, durable attempt admission and
result retention. A profile pin cannot attest running binaries or loaded weights.
"""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import Any, cast

import httpx

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.dictation import DictationProfile, DictationTranscriberError, validate_text
from lychd.extensions.builtin.echo.material import PcmInspectionError, inspect_pcm_utterance


def _validated_profile(profile: DictationProfile) -> DictationProfile:
    # JSON round-trip revalidates nested model_copy/model_construct bypasses and
    # retains strict tuple handling from the profile's canonical loader contract.
    try:
        return DictationProfile.model_validate_json(profile.model_dump_json())
    except (ValueError, TypeError):
        msg = "refused"
        raise DictationTranscriberError(msg, "not_qualified") from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            msg = "unknown"
            raise DictationTranscriberError(msg, "outcome_unknown")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    msg = "unknown"
    raise DictationTranscriberError(msg, "outcome_unknown")


def _response_length(response: httpx.Response, limit: int) -> int | None:
    if response.status_code != HTTPStatus.OK:
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    # Refuse compression before iterating: raw and decoded byte counts are then
    # identical. No compressed response ever enters an expanding decoder.
    if response.headers.get("Content-Encoding", "identity").strip().lower() != "identity":
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    length = response.headers.get("Content-Length")
    if length is None:
        return None
    if not length.isascii() or not length.isdecimal() or len(length) > len(str(limit)) or int(length) > limit:
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    return int(length)


async def _read_response(response: httpx.Response, profile: DictationProfile) -> str:
    limit = profile.max_response_bytes
    declared_length = _response_length(response, limit)
    body = bytearray()
    async for chunk in response.aiter_bytes():
        if response.num_bytes_downloaded > limit or len(chunk) > limit - len(body):
            msg = "unknown"
            raise DictationTranscriberError(msg, "outcome_unknown")
        body.extend(chunk)
    if declared_length is not None and declared_length != len(body):
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    value: Any = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    response_object = cast("dict[str, Any]", value)
    if set(response_object) != {"text"} or type(response_object["text"]) is not str:
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    text = response_object["text"]
    validate_text(text)
    if len(text) > profile.max_text_chars:
        msg = "unknown"
        raise DictationTranscriberError(msg, "outcome_unknown")
    return text


class LocalDictationTranscriber:
    """Submit once to the explicitly configured whisper.cpp CPU binding.

    The caller must persist an unknown claim before invoking this method. Even a
    connection error is conservatively unknown after submission is entered. This
    adapter neither retries nor reconciles attempts. Cancellation stops local
    waiting only; it makes no claim that remote computation stopped.
    """

    def __init__(self, profile: DictationProfile, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Copy and validate the declared binding without making any request."""
        self.profile = _validated_profile(profile)
        self._transport = transport

    async def transcribe(self, source: ArtifactRef, content: bytes, language: str) -> str:
        """Reinspect exact PCM and preserve even an empty successful transcript."""
        profile = _validated_profile(self.profile)
        try:
            inspect_pcm_utterance(source, content)
        except PcmInspectionError:
            msg = "refused"
            raise DictationTranscriberError(msg, "invalid_audio") from None
        binding = profile.transcriber_binding
        if type(language) is not str or language not in binding.model.languages:
            msg = "refused"
            raise DictationTranscriberError(msg, "language_unavailable")
        submitted = False
        try:
            async with (
                asyncio.timeout(profile.total_timeout_seconds),
                httpx.AsyncClient(
                    transport=self._transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=httpx.Timeout(profile.transport_timeout_seconds),
                    headers={"Accept": "application/json", "Accept-Encoding": "identity"},
                ) as client,
            ):
                # No await separates this fence from entering HTTP submission.
                submitted = True
                async with client.stream(
                    "POST",
                    binding.endpoint + "/v1/audio/transcriptions",
                    data={"language": language, "response_format": "json"},
                    files={"file": ("utterance.wav", content, "audio/wav")},
                ) as response:
                    return await _read_response(response, profile)
        except asyncio.CancelledError as exc:
            if submitted:
                exc.add_note(
                    "Dictation outcome is unknown; local cancellation does not prove server computation stopped."
                )
            raise
        except DictationTranscriberError:
            raise
        except Exception:  # noqa: BLE001 - transport/parser failures must not disclose private input or output
            if submitted:
                msg = "unknown"
                raise DictationTranscriberError(msg, "outcome_unknown") from None
            msg = "refused"
            raise DictationTranscriberError(msg, "transport_unavailable") from None
