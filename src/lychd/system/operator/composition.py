"""Bootstrap-safe composition for the public operator services."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.control import OperatorControlService
from lychd.system.operator.inventory import (
    ConfiguredAnimatorDeclarations,
    OperatorInventoryService,
    OperatorPaths,
)
from lychd.system.operator.journal import JournalService
from lychd.system.operator.process import ProcessRunner, SubprocessRunner
from lychd.system.operator.retirement import OwnedUnitRetirementService
from lychd.system.operator.storage import StorageInventoryService
from lychd.system.operator.targets import OperatorTargetResolver
from lychd.system.operator.units import OwnedUnitInventoryService

if TYPE_CHECKING:
    from lychd.system.operator.stop_evidence import ExitReference


@dataclass(frozen=True)
class OperatorServices:
    """One shared service graph for a single CLI invocation."""

    inventory: OperatorInventoryService
    control: OperatorControlService
    journal: JournalService
    retirement: OwnedUnitRetirementService
    storage: StorageInventoryService


def build_operator_services(
    *,
    runner: ProcessRunner | None = None,
    paths: OperatorPaths | None = None,
) -> OperatorServices:
    """Compose local operator services without importing or constructing ASGI."""
    from lychd.system.services.lifecycle.lock import LifecycleLock
    from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
    from lychd.system.services.scribe.facade import ScribeService

    process = runner or SubprocessRunner()
    locations = paths or OperatorPaths.current()
    systemctl = trusted_host_tool("systemctl")
    findmnt = trusted_host_tool("findmnt")
    storage = StorageInventoryService(process, findmnt_bin=findmnt)
    unit_inventory = OwnedUnitInventoryService(
        ScribeService(
            output_dir=locations.bindings,
            systemd_dir=locations.systemd_bindings,
        ),
        process,
        systemctl_bin=systemctl,
    )
    inventory = OperatorInventoryService(
        paths=locations,
        receipt=LifecycleReceiptStore(locations.receipt),
        units=unit_inventory,
        storage=storage,
        animators=ConfiguredAnimatorDeclarations(runes_dir=locations.runes),
    )
    targets = OperatorTargetResolver(inventory)

    def admit_stop(generation: str) -> None:
        from lychd.system.operator.admission_client import StopAdmissionClient

        StopAdmissionClient().admit(generation)

    def hold_exit_evidence() -> AbstractContextManager[ExitReference]:
        from lychd.system.operator.stop_evidence import hold_native_exit

        return hold_native_exit()

    control = OperatorControlService(
        inventory=inventory,
        targets=targets,
        runner=process,
        systemctl_bin=systemctl,
        lock_factory=LifecycleLock,
        stop_admission=admit_stop,
        exit_reference_factory=hold_exit_evidence,
    )
    journal = JournalService(
        targets=targets,
        runner=process,
        journalctl_bin=trusted_host_tool("journalctl"),
    )
    retirement = OwnedUnitRetirementService(
        inventory=inventory,
        runner=process,
        systemctl_bin=systemctl,
    )
    return OperatorServices(
        inventory=inventory,
        control=control,
        journal=journal,
        retirement=retirement,
        storage=storage,
    )
