import json
import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest
from click.testing import CliRunner
from scripts import voice_probe

from lychd.domain.speech_probe import LocalSpeechProfile, SpeechProbeError, content_digest
from lychd.system.services.speech_probe import SpeechProbe
from tests.unit.domain.test_speech_probe import profile, profile_v2
from tests.unit.system.services.test_speech_probe import wav


def private_file(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    path.chmod(0o600)
    return path


@pytest.fixture
def external_root() -> Iterator[Path]:
    # make test keeps its ordinary basetemp inside the checkout; private material cannot go there.
    with TemporaryDirectory(prefix="lychd-speech-test-") as folder:
        yield Path(folder)


@pytest.fixture
def workspace(external_root: Path) -> Path:
    result = external_root / "private"
    result.mkdir(mode=0o700)
    return result


def options(workspace: Path) -> list[str]:
    pinned = private_file(workspace / "profile.json", profile().model_dump_json().encode())
    return [
        "--workspace",
        str(workspace),
        "--checkout-root",
        str(workspace.parent / "checkout"),
        "--profile",
        str(pinned),
    ]


def mock_probe(monkeypatch: pytest.MonkeyPatch, response: httpx.Response) -> list[httpx.Request]:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return response

    def factory(pinned: LocalSpeechProfile) -> SpeechProbe:
        return SpeechProbe(pinned, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(voice_probe, "SpeechProbe", factory)
    return calls


def test_schema_and_profile_do_not_contact_server(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = mock_probe(monkeypatch, httpx.Response(500))
    runner = CliRunner()
    assert runner.invoke(voice_probe.cli, ["schema"]).exit_code == 0
    result = runner.invoke(voice_probe.cli, ["profile", *options(workspace)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["profile_digest"] == profile().digest
    assert calls == []


def test_transcribe_retains_private_attributed_result_without_printing_words(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private_words = "Súkromný slovenský prepis."
    calls = mock_probe(monkeypatch, httpx.Response(200, json={"text": private_words}))
    content = wav()
    source = private_file(workspace / "utterance.wav", content)
    output = workspace / "transcript.json"
    result = CliRunner().invoke(
        voice_probe.cli,
        [
            "transcribe",
            *options(workspace),
            "--source",
            str(source),
            "--source-digest",
            content_digest(content),
            "--source-id",
            "explicit-recording",
            "--language",
            "sk",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    retained = json.loads(output.read_bytes())
    assert retained["text"] == private_words
    assert retained["source"]["digest"] == content_digest(content)
    assert output.stat().st_mode & 0o777 == 0o600
    assert private_words not in result.output
    assert len(calls) == 1


def test_synthesis_retains_wav_and_generation_facts_without_playback(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio = wav(44100)
    calls = mock_probe(monkeypatch, httpx.Response(200, content=audio, headers={"Content-Type": "audio/wav"}))
    words = private_file(workspace / "words.txt", "Ahoj, súkromný svet.".encode())
    output, receipt = workspace / "speech.wav", workspace / "receipt.json"
    result = CliRunner().invoke(
        voice_probe.cli,
        [
            "synthesize",
            *options(workspace),
            "--text",
            str(words),
            "--language",
            "sk",
            "--voice",
            "M1",
            "--output",
            str(output),
            "--receipt",
            str(receipt),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.read_bytes() == audio
    assert len(calls) == 1
    assert json.loads(receipt.read_bytes())["playback"] == "not_attempted"
    assert "súkromný" not in result.output
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in (output, receipt))


def test_existing_outputs_are_refused_before_any_http(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = mock_probe(monkeypatch, httpx.Response(500))
    output = private_file(workspace / "existing.json", b"preserve")
    source = private_file(workspace / "source.wav", wav())
    result = CliRunner().invoke(
        voice_probe.cli,
        [
            "transcribe",
            *options(workspace),
            "--source",
            str(source),
            "--source-digest",
            content_digest(wav()),
            "--source-id",
            "test",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert output.read_bytes() == b"preserve"
    assert calls == []


def test_private_workspace_refuses_traversal_symlink_fifo_and_checkout_material(
    workspace: Path, external_root: Path
) -> None:
    files = voice_probe.PrivateWorkspace(workspace, (external_root / "checkout",))
    target = private_file(workspace / "target", b"private")
    link = workspace / "link"
    link.symlink_to(target)
    with pytest.raises(OSError, match="symbolic links"):
        files.read(link, 100)
    parent_link = workspace / "linked-dir"
    parent_link.symlink_to(workspace, target_is_directory=True)
    with pytest.raises(NotADirectoryError):
        files.read(parent_link / "target", 100)
    fifo = workspace / "pipe"
    os.mkfifo(fifo, 0o600)
    with pytest.raises(SpeechProbeError, match="regular"):
        files.read(fifo, 100)
    for path in (Path("relative"), workspace / ".." / "outside", external_root / "outside"):
        with pytest.raises(SpeechProbeError):
            files.read(path, 100)
    with pytest.raises(SpeechProbeError, match="checkout"):
        voice_probe.PrivateWorkspace(workspace, (external_root,))
    with pytest.raises(SpeechProbeError, match="checkout"):
        voice_probe.PrivateWorkspace(workspace, (workspace / "nested-checkout",))
    with pytest.raises(SpeechProbeError, match="checkout"):
        voice_probe.PrivateWorkspace(workspace, ())


def test_read_bound_private_modes_and_no_overwrite_even_after_preflight(workspace: Path, external_root: Path) -> None:
    files = voice_probe.PrivateWorkspace(workspace, (external_root / "checkout",))
    target = private_file(workspace / "target", b"abc")
    with pytest.raises(SpeechProbeError, match="byte bound"):
        files.read(target, 2)
    target.chmod(0o644)
    with pytest.raises(SpeechProbeError, match="private"):
        files.read(target, 10)
    output = workspace / "new"
    files.preflight_output(output)
    private_file(output, b"preserved")
    with pytest.raises(FileExistsError):
        files.write_new(output, b"replacement")
    assert output.read_bytes() == b"preserved"
    workspace.chmod(0o755)
    with pytest.raises(SpeechProbeError, match="private"):
        voice_probe.PrivateWorkspace(workspace, (external_root / "checkout",))


def test_invalid_profile_error_does_not_print_private_fields(workspace: Path) -> None:
    args = options(workspace)
    private_file(workspace / "profile.json", b'{"credential":"PRIVATE SECRET NOT PRINTED"}')
    result = CliRunner().invoke(voice_probe.cli, ["profile", *args])
    assert result.exit_code != 0
    assert "PRIVATE SECRET" not in result.output


def test_version_two_schema_and_private_profile_load_without_http(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = mock_probe(monkeypatch, httpx.Response(500))
    args = options(workspace)
    pinned = profile_v2()
    private_file(workspace / "profile.json", pinned.model_dump_json().encode())
    result = CliRunner().invoke(voice_probe.cli, ["profile", *args])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["profile_digest"] == pinned.digest
    schema = CliRunner().invoke(voice_probe.cli, ["schema"])
    assert schema.exit_code == 0
    assert {"SpeechProfile", "SpeechProfileV2"} <= set(json.loads(schema.output)["$defs"])
    assert calls == []


@pytest.mark.parametrize("language", [None, "sk"])
def test_version_two_transcription_cli_requires_language_and_retains_operation_provenance(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, language: str | None
) -> None:
    calls = mock_probe(monkeypatch, httpx.Response(200, json={"text": " State\n"}))
    args = options(workspace)
    pinned = profile_v2()
    private_file(workspace / "profile.json", pinned.model_dump_json().encode())
    content = wav()
    source = private_file(workspace / "source.wav", content)
    output = workspace / "transcript.json"
    command = [
        "transcribe",
        *args,
        "--source",
        str(source),
        "--source-id",
        "explicit",
        "--source-digest",
        content_digest(content),
        "--output",
        str(output),
    ]
    if language is not None:
        command.extend(["--language", language])
    result = CliRunner().invoke(voice_probe.cli, command)
    if language is None:
        assert result.exit_code != 0
        assert calls == []
        assert not output.exists()
    else:
        assert result.exit_code == 0, result.output
        assert len(calls) == 1
        assert str(calls[0].url) == "http://127.0.0.1:8081/v1/audio/transcriptions"
        retained = json.loads(output.read_bytes())
        assert retained["text"] == " State\n"
        assert retained["runtime_revision"] == "d" * 40
        assert retained["profile_digest"] == pinned.digest
        assert retained["native_echo_admission"] is False
