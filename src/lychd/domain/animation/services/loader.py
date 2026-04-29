from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, cast, overload

import structlog
from pydantic import ValidationError

from lychd.config.runes import ConfigLoader, RuneConfigError, RuneSchemaDiscovery
from lychd.config.settings import get_settings
from lychd.domain.animation.schemas import AnimatorConfig, PortalConfig, SoulstoneConfig, is_placeholder
from lychd.system.constants import PATH_RUNES_DIR

logger = structlog.get_logger()


class AnimatorConfigError(ValueError):
    """Raised when animation configuration violates runtime constraints."""


class AnimatorLoader:
    """Load animation rune configs with inherited defaults and validation.

    This loader operates purely on rune config schemas (`*Config`). It does not
    construct runtime animator handles or connectors; that responsibility belongs
    to runtime factories/registry code.
    """

    _INHERITABLE_FIELDS = ("orchestration_labels",)

    def __init__(
        self,
        runes_dir: Path | None = None,
        *,
        reserved_ports: dict[str, int] | None = None,
    ) -> None:
        """Initialize loader with rune root and reserved host ports."""
        self._runes_dir = runes_dir or PATH_RUNES_DIR
        self._reserved_ports = reserved_ports or get_settings().reserved_ports_map

    def load_all(self) -> tuple[list[SoulstoneConfig], list[PortalConfig]]:
        """Load Soulstone/Portal rune configs with inherited animator defaults."""
        try:
            schemas = RuneSchemaDiscovery(include_builtin_extensions=True).discover_classes()
            loaded = ConfigLoader(runes_dir=self._runes_dir).load_all(schemas)
        except (RuneConfigError, ValidationError) as exc:
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

        for portal in portals:
            self._validate_portal_requirements(portal)

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
            msg = "Animator defaults must resolve to at most one singleton instance."
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
        return cast("SoulstoneConfig | PortalConfig", merged.with_file_name(instance.file_name))

    def _validate_portal_requirements(self, portal: PortalConfig) -> None:
        if not portal.base_url:
            msg = f"Portal '{portal.name}' requires 'base_url'."
            raise AnimatorConfigError(msg)

    def _validate_ports(self, stones: list[SoulstoneConfig]) -> None:
        errors: list[str] = []
        seen: dict[int, str] = {}

        for stone in stones:
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

    def _is_unset(self, value: Any) -> bool:
        return value in (None, "", [], {})

    def _is_unresolved_sample_soulstone(self, stone: SoulstoneConfig) -> bool:
        if is_placeholder(stone.name) or is_placeholder(stone.image):
            logger.debug("skipping_sample_soulstone", path=str(stone.file_name))
            return True
        return False

    def _is_unresolved_sample_portal(self, portal: PortalConfig) -> bool:
        if is_placeholder(portal.name):
            logger.debug("skipping_sample_portal", path=str(portal.file_name))
            return True
        return False
