from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TokenCounter(Protocol):
    async def count_tokens(self, text: str) -> int: ...


@dataclass(frozen=True)
class LogChunk:
    index: int
    start_line: int
    end_line: int
    text: str
    token_count: int


def render_line(line_number: int, line: str) -> str:
    return f"{line_number}: {line.rstrip(chr(13) + chr(10))}"


async def split_log_file(
    path: str | Path,
    tokenizer: TokenCounter,
    token_budget: int,
) -> AsyncIterator[LogChunk]:
    if token_budget < 1:
        raise ValueError("token_budget must be greater than zero")

    current: list[str] = []
    current_start = 1
    current_tokens = 0
    chunk_index = 0

    with Path(path).open("r", encoding="utf-8", newline="") as source:
        for line_number, line in enumerate(source, start=1):
            rendered = render_line(line_number, line)
            candidate = "\n".join([*current, rendered])
            candidate_tokens = await tokenizer.count_tokens(candidate)

            if current and candidate_tokens > token_budget:
                yield LogChunk(
                    index=chunk_index,
                    start_line=current_start,
                    end_line=line_number - 1,
                    text="\n".join(current),
                    token_count=current_tokens,
                )
                chunk_index += 1
                current = [rendered]
                current_start = line_number
                current_tokens = await tokenizer.count_tokens(rendered)
                continue

            if not current:
                current_start = line_number
                current_tokens = candidate_tokens
            else:
                current_tokens = candidate_tokens
            current.append(rendered)

    if current:
        yield LogChunk(
            index=chunk_index,
            start_line=current_start,
            end_line=current_start + len(current) - 1,
            text="\n".join(current),
            token_count=current_tokens,
        )
