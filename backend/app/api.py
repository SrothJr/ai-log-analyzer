import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select

from .config import Settings, get_settings
from .database import get_session
from .models import AnalysisJob, FindingRecord
from .pipeline import run_analysis_job
from .schemas import Finding, JobResponse
from .uploads import save_text_upload


router = APIRouter(prefix="/api")


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AnalysisJob:
    job = AnalysisJob(
        filename=file.filename or "unnamed.log",
        stored_path="",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    try:
        stored_path, _ = await save_text_upload(file, job.id, settings)
    except Exception:
        session.delete(job)
        session.commit()
        raise

    job.stored_path = stored_path
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    session: Session = Depends(get_session),
) -> AnalysisJob:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    return job


@router.post("/jobs/{job_id}/start", response_model=JobResponse)
def start_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> AnalysisJob:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    if job.status not in {"queued", "failed"}:
        raise HTTPException(status_code=409, detail="The analysis job is already running or complete.")
    job.status = "queued"
    job.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(run_analysis_job, job.id)
    return job


@router.get("/jobs/{job_id}/findings", response_model=list[Finding])
def get_findings(
    job_id: str,
    session: Session = Depends(get_session),
) -> list[Finding]:
    if session.get(AnalysisJob, job_id) is None:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    records = session.exec(
        select(FindingRecord).where(FindingRecord.job_id == job_id)
    ).all()
    return [
        Finding(
            attack_type=record.attack_type,
            severity=record.severity,
            actor_id=record.actor_id,
            evidence=json.loads(record.evidence_json),
            reason=record.reason,
            suggested_action=record.suggested_action,
        )
        for record in records
    ]
