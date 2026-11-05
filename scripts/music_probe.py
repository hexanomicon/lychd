"""Operate finite music/Comfy engineering probes, without native application admission."""

from __future__ import annotations

import asyncio
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import click
import httpx2

from lychd.compositions.riffmaw.offline.models import RenderRecipe
from lychd.compositions.riffmaw.offline.recipe import TrackControls, change_track_controls, demo_recipe

if TYPE_CHECKING:
    from uuid import UUID

CHECKOUT_ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 1024 * 1024


def external_path(path: Path) -> Path:
    """Fence explicit operator probe paths from checkout and symlink traversal."""
    if not path.is_absolute():
        msg = "Probe paths must be absolute."
        raise click.ClickException(msg)
    if any(item.is_symlink() for item in (path, *path.parents)):
        msg = "Probe paths must not traverse symlinks."
        raise click.ClickException(msg)
    resolved = path.resolve()
    if resolved.is_relative_to(CHECKOUT_ROOT):
        msg = "Private probe inputs and outputs must be outside the checkout."
        raise click.ClickException(msg)
    return resolved


def read_external_file(path: Path, limit: int) -> bytes:
    """Read bounded regular bytes without blocking on a replaced FIFO."""
    checked = external_path(path)
    descriptor = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            msg = "Probe input must be a regular file."
            raise click.ClickException(msg)
        data = stream.read(limit + 1)
    if len(data) > limit or len(data) != info.st_size:
        msg = "Probe input exceeds the byte limit or changed during reading."
        raise click.ClickException(msg)
    return data


def read_json_file(path: Path) -> bytes:
    """Read a bounded regular external JSON file."""
    return read_external_file(path, MAX_JSON_BYTES)


def write_new_text(path: Path, data: str) -> Path:
    """Publish private recipe or preview bytes without overwriting earlier work."""
    checked = external_path(path)
    checked.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=checked.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(temporary, checked)
            directory = os.open(checked.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
    return checked


@click.group()
def cli() -> None:
    """Inspect, edit and execute bounded technical probes; outputs remain candidates."""


@cli.command()
@click.argument("kind", type=click.Choice(("recipe", "comfy-profile", "comfy-request")), default="recipe")
def schema(kind: str) -> None:
    """Print the actual worker input schema for agent callers."""
    if kind == "recipe":
        model = RenderRecipe
    else:
        from lychd.domain.comfy_probe import ComfyProfile, ComfyRequest

        model = ComfyProfile if kind == "comfy-profile" else ComfyRequest
    click.echo(json.dumps(model.model_json_schema(), sort_keys=True, indent=2))


@cli.command()
@click.option("--output", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--bars", default=4, type=click.IntRange(1, 16), show_default=True)
@click.option("--tempo", default=145.0, type=click.FloatRange(30.0, 300.0), show_default=True)
def demo(output: Path, bars: int, tempo: float) -> None:
    """Write an original kick/bass/lead recipe, without running audio or a model."""
    recipe = demo_recipe(bars=bars, tempo_bpm=tempo)
    path = write_new_text(output, recipe.model_dump_json(indent=2))
    click.echo(json.dumps({"recipe_path": str(path), "recipe_digest": recipe.content_digest()}))


@cli.command()
@click.argument("recipe_path", type=click.Path(path_type=Path, dir_okay=False))
def validate(recipe_path: Path) -> None:
    """Validate an exact recipe and print its content identity."""
    recipe = RenderRecipe.model_validate_json(read_json_file(recipe_path))
    click.echo(json.dumps({"recipe_digest": recipe.content_digest(), "tracks": len(recipe.tracks)}))


@cli.command()
@click.argument("recipe_path", type=click.Path(path_type=Path, dir_okay=False))
@click.option("--expected-digest", required=True)
@click.option("--track", required=True)
@click.option("--gain", type=click.FloatRange(-60.0, 6.0))
@click.option("--pan", type=click.FloatRange(-1.0, 1.0))
@click.option("--cutoff", type=click.FloatRange(40.0, 20000.0))
@click.option("--output", required=True, type=click.Path(path_type=Path, dir_okay=False))
def edit(
    recipe_path: Path,
    expected_digest: str,
    track: str,
    gain: float | None,
    pan: float | None,
    cutoff: float | None,
    output: Path,
) -> None:
    """Write a guarded control variant, preserving the original recipe."""
    recipe = RenderRecipe.model_validate_json(read_json_file(recipe_path))
    changed = change_track_controls(
        recipe,
        expected_digest=expected_digest,
        track_id=track,
        controls=TrackControls(gain_db=gain, pan=pan, cutoff_hz=cutoff),
    )
    path = write_new_text(output, changed.model_dump_json(indent=2))
    click.echo(
        json.dumps(
            {
                "recipe_path": str(path),
                "parent_digest": recipe.content_digest(),
                "recipe_digest": changed.content_digest(),
            }
        )
    )


@cli.command()
@click.argument("recipe_path", type=click.Path(path_type=Path, dir_okay=False))
@click.option("--workspace", required=True, type=click.Path(path_type=Path, file_okay=False))
@click.option("--timeout", default=30.0, type=click.FloatRange(0.1, 30.0), show_default=True)
def render(recipe_path: Path, workspace: Path, timeout: float) -> None:
    """Run one isolated offline render and return its verified technical receipt."""
    from lychd.system.services.music_probe import render_probe

    root = external_path(workspace)
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True, mode=0o700)
    recipe = RenderRecipe.model_validate_json(read_json_file(recipe_path))
    receipt = render_probe(recipe, assets_dir=assets, output_dir=root / "renders", timeout_seconds=timeout)
    click.echo(receipt.model_dump_json())


@cli.command()
@click.argument("recipe_path", type=click.Path(path_type=Path, dir_okay=False))
@click.option("--workspace", required=True, type=click.Path(path_type=Path, file_okay=False))
@click.option("--output", required=True, type=click.Path(path_type=Path, dir_okay=False))
def audition(recipe_path: Path, workspace: Path, output: Path) -> None:
    """Render/verify a recipe and write its exact local timeline and audio preview."""
    from lychd.compositions.riffmaw.offline.audition import MAX_EMBEDDED_MEDIA_BYTES, audition_html
    from lychd.system.services.music_probe import render_probe

    root = external_path(workspace)
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True, mode=0o700)
    recipe = RenderRecipe.model_validate_json(read_json_file(recipe_path))
    receipt = render_probe(recipe, assets_dir=assets, output_dir=root / "renders")
    if sum(item.size_bytes for item in receipt.outputs) > MAX_EMBEDDED_MEDIA_BYTES:
        msg = "Combined media exceeds the audition byte limit."
        raise click.ClickException(msg)
    folder = root / "renders" / receipt.cache_key
    media: dict[str, bytes] = {}
    for item in receipt.outputs:
        media[item.name] = read_external_file(folder / item.name, item.size_bytes)
    path = write_new_text(output, audition_html(recipe, receipt, media))
    click.echo(json.dumps({"audition_path": str(path), "recipe_digest": recipe.content_digest()}))


@cli.group()
def comfy() -> None:
    """Use one explicitly reviewed local Comfy profile; never retry an unknown effect."""


@comfy.command()
@click.option("--profile", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--request", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--workspace", required=True, type=click.Path(path_type=Path, file_okay=False))
def prepare(profile: Path, request: Path, workspace: Path) -> None:
    """Seal one external-engine probe before any submission."""
    from lychd.domain.comfy_probe import ComfyProfile, ComfyRequest
    from lychd.system.services.comfy_probe import ComfyProbe

    selected = ComfyProfile.model_validate_json(read_json_file(profile))
    inputs = ComfyRequest.model_validate_json(read_json_file(request))
    probe = ComfyProbe(selected, external_path(workspace), checkout_roots=(CHECKOUT_ROOT,))
    click.echo(probe.prepare(inputs).model_dump_json())


@comfy.command()
@click.argument("operation", type=click.Choice(("submit", "reconcile", "fetch", "repair")))
@click.argument("occurrence", type=click.UUID)
@click.option("--profile", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--workspace", required=True, type=click.Path(path_type=Path, file_okay=False))
def attempt(
    operation: Literal["submit", "reconcile", "fetch", "repair"], occurrence: UUID, profile: Path, workspace: Path
) -> None:
    """Advance or inspect the exact existing occurrence, with no implicit replay."""
    from lychd.domain.comfy_probe import ComfyProfile
    from lychd.system.services.comfy_probe import ComfyProbe

    selected = ComfyProfile.model_validate_json(read_json_file(profile))
    probe = ComfyProbe(selected, external_path(workspace), checkout_roots=(CHECKOUT_ROOT,))
    if operation == "repair":
        click.echo(probe.repair_materialization(occurrence).model_dump_json())
        return
    current = probe.load(occurrence)
    operation_call = {"submit": probe.submit, "reconcile": probe.reconcile, "fetch": probe.fetch_outputs}[operation]
    click.echo(asyncio.run(operation_call(current)).model_dump_json())


def main() -> None:
    """Return machine-readable output and concise failures, without host startup."""
    try:
        cli()
    except (OSError, ValueError, RuntimeError, httpx2.HTTPError) as exc:
        error = click.ClickException(str(exc))
        error.show()
        raise SystemExit(error.exit_code) from exc


if __name__ == "__main__":
    main()
