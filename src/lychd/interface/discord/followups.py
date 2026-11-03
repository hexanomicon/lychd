"""Generation-local candidates from exact successfully delivered Discord finals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from lychd.compositions.reach.operator_wire import ReachHistoryEntry

MAX_FINAL_ANCHORS = 512


@dataclass(frozen=True)
class _Final:
    anchor: ReachHistoryEntry
    human_subject_id: str
    group_id: str
    origin_event_id: str | None


class FollowupLedger:
    """Retain bounded own-final excerpts; other channel activity closes adjacency."""

    def __init__(self) -> None:
        """Start a fresh, empty generation with no inherited invitations."""
        self.finals: dict[tuple[str, str], _Final] = {}
        self.adjacent: dict[str, str] = {}
        self.decorations: dict[tuple[str, str], str] = {}

    def activity(
        self,
        conversation_id: str,
        event_id: str,
        subject_id: str,
        occurred_at: datetime,
        *,
        reference_id: str | None,
        allow_reply: bool,
        allow_followup: bool,
        followup_window: int,
    ) -> tuple[Literal["reply", "followup"], ReachHistoryEntry] | None:
        """Consume adjacency before selection without inspecting an incoming body."""
        previous = self.adjacent.pop(conversation_id, None)
        echoed = self.finals.get((conversation_id, event_id))
        final = self.finals.get((conversation_id, previous)) if previous is not None else None
        if (
            previous is not None
            and final is not None
            and final.anchor.subject_id == subject_id
            and (
                (echoed is not None and echoed.group_id == previous)
                or self.decorations.get((conversation_id, event_id)) == previous
            )
        ):
            # Delayed Gateway echoes may arrive after all REST parts have settled.
            self.adjacent[conversation_id] = previous
            return None
        if allow_reply and reference_id is not None:
            final = self.finals.get((conversation_id, reference_id))
            if final is not None and final.anchor.occurred_at < occurred_at:
                return "reply", final.anchor
        if allow_followup and reference_id is None and previous is not None:
            final = self.finals.get((conversation_id, previous))
            if final is not None and final.human_subject_id == subject_id:
                age = (occurred_at - final.anchor.occurred_at).total_seconds()
                if 0 < age <= followup_window:
                    return "followup", final.anchor
        return None

    def delivered(
        self,
        anchors: tuple[ReachHistoryEntry, ...],
        *,
        human_subject_id: str,
        origin_event_id: str | None = None,
    ) -> None:
        """Open one adjacent slot only after the complete final has succeeded."""
        if not anchors:
            return
        conversation = anchors[-1].conversation_id
        self.adjacent.pop(conversation, None)
        if len(self.finals) + len(self.decorations) + len(anchors) > MAX_FINAL_ANCHORS:
            return
        group_id = anchors[-1].event_id
        for anchor in anchors:
            self.finals[(conversation, anchor.event_id)] = _Final(anchor, human_subject_id, group_id, origin_event_id)
        self.adjacent[conversation] = group_id

    def decorated(self, conversation_id: str, event_id: str, *, origin_event_id: str) -> None:
        """Recognize a known successful GIF echo without creating an anchor or invitation."""
        group = self.adjacent.get(conversation_id)
        final = self.finals.get((conversation_id, group)) if group is not None else None
        if (
            final is None
            or final.origin_event_id != origin_event_id
            or (conversation_id, event_id) in self.finals
            or len(self.finals) + len(self.decorations) >= MAX_FINAL_ANCHORS
        ):
            return
        self.decorations[(conversation_id, event_id)] = final.group_id
