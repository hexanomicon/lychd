"""Local cut invariants without an FFmpeg or font dependency in the Core test image."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest
from scripts import short_video_cut as cut

pytest_plugins = ["tests.music_probe_support"]


def picture(frames: int = 60) -> cut.Stream:
    return {
        "codec_name": "mpeg4",
        "start_pts": 0,
        "time_base": "1/30",
        "duration_ts": frames,
        "avg_frame_rate": "30/1",
        "nb_read_frames": str(frames),
    }


@pytest.mark.parametrize(
    ("start", "duration", "caption"), [(-1, 1, "ok"), (0, 0, "ok"), (0, 181, "ok"), (0, 1, "a\nb")]
)
def test_invalid_cut_refused_before_input_open(start: int, duration: int, caption: str, probe_path: Path) -> None:
    missing = probe_path / "absent"
    with pytest.raises(ValueError, match=r"whole seconds|caption"):
        cut.render(missing, start, duration, caption, missing, None, probe_path / "cut.mp4")


def test_checkout_relative_and_symlink_paths_refused(probe_path: Path) -> None:
    link = probe_path / "alias"
    link.symlink_to(probe_path, target_is_directory=True)
    for path in (cut.CHECKOUT / "private.mp4", Path("relative.mp4"), link / "file"):
        with pytest.raises(ValueError, match=r"absolute|outside"):
            cut.external(path)


def test_output_needs_exact_picture_and_correct_audio_duration() -> None:
    voice: cut.Stream = {"codec_name": "aac", "start_pts": 0, "duration_ts": 96000, "time_base": "1/48000"}
    cut.verify([picture(), voice], 2, voiced=True)
    with pytest.raises(ValueError, match="layout"):
        cut.verify([picture(), voice], 2, voiced=False)
    with pytest.raises(ValueError, match="picture"):
        cut.verify([picture(59), voice], 2, voiced=True)
    voice["duration_ts"] = 48000
    with pytest.raises(ValueError, match="narration"):
        cut.verify([picture(), voice], 2, voiced=True)


def test_unconfirmed_directory_sync_preserves_published_bytes(
    probe_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = probe_path / "staged.mp4"
    staged.write_bytes(b"verified bytes")
    destination = probe_path / "accepted.mp4"
    real_sync = os.fsync

    def fail_directory_sync(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            msg = "directory sync failed"
            raise OSError(msg)
        real_sync(fd)

    monkeypatch.setattr(os, "fsync", fail_directory_sync)
    with pytest.raises(OSError, match="directory sync failed"):
        cut.publish_candidate(staged, destination)
    assert destination.read_bytes() == b"verified bytes"
    with pytest.raises(FileExistsError):
        cut.publish_candidate(staged, destination)


@pytest.mark.parametrize("outcome", ["success", "too-short-source", "encoder-failure", "short-output", "racing-writer"])
def test_candidate_publication(probe_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    video = probe_path / "picture.mp4"
    video.write_bytes(b"operator input")
    font = probe_path / "font with quotes'[].ttf"
    font.write_bytes(bytes.fromhex("00010000") + b"synthetic test font")
    caption = "  50%: %{pts} [x], 'a'  "
    destination = probe_path / "cut.mp4"

    def probe(_path: Path, _cwd: Path, *, output: bool = False) -> list[cut.Stream]:
        if output and outcome == "racing-writer":
            destination.write_bytes(b"another candidate")
        short = (output and outcome == "short-output") or (not output and outcome == "too-short-source")
        return [picture(59 if short else 60)]

    def encode(tool: str, arguments: list[str], cwd: Path) -> str:
        assert tool == "ffmpeg"
        assert outcome != "too-short-source"
        assert arguments[arguments.index("-map") + 1] == "0:V:0"
        assert "-an" in arguments
        assert arguments[arguments.index("-protocol_whitelist") + 1] == "file"
        filters = arguments[arguments.index("-vf") + 1]
        assert "expansion=none" in filters
        assert caption not in filters
        assert str(font) not in filters
        assert (cwd / "caption.txt").read_text(encoding="utf-8") == caption
        assert (cwd / "font.ttf").read_bytes() == font.read_bytes()
        Path(arguments[-1]).write_bytes(b"candidate")
        if outcome == "encoder-failure":
            raise subprocess.CalledProcessError(1, tool)
        return ""

    monkeypatch.setattr(cut, "streams", probe)
    monkeypatch.setattr(cut, "run", encode)
    if outcome == "success":
        result = cut.render(video, 0, 2, caption, font, None, destination)
        assert result["seconds"] == 2
        assert destination.read_bytes() == b"candidate"
    elif outcome == "racing-writer":
        with pytest.raises(FileExistsError):
            cut.render(video, 0, 2, caption, font, None, destination)
        assert destination.read_bytes() == b"another candidate"
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError), match=r"picture|non-zero"):
            cut.render(video, 0, 2, caption, font, None, destination)
        assert not destination.exists()
    assert not tuple(probe_path.glob(".short-cut-*"))
