"""Synthetic transport contract tests; no model, server, microphone or network."""

import asyncio
import json
import struct
from collections.abc import AsyncIterator
from email.parser import BytesParser
from email.policy import default
from typing import Any

import httpx2
import pytest

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.dictation import DictationProfile, DictationTranscriberError
from lychd.domain.speech_probe import content_digest
from lychd.system.services.dictation_transcriber import LocalDictationTranscriber


def profile(**updates: Any) -> DictationProfile:
    value = {
        "transcriber_binding": {
            "runtime": "whisper.cpp",
            "dialect": "whisper.cpp-batch-v1",
            "endpoint": "http://127.0.0.1:8080",
            "runtime_revision": "a" * 40,
            "backend": "cpu",
            "device": "host",
            "model": {
                "model": "synthetic-whisper-small",
                "family": "whisper-small",
                "digest": "sha256:" + "b" * 64,
                "languages": ["en", "sk"],
                "license": "MIT",
            },
        },
        "transport_timeout_seconds": 2.0,
        "total_timeout_seconds": 3.0,
        **updates,
    }
    return DictationProfile.model_validate_json(json.dumps(value))


def material() -> tuple[ArtifactRef, bytes]:
    pcm = b"\x00\x00" * 8
    content = (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(pcm),
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            16000,
            32000,
            2,
            16,
            b"data",
            len(pcm),
        )
        + pcm
    )
    return ArtifactRef(
        artifact_id="private-synthetic-dictation",
        digest=content_digest(content),
        media_type="audio/wav",
        size=len(content),
        classification="private",
    ), content


class Chunks(httpx2.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.reads = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "Postav dom, prosím.\n", " \t\r\n"])
@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:8080", "http://[::1]:8080"])
async def test_exact_multipart_and_verbatim_text(text: str, endpoint: str) -> None:
    reference, content = material()
    calls = 0
    pinned = profile()
    pinned = pinned.model_copy(
        update={"transcriber_binding": pinned.transcriber_binding.model_copy(update={"endpoint": endpoint})}
    )

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        assert str(request.url) == endpoint + "/v1/audio/transcriptions"
        assert request.method == "POST"
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        raw = b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.content
        message = BytesParser(policy=default).parsebytes(raw)
        parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        assert set(parts) == {"file", "language", "response_format"}
        assert parts["file"].get_payload(decode=True) == content
        assert parts["file"].get_filename() == "utterance.wav"
        assert parts["file"].get_content_type() == "audio/wav"
        assert parts["language"].get_payload(decode=True) == b"sk"
        assert parts["response_format"].get_payload(decode=True) == b"json"
        assert request.extensions["timeout"] == {"connect": 2.0, "read": 2.0, "write": 2.0, "pool": 2.0}
        return httpx2.Response(200, json={"text": text})

    actual = await LocalDictationTranscriber(pinned, httpx2.MockTransport(handler)).transcribe(reference, content, "sk")
    assert actual == text
    assert calls == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint", "http://localhost:8080"),
        ("endpoint", "http://example.com:8080"),
        ("endpoint", "http://127.0.0.1:8080/path"),
        ("backend", "cuda"),
        ("device", "gpu"),
        ("runtime", "audio.cpp"),
    ],
)
def test_constructed_or_copied_profile_is_revalidated(field: str, value: str) -> None:
    pinned = profile()
    binding = pinned.transcriber_binding.model_copy(update={field: value})
    with pytest.raises(DictationTranscriberError) as failure:
        LocalDictationTranscriber(pinned.model_copy(update={"transcriber_binding": binding}))
    assert (failure.value.outcome, failure.value.reason) == ("refused", "not_qualified")
    assert value not in str(failure.value)


@pytest.mark.asyncio
async def test_effect_revalidates_profile_before_http() -> None:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        pytest.fail("Invalid profile reached transport")

    client = LocalDictationTranscriber(profile(), httpx2.MockTransport(handler))
    client.profile = client.profile.model_copy(update={"max_response_bytes": 65_537})
    reference, content = material()
    with pytest.raises(DictationTranscriberError) as failure:
        await client.transcribe(reference, content, "en")
    assert (failure.value.outcome, failure.value.reason) == ("refused", "not_qualified")


@pytest.mark.asyncio
async def test_audio_identity_and_language_refuse_before_http() -> None:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        pytest.fail("Invalid material reached transport")

    client = LocalDictationTranscriber(profile(), httpx2.MockTransport(handler))
    reference, content = material()
    for source, audio, language, reason in (
        (reference.model_copy(update={"digest": "sha256:" + "0" * 64}), content, "en", "invalid_audio"),
        (reference.model_copy(update={"size": len(content) + 1}), content, "en", "invalid_audio"),
        (reference, content + b"x", "en", "invalid_audio"),
        (reference, content, "auto", "language_unavailable"),
        (reference, content, "EN", "language_unavailable"),
    ):
        with pytest.raises(DictationTranscriberError) as failure:
            await client.transcribe(source, audio, language)
        assert (failure.value.outcome, failure.value.reason) == ("refused", reason)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        b'{"text":"a","text":"b"}',
        b'{"text":"ok","extra":1}',
        b'{"text":null}',
        b'{"text":1}',
        b"[]",
        b"{}",
        b'{"text":"\\ud800"}',
        b'{"text":"\\u0000"}',
        b'{"text":NaN}',
        b'{"text":"\xff"}',
        b'{"text":"secret output"',
        b'{"text":"' + b"x" * 8193 + b'"}',
    ],
)
async def test_malformed_ambiguous_or_unknown_response_is_unknown_without_retry(body: bytes) -> None:
    calls = 0

    def handler(_request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, content=body, headers={"Content-Type": "application/json"})

    reference, content = material()
    with pytest.raises(DictationTranscriberError) as failure:
        await LocalDictationTranscriber(profile(), httpx2.MockTransport(handler)).transcribe(reference, content, "en")
    assert calls == 1
    assert (failure.value.outcome, str(failure.value)) == ("unknown", "outcome_unknown")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "headers"),
    [
        (302, {"Location": "http://127.0.0.1:9090/fallback"}),
        (500, {"Content-Type": "application/json"}),
        (200, {"Content-Type": "text/plain"}),
        (200, {"Content-Type": "application/problem+json"}),
        (200, {"Content-Type": "application/json", "Content-Encoding": "gzip"}),
        (200, {"Content-Type": "application/json", "Content-Encoding": "br"}),
        (200, {"Content-Type": "application/json", "Content-Length": "65537"}),
        (200, {"Content-Type": "application/json", "Content-Length": "-1"}),
        (200, {"Content-Type": "application/json", "Content-Length": "2, 2"}),
    ],
)
async def test_bad_headers_never_consume_body_or_redirect(status: int, headers: dict[str, str]) -> None:
    stream = Chunks([b"private server output"])
    calls = 0

    def handler(_request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(status, stream=stream, headers=headers)

    reference, content = material()
    with pytest.raises(DictationTranscriberError, match=r"^outcome_unknown$"):
        await LocalDictationTranscriber(profile(), httpx2.MockTransport(handler)).transcribe(reference, content, "en")
    assert stream.reads == 0
    assert stream.closed
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("declared_length", [None, "12"])
async def test_streamed_limit_enforced_even_with_missing_or_false_length(declared_length: str | None) -> None:
    stream = Chunks([b"x" * 32, b"x" * 33, b"must never read"])
    headers = {"Content-Type": "application/json"}
    if declared_length is not None:
        headers["Content-Length"] = declared_length
    transport = httpx2.MockTransport(lambda _request: httpx2.Response(200, headers=headers, stream=stream))
    reference, content = material()
    with pytest.raises(DictationTranscriberError, match=r"^outcome_unknown$"):
        await LocalDictationTranscriber(profile(max_response_bytes=64), transport).transcribe(reference, content, "en")
    assert stream.reads == 2
    assert stream.closed


@pytest.mark.asyncio
async def test_exact_stream_limit_and_declared_length_are_checked() -> None:
    body = b'{"text":"ok"}'
    reference, content = material()
    for length, succeeds in ((str(len(body)), True), (str(len(body) - 1), False)):
        stream = Chunks([body[:4], body[4:]])
        response = httpx2.Response(
            200,
            stream=stream,
            headers={"Content-Type": "application/json", "Content-Length": length},
        )
        transport = httpx2.MockTransport(lambda _request, response=response: response)
        client = LocalDictationTranscriber(profile(max_response_bytes=len(body)), transport)
        if succeeds:
            assert await client.transcribe(reference, content, "en") == "ok"
        else:
            with pytest.raises(DictationTranscriberError, match=r"^outcome_unknown$"):
                await client.transcribe(reference, content, "en")
        assert stream.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [httpx2.ConnectError, httpx2.ReadTimeout, httpx2.WriteError, RuntimeError])
async def test_transport_errors_are_unknown_and_content_free(error_type: type[Exception]) -> None:
    calls = 0

    def handler(_request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        msg = "private input or response"
        raise error_type(msg)

    reference, content = material()
    with pytest.raises(DictationTranscriberError) as failure:
        await LocalDictationTranscriber(profile(), httpx2.MockTransport(handler)).transcribe(reference, content, "en")
    assert (failure.value.outcome, failure.value.reason) == ("unknown", "outcome_unknown")
    assert failure.value.__suppress_context__
    assert calls == 1


@pytest.mark.asyncio
async def test_total_timeout_and_cancellation_leave_unknown_without_retry() -> None:
    entered = asyncio.Event()
    calls = 0

    async def handler(_request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError

    reference, content = material()
    transport = httpx2.MockTransport(handler)
    client = LocalDictationTranscriber(profile(), transport)
    task = asyncio.create_task(client.transcribe(reference, content, "en"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError) as cancellation:
        await task
    assert "unknown" in cancellation.value.__notes__[0]
    assert calls == 1
    client = LocalDictationTranscriber(profile(transport_timeout_seconds=0.01, total_timeout_seconds=0.01), transport)
    with pytest.raises(DictationTranscriberError, match=r"^outcome_unknown$"):
        await client.transcribe(reference, content, "en")
    assert calls == 2


@pytest.mark.asyncio
async def test_client_disables_ambient_credentials_proxy_and_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    original = httpx2.AsyncClient
    observed: list[dict[str, Any]] = []

    def client_factory(**kwargs: Any) -> httpx2.AsyncClient:
        observed.append(kwargs)
        return original(**kwargs)

    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:8080")
    monkeypatch.setenv("NETRC", "/synthetic/credentials-must-not-be-read")
    monkeypatch.setattr(httpx2, "AsyncClient", client_factory)
    transport = httpx2.MockTransport(lambda _request: httpx2.Response(200, json={"text": ""}))
    reference, content = material()
    assert await LocalDictationTranscriber(profile(), transport).transcribe(reference, content, "en") == ""
    assert len(observed) == 1
    assert observed[0]["trust_env"] is False
    assert observed[0]["follow_redirects"] is False


@pytest.mark.asyncio
async def test_client_setup_failure_is_predispatch_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(**_kwargs: Any) -> httpx2.AsyncClient:
        msg = "private configuration detail"
        raise RuntimeError(msg)

    monkeypatch.setattr(httpx2, "AsyncClient", unavailable)
    reference, content = material()
    with pytest.raises(DictationTranscriberError) as failure:
        await LocalDictationTranscriber(profile()).transcribe(reference, content, "en")
    assert (failure.value.outcome, failure.value.reason) == ("refused", "transport_unavailable")


@pytest.mark.asyncio
async def test_profile_text_limit_refuses_without_truncation() -> None:
    transport = httpx2.MockTransport(lambda _request: httpx2.Response(200, json={"text": "abcd"}))
    reference, content = material()
    with pytest.raises(DictationTranscriberError, match=r"^outcome_unknown$"):
        await LocalDictationTranscriber(profile(max_text_chars=3), transport).transcribe(reference, content, "en")
