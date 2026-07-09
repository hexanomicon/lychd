"""The keyed-block Context Orchestrator (CAG, ADR 21 / ADR 28 §2).

Assembles a six-layer Stable Floor as an ordered set of frozen `Block`s. The
assembly is a pure function of the block key set: an identical key set yields a
byte-identical prefix, witnessed by `prefix_digest` (sha256 over the layer 1-4
hashes). Volatile data may enter only layers 5-6.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.animation.services.registry import AnimatorRegistry

_DEFAULT_TURN_WINDOW = 20
_DEFAULT_CHAR_CAP = 96_000
_FLOOR_LAYER_MIN = 2
_FLOOR_LAYER_MAX = 4


def _sha256(text: str) -> str:
    """Return the hex sha256 digest of `text`."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, kw_only=True)
class Block:
    """One keyed context block. `content_hash` is the sha256 of `text`."""

    layer: int
    key: str
    content_hash: str
    text: str


@dataclass(frozen=True, kw_only=True)
class AssembledContext:
    """The assembled Stable Floor for one run.

    `prefix_digest` is the cache receipt over layers 1-4; `state_window` is
    layer 5 as message history; `query` is layer 6.
    """

    blocks: tuple[Block, ...]
    prefix_digest: str
    state_window: list[dict[str, str]]
    query: str
    context_window: int | None = None

    def floor_text(self) -> str:
        """Render layers 2-4 in (layer, key) order for the dynamic instructions hook."""
        return "\n\n".join(
            block.text for block in self.blocks if _FLOOR_LAYER_MIN <= block.layer <= _FLOOR_LAYER_MAX and block.text
        )


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
    in the `WeaveContext` node.
    """

    registry: AnimatorRegistry
    turn_window: int = _DEFAULT_TURN_WINDOW
    char_cap: int = _DEFAULT_CHAR_CAP
    _cache: dict[str, AssembledContext] = field(default_factory=dict)
    _env_snapshots: dict[str, Block] = field(default_factory=dict)

    def assemble(
        self,
        *,
        run_id: str,
        session_id: str,
        query: str,
        history: list[dict[str, str]] | None = None,
        grant: CapabilityGrant | None = None,
        grant_epoch: int = 0,
    ) -> AssembledContext:
        """Assemble the six-layer floor, cache it under `run_id`, and return it."""
        window = list(history or [])[-self.turn_window :]

        stable_blocks: list[Block] = [
            self._identity_block(),
            self._codex_block(),
            self._environment_block(session_id=session_id, grant=grant, grant_epoch=grant_epoch),
            self._karma_block(session_id=session_id),
        ]
        stable_blocks.sort(key=lambda block: (block.layer, block.key))

        prefix_digest = _sha256("|".join(block.content_hash for block in stable_blocks))

        state_block = self._state_block(window)
        query_block = self._query_block(query)
        blocks = (*stable_blocks, state_block, query_block)

        assembled = AssembledContext(
            blocks=blocks,
            prefix_digest=prefix_digest,
            state_window=window,
            query=query,
            context_window=self._context_window(grant),
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
        """Drop the cached assembly for `run_id` once its run has settled."""
        self._cache.pop(run_id, None)

    def _identity_block(self) -> Block:
        return Block(
            layer=1,
            key=IDENTITY_BLOCK_KEY,
            content_hash=_sha256(IDENTITY_BLOCK_TEXT),
            text=IDENTITY_BLOCK_TEXT,
        )

    def _codex_block(self) -> Block:
        # Stubbed: key reserved for future path-aware Codex hydration.
        return Block(layer=2, key="codex:none:v0", content_hash=_sha256(""), text="")

    def _environment_block(
        self,
        *,
        session_id: str,
        grant: CapabilityGrant | None,
        grant_epoch: int,
    ) -> Block:
        # Snapshot per (session, grant_epoch): the env block is frozen at that
        # key and refreshed only at a grant-change boundary, so an identical key
        # set yields byte-identical bytes even if warm hardware churns between
        # assembles within the same epoch (§6 Environment ruling).
        key = f"env:{session_id}:{grant_epoch}"
        cached = self._env_snapshots.get(key)
        if cached is not None:
            return cached

        active_key = grant.spec.key if grant is not None else "none"
        warm = self._warm_capability_keys()
        lines = [
            "# Environment",
            f"active capability: {active_key}",
            "warm coven: " + (", ".join(warm) if warm else "none"),
        ]
        text = "\n".join(lines)
        block = Block(layer=3, key=key, content_hash=_sha256(text), text=text)
        self._env_snapshots[key] = block
        return block

    def _karma_block(self, *, session_id: str) -> Block:
        # Stubbed: Archive/mem0 unbuilt; key session-pinned (Cache Meridian after layer 4).
        return Block(layer=4, key=f"karma:{session_id}:pinned", content_hash=_sha256(""), text="")

    def _state_block(self, window: list[dict[str, str]]) -> Block:
        text = "\n".join(f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in window)
        return Block(layer=5, key="state:window", content_hash=_sha256(text), text=text)

    def _query_block(self, query: str) -> Block:
        return Block(layer=6, key="query", content_hash=_sha256(query), text=query)

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
        return grant.spec.max_context or grant.generation.max_context
