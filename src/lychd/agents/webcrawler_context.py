"""Attach bounded Webcrawler material only to detached outbound model messages."""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from pydantic_ai.messages import ModelRequest, UserPromptPart
from pydantic_ai.models.wrapper import WrapperModel

from lychd.domain.webcrawler.profile import (
    MAX_CONTEXT_CHARS,
    WebcrawlerMaterial,
    WebcrawlerWorkflowCode,
    WebcrawlerWorkflowError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from pydantic_ai import RunContext
    from pydantic_ai.messages import ModelMessage, ModelResponse
    from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.usage import RequestUsage


class WebcrawlerModel(WrapperModel):
    """Project one attributed extraction as untrusted data, never Agent history.

    Current authorization is synchronous and last before every provider count or
    inference call. The envelope and detached messages are prepared before that
    check. A model may quote source text in its answer; this is not an output
    censor or a guarantee that derived text never persists.
    """

    def __init__(
        self, wrapped: Model, *, material: WebcrawlerMaterial, authorize: Callable[[], None], max_chars: int
    ) -> None:
        """Pin an immutable bounded projection inside one acquisition station."""
        if type(max_chars) is not int or not 1 <= max_chars <= MAX_CONTEXT_CHARS:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.PROJECTION)
        model = wrapped
        while isinstance(model, WrapperModel):
            if isinstance(model, WebcrawlerModel):
                raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.PROJECTION)
            model = model.wrapped
        super().__init__(wrapped)
        self._authorize = authorize
        self._timestamp = material.acquired_at
        extraction = material.extraction
        self._wire = json.dumps(
            {
                "kind": "webcrawler_public_page",
                "instruction_authority": "none",
                "attribution": {
                    "attempt_id": str(material.attempt_id),
                    "receipt_id": str(material.receipt_id),
                    "receipt_digest": material.receipt_digest,
                    "requested_url": material.requested_url,
                    "contacted_url": material.contacted_url,
                    "acquired_at": material.acquired_at.isoformat(),
                    "media_type": extraction.media_type,
                    "decoded_body_digest": extraction.source_digest,
                    "record_digest": extraction.record_digest,
                    "text_digest": extraction.text_digest,
                    "extractor": extraction.extractor,
                    "strategy": extraction.strategy,
                    "transformations": list(extraction.transformations),
                },
                "text": extraction.text,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        if len(self._wire) > max_chars:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.PROJECTION)

    def projected_chars(self) -> int:
        """Reserve the complete source envelope in the assembled Context budget."""
        self._authorize()
        return len(self._wire)

    def _outbound(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        source = ModelRequest(parts=[UserPromptPart(self._wire, timestamp=self._timestamp)])
        detached = [source, *deepcopy(messages)]
        self._authorize()
        return detached

    def prepare_messages(
        self, messages: list[ModelMessage], model_request_parameters: ModelRequestParameters | None = None
    ) -> list[ModelMessage]:
        """Keep provider preparation from mutating the Agent's retained messages."""
        return self.wrapped.prepare_messages(deepcopy(messages), model_request_parameters)

    async def count_tokens(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> RequestUsage:
        """Recheck consumption before counting the exact projected request."""
        return await self.wrapped.count_tokens(self._outbound(messages), model_settings, model_request_parameters)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Recheck consumption immediately before local inference handoff."""
        return await self.wrapped.request(self._outbound(messages), model_settings, model_request_parameters)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncGenerator[StreamedResponse]:
        """Use the same current check and preserve the provider's stream lifetime."""
        async with self.wrapped.request_stream(
            self._outbound(messages), model_settings, model_request_parameters, run_context
        ) as response:
            yield response
