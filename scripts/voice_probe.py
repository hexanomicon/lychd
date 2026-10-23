"""Explicit private local speech qualification; no microphone or playback effects."""

from __future__ import annotations

import asyncio
import json
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import click
from pydantic import ValidationError

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.speech_probe import (
    MAX_INPUT_BYTES,
    MAX_PROFILE_BYTES,
    MAX_TEXT_CHARS,
    STOCK_VOICES,
    LocalSpeechProfile,
    SpeechProbeError,
    StockVoice,
    load_speech_profile,
    speech_profile_schema,
)
from lychd.system.services.speech_probe import SpeechProbe

CHECKOUT_ROOT = Path(__file__).resolve().parents[1]
_MAX_SOURCE_ID_LENGTH = 128


class PrivateWorkspace:
    """Explicit external private files, using no-follow directory-relative opens.

    The caller declares all additional checkout roots. This filesystem fence is
    an engineering precaution, never a process or LychD containment receipt.
    """

    def __init__(self, root: Path, checkout_roots: tuple[Path, ...]) -> None:
        """Bind an existing private workspace outside the declared checkouts."""
        self.root = self._absolute(root)
        roots = (CHECKOUT_ROOT, *(self._absolute(item).resolve() for item in checkout_roots))
        if not checkout_roots or any(
            self.root.is_relative_to(item) or item.is_relative_to(self.root) for item in roots
        ):
            msg = "Declare every checkout root and use a private workspace with no overlapping checkout trees."
            raise SpeechProbeError(msg)
        descriptor = self._directory(self.root)
        os.close(descriptor)

    @staticmethod
    def _absolute(path: Path) -> Path:
        if not path.is_absolute() or ".." in path.parts:
            msg = "Probe paths must be absolute without parent traversal."
            raise SpeechProbeError(msg)
        return path

    def _directory(self, path: Path) -> int:
        descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in path.parts[1:]:
                next_descriptor = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = next_descriptor
            info = os.fstat(descriptor)
        except BaseException:
            os.close(descriptor)
            raise
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            os.close(descriptor)
            msg = "The workspace and material directories must be private and owned by this user."
            raise SpeechProbeError(msg)
        return descriptor

    def _parent(self, path: Path) -> tuple[int, str]:
        path = self._absolute(path)
        if path == self.root or not path.is_relative_to(self.root):
            msg = "All probe material must remain inside the explicit workspace."
            raise SpeechProbeError(msg)
        return self._directory(path.parent), path.name

    def read(self, path: Path, limit: int) -> bytes:
        directory, name = self._parent(path)
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    msg = "Probe input must be a private owned regular file."
                    raise SpeechProbeError(msg)
                if info.st_size > limit:
                    msg = "Probe input exceeds its byte bound."
                    raise SpeechProbeError(msg)
                content = stream.read(limit + 1)
                after = os.fstat(stream.fileno())
                if len(content) != info.st_size or len(content) > limit or after.st_mtime_ns != info.st_mtime_ns:
                    msg = "Probe input changed or exceeds its byte bound."
                    raise SpeechProbeError(msg)
                return content
        finally:
            os.close(directory)

    def preflight_output(self, path: Path) -> None:
        directory, name = self._parent(path)
        try:
            try:
                os.stat(name, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                return
            msg = "Probe output already exists; overwriting is refused."
            raise SpeechProbeError(msg)
        finally:
            os.close(directory)

    def write_new(self, path: Path, content: bytes) -> None:
        directory, name = self._parent(path)
        try:
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(directory)
        finally:
            os.close(directory)


def _files(function: Callable[..., Any]) -> Callable[..., Any]:
    function = click.option("--profile", required=True, type=click.Path(path_type=Path, dir_okay=False))(function)
    function = click.option("--workspace", required=True, type=click.Path(path_type=Path, file_okay=False))(function)
    return click.option(
        "--checkout-root", required=True, multiple=True, type=click.Path(path_type=Path, file_okay=False)
    )(function)


def _inputs(
    workspace: Path, checkout_root: tuple[Path, ...], profile: Path
) -> tuple[PrivateWorkspace, LocalSpeechProfile]:
    files = PrivateWorkspace(workspace, checkout_root)
    return files, load_speech_profile(files.read(profile, MAX_PROFILE_BYTES))


def _safe(function: Callable[..., Any]) -> Callable[..., Any]:
    from functools import wraps

    @wraps(function)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except (SpeechProbeError, ValidationError, OSError, UnicodeError, ValueError):
            msg = "Speech probe refused or failed; inspect private inputs and profile. Server work may be unknown; no retry or playback."
            raise click.ClickException(msg) from None

    return guarded


@click.group()
def cli() -> None:
    """Qualify explicit local speech files without native Echo or Animator admission."""


@cli.command()
def schema() -> None:
    """Print the pinned profile schema; no endpoint or material is accessed."""
    click.echo(json.dumps(speech_profile_schema(), indent=2, sort_keys=True))


@cli.command("profile")
@_files
@_safe
def validate_profile(workspace: Path, checkout_root: tuple[Path, ...], profile: Path) -> None:
    """Validate an existing explicit profile without contacting the server."""
    _, pinned = _inputs(workspace, checkout_root, profile)
    click.echo(json.dumps({"profile_digest": pinned.digest, "native_echo_admission": False}))


@cli.command()
@_files
@click.option("--source", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--source-digest", required=True)
@click.option("--source-id", required=True)
@click.option("--language")
@click.option("--output", required=True, type=click.Path(path_type=Path, dir_okay=False))
@_safe
def transcribe(
    workspace: Path,
    checkout_root: tuple[Path, ...],
    profile: Path,
    source: Path,
    source_digest: str,
    source_id: str,
    language: str | None,
    output: Path,
) -> None:
    """Send one canonical WAV and write its attributed transcript privately."""
    files, pinned = _inputs(workspace, checkout_root, profile)
    files.preflight_output(output)
    content = files.read(source, MAX_INPUT_BYTES)
    if not 1 <= len(source_id) <= _MAX_SOURCE_ID_LENGTH:
        msg = "Source identity must be bounded."
        raise SpeechProbeError(msg)
    reference = ArtifactRef(
        artifact_id=source_id, digest=source_digest, media_type="audio/wav", size=len(content), classification="private"
    )
    result = asyncio.run(SpeechProbe(pinned).transcribe(reference, content, language=language))
    files.write_new(output, result.model_dump_json(indent=2).encode())
    click.echo(
        json.dumps({"profile_digest": pinned.digest, "transcript_written": True, "native_echo_admission": False})
    )


@cli.command()
@_files
@click.option("--text", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--language", required=True)
@click.option("--voice", required=True, type=click.Choice(STOCK_VOICES))
@click.option("--output", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--receipt", required=True, type=click.Path(path_type=Path, dir_okay=False))
@_safe
def synthesize(
    workspace: Path,
    checkout_root: tuple[Path, ...],
    profile: Path,
    text: Path,
    language: str,
    voice: str,
    output: Path,
    receipt: Path,
) -> None:
    """Generate one stock-voice WAV; retain bytes and facts, with no playback."""
    files, pinned = _inputs(workspace, checkout_root, profile)
    if output == receipt:
        msg = "Audio and receipt outputs must be distinct."
        raise SpeechProbeError(msg)
    files.preflight_output(output)
    files.preflight_output(receipt)
    words = files.read(text, 4 * MAX_TEXT_CHARS).decode("utf-8")
    result, audio = asyncio.run(
        SpeechProbe(pinned).synthesize(words, language=language, voice=cast("StockVoice", voice))
    )
    files.write_new(output, audio)
    files.write_new(receipt, result.model_dump_json(indent=2).encode())
    click.echo(
        json.dumps(
            {
                "profile_digest": pinned.digest,
                "generated": True,
                "playback": "not_attempted",
                "native_echo_admission": False,
            }
        )
    )


if __name__ == "__main__":
    cli()
