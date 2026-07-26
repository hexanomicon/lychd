"""Compatibility facade for the staged deletion lifecycle.

Implementation modules import the narrow planning, execution, ports, storage,
and checkpoint leaves directly. This facade preserves the established public
surface for callers that imported deletion services from this module.
"""

from lychd.system.services.lifecycle.deletion_checkpoint import (
    DeletionCheckpointStore,
)
from lychd.system.services.lifecycle.deletion_execution import DeletionExecutor
from lychd.system.services.lifecycle.deletion_planning import DeletionPlanner
from lychd.system.services.lifecycle.deletion_ports import (
    BindingCleanupPort,
    BtrfsSubvolumeProbe,
    DedicatedRootAuthorityPort,
    ScribeOwnershipPort,
    StorageInventoryPort,
    UnitRetirementPort,
)
from lychd.system.services.lifecycle.deletion_storage import (
    CommandBtrfsSubvolumeProbe,
    ObservedBtrfsSubvolume,
)

__all__ = (
    "BindingCleanupPort",
    "BtrfsSubvolumeProbe",
    "CommandBtrfsSubvolumeProbe",
    "DedicatedRootAuthorityPort",
    "DeletionCheckpointStore",
    "DeletionExecutor",
    "DeletionPlanner",
    "ObservedBtrfsSubvolume",
    "ScribeOwnershipPort",
    "StorageInventoryPort",
    "UnitRetirementPort",
)
