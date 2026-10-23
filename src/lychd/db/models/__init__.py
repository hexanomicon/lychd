"""Phylactery ORM models.

Importing this package registers every model on ``orm_registry.metadata`` so
alembic autogenerate and ``target_metadata`` see the full schema.
"""

from lychd.db.models.archive import ArchiveIntake, ArchiveNamespace, ArchiveNote, ArchiveRecall
from lychd.db.models.archive_derivation import ArchiveEmbeddingGeneration, ArchiveNoteEmbedding
from lychd.db.models.atlas import AtlasProjectRecord, AtlasRequestRecord
from lychd.db.models.blockworld import BlockworldPlacementAction, BlockworldPlacementMission
from lychd.db.models.checkpoint import RunCheckpoint
from lychd.db.models.codex import CodexPreauthorization
from lychd.db.models.consent import Consent
from lychd.db.models.delegation import DelegatedAgentEventRecord, DelegatedAgentJobRecord
from lychd.db.models.intercom import (
    IntercomCapacity,
    IntercomCredential,
    IntercomDeclaration,
    IntercomOutbox,
    IntercomPeer,
    IntercomTask,
    IntercomTransmission,
)
from lychd.db.models.karma import Karma
from lychd.db.models.nexus import NexusSwapRequest
from lychd.db.models.privacy import DisclosureCapacityRecord, DisclosureTransmission
from lychd.db.models.run import Run
from lychd.db.models.run_delivery import RunDelivery
from lychd.db.models.scout import ScoutAttempt, ScoutBudget
from lychd.db.models.session import Session
from lychd.db.models.soulstone import SoulstoneRecord
from lychd.db.models.step import Step

__all__ = [
    "ArchiveEmbeddingGeneration",
    "ArchiveIntake",
    "ArchiveNamespace",
    "ArchiveNote",
    "ArchiveNoteEmbedding",
    "ArchiveRecall",
    "AtlasProjectRecord",
    "AtlasRequestRecord",
    "BlockworldPlacementAction",
    "BlockworldPlacementMission",
    "CodexPreauthorization",
    "Consent",
    "DelegatedAgentEventRecord",
    "DelegatedAgentJobRecord",
    "DisclosureCapacityRecord",
    "DisclosureTransmission",
    "IntercomCapacity",
    "IntercomCredential",
    "IntercomDeclaration",
    "IntercomOutbox",
    "IntercomPeer",
    "IntercomTask",
    "IntercomTransmission",
    "Karma",
    "NexusSwapRequest",
    "Run",
    "RunCheckpoint",
    "RunDelivery",
    "ScoutAttempt",
    "ScoutBudget",
    "Session",
    "SoulstoneRecord",
    "Step",
]
