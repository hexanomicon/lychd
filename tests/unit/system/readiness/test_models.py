from __future__ import annotations

from pathlib import Path

import pytest

from lychd.system.binding_sites import AttestedBindingSite
from lychd.system.host_foundation import (
    PODMAN_QUADLET_READINESS_KEY,
    QUADLET_SOURCES_READINESS_KEY,
    SYSTEMD_USER_READINESS_KEY,
    SYSTEMD_USER_UNITS_READINESS_KEY,
)
from lychd.system.host_tools import TrustedExecutable
from lychd.system.readiness import (
    HostFoundationError,
    HostFoundationInspection,
    HostReadinessItem,
    HostReadinessReport,
    HostReadinessTools,
    ReadinessSection,
    ReadinessState,
)


def _item(
    key: str,
    state: ReadinessState,
    *,
    required: bool,
    target: Path | None = None,
    site_identity: AttestedBindingSite | None = None,
) -> HostReadinessItem:
    return HostReadinessItem(
        key=key,
        label=key,
        section=ReadinessSection.FOUNDATION,
        state=state,
        detail=state.value,
        required_for_bind=required,
        repairable_by_init=state is ReadinessState.PLANNED,
        target=target,
        site_identity=site_identity,
    )


@pytest.mark.parametrize(
    ("items", "ready_for_bind", "ready_after_init"),
    [
        (
            (
                _item("systemd", ReadinessState.VERIFIED, required=True),
                _item("podman", ReadinessState.VERIFIED, required=True),
                _item("selinux", ReadinessState.OPTIONAL, required=False),
                _item("btrfs", ReadinessState.DEGRADED, required=False),
            ),
            True,
            True,
        ),
        (
            (
                _item("systemd", ReadinessState.VERIFIED, required=True),
                _item("quadlet-site", ReadinessState.PLANNED, required=True),
            ),
            False,
            True,
        ),
        (
            (
                _item("systemd", ReadinessState.BLOCKED, required=True),
                _item("quadlet-site", ReadinessState.PLANNED, required=True),
            ),
            False,
            False,
        ),
        (
            (
                HostReadinessItem(
                    key="future-host-law",
                    label="future host law",
                    section=ReadinessSection.FOUNDATION,
                    state=ReadinessState.PLANNED,
                    detail="planned",
                    required_for_bind=True,
                ),
            ),
            False,
            False,
        ),
    ],
)
def test_bind_readiness_depends_only_on_required_verified_or_repairable_items(
    items: tuple[HostReadinessItem, ...],
    *,
    ready_for_bind: bool,
    ready_after_init: bool,
) -> None:
    report = HostReadinessReport(items=items)

    assert report.ready_for_bind is ready_for_bind
    assert report.ready_after_init is ready_after_init


def _tools() -> HostReadinessTools:
    return HostReadinessTools(
        systemctl=TrustedExecutable(path="/systemctl", device=1, inode=1),
        podman=TrustedExecutable(path="/podman", device=1, inode=2),
        quadlet_user_generator=TrustedExecutable(
            path="/quadlet",
            device=1,
            inode=3,
        ),
        findmnt=None,
        btrfs=None,
        chattr=None,
        lsattr=None,
        getenforce=None,
    )


def _verified_binding_gates(tmp_path: Path) -> tuple[HostReadinessItem, ...]:
    systemd = AttestedBindingSite(
        path=tmp_path / "systemd",
        device=1,
        inode=4,
    )
    quadlet = AttestedBindingSite(
        path=tmp_path / "quadlet",
        device=1,
        inode=5,
    )
    return (
        _item(
            SYSTEMD_USER_UNITS_READINESS_KEY,
            ReadinessState.VERIFIED,
            required=True,
            target=systemd.path,
            site_identity=systemd,
        ),
        _item(
            PODMAN_QUADLET_READINESS_KEY,
            ReadinessState.VERIFIED,
            required=True,
        ),
        _item(
            QUADLET_SOURCES_READINESS_KEY,
            ReadinessState.VERIFIED,
            required=True,
            target=quadlet.path,
            site_identity=quadlet,
        ),
        _item(
            SYSTEMD_USER_READINESS_KEY,
            ReadinessState.VERIFIED,
            required=True,
        ),
    )


def test_foundation_refinement_uses_named_gates_not_report_order(
    tmp_path: Path,
) -> None:
    inspection = HostFoundationInspection(
        report=HostReadinessReport(
            items=tuple(reversed(_verified_binding_gates(tmp_path))),
        ),
        tools=_tools(),
    )

    foundation = inspection.require_ready_for_bind()

    assert foundation.sites.quadlet.path == tmp_path / "quadlet"
    assert foundation.sites.systemd_user.path == tmp_path / "systemd"


def test_foundation_refinement_rejects_any_unverified_required_gate(
    tmp_path: Path,
) -> None:
    inspection = HostFoundationInspection(
        report=HostReadinessReport(
            items=(
                *_verified_binding_gates(tmp_path),
                _item(
                    "future-required-gate",
                    ReadinessState.BLOCKED,
                    required=True,
                ),
            ),
        ),
        tools=_tools(),
    )

    with pytest.raises(
        HostFoundationError,
        match="future-required-gate",
    ):
        inspection.require_ready_for_bind()
