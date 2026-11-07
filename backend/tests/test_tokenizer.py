import json

import httpx
import pytest
import respx

from app.config import Settings
from app.tokenizer import LlamaTokenizer, TokenizerError


@pytest.mark.asyncio
@respx.mock
async def test_llama_tokenizer_counts_response_tokens() -> None:
    route = respx.post("http://127.0.0.1:8080/tokenize").mock(
        return_value=httpx.Response(200, json={"tokens": [1, 2, 3]})
    )

    count = await LlamaTokenizer(Settings()).count_tokens("hello")

    assert count == 3
    assert route.called
    assert json.loads(route.calls.last.request.content) == {"content": "hello", "add_special": False}


@pytest.mark.asyncio
@respx.mock
async def test_llama_tokenizer_rejects_invalid_response() -> None:
    respx.post("http://127.0.0.1:8080/tokenize").mock(
        return_value=httpx.Response(200, json={"unexpected": []})
    )

    with pytest.raises(TokenizerError):
        await LlamaTokenizer(Settings()).count_tokens("hello")
