import asyncio
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from api.database import get_session_factory
from api.models import Job, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

POLL_INTERVAL_SECONDS = 1.5
TERMINAL_STATUSES = {JobStatus.done, JobStatus.error}


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: uuid.UUID) -> None:
    """Stream job progress updates to the client via WebSocket polling."""
    await websocket.accept()

    try:
        while True:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

            if job is None:
                await websocket.send_json(
                    {"error": "Job not found", "job_id": str(job_id)}
                )
                break

            payload = {
                "job_id": str(job.id),
                "status": job.status.value,
                "step_message": job.step_message,
                "progress_pct": job.progress_pct,
                "error_message": job.error_message,
            }
            await websocket.send_json(payload)

            if job.status in TERMINAL_STATUSES:
                break

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected for job %s", job_id)
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass  # Already closed by client
