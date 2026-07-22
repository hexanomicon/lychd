"""The `Intent` shape and the deterministic router (A5 §9).

Every surface (Bridge now; CLI and A2A later) enters through `RunEngine.submit`.
The engine routes an `Intent` to a `Workflow` ONCE via the `WorkflowRegistry`
(first-match `Trigger`), persists the choice on the run row, and enqueues the run
onto SAQ — the graph executes only inside the `perform_run` ghoul.

Wave 2 keystone: the old `submit()` (`asyncio.create_task`) is gone — its logic
moved into `domain/cortex/engine.py` (`RunEngine`) and `ghouls/runs.py`
(`perform_run`). Routing itself lives on `WORKFLOW_REGISTRY.route`; this module
now owns only the cross-surface `Intent` shape.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ArtifactContent", "ArtifactRef", "ContentPart", "Intent", "TextContent"]


class ArtifactRef(BaseModel):
    """Immutable metadata for a blob stored outside the run/checkpoint record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_type: str = Field(min_length=1)
    size: int = Field(ge=0)
    classification: Literal["public", "internal", "private", "restricted"] = "private"

    @property
    def modality(self) -> str:
        """Project MIME type onto the dispatch modality vocabulary."""
        prefix = self.media_type.split("/", maxsplit=1)[0].lower()
        if prefix in {"image", "audio", "video"}:
            return prefix
        if self.media_type.lower() == "application/pdf":
            return "document"
        return "binary"


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
    priority: int | None = None  # None → the [orchestration.routing] per-source default

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
