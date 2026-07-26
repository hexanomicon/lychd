"""Concurrent composition of independent bounded host-readiness probes."""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Final

import structlog

from lychd.system.binding_sites import DEFAULT_BINDING_SITES
from lychd.system.constants import (
    PATH_POSTGRESS_DATA_DIR,
)
from lychd.system.host_foundation import (
    PODMAN_QUADLET_READINESS_KEY,
    QUADLET_SOURCES_READINESS_KEY,
    SYSTEMD_USER_READINESS_KEY,
    SYSTEMD_USER_UNITS_READINESS_KEY,
)
from lychd.system.operator.process import ProcessRunner, SubprocessRunner
from lychd.system.readiness.foundation import FoundationReadinessProbe
from lychd.system.readiness.models import (
    HostFoundationInspection,
    HostReadinessItem,
    HostReadinessReport,
    ReadinessSection,
)
from lychd.system.readiness.sites import BindingSiteReadinessProbe
from lychd.system.readiness.storage import StorageReadinessProbe
from lychd.system.readiness.tools import HostReadinessTools

_SELINUX_ENFORCE_PATH: Final = Path("/sys/fs/selinux/enforce")
_CGROUP_V2_CONTROLLERS_PATH: Final = Path("/sys/fs/cgroup/cgroup.controllers")

type Probe = Callable[[], tuple[HostReadinessItem, ...]]
type ToolsFactory = Callable[[], HostReadinessTools]

logger = structlog.get_logger()


class HostReadinessService:
    """Inspect required Binding foundations and optional host hardening."""

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        tools: HostReadinessTools | None = None,
        tools_factory: ToolsFactory = HostReadinessTools.discover,
        postgres_data: Path = PATH_POSTGRESS_DATA_DIR,
        binding_sites: tuple[tuple[str, str, Path], ...] | None = None,
        selinux_enforce_path: Path = _SELINUX_ENFORCE_PATH,
        cgroup_v2_controllers_path: Path = _CGROUP_V2_CONTROLLERS_PATH,
        current_uid: int | None = None,
    ) -> None:
        """Retain dependencies used to assemble one fresh immutable snapshot."""
        self._runner = runner or SubprocessRunner()
        self._injected_tools = tools
        self._tools_factory = tools_factory
        self._postgres_data = postgres_data
        self._binding_sites = binding_sites or (
            (
                QUADLET_SOURCES_READINESS_KEY,
                "Quadlet sources",
                DEFAULT_BINDING_SITES.quadlet,
            ),
            (
                SYSTEMD_USER_UNITS_READINESS_KEY,
                "systemd user units",
                DEFAULT_BINDING_SITES.systemd_user,
            ),
        )
        self._selinux_enforce_path = selinux_enforce_path
        self._cgroup_v2_controllers_path = cgroup_v2_controllers_path
        self._current_uid = os.getuid() if current_uid is None else current_uid

    def inspect(self) -> HostFoundationInspection:
        """Discover tools, run one bounded probe graph, and return its snapshot."""
        tools = self._injected_tools if self._injected_tools is not None else self._tools_factory()
        probes = self._build_probes(tools)
        with ThreadPoolExecutor(
            max_workers=len(probes),
            thread_name_prefix="lychd-host-probe",
        ) as pool:
            futures = {name: pool.submit(self._safe_probe, name, probe, fallback) for name, probe, fallback in probes}
        return HostFoundationInspection(
            report=HostReadinessReport(
                items=tuple(item for name, _probe, _fallback in probes for item in futures[name].result()),
            ),
            tools=tools,
        )

    def _build_probes(
        self,
        tools: HostReadinessTools,
    ) -> tuple[
        tuple[str, Probe, tuple[HostReadinessItem, ...]],
        ...,
    ]:
        """Bind every probe in one inspection to the same discovered tools."""
        foundation = FoundationReadinessProbe(
            runner=self._runner,
            tools=tools,
            selinux_enforce_path=self._selinux_enforce_path,
            cgroup_v2_controllers_path=self._cgroup_v2_controllers_path,
            current_uid=self._current_uid,
        )
        storage = StorageReadinessProbe(
            runner=self._runner,
            tools=tools,
            postgres_data=self._postgres_data,
        )
        sites = BindingSiteReadinessProbe(
            sites=self._binding_sites,
            current_uid=self._current_uid,
        )
        return (
            (
                "systemd",
                lambda: (foundation.systemd(),),
                (
                    self._fallback(
                        SYSTEMD_USER_READINESS_KEY,
                        "systemd user manager",
                        required=True,
                    ),
                ),
            ),
            (
                "podman",
                lambda: (foundation.podman_quadlet(),),
                (
                    self._fallback(
                        PODMAN_QUADLET_READINESS_KEY,
                        "Podman / Quadlet",
                        required=True,
                    ),
                ),
            ),
            (
                "selinux",
                lambda: (foundation.selinux(),),
                (self._fallback("selinux", "SELinux"),),
            ),
            (
                "storage",
                storage.inspect,
                (
                    self._fallback("btrfs", "Btrfs"),
                    self._fallback(
                        "postgres-data",
                        "PostgreSQL data",
                        target=self._postgres_data,
                    ),
                ),
            ),
            (
                "sites",
                sites.inspect,
                tuple(
                    self._fallback(
                        key,
                        label,
                        required=True,
                        section=ReadinessSection.BINDING_SITES,
                        target=target,
                    )
                    for key, label, target in self._binding_sites
                ),
            ),
        )

    @staticmethod
    def _safe_probe(
        name: str,
        probe: Probe,
        fallback: tuple[HostReadinessItem, ...],
    ) -> tuple[HostReadinessItem, ...]:
        try:
            return probe()
        except Exception as exc:  # noqa: BLE001 - observation may never crash init
            logger.warning(
                "host_readiness_probe_failed",
                probe=name,
                error_type=type(exc).__name__,
            )
            return fallback

    @staticmethod
    def _fallback(
        key: str,
        label: str,
        *,
        required: bool = False,
        section: ReadinessSection = ReadinessSection.FOUNDATION,
        target: Path | None = None,
    ) -> HostReadinessItem:
        return HostReadinessItem.failed(
            key=key,
            label=label,
            detail="probe failed unexpectedly",
            required=required,
            section=section,
            target=target,
        )


__all__ = ("HostReadinessService",)
