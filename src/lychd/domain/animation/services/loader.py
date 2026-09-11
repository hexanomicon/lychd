from __future__ import annotations

from collections.abc import Mapping, Sequence
from ipaddress import ip_address
from typing import Any, cast
from urllib.parse import urlsplit

import structlog

from lychd.config.runes import RuneConfig
from lychd.domain.animation.schemas import (
    PortalConfig,
    SoulstoneConfig,
    is_placeholder,
)
from lychd.domain.animation.secret_isolation import validate_secret_declarations

logger = structlog.get_logger()


class AnimatorConfigError(ValueError):
    """Raised when animation configuration violates runtime constraints."""


class AnimatorLoader:
    """Hydrate one already-loaded Rune snapshot into animation declarations.

    Filesystem discovery and Settings ownership remain at composition roots. This
    service receives immutable declarations plus explicit settings-derived policy;
    it never performs a second configuration read.
    """

    _AUTO_PORT_START = 20000
    _MAX_PORT = 65535

    def __init__(
        self,
        *,
        reserved_ports: Mapping[str, int],
        core_secret_names: tuple[str, ...],
    ) -> None:
        """Bind hydration to explicit port and secret-isolation policy."""
        self._reserved_ports = dict(reserved_ports)
        self._core_secret_names = core_secret_names

    def hydrate_all(
        self,
        loaded: Sequence[RuneConfig],
    ) -> tuple[list[SoulstoneConfig], list[PortalConfig]]:
        """Hydrate Soulstone and Portal Runes from one validated snapshot."""
        snapshot = tuple(loaded)
        soulstones = [instance for instance in snapshot if isinstance(instance, SoulstoneConfig)]
        portals = [instance for instance in snapshot if isinstance(instance, PortalConfig)]

        soulstones = [stone for stone in soulstones if not self._is_unresolved_sample_soulstone(stone)]
        portals = [portal for portal in portals if not self._is_unresolved_sample_portal(portal)]
        self._validate_unique_names(soulstones, portals)
        self._validate_secret_isolation(soulstones, portals)

        soulstones = self._hydrate_soulstone_endpoints(soulstones)
        self._validate_ports(soulstones)

        logger.info(
            "animators_loaded",
            soulstones=len(soulstones),
            portals=len(portals),
        )
        return soulstones, portals

    def _hydrate_soulstone_endpoints(self, stones: list[SoulstoneConfig]) -> list[SoulstoneConfig]:
        used_ports = set(self._reserved_ports.values())
        for stone in stones:
            self._validate_soulstone_base_url(stone)
            port_was_set = "port" in stone.model_fields_set
            base_url_was_set = "base_url" in stone.model_fields_set
            base_url_port = self._port_from_base_url(stone.base_url)
            if (
                port_was_set
                and stone.port is not None
                and base_url_was_set
                and base_url_port is not None
                and stone.port != base_url_port
            ):
                msg = f"Soulstone '{stone.name}' declares port {stone.port} but base_url uses port {base_url_port}."
                raise AnimatorConfigError(msg)
            if stone.port is not None:
                used_ports.add(stone.port)
            elif base_url_was_set and base_url_port is not None:
                port = base_url_port
                used_ports.add(port)

        hydrated: list[SoulstoneConfig] = []
        for stone in stones:
            auto_port = stone.port is None
            auto_base_url = "base_url" not in stone.model_fields_set

            port = stone.port
            if auto_port:
                port = self._port_from_base_url(stone.base_url) or self._next_auto_port(used_ports)
                used_ports.add(port)

            base_url = str(stone.base_url) if not auto_base_url else f"http://localhost:{port}/v1"
            if port == stone.port and str(stone.base_url) == base_url:
                hydrated.append(stone)
                continue

            # Defaults are not operator declarations. Reintroducing every default
            # as an explicit field breaks command-authority validation (notably
            # llama.cpp exec passthrough) while merely allocating an endpoint.
            data = stone.model_dump(mode="json", exclude_unset=True)
            data["port"] = port
            data["base_url"] = base_url
            validator = cast("Any", type(stone))
            merged = validator.model_validate(data)
            if stone.source_file is not None:
                merged = merged.bind_source_file(stone.source_file)
            hydrated.append(cast("SoulstoneConfig", merged))

        return hydrated

    def _validate_soulstone_base_url(self, stone: SoulstoneConfig) -> None:
        """Keep local Soulstone traffic on an explicit loopback endpoint.

        A non-loopback endpoint is a Portal-class egress boundary even when its
        configuration is shaped like a Soulstone. Requiring an explicit port also
        keeps the connector URL identical to the locally launched runtime port.
        """
        if stone.base_url is None:
            return
        parsed = urlsplit(str(stone.base_url))
        if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
            msg = f"Soulstone '{stone.name}' base_url cannot contain userinfo, query, or fragment components."
            raise AnimatorConfigError(msg)
        hostname = parsed.hostname
        if hostname is None or not self._is_loopback_host(hostname):
            msg = f"Soulstone '{stone.name}' base_url must use an approved loopback host."
            raise AnimatorConfigError(msg)
        if parsed.port is None:
            msg = f"Soulstone '{stone.name}' base_url must declare an explicit port."
            raise AnimatorConfigError(msg)

    @staticmethod
    def _is_loopback_host(hostname: str) -> bool:
        if hostname == "localhost":
            return True
        try:
            return ip_address(hostname).is_loopback
        except ValueError:
            return False

    def _port_from_base_url(self, base_url: object | None) -> int | None:
        if base_url is None:
            return None
        return urlsplit(str(base_url)).port

    def _next_auto_port(self, used_ports: set[int]) -> int:
        port = self._AUTO_PORT_START
        while port in used_ports:
            port += 1
            if port > self._MAX_PORT:
                msg = "No free auto-allocatable Soulstone ports remain."
                raise AnimatorConfigError(msg)
        return port

    def _validate_ports(self, stones: list[SoulstoneConfig]) -> None:
        errors: list[str] = []
        seen: dict[int, str] = {}

        for stone in stones:
            if stone.port is None:
                errors.append(f"{stone.name} has no hydrated port")
                continue
            for owner, port in self._reserved_ports.items():
                if stone.port == port:
                    errors.append(f"{stone.name} conflicts with {owner} (port {stone.port})")
                    break

            if stone.port in seen:
                errors.append(f"{stone.name} conflicts with {seen[stone.port]} (port {stone.port})")
            seen[stone.port] = stone.name

        if errors:
            msg = f"Port conflicts detected: {', '.join(errors)}"
            raise AnimatorConfigError(msg)

    def _validate_unique_names(self, soulstones: list[SoulstoneConfig], portals: list[PortalConfig]) -> None:
        errors: list[str] = []

        seen_soulstones: set[str] = set()
        for stone in soulstones:
            if stone.name in seen_soulstones:
                errors.append(f"duplicate soulstone name '{stone.name}'")
            seen_soulstones.add(stone.name)

        seen_portals: set[str] = set()
        for portal in portals:
            if portal.name in seen_portals:
                errors.append(f"duplicate portal name '{portal.name}'")
            seen_portals.add(portal.name)

        shared = sorted(seen_soulstones.intersection(seen_portals))
        errors.extend(f"name '{name}' used by both soulstone and portal" for name in shared)

        if errors:
            msg = f"Animator name conflicts detected: {', '.join(errors)}"
            raise AnimatorConfigError(msg)

    def _validate_secret_isolation(
        self,
        soulstones: list[SoulstoneConfig],
        portals: list[PortalConfig],
    ) -> None:
        """Apply the shared declaration policy before any runtime is hydrated."""
        try:
            validate_secret_declarations(
                core_secret_names=self._core_secret_names,
                soulstones=soulstones,
                portals=portals,
            )
        except ValueError as exc:
            raise AnimatorConfigError(str(exc)) from exc

    def _is_unresolved_sample_soulstone(self, stone: SoulstoneConfig) -> bool:
        if is_placeholder(stone.name) or is_placeholder(stone.quadlet.image):
            logger.debug("skipping_sample_soulstone", path=str(stone.source_file))
            return True
        return False

    def _is_unresolved_sample_portal(self, portal: PortalConfig) -> bool:
        if is_placeholder(portal.name):
            logger.debug("skipping_sample_portal", path=str(portal.source_file))
            return True
        return False
