"""Codex decision shapes + pure guards (wave4-design §1.0, §3.4a-c).

`ConsentDecision` is what the ledger's `park` returns to the graph (status + id);
`ConsentView` is the read-model every web surface projects. `censor()` and
`constraints_admit()` are pure, side-effect-free functions (censor scrubs secrets
from a payload before it is stored; constraints_admit is the fail-closed preauth
constraint check).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import Any, Literal, cast

__all__ = [
    "ConsentDecision",
    "ConsentStatusValue",
    "ConsentView",
    "censor",
    "constraints_admit",
]

ConsentStatusValue = Literal["pending", "granted", "denied", "expired", "cancelled"]

# Recursive-key denylist: any dict key matching one of these patterns (case-insensitive)
# has its value replaced before the payload is ever persisted or rendered.
_CENSOR_PATTERNS: tuple[str, ...] = ("*key*", "*secret*", "*token*", "*password*", "*credential*")
_CENSORED = "‹censored›"  # noqa: RUF001 - deliberate guillemet marker (design §3.4a)

# The only constraint keys `constraints_admit` understands. ANY other key is fail-closed.
_KNOWN_CONSTRAINT_KEYS: frozenset[str] = frozenset({"args", "path_prefixes"})


@dataclass(frozen=True, kw_only=True)
class ConsentDecision:
    """The ledger's verdict when a run parks: auto-granted, pending, or denied."""

    status: Literal["granted", "pending", "denied"]
    consent_id: str
    preauth_slug: str | None = None


@dataclass(frozen=True, kw_only=True)
class ConsentView:
    """Read-model for one consent row (what every web surface projects)."""

    id: str
    run_id: str
    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)
    status: ConsentStatusValue
    decided_by: str | None = None
    preauth_slug: str | None = None


def _censor_key(key: str) -> bool:
    lowered = key.lower()
    return any(fnmatchcase(lowered, pattern) for pattern in _CENSOR_PATTERNS)


def censor(payload: Any) -> Any:
    """Recursively replace secret-shaped values with a censored marker.

    A dict value whose KEY matches the denylist is replaced wholesale; lists and
    nested dicts are walked. Scalars pass through unchanged.
    """
    if isinstance(payload, dict):
        result: dict[str, Any] = {}
        for key, value in cast("dict[Any, Any]", payload).items():
            key_str = str(key)
            result[key_str] = _CENSORED if _censor_key(key_str) else censor(value)
        return result
    if isinstance(payload, list):
        return [censor(item) for item in cast("list[Any]", payload)]
    return payload


def _args_admit(allow: Any, payload: dict[str, Any]) -> bool:
    """Every `{arg: [allowed, ...]}` entry must find the payload arg in its allowlist."""
    if not isinstance(allow, dict):
        return False
    for arg_name, allowed in cast("dict[Any, Any]", allow).items():
        if not isinstance(allowed, list):
            return False
        if payload.get(str(arg_name)) not in cast("list[Any]", allowed):
            return False
    return True


def _path_prefixes_admit(prefixes: Any, payload: dict[str, Any]) -> bool:
    """Admit named absolute paths only within their declared lexical roots.

    The constraint shape is ``{payload_field: [allowed_root, ...]}``. Naming the
    field prevents unrelated strings (or a nested path hidden from a shallow scan)
    from being treated as filesystem authority. This is a lexical admission check;
    effect-time code must still resolve symlinks beneath its trusted root.
    """
    if not isinstance(prefixes, dict) or not prefixes:
        return False
    for raw_field, raw_roots in cast("dict[Any, Any]", prefixes).items():
        field_name = str(raw_field)
        candidate_value = payload.get(field_name)
        if not field_name or not isinstance(candidate_value, str):
            return False
        if not isinstance(raw_roots, list) or not raw_roots:
            return False
        candidate = _safe_absolute_path(candidate_value)
        if candidate is None:
            return False
        roots = [_safe_absolute_path(root) if isinstance(root, str) else None for root in cast("list[Any]", raw_roots)]
        if any(root is None for root in roots) or not any(
            candidate.is_relative_to(root) for root in roots if root is not None
        ):
            return False
    return True


def _safe_absolute_path(value: str) -> PurePosixPath | None:
    """Parse one traversal-free absolute lexical path."""
    path = PurePosixPath(value)
    return path if path.is_absolute() and ".." not in path.parts else None


def constraints_admit(constraints: dict[str, Any], payload: dict[str, Any]) -> bool:
    """Whether ``payload`` satisfies a preauthorization's constraint document.

    Supports ``{"args": {name: [allowed]}, "path_prefixes": {name: [root]}}``.
    Empty constraints admit anything. ANY unrecognized constraint key ⇒ ``False``
    (fail-closed — a constraint we do not understand can never be satisfied).
    """
    for key in constraints:
        if key not in _KNOWN_CONSTRAINT_KEYS:
            return False
    if "args" in constraints and not _args_admit(constraints["args"], payload):
        return False
    return not ("path_prefixes" in constraints and not _path_prefixes_admit(constraints["path_prefixes"], payload))
