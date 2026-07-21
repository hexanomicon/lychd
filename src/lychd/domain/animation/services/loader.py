from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any, cast, overload
from urllib.parse import urlsplit

import structlog

from lychd.config.runes import ConfigLoader, RuneConfig
from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    PortalConfig,
    SoulstoneConfig,
    is_placeholder,
)
from lychd.system.constants import PATH_RUNES_DIR

logger = structlog.get_logger()


class AnimatorConfigError(ValueError):
    """Raised when animation configuration violates runtime constraints."""


class AnimatorLoader:
    """Load animation Runes with inherited defaults and validation.

    This loader operates purely on TOML-backed Rune declarations. It does not
    construct runtime animator handles or connectors; that responsibility belongs
    to runtime factories/registry code.
    """

    _INHERITABLE_FIELDS: tuple[str, ...] = ()
    _AUTO_PORT_START = 20000
    _MAX_PORT = 65535

    def __init__(
        self,
        *,
        rune_schemas: Sequence[type[RuneConfig]],
        reserved_ports: dict[str, int] | None = None,
        runes_dir: Path | None = None,
        core_secret_names: tuple[str, str] | None = None,
    ) -> None:
        """Initialize loader with required rune schemas and reserved host ports."""
        settings = get_settings()
        self._runes_dir = runes_dir or PATH_RUNES_DIR
        self._rune_schemas = list(rune_schemas)
        self._reserved_ports = reserved_ports or settings.server.reserved_ports_map
        self._core_secret_names = core_secret_names or (
            settings.server.web.secret_key_secret,
            settings.server.database.password_secret,
        )

    def load_all(self) -> tuple[list[SoulstoneConfig], list[PortalConfig]]:
        """Load Soulstone/Portal Runes with inherited animator defaults."""
        try:
            loaded = ConfigLoader(runes_dir=self._runes_dir).load_all(self._rune_schemas)
        except ValueError as exc:
            msg = f"Failed to load animation runes: {exc}"
            raise AnimatorConfigError(msg) from exc

        animator_defaults = self._resolve_animator_defaults(loaded)
        soulstones = [instance for instance in loaded if isinstance(instance, SoulstoneConfig)]
        portals = [instance for instance in loaded if isinstance(instance, PortalConfig)]

        if animator_defaults is not None:
            soulstones = [self._inherit_defaults(stone, animator_defaults) for stone in soulstones]
            portals = [self._inherit_defaults(portal, animator_defaults) for portal in portals]

        soulstones = [stone for stone in soulstones if not self._is_unresolved_sample_soulstone(stone)]
        portals = [portal for portal in portals if not self._is_unresolved_sample_portal(portal)]
        self._validate_unique_names(soulstones, portals)
        self._validate_secret_isolation(soulstones, portals)

        soulstones = self._hydrate_soulstone_endpoints(soulstones)
        self._validate_ports(soulstones)

        logger.info(
            "animators_loaded",
            animator_defaults=animator_defaults is not None,
            soulstones=len(soulstones),
            portals=len(portals),
        )
        return soulstones, portals

    def _resolve_animator_defaults(self, loaded: list[Any]) -> AnimatorConfig | None:
        defaults = [instance for instance in loaded if type(instance) is AnimatorConfig]
        if len(defaults) > 1:
            msg = "Animator defaults must resolve to at most one parent Rune instance."
            raise AnimatorConfigError(msg)
        return defaults[0] if defaults else None

    @overload
    def _inherit_defaults(self, instance: SoulstoneConfig, defaults: AnimatorConfig) -> SoulstoneConfig: ...

    @overload
    def _inherit_defaults(self, instance: PortalConfig, defaults: AnimatorConfig) -> PortalConfig: ...

    def _inherit_defaults(
        self,
        instance: SoulstoneConfig | PortalConfig,
        defaults: AnimatorConfig,
    ) -> SoulstoneConfig | PortalConfig:
        data = instance.model_dump(mode="python")
        defaults_data = defaults.model_dump(mode="python")

        for field in self._INHERITABLE_FIELDS:
            if field in instance.model_fields_set:
                continue
            if field not in defaults.model_fields_set:
                continue
            fallback = defaults_data.get(field)
            if not self._is_unset(fallback):
                data[field] = deepcopy(fallback)

        validator = cast("Any", type(instance))
        merged = validator.model_validate(data)
        if instance.source_file is not None:
            merged = merged.bind_source_file(instance.source_file)
        return cast("SoulstoneConfig | PortalConfig", merged)

    def _hydrate_soulstone_endpoints(self, stones: list[SoulstoneConfig]) -> list[SoulstoneConfig]:
        used_ports = set(self._reserved_ports.values())
        for stone in stones:
            port_was_set = self._field_was_set(stone, "port")
            base_url_was_set = self._field_was_set(stone, "base_url")
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
            auto_base_url = not self._field_was_set(stone, "base_url")

            port = stone.port
            if auto_port:
                port = self._port_from_base_url(stone.base_url) or self._next_auto_port(used_ports)
                used_ports.add(port)

            base_url = str(stone.base_url) if not auto_base_url else f"http://localhost:{port}/v1"
            if port == stone.port and str(stone.base_url) == base_url:
                hydrated.append(stone)
                continue

            data = stone.model_dump(mode="json")
            data["port"] = port
            data["base_url"] = base_url
            validator = cast("Any", type(stone))
            merged = validator.model_validate(data)
            if stone.source_file is not None:
                merged = merged.bind_source_file(stone.source_file)
            hydrated.append(cast("SoulstoneConfig", merged))

        return hydrated

    def _field_was_set(self, instance: SoulstoneConfig | PortalConfig, field_name: str) -> bool:
        return field_name in instance.model_fields_set

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
        """Reject credential aliases before any Portal connector can resolve them."""
        app_secret, db_secret = self._core_secret_names
        if app_secret == db_secret:
            msg = "Core application-signing and database-password secrets must use distinct names"
            raise AnimatorConfigError(msg)

        core_names = {app_secret, db_secret}
        portal_names = {portal.api_key_secret_name for portal in portals if portal.api_key_secret_name is not None}
        core_aliases = sorted(core_names.intersection(portal_names))
        if core_aliases:
            msg = f"Portal API secret(s) {', '.join(core_aliases)} cannot alias core application or database secrets"
            raise AnimatorConfigError(msg)

        privileged = core_names | portal_names
        control_plane_owners: dict[str, str] = {}
        for stone in soulstones:
            for secret_name in stone.control_plane_secret_names:
                previous_owner = control_plane_owners.get(secret_name)
                if previous_owner is not None:
                    msg = (
                        f"Soulstones '{previous_owner}' and '{stone.name}' cannot share "
                        f"control-plane secret '{secret_name}'"
                    )
                    raise AnimatorConfigError(msg)
                control_plane_owners[secret_name] = stone.name
            rune_secret_names = {
                *stone.secret_env_files.values(),
                *stone.control_plane_secret_names,
            }
            aliases = sorted(rune_secret_names.intersection(privileged))
            if aliases:
                msg = (
                    f"Soulstone '{stone.name}' secret(s) {', '.join(aliases)} must be distinct "
                    "from core and Portal secrets"
                )
                raise AnimatorConfigError(msg)

    def _is_unset(self, value: Any) -> bool:
        return value in (None, "", [], {})

    def _is_unresolved_sample_soulstone(self, stone: SoulstoneConfig) -> bool:
        if is_placeholder(stone.name) or is_placeholder(stone.image):
            logger.debug("skipping_sample_soulstone", path=str(stone.source_file))
            return True
        return False

    def _is_unresolved_sample_portal(self, portal: PortalConfig) -> bool:
        if is_placeholder(portal.name):
            logger.debug("skipping_sample_portal", path=str(portal.source_file))
            return True
        return False
