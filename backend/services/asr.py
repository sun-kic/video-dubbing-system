from __future__ import annotations

from threading import Lock
from typing import List

from backend.core.config import settings
from backend.core.logging import logger
from backend.models.schemas import TranscriptSegment


class ASRService:
    _model = None
    _lock = Lock()

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    try:
                        from faster_whisper import WhisperModel
                    except ImportError as exc:
                        raise RuntimeError(
                            "faster-whisper is not installed. Install requirements.txt"
                        ) from exc

                    logger.info(
                        "Loading Whisper model=%s device=%s",
                        settings.WHISPER_MODEL,
                        settings.WHISPER_DEVICE,
                    )
                    cls._model = WhisperModel(
                        settings.WHISPER_MODEL,
                        device=settings.WHISPER_DEVICE,
                        compute_type=settings.WHISPER_COMPUTE_TYPE,
                    )
        return cls._model

    @classmethod
    def transcribe(cls, audio_path: str, language: str | None = None) -> List[TranscriptSegment]:
        model = cls._load_model()
        segments, info = model.transcribe(audio_path, language=language, vad_filter=True)

        output: List[TranscriptSegment] = []
        for segment in segments:
            output.append(
                TranscriptSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=segment.text.strip(),
                    language=getattr(info, "language", None),
                )
            )

        logger.info("ASR completed for %s: %d segments", audio_path, len(output))
        return output
