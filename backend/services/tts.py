from __future__ import annotations

from pathlib import Path
from threading import Lock

from backend.core.logging import logger


class TTSService:
    _model = None
    _lock = Lock()

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    try:
                        from f5_tts.api import F5TTS
                    except ImportError as exc:
                        raise RuntimeError(
                            "f5-tts is not installed. Run: pip install f5-tts"
                        ) from exc
                    logger.info("Loading F5-TTS model (F5TTS_v1_Base)...")
                    cls._model = F5TTS(model="F5TTS_v1_Base")
                    logger.info("F5-TTS model loaded")
        return cls._model

    @classmethod
    def synthesize_with_clone(
        cls,
        text: str,
        language: str,
        reference_audio_path: str,
        output_path: str,
    ) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        model = cls._load_model()

        try:
            model.infer(
                ref_file=reference_audio_path,
                ref_text="",  # auto-transcribe reference audio
                gen_text=text,
                file_wave=str(out),
                remove_silence=True,
            )
        except Exception as exc:
            logger.exception("F5-TTS synthesis failed for text: %s", text[:50])
            raise RuntimeError(f"F5-TTS synthesis failed: {exc}") from exc

        if not out.exists():
            raise RuntimeError(f"F5-TTS produced no output at {out}")

        logger.info("TTS synthesis done: %s", out)
        return str(out)
