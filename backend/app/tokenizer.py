from typing import Any

import httpx

from .config import Settings


class TokenizerError(RuntimeError):
    """Raised when llama.cpp cannot tokenize text."""


class LlamaTokenizer:
    def __init__(self, settings: Settings) -> None:
        self.url = f"{settings.llama_server_url.rstrip('/')}/tokenize"
        self.timeout = settings.llm_timeout_seconds

    async def count_tokens(self, text: str) -> int:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.url,
                    json={"content": text, "add_special": False},
                )
                response.raise_for_status()
                payload: Any = response.json()
                tokens = payload.get("tokens")
                if not isinstance(tokens, list):
                    raise TokenizerError("llama.cpp tokenizer response has no token list")
                return len(tokens)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise TokenizerError("Unable to count tokens using llama.cpp") from exc
