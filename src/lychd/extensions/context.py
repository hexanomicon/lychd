from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Use TYPE_CHECKING for heavy 3rd party types if you want to keep startup light
if TYPE_CHECKING:
    from litestar.plugins import PluginProtocol
    from litestar.types import ControllerRouterHandler
    from pydantic_ai import Agent

    from lychd.system.schemas import ContainerRune


class ExtensionContext:
    def __init__(self, name: str) -> None:
        """Do The Genetic Interface for Extension Grafting.

        Acts as the primary Inversion of Control (IoC) bridge between an extension's
        logic and the LychD Kernel. During the Assimilation phase, the Federation
        Manager provides this context to an extension's `register()` hook.

        The extension then populates this "Surgical Tray" with the blueprints
        required to graft itself onto the Daemon's anatomy.

        Attributes:
            name: The unique identifier of the extension being assimilated.
            containers: Blueprints for the Body (Systemd Runes/Podman Quadlets).
            workers: Background ghouls and task queues.
            litestar_plugins: Native extensions for the web server logic.
            routes: The sensory interfaces (API Routers/Controllers).
            agents: The cognitive organs (Pydantic AI Agents).
            graphs: The reasoning topologies (Pydantic AI Graphs).

        """
        self.name = name

        # Infrastructure (The Body)
        self.containers: list[ContainerRune] = []
        self.workers: list[Any] = []

        # API (The Senses/Communication)
        self.litestar_plugins: list[PluginProtocol] = []
        self.routes: list[ControllerRouterHandler] = []

        # Litestar
        self.routes = []
        self.signatures = []
        self.listeners = []
        # Intelligence (The Brain)
        self.agents: list[Agent] = []
        self.graphs = []

    # --- Infrastructure Registration ---
    def add_container(self, rune: ContainerRune) -> None:
        """Register a Podman Quadlet container."""
        self.containers.append(rune)

    # --- Litestar Registration ---
    def add_api_route(self, route: ControllerRouterHandler) -> None:
        """Register a Litestar Router, Controller, or Handler."""
        self.routes.append(route)

    def add_litestar_plugin(self, plugin: PluginProtocol) -> None:
        """Register a native Litestar plugin."""
        self.litestar_plugins.append(plugin)

    # --- Intelligence Registration ---
    def add_agent(self, agent: Agent) -> None:
        """Register a Pydantic AI agent for dispatching."""
        self.agents.append(agent)
