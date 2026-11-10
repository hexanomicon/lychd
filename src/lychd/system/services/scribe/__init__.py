"""Stable public surface for Scribe binding compilation and authority."""

from lychd.system.services.scribe.errors import (
    ScribeConflictError,
    ScribeGenerationError,
    ScribeOwnershipError,
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe.facade import ScribeService
from lychd.system.services.scribe.models import (
    BindingChange,
    BindingChangeKind,
    BindingReconcilePlan,
    OwnedBindings,
)

__all__ = [
    "BindingChange",
    "BindingChangeKind",
    "BindingReconcilePlan",
    "OwnedBindings",
    "ScribeConflictError",
    "ScribeGenerationError",
    "ScribeOwnershipError",
    "ScribeService",
    "ScribeTransactionError",
    "ScribeTransactionState",
]
