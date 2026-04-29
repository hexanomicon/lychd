"""Domain DTOs for connector-local model discovery data.

These schemas capture connector outputs that matter to orchestration/model
selection without duplicating Pydantic AI's model/provider/toolset abstractions
used at hydration/execution time.

The objects here are connector-local summaries. Cross-animator aggregation
objects (for example a future ``ModelAvailability`` relation) belong in the
registry/orchestration layer, not at the connector boundary.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelSurface(StrEnum):
    """High-level Pydantic AI model surface family exposed by a connector."""

    CHAT = "chat"
    RESPONSES = "responses"


class ModelInfo(BaseModel):
    """Runtime-discovered model summary exposed by a connector.

    ``ModelInfo`` answers a connector-local question:
    "What models does this connector currently expose?"

    Connectors are free to return Pydantic AI ``Model`` instances directly for
    execution. ``ModelInfo`` exists so orchestration can reason about model
    choice before hydration (capability hints, multimodal support, model ids,
    and other connector-reported metadata).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    description: str | None = None
    surface: ModelSurface | None = Field(
        default=None,
        description="Preferred Pydantic AI model surface for this model (chat/responses).",
    )
    modalities_in: list[str] = Field(
        default_factory=list,
        description="Connector-reported accepted modalities (e.g. text, image, audio).",
    )
    modalities_out: list[str] = Field(
        default_factory=list,
        description="Connector-reported output modalities (e.g. text, image, audio).",
    )
    supports_tools: bool | None = Field(
        default=None,
        description="Whether tool calling is supported for this model, if known.",
    )
    supports_streaming: bool | None = Field(
        default=None,
        description="Whether streaming responses are supported for this model, if known.",
    )
    max_context: int | None = Field(
        default=None,
        ge=1,
        description="Known/advertised context window for this model, if available.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
