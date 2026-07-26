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

# Re-exported classes retain the historical public module identity for repr,
# introspection, and serialized references.
BindingChange.__module__ = __name__
BindingReconcilePlan.__module__ = __name__
OwnedBindings.__module__ = __name__
ScribeConflictError.__module__ = __name__
ScribeGenerationError.__module__ = __name__
ScribeOwnershipError.__module__ = __name__
ScribeService.__module__ = __name__
ScribeTransactionError.__module__ = __name__
ScribeTransactionState.__module__ = __name__
