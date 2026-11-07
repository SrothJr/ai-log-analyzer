import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from app.config import Settings
from app.uploads import save_text_upload


@pytest.mark.asyncio
async def test_save_text_upload_preserves_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    upload = UploadFile(filename="events.log", file=io.BytesIO("héllo\n".encode()))

    path, size = await save_text_upload(upload, str(uuid4()), Settings())

    assert Path(path).read_text(encoding="utf-8") == "héllo\n"
    assert size == len("héllo\n".encode())


@pytest.mark.asyncio
async def test_save_text_upload_rejects_extension(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    upload = UploadFile(filename="events.csv", file=io.BytesIO(b"x"))

    with pytest.raises(HTTPException) as error:
        await save_text_upload(upload, str(uuid4()), Settings())

    assert error.value.status_code == 415


@pytest.mark.asyncio
async def test_save_text_upload_rejects_invalid_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    upload = UploadFile(filename="events.txt", file=io.BytesIO(b"\xff"))

    with pytest.raises(HTTPException) as error:
        await save_text_upload(upload, str(uuid4()), Settings())

    assert error.value.status_code == 400
