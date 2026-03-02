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
                    if settings.WHISPER_BACKEND == "mlx-whisper":
                        cls._model = _load_mlx_model()
                    else:
                        cls._model = _load_faster_whisper_model()
        return cls._model

    @classmethod
    def transcribe(cls, audio_path: str, language: str | None = None) -> List[TranscriptSegment]:
        cls._load_model()
        if settings.WHISPER_BACKEND == "mlx-whisper":
            return _transcribe_mlx(audio_path, language)
        else:
            return _transcribe_faster_whisper(cls._model, audio_path, language)


# ── faster-whisper backend ────────────────────────────────────────────────────

def _load_faster_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed") from exc
    logger.info(
        "Loading faster-whisper model=%s device=%s compute_type=%s",
        settings.WHISPER_MODEL, settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE,
    )
    return WhisperModel(
        settings.WHISPER_MODEL,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )


def _transcribe_faster_whisper(model, audio_path: str, language: str | None) -> List[TranscriptSegment]:
    segments, info = model.transcribe(audio_path, language=language, vad_filter=True)
    output: List[TranscriptSegment] = []
    for segment in segments:
        output.append(TranscriptSegment(
            start=float(segment.start),
            end=float(segment.end),
            text=segment.text.strip(),
            language=getattr(info, "language", None),
        ))
    logger.info("ASR (faster-whisper) completed: %d segments", len(output))
    return output


# ── mlx-whisper backend (Apple Silicon) ──────────────────────────────────────

def _load_mlx_model():
    try:
        import mlx_whisper  # noqa: F401 — confirm importable at load time
    except ImportError as exc:
        raise RuntimeError("mlx-whisper is not installed. Run: pip install mlx-whisper") from exc
    logger.info("mlx-whisper model=%s (loaded on first transcribe call)", settings.WHISPER_MLX_MODEL)
    return "mlx-whisper"  # mlx_whisper.transcribe() is stateless; sentinel value


def _transcribe_mlx(audio_path: str, language: str | None) -> List[TranscriptSegment]:
    import mlx_whisper
    logger.info("Running mlx-whisper transcription: model=%s", settings.WHISPER_MLX_MODEL)
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=settings.WHISPER_MLX_MODEL,
        language=language,
        verbose=False,
    )
    detected_language = result.get("language")
    output: List[TranscriptSegment] = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if text:
            output.append(TranscriptSegment(
                start=float(seg["start"]),
                end=float(seg["end"]),
                text=text,
                language=detected_language,
            ))
    logger.info("ASR (mlx-whisper) completed: %d segments", len(output))
    return output
