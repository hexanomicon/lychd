"""The keyed-block Context Orchestrator (CAG, ADR 21 / ADR 28 §2).

Assembles a six-layer Stable Floor as an ordered set of frozen `Block`s. The
assembly is a pure function of the block key set: an identical key set yields a
byte-identical prefix, witnessed by `prefix_digest` (sha256 over the layer 1-4
hashes). Volatile data may enter only layers 5-6.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from lychd.domain.cortex.privacy import (
    INTERNAL_PRIVATIZATION_LABEL,
    PUBLIC_PRIVATIZATION_LABEL,
    RESTRICTED_UNKNOWN_PRIVATIZATION_LABEL,
    PrivatizationLabel,
)

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.animation.services.registry import AnimatorRegistry

_DEFAULT_TURN_WINDOW = 20
_DEFAULT_CHAR_CAP = 96_000
_FLOOR_LAYER_MIN = 2
_FLOOR_LAYER_MAX = 4


class ContextBudgetExceededError(RuntimeError):
    """The non-negotiable floor and current query exceed the context budget."""


def _sha256(text: str) -> str:
    """Return the hex sha256 digest of `text`."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, kw_only=True)
class Block:
    """One keyed context block with privacy influence metadata."""

    layer: int
    key: str
    content_hash: str
    text: str
    label: PrivatizationLabel


@dataclass(frozen=True, kw_only=True)
class AssembledContext:
    """The assembled Stable Floor for one run.

    `prefix_digest` is the cache receipt over layers 1-4; `state_window` is
    layer 5 as message history; `query` is layer 6.
    """

    blocks: tuple[Block, ...]
    prefix_digest: str
    state_window: list[Any]
    continuation: list[Any]
    query: str
    aggregate_label: PrivatizationLabel
    context_window: int | None = None

    def floor_text(self) -> str:
        """Render layers 2-4 in (layer, key) order for the dynamic instructions hook."""
        return "\n\n".join(
            block.text for block in self.blocks if _FLOOR_LAYER_MIN <= block.layer <= _FLOOR_LAYER_MAX and block.text
        )

    def model_history(self) -> list[Any]:
        """Return bounded settled history followed by the indivisible current chain."""
        return [*self.state_window, *self.continuation]


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

    Layer population (v1): 1/3/5/6 populated; 2/4 stubbed with reserved keys.
    The per-run cache lets `floor_text(run_id)` return exactly the text assembled
    in the `WeaveContext` node. Environment snapshots remain shared and frozen
    only while at least one active run references their key.
    """

    registry: AnimatorRegistry
    turn_window: int = _DEFAULT_TURN_WINDOW
    char_cap: int = _DEFAULT_CHAR_CAP
    _cache: dict[str, AssembledContext] = field(default_factory=dict)
    _env_snapshots: dict[str, _EnvironmentSnapshot] = field(default_factory=dict)
    _env_snapshot_keys_by_run: dict[str, set[str]] = field(default_factory=dict)

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
        query_label: PrivatizationLabel | None = None,
        history_label: PrivatizationLabel | None = None,
        continuation_label: PrivatizationLabel | None = None,
    ) -> AssembledContext:
        """Assemble the six-layer floor, carrying unknown influences as restricted."""
        environment_key, environment_block = self._environment_block(
            session_id=session_id,
            grant=grant,
            grant_epoch=grant_epoch,
        )
        stable_blocks: list[Block] = [
            self._identity_block(),
            self._codex_block(),
            environment_block,
            self._karma_block(session_id=session_id),
        ]
        stable_blocks.sort(key=lambda block: (block.layer, block.key))

        prefix_digest = _sha256("|".join(block.content_hash for block in stable_blocks))

        context_window = self._context_window(grant)
        effective_char_cap = self.char_cap
        if context_window is not None:
            # A conservative conversion keeps the assembled textual context below
            # the discovered token window without pretending to be a tokenizer.
            effective_char_cap = min(effective_char_cap, context_window * 3)
        current_chain = list(continuation or [])
        continuation_chars = self._history_cost(current_chain)
        fixed_chars = sum(len(block.text) for block in stable_blocks) + len(query) + continuation_chars
        if fixed_chars > effective_char_cap:
            msg = (
                f"Stable floor, query, and required continuation require {fixed_chars} characters, "
                f"exceeding the {effective_char_cap}-character context budget."
            )
            raise ContextBudgetExceededError(msg)
        window = self._bounded_history(
            list(history or []),
            budget=effective_char_cap - fixed_chars,
        )
        state_label = PrivatizationLabel.join(
            history_label or self._default_material_label(window),
            continuation_label or self._default_material_label(current_chain),
        )
        state_block = self._state_block([*window, *current_chain], label=state_label)
        query_block = self._query_block(
            query,
            label=query_label or self._default_material_label(query),
        )
        blocks = (*stable_blocks, state_block, query_block)

        assembled = AssembledContext(
            blocks=blocks,
            prefix_digest=prefix_digest,
            state_window=window,
            continuation=current_chain,
            query=query,
            aggregate_label=PrivatizationLabel.join(*(block.label for block in blocks)),
            context_window=context_window,
        )
        self._retain_environment_snapshot(
            run_id=run_id,
            key=environment_key,
            block=environment_block,
        )
        self._cache[run_id] = assembled
        return assembled

    def floor_text(self, run_id: str) -> str:
        """Return the layer 2-4 floor text assembled for `run_id` (empty if unassembled)."""
        assembled = self._cache.get(run_id)
        return assembled.floor_text() if assembled is not None else ""

    def get(self, run_id: str) -> AssembledContext | None:
        """Return the assembled context cached for `run_id`, if any."""
        return self._cache.get(run_id)

    def release(self, run_id: str) -> None:
        """Drop one settled run's assembly and its environment-snapshot leases."""
        self._cache.pop(run_id, None)
        for key in self._env_snapshot_keys_by_run.pop(run_id, ()):
            snapshot = self._env_snapshots.get(key)
            if snapshot is None:
                continue
            snapshot.run_ids.discard(run_id)
            if not snapshot.run_ids:
                self._env_snapshots.pop(key, None)

    def _identity_block(self) -> Block:
        return Block(
            layer=1,
            key=IDENTITY_BLOCK_KEY,
            content_hash=_sha256(IDENTITY_BLOCK_TEXT),
            text=IDENTITY_BLOCK_TEXT,
            label=INTERNAL_PRIVATIZATION_LABEL,
        )

    def _codex_block(self) -> Block:
        # Stubbed: key reserved for future path-aware Codex hydration.
        return Block(
            layer=2,
            key="codex:none:v0",
            content_hash=_sha256(""),
            text="",
            label=PUBLIC_PRIVATIZATION_LABEL,
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
            content_hash=_sha256(text),
            text=text,
            label=INTERNAL_PRIVATIZATION_LABEL,
        )
        return key, block

    def _retain_environment_snapshot(self, *, run_id: str, key: str, block: Block) -> None:
        """Lease a canonical snapshot to one run without double-counting reassembly."""
        snapshot = self._env_snapshots.setdefault(key, _EnvironmentSnapshot(block=block))
        snapshot.run_ids.add(run_id)
        self._env_snapshot_keys_by_run.setdefault(run_id, set()).add(key)

    def _bounded_history(self, history: list[Any], *, budget: int) -> list[Any]:
        """Keep newest complete Pydantic message groups within both governors."""
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

    def _karma_block(self, *, session_id: str) -> Block:
        # Stubbed: Archive/mem0 unbuilt; key session-pinned (Cache Meridian after layer 4).
        return Block(
            layer=4,
            key=f"karma:{session_id}:pinned",
            content_hash=_sha256(""),
            text="",
            label=PUBLIC_PRIVATIZATION_LABEL,
        )

    def _state_block(self, window: list[Any], *, label: PrivatizationLabel) -> Block:
        text = json.dumps(window, sort_keys=True, separators=(",", ":"), default=str)
        return Block(layer=5, key="state:window", content_hash=_sha256(text), text=text, label=label)

    def _query_block(self, query: str, *, label: PrivatizationLabel) -> Block:
        return Block(layer=6, key="query", content_hash=_sha256(query), text=query, label=label)

    @staticmethod
    def _default_material_label(material: str | list[Any]) -> PrivatizationLabel:
        """Treat absent lineage as restricted only when material is present."""
        return RESTRICTED_UNKNOWN_PRIVATIZATION_LABEL if material else PUBLIC_PRIVATIZATION_LABEL

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
        return grant.generation.max_context or grant.spec.max_context
