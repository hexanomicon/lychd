import importlib.machinery
import importlib.util
from pathlib import Path
from typing import Any


class CryptSourceLoader:
    """Load provisional Crypt source modules into Core registries.

    This is a pre-v1 assimilation helper, not an extension ABI. It imports
    trusted Python source so the composed runtime can discover rune-shaped
    schemas and then let Forge/Smith verification own repair.

    Binary organs require Forge-mediated validation before runtime loading.
    """

    def __init__(self, codex_loader: Any) -> None:
        """Create loader bound to a schema registry.

        Args:
            codex_loader: Registry exposing ``register_schema(schema)``.

        """
        self.codex_loader = codex_loader

    def scan_extensions(self, extensions_path: Path) -> None:
        """Scan an extension directory for loadable modules.

        Args:
            extensions_path: Directory containing provisional Python source modules.

        """
        if not extensions_path.exists():
            return

        for item in extensions_path.iterdir():
            if item.suffix == ".py" and not item.name.startswith("_"):
                self._load_and_translate(item)

    def _load_and_translate(self, file_path: Path) -> None:
        """Load one extension module and register rune-shaped classes.

        Args:
            file_path: Python source module path to load.

        """
        module_name = file_path.stem

        # Binary modules are deliberately excluded from this direct runtime path.
        # They need a Forge manifest and platform validation before import.
        loader = importlib.machinery.SourceFileLoader(module_name, str(file_path))

        spec = importlib.util.spec_from_loader(module_name, loader)
        if not spec or not spec.loader:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 2. Scan the isolated module for rune-shaped classes.
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue

            obj = getattr(module, attr_name)

            # We are looking for Classes that match the shape, not instances.
            # issubclass() fails for Protocols with non-method members.
            if isinstance(obj, type):
                has_path = hasattr(obj, "relative_path")
                has_validate = hasattr(obj, "model_validate")
                if has_path and has_validate:
                    self.codex_loader.register_schema(obj)
