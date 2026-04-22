from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Any, cast

import structlog
from pydantic import ValidationError

from lychd.domain.animation.schemas import Portal, Soulstone
from lychd.system.constants import PATH_PORTALS_DIR, PATH_SOULSTONES_DIR

if TYPE_CHECKING:
    from pathlib import Path

# Create the logger for this module
logger = structlog.get_logger()


class AnimatorLoader:
    """The Librarian.

    Responsible for reading the Codex (TOML files), parsing the Inscriptions,
    and manifesting them into strict Pydantic objects (Soulstones and Portals).
    """

    def __init__(
        self,
        soulstones_path: Path | None = None,
        portals_path: Path | None = None,
        reserved_ports: dict[str, int] | None = None,
        default_mounts: list[str] | None = None,  # <--- NEW ARGUMENT
    ) -> None:
        """Initialize the Loader with configuration directories.

        Args:
            soulstones_path: Path to Soulstone definitions. Defaults to HOST_SOULSTONES.
            portals_path: Path to Portal definitions. Defaults to HOST_PORTALS.
            reserved_ports: Mapping of {description: port} for system services.
            default_mounts: List of volumes to inject if none are specified in TOML.

        """
        self._soul_path = soulstones_path or PATH_SOULSTONES_DIR
        self._portal_path = portals_path or PATH_PORTALS_DIR

        # Late import to avoid circular dependencies if settings imports loader
        from lychd.config.settings import get_settings

        settings = get_settings()

        if reserved_ports is None:
            self._reserved_ports = settings.reserved_ports_map
        else:
            self._reserved_ports = reserved_ports

        # Capture the defaults (Global Infrastructure)
        if default_mounts is None:
            self._default_mounts = settings.lychd.default_soulstone_mounts
        else:
            self._default_mounts = default_mounts

    def _validate_ports(self, stones: list[Soulstone]) -> None:
        """Ensure no two soulstones share a port, and none clash with system services."""
        errors: list[str] = []

        # 1. Check against System Reserved Ports
        for s in stones:
            for owner, port in self._reserved_ports.items():
                if s.port == port:
                    errors.append(f"{s.name} conflicts with {owner} (Port {s.port})")
                    break

        # 2. Check for Internal Conflicts
        seen: dict[int, str] = {}
        for s in stones:
            if s.port in seen:
                errors.append(f"{s.name} conflicts with {seen[s.port]} (Port {s.port})")
            seen[s.port] = s.name

        if errors:
            _msg = f"Port conflicts detected: {', '.join(errors)}"
            raise ValueError(_msg)

    def _parse_soulstone_content(self, data: dict[str, Any], filename: str) -> list[Soulstone]:
        """Parse TOML. Handles 'Two-Dot' grouping and schema validation."""
        found: list[Soulstone] = []

        for key, value in data.items():
            if not isinstance(value, dict):
                continue

            entity_conf = cast("dict[str, Any]", value)

            # --- APPLY DEFAULT MOUNTS LOGIC ---
            # If the user did NOT specify 'volumes' (or left it empty),
            # we inject the global defaults.
            # If they DID specify it, we respect their override and do nothing.
            if not entity_conf.get("volumes"):
                entity_conf["volumes"] = list(self._default_mounts)

            try:
                # --- DETECT GROUPING ([logic.alpha]) ---
                # If no 'image' but contains sub-dicts, it's a Group Parent.
                if "image" not in entity_conf and any(isinstance(v, dict) for v in entity_conf.values()):
                    group_name = key
                    for sub_key, sub_val in entity_conf.items():
                        if isinstance(sub_val, dict):
                            child_conf = cast("dict[str, Any]", sub_val)

                            # 1. Inject Identity
                            child_conf["name"] = f"{group_name}.{sub_key}"

                            # 2. Inject Grouping
                            current_groups = child_conf.get("groups", [])
                            if group_name not in current_groups:
                                current_groups.append(group_name)
                            child_conf["groups"] = current_groups

                            # 3. Apply Defaults to Children too
                            if not child_conf.get("volumes"):
                                child_conf["volumes"] = self._default_mounts

                            found.append(Soulstone.model_validate(child_conf))

                # --- SOLITARY ([hermes]) ---
                else:
                    entity_conf["name"] = key
                    found.append(Soulstone.model_validate(entity_conf))

            except ValidationError:
                logger.exception("invalid_soulstone_definition", name=key, file=filename)

        return found

    def load_all(self) -> tuple[list[Soulstone], list[Portal]]:
        """Read the entire Codex and return all found Animators."""
        soulstones = self._load_soulstones()
        portals = self._load_portals()

        logger.info(
            "codex_loaded",
            soulstones=len(soulstones),
            portals=len(portals),
        )
        return soulstones, portals

    def _load_soulstones(self) -> list[Soulstone]:
        """Scan the soulstones directory and validate uniqueness."""
        results: list[Soulstone] = []

        if not self._soul_path.exists():
            logger.warning("soulstone_directory_missing", path=str(self._soul_path))
            return []

        for rune_file in self._soul_path.rglob("*.toml"):
            try:
                content = tomllib.loads(rune_file.read_text(encoding="utf-8"))
                results.extend(self._parse_soulstone_content(content, rune_file.name))
            except tomllib.TOMLDecodeError:
                logger.exception("malformed_toml_file", file=rune_file.name)
            except OSError:
                logger.exception("io_error_reading_file", file=rune_file.name)

        # Validate ports
        self._validate_ports(results)

        return results

    def _load_portals(self) -> list[Portal]:
        """Scan the portals directory."""
        results: list[Portal] = []

        if not self._portal_path.exists():
            return []

        for rune_file in self._portal_path.rglob("*.toml"):
            try:
                content = tomllib.loads(rune_file.read_text(encoding="utf-8"))
                results.extend(self._parse_portal_content(content, rune_file.name))
            except tomllib.TOMLDecodeError:
                logger.exception("malformed_toml_file", file=rune_file.name)
            except OSError:
                logger.exception("io_error_reading_file", file=rune_file.name)

        return results

    def _parse_portal_content(self, data: dict[str, Any], filename: str) -> list[Portal]:
        """Parse a raw TOML dictionary into Portal objects."""
        found: list[Portal] = []

        for key, value in data.items():
            if not isinstance(value, dict):
                continue

            portal_conf = cast("dict[str, Any]", value)

            try:
                portal_conf["name"] = key
                portal = Portal.model_validate(portal_conf)
                found.append(portal)
            except ValidationError:
                logger.exception("invalid_portal_definition", name=key, file=filename)

        return found
