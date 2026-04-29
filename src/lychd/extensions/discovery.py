from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable

import structlog

logger = structlog.get_logger()


class ExtensionDiscovery:
    """Import extension modules so subclass-based contracts are visible at runtime."""

    def import_builtin_modules(self) -> list[str]:
        """Import every module under ``lychd.extensions.builtin``.

        Importing modules is enough for ABC subclass discovery to work.
        """
        return self._import_package_tree("lychd.extensions.builtin")

    def import_packages(self, package_names: Iterable[str]) -> list[str]:
        """Import every module for each provided package name."""
        imported: list[str] = []
        for package_name in package_names:
            imported.extend(self._import_package_tree(package_name))
        return imported

    def _import_package_tree(self, package_name: str) -> list[str]:
        package = importlib.import_module(package_name)
        imported = [package_name]

        if not hasattr(package, "__path__"):
            return imported

        for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
            try:
                importlib.import_module(module_info.name)
            except Exception:  # noqa: BLE001 pragma: no cover - defensive import boundary
                logger.debug("extension_module_skipped", module=module_info.name, reason="import_error")
                continue
            imported.append(module_info.name)

        return imported
