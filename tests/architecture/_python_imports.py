"""Conservative Python import discovery for architecture-law tests."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImportRef:
    """A possible imported module and the base named by an import-from statement."""

    module: str
    from_module: str | None = None


def is_package(module: str, package: str) -> bool:
    """Return whether a module is the package itself or one of its descendants."""
    return module == package or module.startswith(f"{package}.")


def imported_modules(path: Path, *, package_root: Path) -> set[ImportRef]:
    """Resolve absolute, relative, and ``from package import submodule`` candidates."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    refs: set[ImportRef] = set()
    package = [package_root.name, *path.relative_to(package_root).parent.parts]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.update(ImportRef(alias.name) for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level:
            parent = package[: len(package) - (node.level - 1)]
            suffix = node.module.split(".") if node.module else []
            base = ".".join([*parent, *suffix])
        else:
            base = node.module or ""
        if base:
            refs.add(ImportRef(base, from_module=base))
        refs.update(
            ImportRef(".".join(filter(None, (base, alias.name))), from_module=base or None)
            for alias in node.names
            if alias.name != "*"
        )
    return refs
