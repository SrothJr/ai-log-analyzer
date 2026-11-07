from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    total_lines: int | None
    total_chunks: int | None
    completed_chunks: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


Severity = Literal["Low", "Medium", "High", "Critical"]


class EvidenceItem(BaseModel):
    line: int
    summary: str


class Finding(BaseModel):
    attack_type: str = Field(min_length=1, max_length=80)
    severity: Severity
    actor_id: str
    evidence: list[EvidenceItem]
    reason: str
    suggested_action: str


class FindingsResponse(BaseModel):
    findings: list[Finding]


class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    start_line: int
    end_line: int
    status: str
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int | None
    error_message: str | None
