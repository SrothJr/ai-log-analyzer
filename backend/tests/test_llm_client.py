import httpx
import pytest
import respx

from app.config import Settings
from app.llm_client import LlamaClient


@pytest.mark.asyncio
@respx.mock
async def test_llm_client_returns_completion_and_usage() -> None:
    route = respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"findings": []}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        )
    )

    completion = await LlamaClient(Settings()).complete("system", "user")

    assert completion.content == '{"findings": []}'
    assert completion.input_tokens == 10
    assert completion.output_tokens == 3
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_llm_client_retries_once() -> None:
    route = respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}),
        ]
    )

    completion = await LlamaClient(Settings()).complete("system", "user")

    assert completion.content == "ok"
    assert route.call_count == 2
