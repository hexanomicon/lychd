"""Finite operator-selected expressions; model choices never contain destinations."""

from __future__ import annotations

import re
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, model_validator

from lychd.compositions.reach.schemas import Record

type Reaction = Literal["👀", "👍", "❤️", "😂", "✨", "🤔"]
REACTIONS: tuple[Reaction, ...] = ("👀", "👍", "❤️", "😂", "✨", "🤔")
type GifId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")]


def validate_gif_url(value: str) -> str:
    """Accept an exact GIPHY media locator, without redirects, queries or credentials."""
    if (
        type(value) is not str
        or re.fullmatch(r"https://(?:media[0-4]?\.giphy\.com|i\.giphy\.com)/media/[A-Za-z0-9]{1,80}/giphy\.gif", value)
        is None
    ):
        msg = "invalid_gif_url"
        raise ValueError(msg)
    return value


class ExpressionGif(Record):
    """One private operator catalogue entry, shared exactly within a generation."""

    id: GifId
    description: str = Field(min_length=1, max_length=120, pattern=r"^[^\x00-\x1f\x7f]+$")
    url: Annotated[str, Field(max_length=200), AfterValidator(validate_gif_url)]


class ConversationExpressions(Record):
    """Opt-in response decorations, never ambient channel or acquisition authority."""

    enabled: bool = False
    acknowledge: bool = True
    gifs: tuple[ExpressionGif, ...] = Field(default=(), max_length=8)

    @model_validator(mode="after")
    def unique_enabled_catalogue(self) -> Self:
        if (self.gifs and not self.enabled) or len({item.id for item in self.gifs}) != len(self.gifs):
            msg = "expression_catalogue"
            raise ValueError(msg)
        return self

    def validate_selection(self, reaction: Reaction | None, gif_id: str | None) -> None:
        """Bind a model selection to the frozen opt-in catalogue before any effect."""
        if (reaction is not None or gif_id is not None) and (
            not self.enabled
            or (reaction is not None and reaction not in REACTIONS)
            or (gif_id is not None and gif_id not in {item.id for item in self.gifs})
        ):
            msg = "conversation_expression"
            raise ValueError(msg)
