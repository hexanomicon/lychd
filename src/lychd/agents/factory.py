"""`AgentForge` — the ONE process-scoped agent cache (A5 §4, FINAL C6).

The forge never binds a model (Late-Binding law): the model arrives per-run from
the resolved `CapabilityGrant`. What the forge binds is identity, typed output,
retry/settings policy, and the write-gated toolsets. Cache key is the
`AgentSpec` itself (frozen + hashable), so toolset identity is in the key from
day one — the ADR-33 lesson learned pre-emptively.

Wave 1 builds the forge + `AgentSpec` shape and wires `THE_FIRST_ONE` through it.
The full toolset-registry unpack (resolving `toolset_names` through a sealed
registry) is a later wave; here toolsets arrive as explicit factories.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from lychd.agents.deps import LychDDeps

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset

    ToolsetFactory = Callable[[], AbstractToolset[LychDDeps]]
    InstructionHook = Callable[..., Any]
    AgentBuilder = Callable[["AgentSpec"], Agent[LychDDeps, Any]]


@dataclass(frozen=True, kw_only=True)
class AgentSpec:
    """Declarative recipe for one agent. Hashable => forge cache key (FINAL C6).

    `toolset_names` + `writes` replace A5's `gates` (A6's gating vocabulary wins):
    a mutating toolset is bound only when `writes` is true (security by tool
    *absence*, adw-kit idiom), never by prompt pleading.
    """

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
    """Construct a late-binding agent: no model; write-gated toolsets bound by absence.

    The typed output union is the spec's own `output_types` (hashable → in the cache
    key). A toolset named in `mutating` is bound only when `spec.writes` — an agent
    without write authority has no mutating tool at all.
    """
    toolsets: list[AbstractToolset[LychDDeps]] = []
    for tool_name in spec.toolset_names:
        factory = toolset_factories.get(tool_name)
        if factory is None:
            msg = f"AgentSpec '{spec.name}' names toolset '{tool_name}' with no registered factory."
            raise KeyError(msg)
        if tool_name in mutating and not spec.writes:
            continue  # security by absence — no write authority, no mutating tool
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
    """Per-process agent cache keyed by `AgentSpec` (adw-kit's `agent_for`).

    A builder is registered per spec *name*; `agent_for(spec)` builds once and
    caches by the whole spec, so a changed spec (new toolset set, new max_tokens)
    is a distinct cache entry.
    """

    def __init__(self, builders: dict[str, AgentBuilder] | None = None) -> None:
        """Initialize the empty cache with an optional name->builder registry."""
        self._builders: dict[str, AgentBuilder] = dict(builders or {})
        self._cache: dict[AgentSpec, Agent[LychDDeps, Any]] = {}

    def register(self, name: str, builder: AgentBuilder) -> None:
        """Register the builder that turns a named spec into an agent."""
        self._builders[name] = builder

    def agent_for(self, spec: AgentSpec) -> Agent[LychDDeps, Any]:
        """Return the cached agent for `spec`, building (and caching) it on first use."""
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


def build_local_model(*, model_id: str, base_url: str, api_key: str = "placeholder") -> Model:
    """Build the reference local OpenAI-compatible model (A5 §4, Part 5.A).

    A thin wrapper over the ONE shared constructor in
    `domain/animation/model_factory.py` — the SAME builder the production hydrator
    (`AnimatorBinder` → `OpenAICompatibleConnector.get_model`) uses, so the reference
    tests/CLI exercise is byte-for-byte the model the daemon runs (identical tool-call
    JSON-schema profile). Previously this diverged: the reference carried the profile,
    production did not.
    """
    from lychd.domain.animation.model_factory import build_openai_compatible_model, openai_compatible_provider

    return build_openai_compatible_model(
        model_id=model_id,
        provider=openai_compatible_provider(base_url=base_url, api_key=api_key),
    )


__all__ = ["AgentForge", "AgentSpec", "build_agent", "build_local_model"]
