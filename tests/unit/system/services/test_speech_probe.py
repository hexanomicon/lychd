import asyncio
import io
import json
import socket
import wave
from collections.abc import AsyncIterator, Callable
from email.parser import BytesParser
from email.policy import default
from typing import cast

import httpx
import pytest
from pydantic import ValidationError

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.speech_probe import LocalSpeechProfile, SpeechProbeError, StockVoice, content_digest
from lychd.extensions.builtin.echo.material import PcmInspectionError
from lychd.system.services.speech_probe import SpeechProbe, inspect_generated_wav
from tests.unit.domain.test_speech_probe import profile, profile_v2


def wav(rate: int = 16000, channels: int = 1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(b"\x00\x00" * channels * 8)
    return output.getvalue()


def source(content: bytes) -> ArtifactRef:
    return ArtifactRef(
        artifact_id="explicit-private-test",
        digest=content_digest(content),
        media_type="audio/wav",
        size=len(content),
        classification="private",
    )


def probe(handler: Callable[[httpx.Request], httpx.Response], pinned: LocalSpeechProfile | None = None) -> SpeechProbe:
    return SpeechProbe(pinned or profile(), transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["sk", None])
async def test_actual_multipart_has_exact_audio_model_optional_language_and_provenance(language: str | None) -> None:
    content = wav()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert str(request.url) == "http://127.0.0.1:8080/v1/audio/transcriptions"
        assert request.method == "POST"
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        raw = b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.content
        message = BytesParser(policy=default).parsebytes(raw)
        fields = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        assert set(fields) == ({"file", "model", "language"} if language else {"file", "model"})
        assert fields["file"].get_payload(decode=True) == content
        assert fields["file"].get_filename() == "utterance.wav"
        assert fields["model"].get_payload(decode=True) == b"parakeet-test"
        if language:
            assert fields["language"].get_payload(decode=True) == b"sk"
        assert request.extensions["timeout"] == {"connect": 2.0, "read": 2.0, "write": 2.0, "pool": 2.0}
        return httpx.Response(200, json={"text": "Postav dom, prosím.", "confidence": 0.99, "language": "en"})

    reference = source(content)
    result = await probe(handler).transcribe(reference, content, language=language)
    assert calls == 1
    assert result.source == reference
    assert result.text == "Postav dom, prosím."
    assert result.requested_language == language
    assert result.model.model == "parakeet-test"
    assert result.profile_digest == profile().digest
    assert "confidence" not in result.model_dump()
    assert "detected_language" not in result.model_dump()
    assert result.native_echo_admission is False


@pytest.mark.asyncio
async def test_synthesis_sends_separate_binding_seed_stock_voice_and_validates_non_16k_output() -> None:
    content = wav(44100, 2)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/speech"
        assert json.loads(request.content) == {
            "model": "supertonic-test",
            "input": "Ahoj, svet.",
            "language": "sk",
            "voice": "F5",
            "seed": 1234,
            "response_format": "wav",
        }
        return httpx.Response(200, content=content, headers={"Content-Type": "audio/wav"})

    result, returned = await probe(handler).synthesize("Ahoj, svet.", language="sk", voice="F5")
    assert returned == content
    assert result.wav.sample_rate_hz == 44100
    assert result.wav.channels == 2
    assert result.audio_digest == content_digest(content)
    assert result.text_digest == content_digest(b"Ahoj, svet.")
    assert result.playback == "not_attempted"
    assert result.native_echo_admission is False


@pytest.mark.asyncio
async def test_refusal_before_request_for_wrong_hash_language_text_or_voice() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid input reached HTTP transport")

    client = probe(handler)
    content = wav()
    with pytest.raises(PcmInspectionError):
        await client.transcribe(source(content).model_copy(update={"digest": "sha256:" + "0" * 64}), content)
    with pytest.raises(PcmInspectionError):
        await client.transcribe(source(wav(44100)), wav(44100))
    with pytest.raises(SpeechProbeError):
        await client.transcribe(source(content), content, language="ja")
    for text, language, voice in (
        ("words", "ja", "M1"),
        ("", "sk", "M1"),
        ("x" * 257, "sk", "M1"),
        ("words", "sk", "clone"),
        ("x\x00", "sk", "M1"),
        ("\ud800", "sk", "M1"),
    ):
        with pytest.raises(SpeechProbeError):
            await client.synthesize(text, language=language, voice=cast("StockVoice", voice))
    with pytest.raises(ValidationError):
        SpeechProbe(profile().model_copy(update={"endpoint": "http://example.com"}))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://example.com"}),
        httpx.Response(500, text="private server detail must not be logged"),
        httpx.Response(200, content=b"bad", headers={"Content-Type": "audio/wav"}),
        httpx.Response(200, content=b'{"text":"a","text":"b"}', headers={"Content-Type": "application/json"}),
        httpx.Response(200, json={"text": "x" * 257}),
        httpx.Response(200, json={"text": 123}),
        httpx.Response(200, content=b'{"text":"\\ud800"}', headers={"Content-Type": "application/json"}),
        httpx.Response(200, content=b'{"text":"ok","x":NaN}', headers={"Content-Type": "application/json"}),
        httpx.Response(200, content=b"x" * 65537, headers={"Content-Type": "application/json"}),
        httpx.Response(200, content=b"{}", headers={"Content-Type": "application/json", "Content-Encoding": "br"}),
    ],
)
async def test_invalid_status_json_encoding_or_bound_is_content_free_and_never_retried(
    response: httpx.Response,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    content = wav()
    with pytest.raises(SpeechProbeError) as failure:
        await probe(handler).transcribe(source(content), content)
    assert calls == 1
    assert "private server detail" not in str(failure.value)


class Chunks(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"x" * 50
        yield b"x" * 51


@pytest.mark.asyncio
async def test_streamed_body_is_bounded_even_without_content_length() -> None:
    pinned = profile().model_copy(update={"max_response_bytes": 100})
    client = probe(lambda _request: httpx.Response(200, stream=Chunks(), headers={"Content-Type": "audio/wav"}), pinned)
    with pytest.raises(SpeechProbeError, match="byte bound"):
        await client.synthesize("words", language="sk", voice="M1")


@pytest.mark.asyncio
async def test_transport_timeout_has_unknown_outcome_and_no_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        msg = "secret input"
        raise httpx.ReadTimeout(msg, request=request)

    with pytest.raises(SpeechProbeError, match="unknown") as failure:
        await probe(handler).synthesize("private words", language="sk", voice="M1")
    assert calls == 1
    assert "secret input" not in str(failure.value)


@pytest.mark.asyncio
async def test_total_deadline_and_cancellation_stop_local_waiting_only() -> None:
    entered = asyncio.Event()
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError

    client = SpeechProbe(profile(), transport=httpx.MockTransport(handler))
    task = asyncio.create_task(client.synthesize("private words", language="sk", voice="M1"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError) as failure:
        await task
    assert "unknown" in failure.value.__notes__[0]
    assert calls == 1
    short = profile().model_copy(update={"total_timeout_seconds": 0.01})
    with pytest.raises(SpeechProbeError, match="unknown"):
        await SpeechProbe(short, transport=httpx.MockTransport(handler)).synthesize("words", language="sk", voice="M1")
    assert calls == 2


@pytest.mark.parametrize("content", [b"", b"RIFF", wav() + b"trailing", wav()[:40] + b"\x00\x00\x00\x00", wav(1)])
def test_generated_wav_rejects_invalid_lengths_profiles_and_empty_data(content: bytes) -> None:
    with pytest.raises(SpeechProbeError):
        inspect_generated_wav(content)


@pytest.mark.asyncio
async def test_default_transport_ignores_ambient_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    content = wav()
    requests: list[bytes] = []

    async def respond(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            async with asyncio.timeout(2):
                headers = await reader.readuntil(b"\r\n\r\n")
                length = next(
                    int(line.split(b":", 1)[1])
                    for line in headers.split(b"\r\n")
                    if line.lower().startswith(b"content-length:")
                )
                assert 0 < length < 4096
                requests.append(await reader.readexactly(length))
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: audio/wav\r\nContent-Length: "
                    + str(len(content)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + content
                )
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(respond, "127.0.0.1", 0, limit=4096)
    async with server, asyncio.timeout(5):
        endpoint = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        # Reserving without listening makes the proxy deterministically refuse connections.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy:
            proxy.bind(("127.0.0.1", 0))
            proxy_url = f"http://127.0.0.1:{proxy.getsockname()[1]}"
            for variable in ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
                monkeypatch.setenv(variable, proxy_url)
            for variable in ("NO_PROXY", "no_proxy"):
                monkeypatch.setenv(variable, "")
            # This control proves that the environment actually intercepts default HTTPX traffic.
            async with httpx.AsyncClient(trust_env=True, timeout=0.5) as ambient:
                with pytest.raises(httpx.ConnectError):
                    await ambient.post(endpoint, content=b"control")
            assert requests == []
            pinned = profile().model_copy(update={"endpoint": endpoint})
            result, returned = await SpeechProbe(pinned).synthesize("words", language="sk", voice="M1")
            assert returned == content
            assert result.generated is True
            assert len(requests) == 1
            assert json.loads(requests[0])["input"] == "words"


@pytest.mark.parametrize("transcriber", ["whisper", "parakeet"])
@pytest.mark.asyncio
async def test_version_two_uses_operation_endpoint_dialect_model_and_revision(transcriber: str) -> None:
    pinned = profile_v2()
    if transcriber == "parakeet":
        pinned = pinned.model_copy(update={"transcriber_binding": profile().transcriber_binding})
    calls: list[str] = []
    content = wav()

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        if request.url.path == "/v1/audio/transcriptions":
            raw = b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.content
            message = BytesParser(policy=default).parsebytes(raw)
            fields = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
            assert fields["file"].get_payload(decode=True) == content
            assert fields["language"].get_payload(decode=True) == b"sk"
            if transcriber == "whisper":
                assert set(fields) == {"file", "language", "response_format"}
                assert fields["response_format"].get_payload(decode=True) == b"json"
            else:
                assert set(fields) == {"file", "language", "model"}
                assert fields["model"].get_payload(decode=True) == b"parakeet-test"
            return httpx.Response(200, json={"text": " Čakaj!\n"})
        assert str(request.url) == "http://127.0.0.1:8082/v1/audio/speech"
        assert json.loads(request.content)["model"] == "supertonic-test"
        return httpx.Response(200, content=content, headers={"Content-Type": "audio/wav"})

    client = probe(handler, pinned)
    transcript = await client.transcribe(source(content), content, language="sk")
    synthesis, audio = await client.synthesize("Čakám.", language="sk", voice="M1")
    assert calls == [
        f"{pinned.transcriber_binding.endpoint}/v1/audio/transcriptions",
        "http://127.0.0.1:8082/v1/audio/speech",
    ]
    assert transcript.text == " Čakaj!\n"
    assert transcript.runtime_revision == pinned.transcriber_binding.runtime_revision
    assert synthesis.runtime_revision == "e" * 40
    assert transcript.model == pinned.transcriber_binding.model
    assert synthesis.model == pinned.synthesizer_binding.model
    assert transcript.profile_digest == pinned.digest
    assert synthesis.profile_digest == pinned.digest
    assert transcript.native_echo_admission is False
    assert synthesis.native_echo_admission is False
    assert audio == content


@pytest.mark.parametrize("language", [None, "ja", "", "SK"])
@pytest.mark.asyncio
async def test_whisper_refuses_missing_or_unsupported_language_before_any_request(language: str | None) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("An undeclared or missing Whisper language reached HTTP")

    content = wav()
    with pytest.raises(SpeechProbeError, match="language"):
        await probe(handler, profile_v2()).transcribe(source(content), content, language=language)


@pytest.mark.parametrize("role", ["transcriber_binding", "synthesizer_binding"])
@pytest.mark.parametrize("field", ["endpoint", "dialect", "model"])
def test_version_two_copied_binding_tampering_is_revalidated_before_use(role: str, field: str) -> None:
    pinned = profile_v2()
    binding = getattr(pinned, role)
    changed: object = {
        "endpoint": "http://example.com:8080",
        "dialect": "unsupported-dialect",
        "model": binding.model.model_copy(update={"family": "unsupported-family"}),
    }[field]
    tampered = pinned.model_copy(update={role: binding.model_copy(update={field: changed})})
    with pytest.raises(ValidationError):
        SpeechProbe(tampered)


@pytest.mark.parametrize("status", [302, 400, 500])
@pytest.mark.asyncio
async def test_whisper_failure_never_selects_the_synthesizer_or_another_runtime(status: int) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(status, headers={"location": "http://127.0.0.1:8082/v1/audio/transcriptions"})

    content = wav()
    with pytest.raises(SpeechProbeError, match="unconfirmed"):
        await probe(handler, profile_v2()).transcribe(source(content), content, language="sk")
    assert calls == ["http://127.0.0.1:8081/v1/audio/transcriptions"]


@pytest.mark.asyncio
async def test_whisper_total_deadline_and_cancellation_keep_server_work_unknown_without_retry() -> None:
    entered = asyncio.Event()
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError

    content = wav()
    client = SpeechProbe(profile_v2(), transport=httpx.MockTransport(handler))
    task = asyncio.create_task(client.transcribe(source(content), content, language="sk"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError) as failure:
        await task
    assert "unknown" in failure.value.__notes__[0]
    short = profile_v2().model_copy(update={"total_timeout_seconds": 0.01})
    with pytest.raises(SpeechProbeError, match="unknown"):
        await SpeechProbe(short, transport=httpx.MockTransport(handler)).transcribe(
            source(content), content, language="sk"
        )
    assert calls == 2
