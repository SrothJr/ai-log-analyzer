import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings


class LlamaClientError(RuntimeError):
    """Raised when llama.cpp cannot complete a request."""


@dataclass(frozen=True)
class Completion:
    content: str
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int


class LlamaClient:
    def __init__(self, settings: Settings) -> None:
        base_url = settings.llama_server_url.rstrip("/")
        self.url = f"{base_url}/v1/chat/completions"
        self.timeout = settings.llm_timeout_seconds
        self.context_size = settings.llama_context_size
        self.max_output_tokens = settings.max_output_tokens
        self._lock = asyncio.Lock()

    async def complete(self, system_prompt: str, user_prompt: str) -> Completion:
        request = {
            "model": "local",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": self.max_output_tokens,
            "stream": False,
        }

        async with self._lock:
            last_error: Exception | None = None
            for attempt in range(2):
                started = time.perf_counter()
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(self.url, json=request)
                        response.raise_for_status()
                        payload: Any = response.json()
                        content = payload["choices"][0]["message"]["content"]
                        if not isinstance(content, str):
                            raise ValueError("completion content is not text")
                        usage = payload.get("usage") or {}
                        return Completion(
                            content=content,
                            input_tokens=usage.get("prompt_tokens"),
                            output_tokens=usage.get("completion_tokens"),
                            duration_ms=round((time.perf_counter() - started) * 1000),
                        )
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                    last_error = exc
                    if attempt == 0:
                        continue
            raise LlamaClientError("llama.cpp completion failed after one retry") from last_error
