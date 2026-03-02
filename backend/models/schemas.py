from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional  # Optional kept for other models

from pydantic import BaseModel, Field, field_validator


class JobState(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    language: Optional[str] = None


class DiarizationSegment(BaseModel):
    start: float
    end: float
    speaker: str


class DubbingSegment(BaseModel):
    start: float
    end: float
    speaker: str
    text: str
    output_audio_path: Optional[str] = None


class CreateDubbingJobRequest(BaseModel):
    video_path: str = Field(..., description="Absolute or mounted path to source video")
    target_language: str = Field(default="en")
    speaker_voice_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Map diarization speaker labels to reference WAV paths for cloning",
    )

    @field_validator("video_path")
    @classmethod
    def validate_video_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("video_path cannot be empty")
        return value


class CreateDubbingJobResponse(BaseModel):
    task_id: str
    status: JobState
    submitted_at: datetime


class TaskStatusResponse(BaseModel):
    task_id: str
    status: JobState
    progress: float = 0.0
    message: str = ""
    result: Optional[dict] = None


class VoiceCloneRequest(BaseModel):
    text: str
    language: str = "en"
    reference_audio_path: str
    output_path: Optional[str] = None


class VoiceCloneResponse(BaseModel):
    output_path: str


class PipelineResult(BaseModel):
    input_video: str
    output_video: str
    transcript_segments: int
    speakers_detected: List[str]
    generated_audio_dir: str
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str


def validate_existing_path(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return p
