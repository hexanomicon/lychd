"""Codex decision shapes + pure guards (wave4-design §1.0, §3.4a-c).

`ConsentDecision` is what the ledger's `park` returns to the graph (status + id);
`ConsentView` is the read-model every web surface projects. `censor()` and
`constraints_admit()` are pure, side-effect-free functions: censor creates the
default-deny audit/UI copy while constraints_admit is the fail-closed preauth
constraint check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Literal, cast

__all__ = [
    "CENSORED_VALUE",
    "ConsentDecision",
    "ConsentStatusValue",
    "ConsentView",
    "censor",
    "constraints_admit",
]

ConsentStatusValue = Literal["pending", "granted", "denied", "expired", "cancelled"]

CENSORED_VALUE = "‹censored›"  # noqa: RUF001 - deliberate guillemet marker (design §3.4a)

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
    decided_at: datetime | None = None
    preauth_slug: str | None = None


def censor(payload: dict[str, Any]) -> dict[str, str]:
    """Retain argument names while refusing every value in the consent projection.

    Raw arguments remain available to preauthorization and exact deferred
    execution. The durable consent audit/UI copy is default-deny because a key
    name cannot prove that an arbitrary value is safe to disclose.
    """
    return {str(key): CENSORED_VALUE for key in payload}


def _args_admit(allow: Any, payload: dict[str, Any]) -> bool:
    """Every `{arg: [allowed, ...]}` entry must find the payload arg in its allowlist."""
    if not isinstance(allow, dict):
        return False
    for arg_name, allowed in cast("dict[Any, Any]", allow).items():
        field_name = str(arg_name)
        if not isinstance(allowed, list):
            return False
        if not field_name or field_name not in payload:
            return False
        actual = payload[field_name]
        if not any(_same_json_value(actual, candidate) for candidate in cast("list[Any]", allowed)):
            return False
    return True


def _same_json_value(actual: Any, expected: Any) -> bool:
    """Compare JSON-shaped authority without Python's bool/number coercion."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        actual_object = cast("dict[Any, Any]", actual)
        expected_object = cast("dict[Any, Any]", expected)
        if any(not isinstance(key, str) for key in actual_object) or actual_object.keys() != expected_object.keys():
            return False
        return all(_same_json_value(value, expected_object[key]) for key, value in actual_object.items())
    if isinstance(actual, list):
        actual_array = cast("list[Any]", actual)
        expected_array = cast("list[Any]", expected)
        return len(actual_array) == len(expected_array) and all(
            _same_json_value(value, candidate) for value, candidate in zip(actual_array, expected_array, strict=True)
        )
    if actual is None or isinstance(actual, (bool, int, float, str)):
        return bool(actual == expected)
    return False


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
