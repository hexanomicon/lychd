from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from pathlib import Path

from lychd.config.runes.base import RUNE_PATH_PART_PATTERN, RuneConfig
from lychd.extensions.discovery import CryptSourceLoader
from lychd.system.constants import PATH_EXTENSIONS_DIR


class RuneSchemaDiscovery:
    """Discover RuneConfig rune classes after runtime import/bootstrap."""

    def __init__(
        self,
        *,
        extension_packages: Iterable[str] = ("lychd.extensions",),
        allowed_packages: Iterable[str] = ("lychd",),
        extensions_path: Path | None = None,
    ) -> None:
        """Create a rune class discoverer.

        Args:
            extension_packages: Importable package roots to scan before rune
                collection.
            allowed_packages: Package prefixes allowed for in-process rune
                subclasses.
            extensions_path: Path to the provisional Crypt extension source directory.

        """
        self._extension_packages = tuple(extension_packages)
        self._allowed_packages = tuple(allowed_packages)
        self._extensions_path = extensions_path or PATH_EXTENSIONS_DIR

    def discover_classes(self) -> list[type[RuneConfig]]:
        """Discover loadable rune classes.

        Returns:
            Deterministically sorted rune classes accepted by the discovery
            filters.

        """
        self._import_extension_packages()

        discovered: set[type[RuneConfig]] = set()
        self._collect_subclasses(RuneConfig, discovered)

        # Provisional Crypt source modules register rune-shaped classes here.
        external_schemas: set[type[RuneConfig]] = set()

        class SchemaCollector:
            def register_schema(self, schema: type[RuneConfig]) -> None:
                external_schemas.add(schema)

        loader = CryptSourceLoader(SchemaCollector())
        loader.scan_extensions(self._extensions_path)

        all_schemas = discovered | external_schemas
        filtered = [cls for cls in all_schemas if self._is_allowed_schema_module(cls, external=cls in external_schemas)]
        return sorted(filtered, key=lambda cls: (cls.__module__, cls.__qualname__))

    def _import_extension_packages(self) -> None:
        """Import configured extension package roots before subclass traversal.

        Raises:
            ImportError: If an extension package or module cannot be imported.

        """
        for package_name in self._extension_packages:
            package = importlib.import_module(package_name)
            package_path = getattr(package, "__path__", None)
            if package_path is None:
                continue
            for module in pkgutil.walk_packages(package_path, f"{package.__name__}."):
                importlib.import_module(module.name)

    def _collect_subclasses(self, parent: type[RuneConfig], discovered: set[type[RuneConfig]]) -> None:
        """Recursively collect RuneConfig subclasses.

        Args:
            parent: Rune class whose subclasses should be walked.
            discovered: Mutable set receiving discovered subclasses.

        """
        for subclass in parent.__subclasses__():
            self._collect_subclasses(subclass, discovered)
            discovered.add(subclass)

    def _is_allowed_schema_module(self, cls: type[RuneConfig], *, external: bool = False) -> bool:
        """Return whether a rune class may enter the loader set.

        Args:
            cls: Candidate rune class from subclass or Crypt source discovery.
            external: Whether the class came from Crypt source discovery.

        Returns:
            ``True`` when the class exposes the rune discovery shape or belongs to
            an allowed package.

        """
        if external and hasattr(cls, "relative_path") and hasattr(cls, "model_validate"):
            raw_path = getattr(cls, "relative_path", None)
            if raw_path is not None and not isinstance(raw_path, Path):
                msg = f"Rune '{cls.__name__}' declares non-Path relative_path {raw_path!r}."
                raise TypeError(msg)
            if raw_path is None:
                msg = f"Rune '{cls.__name__}' declares no relative_path."
                raise ValueError(msg)
            if raw_path.is_absolute() or raw_path == Path():
                msg = f"Rune '{cls.__name__}' declares invalid relative_path '{raw_path}'."
                raise ValueError(msg)
            for part in raw_path.parts:
                if not RUNE_PATH_PART_PATTERN.fullmatch(part):
                    msg = f"Rune '{cls.__name__}' declares invalid relative_path part '{part}'."
                    raise ValueError(msg)
            return True

        module = cls.__module__
        return any(module == package or module.startswith(f"{package}.") for package in self._allowed_packages)
