from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # App
    APP_NAME: str = "Video Dubbing System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")
    API_V1_PREFIX: str = Field(default="/api/v1")
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # Runtime paths
    BASE_DIR: Path = Field(default=Path(__file__).resolve().parents[2])
    DATA_DIR: Path = Field(default=Path("/tmp/video-dubbing"))
    LOCAL_STORAGE_PATH: Path = Field(default=Path("/tmp/video-dubbing/storage"))
    TEMP_DIR: Path = Field(default=Path("/tmp/video-dubbing/tmp"))

    # Async processing
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./video_dubbing.db")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1")

    # Model config
    WHISPER_MODEL: str = Field(default="large-v3")
    WHISPER_DEVICE: str = Field(default="cpu")
    WHISPER_COMPUTE_TYPE: str = Field(default="int8")

    DIARIZATION_MODEL: str = Field(default="pyannote/speaker-diarization-3.1")
    DIARIZATION_DEVICE: str = Field(default="cpu")
    HF_TOKEN: str = Field(default="")

    VOICE_CLONE_MODEL: str = Field(default="tts_models/multilingual/multi-dataset/xtts_v2")
    TTS_DEVICE: str = Field(default="cpu")

    # Pipeline defaults
    TARGET_LANGUAGE: str = Field(default="en")
    MAX_UPLOAD_SIZE_MB: int = Field(default=500)
    DEFAULT_AUDIO_SAMPLE_RATE: int = Field(default=16000)

    # FFmpeg
    FFMPEG_BIN: str = Field(default="ffmpeg")
    FFPROBE_BIN: str = Field(default="ffprobe")


settings = Settings()


def ensure_directories() -> None:
    for path in (settings.DATA_DIR, settings.LOCAL_STORAGE_PATH, settings.TEMP_DIR):
        path.mkdir(parents=True, exist_ok=True)
