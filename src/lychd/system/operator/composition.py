"""Bootstrap-safe composition for the public operator services."""

from __future__ import annotations

from dataclasses import dataclass

from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.control import OperatorControlService, VesselControlPort
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


@dataclass(frozen=True)
class OperatorServices:
    """One shared service graph for a single CLI invocation."""

    inventory: OperatorInventoryService
    control: OperatorControlService
    journal: JournalService
    retirement: OwnedUnitRetirementService
    storage: StorageInventoryService
    targets: OperatorTargetResolver


def build_operator_services(
    *,
    runner: ProcessRunner | None = None,
    paths: OperatorPaths | None = None,
    vessel: VesselControlPort | None = None,
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
    control = OperatorControlService(
        inventory=inventory,
        targets=targets,
        runner=process,
        systemctl_bin=systemctl,
        lock_factory=LifecycleLock,
        vessel=vessel,
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
        targets=targets,
    )
