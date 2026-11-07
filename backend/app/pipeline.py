import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from .config import Settings
from .correlation import correlation_prompt, merge_findings
from .detector import detect_observations
from .deterministic_findings import build_findings
from .evidence import (
    EvidenceValidationError,
    validate_finding_against_source,
    validate_known_finding_evidence,
    validate_novel_finding_evidence,
)
from .llm_client import LlamaClient
from .models import AnalysisChunk, AnalysisJob, FindingRecord, ObservationRecord
from .normalization import KNOWN_TYPES, PLACEHOLDER_TYPES, canonicalize_finding
from .prompts import SYSTEM_PROMPT, chunk_prompt
from .splitter import split_log_file
from .tokenizer import LlamaTokenizer
from .validation import validate_findings


def count_lines(path: str) -> int:
    with open(path, encoding="utf-8") as source:
        return sum(1 for _ in source)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def analyze_job(job_id: str, session: Session, settings: Settings) -> None:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        return

    job.status = "running"
    job.error_message = None
    job.total_lines = count_lines(job.stored_path)
    session.add(job)
    session.commit()

    tokenizer = LlamaTokenizer(settings)
    llm = LlamaClient(settings)
    observations = detect_observations(job.stored_path)
    observation_lines: dict[int, set[str]] = {}
    for observation in observations:
        observation_lines.setdefault(observation.line, set()).add(observation.event_type)
    observation_records = [
        ObservationRecord(
            job_id=job.id,
            line_number=observation.line,
            timestamp=observation.timestamp,
            actor_id=observation.actor_id,
            event_type=observation.event_type,
            summary=observation.summary,
            attributes_json=json.dumps(observation.attributes),
        )
        for observation in observations
    ]
    session.add_all(observation_records)
    session.commit()
    context: list[str] = []
    model_findings = []
    seen_chunks = 0

    try:
        async for source_chunk in split_log_file(
            job.stored_path,
            tokenizer,
            settings.log_token_budget,
        ):
            chunk = AnalysisChunk(
                job_id=job.id,
                chunk_index=source_chunk.index,
                start_line=source_chunk.start_line,
                end_line=source_chunk.end_line,
                text=source_chunk.text,
                input_tokens=source_chunk.token_count,
                status="running",
            )
            session.add(chunk)
            session.commit()
            session.refresh(chunk)
            seen_chunks += 1
            for observation_record in observation_records:
                if source_chunk.start_line <= observation_record.line_number <= source_chunk.end_line:
                    observation_record.chunk_id = chunk.id
                    session.add(observation_record)
            job.total_chunks = seen_chunks
            session.add(job)
            session.commit()

            try:
                completion = await llm.complete(
                    SYSTEM_PROMPT,
                    chunk_prompt(
                        chunk_index=source_chunk.index,
                        start_line=source_chunk.start_line,
                        end_line=source_chunk.end_line,
                        text=source_chunk.text,
                        context=context,
                        observations=[
                            {
                                "line": item.line,
                                "event_type": item.event_type,
                                "actor_id": item.actor_id,
                                "summary": item.summary,
                            }
                            for item in observations
                            if source_chunk.start_line <= item.line <= source_chunk.end_line
                        ],
                    ),
                )
                response = validate_findings(
                    completion.content,
                    start_line=source_chunk.start_line,
                    end_line=source_chunk.end_line,
                )
                chunk.raw_response = completion.content
                chunk.output_tokens = completion.output_tokens
                chunk.duration_ms = completion.duration_ms
                chunk.status = "completed"
                for finding in response.findings:
                    try:
                        validate_finding_against_source(finding, job.stored_path)
                        validate_known_finding_evidence(finding, observation_lines)
                    except EvidenceValidationError:
                        continue
                    model_findings.append(finding)
            except Exception as exc:
                chunk.status = "failed"
                chunk.error_message = str(exc)
            finally:
                session.add(chunk)
                job.completed_chunks = seen_chunks
                session.add(job)
                session.commit()

        job.status = "completed"
        job.total_chunks = seen_chunks
        job.completed_at = utc_now()
        deterministic_findings = [
            canonicalize_finding(finding) for finding in build_findings(observations)
        ]
        deterministic_findings = merge_findings(deterministic_findings)
        valid_findings = list(deterministic_findings)
        for raw_finding in model_findings:
            finding = canonicalize_finding(raw_finding)
            if finding.attack_type in PLACEHOLDER_TYPES:
                continue
            try:
                validate_finding_against_source(finding, job.stored_path)
                validate_known_finding_evidence(finding, observation_lines)
            except EvidenceValidationError:
                continue
            if finding.attack_type in KNOWN_TYPES:
                # Known families are represented by deterministic aggregate findings.
                # The model still participates in chunk analysis and final explanation,
                # but cannot create duplicate or weaker known-family records.
                continue
            try:
                validate_novel_finding_evidence(finding, job.stored_path, observation_lines)
            except EvidenceValidationError:
                continue
            valid_findings.append(finding)
        merged = merge_findings(valid_findings)
        if merged:
            try:
                completion = await llm.complete(
                    SYSTEM_PROMPT,
                    correlation_prompt(merged),
                )
                final_response = validate_findings(completion.content)
                explained = []
                for candidate in merged:
                    matches = [
                        item
                        for item in final_response.findings
                        if item.attack_type == candidate.attack_type
                        and item.actor_id == candidate.actor_id
                        and {e.line for e in item.evidence}.issubset(
                            {e.line for e in candidate.evidence}
                        )
                    ]
                    if matches:
                        model_explanation = matches[0]
                        explained.append(
                            candidate.model_copy(
                                update={
                                    "reason": model_explanation.reason,
                                    "suggested_action": model_explanation.suggested_action,
                                }
                            )
                        )
                    else:
                        explained.append(candidate)
                merged = explained
            except Exception:
                # Deterministic findings remain the safe fallback.
                pass
            for record in session.exec(
                select(FindingRecord).where(FindingRecord.job_id == job.id)
            ).all():
                session.delete(record)
            session.commit()
            for finding in merged:
                session.add(
                    FindingRecord(
                        job_id=job.id,
                        attack_type=finding.attack_type,
                        severity=finding.severity,
                        actor_id=finding.actor_id,
                        evidence_json=json.dumps(
                            [item.model_dump() for item in finding.evidence]
                        ),
                        reason=finding.reason,
                        suggested_action=finding.suggested_action,
                    )
                )
        session.add(job)
        session.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.total_chunks = seen_chunks
        session.add(job)
        session.commit()


async def run_analysis_job(job_id: str) -> None:
    from .database import engine

    with Session(engine) as session:
        await analyze_job(job_id, session, Settings())
