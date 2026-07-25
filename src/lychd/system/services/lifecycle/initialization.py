"""Read-only planning for ``lychd init``."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.system.services.lifecycle._authority import current_authority
from lychd.system.services.lifecycle.models import (
    CreatedResources,
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
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

type InitializationRecorder = Callable[[CreatedResources], None]
type InitializationEffect = Callable[[InitializationRecorder], CreatedResources]


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
            *(inspect_init_file(path, expected_mode=mode, authority=authority) for path, mode in sorted(files.items())),
        ]
        receipt = self._receipt_store.load()
        root_attestation = self._receipt_store.plan_dedicated_root_attestation()
        if root_attestation.disposition is LifecycleDisposition.BLOCKED:
            actions.append(root_attestation)
        elif self._receipt_store.exists:
            if root_attestation.disposition is LifecycleDisposition.PRESERVE:
                actions.append(
                    LifecycleAction(
                        LifecycleDisposition.PRESERVE,
                        LifecycleResourceKind.RECEIPT,
                        str(self._receipt_store.path),
                        (
                            f"valid lifecycle receipt records {len(receipt.directories)} "
                            f"directories, {len(receipt.files)} files, and exact dedicated-root identities"
                        ),
                    )
                )
            else:
                actions.append(root_attestation)
        else:
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.WOULD_CREATE,
                    LifecycleResourceKind.RECEIPT,
                    str(self._receipt_store.path),
                    (
                        "record created resources and deliberately adopt the exact "
                        "dedicated XDG roots as recursively removable only after "
                        "parent-mount verification and device/inode attestation"
                    ),
                )
            )
        return LifecyclePlan.combine(LifecyclePlan(actions=tuple(actions)))


class InitializationExecutor:
    """Consume one exact initialization plan through journaled effect ports."""

    def __init__(
        self,
        *,
        planner: InitializationPlanner,
        receipt: LifecycleReceiptStore,
    ) -> None:
        """Bind execution to the same planner and owner-only receipt authority."""
        self._planner = planner
        self._receipt = receipt

    def execute(
        self,
        approved_plan: LifecyclePlan,
        *,
        effects: Sequence[InitializationEffect],
    ) -> LifecyclePlan:
        """Revalidate, execute only planned creations, seal, and verify convergence."""
        approved_plan.require_executable()
        observed_plan = self._planner.plan()
        if observed_plan != approved_plan:
            msg = (
                "Initialization state changed after planning; inspect a fresh "
                "`lychd init --dry-run` plan before retrying."
            )
            raise LifecycleError(msg)

        allowed_directories = self._creation_paths(
            approved_plan,
            kind=LifecycleResourceKind.DIRECTORY,
        )
        allowed_files = self._creation_paths(
            approved_plan,
            kind=LifecycleResourceKind.FILE,
        )
        receipt_planned = any(
            action.kind is LifecycleResourceKind.RECEIPT
            and Path(action.target) == self._receipt.path
            and action.disposition
            in {
                LifecycleDisposition.WOULD_CREATE,
                LifecycleDisposition.PRESERVE,
            }
            for action in approved_plan.actions
        )
        if not receipt_planned:
            msg = f"Initialization plan does not contain the exact lifecycle receipt authority: {self._receipt.path}"
            raise LifecycleError(msg)

        def record(resources: CreatedResources) -> None:
            unexpected_directories = set(resources.directories) - allowed_directories
            unexpected_files = set(resources.files) - allowed_files
            if unexpected_directories or unexpected_files:
                unexpected = sorted(
                    (*unexpected_directories, *unexpected_files),
                    key=str,
                )
                msg = "Initialization attempted an unplanned creation: " + ", ".join(str(path) for path in unexpected)
                raise LifecycleError(msg)
            self._receipt.record(resources)

        for effect in effects:
            # The callback journals every successful batch immediately. Recording
            # the returned aggregate again also verifies the effect's public report.
            record(effect(record))

        preseal_plan = self._planner.plan()
        self._require_preseal_convergence(preseal_plan)
        self._receipt.seal_dedicated_roots()
        return self._committed_plan(preseal_plan)

    def _require_preseal_convergence(self, plan: LifecyclePlan) -> None:
        """Require complete convergence except for this receipt's final seal."""
        plan.require_executable()
        receipt_actions = tuple(
            action
            for action in plan.actions
            if action.kind is LifecycleResourceKind.RECEIPT and Path(action.target) == self._receipt.path
        )
        if len(receipt_actions) != 1:
            msg = f"Initialization did not converge to one exact lifecycle receipt attestation: {self._receipt.path}"
            raise LifecycleError(msg)
        pending_attestation = receipt_actions[0]
        if pending_attestation.disposition not in {
            LifecycleDisposition.WOULD_CREATE,
            LifecycleDisposition.PRESERVE,
        }:
            msg = f"Initialization lifecycle receipt is not ready for its terminal seal: {self._receipt.path}"
            raise LifecycleError(msg)
        remaining = tuple(
            action
            for action in plan.actions
            if action is not pending_attestation and action.disposition is not LifecycleDisposition.PRESERVE
        )
        if remaining:
            detail = "; ".join(f"{action.target}: {action.detail}" for action in remaining)
            msg = f"Initialization did not converge: {detail}"
            raise LifecycleError(msg)

    def _committed_plan(self, preseal_plan: LifecyclePlan) -> LifecyclePlan:
        """Project the successful terminal seal without another fallible host read."""
        actions = tuple(
            LifecycleAction(
                LifecycleDisposition.PRESERVE,
                action.kind,
                action.target,
                "dedicated-root authority was sealed by successful initialization",
            )
            if (
                action.kind is LifecycleResourceKind.RECEIPT
                and Path(action.target) == self._receipt.path
                and action.disposition is LifecycleDisposition.WOULD_CREATE
            )
            else action
            for action in preseal_plan.actions
        )
        return LifecyclePlan.combine(LifecyclePlan(actions=actions))

    @staticmethod
    def _creation_paths(
        plan: LifecyclePlan,
        *,
        kind: LifecycleResourceKind,
    ) -> set[Path]:
        """Return exact absolute creation targets of one filesystem kind."""
        return {
            Path(action.target)
            for action in plan.actions
            if action.disposition is LifecycleDisposition.WOULD_CREATE
            and action.kind is kind
            and Path(action.target).is_absolute()
        }
