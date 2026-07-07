from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Final

from lychd.config.settings import ExtensionSettings, get_settings
from lychd.extensions.context import ExtensionContext
from lychd.system.constants import PATH_EXTENSIONS_DIR

BUILTIN_ROOT_PACKAGE: Final = "lychd.extensions.builtin"


class ExtensionManager:
    """Assemble selected built-in and Crypt extension contributions."""

    def __init__(
        self,
        *,
        builtins: list[str] | tuple[str, ...],
        crypt: list[str] | tuple[str, ...],
        crypt_root: Path | None = None,
    ) -> None:
        """Create a manager for explicit extension activation lists."""
        self._builtins = list(builtins)
        self._crypt = list(crypt)
        self._crypt_root = crypt_root or PATH_EXTENSIONS_DIR

    @classmethod
    def from_settings(cls, settings: ExtensionSettings | None = None) -> ExtensionManager:
        """Build an extension manager from active settings."""
        active = settings or get_settings().extensions
        return cls(builtins=active.builtins, crypt=active.crypt)

    def assemble(self) -> ExtensionContext:
        """Import selected extensions and return their registered contributions.

        Each ``register()`` call runs inside a provenance bracket so stores can
        attribute contributions to the extension that made them.
        """
        context = ExtensionContext()

        # Core pre-pass (wave4-design §3.4d): the Codex preauthorization schema is
        # registered by CORE, before any extension registrant runs, so the loaded
        # RuneRegistry always carries CodexPreauthRune instances.
        from lychd.domain.codex.runes import CodexPreauthRune

        context.runes.add_schema(CodexPreauthRune)

        for extension_id in self._builtins:
            with context.provenance(extension_id):
                self._register_builtin(extension_id, context)

        for extension_id in self._crypt:
            with context.provenance(extension_id):
                self._register_crypt(extension_id, context)

        return context

    def _register_builtin(self, extension_id: str, context: ExtensionContext) -> None:
        module_path = self._builtin_register_module(extension_id)
        module = importlib.import_module(module_path)
        self._call_register(module, extension_id, context)

    def _builtin_register_module(self, extension_id: str) -> str:
        """Resolve a selected built-in id to its required register module."""
        dotted_id = ".".join(part.replace("-", "_") for part in self._extension_id_parts(extension_id))
        return f"{BUILTIN_ROOT_PACKAGE}.{dotted_id}.register"

    def _register_crypt(self, extension_id: str, context: ExtensionContext) -> None:
        module_path = self._crypt_module_path(extension_id)
        module = self._load_module(module_path, extension_id)
        self._call_register(module, extension_id, context)

    def _call_register(self, module: ModuleType, extension_id: str, context: ExtensionContext) -> None:
        """Call the selected extension's register(context) shim."""
        register = getattr(module, "register", None)
        if register is None:
            msg = f"Extension '{extension_id}' has no register(context) shim in '{module.__name__}'."
            raise ValueError(msg)
        register(context)

    def _crypt_module_path(self, extension_id: str) -> Path:
        """Resolve the selected Crypt extension register shim path without scanning."""
        register_py = self._crypt_root.joinpath(*self._extension_id_parts(extension_id), "register.py")
        if register_py.exists():
            return register_py

        msg = f"Crypt extension '{extension_id}' was selected but no register shim exists at '{register_py}'."
        raise ValueError(msg)

    def _extension_id_parts(self, extension_id: str) -> tuple[str, ...]:
        """Return validated extension id path parts."""
        path = PurePosixPath(extension_id)
        if path.is_absolute() or not path.parts or any(part in {".", ".."} for part in path.parts):
            msg = f"Invalid extension id '{extension_id}'."
            raise ValueError(msg)
        return path.parts

    def _load_module(self, module_path: Path, extension_id: str) -> ModuleType:
        """Load one explicitly selected extension shim from disk."""
        module_name = f"lychd_crypt_extension_{extension_id.replace('/', '_').replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            msg = f"Could not load Crypt extension '{extension_id}' from '{module_path}'."
            raise ValueError(msg)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
