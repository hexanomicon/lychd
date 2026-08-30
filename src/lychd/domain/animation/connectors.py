"""Connector hierarchy for animation runtime integration.

This module defines the *second axis* of the animation domain:

- ``Animator`` classes model *where/how* execution is reached (local Soulstone or
  remote Portal).
- ``Connector`` classes model *how capabilities are exposed* at that endpoint
  (OpenAI-compatible API, Anthropic API, Gemini API, custom protocol, etc.).

Connectors are explicit ABCs because this codebase favors subclass-based
extension contracts and discovery over structural typing for core runtime
objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING

from lychd.domain.animation.links import Link

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset


class Connector(ABC):
    """Base connector for a runtime animator.

    A connector encapsulates protocol details and endpoint path expansion. It
    hides how a connector endpoint is turned into callable capability
    surfaces. Concrete connectors may support one or many capabilities by
    inheriting the mixins below.

    A connector owns a persistent ``link`` status snapshot. Link liveness is
    only one probe fact; exact capability/profile readiness remains a separate
    registry observation.
    """

    @property
    @abstractmethod
    def link(self) -> Link:
        """Return the current connector-liveness snapshot for orchestration."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the connector endpoint root, when URL-backed."""
        ...


class ModelConnector(ABC):
    """Connector capability mixin for model-facing agent hydration.

    Connectors return Pydantic AI ``Model`` instances directly. LychD keeps
    orchestration/runtime abstractions (Animator/Connector/Link) as domain
    truth, but does not duplicate Pydantic AI's mature model/provider
    abstractions.
    """

    @abstractmethod
    def get_model(self, *, model_id: str | None = None) -> Model:
        """Return a Pydantic AI model for agent hydration/execution.

        ``model_id`` may be omitted when the connector has a natural default
        (for example a single-model Soulstone).
        """
        ...


class ToolConnector(ABC):
    """Connector mixin for Pydantic AI agent-loop toolset hydration.

    This covers classic function/tool-calling surfaces. It does not turn media,
    search, host-process, browser, payment, or other effect interfaces into
    agent authority merely because a model can invoke a tool-shaped wrapper.

    Connectors return Pydantic AI toolset abstractions directly. This allows
    LychD to reuse deferred tools, external tool execution, and toolset
    composition from Pydantic AI instead of re-implementing a parallel
    tool-binding protocol.
    """

    @abstractmethod
    def get_toolsets(self) -> Sequence[AbstractToolset]:
        """Return Pydantic AI toolsets exposed by this connector.

        Return an empty sequence when no tools are currently exposed.
        """
        ...
