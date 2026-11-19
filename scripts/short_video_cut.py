"""Render one local Atelier cut with a burned-in caption and optional replacement narration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import TypedDict, cast

CHECKOUT = Path(__file__).resolve().parents[1]
FPS = 30
AUDIO_RATE = 48000
MAX_SECONDS = 180
MAX_CAPTION_CHARS = 100
LOCAL_MOV = ("-protocol_whitelist", "file", "-f", "mov", "-enable_drefs", "0")


class Stream(TypedDict, total=False):
    codec_type: str
    codec_name: str
    start_pts: int
    time_base: str
    duration_ts: int
    nb_read_frames: str
    avg_frame_rate: str


def external(path: Path) -> Path:
    """Accept only explicit paths without symlinks outside the running checkout."""
    if not path.is_absolute() or ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        msg = "Use an absolute local path without symlinks or parent traversal."
        raise ValueError(msg)
    if path.is_relative_to(CHECKOUT):
        msg = "Private media and output must be outside the checkout."
        raise ValueError(msg)
    return path


def asset(path: Path) -> Path:
    if not external(path).is_file():
        msg = f"Expected a regular local file: {path}"
        raise ValueError(msg)
    return path


def run(tool: str, arguments: list[str], cwd: Path) -> str:
    binary = shutil.which(tool)
    if binary is None:
        msg = f"Missing render dependency: {tool}"
        raise ValueError(msg)
    return subprocess.run(  # noqa: S603 - fixed binaries and argv; operator material never becomes a command.
        [binary, "-v", "error", *arguments],
        cwd=cwd,
        env={"FONTCONFIG_FILE": str(cwd / "fontconfig.xml")},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        check=True,
        timeout=600,
        text=True,
    ).stdout


def streams(path: Path, cwd: Path, *, output: bool = False) -> list[Stream]:
    selection = ["-count_frames"] if output else ["-select_streams", "V:0"]
    data = run(
        "ffprobe",
        [
            *LOCAL_MOV,
            *selection,
            "-show_entries",
            "stream=codec_type,codec_name,start_pts,time_base,duration_ts,nb_read_frames,avg_frame_rate",
            "-of",
            "json",
            "-i",
            str(path),
        ],
        cwd,
    )
    return cast("list[Stream]", json.loads(data)["streams"])


def seconds(stream: Stream) -> Fraction:
    if stream.get("start_pts") != 0 or "duration_ts" not in stream or "time_base" not in stream:
        msg = "A measured, zero-origin stream timeline is required."
        raise ValueError(msg)
    return stream["duration_ts"] * Fraction(stream["time_base"])


def verify(rendered: list[Stream], duration: int, *, voiced: bool) -> None:
    expected_codecs = ["mpeg4", "aac"] if voiced else ["mpeg4"]
    if [stream.get("codec_name") for stream in rendered] != expected_codecs:
        msg = "Unexpected candidate stream layout or codec."
        raise ValueError(msg)
    picture = rendered[0]
    if (
        seconds(picture) != duration
        or picture.get("nb_read_frames") != str(duration * FPS)
        or picture.get("avg_frame_rate") != f"{FPS}/1"
    ):
        msg = "Candidate picture failed its duration, frame count or frame rate check."
        raise ValueError(msg)
    if voiced and abs(seconds(rendered[1]) - duration) > Fraction(1, AUDIO_RATE):
        msg = "Candidate narration does not cover the cut."
        raise ValueError(msg)


def caption_filter(stage: Path, caption: str, font: Path) -> tuple[str, str]:
    selected_font = stage / "font.ttf"
    shutil.copyfile(font, selected_font)
    # A corrupt font must fail instead of selecting a different system face.
    (stage / "fontconfig.xml").write_text("<fontconfig></fontconfig>", encoding="ascii")
    with selected_font.open("rb") as file:
        if file.read(4) not in (b"\x00\x01\x00\x00", b"true"):
            msg = "Select a TrueType font file."
            raise ValueError(msg)
        file.seek(0)
        font_digest = hashlib.file_digest(file, "sha256").hexdigest()
    # Both filenames in the filter are fixed. expansion=none makes percent escapes literal.
    (stage / "caption.txt").write_text(caption, encoding="utf-8")
    filters = (
        f"fps={FPS},drawtext=fontfile=font.ttf:textfile=caption.txt:expansion=none:"
        f"fontsize='max(1,min(h/18,w*0.78/{len(caption)}))':fontcolor=white:"
        "box=1:boxcolor=black:boxborderw=2:x=(w-tw)/2:y=h*0.86-th"
    )
    return filters, font_digest


def publish_candidate(candidate: Path, output: Path) -> str:
    """Acknowledge only after both the verified bytes and their new name are durable."""
    candidate.chmod(0o600)
    with candidate.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
        os.fsync(file.fileno())
    os.link(candidate, output)
    directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return digest


def render(
    video: Path, start: int, duration: int, caption: str, font: Path, voice: Path | None, output: Path
) -> dict[str, str | int]:
    if start < 0 or not 1 <= duration <= MAX_SECONDS:
        msg = f"Start must be nonnegative and duration must be 1 to {MAX_SECONDS} whole seconds."
        raise ValueError(msg)
    if not caption.strip() or not caption.isprintable() or len(caption) > MAX_CAPTION_CHARS:
        msg = f"Use one printable caption of 1 to {MAX_CAPTION_CHARS} characters."
        raise ValueError(msg)
    asset(video)
    asset(font)
    if voice is not None:
        asset(voice)
    external(output)
    if output.suffix.lower() != ".mp4" or not output.parent.is_dir():
        msg = "Choose a new .mp4 in an existing private directory."
        raise ValueError(msg)
    if output.exists():
        msg = f"Output already exists: {output}"
        raise FileExistsError(msg)
    with tempfile.TemporaryDirectory(prefix=".short-cut-", dir=output.parent) as temporary:
        stage = Path(temporary)
        source = streams(video, stage)
        if len(source) != 1 or seconds(source[0]) < start + duration:
            msg = "Source picture does not cover the requested cut."
            raise ValueError(msg)
        filters, font_digest = caption_filter(stage, caption, font)
        inputs = [*LOCAL_MOV, "-ss", str(start), "-i", str(video)]
        tracks = ["-map", "0:V:0"]
        if voice is not None:
            inputs.extend(["-protocol_whitelist", "file", "-f", "wav", "-i", str(voice)])
            tracks.extend(["-map", "1:a:0", "-af", "apad", "-c:a", "aac", "-ac", "2", "-ar", str(AUDIO_RATE)])
        else:
            tracks.append("-an")
        candidate = stage / "cut.mp4"
        run(
            "ffmpeg",
            [
                "-nostdin",
                "-n",
                "-xerror",
                *inputs,
                *tracks,
                "-t",
                str(duration),
                "-map_metadata",
                "-1",
                "-map_chapters",
                "-1",
                "-vf",
                filters,
                "-c:v",
                "mpeg4",
                "-q:v",
                "3",
                "-pix_fmt",
                "yuv420p",
                "-f",
                "mp4",
                str(candidate),
            ],
            stage,
        )
        verify(streams(candidate, stage, output=True), duration, voiced=voice is not None)
        digest = publish_candidate(candidate, output)
    return {"output": str(output), "sha256": digest, "font_sha256": font_digest, "seconds": duration, "fps": FPS}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--video", required=True, type=Path, help="Local zero-origin MP4 picture. Source sound is discarded."
    )
    parser.add_argument("--start", default=0, type=int, help="Start offset in whole seconds.")
    parser.add_argument("--duration", required=True, type=int, help="Cut length in whole seconds, 1 through 180.")
    parser.add_argument("--caption", required=True, help="One line of plain text shown throughout the cut.")
    parser.add_argument("--font", required=True, type=Path, help="Pinned local TrueType font for the caption.")
    parser.add_argument("--voice", type=Path, help="Optional WAV from time zero, trimmed or padded with silence.")
    parser.add_argument("--output", required=True, type=Path, help="New MP4 in an existing private directory.")
    args = parser.parse_args()
    try:
        result = render(args.video, args.start, args.duration, args.caption, args.font, args.voice, args.output)
    except subprocess.CalledProcessError as exc:
        parser.exit(1, f"Local media command failed with exit code {exc.returncode}.\n")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Short cut failed: {exc}\n")
    sys.stdout.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
