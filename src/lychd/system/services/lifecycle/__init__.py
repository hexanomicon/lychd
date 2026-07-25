"""Plan and apply attested host inscription and deletion lifecycles.

The lifecycle receipt is deletion authority. Geography alone never grants
permission to remove a path: ``init`` records created resources and seals the
exact dedicated-root identities it may deliberately adopt; ``del`` revalidates
that authority before bounded removal.

This facade preserves the public import surface while keeping each lifecycle
responsibility in a focused module.
"""

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
