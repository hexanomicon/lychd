"""The keyed-block Context Orchestrator (CAG, ADR 21 / ADR 28 §2)."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.animation.services.registry import AnimatorRegistry

_DEFAULT_TURN_WINDOW = 20
_DEFAULT_CHAR_CAP = 96_000
_FLOOR_LAYER_MIN = 2
_FLOOR_LAYER_MAX = 4


class ContextBudgetExceededError(RuntimeError):
    """The non-negotiable floor and current query exceed the context budget."""


@dataclass(frozen=True, kw_only=True)
class Block:
    """One ordered context block."""

    layer: int
    key: str
    text: str


@dataclass(frozen=True, kw_only=True)
class AssembledContext:
    """The assembled Stable Floor for one run.

    `state_window` is layer 5 as message history; `query` is layer 6.
    """

    blocks: tuple[Block, ...]
    state_window: list[Any]
    continuation: list[Any]
    query: str
    context_window: int | None = None

    def floor_text(self) -> str:
        """Render layers 2-4 in (layer, key) order for the dynamic instructions hook."""
        return "\n\n".join(
            block.text for block in self.blocks if _FLOOR_LAYER_MIN <= block.layer <= _FLOOR_LAYER_MAX and block.text
        )

    def model_history(self) -> list[Any]:
        """Return detached settled history followed by the indivisible current chain."""
        return deepcopy([*self.state_window, *self.continuation])


def _detached_context(assembled: AssembledContext) -> AssembledContext:
    """Detach mutable message values while sharing immutable context blocks."""
    return replace(
        assembled,
        state_window=deepcopy(assembled.state_window),
        continuation=deepcopy(assembled.continuation),
    )


@dataclass
class _EnvironmentSnapshot:
    """One frozen environment block shared by every active referencing run."""

    block: Block
    run_ids: set[str] = field(default_factory=set)


# The First One's persona text — identical to `Agent.instructions` (layer 1, same key).
IDENTITY_BLOCK_KEY = "identity:the-first-one:v1"
IDENTITY_BLOCK_TEXT = (
    "You are The First One, the resident intelligence of the Altar. You speak "
    "with cold precision and economy. You reason over the woven Stable Floor "
    "you are given and never invent capabilities you were not granted. When you "
    "would render structured UI, you name a registered fragment and its params; "
    "you never emit markup. You may propose a coven swap, but the Magus disposes."
)


@dataclass
class ContextOrchestrator:
    """Assemble the keyed-block Stable Floor and cache per-run floor text.

    Layers 1/3/5/6 carry the identity, environment, state, and current query.
    The per-run cache lets `floor_text(run_id)` return exactly the text assembled
    in the `WeaveContext` node. Environment snapshots remain shared and frozen
    only while at least one active run references their key.
    """

    registry: AnimatorRegistry
    turn_window: int = _DEFAULT_TURN_WINDOW
    char_cap: int = _DEFAULT_CHAR_CAP
    _cache: dict[str, AssembledContext] = field(default_factory=dict)
    _env_snapshots: dict[str, _EnvironmentSnapshot] = field(default_factory=dict)
    _env_snapshot_key_by_run: dict[str, str] = field(default_factory=dict)

    def assemble(
        self,
        *,
        run_id: str,
        session_id: str,
        query: str,
        history: list[Any] | None = None,
        continuation: list[Any] | None = None,
        grant: CapabilityGrant | None = None,
        grant_epoch: str | int = 0,
    ) -> AssembledContext:
        """Assemble and retain the six-layer floor without borrowing mutable messages."""
        environment_key, environment_block = self._environment_block(
            session_id=session_id,
            grant=grant,
            grant_epoch=grant_epoch,
        )
        stable_blocks: list[Block] = [
            self._identity_block(),
            environment_block,
        ]
        stable_blocks.sort(key=lambda block: (block.layer, block.key))

        context_window = self._context_window(grant)
        effective_char_cap = self.char_cap
        if context_window is not None:
            # A conservative conversion keeps the assembled textual context below
            # the discovered token window without pretending to be a tokenizer.
            effective_char_cap = min(effective_char_cap, context_window * 3)
        current_chain = deepcopy(continuation or [])
        continuation_chars = self._history_cost(current_chain)
        fixed_chars = sum(len(block.text) for block in stable_blocks) + len(query) + continuation_chars
        if fixed_chars > effective_char_cap:
            msg = (
                f"Stable floor, query, and required continuation require {fixed_chars} characters, "
                f"exceeding the {effective_char_cap}-character context budget."
            )
            raise ContextBudgetExceededError(msg)
        window = deepcopy(
            self._bounded_history(
                list(history or []),
                budget=effective_char_cap - fixed_chars,
            )
        )
        state_block = self._state_block([*window, *current_chain])
        query_block = self._query_block(query)
        blocks = (*stable_blocks, state_block, query_block)

        assembled = AssembledContext(
            blocks=blocks,
            state_window=window,
            continuation=current_chain,
            query=query,
            context_window=context_window,
        )
        self._retain_environment_snapshot(
            run_id=run_id,
            key=environment_key,
            block=environment_block,
        )
        self._cache[run_id] = _detached_context(assembled)
        return assembled

    def floor_text(self, run_id: str) -> str:
        """Return the layer 2-4 floor text assembled for `run_id` (empty if unassembled)."""
        assembled = self._cache.get(run_id)
        return assembled.floor_text() if assembled is not None else ""

    def get(self, run_id: str) -> AssembledContext | None:
        """Return a detached projection of the cached context for `run_id`, if any."""
        assembled = self._cache.get(run_id)
        return _detached_context(assembled) if assembled is not None else None

    def release(self, run_id: str) -> None:
        """Drop one settled run's assembly and its environment-snapshot leases."""
        self._cache.pop(run_id, None)
        key = self._env_snapshot_key_by_run.pop(run_id, None)
        if key is None:
            return
        snapshot = self._env_snapshots.get(key)
        if snapshot is None:
            return
        snapshot.run_ids.discard(run_id)
        if not snapshot.run_ids:
            self._env_snapshots.pop(key, None)

    def _identity_block(self) -> Block:
        return Block(
            layer=1,
            key=IDENTITY_BLOCK_KEY,
            text=IDENTITY_BLOCK_TEXT,
        )

    def _environment_block(
        self,
        *,
        session_id: str,
        grant: CapabilityGrant | None,
        grant_epoch: str | int,
    ) -> tuple[str, Block]:
        # Snapshot per (session, grant_epoch): the env block is frozen at that
        # key and refreshed only at a grant-change boundary, so an identical key
        # set yields byte-identical bytes even if warm hardware churns between
        # assembles within the same epoch (§6 Environment ruling).
        binding = grant.spec.key if grant is not None else "unbound"
        key = f"env:{session_id}:{binding}:{grant_epoch}"
        cached = self._env_snapshots.get(key)
        if cached is not None:
            return key, cached.block

        active_key = grant.spec.key if grant is not None else "none"
        warm = self._warm_capability_keys()
        lines = [
            "# Environment",
            f"active capability: {active_key}",
            "warm coven: " + (", ".join(warm) if warm else "none"),
        ]
        text = "\n".join(lines)
        block = Block(
            layer=3,
            key=key,
            text=text,
        )
        return key, block

    def _retain_environment_snapshot(self, *, run_id: str, key: str, block: Block) -> None:
        """Lease one current canonical snapshot to a run."""
        previous_key = self._env_snapshot_key_by_run.get(run_id)
        if previous_key is not None and previous_key != key:
            previous = self._env_snapshots.get(previous_key)
            if previous is not None:
                previous.run_ids.discard(run_id)
                if not previous.run_ids:
                    self._env_snapshots.pop(previous_key, None)
        snapshot = self._env_snapshots.setdefault(key, _EnvironmentSnapshot(block=block))
        snapshot.run_ids.add(run_id)
        self._env_snapshot_key_by_run[run_id] = key

    def _bounded_history(self, history: list[Any], *, budget: int) -> list[Any]:
        """Keep newest complete Pydantic message groups within both governors."""
        if self.turn_window <= 0:
            return []
        groups = self._history_groups(history)[-self.turn_window :]
        selected: list[list[Any]] = []
        remaining = budget
        for group in reversed(groups):
            cost = self._history_cost(group)
            if cost > remaining:
                break
            selected.append(group)
            remaining -= cost
        selected.reverse()
        return [message for group in selected for message in group]

    def _history_groups(self, history: list[Any]) -> list[list[Any]]:
        """Group messages by Pydantic run id, with a safe legacy request boundary."""
        groups: list[list[Any]] = []
        current: list[Any] = []
        current_run_id: str | None = None
        for message in history:
            payload = cast("dict[str, Any]", message) if isinstance(message, dict) else {}
            run_id = payload.get("run_id")
            typed_run_id = str(run_id) if run_id else None
            is_request = payload.get("kind") == "request" or payload.get("role") == "user"
            boundary = bool(
                current
                and (
                    (typed_run_id is not None and typed_run_id != current_run_id)
                    or (typed_run_id is None and is_request)
                )
            )
            if boundary:
                groups.append(current)
                current = []
            current.append(message)
            current_run_id = typed_run_id
        if current:
            groups.append(current)
        return groups

    def _history_cost(self, history: list[Any]) -> int:
        """Return the conservative serialized-character cost used by both governors."""
        return len(json.dumps(history, sort_keys=True, separators=(",", ":"), default=str))

    def _state_block(self, window: list[Any]) -> Block:
        text = json.dumps(window, sort_keys=True, separators=(",", ":"), default=str)
        return Block(layer=5, key="state:window", text=text)

    def _query_block(self, query: str) -> Block:
        return Block(layer=6, key="query", text=query)

    def _warm_capability_keys(self) -> list[str]:
        return sorted(
            state.capability_key for state in self.registry.list_capability_states() if state.warm or state.is_active
        )

    def _context_window(self, grant: CapabilityGrant | None) -> int | None:
        """Read the context window from the active grant, never from static config.

        The spec carries the discovered ``max_context``; the resolved generation profile
        overlays a rune override. (The old metadata-key lookup read keys no writer ever
        produced and getattr'd a StrEnum surface — it was silently always None.)
        """
        if grant is None:
            return None
        return grant.spec.generation_profile.max_context or grant.spec.max_context
