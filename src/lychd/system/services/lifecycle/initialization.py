"""Read-only planning for ``lychd init``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.system.services.lifecycle._authority import current_authority
from lychd.system.services.lifecycle.models import (
    LifecycleAction,
    LifecycleDisposition,
    LifecyclePlan,
    LifecycleResourceKind,
)
from lychd.system.services.lifecycle.paths import (
    inspect_init_directory,
    inspect_init_file,
    is_within,
)

if TYPE_CHECKING:
    from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore


class InitializationPlanner:
    """Build the complete read-only plan consumed by ``lychd init``."""

    def __init__(
        self,
        *,
        reactor_directories: Sequence[Path],
        anchor_paths: Sequence[Path],
        sample_paths: Sequence[Path],
        receipt_store: LifecycleReceiptStore | None = None,
    ) -> None:
        """Capture the assembled initialization topology."""
        if receipt_store is None:
            from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore

            receipt_store = LifecycleReceiptStore()
        self._reactor_directories = tuple(reactor_directories)
        self._anchor_paths = tuple(anchor_paths)
        self._sample_paths = tuple(sample_paths)
        self._receipt_store = receipt_store

    def plan(self) -> LifecyclePlan:
        """Inspect every initialization target without performing an effect."""
        authority = current_authority()
        directory_modes = dict.fromkeys(self._reactor_directories, 0o700)
        reactor_directories: set[Path] = set()
        for target in self._reactor_directories:
            reactor_directories.add(target)
            current = target.parent
            while is_within(current, authority.crypt_root):
                reactor_directories.add(current)
                if current == authority.crypt_root:
                    break
                current = current.parent
        anchor_directories: set[Path] = set()
        for anchor in self._anchor_paths:
            current = anchor
            while is_within(current, authority.runes):
                anchor_directories.add(current)
                if current == authority.runes:
                    break
                current = current.parent
        directories = {
            *authority.host_layout,
            *reactor_directories,
            *anchor_directories,
            *(path.parent for path in self._sample_paths),
            authority.codex_root.parent,
            authority.crypt_root.parent,
            authority.cache_root.parent,
            authority.systemd_units.parent,
            authority.systemd_user_units.parent,
        }
        files: dict[Path, int] = {
            authority.lychd_toml: 0o600,
            authority.postgres_root / "init_db.sh": 0o755,
        }
        files.update(dict.fromkeys(self._sample_paths, 0o600))
        actions = [
            *(
                inspect_init_directory(
                    path,
                    expected_mode=directory_modes.get(path),
                    authority=authority,
                )
                for path in sorted(directories, key=lambda item: (len(item.parts), str(item)))
            ),
            *(
                inspect_init_file(path, expected_mode=mode, authority=authority)
                for path, mode in sorted(files.items())
            ),
        ]
        receipt = self._receipt_store.load()
        if self._receipt_store.exists:
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.PRESERVE,
                    LifecycleResourceKind.RECEIPT,
                    str(self._receipt_store.path),
                    f"valid lifecycle receipt records {len(receipt.directories)} directories and {len(receipt.files)} files",
                )
            )
        else:
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.WOULD_CREATE,
                    LifecycleResourceKind.RECEIPT,
                    str(self._receipt_store.path),
                    "record exact resources created by initialization",
                )
            )
        return LifecyclePlan.combine(LifecyclePlan(actions=tuple(actions)))
