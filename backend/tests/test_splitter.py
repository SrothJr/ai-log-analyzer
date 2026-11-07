from pathlib import Path

import pytest

from app.splitter import split_log_file


class CharacterTokenizer:
    async def count_tokens(self, text: str) -> int:
        return len(text)


@pytest.mark.asyncio
async def test_splitter_preserves_lines_and_budget(tmp_path: Path) -> None:
    source = tmp_path / "events.log"
    source.write_text("alpha\nbravo\ncharlie\ndelta\n", encoding="utf-8")

    chunks = [
        chunk
        async for chunk in split_log_file(source, CharacterTokenizer(), token_budget=18)
    ]

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 2), (3, 3), (4, 4)]
    assert [chunk.text for chunk in chunks] == ["1: alpha\n2: bravo", "3: charlie", "4: delta"]
    assert all(chunk.token_count <= 18 for chunk in chunks)


@pytest.mark.asyncio
async def test_splitter_combines_complete_lines(tmp_path: Path) -> None:
    source = tmp_path / "events.log"
    source.write_text("a\nb\nc\n", encoding="utf-8")

    chunks = [
        chunk
        async for chunk in split_log_file(source, CharacterTokenizer(), token_budget=13)
    ]

    assert len(chunks) == 2
    assert chunks[0].text == "1: a\n2: b"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 2
    assert chunks[1].text == "3: c"


@pytest.mark.asyncio
async def test_splitter_rejects_invalid_budget(tmp_path: Path) -> None:
    source = tmp_path / "events.log"
    source.write_text("a\n", encoding="utf-8")

    with pytest.raises(ValueError):
        _ = [chunk async for chunk in split_log_file(source, CharacterTokenizer(), 0)]
