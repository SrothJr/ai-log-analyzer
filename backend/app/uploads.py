import codecs
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from .config import Settings


ALLOWED_EXTENSIONS = {".log", ".txt"}
READ_SIZE = 1024 * 1024


async def save_text_upload(
    upload: UploadFile,
    job_id: str,
    settings: Settings,
) -> tuple[str, int]:
    filename = Path(upload.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .log and .txt files are supported.",
        )

    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{job_id}{suffix}"
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    total_bytes = 0

    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(READ_SIZE):
                total_bytes += len(chunk)
                if total_bytes > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="The uploaded file exceeds the configured size limit.",
                    )
                decoder.decode(chunk)
                output.write(chunk)
            decoder.decode(b"", final=True)
    except UnicodeDecodeError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file must be valid UTF-8 text.",
        ) from exc
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return str(destination), total_bytes
