"""Bounded source-bearing HTTP for the one qualified llama.cpp embedding profile."""

from __future__ import annotations

import asyncio
import json
import math
from hashlib import sha256
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, cast

import httpx2

from lychd.domain.animation.embeddings import (
    EmbeddingBatch,
    EmbeddingDriver,
    EmbeddingRefused,
    EmbeddingVector,
    canonical_float32_vector,
    embedding_digest,
    embedding_vector_digest,
)
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import PROFILE, require_endpoint
from lychd.lib.http import create_async_http_client

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Self

    from lychd.domain.animation.embeddings import EmbeddingInput, EmbeddingOperation


_MAX_ITEM_ID = 160
_CONTROL_CHAR_LIMIT = 32


class LlamaCppEmbeddingDriver(EmbeddingDriver):
    """Single-use operation whose active work cannot escape its admitted lease."""

    def __init__(self, *, base_url: str, operation: EmbeddingOperation) -> None:
        """Validate local routing without opening a connection."""
        self._base_url = require_endpoint(base_url)
        if operation not in {"embed_document", "embed_query"}:
            raise EmbeddingRefused("operation")  # noqa: EM101 - closed machine-readable refusal code
        self._operation: EmbeddingOperation = operation
        self._client: httpx2.AsyncClient | None = None
        self._entered = False
        self._closed = False
        self._used = False
        self._active: set[asyncio.Task[Any]] = set()

    async def __aenter__(self) -> Self:
        """Allocate a nonambient transport without any suspension or source read."""
        if self._entered or self._closed:
            raise EmbeddingRefused("scope")  # noqa: EM101 - closed machine-readable refusal code
        self._client = create_async_http_client(
            timeout=PROFILE.timeout_seconds,
            limits=httpx2.Limits(max_connections=1, max_keepalive_connections=1),
            headers={"Accept-Encoding": "identity"},
        )
        self._entered = True
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        """Close admission then cancel and join every in-flight call before release."""
        self._closed = True
        active = tuple(self._active)
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        if self._client is not None:
            await self._client.aclose()

    async def embed(self, inputs: tuple[EmbeddingInput, ...], *, authorize: Callable[[], None]) -> EmbeddingBatch:
        """Validate source, count exact runtime tokens, then obtain one float32 vector."""
        if not self._entered or self._closed or self._used:
            raise EmbeddingRefused("scope")  # noqa: EM101 - closed machine-readable refusal code
        self._used = True
        current = asyncio.current_task()
        if current is None:
            raise EmbeddingRefused("scope")  # noqa: EM101 - closed refusal code
        self._active.add(current)
        try:
            async with asyncio.timeout(PROFILE.timeout_seconds):
                return await self._embed(inputs, authorize=authorize)
        except (TimeoutError, httpx2.HTTPError):
            raise EmbeddingRefused("transport") from None  # noqa: EM101 - closed machine-readable refusal code
        finally:
            self._active.discard(current)

    async def _embed(self, inputs: tuple[EmbeddingInput, ...], *, authorize: Callable[[], None]) -> EmbeddingBatch:
        if len(inputs) != 1:
            raise EmbeddingRefused("input_count")  # noqa: EM101 - closed machine-readable refusal code
        item = inputs[0]
        if (
            not item.item_id
            or len(item.item_id) > _MAX_ITEM_ID
            or any(ord(c) < _CONTROL_CHAR_LIMIT for c in item.item_id)
        ):
            raise EmbeddingRefused("input_identity")  # noqa: EM101 - closed machine-readable refusal code
        if not item.text or len(item.text) > PROFILE.max_input_bytes or not item.text.strip() or "\0" in item.text:
            raise EmbeddingRefused("input")  # noqa: EM101 - closed machine-readable refusal code
        try:
            item.item_id.encode("utf-8")
            original = item.text.encode("utf-8")
            rendered = (
                PROFILE.query_prefix if self._operation == "embed_query" else PROFILE.document_prefix
            ) + item.text
            encoded = rendered.encode("utf-8")
        except UnicodeError:
            raise EmbeddingRefused("input") from None  # noqa: EM101 - closed machine-readable refusal code
        if len(encoded) > PROFILE.max_input_bytes or sha256(original).hexdigest() != item.input_digest:
            raise EmbeddingRefused("input_digest_or_size")  # noqa: EM101 - closed machine-readable refusal code
        rendered_digest = sha256(encoded).hexdigest()
        counted = await self._post(
            "/tokenize",
            {
                "content": rendered,
                "add_special": True,
                "parse_special": True,
                "with_pieces": False,
            },
            authorize=authorize,
        )
        raw_tokens = counted.get("tokens")
        if not isinstance(raw_tokens, list):
            raise EmbeddingRefused("tokenizer_response")  # noqa: EM101 - closed refusal code
        tokens = cast("list[Any]", raw_tokens)
        if not tokens or any(type(t) is not int or t < 0 for t in tokens):
            raise EmbeddingRefused("tokenizer_response")  # noqa: EM101 - closed machine-readable refusal code
        if len(tokens) > PROFILE.max_input_tokens:
            raise EmbeddingRefused("input_tokens")  # noqa: EM101 - closed machine-readable refusal code
        result = await self._post(
            "/v1/embeddings",
            {
                "model": PROFILE.model_id,
                "input": rendered,
                "encoding_format": "float",
                "embd_normalize": 2,
            },
            authorize=authorize,
        )
        vector = self._vector(result, len(tokens))
        vector_digest = embedding_vector_digest(vector)
        output = EmbeddingVector(item.item_id, item.input_digest, rendered_digest, vector, len(tokens), vector_digest)
        receipt = embedding_digest(
            {
                "profile": PROFILE.digest,
                "operation": self._operation,
                "items": [
                    {
                        "item_id": item.item_id,
                        "input_digest": item.input_digest,
                        "rendered_digest": rendered_digest,
                        "vector_digest": vector_digest,
                        "tokens": len(tokens),
                    }
                ],
            }
        )
        authorize()
        return EmbeddingBatch(PROFILE.digest, self._operation, (output,), receipt)

    async def _post(self, path: str, payload: dict[str, object], *, authorize: Callable[[], None]) -> dict[str, Any]:
        client = self._client
        if client is None or self._closed:
            raise EmbeddingRefused("scope")  # noqa: EM101 - closed machine-readable refusal code
        # Build the exact bytes before the final synchronous disclosure check.
        request = client.build_request("POST", self._base_url.removesuffix("/v1") + path, json=payload)
        authorize()
        response = await client.send(request, stream=True)
        try:
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise EmbeddingRefused("response_encoding")  # noqa: EM101 - closed machine-readable refusal code
            body = bytearray()
            async for chunk in response.aiter_raw(chunk_size=4096):
                if len(body) + len(chunk) > PROFILE.max_response_bytes:
                    raise EmbeddingRefused("response_size")  # noqa: EM101 - closed machine-readable refusal code
                body.extend(chunk)
            if response.status_code != HTTPStatus.OK:
                raise EmbeddingRefused("response_status")  # noqa: EM101 - closed machine-readable refusal code
            try:
                result = json.loads(body)
            except (ValueError, UnicodeError, RecursionError):
                raise EmbeddingRefused("response_json") from None  # noqa: EM101 - closed machine-readable refusal code
            if not isinstance(result, dict):
                raise EmbeddingRefused("response_shape")  # noqa: EM101 - closed machine-readable refusal code
            return cast("dict[str, Any]", result)
        finally:
            await response.aclose()

    @staticmethod
    def _vector(result: dict[str, Any], tokens: int) -> tuple[float, ...]:
        raw_data = result.get("data")
        raw_usage = result.get("usage")
        if not isinstance(raw_data, list) or not isinstance(raw_usage, dict):
            raise EmbeddingRefused("response_identity")  # noqa: EM101 - closed refusal code
        data = cast("list[Any]", raw_data)
        usage = cast("dict[str, Any]", raw_usage)
        if result.get("model") != PROFILE.model_id or len(data) != 1 or not isinstance(data[0], dict):
            raise EmbeddingRefused("response_identity")  # noqa: EM101 - closed refusal code
        entry = cast("dict[str, Any]", data[0])
        if (
            type(entry.get("index")) is not int
            or entry["index"] != 0
            or type(usage.get("prompt_tokens")) is not int
            or usage["prompt_tokens"] != tokens
        ):
            raise EmbeddingRefused("response_identity")  # noqa: EM101 - closed refusal code
        raw_values = entry.get("embedding")
        if not isinstance(raw_values, list):
            raise EmbeddingRefused("vector_dimension")  # noqa: EM101 - closed refusal code
        values = cast("list[Any]", raw_values)
        if len(values) != PROFILE.dimension:
            raise EmbeddingRefused("vector_dimension")  # noqa: EM101 - closed refusal code
        vector = canonical_float32_vector(tuple(values))
        norm = math.sqrt(math.fsum(v * v for v in vector))
        if abs(norm - 1.0) > PROFILE.normalization_tolerance:
            raise EmbeddingRefused("vector_norm")  # noqa: EM101 - closed refusal code
        return vector
