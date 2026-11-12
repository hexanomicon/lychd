"""Closed native Tether operations; command output contains only public receipts."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Callable

    from lychd.system.services.tether.service import NativeTetherService

_MAX_PEER_BYTES = 64 * 1024
_PRIVATE_DECLARATION_MODE = 0o600


def _invoke(operation: Callable[[NativeTetherService], dict[str, object]]) -> None:
    from lychd.system.services.tether.service import NativeTetherService

    try:
        result = json.dumps(operation(NativeTetherService()), sort_keys=True)
    except Exception:  # noqa: BLE001 - native diagnostics must never expose credential input
        message = "Tether operation refused; inspect current native state and admitted inputs."
        raise click.ClickException(message) from None
    click.echo(result)


@click.group(name="tether")
def tether_group() -> None:
    """Prepare, inspect and reconcile explicitly admitted Tether roads."""


@tether_group.command("prepare")
@click.option("--intent", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--dry-run", is_flag=True)
def prepare(intent: Path, *, dry_run: bool) -> None:
    """Admit public intent through native custody without exposing key material."""
    _invoke(lambda service: service.prepare(intent_path=intent, dry_run=dry_run))


@tether_group.command("bind")
@click.option("--dry-run", is_flag=True)
def bind(*, dry_run: bool) -> None:
    """Bind the exact admitted deployment through the native service."""
    _invoke(lambda service: service.bind(dry_run=dry_run))


@tether_group.command("activate")
@click.option("--dry-run", is_flag=True)
def activate(*, dry_run: bool) -> None:
    """Activate and verify admitted networks before publishing consumer routes."""
    _invoke(lambda service: service.activate(dry_run=dry_run))


@tether_group.command("inspect")
def inspect_tether() -> None:
    """Observe current native custody and runtime without mutation."""
    _invoke(lambda service: service.inspect())


@tether_group.command("revoke")
@click.option("--network", required=True)
@click.option("--peer", default=None)
@click.option("--generation", required=True)
@click.option("--dry-run", is_flag=True)
def revoke(network: str, peer: str | None, generation: str, *, dry_run: bool) -> None:
    """Fence one exact current generation; stale requests remain refused."""
    _invoke(
        lambda service: service.revoke(
            network_id=network, peer_id=peer, expected_generation=generation, dry_run=dry_run
        )
    )


@tether_group.command("import-key")
@click.option("--secret", required=True)
@click.option("--file", "key_file", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--dry-run", is_flag=True)
def import_key(secret: str, key_file: Path, *, dry_run: bool) -> None:
    """Import an owner-controlled secret through the native custody boundary."""
    _invoke(lambda service: service.import_key(secret_ref=secret, path=key_file, dry_run=dry_run))


@tether_group.command("enroll")
@click.option("--peer-file", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--dry-run", is_flag=True)
def enroll(peer_file: Path, *, dry_run: bool) -> None:
    """Enroll a public peer; additive admission preserves an unchanged live offered Pod."""
    from lychd.domain.tether.models import OfferedPeer

    try:
        descriptor = os.open(peer_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            metadata = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1
                or metadata.st_mode & 0o022
                or metadata.st_size > _MAX_PEER_BYTES
            ):
                raise ValueError  # noqa: TRY301 - normalize the public file boundary
            data = source.read(_MAX_PEER_BYTES + 1)
        if len(data) > _MAX_PEER_BYTES:
            raise ValueError  # noqa: TRY301 - normalize the public file boundary
        document = json.loads(data, object_pairs_hook=_closed_object)
        peer = OfferedPeer.model_validate_json(json.dumps(document), strict=True)
    except (OSError, ValueError, RecursionError):
        message = "Public peer declaration refused."
        raise click.ClickException(message) from None
    _invoke(lambda service: service.enroll(peer=peer, dry_run=dry_run))


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError
        document[key] = value
    return document


@tether_group.command("runtime-dir", hidden=True)
def runtime_dir() -> None:
    """Recreate only the attested ephemeral runtime directory after reboot."""
    _invoke(lambda service: service.runtime_dir())


@tether_group.command("resume", hidden=True)
def resume() -> None:
    """Resume only generations with prior explicit activation authority."""
    _invoke(lambda service: service.resume())


@tether_group.command("admit")
@click.option("--attachment", required=True)
@click.option("--generation", required=True, type=click.IntRange(min=1))
@click.option("--dry-run", is_flag=True)
def admit(attachment: str, generation: int, *, dry_run: bool) -> None:
    """Independently admit one current imported attachment generation."""
    _invoke(lambda service: service.admit(attachment_id=attachment, generation=generation, dry_run=dry_run))


@tether_group.command("register")
@click.option("--attachment-file", required=True, type=click.Path(path_type=Path, dir_okay=False))
@click.option("--dry-run", is_flag=True)
def register(attachment_file: Path, *, dry_run: bool) -> None:
    """Stage one public imported attachment; import its key and admit it separately."""
    from lychd.domain.tether.models import ImportedAttachment

    try:
        data = _read_private_declaration(attachment_file)
        document = json.loads(data, object_pairs_hook=_closed_object)
        attachment = ImportedAttachment.model_validate_json(json.dumps(document), strict=True)
    except (OSError, ValueError, RecursionError):
        message = "Public attachment declaration refused."
        raise click.ClickException(message) from None
    _invoke(lambda service: service.register_attachment(attachment, dry_run=dry_run))


def _read_private_declaration(path: Path) -> bytes:
    """Read bounded owner-only public input without following any path symlink."""
    path = path.absolute()
    if ".." in path.parts:
        raise ValueError
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in path.parent.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            os.close(parent)
            parent = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as source:
            metadata = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != _PRIVATE_DECLARATION_MODE
                or metadata.st_size > _MAX_PEER_BYTES
            ):
                raise ValueError
            data = source.read(_MAX_PEER_BYTES + 1)
    finally:
        os.close(parent)
    if len(data) > _MAX_PEER_BYTES:
        raise ValueError
    return data
