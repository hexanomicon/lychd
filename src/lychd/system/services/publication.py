"""Stable public facade for journal-bound initialization publication."""

import os as _os

from lychd.system.services.file_publication_models import PublicationRollbackError
from lychd.system.services.file_publication_transaction import JournaledCreation

# Existing adversarial callers patch this shared module adapter.
os = _os

# Preserve public introspection and pickle provenance across the extraction.
JournaledCreation.__module__ = __name__
PublicationRollbackError.__module__ = __name__

__all__ = (
    "JournaledCreation",
    "PublicationRollbackError",
)
