import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_session_factory, get_db
from api.models import Job, JobStatus, Transcription
from api.storage import StorageError, get_presigned_download_url, upload_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

ALLOWED_EXTENSIONS = {"mp3", "wav", "flac", "m4a", "ogg", "aac"}
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


def _validate_upload(filename: str, size: int) -> str:
    """Validate file extension and size. Return the lowercase extension."""
    if "." not in filename:
        raise HTTPException(
            status_code=422,
            detail="File must have an extension.",
        )
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )
    return ext


async def _dispatch_transcription(job_id: str, tuning: str) -> None:
    """Import Modal at call-time and dispatch the transcription worker."""
    try:
        import modal

        transcribe_fn = modal.Function.from_name(
            "tabai-transcription", "run_transcription_pipeline"
        )
        await transcribe_fn.remote.aio(job_id=job_id, tuning=tuning)
    except Exception:
        logger.exception("Modal dispatch failed for job %s", job_id)
        async with get_session_factory()() as session:
            result = await session.execute(
                select(Job).where(Job.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job is not None:
                job.status = JobStatus.error
                job.error_message = "Failed to dispatch transcription worker."
                await session.commit()


@router.post("/upload", status_code=201)
async def upload_audio_file(
    file: UploadFile = File(...),
    tuning: str = Form("standard"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept an audio upload, persist it to R2, and kick off transcription."""
    filename = file.filename or "unknown"
    contents = await file.read()
    _validate_upload(filename, len(contents))

    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        original_filename=filename,
        status=JobStatus.uploading,
        step_message="Uploading audio file…",
        progress_pct=0,
    )
    db.add(job)
    await db.flush()

    try:
        r2_key = upload_audio(contents, filename, str(job_id))
    except StorageError as exc:
        job.status = JobStatus.error
        job.error_message = str(exc)
        await db.flush()
        raise HTTPException(status_code=503, detail="Storage service unavailable.") from exc

    job.audio_r2_key = r2_key
    job.status = JobStatus.pending
    job.step_message = "Queued for processing"
    await db.flush()

    asyncio.create_task(_dispatch_transcription(str(job_id), tuning))

    return {
        "job_id": str(job_id),
        "status": job.status.value,
        "message": "Upload complete. Transcription queued.",
    }


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current status and progress for a job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "step_message": job.step_message,
        "progress_pct": job.progress_pct,
        "error_message": job.error_message,
    }


@router.get("/{job_id}/result")
async def get_job_result(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the full transcription result with presigned download URLs."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status == JobStatus.error:
        raise HTTPException(
            status_code=422,
            detail=job.error_message or "Transcription failed.",
        )
    if job.status != JobStatus.done:
        raise HTTPException(
            status_code=202,
            detail="Transcription is still in progress.",
        )

    tx_result = await db.execute(
        select(Transcription).where(Transcription.job_id == job_id)
    )
    transcription = tx_result.scalar_one_or_none()
    if transcription is None:
        raise HTTPException(
            status_code=404, detail="Transcription record not found."
        )

    download_urls: dict[str, str | None] = {}
    for fmt, key in [
        ("gp5", transcription.gp5_r2_key),
        ("midi", transcription.midi_r2_key),
        ("musicxml", transcription.musicxml_r2_key),
    ]:
        if key:
            try:
                download_urls[fmt] = get_presigned_download_url(key)
            except StorageError:
                logger.warning("Failed to generate presigned URL for %s/%s", fmt, key)
                download_urls[fmt] = None
        else:
            download_urls[fmt] = None

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "tab_data": transcription.tab_data,
        "chords": transcription.chords,
        "bpm": transcription.bpm,
        "key": transcription.key,
        "time_signature": transcription.time_signature,
        "tuning": transcription.tuning,
        "capo_suggestion": transcription.capo_suggestion,
        "download_urls": download_urls,
    }


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a job and its associated transcription."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.transcription is not None:
        await db.delete(job.transcription)
    await db.delete(job)
