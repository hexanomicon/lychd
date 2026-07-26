"""The Projection Law generative-UI descriptor registry.

Agents select closed descriptor keys and provide data. The Vessel validates that
data and emits inert JSON; the Svelte Altar owns the compile-time component map.
Model output is never interpreted as markup or executable code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from lychd.agents.workflows.bridge_chat import FragmentCall

logger = structlog.get_logger()


class PlanChecklistParams(BaseModel):
    """Params for `genui.plan_checklist`."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    steps: list[str] = Field(default_factory=list)


class CapabilityTableRow(BaseModel):
    """One row of `genui.capability_table`."""

    model_config = ConfigDict(extra="forbid")

    capability_key: str = Field(min_length=1)
    family: str = Field(min_length=1)
    state: str = Field(min_length=1)


class CapabilityTableParams(BaseModel):
    """Params for `genui.capability_table`."""

    model_config = ConfigDict(extra="forbid")

    rows: list[CapabilityTableRow] = Field(default_factory=list)


class VisionSummaryParams(BaseModel):
    """Params for `genui.vision_summary`."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    severity: str = "info"


@dataclass(frozen=True)
class FragmentDef:
    """One registered generative-UI descriptor and its validation schema."""

    key: str
    params_model: type[BaseModel]


@dataclass(frozen=True)
class ValidatedFragment:
    """A descriptor call that passed registry validation."""

    key: str
    params: BaseModel


class FragmentRegistry:
    """The Vessel-owned registry of renderable generative-UI fragments."""

    def __init__(self, defs: dict[str, FragmentDef] | None = None) -> None:
        """Initialize the registry from a key -> `FragmentDef` mapping."""
        self._defs: dict[str, FragmentDef] = dict(defs or {})

    def register(self, definition: FragmentDef) -> None:
        """Register (or replace) one fragment definition by key."""
        self._defs[definition.key] = definition

    def get(self, key: str) -> FragmentDef | None:
        """Return the definition for `key`, or `None` if unregistered."""
        return self._defs.get(key)

    def keys(self) -> tuple[str, ...]:
        """Return the registered fragment keys in insertion order."""
        return tuple(self._defs)

    def validate_calls(self, calls: list[FragmentCall]) -> list[ValidatedFragment]:
        """Validate fragment calls; drop-and-log unknown keys and invalid params."""
        validated: list[ValidatedFragment] = []
        for call in calls:
            definition = self._defs.get(call.fragment)
            if definition is None:
                logger.warning("fragment_unknown", fragment=call.fragment)
                continue
            try:
                params = definition.params_model.model_validate(call.params)
            except ValidationError as exc:
                logger.warning("fragment_invalid_params", fragment=call.fragment, error=str(exc))
                continue
            validated.append(ValidatedFragment(key=definition.key, params=params))
        return validated

    def descriptor(self, fragment: ValidatedFragment) -> dict[str, Any]:
        """Return the inert client descriptor for a validated fragment."""
        return {
            "kind": fragment.key,
            "schema_version": 1,
            "props": fragment.params.model_dump(mode="json"),
            "actions": [],
        }


def build_fragment_registry() -> FragmentRegistry:
    """Seed the v1 generative-UI registry with its three canonical fragments."""
    return FragmentRegistry(
        {
            "genui.plan_checklist": FragmentDef(
                key="genui.plan_checklist",
                params_model=PlanChecklistParams,
            ),
            "genui.capability_table": FragmentDef(
                key="genui.capability_table",
                params_model=CapabilityTableParams,
            ),
            "genui.vision_summary": FragmentDef(
                key="genui.vision_summary",
                params_model=VisionSummaryParams,
            ),
        }
    )
