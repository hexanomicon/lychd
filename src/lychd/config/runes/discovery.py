from __future__ import annotations

import importlib
from collections.abc import Iterable

from lychd.config.runes.base import RuneConfig
from lychd.extensions.discovery import ExtensionDiscovery


class RuneSchemaDiscovery:
    """Discover RuneConfig schemas after runtime import/bootstrap."""

    def __init__(
        self,
        *,
        include_builtin_extensions: bool = True,
        external_packages: Iterable[str] = (),
    ) -> None:
        """Create a schema discoverer.

        Args:
            include_builtin_extensions: Import built-in extension modules.
            external_packages: Additional extension package trees to import.

        """
        self._include_builtin_extensions = include_builtin_extensions
        self._external_packages = tuple(external_packages)

    def discover_classes(self) -> list[type[RuneConfig]]:
        """Return all currently imported RuneConfig subclasses."""
        # Import core schema module before subclass traversal.
        importlib.import_module("lychd.domain.animation.schemas")

        discovery = ExtensionDiscovery()
        if self._include_builtin_extensions:
            discovery.import_builtin_modules()
        if self._external_packages:
            discovery.import_packages(self._external_packages)

        discovered: set[type[RuneConfig]] = set()
        self._collect_subclasses(RuneConfig, discovered)
        filtered = [cls for cls in discovered if self._is_allowed_schema_module(cls)]
        return sorted(filtered, key=lambda cls: (cls.__module__, cls.__qualname__))

    def _collect_subclasses(self, parent: type[RuneConfig], discovered: set[type[RuneConfig]]) -> None:
        for subclass in parent.__subclasses__():
            self._collect_subclasses(subclass, discovered)
            discovered.add(subclass)

    def _is_allowed_schema_module(self, cls: type[RuneConfig]) -> bool:
        module = cls.__module__
        allowed_packages = ("lychd", *self._external_packages)
        return any(module == package or module.startswith(f"{package}.") for package in allowed_packages)
