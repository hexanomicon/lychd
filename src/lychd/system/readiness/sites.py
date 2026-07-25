"""Read-only verification of initialization-owned Binding preparation."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from lychd.system.path_safety import path_has_symlink_component
from lychd.system.readiness.models import (
    HostReadinessItem,
    ReadinessSection,
    ReadinessState,
)


class BindingSiteReadinessProbe:
    """Verify exact shared directories without granting namespace ownership."""

    def __init__(
        self,
        *,
        sites: tuple[tuple[str, str, Path], ...],
        current_uid: int,
    ) -> None:
        """Bind inspection to exact site identities and current user."""
        self._sites = sites
        self._current_uid = current_uid

    def inspect(self) -> tuple[HostReadinessItem, ...]:
        """Return one stable result for each required Binding site."""
        return tuple(
            self._inspect_site(key=key, label=label, target=target)
            for key, label, target in self._sites
        )

    def _inspect_site(
        self,
        *,
        key: str,
        label: str,
        target: Path,
    ) -> HostReadinessItem:
        if symlink := path_has_symlink_component(target):
            return self._failed(
                key=key,
                label=label,
                target=target,
                detail=f"symlink component is not trusted: {symlink}",
            )
        if os.path.lexists(target):
            metadata = target.lstat()
            if not stat.S_ISDIR(metadata.st_mode):
                detail = "target exists but is not a directory"
            elif metadata.st_uid != self._current_uid:
                detail = f"owned by uid {metadata.st_uid}, expected {self._current_uid}"
            elif not os.access(target, os.W_OK | os.X_OK):
                detail = "present but not writable and searchable"
            else:
                return HostReadinessItem(
                    key=key,
                    label=label,
                    section=ReadinessSection.BINDING_SITES,
                    state=ReadinessState.VERIFIED,
                    detail="prepared",
                    required_for_bind=True,
                    target=target,
                )
            return self._failed(key=key, label=label, target=target, detail=detail)

        parent = self._nearest_existing(target.parent)
        try:
            parent_metadata = parent.stat()
        except OSError as exc:
            detail = f"cannot inspect creation parent: {' '.join(str(exc).split())[:240]}"
        else:
            if not stat.S_ISDIR(parent_metadata.st_mode):
                detail = f"creation parent is not a directory: {parent}"
            elif not os.access(parent, os.W_OK | os.X_OK):
                detail = f"creation parent is not writable and searchable: {parent}"
            else:
                return HostReadinessItem(
                    key=key,
                    label=label,
                    section=ReadinessSection.BINDING_SITES,
                    state=ReadinessState.PLANNED,
                    detail="will prepare",
                    required_for_bind=True,
                    target=target,
                )
        return self._failed(key=key, label=label, target=target, detail=detail)

    @staticmethod
    def _nearest_existing(path: Path) -> Path:
        candidate = path
        while not candidate.exists() and candidate != candidate.parent:
            candidate = candidate.parent
        return candidate

    @staticmethod
    def _failed(
        *,
        key: str,
        label: str,
        target: Path,
        detail: str,
    ) -> HostReadinessItem:
        return HostReadinessItem.failed(
            key=key,
            label=label,
            detail=detail,
            required=True,
            section=ReadinessSection.BINDING_SITES,
            target=target,
        )


__all__ = ("BindingSiteReadinessProbe",)
