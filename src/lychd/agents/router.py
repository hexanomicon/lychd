"""Cross-surface Intent and content contracts.

Every surface enters through ``RunEngine.submit``. The engine resolves an Intent once
against its injected ``WorkflowRegistry``, persists the exact Pattern revision, and
admits a durable delivery. Graph execution occurs only inside ``perform_run``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lychd.domain.artifacts import ArtifactRef

__all__ = ["ArtifactContent", "ArtifactRef", "ContentPart", "Intent", "TextContent"]


class TextContent(BaseModel):
    """One textual intent part."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["text"] = "text"
    text: str


class ArtifactContent(BaseModel):
    """One immutable reference to externally stored multimodal content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["artifact"] = "artifact"
    artifact: ArtifactRef


ContentPart = Annotated[TextContent | ArtifactContent, Field(discriminator="kind")]


class Intent(BaseModel):
    """The single cross-surface request shape — one shape, one `submit()` law."""

    session_id: str
    # S3: run_id is advisory client-correlation ONLY. Run identity is minted by the
    # ledger (`engine.submit` returns the canonical id on the handle) and stashed here
    # in the intent JSONB. A caller may leave it None; surfaces no longer mint one.
    run_id: str | None = None
    prompt: str
    content: tuple[ContentPart, ...] = ()
    source: str = "bridge"
    sigil_name: str = Field(default="magus", min_length=1)
    sigil_scopes: frozenset[str] = Field(default_factory=frozenset)
    priority: int | None = Field(default=None, ge=0, le=100)  # None → the per-source default

    @model_validator(mode="after")
    def _default_text_content(self) -> Intent:
        """Preserve the text-only API while making the durable content shape explicit."""
        if not self.content:
            self.content = (TextContent(text=self.prompt),)
        return self

    @property
    def required_modalities(self) -> tuple[str, ...]:
        """Return non-text modalities required by referenced artifacts."""
        return tuple(sorted({part.artifact.modality for part in self.content if isinstance(part, ArtifactContent)}))
