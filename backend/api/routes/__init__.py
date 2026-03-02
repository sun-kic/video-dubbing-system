from __future__ import annotations

from datetime import datetime
from pathlib import Path

from celery.result import AsyncResult
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.models.schemas import (
    CreateDubbingJobRequest,
    CreateDubbingJobResponse,
    JobState,
    TaskStatusResponse,
    VoiceCloneRequest,
    VoiceCloneResponse,
)
from backend.services.tts import TTSService
from backend.workers.celery_app import celery_app
from backend.workers.tasks import process_video_dubbing

router = APIRouter()


@router.post(
    "/dubbing/jobs",
    response_model=CreateDubbingJobResponse,
    responses={400: {"description": "Bad request"}, 500: {"description": "Internal server error"}},
)
async def create_dubbing_job(payload: CreateDubbingJobRequest) -> CreateDubbingJobResponse:
    source_path = Path(payload.video_path)
    if not source_path.exists():
        raise HTTPException(status_code=400, detail=f"Source video not found: {payload.video_path}")

    task = process_video_dubbing.delay(
        video_path=payload.video_path,
        target_language=payload.target_language,
        speaker_voice_map=payload.speaker_voice_map,
    )

    return CreateDubbingJobResponse(
        task_id=task.id,
        status=JobState.PENDING,
        submitted_at=datetime.utcnow(),
    )


@router.get("/dubbing/jobs/{task_id}", response_model=TaskStatusResponse)
async def get_dubbing_job_status(task_id: str) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)
    status = JobState(result.status) if result.status in JobState._value2member_map_ else JobState.PENDING

    progress = 0.0
    message = ""
    payload = None

    if isinstance(result.info, dict):
        progress = float(result.info.get("progress", 0.0))
        message = str(result.info.get("message", ""))

    if result.successful():
        payload = result.result
        progress = 1.0

    if result.failed() and not message:
        message = str(result.info)

    return TaskStatusResponse(
        task_id=task_id,
        status=status,
        progress=progress,
        message=message,
        result=payload,
    )


@router.post("/voice-clone/synthesize", response_model=VoiceCloneResponse)
async def synthesize_voice_clone(payload: VoiceCloneRequest) -> VoiceCloneResponse:
    ref = Path(payload.reference_audio_path)
    if not ref.exists():
        raise HTTPException(status_code=400, detail=f"Reference audio not found: {payload.reference_audio_path}")

    output_path = payload.output_path or str(settings.LOCAL_STORAGE_PATH / f"tts_{datetime.utcnow().timestamp():.0f}.wav")
    try:
        generated = TTSService.synthesize_with_clone(
            text=payload.text,
            language=payload.language,
            reference_audio_path=payload.reference_audio_path,
            output_path=output_path,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return VoiceCloneResponse(output_path=generated)


@router.post("/media/upload")
async def upload_media(file: UploadFile = File(...)) -> JSONResponse:
    suffix = Path(file.filename or "upload.bin").suffix
    save_dir = settings.LOCAL_STORAGE_PATH / "uploads"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{datetime.utcnow().timestamp():.0f}{suffix}"

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    save_path.write_bytes(content)
    return JSONResponse({"path": str(save_path), "filename": file.filename})
