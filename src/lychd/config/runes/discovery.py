from __future__ import annotations
from collections.abc import Iterable
from pathlib import Path

from lychd.config.runes.base import RuneConfig
from lychd.extensions.discovery import CryptMachinery
from lychd.system.constants import PATH_EXTENSIONS_DIR


class RuneSchemaDiscovery:
    """Discover RuneConfig schemas after runtime import/bootstrap."""

    def __init__(
        self,
        *,
        include_builtin_extensions: bool = True,
        external_packages: Iterable[str] = (),
        crypt_path: Path | None = None,
    ) -> None:
        """Create a schema discoverer.

        Args:
            include_builtin_extensions: Import built-in extension modules.
            external_packages: Additional extension package trees to import.
            crypt_path: Path to the external extensions directory (The Crypt).
        """
        self._include_builtin_extensions = include_builtin_extensions
        self._external_packages = tuple(external_packages)
        self._crypt_path = crypt_path or PATH_EXTENSIONS_DIR

    def discover_classes(self) -> list[type[RuneConfig]]:
        """Return all discovered RuneConfig and ExtensionSchemaProtocol schemas."""
        # 1. Discover built-in and package-based schemas via inheritance
        # Import core schema module before subclass traversal.
        # importlib.import_module("lychd.domain.animation.schemas") # Stub for now

        discovered: set[type[RuneConfig]] = set()
        self._collect_subclasses(RuneConfig, discovered)
        
        # 2. Discover external schemas via CryptMachinery (The Codex Paradox Resolution)
        # CryptMachinery will register discovered schemas into a collector.
        # For simplicity in this discoverer, we'll let it populate a set.
        external_schemas: set[type[RuneConfig]] = set()
        
        class SchemaCollector:
            def register_schema(self, schema: type[RuneConfig]) -> None:
                external_schemas.add(schema)

        machinery = CryptMachinery(SchemaCollector())
        machinery.scan_crypt(self._crypt_path)

        all_schemas = discovered | external_schemas
        filtered = [cls for cls in all_schemas if self._is_allowed_schema_module(cls)]
        return sorted(filtered, key=lambda cls: (cls.__module__, cls.__qualname__))

    def _collect_subclasses(self, parent: type[RuneConfig], discovered: set[type[RuneConfig]]) -> None:
        for subclass in parent.__subclasses__():
            self._collect_subclasses(subclass, discovered)
            discovered.add(subclass)

    def _is_allowed_schema_module(self, cls: type[RuneConfig]) -> bool:
        # For external schemas discovered via machinery, they might not be in "lychd" package.
        # We allow them if they satisfy the protocol.
        if isinstance(cls, type) and hasattr(cls, "relative_path") and hasattr(cls, "singleton"):
            return True
            
        module = cls.__module__
        allowed_packages = ("lychd", *self._external_packages)
        return any(module == package or module.startswith(f"{package}.") for package in allowed_packages)
