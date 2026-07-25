"""Exact Scribe-owned unit discovery and bounded systemd observation."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.system.operator.models import ObservationState, OwnedUnit, OwnedUnitCatalog
from lychd.system.operator.process import ProcessInvocationError, ProcessRunner

if TYPE_CHECKING:
    from lychd.system.services.scribe import ScribeService

_SYSTEMCTL_TIMEOUT_SECONDS = 3.0


class OwnedUnitInventoryService:
    """Project Scribe authority into exact runtime units and observed state."""

    def __init__(
        self,
        scribe: ScribeService,
        runner: ProcessRunner,
        *,
        systemctl_bin: str | None,
    ) -> None:
        """Bind the exact ownership source and read-only systemd adapter."""
        self._scribe = scribe
        self._runner = runner
        self._systemctl = systemctl_bin

    def inspect(self) -> OwnedUnitCatalog:
        """Return exact owned units; invalid authority becomes an explicit warning."""
        try:
            bindings = self._scribe.inspect_owned_bindings()
        except Exception as exc:  # noqa: BLE001 - status must survive corrupt local authority
            return OwnedUnitCatalog(
                receipt_present=True,
                warning=f"Cannot validate Scribe ownership: {exc}",
            )
        if not bindings.receipt_present:
            return OwnedUnitCatalog(receipt_present=False)

        sources_by_unit: defaultdict[str, list[str]] = defaultdict(list)
        for source in (*bindings.quadlet_sources, *bindings.systemd_sources):
            unit = self._unit_for_source(source)
            if unit is not None:
                sources_by_unit[unit].append(str(source))

        units = tuple(
            self._observe_unit(name, tuple(sorted(sources_by_unit.get(name, ())))) for name in bindings.runtime_units
        )
        return OwnedUnitCatalog(
            receipt_present=True,
            units=units,
            generation=bindings.generation,
        )

    @staticmethod
    def _unit_for_source(source: Path) -> str | None:
        suffix = source.suffix
        if suffix == ".container":
            return f"{source.stem}.service"
        if suffix == ".pod":
            return f"{source.stem}-pod.service"
        if suffix in {".target", ".service", ".path"}:
            return source.name
        return None

    def _observe_unit(self, unit: str, sources: tuple[str, ...]) -> OwnedUnit:
        if self._systemctl is None:
            return OwnedUnit(
                name=unit,
                sources=sources,
                detail="systemctl is unavailable",
            )
        argv = (
            self._systemctl,
            "--user",
            "show",
            unit,
            "--property=LoadState",
            "--property=ActiveState",
            "--property=UnitFileState",
        )
        try:
            result = self._runner.run(argv, timeout_s=_SYSTEMCTL_TIMEOUT_SECONDS)
        except ProcessInvocationError as exc:
            return OwnedUnit(name=unit, sources=sources, detail=f"systemd probe failed: {exc}")
        if result.returncode != 0:
            detail = result.stderr.strip() or f"systemctl exited {result.returncode}"
            return OwnedUnit(name=unit, sources=sources, detail=detail)

        fields = self._parse_show(result.stdout)
        active = fields.get("ActiveState")
        states: dict[str, ObservationState] = {
            "active": ObservationState.ACTIVE,
            "activating": ObservationState.ACTIVE,
            "reloading": ObservationState.ACTIVE,
            "inactive": ObservationState.INACTIVE,
            "deactivating": ObservationState.ACTIVE,
            "failed": ObservationState.FAILED,
        }
        state = states.get(active, ObservationState.UNKNOWN) if active is not None else ObservationState.UNKNOWN
        load_state = fields.get("LoadState", "unknown")
        detail = "" if load_state == "loaded" else f"load state: {load_state}"
        return OwnedUnit(
            name=unit,
            sources=sources,
            state=state,
            unit_file_state=fields.get("UnitFileState", "unknown"),
            detail=detail,
        )

    @staticmethod
    def _parse_show(content: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for line in content.splitlines():
            key, separator, value = line.partition("=")
            if separator and key not in fields:
                fields[key] = value
        return fields
