"""Read-only projection of the shared binding-site authority law."""

from __future__ import annotations

from pathlib import Path

from lychd.system.binding_sites import (
    BindingSiteState,
    inspect_binding_site,
)
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
        return tuple(self._inspect_site(key=key, label=label, target=target) for key, label, target in self._sites)

    def _inspect_site(
        self,
        *,
        key: str,
        label: str,
        target: Path,
    ) -> HostReadinessItem:
        inspection = inspect_binding_site(
            target,
            current_uid=self._current_uid,
        )
        if inspection.state is BindingSiteState.BLOCKED:
            return self._failed(
                key=key,
                label=label,
                target=target,
                detail=inspection.detail,
            )
        return HostReadinessItem(
            key=key,
            label=label,
            section=ReadinessSection.BINDING_SITES,
            state=(
                ReadinessState.VERIFIED if inspection.state is BindingSiteState.PREPARED else ReadinessState.PLANNED
            ),
            detail=inspection.detail,
            required_for_bind=True,
            repairable_by_init=inspection.state is BindingSiteState.CREATABLE,
            target=target,
            site_identity=inspection.identity,
        )

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
