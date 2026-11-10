"""Closed native `run tether` adapters; no extension-owned callback dispatch."""

from __future__ import annotations

from functools import wraps
from ipaddress import IPv4Interface
from typing import TYPE_CHECKING, Any
from uuid import UUID

import click

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel


def _request_options(function: Callable[..., Any]) -> Callable[..., Any]:
    for decorator in reversed(
        (
            click.option("--installation-id", type=click.UUID, required=True),
            click.option("--operation-id", type=click.UUID, required=True),
            click.option("--expected-generation", type=click.IntRange(min=0), required=True),
            click.option("--envelope-digest", required=True),
        )
    ):
        function = decorator(function)
    return function


def _native(function: Callable[..., BaseModel]) -> Callable[..., None]:
    @wraps(function)
    def wrapped(*args: object, **kwargs: object) -> None:
        from lychd.system.services.tether.models import TetherError

        try:
            result = function(*args, **kwargs)
            click.echo(result.model_dump_json(indent=2))
        except TetherError as exc:
            raise click.ClickException(str(exc)) from None
        except Exception:  # noqa: BLE001 - never expose settings/secret validation diagnostics
            msg = "Native Tether request refused; inspect public intent and native receipts"
            raise click.ClickException(msg) from None

    return wrapped


def _show_declared_plan(ctx: click.Context, _parameter: click.Parameter, value: bool) -> None:  # noqa: FBT001 - Click owns the positional eager-option callback signature
    if not value or ctx.resilient_parsing:
        return
    try:
        from lychd.system.services.tether.composition import declared_tether_plan

        public_plan = declared_tether_plan().model_dump_json(indent=2)
    except Exception:  # noqa: BLE001 - declared configuration validation may include sensitive input
        msg = "Declared Tether plan is unavailable; check the selected builtin and public Rune"
        raise click.ClickException(msg) from None
    click.echo(public_plan)
    ctx.exit()


def _show_prepared_inspection(ctx: click.Context, _parameter: click.Parameter, value: bool) -> None:  # noqa: FBT001 - Click owns its eager-option callback signature
    if not value or ctx.resilient_parsing:
        return
    try:
        from lychd.system.services.tether.composition import prepared_tether_inspection

        metadata = prepared_tether_inspection().model_dump_json(indent=2)
    except Exception:  # noqa: BLE001 - no private key or validation payload may escape metadata inspection
        msg = "Prepared Tether metadata is unavailable; check native preparation and creation receipts"
        raise click.ClickException(msg) from None
    click.echo(metadata)
    ctx.exit()


@click.group(name="run")
def run() -> None:
    """Execute closed native host operations."""


@run.group(name="tether")
def tether() -> None:
    """Prepare, enroll, inspect or revoke the fixed private road."""


@tether.command(name="prepare")
@_request_options
@click.option(
    "--expected-preparation-digest", help="Replace only the cold transport image from this exact prepared selection."
)
@click.option("--dry-run", is_flag=True)
@_native
def prepare(
    *,
    installation_id: UUID,
    operation_id: UUID,
    expected_generation: int,
    envelope_digest: str,
    dry_run: bool,
    expected_preparation_digest: str | None,
) -> BaseModel:
    """Prepare server secrets initially, or select a cold image-only replacement."""
    from lychd.system.services.tether.composition import build_tether_operations
    from lychd.system.services.tether.models import PrepareImageRequest, PrepareRequest

    if expected_preparation_digest is not None:
        image_request = PrepareImageRequest(
            installation_id=installation_id,
            operation_id=operation_id,
            expected_generation=expected_generation,
            envelope_digest=envelope_digest,
            intent_digest=envelope_digest,
            expected_preparation_digest=expected_preparation_digest,
        )
        return build_tether_operations().prepare_image(image_request, dry_run=dry_run)
    request = PrepareRequest(
        installation_id=installation_id,
        operation_id=operation_id,
        expected_generation=expected_generation,
        envelope_digest=envelope_digest,
        intent_digest=envelope_digest,
    )
    return build_tether_operations().prepare(request, dry_run=dry_run)


@tether.command(name="enroll")
@_request_options
@click.option("--peer-id", required=True)
@click.option("--wireguard-public-key", required=True)
@click.option("--peer-address", required=True)
@click.option("--ssh-public-key", required=True)
@click.option("--persistent-keepalive", type=click.IntRange(min=0, max=120), default=25, show_default=True)
@click.option("--dry-run", is_flag=True)
@_native
def enroll(
    *,
    installation_id: UUID,
    operation_id: UUID,
    expected_generation: int,
    envelope_digest: str,
    peer_id: str,
    wireguard_public_key: str,
    peer_address: str,
    ssh_public_key: str,
    persistent_keepalive: int,
    dry_run: bool,
) -> BaseModel:
    """Enroll only client public keys into a proven-cold next generation."""
    from lychd.domain.tether.models import TetherPeerIntent
    from lychd.system.services.tether.composition import build_tether_operations
    from lychd.system.services.tether.models import EnrollRequest, digest

    peer = TetherPeerIntent(
        installation_id=installation_id,
        operation_id=operation_id,
        generation=expected_generation + 1,
        peer_id=peer_id,
        wireguard_public_key=wireguard_public_key,
        address=IPv4Interface(peer_address),
        ssh_authorized_public_key=ssh_public_key,
        persistent_keepalive=persistent_keepalive,
    )
    request = EnrollRequest(
        installation_id=installation_id,
        operation_id=operation_id,
        expected_generation=expected_generation,
        envelope_digest=envelope_digest,
        intent_digest=digest(peer),
        peer=peer,
    )
    return build_tether_operations().enroll(request, dry_run=dry_run)


@tether.command(name="inspect")
@click.option(
    "--prepared",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_show_prepared_inspection,
    help="Print current selected-preparation metadata before binding or peer enrollment.",
)
@click.option(
    "--declared",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_show_declared_plan,
    help="Print the public declared plan and digest before preparation or bind.",
)
@_request_options
@click.option("--intent-digest", required=True)
@_native
def inspect(
    *, installation_id: UUID, operation_id: UUID, expected_generation: int, envelope_digest: str, intent_digest: str
) -> BaseModel:
    """Observe desired generation, fences and bounded whole-road state."""
    from lychd.system.services.tether.composition import build_tether_operations
    from lychd.system.services.tether.models import InspectRequest

    return build_tether_operations(for_closure=True).inspect(
        InspectRequest(
            installation_id=installation_id,
            operation_id=operation_id,
            expected_generation=expected_generation,
            envelope_digest=envelope_digest,
            intent_digest=intent_digest,
        )
    )


@tether.command(name="revoke")
@_request_options
@click.option("--intent-digest", required=True)
@click.option("--dry-run", is_flag=True)
@_native
def revoke(
    *,
    installation_id: UUID,
    operation_id: UUID,
    expected_generation: int,
    envelope_digest: str,
    intent_digest: str,
    dry_run: bool,
) -> BaseModel:
    """Durably fence the exact public generation and close its whole road."""
    from lychd.system.services.tether.composition import build_tether_operations
    from lychd.system.services.tether.models import RevokeRequest

    return build_tether_operations(for_closure=True).revoke(
        RevokeRequest(
            installation_id=installation_id,
            operation_id=operation_id,
            expected_generation=expected_generation,
            envelope_digest=envelope_digest,
            intent_digest=intent_digest,
        ),
        dry_run=dry_run,
    )
