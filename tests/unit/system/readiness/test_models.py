from __future__ import annotations

from lychd.system.readiness import (
    HostReadinessItem,
    HostReadinessReport,
    ReadinessSection,
    ReadinessState,
)


def _item(
    key: str,
    state: ReadinessState,
    *,
    required: bool,
) -> HostReadinessItem:
    return HostReadinessItem(
        key=key,
        label=key,
        section=ReadinessSection.FOUNDATION,
        state=state,
        detail=state.value,
        required_for_bind=required,
    )


def test_optional_hardening_does_not_block_bind_foundation() -> None:
    report = HostReadinessReport(
        items=(
            _item("systemd", ReadinessState.VERIFIED, required=True),
            _item("podman", ReadinessState.VERIFIED, required=True),
            _item("selinux", ReadinessState.OPTIONAL, required=False),
            _item("btrfs", ReadinessState.DEGRADED, required=False),
        )
    )

    assert report.ready_for_bind
    assert report.ready_after_init


def test_planned_required_site_is_ready_only_after_initialization() -> None:
    report = HostReadinessReport(
        items=(
            _item("systemd", ReadinessState.VERIFIED, required=True),
            _item("quadlet-site", ReadinessState.PLANNED, required=True),
        )
    )

    assert not report.ready_for_bind
    assert report.ready_after_init


def test_blocked_required_foundation_cannot_be_repaired_by_init() -> None:
    report = HostReadinessReport(
        items=(
            _item("systemd", ReadinessState.BLOCKED, required=True),
            _item("quadlet-site", ReadinessState.PLANNED, required=True),
        )
    )

    assert not report.ready_for_bind
    assert not report.ready_after_init
