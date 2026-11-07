from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisJob(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    filename: str
    stored_path: str
    status: str = Field(default="queued", index=True)
    total_lines: Optional[int] = None
    total_chunks: Optional[int] = None
    completed_chunks: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None


class AnalysisChunk(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(index=True)
    chunk_index: int
    start_line: int
    end_line: int
    text: str
    status: str = Field(default="queued", index=True)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    duration_ms: Optional[int] = None
    raw_response: Optional[str] = None
    error_message: Optional[str] = None


class ObservationRecord(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(index=True)
    chunk_id: Optional[str] = Field(default=None, index=True)
    line_number: int = Field(index=True)
    timestamp: Optional[datetime] = None
    actor_id: Optional[str] = Field(default=None, index=True)
    event_type: str = Field(index=True)
    summary: str
    attributes_json: str = "{}"


class FindingRecord(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(index=True)
    chunk_id: Optional[str] = Field(default=None, index=True)
    attack_type: str
    severity: str
    actor_id: str
    evidence_json: str
    reason: str
    suggested_action: str
    fingerprint: Optional[str] = Field(default=None, index=True)
    source_chunk_ids: str = ""
