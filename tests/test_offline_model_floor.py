"""Selecting a test outside the agents package still refuses real model requests."""

from __future__ import annotations

import httpx2
import pytest
from openai import AsyncOpenAI
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [False, True])
async def test_repository_model_guard_precedes_transport(*, streaming: bool) -> None:
    def unexpected_request(request: httpx2.Request) -> httpx2.Response:
        pytest.fail(f"The offline test guard allowed a transport call to {request.url.host}.")

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(unexpected_request)) as client:
        sdk = AsyncOpenAI(base_url="https://offline.invalid/v1", api_key="fixture", http_client=client)
        model = OpenAIChatModel("fixture", provider=OpenAIProvider(openai_client=sdk))
        messages: list[ModelMessage] = [
            ModelRequest(parts=[UserPromptPart("The request must be refused before transport.")])
        ]
        if streaming:
            with (
                pytest.raises(RuntimeError, match="Model requests are not allowed"),
            ):
                async with model.request_stream(messages, None, ModelRequestParameters()):
                    pass
        else:
            with pytest.raises(RuntimeError, match="Model requests are not allowed"):
                await model.request(messages, None, ModelRequestParameters())
