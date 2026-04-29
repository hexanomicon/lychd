from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar.plugins import PluginProtocol
    from litestar.types import ControllerRouterHandler
    from pydantic_ai import Agent

    from lychd.system.schemas import QuadletContainer


class ExtensionContext:
    """Registration surface passed to extension ``register()`` hooks."""

    def __init__(self, name: str) -> None:
        """Initialize mutable extension registration collections."""
        self.name = name

        # Infrastructure
        self.containers: list[QuadletContainer] = []
        self.workers: list[Any] = []

        # API / integration
        self.litestar_plugins: list[PluginProtocol] = []
        self.routes: list[ControllerRouterHandler] = []
        self.signatures: list[Any] = []
        self.listeners: list[Any] = []

        # Intelligence
        self.agents: list[Agent] = []
        self.graphs: list[Any] = []

    def add_container(self, rune: QuadletContainer) -> None:
        """Register a Podman Quadlet container."""
        self.containers.append(rune)

    def add_api_route(self, route: ControllerRouterHandler) -> None:
        """Register a Litestar Router, Controller, or Handler."""
        self.routes.append(route)

    def add_litestar_plugin(self, plugin: PluginProtocol) -> None:
        """Register a native Litestar plugin."""
        self.litestar_plugins.append(plugin)

    def add_signature(self, signature: Any) -> None:
        """Register signature metadata consumed by framework adapters."""
        self.signatures.append(signature)

    def add_listener(self, listener: Any) -> None:
        """Register lifecycle/event listener metadata."""
        self.listeners.append(listener)

    def add_agent(self, agent: Agent) -> None:
        """Register a Pydantic AI agent for dispatching."""
        self.agents.append(agent)

    def add_graph(self, graph: Any) -> None:
        """Register graph/reasoning topology metadata."""
        self.graphs.append(graph)
