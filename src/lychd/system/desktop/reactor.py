"""Provision and run the resident Animator owner for a containerized desktop Vessel."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import secrets
import sys
from contextlib import nullcontext, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import click
import tomlkit

from lychd.config.runes.registry import load_rune_registry
from lychd.config.settings.root import Settings, get_settings
from lychd.domain.animation.services.declarations import compile_animator_declarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.orchestration.actuator import capability_config_generation
from lychd.domain.orchestration.policies import resolve_switch_policy
from lychd.extensions.host import get_extensions
from lychd.system.constants import CONTAINER_LYCHD_PORT, CONTAINER_POSTGRES_PORT, PATH_CRYPT_ROOT
from lychd.system.desktop.private import private_directory, publish_file, verify_private_directory, verify_private_file
from lychd.system.desktop.reactor_identity import create_identities
from lychd.system.desktop.reactor_link import LINK_PORT, ReactorProjection, expose_host_engines
from lychd.system.services.native_runtime import NativeRuntimeActuator
from lychd.system.services.reactor import HostReactor

if TYPE_CHECKING:
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig

_logger = logging.getLogger(__name__)
_COMPOSE_HOST_WEB_PORT = 7134


def _host_projection(
    settings: Settings,
) -> tuple[AnimatorRegistry, ReactorProjection, tuple[SoulstoneConfig | PortalConfig, ...]]:
    """Publish the host-resolved Rune endpoints that both desktop network namespaces can serve."""
    if settings.orchestration.switching.actuator != "native-process":
        msg = "Configure the host desktop settings and native state directory first."
        raise ValueError(msg)
    extensions = get_extensions()
    runes = load_rune_registry(extensions)
    declarations = compile_animator_declarations(settings=settings, runes=runes)
    registry = AnimatorRegistry(
        declarations=declarations,
        soulstone_registrations=extensions.soulstone_registrations,
        portal_registrations=extensions.portal_registrations,
    )
    registry.load(probe_readiness=False)
    if not declarations.lifecycle_binding_digest:
        msg = "Configure at least one dedicated desktop Soulstone."
        raise ValueError(msg)
    ports: dict[str, int] = {}
    host_reserved = {_COMPOSE_HOST_WEB_PORT, LINK_PORT}
    for binding in settings.orchestration.switching.containers:
        if binding.host_port in host_reserved:
            msg = f"Host port {binding.host_port} for {binding.animator!r} is reserved by the desktop Reactor project."
            raise ValueError(msg)
    reserved = {CONTAINER_LYCHD_PORT, CONTAINER_POSTGRES_PORT, *host_reserved}
    for stone in declarations.soulstones:
        if stone.port is None or not stone.concurrency.dedicated:
            msg = f"Expected a dedicated desktop endpoint for {stone.name!r}."
            raise ValueError(msg)
        if stone.port in reserved:
            msg = f"Port {stone.port} for {stone.name!r} is reserved by the desktop Reactor project."
            raise ValueError(msg)
        if str(stone.base_url).rstrip("/") != f"http://127.0.0.1:{stone.port}/v1":
            msg = f"Configure an explicit http://127.0.0.1:{stone.port}/v1 endpoint for {stone.name!r}."
            raise ValueError(msg)
        ports[stone.name] = stone.port
    exported = (*declarations.soulstones, *declarations.portals)
    documents = _guest_documents(settings, exported)
    digest = hashlib.sha256()
    for path, content in sorted(documents.items()):
        digest.update(path.as_posix().encode() + b"\0" + hashlib.sha256(content).digest())
    projection = ReactorProjection(
        binding_digest=declarations.lifecycle_binding_digest,
        generation=capability_config_generation(registry),
        profile_digest=f"sha256:{digest.hexdigest()}",
        ports=ports,
    )
    return registry, projection, exported


def _guest_documents(settings: Settings, runes: tuple[SoulstoneConfig | PortalConfig, ...]) -> dict[Path, bytes]:
    document = tomlkit.document()
    document["extensions"] = settings.extensions.model_dump(mode="json")
    public_switching = settings.orchestration.switching.model_dump(
        mode="json",
        include={
            "policy",
            "min_priority_for_hard_swap",
            "planning_timeout_s",
            "drain_timeout_s",
            "warmup_timeout_s",
            "reactor_ack_timeout_s",
        },
    )
    document["orchestration"] = {"switching": {**public_switching, "actuator": "host-reactor"}}
    if settings.weaver.bridge is not None:
        document["weaver"] = {"bridge": settings.weaver.bridge.model_dump(mode="json", exclude_none=True)}
    config = Path("config/lychd")
    documents = {config / "lychd.toml": tomlkit.dumps(document).encode()}
    for index, rune in enumerate(runes):
        values = rune.model_dump(mode="json", exclude_unset=True, exclude_none=True)
        documents[config / "runes" / type(rune).relative_path / f"animator-{index:08d}.toml"] = tomlkit.dumps(
            values
        ).encode()
    return documents


def _bundle(root: Path, projection: ReactorProjection) -> Path:
    public_ca = root / "identities" / "host" / "ca.pem"
    verify_private_file(public_ca)
    digest = hashlib.sha256(projection.link_id.encode() + public_ca.read_bytes()).hexdigest()
    return root / "bundles" / digest


def _prepare_identity(root: Path) -> Path:
    identities = root / "identities"
    if not identities.exists():
        with TemporaryDirectory(dir=root) as staging:
            target = Path(staging) / "identities"
            private_directory(target)
            create_identities(target)
            target.rename(identities)
    # Verify original custody even when the guest projection already exists.
    for role in ("host", "vessel"):
        for filename in ("ca.pem", "identity.pem", "identity.key"):
            verify_private_file(identities / role / filename)
    return identities


def _prepare(root: Path, settings: Settings) -> Path:
    _, projection, runes = _host_projection(settings)
    for part in (root, root / "inbox", root / "journal", root / "bundles"):
        if part.exists():
            verify_private_directory(part)
        else:
            private_directory(part)
    identities = _prepare_identity(root)
    documents = _guest_documents(settings, runes)
    bundle = _bundle(root, projection)
    if bundle.is_dir():
        if ReactorProjection.model_validate_json((bundle / "projection.json").read_bytes()) != projection:
            msg = "Existing Reactor projection differs from the host generation."
            raise ValueError(msg)
        return bundle
    with TemporaryDirectory(dir=root / "bundles") as staging:
        target = Path(staging) / "guest"
        private_directory(target)
        for filename in ("ca.pem", "identity.pem", "identity.key"):
            publish_file(target / filename, (identities / "vessel" / filename).read_bytes())
        for relative, content in documents.items():
            private_directory((target / relative).parent)
            publish_file(target / relative, content)
        publish_file(target / "projection.json", projection.model_dump_json().encode())
        target.rename(bundle)
    return bundle


async def _serve(root: Path, settings: Settings, listen: str) -> None:
    address = ipaddress.ip_address(listen)
    if not address.is_private or address.is_unspecified or address.is_multicast or address.is_reserved:
        msg = "Choose a specific loopback or private host address for desktop inference."
        raise ValueError(msg)
    registry, projection, _ = _host_projection(settings)
    bundle = _bundle(root, projection)
    verify_private_directory(bundle)
    if ReactorProjection.model_validate_json((bundle / "projection.json").read_bytes()) != projection:
        msg = "Re-run desktop reactor-prepare for the active configuration."
        raise ValueError(msg)
    for part in (root / "inbox", root / "journal", root / "identities" / "host"):
        verify_private_directory(part)
    actuator = NativeRuntimeActuator(registry, settings.orchestration.switching)
    try:
        await actuator.verify_startup()
        consumer = HostReactor(
            registry,
            actuator=actuator,
            inbox_dir=root / "inbox",
            journal_dir=root / "journal",
            lock_factory=nullcontext,
            policy=resolve_switch_policy(settings.orchestration.switching.policy),
        )
        session = secrets.token_hex(32)
        for folder in ("journal", "inbox"):
            marker = root / folder / ".host-session"
            publish_file(marker, session.encode(), replace=marker.exists())
        async with expose_host_engines(projection, root / "identities" / "host", listen=str(address), session=session):
            while True:
                if (
                    any((root / "inbox").glob("*.json"))
                    or any((root / "journal").glob("*.processing.json"))
                    or any((root / "journal").glob("*.acquiring.json"))
                    or any((root / "journal").glob("*.contained.json"))
                ):
                    try:
                        await consumer.consume_all()
                    except RuntimeError:
                        if any((root / "journal").glob("*.contained.json")) or any(
                            (root / "journal").glob("*.processing.json")
                        ):
                            _logger.exception("Unresolved desktop transition; preserving live Animator ownership")
                            await asyncio.Event().wait()
                        _logger.exception("Desktop Reactor declined or rejected a request")
                await asyncio.sleep(0.25)
    finally:
        await actuator.aclose()


def prepare() -> None:
    """Return the three bind sources needed by the desktop Compose overlay."""
    root = PATH_CRYPT_ROOT / "desktop-reactor"
    with redirect_stdout(sys.stderr):
        bundle = _prepare(root, get_settings())
    click.echo(
        json.dumps(
            {
                "LYCHD_REACTOR_UID": str(os.getuid() if os.name != "nt" else 1001),
                "LYCHD_REACTOR_BUNDLE": str(bundle),
                "LYCHD_REACTOR_INBOX": str(root / "inbox"),
                "LYCHD_REACTOR_JOURNAL": str(root / "journal"),
            },
            indent=2,
        )
    )


def serve(listen: str) -> None:
    """Keep host child handles and reserved endpoints alive for the caged Vessel."""
    asyncio.run(_serve(PATH_CRYPT_ROOT / "desktop-reactor", get_settings(), listen))
