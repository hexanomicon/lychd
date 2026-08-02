from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

from lychd.config.settings.extensions import ExtensionSettings, extension_id_parts
from lychd.config.settings.root import get_settings
from lychd.extensions.builtin.catalog import builtin_register_module, builtin_registration_order
from lychd.extensions.context import ExtensionContext, ExtensionRegistrationContext
from lychd.system.constants import PATH_EXTENSIONS_DIR

_CORE_PROVIDER_ID = "core"
_BUILTIN_PROVIDER_PREFIX = "builtin:"
_CRYPT_PROVIDER_PREFIX = "crypt:"
_CRYPT_PACKAGE_PREFIX = "lychd_crypt_extension_"


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

        with context.provenance(_CORE_PROVIDER_ID):
            context.runes.add_schema(CodexPreauthRune)

        for activation_id in builtin_registration_order(self._builtins):
            provider_id = f"{_BUILTIN_PROVIDER_PREFIX}{activation_id}"
            self._register_builtin(activation_id, context.registration_view(provider_id))

        for activation_id in self._crypt:
            provider_id = f"{_CRYPT_PROVIDER_PREFIX}{activation_id}"
            self._register_crypt(activation_id, context.registration_view(provider_id))

        context.freeze()
        return context

    def _register_builtin(self, activation_id: str, context: ExtensionRegistrationContext) -> None:
        module_path = self._builtin_register_module(activation_id)
        module = importlib.import_module(module_path)
        self._call_register(module, activation_id, context)

    def _builtin_register_module(self, extension_id: str) -> str:
        """Resolve a selected built-in id to its required register module."""
        return builtin_register_module(extension_id)

    def _register_crypt(self, activation_id: str, context: ExtensionRegistrationContext) -> None:
        module_path = self._crypt_module_path(activation_id)
        module = self._load_module(module_path, activation_id)
        try:
            self._call_register(module, activation_id, context)
        except BaseException:
            self._clear_module_namespace(self._crypt_package_name(activation_id))
            raise

    def _call_register(
        self,
        module: ModuleType,
        extension_id: str,
        context: ExtensionRegistrationContext,
    ) -> None:
        """Call the selected extension's register(context) shim."""
        register = getattr(module, "register", None)
        if register is None:
            msg = f"Extension '{extension_id}' has no register(context) shim in '{module.__name__}'."
            raise ValueError(msg)
        result = register(context)
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            msg = f"Extension '{extension_id}' register(context) must be synchronous and return None."
            raise TypeError(msg)
        if result is not None:
            msg = f"Extension '{extension_id}' register(context) must return None."
            raise TypeError(msg)

    def _crypt_module_path(self, extension_id: str) -> Path:
        """Resolve the selected Crypt extension register shim path without scanning."""
        register_py = self._crypt_root.joinpath(*self._extension_id_parts(extension_id), "register.py")
        if register_py.exists():
            return register_py

        msg = f"Crypt extension '{extension_id}' was selected but no register shim exists at '{register_py}'."
        raise ValueError(msg)

    def _extension_id_parts(self, extension_id: str) -> tuple[str, ...]:
        """Return validated extension id path parts."""
        return extension_id_parts(extension_id)

    def _load_module(self, module_path: Path, activation_id: str) -> ModuleType:
        """Load one selected shim in an isolated package namespace.

        The exact activation id is UTF-8 hex encoded, making the namespace
        injective for every legal id. The synthetic package exposes only the
        selected extension directory, so ``register.py`` can use ordinary
        relative sibling imports without executing package discovery.
        """
        package_name = self._crypt_package_name(activation_id)
        module_name = f"{package_name}.register"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            msg = f"Could not load Crypt extension '{activation_id}' from '{module_path}'."
            raise ValueError(msg)

        package_spec = ModuleSpec(package_name, loader=None, is_package=True)
        package_spec.submodule_search_locations = [str(module_path.parent)]
        package = importlib.util.module_from_spec(package_spec)
        module = importlib.util.module_from_spec(spec)
        self._clear_module_namespace(package_name)
        sys.modules[package_name] = package
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            self._clear_module_namespace(package_name)
            raise
        return module

    @staticmethod
    def _crypt_package_name(activation_id: str) -> str:
        """Return the injective synthetic package for one canonical activation id."""
        return f"{_CRYPT_PACKAGE_PREFIX}{activation_id.encode('utf-8').hex()}"

    @staticmethod
    def _clear_module_namespace(package_name: str) -> None:
        """Remove one synthetic Crypt package generation after replacement/failure."""
        prefix = f"{package_name}."
        for loaded_name in tuple(sys.modules):
            if loaded_name == package_name or loaded_name.startswith(prefix):
                del sys.modules[loaded_name]
