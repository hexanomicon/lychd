"""Plan and apply reversible host inscription lifecycle operations.

The lifecycle receipt is deletion authority. Geography alone never grants
permission to remove a path: ``init`` records only removable resources it
actually created, and ``destroy`` later removes only those resources while
they remain pristine and safe.

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
from lychd.system.services.lifecycle.bindings import BindingLifecycleService
from lychd.system.services.lifecycle.initialization import InitializationPlanner
from lychd.system.services.lifecycle.lock import LifecycleLock
from lychd.system.services.lifecycle.models import (
    CreatedResources,
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
    LifecyclePlan,
    LifecycleResourceKind,
    created_resources,
)
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore

__all__ = (
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
    "CreatedResources",
    "InitializationPlanner",
    "LifecycleAction",
    "LifecycleDisposition",
    "LifecycleError",
    "LifecycleLock",
    "LifecyclePlan",
    "LifecycleReceiptStore",
    "LifecycleResourceKind",
    "created_resources",
)
