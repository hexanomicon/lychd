"""Whole-system status projection over exact local authority."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from lychd.system.operator.models import (
    DeclaredAnimator,
    InventoryItem,
    InventoryReport,
    ObservationState,
    OperatorTarget,
    OwnedUnit,
    OwnedUnitCatalog,
    SystemSummary,
)
from lychd.system.operator.storage import StorageInventoryService
from lychd.system.operator.units import OwnedUnitInventoryService

if TYPE_CHECKING:
    from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore


@dataclass(frozen=True)
class OperatorPaths:
    """Filesystem locations observed by the bootstrap-safe operator surface."""

    codex_root: Path
    config: Path
    receipt: Path
    runes: Path
    bindings: Path
    systemd_bindings: Path
    storage_data: Path
    snapshots: Path

    @classmethod
    def current(cls) -> OperatorPaths:
        """Read current XDG-derived project constants at service construction."""
        from lychd.system import constants

        return cls(
            codex_root=constants.PATH_CODEX_ROOT,
            config=constants.PATH_LYCHD_TOML,
            receipt=constants.PATH_LIFECYCLE_RECEIPT,
            runes=constants.PATH_RUNES_DIR,
            bindings=constants.PATH_SYSTEMD_UNITS_DIR,
            systemd_bindings=constants.PATH_SYSTEMD_USER_UNITS_DIR,
            storage_data=constants.PATH_POSTGRESS_DATA_DIR,
            snapshots=constants.PATH_POSTGRESS_SNAPSHOTS_DIR,
        )


class AnimatorDeclarationProvider(Protocol):
    """Lazy declaration source used only by ``status animators``."""

    def declarations(self) -> tuple[DeclaredAnimator, ...]:
        """Return typed local and remote Animator declarations."""
        ...


class ConfiguredAnimatorDeclarations:
    """Load declaration truth without constructing the ASGI application."""

    def __init__(self, *, runes_dir: Path) -> None:
        """Bind one explicit Rune root."""
        self._runes_dir = runes_dir

    def declarations(self) -> tuple[DeclaredAnimator, ...]:
        """Load Soulstones and Portals without claiming model-level readiness."""
        from lychd.config.runes.registry import load_rune_registry
        from lychd.config.settings.root import get_settings
        from lychd.domain.animation.services.declarations import (
            compile_animator_declarations,
        )
        from lychd.extensions.host import get_extensions

        extensions = get_extensions()
        settings = get_settings()
        runes = load_rune_registry(extensions, self._runes_dir)
        declarations = compile_animator_declarations(
            settings=settings,
            runes=runes,
        )
        local = (
            DeclaredAnimator(
                name=stone.name,
                kind="soulstone",
                runtime=stone.runtime_name,
                unit_name=f"{stone.service_name}.service",
            )
            for stone in declarations.soulstones
        )
        remote = (
            DeclaredAnimator(
                name=portal.name,
                kind="portal",
                runtime=portal.provider_name,
            )
            for portal in declarations.portals
        )
        return tuple(sorted((*local, *remote), key=lambda item: (item.kind, item.name)))


class OperatorInventoryService:
    """Answer operator questions without constructing the Vessel or mutating state."""

    def __init__(
        self,
        *,
        paths: OperatorPaths,
        receipt: LifecycleReceiptStore,
        units: OwnedUnitInventoryService,
        storage: StorageInventoryService,
        animators: AnimatorDeclarationProvider,
    ) -> None:
        """Compose read-only probes behind typed ports."""
        self._paths = paths
        self._receipt = receipt
        self._units = units
        self._storage = storage
        self._animators = animators

    def inspect(self, selector: OperatorTarget = OperatorTarget.SYSTEM) -> InventoryReport:
        """Build a report for one stable selector, degrading instead of guessing."""
        warnings: list[str] = []
        receipt_present, receipt_valid = self._receipt_state(warnings)
        catalog = self._units.inspect()
        if catalog.warning:
            warnings.append(catalog.warning)
        summary = self._summary(
            receipt_present=receipt_present,
            receipt_valid=receipt_valid,
            catalog=catalog,
            warnings=warnings,
        )

        if selector is OperatorTarget.SYSTEM:
            items = self._system_items(
                receipt_present=receipt_present,
                receipt_valid=receipt_valid,
                catalog=catalog,
            )
        elif selector is OperatorTarget.SERVICES:
            items = self._service_items(catalog)
        elif selector is OperatorTarget.WORKERS:
            items = self._worker_items(catalog)
        elif selector is OperatorTarget.ANIMATORS:
            items = self._animator_items(catalog, warnings)
        elif selector is OperatorTarget.STORAGE:
            items = self._storage_items()
        elif selector is OperatorTarget.CONFIG:
            items = self._config_items(
                receipt_present=receipt_present,
                receipt_valid=receipt_valid,
            )
        elif selector is OperatorTarget.BINDINGS:
            items = self._binding_items(catalog)
        else:
            items = self._run_items(catalog)
        return InventoryReport(
            selector=selector,
            summary=summary,
            items=items,
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def owned_units(self) -> OwnedUnitCatalog:
        """Expose the reusable exact-owned unit catalogue to logs and deletion."""
        return self._units.inspect()

    def declared_animators(self) -> tuple[DeclaredAnimator, ...]:
        """Expose typed declaration truth to exact target resolvers."""
        return self._animators.declarations()

    def _receipt_state(self, warnings: list[str]) -> tuple[bool, bool]:
        if not self._receipt.exists:
            return False, False
        try:
            self._receipt.load()
        except Exception as exc:  # noqa: BLE001 - status reports corrupt ownership as degraded
            warnings.append(f"Cannot validate initialization receipt: {exc}")
            return True, False
        return True, True

    def _summary(
        self,
        *,
        receipt_present: bool,
        receipt_valid: bool,
        catalog: OwnedUnitCatalog,
        warnings: list[str],
    ) -> SystemSummary:
        summary = SystemSummary.STOPPED
        if not receipt_present:
            managed_state_exists = os.path.lexists(self._paths.config) or catalog.receipt_present or bool(warnings)
            summary = SystemSummary.DEGRADED if managed_state_exists else SystemSummary.NOT_INITIALIZED
        elif warnings or not receipt_valid:
            summary = SystemSummary.DEGRADED
        elif not catalog.receipt_present:
            summary = SystemSummary.UNBOUND
        elif any(unit.state in {ObservationState.FAILED, ObservationState.UNKNOWN} for unit in catalog.units):
            summary = SystemSummary.DEGRADED
        elif any(unit.state is ObservationState.ACTIVE for unit in catalog.units):
            summary = SystemSummary.RUNNING
        return summary

    def _system_items(
        self,
        *,
        receipt_present: bool,
        receipt_valid: bool,
        catalog: OwnedUnitCatalog,
    ) -> tuple[InventoryItem, ...]:
        initialized = receipt_present and receipt_valid
        active = sum(unit.state is ObservationState.ACTIVE for unit in catalog.units)
        failed = sum(unit.state is ObservationState.FAILED for unit in catalog.units)
        binding_state = (
            ObservationState.UNKNOWN
            if catalog.warning
            else ObservationState.PRESENT
            if catalog.receipt_present
            else ObservationState.ABSENT
        )
        return (
            InventoryItem(
                category=OperatorTarget.CONFIG,
                name="installation",
                state=ObservationState.PRESENT if initialized else ObservationState.ABSENT,
                detail="validated lifecycle receipt" if initialized else "no validated initialization ownership",
            ),
            InventoryItem(
                category=OperatorTarget.BINDINGS,
                name="bindings",
                state=binding_state,
                detail=catalog.warning or f"{len(catalog.units)} exact owned runtime unit(s)",
            ),
            InventoryItem(
                category=OperatorTarget.SERVICES,
                name="services",
                state=self._aggregate_unit_state(catalog.units),
                detail=f"{active} active · {failed} failed · {len(catalog.units)} owned",
            ),
            self._mount_item(self._paths.storage_data, name="phylactery"),
        )

    @staticmethod
    def _service_items(catalog: OwnedUnitCatalog) -> tuple[InventoryItem, ...]:
        if not catalog.units:
            return (
                InventoryItem(
                    category=OperatorTarget.SERVICES,
                    name="services",
                    state=ObservationState.ABSENT,
                    detail="no validated Scribe-owned runtime units",
                ),
            )
        return tuple(
            InventoryItem(
                category=OperatorTarget.SERVICES,
                name=unit.name,
                state=unit.state,
                detail=unit.detail,
                attributes=(
                    ("unit_file_state", unit.unit_file_state),
                    ("sources", ", ".join(unit.sources)),
                ),
            )
            for unit in catalog.units
        )

    @staticmethod
    def _worker_items(catalog: OwnedUnitCatalog) -> tuple[InventoryItem, ...]:
        vessel = OperatorInventoryService._vessel_unit(catalog)
        if vessel is None:
            state = ObservationState.ABSENT
            detail = "Vessel is not uniquely bound; workers have no independent host unit"
        elif vessel.state is ObservationState.INACTIVE:
            state = ObservationState.INACTIVE
            detail = "workers are co-resident in the stopped Vessel"
        else:
            state = ObservationState.UNKNOWN
            detail = "Vessel activity does not attest queue readiness; Vessel projection is not wired yet"
        return (
            InventoryItem(category=OperatorTarget.WORKERS, name="runs", state=state, detail=detail),
            InventoryItem(category=OperatorTarget.WORKERS, name="rites", state=state, detail=detail),
        )

    def _animator_items(
        self,
        catalog: OwnedUnitCatalog,
        warnings: list[str],
    ) -> tuple[InventoryItem, ...]:
        try:
            declarations = self._animators.declarations()
        except Exception as exc:  # noqa: BLE001 - malformed config belongs in the report
            warnings.append(f"Cannot load Animator declarations: {exc}")
            return (
                InventoryItem(
                    category=OperatorTarget.ANIMATORS,
                    name="animators",
                    state=ObservationState.UNKNOWN,
                    detail="declaration inventory is unavailable",
                ),
            )
        if not declarations:
            return (
                InventoryItem(
                    category=OperatorTarget.ANIMATORS,
                    name="animators",
                    state=ObservationState.ABSENT,
                    detail="no active Animator Runes",
                ),
            )

        items: list[InventoryItem] = []
        for declaration in declarations:
            if declaration.unit_name is None:
                state = ObservationState.UNKNOWN
                detail = "external Portal readiness is not probed by bootstrap status"
            elif (unit := catalog.unit(declaration.unit_name)) is None:
                state = ObservationState.ABSENT
                detail = "declared Soulstone has no exact Scribe-owned unit"
            else:
                state = unit.state
                detail = "runtime activity only; model-level warmth is not yet projected"
            items.append(
                InventoryItem(
                    category=OperatorTarget.ANIMATORS,
                    name=declaration.name,
                    state=state,
                    detail=detail,
                    attributes=(
                        ("kind", declaration.kind),
                        ("runtime", declaration.runtime),
                        ("unit", declaration.unit_name or ""),
                    ),
                )
            )
        return tuple(items)

    def _storage_items(self) -> tuple[InventoryItem, ...]:
        return (
            self._mount_item(self._paths.storage_data, name="phylactery"),
            self._path_item(OperatorTarget.STORAGE, "snapshots", self._paths.snapshots),
        )

    def _config_items(
        self,
        *,
        receipt_present: bool,
        receipt_valid: bool,
    ) -> tuple[InventoryItem, ...]:
        receipt_state = (
            ObservationState.PRESENT
            if receipt_present and receipt_valid
            else ObservationState.UNKNOWN
            if receipt_present
            else ObservationState.ABSENT
        )
        return (
            self._path_item(OperatorTarget.CONFIG, "codex", self._paths.codex_root),
            self._path_item(OperatorTarget.CONFIG, "lychd.toml", self._paths.config),
            InventoryItem(
                category=OperatorTarget.CONFIG,
                name="lifecycle receipt",
                state=receipt_state,
                detail=str(self._paths.receipt),
            ),
            self._path_item(OperatorTarget.CONFIG, "runes", self._paths.runes),
        )

    @staticmethod
    def _binding_items(catalog: OwnedUnitCatalog) -> tuple[InventoryItem, ...]:
        if not catalog.receipt_present:
            return (
                InventoryItem(
                    category=OperatorTarget.BINDINGS,
                    name="Scribe receipt",
                    state=ObservationState.ABSENT,
                    detail="no exact binding ownership recorded",
                ),
            )
        if catalog.warning:
            return (
                InventoryItem(
                    category=OperatorTarget.BINDINGS,
                    name="Scribe receipt",
                    state=ObservationState.UNKNOWN,
                    detail=catalog.warning,
                ),
            )
        return (
            InventoryItem(
                category=OperatorTarget.BINDINGS,
                name="Scribe receipt",
                state=ObservationState.PRESENT,
                detail=f"{len(catalog.units)} exact runtime unit(s)",
                attributes=(("generation", catalog.generation or ""),),
            ),
            *OperatorInventoryService._service_items(catalog),
        )

    @staticmethod
    def _run_items(catalog: OwnedUnitCatalog) -> tuple[InventoryItem, ...]:
        vessel = OperatorInventoryService._vessel_unit(catalog)
        if vessel is not None and vessel.state is ObservationState.INACTIVE:
            state = ObservationState.INACTIVE
            detail = "Vessel is stopped"
        else:
            state = ObservationState.UNKNOWN
            detail = "durable run inventory requires the future Vessel status projection"
        return (
            InventoryItem(
                category=OperatorTarget.RUNS,
                name="runs",
                state=state,
                detail=detail,
            ),
        )

    def _mount_item(self, path: Path, *, name: str) -> InventoryItem:
        mount = self._storage.observe(path)
        if mount.warning:
            state = ObservationState.UNKNOWN
        elif mount.mounted:
            state = ObservationState.ACTIVE
        elif mount.exists:
            state = ObservationState.PRESENT
        else:
            state = ObservationState.ABSENT
        attributes = (
            ("path", str(path)),
            ("mountpoint", str(mount.mount_target or "")),
            ("source", mount.source or ""),
            ("filesystem", mount.filesystem or ""),
            ("fs_root", mount.fs_root or ""),
            ("options", ",".join(mount.options)),
            ("top_level_mount", str(mount.top_level_mount or "")),
        )
        detail = mount.warning or ("exact mountpoint" if mount.mounted else "not an exact mountpoint")
        return InventoryItem(
            category=OperatorTarget.STORAGE,
            name=name,
            state=state,
            detail=detail,
            attributes=attributes,
        )

    @staticmethod
    def _path_item(category: OperatorTarget, name: str, path: Path) -> InventoryItem:
        if not os.path.lexists(path):
            return InventoryItem(
                category=category,
                name=name,
                state=ObservationState.ABSENT,
                detail=str(path),
            )
        try:
            metadata = path.lstat()
        except OSError as exc:
            return InventoryItem(
                category=category,
                name=name,
                state=ObservationState.UNKNOWN,
                detail=f"{path}: {exc}",
            )
        kind = (
            "symlink" if stat.S_ISLNK(metadata.st_mode) else "directory" if stat.S_ISDIR(metadata.st_mode) else "file"
        )
        return InventoryItem(
            category=category,
            name=name,
            state=ObservationState.PRESENT,
            detail=str(path),
            attributes=(
                ("kind", kind),
                ("mode", f"{stat.S_IMODE(metadata.st_mode):04o}"),
                ("owner_uid", str(metadata.st_uid)),
            ),
        )

    @staticmethod
    def _aggregate_unit_state(units: tuple[OwnedUnit, ...]) -> ObservationState:
        if not units:
            return ObservationState.ABSENT
        if any(unit.state is ObservationState.FAILED for unit in units):
            return ObservationState.FAILED
        if any(unit.state is ObservationState.UNKNOWN for unit in units):
            return ObservationState.UNKNOWN
        if any(unit.state is ObservationState.ACTIVE for unit in units):
            return ObservationState.ACTIVE
        return ObservationState.INACTIVE

    @staticmethod
    def _vessel_unit(catalog: OwnedUnitCatalog) -> OwnedUnit | None:
        candidates = catalog.select({"lychd-vessel.service", "lychd-uncaged-vessel.service"})
        return candidates[0] if len(candidates) == 1 else None
