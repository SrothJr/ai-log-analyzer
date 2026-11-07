from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import Settings
from app.llm_client import Completion
from app.models import AnalysisChunk, AnalysisJob, FindingRecord, ObservationRecord
from app.pipeline import analyze_job


class FakeTokenizer:
    def __init__(self, settings: Settings) -> None:
        pass

    async def count_tokens(self, text: str) -> int:
        return len(text)


class FakeLlamaClient:
    def __init__(self, settings: Settings) -> None:
        self.calls = 0

    async def complete(self, system_prompt: str, user_prompt: str) -> Completion:
        self.calls += 1
        return Completion(
            content=(
                '{"findings":[{"attack_type":"scanning","severity":"Medium",'
                '"actor_id":"203.0.113.90","evidence":[{"line":1,"summary":"probe"}],'
                '"reason":"Repeated probe pattern","suggested_action":"Investigate source"}]}'
            ),
            input_tokens=10,
            output_tokens=5,
            duration_ms=2,
        )


@pytest.mark.asyncio
async def test_analyze_job_persists_each_chunk_and_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "events.log"
    lines = [
        '{"time":"2026-01-01T00:00:00Z","client_ip":"192.0.2.44","method":"POST","path":"/auth/login","status":401,"auth_result":"invalid_password"}',
        '{"time":"2026-01-01T00:01:00Z","client_ip":"192.0.2.44","method":"POST","path":"/auth/login","status":401,"auth_result":"invalid_password"}',
        '{"time":"2026-01-01T00:02:00Z","client_ip":"192.0.2.44","method":"POST","path":"/auth/login","status":401,"auth_result":"invalid_password"}',
    ]
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr("app.pipeline.LlamaTokenizer", FakeTokenizer)
    monkeypatch.setattr("app.pipeline.LlamaClient", FakeLlamaClient)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        job = AnalysisJob(filename="events.log", stored_path=str(source))
        session.add(job)
        session.commit()
        session.refresh(job)

        await analyze_job(job.id, session, Settings(log_token_budget=30))

        saved_job = session.get(AnalysisJob, job.id)
        chunks = session.exec(select(AnalysisChunk)).all()
        findings = session.exec(select(FindingRecord)).all()
        observations = session.exec(select(ObservationRecord)).all()

    assert saved_job is not None
    assert saved_job.status == "completed"
    assert saved_job.completed_chunks == len(chunks)
    assert len(chunks) >= 1
    assert len(findings) == 1
    assert findings[0].attack_type == "brute_force"
    assert len(observations) == 3
