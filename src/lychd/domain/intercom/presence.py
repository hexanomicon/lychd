"""Coarse colleague observations and the operator's bounded sharing choice."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

type Availability = Literal["ready", "busy", "hidden"]


class PresenceIntent(BaseModel):
    """Select availability for exactly the audience shown by this Vessel boot."""

    model_config = ConfigDict(extra="forbid")
    audience_id: UUID
    availability: Availability


class ColleagueObservation(BaseModel):
    """Project a peer report and the local outcome of writing into its pair folder."""

    name: str
    availability: Literal["ready", "busy", "unknown"]
    expires_at: datetime | None
    observed_at: datetime | None
    publication: Literal["waiting", "published", "unavailable"]


class PresenceBoard(BaseModel):
    """Expose labels and times to the local operator while keeping pairing credentials private."""

    audience_id: UUID
    sharing: Availability
    sharing_until: datetime | None
    peers: list[ColleagueObservation]
