"""Recover source-level attribute docstrings for presentation.

Python deliberately discards string literals placed after assignments.  They
remain useful source documentation, however, and Pydantic applies the same
source-inspection pattern for ``use_attribute_docstrings``.  This module keeps
that concern at the presentation boundary: descriptions may disappear when
source is unavailable, but lifecycle authority and execution never depend on
them.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Collection, Mapping
from functools import cache
from pathlib import Path
from types import MappingProxyType, ModuleType


@cache
def module_attribute_docstrings(module: ModuleType) -> Mapping[str, str]:
    """Return module assignments paired with their adjacent string literals."""
    try:
        source = inspect.getsource(module)
    except (OSError, TypeError):
        return MappingProxyType({})

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return MappingProxyType({})

    descriptions: dict[str, str] = {}
    for statement, following in zip(tree.body, tree.body[1:], strict=False):
        name = _assigned_name(statement)
        if name is None:
            continue
        if not isinstance(following, ast.Expr) or not isinstance(following.value, ast.Constant):
            continue
        if not isinstance(following.value.value, str):
            continue
        description = inspect.cleandoc(following.value.value)
        if description:
            descriptions[name] = description
    return MappingProxyType(descriptions)


def path_attribute_summaries(
    module: ModuleType,
    *,
    include: Collection[Path] | None = None,
) -> dict[Path, str]:
    """Resolve first-line attribute docstrings for path values in ``module``."""
    namespace = vars(module)
    summaries: dict[Path, str] = {}
    for name, description in module_attribute_docstrings(module).items():
        value = namespace.get(name)
        if not isinstance(value, Path) or (include is not None and value not in include):
            continue
        summaries[value] = description.partition("\n")[0]
    return summaries


def _assigned_name(statement: ast.stmt) -> str | None:
    """Return the sole simple name assigned by one module-level statement."""
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
        return statement.targets[0].id
    return None
