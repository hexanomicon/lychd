"""Pure bounded metadata handoff from the exact isolated worker declaration."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from lychd.domain.weaver.inspection import InspectionValue, PatternInspectionDescriptor
from lychd.interface.observation import ObservationUuid


class ReachPatternObservation(InspectionValue):
    """The hosted Core's scores, never an executable registry or private profile."""

    kind: Literal["reach_pattern_observation"] = "reach_pattern_observation"
    schema_version: Literal[1] = 1
    generation: ObservationUuid
    patterns: tuple[PatternInspectionDescriptor, ...] = Field(min_length=1, max_length=2)
