from __future__ import annotations

from io import StringIO
from pathlib import Path

from rich.console import Console

from lychd.cli.readiness_view import (
    render_host_readiness,
    render_readiness_changes,
)
from lychd.system.readiness import (
    HostReadinessItem,
    HostReadinessReport,
    ReadinessSection,
    ReadinessState,
)


def _render(report: HostReadinessReport) -> str:
    stream = StringIO()
    render_host_readiness(
        report=report,
        console=Console(file=stream, color_system=None, width=120),
    )
    return stream.getvalue()


def _report(*, site_state: ReadinessState) -> HostReadinessReport:
    return HostReadinessReport(
        items=(
            HostReadinessItem(
                key="systemd",
                label="systemd user manager",
                section=ReadinessSection.FOUNDATION,
                state=ReadinessState.VERIFIED,
                detail="reachable",
                required_for_bind=True,
            ),
            HostReadinessItem(
                key="selinux",
                label="SELinux",
                section=ReadinessSection.FOUNDATION,
                state=ReadinessState.DEGRADED,
                detail="permissive",
            ),
            HostReadinessItem(
                key="site",
                label="Quadlet sources",
                section=ReadinessSection.BINDING_SITES,
                state=site_state,
                detail="will be prepared" if site_state is ReadinessState.PLANNED else "prepared",
                required_for_bind=True,
                target=Path.home() / ".config" / "containers" / "systemd",
            ),
        )
    )


def test_readiness_panel_separates_verified_planned_and_degraded_facts() -> None:
    output = _render(_report(site_state=ReadinessState.PLANNED))

    assert "HOST FOUNDATION" in output
    assert "✓ systemd user manager — reachable" in output
    assert "! SELinux — permissive" in output
    assert "BINDING SITES" in output
    assert "◌ Quadlet sources — ~/.config/containers/systemd · will be prepared" in output
    assert "BIND   ◌ host foundation ready · binding sites will be prepared" in output


def test_post_init_projection_prints_only_changed_facts_and_ready_verdict() -> None:
    stream = StringIO()
    render_readiness_changes(
        before=_report(site_state=ReadinessState.PLANNED),
        after=_report(site_state=ReadinessState.VERIFIED),
        console=Console(file=stream, color_system=None, width=120),
    )
    output = stream.getvalue()

    assert "AFTER INITIALIZATION" in output
    assert "✓ Quadlet sources" in output
    assert "systemd user manager" not in output
    assert "BIND   ✓ host foundation and binding sites ready" in output
