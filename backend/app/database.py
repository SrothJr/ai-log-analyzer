from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings
from . import models  # noqa: F401


settings = get_settings()
connect_args = {"check_same_thread": False}
engine = create_engine(settings.database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    if settings.database_url.startswith("sqlite:///./"):
        Path("data").mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
