from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from celery import states

from backend.core.config import settings
from backend.core.logging import logger
from backend.models.schemas import (
    DiarizationSegment,
    DubbingSegment,
    PipelineResult,
    TranscriptSegment,
)
from backend.services.asr import ASRService
from backend.services.speaker_diarization import SpeakerDiarizationService
from backend.services.tts import TTSService
from backend.services.translation import TranslationService
from backend.services.video_processor import VideoProcessingError, VideoProcessor
from backend.workers.celery_app import celery_app


def _find_best_speaker(
    transcript_segment: TranscriptSegment,
    diarization_segments: List[DiarizationSegment],
) -> str:
    best_speaker = "SPEAKER_00"
    best_overlap = 0.0
    for diar in diarization_segments:
        overlap = max(
            0.0,
            min(transcript_segment.end, diar.end) - max(transcript_segment.start, diar.start),
        )
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = diar.speaker
    return best_speaker


def _align_segments(
    transcript: List[TranscriptSegment],
    diarization: List[DiarizationSegment],
) -> List[DubbingSegment]:
    aligned: List[DubbingSegment] = []
    for seg in transcript:
        aligned.append(
            DubbingSegment(
                start=seg.start,
                end=seg.end,
                speaker=_find_best_speaker(seg, diarization),
                text=seg.text,
            )
        )
    return aligned


def _auto_extract_speaker_refs(
    diarization: List[DiarizationSegment],
    source_audio: str,
    ref_dir: Path,
    target_duration: float = 10.0,
    min_duration: float = 3.0,
) -> Dict[str, str]:
    """
    For each detected speaker, find their longest clean segment and
    extract it as a reference WAV for voice cloning.
    """
    speaker_segments: Dict[str, List[DiarizationSegment]] = defaultdict(list)
    for seg in diarization:
        speaker_segments[seg.speaker].append(seg)

    speaker_refs: Dict[str, str] = {}
    for speaker, segments in speaker_segments.items():
        # Pick the single longest segment for cleanest reference audio
        best = max(segments, key=lambda s: s.end - s.start)
        duration = min(target_duration, best.end - best.start)

        if duration < min_duration:
            logger.warning(
                "Speaker %s has no segment >= %.1fs (best=%.1fs); using anyway",
                speaker, min_duration, duration,
            )

        ref_path = ref_dir / f"ref_{speaker}.wav"
        VideoProcessor.extract_audio_segment(source_audio, str(ref_path), best.start, duration)
        speaker_refs[speaker] = str(ref_path)
        logger.info(
            "Auto ref audio: %s → %.1fs from t=%.1fs", speaker, duration, best.start
        )

    return speaker_refs


@celery_app.task(bind=True, name="dubbing.process_video")
def process_video_dubbing(
    self,
    video_path: str,
    target_language: str,
    speaker_voice_map: Dict[str, str],
    source_language: str = "auto",
) -> dict:
    """
    Process video dubbing with translation and voice cloning.

    Args:
        video_path: Path to source video
        target_language: Target language code (e.g., "en", "ja", "zh")
        speaker_voice_map: Dict mapping speaker labels to reference audio paths.
                           Pass an empty dict {} to auto-extract from the video.
        source_language: Source language code or "auto" for detection
    """
    job_id = str(uuid4())
    logger.info("Starting dubbing job=%s video=%s", job_id, video_path)

    work_dir = settings.TEMP_DIR / f"job-{job_id}"
    generated_audio_dir = work_dir / "tts"
    ref_dir = work_dir / "refs"
    work_dir.mkdir(parents=True, exist_ok=True)
    generated_audio_dir.mkdir(parents=True, exist_ok=True)
    ref_dir.mkdir(parents=True, exist_ok=True)

    try:
        source_video = Path(video_path)
        if not source_video.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        source_audio = str(work_dir / "source.wav")

        # Step 1: Extract audio
        self.update_state(state=states.STARTED, meta={"progress": 0.05, "message": "Extracting audio"})
        VideoProcessor.extract_audio(str(source_video), source_audio, settings.DEFAULT_AUDIO_SAMPLE_RATE)

        # Step 2: ASR
        self.update_state(state=states.STARTED, meta={"progress": 0.15, "message": "Running ASR (speech recognition)"})
        transcript = ASRService.transcribe(source_audio)

        if source_language == "auto":
            source_language = (transcript[0].language if transcript and transcript[0].language else "en")
            logger.info("Detected source language: %s", source_language)

        # Step 3: Translation
        if source_language != target_language:
            self.update_state(state=states.STARTED, meta={"progress": 0.25, "message": f"Translating from {source_language} to {target_language}"}),
            texts = [seg.text for seg in transcript]
            translated_texts = TranslationService.translate(texts, source_language=source_language, target_language=target_language)
            for i, seg in enumerate(transcript):
                if i < len(translated_texts):
                    seg.text = translated_texts[i]
            logger.info("Translation completed: %d segments", len(translated_texts))

        # Step 4: Speaker diarization
        self.update_state(state=states.STARTED, meta={"progress": 0.40, "message": "Running speaker diarization"})
        diarization = SpeakerDiarizationService.diarize(source_audio)

        # Step 5: Auto-extract speaker reference audio if not provided
        if not speaker_voice_map:
            self.update_state(state=states.STARTED, meta={"progress": 0.48, "message": "Auto-extracting speaker reference audio"})
            speaker_voice_map = _auto_extract_speaker_refs(diarization, source_audio, ref_dir)
            logger.info("Auto-extracted refs for %d speakers: %s", len(speaker_voice_map), list(speaker_voice_map.keys()))

        # Step 6: Align segments
        self.update_state(state=states.STARTED, meta={"progress": 0.55, "message": "Aligning segments with speakers"})
        aligned_segments = _align_segments(transcript, diarization)

        # Step 7: TTS synthesis with voice cloning
        self.update_state(state=states.STARTED, meta={"progress": 0.65, "message": "Synthesizing speech with voice cloning"})
        discovered_speakers = sorted({segment.speaker for segment in aligned_segments})

        output_segments: List[str] = []
        for idx, segment in enumerate(aligned_segments):
            segment_file = generated_audio_dir / f"segment_{idx:05d}.wav"
            segment.output_audio_path = str(segment_file)

            speaker_ref = speaker_voice_map.get(segment.speaker)
            if not speaker_ref:
                # Fall back to first available reference
                speaker_ref = next(iter(speaker_voice_map.values()))
                logger.warning("No ref for %s, using fallback", segment.speaker)

            TTSService.synthesize_with_clone(
                text=segment.text,
                language=target_language,
                reference_audio_path=speaker_ref,
                output_path=str(segment_file),
            )
            output_segments.append(str(segment_file))

            segment_progress = 0.65 + (0.20 * (idx + 1) / len(aligned_segments))
            self.update_state(
                state=states.STARTED,
                meta={"progress": segment_progress, "message": f"Synthesizing segment {idx + 1}/{len(aligned_segments)}"}
            )

        # Step 8: Merge audio segments
        self.update_state(state=states.STARTED, meta={"progress": 0.85, "message": "Merging audio segments"})
        dubbed_audio = str(work_dir / "dubbed.wav")
        VideoProcessor.merge_audio_segments(output_segments, dubbed_audio)

        # Step 9: Mux with video
        self.update_state(state=states.STARTED, meta={"progress": 0.95, "message": "Creating output video"})
        output_video = settings.LOCAL_STORAGE_PATH / f"dubbed_{source_video.stem}_{job_id}.mp4"
        VideoProcessor.mux_video_with_audio(str(source_video), dubbed_audio, str(output_video))

        result = PipelineResult(
            input_video=str(source_video),
            output_video=str(output_video),
            transcript_segments=len(aligned_segments),
            speakers_detected=discovered_speakers,
            generated_audio_dir=str(generated_audio_dir),
            created_at=datetime.utcnow(),
        )

        logger.info("Completed dubbing job=%s output=%s", job_id, output_video)
        return result.model_dump()

    except (FileNotFoundError, VideoProcessingError, RuntimeError, ValueError) as exc:
        logger.exception("Dubbing task failed job=%s", job_id)
        self.update_state(state=states.FAILURE, meta={"progress": 1.0, "message": str(exc)})
        raise
