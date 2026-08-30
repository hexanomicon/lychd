"""Construction and process-local caching for declarative agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from lychd.agents.deps import LychDDeps

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic_ai.toolsets import AbstractToolset

    ToolsetFactory = Callable[[], AbstractToolset[LychDDeps]]
    InstructionHook = Callable[..., Any]
    AgentBuilder = Callable[["AgentSpec"], Agent[LychDDeps, Any]]


@dataclass(frozen=True, kw_only=True)
class AgentSpec:
    """Hashable construction recipe and cache key for an agent."""

    name: str
    instructions_key: str
    instructions: str
    output_types: tuple[type, ...]
    toolset_names: tuple[str, ...] = ()
    writes: bool = False
    retries: int = 2
    max_tokens: int | None = 4096


def build_agent(
    spec: AgentSpec,
    *,
    toolset_factories: dict[str, ToolsetFactory],
    mutating: frozenset[str] = frozenset(),
    instruction_hooks: tuple[InstructionHook, ...] = (),
) -> Agent[LychDDeps, Any]:
    """Build a model-free agent, omitting mutating toolsets without write authority."""
    toolsets: list[AbstractToolset[LychDDeps]] = []
    for tool_name in spec.toolset_names:
        factory = toolset_factories.get(tool_name)
        if factory is None:
            msg = f"AgentSpec '{spec.name}' names toolset '{tool_name}' with no registered factory."
            raise KeyError(msg)
        if tool_name not in mutating or spec.writes:
            toolsets.append(factory())

    output_type: Any = list(spec.output_types)
    agent: Agent[LychDDeps, Any] = Agent(
        deps_type=LychDDeps,
        output_type=output_type,
        retries=spec.retries,
        instructions=spec.instructions,
        model_settings=ModelSettings(max_tokens=spec.max_tokens) if spec.max_tokens else None,
        toolsets=toolsets,
    )
    for hook in instruction_hooks:
        agent.instructions(hook)
    return agent


class AgentForge:
    """Cache agents by their complete specification."""

    def __init__(self, builders: dict[str, AgentBuilder] | None = None) -> None:
        """Initialize registered builders and an empty cache."""
        self._builders: dict[str, AgentBuilder] = dict(builders or {})
        self._cache: dict[AgentSpec, Agent[LychDDeps, Any]] = {}

    def register(self, name: str, builder: AgentBuilder) -> None:
        """Register the builder for a specification name."""
        self._builders[name] = builder

    def agent_for(self, spec: AgentSpec) -> Agent[LychDDeps, Any]:
        """Return the cached agent, constructing it on first use."""
        cached = self._cache.get(spec)
        if cached is not None:
            return cached
        builder = self._builders.get(spec.name)
        if builder is None:
            msg = f"No agent builder registered for spec '{spec.name}'."
            raise KeyError(msg)
        agent = builder(spec)
        self._cache[spec] = agent
        return agent


__all__ = ["AgentForge", "AgentSpec", "build_agent"]
