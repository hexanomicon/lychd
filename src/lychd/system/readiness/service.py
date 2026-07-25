"""Concurrent composition of independent bounded host-readiness probes."""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Final

import structlog

from lychd.system.constants import (
    PATH_POSTGRESS_DATA_DIR,
    PATH_SYSTEMD_UNITS_DIR,
    PATH_SYSTEMD_USER_UNITS_DIR,
)
from lychd.system.operator.process import ProcessRunner, SubprocessRunner
from lychd.system.readiness.foundation import FoundationReadinessProbe
from lychd.system.readiness.models import (
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

logger = structlog.get_logger()


class HostReadinessService:
    """Inspect required Binding foundations and optional host hardening."""

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        tools: HostReadinessTools | None = None,
        postgres_data: Path = PATH_POSTGRESS_DATA_DIR,
        binding_sites: tuple[tuple[str, str, Path], ...] | None = None,
        selinux_enforce_path: Path = _SELINUX_ENFORCE_PATH,
        cgroup_v2_controllers_path: Path = _CGROUP_V2_CONTROLLERS_PATH,
        current_uid: int | None = None,
    ) -> None:
        """Assemble probes from explicit process, path, and identity dependencies."""
        selected_runner = runner or SubprocessRunner()
        selected_tools = tools or HostReadinessTools.discover()
        selected_uid = os.getuid() if current_uid is None else current_uid
        selected_sites = binding_sites or (
            ("quadlet-sources", "Quadlet sources", PATH_SYSTEMD_UNITS_DIR),
            ("systemd-user-units", "systemd user units", PATH_SYSTEMD_USER_UNITS_DIR),
        )
        foundation = FoundationReadinessProbe(
            runner=selected_runner,
            tools=selected_tools,
            selinux_enforce_path=selinux_enforce_path,
            cgroup_v2_controllers_path=cgroup_v2_controllers_path,
            current_uid=selected_uid,
        )
        storage = StorageReadinessProbe(
            runner=selected_runner,
            tools=selected_tools,
            postgres_data=postgres_data,
        )
        sites = BindingSiteReadinessProbe(
            sites=selected_sites,
            current_uid=selected_uid,
        )
        self._probes: tuple[
            tuple[str, Probe, tuple[HostReadinessItem, ...]],
            ...,
        ] = (
            (
                "systemd",
                lambda: (foundation.systemd(),),
                (self._fallback("systemd-user", "systemd user manager", required=True),),
            ),
            (
                "podman",
                lambda: (foundation.podman_quadlet(),),
                (self._fallback("podman-quadlet", "Podman / Quadlet", required=True),),
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
                    self._fallback("postgres-data", "PostgreSQL data", target=postgres_data),
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
                    for key, label, target in selected_sites
                ),
            ),
        )

    def inspect(self) -> HostReadinessReport:
        """Run bounded probes concurrently, await them, then restore stable order."""
        with ThreadPoolExecutor(
            max_workers=len(self._probes),
            thread_name_prefix="lychd-host-probe",
        ) as pool:
            futures = {
                name: pool.submit(self._safe_probe, name, probe, fallback)
                for name, probe, fallback in self._probes
            }
        return HostReadinessReport(
            items=tuple(
                item
                for name, _probe, _fallback in self._probes
                for item in futures[name].result()
            )
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
