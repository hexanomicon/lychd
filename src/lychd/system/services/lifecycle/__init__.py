"""Lazy compatibility facade for host inscription and deletion lifecycles.

The lifecycle receipt is deletion authority. Geography alone never grants
permission to remove a path: ``init`` records created resources and seals the
exact dedicated-root identities it may deliberately adopt; ``del`` revalidates
that authority before bounded removal.

Internal modules import focused lifecycle leaves. This facade preserves the
historical public import surface without eagerly loading deletion, operator,
Scribe, and storage graphs whenever a leaf model is imported.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from lychd.system.constants import (
    HOST_LAYOUT,
    PATH_CACHE_ROOT,
    PATH_CODEX_ROOT,
    PATH_CRYPT_ROOT,
    PATH_LIFECYCLE_RECEIPT,
    PATH_LYCHD_TOML,
    PATH_POSTGRES_ROOT_DIR,
    PATH_POSTGRESS_DATA_DIR,
    PATH_POSTGRESS_SNAPSHOTS_DIR,
    PATH_RUNES_DIR,
    PATH_SYSTEMD_UNITS_DIR,
    PATH_SYSTEMD_USER_UNITS_DIR,
)

if TYPE_CHECKING:
    from lychd.system.services.lifecycle._authority import (
        LifecycleAuthority,
        current_authority,
    )
    from lychd.system.services.lifecycle.bindings import BindingLifecycleService
    from lychd.system.services.lifecycle.deletion import (
        CommandBtrfsSubvolumeProbe,
        DeletionCheckpointStore,
        DeletionExecutor,
        DeletionPlanner,
        ObservedBtrfsSubvolume,
    )
    from lychd.system.services.lifecycle.deletion_composition import (
        DeletionServices,
        build_deletion_services,
    )
    from lychd.system.services.lifecycle.deletion_models import (
        DELETION_STAGE_ORDER,
        BtrfsSubvolumeIdentity,
        DeletionAction,
        DeletionActionKind,
        DeletionDisposition,
        DeletionOutcome,
        DeletionPaths,
        DeletionPlan,
        DeletionResult,
        DeletionStage,
        PrivilegedHandoff,
    )
    from lychd.system.services.lifecycle.initialization import (
        InitializationEffect,
        InitializationExecutor,
        InitializationPlanner,
        InitializationRecorder,
    )
    from lychd.system.services.lifecycle.lock import LifecycleLock
    from lychd.system.services.lifecycle.models import (
        CreatedBtrfsSubvolume,
        CreatedDirectory,
        CreatedResources,
        DedicatedRootIdentity,
        LifecycleAction,
        LifecycleDisposition,
        LifecycleError,
        LifecyclePlan,
        LifecycleResourceKind,
        created_resources,
    )
    from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
    from lychd.system.services.lifecycle.trees import (
        ManagedTreeInspection,
        ManagedTreeService,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "DELETION_STAGE_ORDER": (
        "lychd.system.services.lifecycle.deletion_models",
        "DELETION_STAGE_ORDER",
    ),
    "BindingLifecycleService": (
        "lychd.system.services.lifecycle.bindings",
        "BindingLifecycleService",
    ),
    "BtrfsSubvolumeIdentity": (
        "lychd.system.services.lifecycle.deletion_models",
        "BtrfsSubvolumeIdentity",
    ),
    "CommandBtrfsSubvolumeProbe": (
        "lychd.system.services.lifecycle.deletion",
        "CommandBtrfsSubvolumeProbe",
    ),
    "CreatedBtrfsSubvolume": (
        "lychd.system.services.lifecycle.models",
        "CreatedBtrfsSubvolume",
    ),
    "CreatedDirectory": (
        "lychd.system.services.lifecycle.models",
        "CreatedDirectory",
    ),
    "CreatedResources": (
        "lychd.system.services.lifecycle.models",
        "CreatedResources",
    ),
    "DedicatedRootIdentity": (
        "lychd.system.services.lifecycle.models",
        "DedicatedRootIdentity",
    ),
    "DeletionAction": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionAction",
    ),
    "DeletionActionKind": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionActionKind",
    ),
    "DeletionCheckpointStore": (
        "lychd.system.services.lifecycle.deletion",
        "DeletionCheckpointStore",
    ),
    "DeletionDisposition": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionDisposition",
    ),
    "DeletionExecutor": (
        "lychd.system.services.lifecycle.deletion",
        "DeletionExecutor",
    ),
    "DeletionOutcome": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionOutcome",
    ),
    "DeletionPaths": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionPaths",
    ),
    "DeletionPlan": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionPlan",
    ),
    "DeletionPlanner": (
        "lychd.system.services.lifecycle.deletion",
        "DeletionPlanner",
    ),
    "DeletionResult": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionResult",
    ),
    "DeletionServices": (
        "lychd.system.services.lifecycle.deletion_composition",
        "DeletionServices",
    ),
    "DeletionStage": (
        "lychd.system.services.lifecycle.deletion_models",
        "DeletionStage",
    ),
    "InitializationEffect": (
        "lychd.system.services.lifecycle.initialization",
        "InitializationEffect",
    ),
    "InitializationExecutor": (
        "lychd.system.services.lifecycle.initialization",
        "InitializationExecutor",
    ),
    "InitializationPlanner": (
        "lychd.system.services.lifecycle.initialization",
        "InitializationPlanner",
    ),
    "InitializationRecorder": (
        "lychd.system.services.lifecycle.initialization",
        "InitializationRecorder",
    ),
    "LifecycleAction": (
        "lychd.system.services.lifecycle.models",
        "LifecycleAction",
    ),
    "LifecycleAuthority": (
        "lychd.system.services.lifecycle._authority",
        "LifecycleAuthority",
    ),
    "LifecycleDisposition": (
        "lychd.system.services.lifecycle.models",
        "LifecycleDisposition",
    ),
    "LifecycleError": (
        "lychd.system.services.lifecycle.models",
        "LifecycleError",
    ),
    "LifecycleLock": (
        "lychd.system.services.lifecycle.lock",
        "LifecycleLock",
    ),
    "LifecyclePlan": (
        "lychd.system.services.lifecycle.models",
        "LifecyclePlan",
    ),
    "LifecycleReceiptStore": (
        "lychd.system.services.lifecycle.receipt",
        "LifecycleReceiptStore",
    ),
    "LifecycleResourceKind": (
        "lychd.system.services.lifecycle.models",
        "LifecycleResourceKind",
    ),
    "ManagedTreeInspection": (
        "lychd.system.services.lifecycle.trees",
        "ManagedTreeInspection",
    ),
    "ManagedTreeService": (
        "lychd.system.services.lifecycle.trees",
        "ManagedTreeService",
    ),
    "ObservedBtrfsSubvolume": (
        "lychd.system.services.lifecycle.deletion",
        "ObservedBtrfsSubvolume",
    ),
    "PrivilegedHandoff": (
        "lychd.system.services.lifecycle.deletion_models",
        "PrivilegedHandoff",
    ),
    "build_deletion_services": (
        "lychd.system.services.lifecycle.deletion_composition",
        "build_deletion_services",
    ),
    "created_resources": (
        "lychd.system.services.lifecycle.models",
        "created_resources",
    ),
    "current_authority": (
        "lychd.system.services.lifecycle._authority",
        "current_authority",
    ),
}


def __getattr__(name: str) -> Any:
    """Load one compatibility export only when a caller requests it."""
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message) from exc
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose eager constants and lazy compatibility symbols to introspection."""
    return sorted({*globals(), *_EXPORTS})


__all__ = (
    "DELETION_STAGE_ORDER",
    "HOST_LAYOUT",
    "PATH_CACHE_ROOT",
    "PATH_CODEX_ROOT",
    "PATH_CRYPT_ROOT",
    "PATH_LIFECYCLE_RECEIPT",
    "PATH_LYCHD_TOML",
    "PATH_POSTGRESS_DATA_DIR",
    "PATH_POSTGRESS_SNAPSHOTS_DIR",
    "PATH_POSTGRES_ROOT_DIR",
    "PATH_RUNES_DIR",
    "PATH_SYSTEMD_UNITS_DIR",
    "PATH_SYSTEMD_USER_UNITS_DIR",
    "BindingLifecycleService",
    "BtrfsSubvolumeIdentity",
    "CommandBtrfsSubvolumeProbe",
    "CreatedBtrfsSubvolume",
    "CreatedDirectory",
    "CreatedResources",
    "DedicatedRootIdentity",
    "DeletionAction",
    "DeletionActionKind",
    "DeletionCheckpointStore",
    "DeletionDisposition",
    "DeletionExecutor",
    "DeletionOutcome",
    "DeletionPaths",
    "DeletionPlan",
    "DeletionPlanner",
    "DeletionResult",
    "DeletionServices",
    "DeletionStage",
    "InitializationEffect",
    "InitializationExecutor",
    "InitializationPlanner",
    "InitializationRecorder",
    "LifecycleAction",
    "LifecycleAuthority",
    "LifecycleDisposition",
    "LifecycleError",
    "LifecycleLock",
    "LifecyclePlan",
    "LifecycleReceiptStore",
    "LifecycleResourceKind",
    "ManagedTreeInspection",
    "ManagedTreeService",
    "ObservedBtrfsSubvolume",
    "PrivilegedHandoff",
    "build_deletion_services",
    "created_resources",
    "current_authority",
)
