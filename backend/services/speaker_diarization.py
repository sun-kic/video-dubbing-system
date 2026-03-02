from __future__ import annotations

from threading import Lock

from backend.core.config import settings
from backend.core.logging import logger
from backend.models.schemas import DiarizationSegment


class SpeakerDiarizationService:
    _pipeline = None
    _lock = Lock()

    @classmethod
    def _load_pipeline(cls):
        if cls._pipeline is None:
            with cls._lock:
                if cls._pipeline is None:
                    try:
                        from pyannote.audio import Pipeline
                    except ImportError as exc:
                        raise RuntimeError(
                            "pyannote.audio is not installed. Install requirements.txt"
                        ) from exc

                    logger.info(
                        "Loading diarization model=%s device=%s",
                        settings.DIARIZATION_MODEL,
                        settings.DIARIZATION_DEVICE,
                    )
                    cls._pipeline = Pipeline.from_pretrained(
                        settings.DIARIZATION_MODEL,
                        token=settings.HF_TOKEN or None,
                    )
                    # Move to configured device (cpu / cuda / mps)
                    if settings.DIARIZATION_DEVICE != "cpu":
                        import torch
                        cls._pipeline = cls._pipeline.to(
                            torch.device(settings.DIARIZATION_DEVICE)
                        )
        return cls._pipeline

    @classmethod
    def diarize(cls, audio_path: str) -> list[DiarizationSegment]:
        pipeline = cls._load_pipeline()
        output = pipeline(audio_path, min_speakers=1, max_speakers=10)

        # Support both pyannote 3.x (returns Annotation directly)
        # and pyannote 4.x (returns DiarizeOutput with .speaker_diarization)
        if hasattr(output, "speaker_diarization"):
            annotation = output.speaker_diarization
        else:
            annotation = output

        segments: list[DiarizationSegment] = []
        for segment, _, label in annotation.itertracks(yield_label=True):
            segments.append(
                DiarizationSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    speaker=str(label),
                )
            )

        logger.info("Diarization completed for %s: %d segments", audio_path, len(segments))
        return segments
