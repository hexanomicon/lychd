"""Cross-surface Intent contract.

Every surface enters through ``RunEngine.submit``. The engine resolves an Intent once
against its injected ``WorkflowRegistry``, persists the exact Pattern revision, and
admits a durable delivery. Graph execution occurs only inside ``perform_run``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Intent"]


class Intent(BaseModel):
    """The single cross-surface request shape — one shape, one `submit()` law."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    # S3: run_id is advisory client-correlation ONLY. Run identity is minted by the
    # ledger (`engine.submit` returns the canonical id on the handle) and stashed here
    # in the intent JSONB. A caller may leave it None; surfaces no longer mint one.
    run_id: str | None = None
    prompt: str
    source: str = "bridge"
    sigil_name: str = Field(default="magus", min_length=1)
    sigil_scopes: frozenset[str] = Field(default_factory=frozenset)
    priority: int | None = Field(default=None, ge=0, le=100)  # None → the per-source default
