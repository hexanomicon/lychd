"""Compatibility evidence for the deletion lifecycle module split."""

from lychd.system.services.lifecycle import deletion
from lychd.system.services.lifecycle.deletion_checkpoint import DeletionCheckpointStore
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


def test_deletion_facade_preserves_established_public_objects() -> None:
    """Every historical deletion export resolves to its focused leaf object."""
    expected = {
        "BindingCleanupPort": BindingCleanupPort,
        "BtrfsSubvolumeProbe": BtrfsSubvolumeProbe,
        "CommandBtrfsSubvolumeProbe": CommandBtrfsSubvolumeProbe,
        "DedicatedRootAuthorityPort": DedicatedRootAuthorityPort,
        "DeletionCheckpointStore": DeletionCheckpointStore,
        "DeletionExecutor": DeletionExecutor,
        "DeletionPlanner": DeletionPlanner,
        "ObservedBtrfsSubvolume": ObservedBtrfsSubvolume,
        "ScribeOwnershipPort": ScribeOwnershipPort,
        "StorageInventoryPort": StorageInventoryPort,
        "UnitRetirementPort": UnitRetirementPort,
    }

    assert deletion.__all__ == tuple(expected)
    assert {name: getattr(deletion, name) for name in deletion.__all__} == expected
