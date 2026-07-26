"""Pure construction and validation of Scribe binding write sets."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from lychd.system.binding_sites import BindingSites
from lychd.system.schemas import QuadletBase
from lychd.system.services.scribe.authority import BindingAuthority
from lychd.system.services.scribe.errors import ScribeConflictError, ScribeOwnershipError
from lychd.system.services.scribe.models import (
    BindingBase,
    BindingChange,
    BindingReconcilePlan,
    BindingWriteSet,
    OwnershipManifest,
    SitePlan,
)
from lychd.system.services.scribe.naming import (
    GENERATED_SYSTEMD_SUFFIXES,
    encode_plain_units,
)
from lychd.system.services.scribe.rendering import BindingRenderer
from lychd.system.services.scribe.storage import capture_path_state


def validate_plans(plans: Sequence[SitePlan]) -> None:
    """Prove every affected live path is inside the exact authority set."""
    for plan in plans:
        if not plan.previous_names <= plan.owned_names:
            msg = "Scribe transaction attempted to replace a filename it does not own."
            raise ScribeOwnershipError(msg)

        for name in plan.owned_names:
            target = plan.directory / name
            state = capture_path_state(target)
            if state is not None and state.content is None:
                msg = f"Owned unit path is not a regular file: {target}."
                raise ScribeOwnershipError(msg)

        for name in plan.files:
            target = plan.directory / name
            if capture_path_state(target) is not None and name not in plan.owned_names:
                msg = f"Refusing to overwrite unowned binding-site path: {target}."
                raise ScribeConflictError(msg)


class BindingPlanner:
    """Build exact desired file sets without mutating either binding site."""

    def __init__(
        self,
        *,
        sites: BindingSites,
        renderer: BindingRenderer,
        authority: BindingAuthority,
    ) -> None:
        """Compose the read-only collaborators used to derive write sets."""
        self._sites = sites
        self._renderer = renderer
        self._authority = authority

    def generated(self, manifests: Sequence[QuadletBase]) -> BindingWriteSet:
        """Plan generated units while preserving independently managed plain units."""
        base = self._observe_base()
        previous = base.ownership
        quadlet_files, systemd_files = self._renderer.render_generated(manifests)
        previous_targets = frozenset(
            name for name in previous.systemd if Path(name).suffix in GENERATED_SYSTEMD_SUFFIXES
        )
        preserved_plain_units = set(previous.systemd) - set(previous_targets)
        next_ownership = OwnershipManifest(
            version=1,
            quadlet=tuple(sorted(quadlet_files)),
            systemd=tuple(sorted(preserved_plain_units | set(systemd_files))),
        )
        return BindingWriteSet(
            plans=(
                SitePlan(
                    directory=self._sites.quadlet,
                    owned_names=frozenset(previous.quadlet),
                    previous_names=frozenset(previous.quadlet),
                    files=quadlet_files,
                ),
                SitePlan(
                    directory=self._sites.systemd_user,
                    owned_names=frozenset(previous.systemd),
                    previous_names=previous_targets,
                    files=systemd_files,
                ),
            ),
            ownership=next_ownership,
            base=base,
        )

    def complete(
        self,
        manifests: Sequence[QuadletBase],
        *,
        plain_units: Mapping[str, str],
    ) -> BindingWriteSet:
        """Plan one complete generated and plain desired binding state."""
        plain_files = encode_plain_units(plain_units)
        base = self._observe_base()
        previous = base.ownership
        quadlet_files, generated_systemd_files = self._renderer.render_generated(manifests)
        systemd_files = {**generated_systemd_files, **plain_files}
        next_ownership = OwnershipManifest(
            version=1,
            quadlet=tuple(sorted(quadlet_files)),
            systemd=tuple(sorted(systemd_files)),
        )
        return BindingWriteSet(
            plans=(
                SitePlan(
                    directory=self._sites.quadlet,
                    owned_names=frozenset(previous.quadlet),
                    previous_names=frozenset(previous.quadlet),
                    files=quadlet_files,
                ),
                SitePlan(
                    directory=self._sites.systemd_user,
                    owned_names=frozenset(previous.systemd),
                    previous_names=frozenset(previous.systemd),
                    files=systemd_files,
                ),
            ),
            ownership=next_ownership,
            base=base,
        )

    def plain_unit(self, filename: str, file: Mapping[str, bytes]) -> BindingWriteSet:
        """Plan replacement of one plain user unit while preserving every peer."""
        base = self._observe_base()
        previous = base.ownership
        next_ownership = OwnershipManifest(
            version=1,
            quadlet=tuple(sorted(previous.quadlet)),
            systemd=tuple(sorted({*previous.systemd, filename})),
        )
        return BindingWriteSet(
            plans=(
                SitePlan(
                    directory=self._sites.quadlet,
                    owned_names=frozenset(previous.quadlet),
                    previous_names=frozenset(),
                    files={},
                ),
                SitePlan(
                    directory=self._sites.systemd_user,
                    owned_names=frozenset(previous.systemd),
                    previous_names=frozenset({filename}) if filename in previous.systemd else frozenset(),
                    files=file,
                ),
            ),
            ownership=next_ownership,
            base=base,
        )

    def removal(
        self,
        *,
        include_systemd: bool,
        release_authority: bool,
    ) -> BindingWriteSet:
        """Plan exact source removal without assuming a missing site can be recreated."""
        base = self._observe_base()
        previous = base.ownership
        next_ownership = OwnershipManifest(version=1) if release_authority else previous
        plans = [
            SitePlan(
                directory=self._sites.quadlet,
                owned_names=frozenset(previous.quadlet),
                previous_names=frozenset(previous.quadlet),
                files={},
            )
        ]
        if include_systemd:
            plans.append(
                SitePlan(
                    directory=self._sites.systemd_user,
                    owned_names=frozenset(previous.systemd),
                    previous_names=frozenset(previous.systemd),
                    files={},
                )
            )
        return BindingWriteSet(
            plans=tuple(plans),
            ownership=next_ownership,
            base=base,
        )

    def preview(self, write_set: BindingWriteSet) -> BindingReconcilePlan:
        """Classify the exact filesystem effects of one complete write set."""
        validate_plans(write_set.plans)
        changes: list[BindingChange] = []
        for plan in write_set.plans:
            changes.extend(self._site_changes(plan))
        changes.append(self._ownership_change(write_set.ownership))
        return BindingReconcilePlan(
            changes=tuple(changes),
            observed_generation=write_set.base.generation,
            desired_generation=self._authority.desired_generation(write_set),
        )

    @staticmethod
    def _site_changes(plan: SitePlan) -> list[BindingChange]:
        """Classify one binding site's exact desired-fileset transition."""
        changes: list[BindingChange] = []
        for name, content in sorted(plan.files.items()):
            target = plan.directory / name
            state = capture_path_state(target)
            if state is None:
                changes.append(BindingChange("create", target, "desired binding is absent"))
            elif state.content is None:
                msg = f"Owned unit path is not a regular file: {target}."
                raise ScribeOwnershipError(msg)
            elif state.content == content:
                changes.append(BindingChange("preserve", target, "binding already matches intent"))
            else:
                changes.append(BindingChange("update", target, "owned binding differs from intent"))
        for name in sorted(plan.previous_names - frozenset(plan.files)):
            target = plan.directory / name
            if capture_path_state(target) is not None:
                changes.append(BindingChange("remove", target, "stale owned binding"))
        return changes

    def _observe_base(self) -> BindingBase:
        """Capture exact receipt bytes and every source named by that receipt."""
        authority, ownership = self._authority.snapshot()
        sources = (
            *(self._sites.quadlet / name for name in ownership.quadlet),
            *(self._sites.systemd_user / name for name in ownership.systemd),
        )
        return BindingBase(
            authority=authority,
            ownership=ownership,
            sources=tuple(sources),
            generation=self._authority.generation(
                authority=authority,
                sources=tuple(sources),
            ),
        )

    def _ownership_change(self, ownership: OwnershipManifest) -> BindingChange:
        """Classify the authority receipt written by the transaction."""
        ownership_content = self._authority.encode(ownership)
        if not os.path.lexists(self._authority.path):
            return BindingChange("create", self._authority.path, "binding ownership receipt is absent")
        if self._authority.read() == ownership_content:
            return BindingChange("preserve", self._authority.path, "binding ownership already matches")
        return BindingChange("update", self._authority.path, "binding ownership differs from intent")
