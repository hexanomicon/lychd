import importlib.machinery
import importlib.util
from typing import Any
from pathlib import Path

class CryptMachinery:
    """
    The Translation layer bridging independent Extension Protocol organs into
    the strict structural registry of the Core.
    Resolves the Codex Paradox and supports Dual-Path organs (Python & Rust/PyO3).
    """
    
    def __init__(self, codex_loader: Any) -> None:
        """
        :param codex_loader: The internal singleton registry that manages Rune schemas.
        """
        self.codex_loader = codex_loader
        
    def scan_crypt(self, crypt_path: Path) -> None:
        """
        Scans the external Crypt directory for compiled Rust binaries (.so) 
        and Python modules (.py).
        """
        if not crypt_path.exists():
            return
            
        for item in crypt_path.iterdir():
            if item.suffix in (".py", ".so") and not item.name.startswith("_"):
                self._load_and_translate(item)
                
    def _load_and_translate(self, file_path: Path) -> None:
        """
        Loads the extension bypassing standard import semantics to isolate
        the module. If it satisfies ExtensionSchemaProtocol, dynamically translates 
        and registers it into the Core structural registry.
        """
        module_name = file_path.stem
        
        # 1. Dual-Path Loading via Machinery
        if file_path.suffix == ".so":
            loader = importlib.machinery.ExtensionFileLoader(module_name, str(file_path))
        else:
            loader = importlib.machinery.SourceFileLoader(module_name, str(file_path))
            
        spec = importlib.util.spec_from_loader(module_name, loader)
        if not spec or not spec.loader:
            return
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 2. Translation (The Codex Paradox Resolution)
        # Scan the isolated module for any object conforming to the Protocol memory shape
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
                
            obj = getattr(module, attr_name)
            
            # We are looking for Classes that match the shape, not instances.
            # issubclass() fails for Protocols with non-method members.
            if isinstance(obj, type):
                has_rel = hasattr(obj, "relative_path")
                has_sin = hasattr(obj, "singleton")
                if has_rel and has_sin:
                    self.codex_loader.register_schema(obj)
