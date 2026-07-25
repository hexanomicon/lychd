"""Shared, authority-neutral filesystem projection for host CLI plans."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Final

from lychd.system.services.lifecycle import current_authority


class HostTier(StrEnum):
    """One operator-facing XDG tier, plus paths outside those tiers."""

    CODEX = "CODEX"
    CRYPT = "CRYPT"
    FORGE = "FORGE"
    HOST = "HOST"


HOST_TIER_ORDER: Final = (
    HostTier.CODEX,
    HostTier.CRYPT,
    HostTier.FORGE,
    HostTier.HOST,
)


@dataclass(frozen=True)
class HostTopology:
    """One path-tier snapshot derived from current lifecycle authority."""

    codex: Path
    crypt: Path
    forge: Path
    shared_anchors: frozenset[Path]
    routine_anchors: frozenset[Path]

    @classmethod
    def current(cls) -> HostTopology:
        """Derive presentation roots from the planner's patchable authority."""
        authority = current_authority()
        codex = authority.codex_root.parent
        crypt = authority.crypt_root.parent
        forge = authority.cache_root.parent
        containers = authority.systemd_units.parent
        systemd = authority.systemd_user_units.parent
        return cls(
            codex=codex,
            crypt=crypt,
            forge=forge,
            shared_anchors=frozenset(
                {
                    codex,
                    crypt,
                    forge,
                    containers,
                    authority.systemd_units,
                    systemd,
                    authority.systemd_user_units,
                }
            ),
            routine_anchors=frozenset({containers, systemd}),
        )

    def root(self, tier: HostTier) -> Path | None:
        """Return the XDG root represented by ``tier``."""
        return {
            HostTier.CODEX: self.codex,
            HostTier.CRYPT: self.crypt,
            HostTier.FORGE: self.forge,
            HostTier.HOST: None,
        }[tier]

    def tier_for(self, path: Path) -> HostTier:
        """Classify one path without implying ownership or deletion authority."""
        for tier in HOST_TIER_ORDER:
            root = self.root(tier)
            if root is not None and (path == root or root in path.parents):
                return tier
        return HostTier.HOST


@dataclass
class PathNode[T]:
    """One generic node in a display-only filesystem trie."""

    label: str
    items: list[T] = field(default_factory=list)
    children: dict[str, PathNode[T]] = field(default_factory=dict)


def build_path_trie[T](
    items: Iterable[T],
    *,
    target_of: Callable[[T], Path],
    relative_to: Path | None,
    compact_home: bool = True,
) -> PathNode[T]:
    """Build a deterministic trie without changing the items it projects."""
    root: PathNode[T] = PathNode("")
    for item in sorted(items, key=lambda candidate: str(target_of(candidate))):
        node = root
        for part in display_parts(
            target_of(item),
            relative_to=relative_to,
            compact_home=compact_home,
        ):
            node = node.children.setdefault(part, PathNode(part))
        node.items.append(item)
    return root


def display_parts(
    path: Path,
    *,
    relative_to: Path | None = None,
    compact_home: bool = True,
) -> tuple[str, ...]:
    """Represent a path relative to its tier, or compactly beneath home."""
    if relative_to is not None:
        try:
            relative = path.relative_to(relative_to)
        except ValueError:
            pass
        else:
            return relative.parts
    if path.is_absolute() and compact_home:
        try:
            relative = path.relative_to(Path.home())
        except ValueError:
            pass
        else:
            return ("~", *relative.parts)
    return path.parts or (str(path),)


def display_path(path: Path) -> str:
    """Render one tier root using the compact path grammar."""
    return str(Path(*display_parts(path)))


def path_children[T](node: PathNode[T]) -> tuple[PathNode[T], ...]:
    """Return deterministic, concretely typed children for recursive renderers."""
    return tuple(sorted(node.children.values(), key=lambda item: item.label))


__all__ = (
    "HOST_TIER_ORDER",
    "HostTier",
    "HostTopology",
    "PathNode",
    "build_path_trie",
    "display_parts",
    "display_path",
    "path_children",
)
